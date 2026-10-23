"""The bucket-brigade echo (a technique): a stereo echo whose delay is a fixed number of bucket-brigade stages run at a
clock, with the anti-aliasing and reconstruction filters, the compander and the chip's noise and distortion of a BBD
echo circuit, a drop-in for the tape-style echo (references/dsp.md, "Bucket-brigade echo").

A technique, not a circuit module: it models no one unit. Its BBD is Holters & Parker's combined model (DAFx-18), its
filters the typical echo circuit's Sallen-Key filters and its compander the NE570 / 571 law from Raffel & Smith
(DAFx-10), the stage count a constructor number (two 4096-stage chips in series, as the Memory Man's MN3005 pair,
`TWO_CHIP_STAGES`). A modelled Memory Man (its own filters, its feedback point, its clock) would be a circuit module;
neither is in any source we have (references/dsp.md).

What it promises (tests/test_techniques.py checks each):
- **A BBD.** `stages` buckets clocked by two antiphase clocks: the input is sampled on every even edge and comes out
  on the odd edge N - 1 edges later, held for a clock period, so the delay is N / (2 f_clock) and the hold's
  sinc is in the sound (HP18 eq. 1). The clock is the delay's: f_clock = (N / 2 + the filters' own periods) / the
  time left after the loop's other delays. Longer times clock slower.
- **Holters & Parker's resampling.** The host-rate audio reaches the clock-rate buckets through the anti-aliasing
  filter itself, and the buckets reach the host rate through the reconstruction filter: each filter in partial
  fractions, evaluated at the clock's edges exactly (HP18 §3, Algorithm 1). The input side treats the host samples
  as a straight line between them (first-order hold, worked here: HP18's impulse train gains up to +8 dB in the pass
  band when the clock is fast, see references/dsp.md); the output side is HP18's step-invariant form. So the BBD
  aliases where its clock is slow (content above f_clock / 2 folds), images where its hold does, and a clock that
  moves pitch-shifts what is in the buckets, as the chips do. At most MAXIMUM_EDGES_PER_SAMPLE edges a host sample.
- **The band follows the clock.** The filters are Raffel & Smith's typical echo circuit (a third-order anti-aliasing
  filter; a third-order reconstruction filter and a second-order "corner correction", RS10 §2.2, R = 10 k), set for
  RS10's own 4096-stage, 300 ms example clock (6826.7 Hz: its anti-aliasing filter's -3 dB, 3.23 kHz, sits under that
  clock's Nyquist, RS10 §4.2's "worst-case" design). A fixed circuit's filters stay put while its clock moves over a
  short range; this echo's Time moves the clock over tens of times that, so its filters are the circuit's scaled
  to the clock of the set (glided) Time, as if a unit were built for each Time. The clock's wobble (wow, flutter) and
  nothing else moves under fixed filters. At 1 s the clock is 4.1 kHz, its Nyquist 2.05 kHz, and the band is -3 dB
  at 1.61 kHz (2sl dub SPEC §3.4: "near 2 kHz").
- **The compander.** A feedback 2:1 compressor before the anti-aliasing filter and a feed-forward 1:2 expander after
  the reconstruction filter, outside the filters (RS10 §1.3, §3.4: f(x) = x / avg(|f(x)|), f(x) = avg(|x|) x; inside
  them with `compander_inside_filters`, below), each averaging a full-wave rectified signal over COMPANDER_TIME_MS
  (RS10 §3.3: 10 kOhm x 0.22-1 uF). Unity at the BBD's full level; the compressor solved with no unit delay. Its
  breathing is the expander's gain following its averager: the noise floor rises with the signal and falls after it.
- **The chips' own faults.** A noise floor NOISE_DB under a full-level sine at the buckets' output (RS10 §3.1, §4.3:
  "about 60 dB"), shaped by the hold and the reconstruction filter, so it darkens with the clock; RS10's
  third-order distortion (§4.5) scaled so a full-level sine has RS10's THD for N stages, 1.01^(N / 1024) - 1 (§4.4),
  clipping at the full level; the frequency-dependent insertion gain, INSERTION_GAIN_AT_NYQUIST_DB at the clock's
  Nyquist (§4.2), as a two-tap filter on the buckets; the clock's leakage, a square wave at f_clock of
  CLOCK_LEAKAGE_DB through the reconstruction filter (Morrin: an audible whine at slow clocks; its level UNVERIFIED);
  a DC coupling high-pass, COUPLING_HIGH_PASS_HZ, after the reconstruction filter (HP18 §4: the circuit's first-order
  high-passes "for adjusting bias voltages").
- **On the grid.** Every repeat lands at n T: the loop's own delays (the filters' and the insertion filter's group
  delay where the loop's gain is highest, where the repeats converge, in clock periods; the loop's tone filters, the
  sample the loop waits, the sample the BBDs' input waits and what the device puts in the loop, in host samples) are
  taken out of the buckets' time (a low sound's first repeat is 2.7 clock periods early: 0.66 ms at 1 s), and what
  is heard is read from a short line that adds back what the loop has and the first pass hasn't (the tone filters
  and a sample). The right side reads `right_lag_ms` later (stereo), as the tape echo.
- **Glide.** The time starts at its target on the first sample, then glides as the tape echo's does (its constants),
  so the clock's speed ratio over the buckets stays in [0.5, 1.5]: what comes out is never played backwards (a BBD
  can't: its clock only runs forwards).
- **Howl.** `feedback` is the loop's highest gain for a steady tone (`PEAK_LOOP_GAIN`, computed at build: the
  filters' presence peak, +8.3 dB a pass at 0.28 of the clock, doubled in dB by the compander, which expands the level
  the filters made), so over 1 the loop grows at its peak and holds where the buckets clip, their full level set
  (`howl_full_level`) so a howl at the peak comes out near 1 / `saturation_gain`, as the tape echo's |loop| <=
  1 / saturation_gain (measured: 0.69 at saturation 2, the clipped tone's harmonics on top); under 1 it dies. The
  compander's unity point is that full level. The noise starts it with no input (RS10 §4.3). The price: a sound whose
  level is mostly low (where the filters are flat) comes round at about feedback / PEAK_LOOP_GAIN a pass, -16.6 dB at
  feedback 1, much faster than the tape echo's repeats.
- **Wow and flutter as the clock's wobble.** `wow_cents` is the RMS of the clock's slow wobble (the tape echo's
  WOW_HZ noise), `flutter_cents` of its FLUTTER_HZ sine. What is heard is the clock now against the clock when the
  sound went in, so a slow wobble is heard less at short times than on tape.
- **Stop.** On `stop_pressed`, the repeats fade over the tape echo's STOP_FADE_MS and nothing from before is heard
  again: the buckets from before are emptied as they come out, the filters and averagers reset, the loop cut until
  then. The anti-aliasing filter restarts at Stop (what was in it was the loop's).
- **Rounds** (for a display) and the level meter, as the tape echo's.

Options (as the tape echo's): `stereo_mode` (0 stereo, 1 ping-pong, 2 wide, 3 mono: the tape echo's
`STEREO_MODES`), and `loop_insert=True` with `insert_delay_samples` and a `BucketBrigadeEchoWriter` (the device's own
processing in the loop: the echo leaves what goes into each BBD in `<name>_left_into_tape`, `<name>_right_into_tape`,
and the writer's marker, after the device's processing, gives the BBDs what the device made of it, which they take
on the next sample: the sample counted in the loop's delay). No diffusion and no clean loop:
the BBD's clip is its saturation.

`compander_inside_filters=True` (left out: False, the code as without it): the other circuit RS10 §1.3 gives ("most"
put the compander outside the filters, so some don't): the compressor after the anti-aliasing filter, on its samples
at each even edge, and the expander on the buckets' output at each odd edge, before the reconstruction filter (the
coupling high-pass moves with it, before the expander, at the clock). Both averagers are COMPANDER_TIME_MS one-poles,
now at the clock, and a full-wave average of the held output is the average of its samples, so they work as outside.
For a steady tone only the chip is between the compander's halves: the filters and the hold count once, the chip's
insertion gain twice: the loop's steady-tone gain is |chain| |insertion| (`inside_loop_gain`), its peak +6.2 dB a pass
at 0.267 of the clock (`INSIDE_PEAK_LOOP_GAIN`, `INSIDE_PEAK_CLOCK_FRACTION`) against +16.6 dB at 0.28 outside: the
filters' lift no more doubled (and the insertion loss at the peak, -2 dB, doubled instead), so a sound whose level
is mostly low comes round at about feedback / 2.04 a pass, not / 6.79. Everything above holds as it is, from its own
peak: feedback 1 is the howl (`INSIDE_PEAK_LOOP_GAIN`), the host's straight line given back once, not doubled (it is
before the compressor now), the howl's full level (1 - a - b)^2 i^2 h F = 1 (i the insertion gain, h the hold and the
reconstruction filter), the grid from the chain's group delay at that peak (`INSIDE_CHAIN_PERIODS`, 3.7 periods),
Stop, the stereo modes and the loop insert. The noise is still inside the compander (it breathes). The clock's
leakage, outside the expander's detector in this model, is scaled by the expander's gain (DESIGN: the leak is a
square at the clock the edges don't carry; it comes after the expander in the circuit, its level UNVERIFIED anyway).

Outputs: `<name>_left`, `<name>_right` (the repeats), `<name>_level`, `<name>_round_peak_so_far`,
`<name>_round_peak_1` .. `_<rounds_kept>`, `<name>_loop_samples` (T), `<name>_left_clock_hz`,
`<name>_right_clock_hz` (the chips' clocks, wobble included); `<name>_left_u` (what reaches the anti-aliasing filter:
the compressor's output outside the filters, the input inside; for a test).
"""
import cmath
import math

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique
from twosl_dsp.generated_numbers import generated_number
from twosl_dsp.techniques.histories_start_at_their_targets import HistoriesStartAtTheirTargets
from twosl_dsp.techniques.tape_style_echo import (FLUTTER_HZ, HIGHEST_FLUTTER_CENTS, HIGHEST_SAMPLE_RATE,
                                                HIGHEST_TIME_CHANGE, HIGHEST_WOW_CENTS, LEVEL_METER_FALL_MS,
                                                STEREO_MODE_GLIDE_MS, STOP_FADE_MS, TIME_GLIDE_DOWN_MS,
                                                TIME_GLIDE_UP_MS, WIDE_RIGHT_RATIO, WOW_HZ)

