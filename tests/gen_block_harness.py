"""The harness every gen block test renders through: a gen~ program around blocks, rendered by our GenExpr renderer
(m4l_dev/genexpr.py), and the spectral measures the claims are stated in. Standard library only."""
import cmath
import math
from fractions import Fraction
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m4l_dev.gen_blocks import gen_code_with_blocks  # noqa: E402
from m4l_dev.genexpr import GenProgram, check  # noqa: E402


def harness(blocks, params, outputs, num_inputs=1, samplerate=44100.0):
    """A gen~ program: the Params (name -> default), the blocks, `outN = outputs[N-1];`."""
    declarations = "\n".join(f"Param {name}({value!r}, min=-1e9, max=1e9);" for name, value in params.items())
    statements = "\n".join(f"/*{block.marker}*/" for block in blocks)
    template = (f"/*GEN_BLOCK_FUNCTIONS*/\n{declarations}\n/*GEN_BLOCK_DECLARATIONS*/\n{statements}\n"
                + "".join(f"out{n} = {expression};\n" for n, expression in enumerate(outputs, start=1)))
    code = gen_code_with_blocks(template, blocks, "test harness")
    check(code, num_inputs=num_inputs, num_outputs=len(outputs))
    return GenProgram(code, num_inputs, len(outputs), samplerate=samplerate)


def frequency_by_zero_crossings(signal, samplerate):
    crossings = [i + signal[i] / (signal[i] - signal[i + 1]) for i in range(len(signal) - 1)
                 if signal[i] <= 0 < signal[i + 1]]
    return samplerate * (len(crossings) - 1) / (crossings[-1] - crossings[0])


def amplitude_at(signal, frequency, samplerate):
    """The amplitude of the sinusoid at `frequency` in `signal` (Hann window, one DFT bin evaluated directly)."""
    n = len(signal)
    real = imaginary = window_sum = 0.0
    step = 2 * math.pi * frequency / samplerate
    for i, value in enumerate(signal):
        window = 0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1))
        real += value * window * math.cos(step * i)
        imaginary -= value * window * math.sin(step * i)
        window_sum += window
    return 2 * math.hypot(real, imaginary) / window_sum


def complex_amplitude_at(signal, frequency, samplerate):
    """The complex amplitude (magnitude and phase re a cosine at sample 0) of the sinusoid at `frequency` (Hann
    window, one DFT bin evaluated directly)."""
    n = len(signal)
    total = 0j
    window_sum = 0.0
    step = 2 * math.pi * frequency / samplerate
    for i, value in enumerate(signal):
        window = 0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1))
        total += value * window * complex(math.cos(step * i), -math.sin(step * i))
        window_sum += window
    return 2 * total / window_sum


def phase_degrees(output, reference, frequency, samplerate):
    """The phase of `output` re `reference` at `frequency`, in degrees, (-180, 180]."""
    ratio = complex_amplitude_at(output, frequency, samplerate) / complex_amplitude_at(reference, frequency, samplerate)
    return math.degrees(math.atan2(ratio.imag, ratio.real))


def folded(frequency, samplerate):
    frequency = math.fmod(frequency, samplerate)
    return samplerate - frequency if frequency > samplerate / 2 else frequency


def worst_alias_db(signal, fundamental, harmonics, samplerate, below_hz):
    """The loudest folded harmonic (of `harmonics`, all above Nyquist) landing below `below_hz`, dB re the
    fundamental."""
    reference = amplitude_at(signal, fundamental, samplerate)
    levels = [amplitude_at(signal, folded(k * fundamental, samplerate), samplerate) for k in harmonics
              if k * fundamental > samplerate / 2 and folded(k * fundamental, samplerate) < below_hz]
    return 20 * math.log10(max(levels) / reference)


def cents(frequency, reference):
    return 1200 * math.log2(frequency / reference)


