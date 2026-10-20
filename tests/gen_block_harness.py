"""The harness every gen block test renders through: a gen~ program around blocks, rendered by our GenExpr renderer
(m4l_dev/genexpr.py), and the spectral measures the claims are stated in. Standard library only."""
import math
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