# Two 4096-stage chips in series (the MN3005's stages, RS10 footnote 1; the Memory Man's MN3005 pair, Morrin's
# calibration notes in 2sl dub references/echoes.md §2.2).
TWO_CHIP_STAGES = 8192
HIGHEST_STAGES = 65536                   # a Data's size is a literal; far over any chain of chips

# Raffel & Smith's typical echo circuit (RS10 §2.2): every R 10 kOhm; the anti-aliasing third-order Sallen-Key
# (C1 to ground, C2 to the follower's output, C3 to ground), the reconstruction third-order the same, then the
# second-order "corner correction" (C1 to the output, C2 to ground).
FILTER_RESISTANCE_OHMS = 10e3
ANTI_ALIASING_FARADS = (0.0068e-6, 0.082e-6, 0.00033e-6)
RECONSTRUCTION_THIRD_ORDER_FARADS = (0.0022e-6, 0.033e-6, 0.001e-6)
RECONSTRUCTION_SECOND_ORDER_FARADS = (0.039e-6, 0.00033e-6)
# The clock those filters are the worst case for: RS10's own example, 4096 stages at 300 ms (§2.1).
DESIGN_CLOCK_HZ = 4096 / (2 * 0.300)

COMPANDER_TIME_MS = 10.0                 # 10 kOhm x 1 uF, the top of RS10's 0.22-1 uF (the smoothest average)
NOISE_DB = -60.0                         # under a full-level sine's RMS, at the buckets (RS10 §3.1, §4.3)
INSERTION_GAIN_AT_NYQUIST_DB = -5.0      # RS10 §4.2: 0..2 dB at low frequencies, -4..-6 dB at the Nyquist limit;
                                         # 0 dB low (the circuit's level trims) and the middle of the fall
CLOCK_LEAKAGE_DB = -30.0                 # the clock's square at the buckets' output, re the full level: UNVERIFIED
COUPLING_HIGH_PASS_HZ = 10.0             # DESIGN: HP18 names the high-passes, not their corners
RS10_POLYNOMIAL = (1 / 8, 1 / 18)        # f(x) = x - a x^2 - b x^3 (RS10 §4.5, fitted to a measured BBD)
MAXIMUM_EDGES_PER_SAMPLE = 16            # the clock is held under 8 x the host rate (a delay of N / (16 fs))
WOBBLE_LIMIT_CENTS = 300.0               # the clock's wobble is clamped here (40 cents of wow is > 6 sigma under it)
HEARD_LIMIT_MS = 50.0                    # the heard line's reach past the right side's lag (the loop's own delays)
NATURAL_LOG_OF_2 = math.log(2.0)


def polynomial_roots(coefficients):
    """The roots of a polynomial (coefficients highest power first), by Durand-Kerner iteration."""
    leading = coefficients[0]
    monic = [c / leading for c in coefficients]
    degree = len(monic) - 1
    roots = [complex(0.4, 0.9) ** k for k in range(degree)]
    for _ in range(500):
        updated = []
        for i, root in enumerate(roots):
            value = sum(c * root ** (degree - k) for k, c in enumerate(monic))
            others = 1
            for j, other in enumerate(roots):
                if j != i:
                    others *= root - other
            updated.append(root - value / others)
        roots = updated
    return roots


def polynomial_product(first, second):
    product = [0.0] * (len(first) + len(second) - 1)
    for i, a in enumerate(first):
        for j, b in enumerate(second):
            product[i + j] += a * b
    return product


def third_order_denominator(farads):
    """1 + (t1 + 3 t3) s + 2 t3 (t1 + t2) s^2 + t1 t2 t3 s^3 (highest first), t = R C: the nodal equations of RS10's
    figure 4 with C2 to the follower's output (RS10 prints a2 = 2 / (R C1) + 2 / (R C2), as here; its a1 reads
    1 / (R^2 C1 C2) + 1 / (R^2 C2 C3) in the PDF, where the circuit gives 3 / (R^2 C1 C2) + 1 / (R^2 C2 C3))."""
    t1, t2, t3 = (FILTER_RESISTANCE_OHMS * c for c in farads)
    return [t1 * t2 * t3, 2 * t3 * (t1 + t2), t1 + 3 * t3, 1.0]


