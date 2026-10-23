"""The harness every gen block test renders through: a gen~ program around blocks, rendered by our GenExpr renderer
(twosl_dsp/genexpr.py), and the spectral measures the claims are stated in. Standard library only."""
import cmath
import math
from fractions import Fraction
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp.gen_blocks import gen_code_with_blocks  # noqa: E402
from twosl_dsp.genexpr import GenProgram, check  # noqa: E402


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


def equalised_adaa_outputs(raw_means, taps):
    """An ADAA block's output from its raw means (oldest first): the equaliser's `taps` (symmetric) over the last of
    them, the means before the first taken as 0 (its Histories' start)."""
    padded = [0.0] * (len(taps) - 1) + list(raw_means)
    return [sum(tap * padded[i + k] for k, tap in enumerate(taps)) for i in range(len(raw_means))]


def fft(values):
    """The DFT of `values` (a power-of-two length), complex, by an iterative radix-2 FFT."""
    n = len(values)
    if n & (n - 1):
        raise ValueError(f"fft: the length must be a power of two, got {n}")
    values = [complex(value) for value in values]
    bits = n.bit_length() - 1
    for i in range(n):
        j = int(format(i, f"0{bits}b")[::-1], 2) if bits else 0
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
    return values


def autocorrelation(signal, lags):
    """The autocorrelation of `signal` at lags 0..lags - 1 (zero-padded, so not circular), normalised to 1 at lag 0."""
    size = 1
    while size < len(signal) + lags:
        size *= 2
    spectrum = fft(list(signal) + [0.0] * (size - len(signal)))
    power = [abs(value) ** 2 for value in spectrum]
    # the inverse DFT of a real, even sequence: the conjugate's forward DFT over n
    correlation = [value.real / size for value in fft(power)[:lags]]
    return [value / correlation[0] for value in correlation]


def group_delay_seconds(signal, frequency, samplerate, step_hz=0.25):
    """The group delay of the impulse response `signal` at `frequency`, from its DFT's phase at frequency +- step_hz
    (the whole signal, rectangular window: the response must have died away inside it)."""
    def dft(at):
        w = 2 * math.pi * at / samplerate
        rotation, phasor, total = cmath.exp(-1j * w), 1 + 0j, 0j
        for value in signal:
            total += value * phasor
            phasor *= rotation
        return total
    return -cmath.phase(dft(frequency + step_hz) / dft(frequency - step_hz)) / (2 * math.pi * 2 * step_hz)


def band_decay_seconds(signal, frequency, samplerate, q=2.0, upper_db=-5.0, lower_db=-25.0):
    """The T60 of `signal` (an impulse response) around `frequency`: through a band-pass (RBJ's, 0 dB peak, `q`), the
    Schroeder energy decay curve's time from `upper_db` to `lower_db`, extrapolated to 60 dB."""
    w = 2 * math.pi * frequency / samplerate
    alpha = math.sin(w) / (2 * q)
    b0, b2, a0, a1, a2 = alpha, -alpha, 1 + alpha, -2 * math.cos(w), 1 - alpha
    x1 = x2 = y1 = y2 = 0.0
    energy = []
    for x in signal:
        y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x, y1, y
        energy.append(y * y)
    remaining, total = [], 0.0
    for value in reversed(energy):
        total += value
        remaining.append(total)
    remaining.reverse()
    levels = [10 * math.log10(value / remaining[0]) if value > 0 else -400.0 for value in remaining]
    upper = next(n for n, level in enumerate(levels) if level <= upper_db)
    lower = next(n for n, level in enumerate(levels) if level <= lower_db)
    return (lower - upper) / samplerate * 60 / (upper_db - lower_db)


def band_levels_db(signal, bands, samplerate, frame=8192):
    """The mean power of `signal` in each (low Hz, high Hz) band, dB re the first band's: Hann-windowed frames of
    `frame` samples, half overlapped, their power spectra summed (Welch's average)."""
    window = [0.5 - 0.5 * math.cos(2 * math.pi * i / (frame - 1)) for i in range(frame)]
    power = [0.0] * (frame // 2 + 1)
    for start in range(0, len(signal) - frame + 1, frame // 2):
        spectrum = magnitude_spectrum([value * weight for value, weight in zip(signal[start:start + frame], window)])
        for k, value in enumerate(spectrum):
            power[k] += value * value
    bin_hz = samplerate / frame
    levels = []
    for low, high in bands:
        bins = range(max(1, int(math.ceil(low / bin_hz))), int(high / bin_hz) + 1)
        levels.append(10 * math.log10(sum(power[k] for k in bins) / len(bins)))
    return [level - levels[0] for level in levels]