def magnitude_spectrum(signal):
    """|DFT| of `signal` (a power-of-two length), bins 0..n/2: an iterative radix-2 FFT, rectangular window."""
    n = len(signal)
    if n & (n - 1):
        raise ValueError(f"magnitude_spectrum: the length must be a power of two, got {n}")
    values = [complex(value) for value in signal]
    bits = n.bit_length() - 1
    for i in range(n):
        j = int(format(i, f"0{bits}b")[::-1], 2)
        if j > i:
            values[i], values[j] = values[j], values[i]
    size = 2
    while size <= n:
        twiddle_step = cmath.exp(-2j * math.pi / size)
        for start in range(0, n, size):
            twiddle = 1 + 0j
            for k in range(size // 2):
                even, odd = values[start + k], values[start + k + size // 2] * twiddle
                values[start + k], values[start + k + size // 2] = even + odd, even - odd
                twiddle *= twiddle_step
        size *= 2
    return [abs(value) for value in values[:n // 2 + 1]]


def coherent_frequency(frequency, samplerate, length):
    """(bin, frequency): the odd bin nearest `frequency` in a `length`-point DFT and its frequency. A periodic wave
    there fills the window whole (no leakage), and its aliases (odd bin x k, folded at length / 2, a power of two)
    never land on a harmonic's bin."""
    bin_number = round(frequency * length / samplerate)
    if bin_number % 2 == 0:
        bin_number += 1
    return bin_number, bin_number * samplerate / length


def coherent_worst_alias_db(signal, fundamental_bin, samplerate, below_hz):
    """The loudest bin under `below_hz` that is not a harmonic of `fundamental_bin` (a wave at
    `coherent_frequency`), dB re the fundamental: every alias, with no leakage from the harmonics."""
    spectrum = magnitude_spectrum(signal)
    length = len(signal)
    harmonics = set(range(fundamental_bin, length // 2 + 1, fundamental_bin))
    top = int(below_hz * length / samplerate)
    worst = max(spectrum[k] for k in range(1, top) if k not in harmonics)
    return 20 * math.log10(worst / spectrum[fundamental_bin])


def exact_second_order_mean(pieces, x0, x1, x2):
    """Second-order ADAA (Bilbao et al. 2017 eq. (15)) of a piecewise-linear transfer [(from x, slope, intercept)]
    through x0 (newest), x1, x2, in exact rational arithmetic on the pieces: the reference for the kit's GenExpr."""
    exact = [(Fraction(start) if math.isfinite(start) else None, Fraction(slope), Fraction(intercept))
             for start, slope, intercept in pieces]

    def second_integral(x):           # from 0, piece by piece, exactly
        total, first, position = Fraction(0), Fraction(0), Fraction(0)
        while position != x:
            if x > position:
                index = max(i for i, piece in enumerate(exact) if piece[0] is None or piece[0] <= position)
            else:
                index = max(i for i, piece in enumerate(exact) if piece[0] is None or piece[0] < position)
            start, slope, intercept = exact[index]
            end = exact[index + 1][0] if index + 1 < len(exact) else None
            if x > position:
                target = min(x, end) if end is not None else x
            else:
                target = max(x, start) if start is not None else x
            width = target - position
            total += first * width + slope * ((target ** 3 - position ** 3) / 6 - position ** 2 * width / 2) \
                + intercept * width ** 2 / 2
            first += slope * (target ** 2 - position ** 2) / 2 + intercept * width
            position = target
        return total
    x0, x1, x2 = Fraction(x0), Fraction(x1), Fraction(x2)
    differences = [(second_integral(a) - second_integral(b)) / (a - b) for a, b in ((x0, x1), (x1, x2))]
    return float(2 * (differences[0] - differences[1]) / (x0 - x2))


def equalised_second_order_outputs(raw_means):
    """The technique's second-order output from ADAA2's raw means (oldest first): the equaliser's taps over the last
    five, the means before the first taken as 0 (its Histories' start)."""
    from m4l_dev.techniques.antiderivative_piecewise_linear_shaper import SECOND_ORDER_EQUALISER_TAPS
    padded = [0.0] * (len(SECOND_ORDER_EQUALISER_TAPS) - 1) + list(raw_means)
    return [sum(tap * padded[i + k] for k, tap in enumerate(SECOND_ORDER_EQUALISER_TAPS)) for i in range(len(raw_means))]


def second_order_equaliser_remez(edge_cycles_per_sample):
    """(outer tap, inner tap, worst deviation): the symmetric 5-tap equaliser whose product with ADAA2's 3-tap mean
    (1 + 2 cos w) / 3 is 1 at DC and equiripple up to the edge, by the Remez exchange on three extrema."""
    edge = 2 * math.pi * edge_cycles_per_sample

    def mean_response(w):
        return (1 + 2 * math.cos(w)) / 3

    def deviation(outer, inner, w):            # the equaliser, its DC fixed at 3 / 3 = 1 by its middle tap
        return mean_response(w) * (1 + 2 * inner * (math.cos(w) - 1) + 2 * outer * (math.cos(2 * w) - 1)) - 1
    extrema = [0.4 * edge, 0.8 * edge, edge]
    grid = [edge * k / 20000 for k in range(20001)]
    for _ in range(30):
        rows = [[mean_response(w) * 2 * (math.cos(2 * w) - 1), mean_response(w) * 2 * (math.cos(w) - 1), -(-1) ** i,
                 1 - mean_response(w)] for i, w in enumerate(extrema)]
        for i in range(3):                     # Gauss-Jordan on the 3 x 3 system
            pivot = max(range(i, 3), key=lambda r: abs(rows[r][i]))
            rows[i], rows[pivot] = rows[pivot], rows[i]
            for r in range(3):
                if r != i:
                    factor = rows[r][i] / rows[i][i]
                    rows[r] = [a - factor * b for a, b in zip(rows[r], rows[i])]
        outer, inner = rows[0][3] / rows[0][0], rows[1][3] / rows[1][1]
        errors = [deviation(outer, inner, w) for w in grid]
        peaks = [grid[k] for k in range(1, len(grid) - 1)
                 if abs(errors[k]) >= abs(errors[k - 1]) and abs(errors[k]) >= abs(errors[k + 1]) and abs(errors[k]) > 1e-12]
        extrema = sorted(set(peaks + [edge]))[-3:]
    return outer, inner, max(abs(error) for error in errors)