def second_order_denominator(farads):
    """1 + 2 t2 s + t1 t2 s^2 (RS10 §2.2's unity-gain Sallen-Key, C1 to the output)."""
    t1, t2 = (FILTER_RESISTANCE_OHMS * c for c in farads)
    return [t1 * t2, 2 * t2, 1.0]


ANTI_ALIASING_DENOMINATOR = third_order_denominator(ANTI_ALIASING_FARADS)
RECONSTRUCTION_DENOMINATOR = polynomial_product(third_order_denominator(RECONSTRUCTION_THIRD_ORDER_FARADS),
                                                second_order_denominator(RECONSTRUCTION_SECOND_ORDER_FARADS))


def response(denominator, frequency_hz, scale=1.0):
    """1 / D(s) at `frequency_hz`, the filter's frequencies multiplied by `scale`."""
    s = 2j * math.pi * frequency_hz / scale
    return 1 / sum(c * s ** (len(denominator) - 1 - k) for k, c in enumerate(denominator))


def partial_fractions(denominator):
    """[(pole / DESIGN_CLOCK_HZ, residue / pole, weight)]: 1 / D(s) = sum r / (s - p), D(0) = 1. A complex pair is
    kept once, its positive-imaginary pole, weight 2 (the pair's sum is twice the real part); a real pole weight 1."""
    poles = polynomial_roots(denominator)
    derivative = [c * (len(denominator) - 1 - k) for k, c in enumerate(denominator[:-1])]
    terms = []
    for pole in poles:
        if pole.imag < -1e-9 * abs(pole):
            continue
        residue = 1 / sum(c * pole ** (len(derivative) - 1 - k) for k, c in enumerate(derivative))
        real = abs(pole.imag) <= 1e-9 * abs(pole)
        pole = complex(pole.real, 0.0) if real else pole
        ratio = residue / pole
        ratio = complex(ratio.real, 0.0) if real else ratio
        per_clock = pole / DESIGN_CLOCK_HZ
        terms.append((complex(generated_number(per_clock.real), generated_number(per_clock.imag)),
                      complex(generated_number(ratio.real), generated_number(ratio.imag)), 1 if real else 2))
    return sorted(terms, key=lambda term: (term[2], term[0].imag))


ANTI_ALIASING_POLES = partial_fractions(ANTI_ALIASING_DENOMINATOR)
RECONSTRUCTION_POLES = partial_fractions(RECONSTRUCTION_DENOMINATOR)

# The insertion gain as a two-tap filter on the buckets, c + d z^-1: c + d = 1 at DC, c - d at the clock's Nyquist.
_NYQUIST_GAIN = 10 ** (INSERTION_GAIN_AT_NYQUIST_DB / 20)
INSERTION_TAPS = (generated_number((1 + _NYQUIST_GAIN) / 2), generated_number((1 - _NYQUIST_GAIN) / 2))


def insertion_response(clock_fraction):
    """The insertion filter at `clock_fraction` x the clock (a frequency over the clock rate)."""
    return INSERTION_TAPS[0] + INSERTION_TAPS[1] * cmath.exp(-2j * math.pi * clock_fraction)


def hold_response(clock_fraction):
    """The output's one-period hold, sinc(f / f_clock) (HP18 eq. 34), its delay counted with the buckets'."""
    x = math.pi * clock_fraction
    return 1.0 if x == 0 else math.sin(x) / x


def chain_response(clock_fraction):
    """The BBD path's small-signal response (filters, hold, insertion gain; not the buckets' delay) at a frequency
    `clock_fraction` x the clock, at any clock (every part of it scales with the clock)."""
    frequency = clock_fraction * DESIGN_CLOCK_HZ
    return (response(ANTI_ALIASING_DENOMINATOR, frequency) * response(RECONSTRUCTION_DENOMINATOR, frequency)
            * hold_response(clock_fraction) * insertion_response(clock_fraction))


# The loop's highest gain for a steady tone (below the clock's Nyquist): the circuit's presence peak, squared. The
# compander sits outside the filters (RS10 §1.3), so for a steady tone the expander's averager sees the level the
# filters made and expands it again: the tone comes out at |chain|^2 (a broadband sound, whose level is mostly where
# the chain is flat, at about |chain|). A howl is a steady tone: this is where it starts.
PEAK_CLOCK_FRACTION = generated_number(max(range(1, 10000), key=lambda k: abs(chain_response(k / 20000))) / 20000)
PEAK_LOOP_GAIN = generated_number(abs(chain_response(PEAK_CLOCK_FRACTION)) ** 2)


def chain_group_delay_periods(clock_fraction, step=1e-6):
    """The chain's group delay (filters and insertion filter; the hold's is the buckets'), in clock periods."""
    later, earlier = (cmath.phase(chain_response(clock_fraction + side * step)) for side in (1, -1))
    return -(later - earlier) / (2 * step) / (2 * math.pi)


# The filters' and the insertion filter's group delay where the loop's gain is highest, in clock periods: the repeats
# that last converge there (3.8 periods; 1.15 at DC, so a low sound's first repeat is 2.7 periods early: 0.33 ms at
# 500 ms, 0.66 ms at 1 s).
CHAIN_PERIODS = generated_number(chain_group_delay_periods(PEAK_CLOCK_FRACTION))


def inside_loop_gain(clock_fraction):
    """The loop's steady-tone gain with the compander inside the filters (`compander_inside_filters=True`): the
    compressor after the anti-aliasing filter, the expander before the reconstruction filter, so only the chip (its
    insertion gain) is between them and is expanded again; the filters and the hold count once. |chain| |insertion|."""
    return abs(chain_response(clock_fraction)) * abs(insertion_response(clock_fraction))


# The same three numbers with the compander inside the filters: the peak +6.2 dB a pass at 0.267 of the clock (the
# filters' +8.2 dB there once, the chip's insertion loss twice), its group delay 3.7 periods.
INSIDE_PEAK_CLOCK_FRACTION = generated_number(max(range(1, 10000), key=lambda k: inside_loop_gain(k / 20000)) / 20000)
INSIDE_PEAK_LOOP_GAIN = generated_number(inside_loop_gain(INSIDE_PEAK_CLOCK_FRACTION))
INSIDE_CHAIN_PERIODS = generated_number(chain_group_delay_periods(INSIDE_PEAK_CLOCK_FRACTION))
# The clock's leakage through the reconstruction filter at the clock: a constant, the filter scaling with the clock.
_LEAK_AT_CLOCK = response(RECONSTRUCTION_DENOMINATOR, DESIGN_CLOCK_HZ)
LEAK_GAIN = generated_number(10 ** (CLOCK_LEAKAGE_DB / 20) * 4 / math.pi * abs(_LEAK_AT_CLOCK))
LEAK_PHASE = generated_number(cmath.phase(_LEAK_AT_CLOCK))


def howl_full_level(distortion, compander_inside_filters=False):
    """The buckets' full level for a howl held at 1 (x 1 / saturation_gain): a howl is a tone at the loop's peak,
    clipped at the buckets to the curve's top (1 - a - b of the full level F), through the reconstruction side's gain
    there g, and expanded (an amplitude A comes out as A^2 / F): (1 - a - b)^2 g^2 F = 1. With the compander inside
    the filters only the insertion gain i is expanded, the hold and the reconstruction filter h after the expander:
    (1 - a - b)^2 i^2 h F = 1."""
    a, b = distortion
    if compander_inside_filters:
        fraction = INSIDE_PEAK_CLOCK_FRACTION
        insertion = abs(insertion_response(fraction))
        after = abs(response(RECONSTRUCTION_DENOMINATOR, fraction * DESIGN_CLOCK_HZ)) * hold_response(fraction)
        return generated_number(1 / ((1 - a - b) ** 2 * insertion ** 2 * after))
    reconstruction_gain = abs(chain_response(PEAK_CLOCK_FRACTION)
                              / response(ANTI_ALIASING_DENOMINATOR, PEAK_CLOCK_FRACTION * DESIGN_CLOCK_HZ))
    return generated_number(1 / ((1 - a - b) ** 2 * reconstruction_gain ** 2))


def total_harmonic_distortion(a, b):
    """THD of x - a x^2 - b x^3 for a unit sine: harmonics a / 2 and b / 4 against the fundamental 1 - 3 b / 4."""
    return math.hypot(a / 2, b / 4) / (1 - 3 * b / 4)


def distortion_polynomial(stages):
    """RS10's (a, b) scaled so a full-level sine's THD is 1.01^(N / 1024) - 1 (RS10 §4.4)."""
    target = 1.01 ** (stages / 1024) - 1
    low, high = 0.0, 2.0
    for _ in range(200):
        middle = (low + high) / 2
        if total_harmonic_distortion(middle * RS10_POLYNOMIAL[0], middle * RS10_POLYNOMIAL[1]) < target:
            low = middle
        else:
            high = middle
    scale = (low + high) / 2
    a, b = scale * RS10_POLYNOMIAL[0], scale * RS10_POLYNOMIAL[1]
    if 1 - 2 * a - 3 * b <= 0:
        raise BuildError(f"BucketBrigadeEcho: {stages} stages distort past a rising curve (THD {target:.3f})")
    return generated_number(a), generated_number(b)


def complex_product(name, first, second):
    """GenExpr lines: `name`_re, `name`_im = first x second (each a (re, im) pair of expressions)."""
    (a, b), (c, d) = ([f"({part})" if " " in part else part for part in pair] for pair in (first, second))
    return f"{name}_re = {a} * {c} - {b} * {d};\n{name}_im = {a} * {d} + {b} * {c};"


class BucketBrigadeEcho(Technique):
    """See the module docstring. Inputs are GenExpr expressions; `stages`, `longest_time_ms`, `right_lag_ms` and
    `rounds_kept` are numbers."""

    def __init__(self, instance_name, *, left_input, right_input, time_ms, feedback, loop_lowpass_hz,
                 loop_highpass_hz, saturation_gain, wow_cents, flutter_cents, stop_pressed, stages, longest_time_ms,
                 right_lag_ms, rounds_kept, stereo_mode=None, loop_insert=False, insert_delay_samples=None,
                 compander_inside_filters=False):
        inputs = dict(left_input=left_input, right_input=right_input, time_ms=time_ms, feedback=feedback,
                      loop_lowpass_hz=loop_lowpass_hz, loop_highpass_hz=loop_highpass_hz,
                      saturation_gain=saturation_gain, wow_cents=wow_cents, flutter_cents=flutter_cents,
                      stop_pressed=stop_pressed)
        if loop_insert != (insert_delay_samples is not None):
            raise BuildError(f"BucketBrigadeEcho {instance_name}: insert_delay_samples is given exactly with "
                             "loop_insert")
        for name, expression in (("stereo_mode", stereo_mode), ("insert_delay_samples", insert_delay_samples)):
            if expression is not None:
                inputs[name] = expression
        super().__init__(instance_name, **inputs)
        self.latency_samples = 0       # its repeats land at n T: the loop's own delays are taken out of the time
        if int(stages) != stages or stages < 2 or stages % 2 or stages > HIGHEST_STAGES:
            raise BuildError(f"BucketBrigadeEcho {instance_name}: stages {stages} must be an even whole number in "
                             f"2..{HIGHEST_STAGES} (a sample goes in on every second edge)")
        if not longest_time_ms > 0:
            raise BuildError(f"BucketBrigadeEcho {instance_name}: longest time {longest_time_ms} ms must be > 0")
        if right_lag_ms < 0 or rounds_kept < 0 or int(rounds_kept) != rounds_kept:
            raise BuildError(f"BucketBrigadeEcho {instance_name}: right_lag_ms must be >= 0, rounds_kept a whole "
                             "number >= 0")
        self.stages = int(stages)
        self.buckets = self.stages // 2          # samples in the chain: one in on every second edge
        self.compander_inside = bool(compander_inside_filters)
        if self.compander_inside:
            self.peak_clock_fraction, self.peak_loop_gain = INSIDE_PEAK_CLOCK_FRACTION, INSIDE_PEAK_LOOP_GAIN
            chain_periods = INSIDE_CHAIN_PERIODS
        else:
            self.peak_clock_fraction, self.peak_loop_gain = PEAK_CLOCK_FRACTION, PEAK_LOOP_GAIN
            chain_periods = CHAIN_PERIODS
        self.chain_periods = generated_number(self.buckets + chain_periods)   # the clock periods a pass takes
        self.distortion = distortion_polynomial(self.stages)
        self.full_level = howl_full_level(self.distortion, self.compander_inside)
        self.longest_time_ms = float(longest_time_ms)
        self.right_lag_ms = generated_number(float(right_lag_ms))
        self.rounds_kept = int(rounds_kept)
        self.has_stereo_mode = stereo_mode is not None
        self.loop_insert = bool(loop_insert)
        self.heard_samples = int(math.ceil(HIGHEST_SAMPLE_RATE * (self.right_lag_ms + HEARD_LIMIT_MS) / 1000.0)) + 8
        self.time_starts_at_its_target = HistoriesStartAtTheirTargets(f"{instance_name}_time_start",
                                                                      targets={f"{instance_name}_time_ms": time_ms})

    def side_histories(self, side):
        names = [f"{side}_into_bbd", f"{side}_u_previous", f"{side}_held", f"{side}_bucket_previous",
                 f"{side}_edge_time", f"{side}_odd_edge_next", f"{side}_enqueued", f"{side}_compressor_level",
                 f"{side}_expander_level", f"{side}_coupling", f"{side}_lowpass_1", f"{side}_lowpass_2",
                 f"{side}_highpass", f"{side}_z_previous"]
        for kind, poles in (("in", ANTI_ALIASING_POLES), ("out", RECONSTRUCTION_POLES)):
            for number, (_, _, weight) in enumerate(poles):
                names.append(f"{side}_{kind}_{number}_re")
                if weight == 2:
                    names.append(f"{side}_{kind}_{number}_im")
        return names

    def declarations(self):
        lines = [self.substituted(f"Data ${{p}}_{side}_buckets(${{size}});", size=str(self.buckets))
                 for side in ("left", "right")]
        lines += [self.substituted(f"Delay ${{p}}_{side}_heard(${{size}});", size=str(self.heard_samples))
                  for side in ("left", "right")]
        histories = ["${p}_time_ms(0)", "${p}_wow_1(0)", "${p}_wow_2(0)", "${p}_flutter_phase(0)",
                     "${p}_since_stop(1e9)", "${p}_stop_fade(0)", "${p}_left_stop_index(-1e9)",
                     "${p}_right_stop_index(-1e9)", "${p}_reset_done(1)",
                     "${p}_level(0)", "${p}_round_elapsed(0)", "${p}_round_peak_so_far(0)"]
        if self.has_stereo_mode:
            histories += ["${p}_cross(0)", "${p}_wide(0)", "${p}_mono(0)"]
        histories += [f"${{p}}_round_peak_{n}(0)" for n in range(1, self.rounds_kept + 1)]
        for side in ("left", "right"):
            # the first edge is an even one (a sample in), a period from the start
            histories += [f"${{p}}_{name}({'1' if name.endswith('_edge_time') else '0'})"
                          for name in self.side_histories(side)]
        lines.append(self.substituted("History " + ", ".join(histories) + ";"))
        lines.append(self.time_starts_at_its_target.declarations())
        return "\n".join(lines)

    def chain_code(self, side):
        """One side's BBD chain for this sample: the compressor, the clock's edges (the anti-aliasing filter sampled
        at each even edge into the buckets, each odd edge's step into the reconstruction filter), the reconstruction
        filter's output, the coupling high-pass, the expander, the heard line. Leaves `<p>_<side>_z`."""
        p = self.instance_name
        s = f"{p}_{side}"
        a, b = self.distortion
        c0, c1 = INSERTION_TAPS
        if self.compander_inside:
            lines = [f"""
// {side}: the compander is inside the filters, at the clock's edges: the compressor on the anti-aliasing filter's
// samples, the expander on the buckets' output before the reconstruction filter; its averagers' poles and the
// coupling high-pass's are a clock period's
{s}_x = {p}_stop_now ? 0 : {s}_into_bbd;
{s}_u = {s}_x;
{s}_edge_compander_pole = smoothing_coefficient({COMPANDER_TIME_MS!r}, {s}_clock_hz);
{s}_edge_coupling_pole = 1 - exp(-twopi * {COUPLING_HIGH_PASS_HZ!r} / {s}_clock_hz);
if ({p}_stop_now) {{"""]
        else:
            lines = [f"""
// {side}: the compressor (2:1, feedback, solved with this sample's own level: the level a is the root of
// a^2 - (1 - k) a_before a - k |x| ref = 0, the output x ref / a)
{s}_x = {p}_stop_now ? 0 : {s}_into_bbd;
{s}_held_level = (1 - {p}_compander_pole) * {s}_compressor_level;
{s}_compressor_level = 0.5 * ({s}_held_level + sqrt({s}_held_level * {s}_held_level + 4 * {p}_compander_pole * abs({s}_x) * {p}_reference));
{s}_u = {s}_compressor_level > 0 ? {s}_x * {p}_reference / {s}_compressor_level : 0;
if ({p}_stop_now) {{"""]
        # Stop: the anti-aliasing filter held the loop's sound: it starts again
        for number, (_, _, weight) in enumerate(ANTI_ALIASING_POLES):
            lines.append(f"\t{s}_in_{number}_re = 0;")
            if weight == 2:
                lines.append(f"\t{s}_in_{number}_im = 0;")
        lines.append(f"""\t{s}_u_previous = {s}_u;
}}
// the filters at this clock: each pole a = p T, its step q = e^a, and 1 / a (the input's straight line)""")
        for kind, poles in (("in", ANTI_ALIASING_POLES), ("out", RECONSTRUCTION_POLES)):
            for number, (pole, _, weight) in enumerate(poles):
                name = f"{s}_{kind}_{number}"
                if weight == 1:
                    lines.append(f"{name}_a = {pole.real!r} * {s}_filter_clock / samplerate;\n"
                                 f"{name}_step = exp({name}_a);")
                    if kind == "in":
                        lines.append(f"{name}_inverse = 1 / {name}_a;")
                else:
                    lines.append(f"{name}_a_re = {pole.real!r} * {s}_filter_clock / samplerate;\n"
                                 f"{name}_a_im = {pole.imag!r} * {s}_filter_clock / samplerate;\n"
                                 f"{name}_magnitude = exp({name}_a_re);\n"
                                 f"{name}_step_re = {name}_magnitude * cos({name}_a_im);\n"
                                 f"{name}_step_im = {name}_magnitude * sin({name}_a_im);")
                    if kind == "in":
                        lines.append(f"{name}_norm = {name}_a_re * {name}_a_re + {name}_a_im * {name}_a_im;\n"
                                     f"{name}_inverse_re = {name}_a_re / {name}_norm;\n"
                                     f"{name}_inverse_im = -{name}_a_im / {name}_norm;")
        # the edges
        sample_in = [f"{s}_v = 0;"]
        for number, (pole, ratio, weight) in enumerate(ANTI_ALIASING_POLES):
            name = f"{s}_in_{number}"
            if weight == 1:
                # S(d) = q S + rho (u0 (q - 1) + (u1 - u0) ((q - 1) / a - d)), q = e^(a d)
                sample_in.append(f"""{name}_q = exp({name}_a * {s}_d);
{s}_v = {s}_v + {name}_q * {name}_re + {ratio.real!r} * ({s}_u_previous * ({name}_q - 1) + {s}_u_slope * (({name}_q - 1) * {name}_inverse - {s}_d));""")
            else:
                sample_in.append(f"""{name}_q_magnitude = exp({name}_a_re * {s}_d);
{name}_q_re = {name}_q_magnitude * cos({name}_a_im * {s}_d);
{name}_q_im = {name}_q_magnitude * sin({name}_a_im * {s}_d);
{complex_product(f"{name}_qs", (f"{name}_q_re", f"{name}_q_im"), (f"{name}_re", f"{name}_im"))}
{complex_product(f"{name}_qa", (f"{name}_q_re - 1", f"{name}_q_im"), (f"{name}_inverse_re", f"{name}_inverse_im"))}
{name}_drive_re = {s}_u_previous * ({name}_q_re - 1) + {s}_u_slope * ({name}_qa_re - {s}_d);
{name}_drive_im = {s}_u_previous * {name}_q_im + {s}_u_slope * {name}_qa_im;
{s}_v = {s}_v + 2 * ({name}_qs_re + {ratio.real!r} * {name}_drive_re - {ratio.imag!r} * {name}_drive_im);""")
        step_out = []
        for number, (pole, ratio, weight) in enumerate(RECONSTRUCTION_POLES):
            name = f"{s}_out_{number}"
            # the step at d reaches the end of the sample as rho e^(a (1 - d)) delta (HP18 eq. 21)
            if weight == 1:
                step_out.append(f"{name}_re = {name}_re + {ratio.real!r} * exp({name}_a * (1 - {s}_d)) * {s}_delta;")
            else:
                step_out.append(f"""{name}_e_magnitude = exp({name}_a_re * (1 - {s}_d)) * {s}_delta;
{name}_e_re = {name}_e_magnitude * cos({name}_a_im * (1 - {s}_d));
{name}_e_im = {name}_e_magnitude * sin({name}_a_im * (1 - {s}_d));
{name}_re = {name}_re + {ratio.real!r} * {name}_e_re - {ratio.imag!r} * {name}_e_im;
{name}_im = {name}_im + {ratio.real!r} * {name}_e_im + {ratio.imag!r} * {name}_e_re;""")
        indent = lambda text, tabs: text.replace("\n", "\n" + "\t" * tabs)  # noqa: E731
        compress_at_edge, expand_at_edge = [], ""
        if self.compander_inside:
            compress_at_edge = [f"""// the compressor (2:1, feedback, solved with this edge's own level, as outside the filters)
{s}_held_level = (1 - {s}_edge_compander_pole) * {s}_compressor_level;
{s}_compressor_level = 0.5 * ({s}_held_level + sqrt({s}_held_level * {s}_held_level + 4 * {s}_edge_compander_pole * abs({s}_v) * {p}_reference));
{s}_v = {s}_compressor_level > 0 ? {s}_v * {p}_reference / {s}_compressor_level : 0;"""]
            expand_at_edge = f"""
// the coupling high-pass, then the expander (1:2, feed-forward on its own input), before the reconstruction filter
{s}_coupling = {s}_coupling + {s}_edge_coupling_pole * ({s}_out - {s}_coupling);
{s}_coupled = {s}_out - {s}_coupling;
{s}_expander_level = {s}_expander_level + {s}_edge_compander_pole * (abs({s}_coupled) - {s}_expander_level);
{s}_out = {s}_coupled * {s}_expander_level / {p}_reference;"""
        lines.append(f"""
// the clock's edges in this sample (HP18 Algorithm 1), at {s}_edge_time samples after the last one: an even edge
// samples the anti-aliasing filter into the buckets, an odd edge puts the oldest out, held to the next odd edge
{s}_edge_step = samplerate / (2 * {s}_clock_hz);
{s}_u_slope = {s}_u - {s}_u_previous;
for ({s}_edge = 0; {s}_edge < {MAXIMUM_EDGES_PER_SAMPLE}; {s}_edge += 1) {{
	if ({s}_edge_time > 1) {{
		break;
	}}
	{s}_d = {s}_edge_time;
	if ({s}_odd_edge_next < 0.5) {{
		{indent(chr(10).join(sample_in + compress_at_edge), 2)}
		// the chip's distortion (RS10 §4.5, scaled for {self.stages} stages), clipped at the full level
		{s}_w = clamp({s}_v / {p}_full_level, -1, 1);
		poke({s}_buckets, {p}_full_level * ({s}_w - {a!r} * {s}_w * {s}_w - {b!r} * {s}_w * {s}_w * {s}_w), {s}_enqueued % {self.buckets});
		{s}_enqueued = {s}_enqueued + 1;
	}} else {{
		// the oldest bucket (sent in {self.buckets} even edges ago; one from before Stop fades and then is gone),
		// the insertion gain, the chip's noise
		{s}_bucket = peek({s}_buckets, {s}_enqueued % {self.buckets}) * ({s}_enqueued - {self.buckets} >= {s}_stop_index ? 1 : {p}_stop_fade);
		{s}_out = {c0!r} * {s}_bucket + {c1!r} * {s}_bucket_previous + {p}_noise_level * noise();
		{s}_bucket_previous = {s}_bucket;{indent(expand_at_edge, 2)}
		{s}_delta = {s}_out - {s}_held;
		{s}_held = {s}_out;
		{indent(chr(10).join(step_out), 2)}
	}}
	{s}_odd_edge_next = 1 - {s}_odd_edge_next;
	{s}_edge_time = {s}_edge_time + {s}_edge_step;
}}
{s}_edge_time = {s}_edge_time - 1;
""")
        # the anti-aliasing filter's states move to this sample's end
        for number, (pole, ratio, weight) in enumerate(ANTI_ALIASING_POLES):
            name = f"{s}_in_{number}"
            if weight == 1:
                lines.append(f"{name}_re = {name}_step * {name}_re + {ratio.real!r} * ({s}_u_previous * ({name}_step - 1) + {s}_u_slope * (({name}_step - 1) * {name}_inverse - 1));")
            else:
                lines.append(f"""{complex_product(f"{name}_ss", (f"{name}_step_re", f"{name}_step_im"), (f"{name}_re", f"{name}_im"))}
{complex_product(f"{name}_sa", (f"{name}_step_re - 1", f"{name}_step_im"), (f"{name}_inverse_re", f"{name}_inverse_im"))}
{name}_drive_re = {s}_u_previous * ({name}_step_re - 1) + {s}_u_slope * ({name}_sa_re - 1);
{name}_drive_im = {s}_u_previous * {name}_step_im + {s}_u_slope * {name}_sa_im;
{name}_re = {name}_ss_re + {ratio.real!r} * {name}_drive_re - {ratio.imag!r} * {name}_drive_im;
{name}_im = {name}_ss_im + {ratio.real!r} * {name}_drive_im + {ratio.imag!r} * {name}_drive_re;""")
        lines.append(f"{s}_u_previous = {s}_u;")
        # the reconstruction filter's output now (HP18 eq. 25: H0 = 1), then its states a sample on
        output = " + ".join(f"{'2 * ' if weight == 2 else ''}{s}_out_{number}_re"
                            for number, (_, _, weight) in enumerate(RECONSTRUCTION_POLES))
        if self.compander_inside:
            lines.append(f"""
// the reconstruction filter (HP18 eq. 25, H0 = 1), the clock's leakage through it (and the expander's gain)
{s}_y = {s}_held + {output}
	+ {p}_leak_level * {s}_expander_level / {p}_reference * clamp((0.45 * samplerate - {s}_clock_hz) / (0.05 * samplerate), 0, 1)
	* sin(pi * ({s}_odd_edge_next < 0.5 ? 1 : 0) + pi * (1 - {s}_edge_time / {s}_edge_step) + {LEAK_PHASE!r});""")
        else:
            lines.append(f"""
// the reconstruction filter (HP18 eq. 25, H0 = 1), the clock's leakage through it, the coupling high-pass
{s}_y = {s}_held + {output}
	+ {p}_leak_level * clamp((0.45 * samplerate - {s}_clock_hz) / (0.05 * samplerate), 0, 1)
	* sin(pi * ({s}_odd_edge_next < 0.5 ? 1 : 0) + pi * (1 - {s}_edge_time / {s}_edge_step) + {LEAK_PHASE!r});""")
        for number, (_, _, weight) in enumerate(RECONSTRUCTION_POLES):
            name = f"{s}_out_{number}"
            if weight == 1:
                lines.append(f"{name}_re = {name}_step * {name}_re;")
            else:
                lines.append(f"""{complex_product(f"{name}_next", (f"{name}_step_re", f"{name}_step_im"), (f"{name}_re", f"{name}_im"))}
{name}_re = {name}_next_re;
{name}_im = {name}_next_im;""")
        if self.compander_inside:
            lines.append(f"""{s}_z = {s}_y;
{s}_heard.write({s}_z);""")
            return "\n".join(lines)
        lines.append(f"""{s}_coupling = {s}_coupling + {p}_coupling_pole * ({s}_y - {s}_coupling);
{s}_coupled = {s}_y - {s}_coupling;
// the expander (1:2, feed-forward on its own input)
{s}_expander_level = {s}_expander_level + {p}_compander_pole * (abs({s}_coupled) - {s}_expander_level);
{s}_z = {s}_coupled * {s}_expander_level / {p}_reference;
{s}_heard.write({s}_z);""")
        return "\n".join(lines)

    def reset_code(self, side):
        """Stop, once the old repeats have faded: the output side starts again."""
        s = f"{self.instance_name}_{side}"
        names = [f"{s}_held", f"{s}_bucket_previous", f"{s}_coupling", f"{s}_expander_level", f"{s}_lowpass_1",
                 f"{s}_lowpass_2", f"{s}_highpass", f"{s}_z_previous"]
        for number, (_, _, weight) in enumerate(RECONSTRUCTION_POLES):
            names.append(f"{s}_out_{number}_re")
            if weight == 2:
                names.append(f"{s}_out_{number}_im")
        return "\n\t".join(f"{name} = 0;" for name in names)

    def statements(self):
        p = self.instance_name
        rounds = range(1, self.rounds_kept + 1)
        clear_rounds = "".join(f"\n\t{p}_round_peak_{n} = 0;" for n in rounds)
        shift_rounds = "".join(f"\n\t{p}_round_peak_{n} = {p}_round_peak_{n - 1};" for n in reversed(rounds) if n > 1)
        if self.rounds_kept:
            shift_rounds += f"\n\t{p}_round_peak_1 = {p}_round_peak_so_far;"
        insert_delay = " + max(${insert_delay_samples}, 0)" if self.loop_insert else ""
        if self.has_stereo_mode:
            mode_code = f"""// the stereo mode: each mode's weight glides there; wide stretches the right loop, ping-pong and mono take the
// right side's lag out
{p}_mode_glide = smoothing_coefficient({STEREO_MODE_GLIDE_MS!r}, samplerate);
{p}_cross = {p}_cross + {p}_mode_glide * ((${{stereo_mode}} == 1) - {p}_cross);
{p}_wide = {p}_wide + {p}_mode_glide * ((${{stereo_mode}} == 2) - {p}_wide);
{p}_mono = {p}_mono + {p}_mode_glide * ((${{stereo_mode}} == 3) - {p}_mono);
{p}_right_time_samples = {p}_steady_samples * (1 + {generated_number(WIDE_RIGHT_RATIO - 1)!r} * {p}_wide);
{p}_right_lag_samples = mstosamps({self.right_lag_ms!r}) * max(1 - {p}_cross - {p}_mono, 0);"""
        else:
            mode_code = f"""{p}_right_time_samples = {p}_steady_samples;
{p}_right_lag_samples = mstosamps({self.right_lag_ms!r});"""
        code = f"""// {p}: bucket-brigade echo (kit technique: bucket-brigade echo)
// Stop: the repeats fade, then nothing from before is heard again
{p}_stop_now = ${{stop_pressed}};
if ({p}_stop_now) {{
	{p}_since_stop = 0;
	{p}_stop_fade = 1;
	{p}_left_stop_index = {p}_left_enqueued;
	{p}_right_stop_index = {p}_right_enqueued;
	{p}_reset_done = 0;
	{p}_round_elapsed = 0;
	{p}_round_peak_so_far = 0;{clear_rounds}
}}

// Time starts at its target, then glides as the tape echo's does: the clock never turns round
{self.time_starts_at_its_target.statements()}
{p}_target_ms = ${{time_ms}};
{p}_glide = ({p}_target_ms - {p}_time_ms) * smoothing_coefficient({p}_target_ms > {p}_time_ms ? {TIME_GLIDE_UP_MS!r} : {TIME_GLIDE_DOWN_MS!r}, samplerate);
{p}_time_ms = {p}_time_ms + clamp({p}_glide, -{HIGHEST_TIME_CHANGE!r} * 1000 / samplerate, {HIGHEST_TIME_CHANGE!r} * 1000 / samplerate);
{p}_steady_samples = mstosamps({p}_time_ms);
{mode_code}

// the clock's wobble in cents: wow (noise through two one-poles at WOW_HZ, unit RMS) and flutter (a sine of RMS
// flutter_cents); it multiplies both chips' clocks
{p}_wow_pole = 1 - exp(-twopi * {WOW_HZ!r} / samplerate);
{p}_wow_1 = {p}_wow_1 + {p}_wow_pole * (noise() - {p}_wow_1);
{p}_wow_2 = {p}_wow_2 + {p}_wow_pole * ({p}_wow_1 - {p}_wow_2);
{p}_wow_pole_rest_2 = (1 - {p}_wow_pole) * (1 - {p}_wow_pole);
{p}_wow_unit = {p}_wow_2 / sqrt((1 / 3) * pow({p}_wow_pole, 4) * (1 + {p}_wow_pole_rest_2) / pow(1 - {p}_wow_pole_rest_2, 3));
{p}_flutter_phase = wrap({p}_flutter_phase + {FLUTTER_HZ!r} / samplerate, 0, 1);
{p}_wobble_cents = clamp(clamp(${{wow_cents}}, 0, {HIGHEST_WOW_CENTS!r}) * {p}_wow_unit
	+ clamp(${{flutter_cents}}, 0, {HIGHEST_FLUTTER_CENTS!r}) * {generated_number(math.sqrt(2))!r} * sin(twopi * {p}_flutter_phase), -{WOBBLE_LIMIT_CENTS!r}, {WOBBLE_LIMIT_CENTS!r});
{p}_wobble = exp({p}_wobble_cents * {generated_number(NATURAL_LOG_OF_2 / 1200)!r});

// the loop's own delays in host samples: the tone filters' group delay at the middle of their band (as the tape
// echo's), the sample the loop waits, the sample the BBD's input waits, what the device puts in the loop
{p}_feedback = ${{feedback}} / {self.peak_loop_gain!r};
{p}_full_level = {self.full_level!r} / max(${{saturation_gain}}, 1);
{p}_reference = {generated_number(2 / math.pi)!r} * {p}_full_level;
{p}_noise_level = {generated_number(10 ** (NOISE_DB / 20) * math.sqrt(0.5) * math.sqrt(3))!r} * {p}_full_level;
{p}_leak_level = {LEAK_GAIN!r} * {p}_full_level;
{p}_compander_pole = smoothing_coefficient({COMPANDER_TIME_MS!r}, samplerate);
{p}_coupling_pole = 1 - exp(-twopi * {COUPLING_HIGH_PASS_HZ!r} / samplerate);
{p}_lowpass_hz = clamp(${{loop_lowpass_hz}}, 20, samplerate * 0.45);
{p}_highpass_hz = clamp(${{loop_highpass_hz}}, 1, samplerate * 0.45);
{p}_tone_delay = 2 * samplerate / (twopi * {p}_lowpass_hz * (1 + {p}_highpass_hz / {p}_lowpass_hz))
	+ samplerate / (twopi * {p}_highpass_hz * (1 + {p}_lowpass_hz / {p}_highpass_hz));
{p}_lowpass_pole = 1 - exp(-twopi * {p}_lowpass_hz / samplerate);
{p}_highpass_pole = 1 - exp(-twopi * {p}_highpass_hz / samplerate);
{p}_loop_delay = {p}_tone_delay + 2{insert_delay};
// the clock: the chain's periods (the buckets, the filters, the insertion filter) in the time left; the filters at
// the steady clock, the chips at the wobbling one, held under {MAXIMUM_EDGES_PER_SAMPLE} edges a sample
{p}_left_filter_clock = {self.chain_periods!r} * samplerate / max({p}_steady_samples - {p}_loop_delay, 1);
{p}_right_filter_clock = {self.chain_periods!r} * samplerate / max({p}_right_time_samples - {p}_loop_delay, 1);
{p}_left_clock_hz = min({p}_left_filter_clock * {p}_wobble, {MAXIMUM_EDGES_PER_SAMPLE / 2 - 0.01!r} * samplerate);
{p}_right_clock_hz = min({p}_right_filter_clock * {p}_wobble, {MAXIMUM_EDGES_PER_SAMPLE / 2 - 0.01!r} * samplerate);
{p}_left_filter_clock = min({p}_left_filter_clock, {MAXIMUM_EDGES_PER_SAMPLE / 2 - 0.01!r} * samplerate);
{p}_right_filter_clock = min({p}_right_filter_clock, {MAXIMUM_EDGES_PER_SAMPLE / 2 - 0.01!r} * samplerate);

// Stop's fade, and what is heard: the old repeats fade, the heard line holds them a little longer
{p}_since_stop = min({p}_since_stop + 1, 1e9);
{p}_stop_fade = max({p}_stop_fade - 1 / mstosamps({STOP_FADE_MS!r}), 0);
{p}_loop_open = {p}_reset_done;
{p}_heard_samples = clamp({p}_tone_delay + 1, 1, mstosamps({HEARD_LIMIT_MS!r}));
{p}_keep = max({p}_stop_fade, clamp(({p}_since_stop - mstosamps({STOP_FADE_MS!r}) - {p}_heard_samples - {p}_right_lag_samples - 4) / mstosamps({STOP_FADE_MS!r}), 0, 1));
"""
        for side in ("left", "right"):
            code += self.chain_code(side)
        code += f"""
// what is heard: the line adds what the loop has that the first pass hasn't (the tone filters, a sample)
{p}_left = {p}_left_heard.read({p}_heard_samples, interp="spline") * {p}_keep;
{p}_right = {p}_right_heard.read({p}_heard_samples + {p}_right_lag_samples, interp="spline") * {p}_keep;
if ({p}_stop_fade <= 0 && {p}_reset_done < 1) {{
	{self.reset_code("left")}
	{self.reset_code("right")}
	{p}_reset_done = 1;
}}
"""
        for side in ("left", "right"):
            s = f"{p}_{side}"
            code += f"""
// {side}: the loop's tone, low-pass (12 dB), high-pass (6 dB), on last sample's repeat
{s}_lowpass_1 = {s}_lowpass_1 + {p}_lowpass_pole * ({s}_z_previous - {s}_lowpass_1);
{s}_lowpass_2 = {s}_lowpass_2 + {p}_lowpass_pole * ({s}_lowpass_1 - {s}_lowpass_2);
{s}_highpass = {s}_highpass + {p}_highpass_pole * ({s}_lowpass_2 - {s}_highpass);
// the host samples reach the anti-aliasing filter as a straight line between them, sinc^2(f / fs) at the loop's
// peak, {'once (the compander inside the filters does not double it)' if self.compander_inside else 'doubled by the compander for a steady tone'}: given back, so feedback 1 is unity there at any host rate while
// the peak is under a quarter of it (a shorter time's peak is past what the host carries well: no more is given)
{s}_peak_angle = min({generated_number(math.pi * self.peak_clock_fraction)!r} * {s}_filter_clock / samplerate, {generated_number(math.pi / 4)!r});
{s}_line_loss = sin({s}_peak_angle) / {s}_peak_angle;
{s}_fed = ({s}_lowpass_2 - {s}_highpass) * {p}_feedback * {p}_loop_open / pow({s}_line_loss, {2 if self.compander_inside else 4});
{s}_z_previous = {s}_z;
"""
        code += f"""
// what goes into each BBD
{p}_left_sent = ${{left_input}};
{p}_right_sent = ${{right_input}};"""
        if self.has_stereo_mode:
            code += f"""
// ping-pong: both inputs into the left BBD, each side's repeat into the other's; mono: both the inputs' mean
{p}_both_sent = 0.5 * ({p}_left_sent + {p}_right_sent);
{p}_left_into_tape = (1 - {p}_mono) * ({p}_left_sent + {p}_cross * {p}_right_sent) + {p}_mono * {p}_both_sent
	+ (1 - {p}_cross) * {p}_left_fed + {p}_cross * {p}_right_fed;
{p}_right_into_tape = (1 - {p}_mono) * (1 - {p}_cross) * {p}_right_sent + {p}_mono * {p}_both_sent
	+ (1 - {p}_cross) * {p}_right_fed + {p}_cross * {p}_left_fed;
// mono: both outputs their mean
{p}_left_heard_now = {p}_left;
{p}_left = {p}_left + 0.5 * {p}_mono * ({p}_right - {p}_left);
{p}_right = {p}_right + 0.5 * {p}_mono * ({p}_left_heard_now - {p}_right);"""
        else:
            code += f"""
{p}_left_into_tape = {p}_left_sent + {p}_left_fed;
{p}_right_into_tape = {p}_right_sent + {p}_right_fed;"""
        if not self.loop_insert:
            code += f"""
{p}_left_into_bbd = {p}_left_into_tape;
{p}_right_into_bbd = {p}_right_into_tape;"""
        code += f"""

// the meter and the rounds: what the loop really did, round by round (the 2 ms fade at Stop isn't counted)
{p}_loop_samples = {p}_steady_samples;
{p}_level = max(abs({p}_left) + abs({p}_right), {p}_level * (1 - smoothing_coefficient({LEVEL_METER_FALL_MS!r}, samplerate)));
if ({p}_stop_fade <= 0) {{
	{p}_round_peak_so_far = max({p}_round_peak_so_far, abs({p}_left) + abs({p}_right));
}}
{p}_round_elapsed = {p}_round_elapsed + 1;
if ({p}_round_elapsed >= {p}_loop_samples) {{{shift_rounds}
	{p}_round_peak_so_far = 0;
	{p}_round_elapsed = 0;
}}"""
        return self.substituted(code)


class BucketBrigadeEchoWriter(Technique):
    """Gives a `BucketBrigadeEcho`'s BBDs their input when the device has its own processing in the loop
    (`loop_insert=True`): `left` and `right` are what the device made of `<echo>_left_into_tape` and
    `<echo>_right_into_tape`. Its marker (`<ECHO>_BBD_WRITER`) goes after that processing; the BBDs take it on the
    next sample (the sample counted in the loop's delay). What the device puts in the loop must hold its own Stop. No
    outputs."""

    def __init__(self, echo, *, left, right):
        if not isinstance(echo, BucketBrigadeEcho) or not echo.loop_insert:
            raise BuildError("BucketBrigadeEchoWriter: it feeds the BBDs of a BucketBrigadeEcho made with "
                             "loop_insert=True")
        super().__init__(f"{echo.instance_name}_bbd_writer", left=left, right=right)
        self.echo_name = echo.instance_name
        self.latency_samples = 0

    def statements(self):
        return self.substituted(f"""// {self.echo_name}'s BBDs: what the device made of what goes into them
{self.echo_name}_left_into_bbd = ${{left}};
{self.echo_name}_right_into_bbd = ${{right}};""")
