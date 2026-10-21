"""The Moog transistor ladder low-pass filter (a circuit module): the 904A / Minimoog VCF, Moog's patent US 3,475,623,
every one of the ladder's four stages and its input pair a tanh of its own (references/circuits/moog-transistor-ladder.md).

The circuit (§2 there): an input differential pair (the audio on one base, the fed-back output on the other) drives
four stages, each two transistors with a capacitor C between their emitters; the current If drawn from the bottom of
the ladder, set by an exponential converter, sets the cutoff. The large-signal model (D'Angelo & Valimaki 2014
Part I eqs. 1-2, Huovilainen DAFx-04 eq. 10), with the differential capacitor voltages Vi and x = V / (2 VT):

    dx1/dt = wc (tanh(u - k x4) - tanh(x1)),   dxi/dt = wc (tanh(x(i-1)) - tanh(xi)),   wc = If / (4 C VT)

where u = (the input pair's base voltage + its offset) / (2 VT) and k the feedback gain (the Emphasis pot). Small
signals: H(s) = 1 / ((1 + s / wc)^4 + k), the cutoff fc = If / (8 pi C VT) (Stinchcombe 2008 eq. 13), self-oscillation
from k = 4 at fc, the pass band 1 / (1 + k) (-14 dB at k = 4: Stinchcombe §2.5).

The solve: each step is the trapezoidal rule on all five tanh (TPT one-poles, prewarped at fc, so the small-signal
loop is exactly 180 degrees at fc), the nonlinear loop solved with no unit delay by Newton's method: the Jacobian is
cyclic bidiagonal, so each iteration is one forward sweep and one division (stage i's correction p_i + q_i d4, d4 =
p4 / (1 - q4), 1 - q4 >= 1 for k >= 0: never singular). NEWTON_ITERATIONS = 2 from the last step's solution (research
2026-10-20, against RK4 at 64x decimated by a Blackman sinc: 2 iterations are within 0.02 dB of 8 on every harmonic
below 10 kHz; 1 iteration blows up at fc 18 kHz, k 3.9, a hot input). `oversampling` (a wiring choice, required: 2
or 1) runs it twice a host sample between the kit's halfband oversampler's upsampler and downsampler (3.07
samples late at low frequencies: `latency_samples`, theirs summed), or once with no latency. At 2x the controls
meet the audio: the cutoff's warp and k, worked out at the host rate, reach each step delayed by the upsampler's own
latency (`ControlsAtTheUpsampledSteps`), so a cutoff step acts on the audio sent with it (held over both steps they
led it by 1.53 samples, found by 2sl stab 2.2.8; the test measures the alignment by cutoff FM's sidebands). The worst
alias of a hot sine (drive 10 = 0.52 V at the bases, fc 12 kHz, k 2, 2.5 kHz): -30 dB at 1x, -55 dB at 2x; drive 5, fc 5 kHz, k 3:
-84 dB at 1x, -127 dB at 2x; at fc 18 kHz, k 3.9, drive 20: -12 dB at 1x, -34 dB at 2x, the aliases made above the
doubled rate's Nyquist (the research's table, references/circuits/moog-transistor-ladder.md §6).

Inputs (the circuit's): `input_volts` (the audio at the filter's input), `control_volts` (the sum at the control node,
exponential: `volts_per_octave` a doubling of If), `emphasis` (the Emphasis pot's rotation, 0..1, 0 to 10 on its
dial). k from the rotation is the circuit's law (references/circuits/moog-transistor-ladder.md §2.4): the 50k
reverse-audio pot divides the loop's tap (15.1 x the top stage's volts) with the REGEN CAL trim and R76,
k = tap (R76 + w R73) / (R76 + R73 + Rtop(rotation)), hyperbolic in the pot's resistance above its wiper; the trim w is
set as the service manual's calibration sets it, so the loop's gain is 4 (regeneration starts) at Emphasis 7.5 of 10
(`feedback_gain_at_emphasis`, `regeneration_trim_wiper`). With the default taper: k 0.2 at 0, 4 at 7.5, 7.75 at 10. Outputs: `<name>_out` (volts: the output buffer's gain makes it
the input at low frequencies for k = 0, patent col. 2 l. 6-9; then the output's coupling capacitor's high-pass),
`<name>_cutoff_hz` (fc, as clamped), `<name>_feedback_gain` (k; both as the controls are now, before the 2x
core's delay), `<name>_ladder_current_amps` (If).
`reset_statements()` empties the ladder. `response_script_code()`: the instance's small-signal response and its
Emphasis law in ES5, for a display (templates/moog-transistor-ladder-response.template.js).

The build character (`MoogTransistorLadderCharacter`): VT, C (the Minimoog's 0.068 uF), each stage's capacitor as a
ratio (mismatch), the input pair's offset (even harmonics), the mixer's volts-at-the-bases per input volt (an input:
one full-level mixer channel's source volts; how hot a given level drives it), the converter's reference current and
volts per octave, the Emphasis loop's parts (the tap's gain, R76, the REGEN CAL trim, the pot and its taper, the
calibration's Emphasis) and the output coupling corner. The UNVERIFIED defaults (the pot's taper) are marked; §7 of the
reference says which.
"""

import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.halfband_oversampler import (ControlsAtTheUpsampledSteps, HalfbandDownsampler,
                                                     HalfbandUpsampler, halfband_coefficients, halfband_response)
from m4l_dev.techniques.zero_delay_one_pole_filter import ZeroDelayOnePoleFilter

NEWTON_ITERATIONS = 2
HIGHEST_CUTOFF_OF_SAMPLE_RATE = 0.45     # fc held under 0.45 of the host rate (the steps prewarp at fc)
LOWEST_CUTOFF_HZ = 5.0
STAGES = 4
OVERSAMPLINGS = (1, 2)                   # once a sample, or twice through the kit's halfband oversampler
REFERENCE_CUTOFF_HZ = 261.6255653  # [DESIGN] 0 V at the control node is middle C (to generated_number's digits)
REGENERATION_ONSET_FEEDBACK_GAIN = 4.0   # [VERIFIED] the ladder self-oscillates from k = 4 (Stinchcombe 2008 §2.5)


def ladder_cutoff_hz(ladder_current_amps, ladder_capacitance_farads, thermal_voltage_volts):
    """fc = If / (8 pi C VT) (Stinchcombe 2008 eq. 13; D'Angelo & Valimaki Part I eq. 11 at k = 0)."""
    return ladder_current_amps / (8 * math.pi * ladder_capacitance_farads * thermal_voltage_volts)


_TYPICAL_CAPACITANCE = 0.068e-6          # Minimoog filter board no. 4, C3 / C7 / C11 / C16 .068 (fig. 9-11)
_TYPICAL_THERMAL_VOLTAGE = 0.026         # D'Angelo & Valimaki Part I: "VT ... (~26 mV at room temperature 300 K)"


@dataclasses.dataclass(frozen=True)
class MoogTransistorLadderCharacter:
    """One ladder's build character; defaults: a Minimoog's capacitors, a matched ladder, room temperature."""
    thermal_voltage_volts: float = _TYPICAL_THERMAL_VOLTAGE
    ladder_capacitance_farads: float = _TYPICAL_CAPACITANCE
    stage_1_capacitance_ratio: float = 1.0          # each stage's C over `ladder_capacitance_farads`: mismatch
    stage_2_capacitance_ratio: float = 1.0
    stage_3_capacitance_ratio: float = 1.0
    stage_4_capacitance_ratio: float = 1.0
    input_pair_offset_volts: float = 0.0            # base-to-base offset of the input pair (Minimoog: matched pairs)
    base_volts_per_input_volt: float = 0.014        # [DERIVED] one full-level mixer channel: 470 / (470 + 33k), ref §2.4
    ladder_current_at_zero_control_volts_amps: float = (
        REFERENCE_CUTOFF_HZ * 8 * math.pi * _TYPICAL_CAPACITANCE * _TYPICAL_THERMAL_VOLTAGE)   # [DESIGN] fc(0 V) = C4
    volts_per_octave: float = 1.0                   # the Scale trim's calibration (R49, Minimoog)
    emphasis_tap_gain: float = 15.1                 # [DERIVED] ref §2.4: the R3 / R7 tap's volts per top-stage volt
    regeneration_fixed_ohms: float = 330.0          # [VERIFIED] R76 (Minimoog fig. 9-11)
    regeneration_trim_ohms: float = 1000.0          # [VERIFIED] R73, the REGEN CAL trimpot (fig. 9-11)
    emphasis_pot_ohms: float = 50000.0              # [VERIFIED] R14 50k REV AUD (fig. 9-17)
    emphasis_pot_audio_taper_at_half_rotation: float = 0.10   # [UNVERIFIED] ref §7: the reverse-audio taper's mirror
    regeneration_onset_emphasis: float = 0.75       # [VERIFIED] Folkman Model D service manual p. 14: trimmed to start at 7.5
    output_coupling_corner_hz: float = 15.4         # [INFERENCE] C5 0.22 uF into R31 47 kOhm (Minimoog fig. 9-11)


def check_the_character(character, instance_name):
    """Fails the build on a character the model has no meaning for."""
    positive_fields = ("thermal_voltage_volts", "ladder_capacitance_farads", "stage_1_capacitance_ratio",
                       "stage_2_capacitance_ratio", "stage_3_capacitance_ratio", "stage_4_capacitance_ratio",
                       "base_volts_per_input_volt", "ladder_current_at_zero_control_volts_amps", "volts_per_octave",
                       "output_coupling_corner_hz", "emphasis_tap_gain", "regeneration_fixed_ohms",
                       "regeneration_trim_ohms", "emphasis_pot_ohms")
    for field_name in positive_fields:
        value = getattr(character, field_name)
        if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
            raise BuildError(f"MoogTransistorLadder {instance_name}: character {field_name} is {value!r}; it must be "
                             "a finite number above 0")
    value = character.input_pair_offset_volts
    if not (isinstance(value, (int, float)) and math.isfinite(value)):
        raise BuildError(f"MoogTransistorLadder {instance_name}: character input_pair_offset_volts is {value!r}; it "
                         "must be a finite number")
    taper = character.emphasis_pot_audio_taper_at_half_rotation
    if not (isinstance(taper, (int, float)) and 0 < taper < 0.5):
        raise BuildError(f"MoogTransistorLadder {instance_name}: emphasis_pot_audio_taper_at_half_rotation is "
                         f"{taper!r}; an audio taper's resistance at half rotation is a fraction in (0, 0.5)")
    onset = character.regeneration_onset_emphasis
    if not (isinstance(onset, (int, float)) and 0 <= onset <= 1):
        raise BuildError(f"MoogTransistorLadder {instance_name}: regeneration_onset_emphasis is {onset!r}; it is a "
                         "rotation in [0, 1]")
    wiper = regeneration_trim_wiper(character)
    if not 0 <= wiper <= 1:
        raise BuildError(f"MoogTransistorLadder {instance_name}: no REGEN CAL setting starts regeneration at Emphasis "
                         f"{onset}: the trim's wiper would have to be at {wiper:.3f} of its travel (0..1)")


def emphasis_taper_base(character):
    """b of the audio taper A(t) = (b^t - 1) / (b - 1) (A(0) 0, A(1) 1) with A(1/2) = m, the character's fraction at
    half rotation: b = ((1 - m) / m)^2."""
    fraction = character.emphasis_pot_audio_taper_at_half_rotation
    return ((1 - fraction) / fraction) ** 2


def emphasis_pot_ohms_above_wiper(emphasis, character):
    """Rtop: the 50k reverse-audio pot's resistance from the tap's end (pin 7, the clockwise end) to its wiper at a
    rotation 0..1 (clamped). A reverse-audio pot is the audio taper mirrored: its resistance from the clockwise end is
    A(1 - rotation) of the whole."""
    rotation = min(max(emphasis, 0.0), 1.0)
    base = emphasis_taper_base(character)
    return character.emphasis_pot_ohms * (base ** (1 - rotation) - 1) / (base - 1)


def regeneration_numerator(character):
    """tap x (R76 + w R73) with the trim w calibrated (k = 4 at the onset Emphasis): 4 (R76 + R73 + Rtop(onset))."""
    return REGENERATION_ONSET_FEEDBACK_GAIN * (character.regeneration_fixed_ohms + character.regeneration_trim_ohms
                                               + emphasis_pot_ohms_above_wiper(character.regeneration_onset_emphasis,
                                                                               character))


def regeneration_trim_wiper(character):
    """Where the service manual's calibration leaves the REGEN CAL trim's wiper (0 at R76's end, 1 at the pot's)."""
    return ((regeneration_numerator(character) / character.emphasis_tap_gain - character.regeneration_fixed_ohms)
            / character.regeneration_trim_ohms)


def feedback_gain_at_emphasis(emphasis, character):
    """k at an Emphasis rotation 0..1 (clamped): the circuit's law, tap (R76 + w R73) / (R76 + R73 + Rtop)."""
    return regeneration_numerator(character) / (character.regeneration_fixed_ohms + character.regeneration_trim_ohms
                                                + emphasis_pot_ohms_above_wiper(emphasis, character))


def emphasis_for_feedback_gain(feedback_gain, character):
    """The rotation that gives `feedback_gain` (feedback_gain_at_emphasis's inverse; k(0) <= k <= k(1))."""
    lowest, highest = feedback_gain_at_emphasis(0.0, character), feedback_gain_at_emphasis(1.0, character)
    if not lowest <= feedback_gain <= highest:
        raise BuildError(f"MoogTransistorLadder: the Emphasis reaches k {lowest:.4g} to {highest:.4g}, not {feedback_gain}")
    ohms_above_wiper = (regeneration_numerator(character) / feedback_gain - character.regeneration_fixed_ohms
                        - character.regeneration_trim_ohms)
    base = emphasis_taper_base(character)
    return min(max(1 - math.log(1 + max(ohms_above_wiper, 0.0) / character.emphasis_pot_ohms * (base - 1), base), 0.0), 1.0)


def stage_capacitance_ratios(character):
    return tuple(getattr(character, f"stage_{stage}_capacitance_ratio") for stage in range(1, STAGES + 1))


def cutoff_hz_at_control_volts(control_volts, character):
    """The ladder's fc at `control_volts` on the control node: If = I0 2^(V / volts_per_octave), fc = If / (8 pi C VT)."""
    current = character.ladder_current_at_zero_control_volts_amps * 2 ** (control_volts / character.volts_per_octave)
    return ladder_cutoff_hz(current, character.ladder_capacitance_farads, character.thermal_voltage_volts)


def control_volts_for_cutoff_hz(cutoff_hz, character):
    """The control-node volts that put fc at `cutoff_hz` (cutoff_hz_at_control_volts's inverse): what an instrument
    whose knob is in Hz sends."""
    if cutoff_hz <= 0:
        raise BuildError(f"MoogTransistorLadder: no control voltage gives a cutoff of {cutoff_hz} Hz")
    return character.volts_per_octave * math.log2(cutoff_hz / cutoff_hz_at_control_volts(0.0, character))


def small_signal_response(frequency_hz, cutoff_hz, feedback_gain, sample_rate, *, oversampling, character=None):
    """The module's complex response for small signals (every tanh's slope 1, no offset), input volts to output volts
    before the coupling high-pass: the TPT ladder at `oversampling` x the host rate (each stage the bilinear one-pole
    at g_i = tan(pi fc / (N sr)) / r_i, the loop 1 / (P^-1 + k)); at 2x, between the halfband upsampler and
    downsampler, the half-band low-pass at f / (2 sr) twice (their images 99 dB down, left out). At 1x it is the
    analog 1 / ((1 + s)^4 + k) at s = j tan(pi f / sr) / tan(pi fc / sr)."""
    if oversampling not in OVERSAMPLINGS:
        raise BuildError(f"MoogTransistorLadder: oversampling is one of {OVERSAMPLINGS}, got {oversampling!r}")
    character = character or MoogTransistorLadderCharacter()
    cutoff_hz = min(max(cutoff_hz, LOWEST_CUTOFF_HZ), HIGHEST_CUTOFF_OF_SAMPLE_RATE * sample_rate)
    warp = math.tan(math.pi * cutoff_hz / (sample_rate * oversampling))
    theta = 2 * math.pi * frequency_hz / (sample_rate * oversampling)
    z = complex(math.cos(theta), math.sin(theta))
    s_bilinear = (z - 1) / (z + 1)
    product = 1
    for ratio in stage_capacitance_ratios(character):
        product *= 1 / (1 + s_bilinear * ratio / warp)
    ladder = product / (1 + feedback_gain * product)
    if oversampling == 1:
        return ladder
    # the up / down pair measures as the half-band squared one doubled-rate sample early (z), to 1e-3 degrees
    return ladder * halfband_response(frequency_hz / (2 * sample_rate), halfband_coefficients()) ** 2 * z


class MoogTransistorLadder(CircuitModule):
    """`<name>_out`: `input_volts` through the Moog transistor ladder at `control_volts` (exponential) and `emphasis`
    (0..1). See the module's docstring for every input and output."""

    references_entry = "references/circuits/moog-transistor-ladder.md"
    character_type = MoogTransistorLadderCharacter

    def __init__(self, instance_name, *, input_volts, control_volts, emphasis, oversampling, character=None):
        super().__init__(instance_name, character=character, input_volts=input_volts, control_volts=control_volts,
                         emphasis=emphasis)
        if isinstance(oversampling, bool) or oversampling not in OVERSAMPLINGS:
            raise BuildError(f"MoogTransistorLadder {instance_name}: oversampling is one of {OVERSAMPLINGS} (the kit's "
                             f"oversampler is 2x), got {oversampling!r}")
        check_the_character(self.character, instance_name)
        self.oversampling = oversampling
        self.upsampler = self.downsampler = self.controls_at_the_steps = None
        if oversampling == 2:
            self.upsampler = HalfbandUpsampler(f"{instance_name}_up", input=f"{instance_name}_input")
            self.downsampler = HalfbandDownsampler(f"{instance_name}_down", first=f"{instance_name}_x4_step_1",
                                                   second=f"{instance_name}_x4_step_2")
            self.controls_at_the_steps = ControlsAtTheUpsampledSteps(
                f"{instance_name}_controls", upsampler=self.upsampler,
                controls=dict(warp=f"{instance_name}_warp", feedback_gain=f"{instance_name}_feedback_gain"))
        # the ladder and its coupling are zero-delay: the module is as late as its oversampler's pair
        self.latency_samples = 0 if oversampling == 1 else \
            self.upsampler.latency_samples + self.downsampler.latency_samples
        self.output_coupling = ZeroDelayOnePoleFilter(f"{instance_name}_coupling", input=f"{instance_name}_ladder_volts",
                                                      cutoff_hz=repr(float(self.character.output_coupling_corner_hz)))

    def declarations(self):
        declarations = [self.substituted("History ${p}_s1(0), ${p}_s2(0), ${p}_s3(0), ${p}_s4(0), ${p}_x1(0), "
                                         "${p}_x2(0), ${p}_x3(0), ${p}_x4(0);"), self.output_coupling.declarations()]
        if self.oversampling == 2:
            declarations += [self.upsampler.declarations(), self.controls_at_the_steps.declarations(),
                             self.downsampler.declarations()]
        return "\n".join(declarations)

    def _newton_iteration(self):
        """One Newton step on the five-tanh trapezoidal loop (the module docstring's solve)."""
        return self.substituted("""${p}_t0 = tanh(${p}_drive - ${p}_step_feedback_gain * ${p}_x4);
${p}_t1 = tanh(${p}_x1);
${p}_t2 = tanh(${p}_x2);
${p}_t3 = tanh(${p}_x3);
${p}_t4 = tanh(${p}_x4);
${p}_slope0 = 1 - ${p}_t0 * ${p}_t0;
${p}_slope1 = 1 - ${p}_t1 * ${p}_t1;
${p}_slope2 = 1 - ${p}_t2 * ${p}_t2;
${p}_slope3 = 1 - ${p}_t3 * ${p}_t3;
${p}_a1 = 1 + ${p}_g1 * ${p}_slope1;
${p}_a2 = 1 + ${p}_g2 * ${p}_slope2;
${p}_a3 = 1 + ${p}_g3 * ${p}_slope3;
${p}_a4 = 1 + ${p}_g4 * (1 - ${p}_t4 * ${p}_t4);
${p}_p1 = (${p}_s1 + ${p}_g1 * (${p}_t0 - ${p}_t1) - ${p}_x1) / ${p}_a1;
${p}_q1 = -${p}_g1 * ${p}_step_feedback_gain * ${p}_slope0 / ${p}_a1;
${p}_p2 = (${p}_s2 + ${p}_g2 * (${p}_t1 - ${p}_t2) - ${p}_x2 + ${p}_g2 * ${p}_slope1 * ${p}_p1) / ${p}_a2;
${p}_q2 = ${p}_g2 * ${p}_slope1 * ${p}_q1 / ${p}_a2;
${p}_p3 = (${p}_s3 + ${p}_g3 * (${p}_t2 - ${p}_t3) - ${p}_x3 + ${p}_g3 * ${p}_slope2 * ${p}_p2) / ${p}_a3;
${p}_q3 = ${p}_g3 * ${p}_slope2 * ${p}_q2 / ${p}_a3;
${p}_p4 = (${p}_s4 + ${p}_g4 * (${p}_t3 - ${p}_t4) - ${p}_x4 + ${p}_g4 * ${p}_slope3 * ${p}_p3) / ${p}_a4;
${p}_q4 = ${p}_g4 * ${p}_slope3 * ${p}_q3 / ${p}_a4;
${p}_d4 = ${p}_p4 / (1 - ${p}_q4);
${p}_x1 = ${p}_x1 + ${p}_p1 + ${p}_q1 * ${p}_d4;
${p}_x2 = ${p}_x2 + ${p}_p2 + ${p}_q2 * ${p}_d4;
${p}_x3 = ${p}_x3 + ${p}_p3 + ${p}_q3 * ${p}_d4;
${p}_x4 = ${p}_x4 + ${p}_d4;
""")

    def _step(self, step_number, input_volts, warp, feedback_gain):
        """One trapezoidal step at `oversampling` x the host rate on `input_volts` at the controls `warp` and
        `feedback_gain` (the step's own: at 2x delayed to its audio), leaving `<name>_x4_step_<n>`."""
        ratios = stage_capacitance_ratios(self.character)
        text = self.substituted("""// ${p}: step ${step} of ${steps}
${p}_g1 = ${warp} / ${ratio1};
${p}_g2 = ${warp} / ${ratio2};
${p}_g3 = ${warp} / ${ratio3};
${p}_g4 = ${warp} / ${ratio4};
${p}_step_feedback_gain = ${feedback_gain};
${p}_drive = ${step_input} * ${p}_drive_per_volt + ${p}_offset_drive;
""", step=str(step_number), steps=str(self.oversampling), step_input=input_volts, warp=warp,
            feedback_gain=feedback_gain, ratio1=ratios[0], ratio2=ratios[1], ratio3=ratios[2], ratio4=ratios[3])
        text += self._newton_iteration() * NEWTON_ITERATIONS
        text += self.substituted("""${p}_s1 = 2 * ${p}_x1 - ${p}_s1;
${p}_s2 = 2 * ${p}_x2 - ${p}_s2;
${p}_s3 = 2 * ${p}_x3 - ${p}_s3;
${p}_s4 = 2 * ${p}_x4 - ${p}_s4;
${p}_x4_step_${step} = ${p}_x4;
""", step=str(step_number))
        return text

    def statements(self):
        character = self.character
        p = self.instance_name
        text = self.substituted("""// ${p}: the Moog transistor ladder (kit circuit module: Moog transistor ladder)
${p}_input = ${input_volts};
${p}_ladder_current_amps = ${current_at_zero} * pow(2, ${control_volts} / ${volts_per_octave});
${p}_cutoff_hz = clamp(${p}_ladder_current_amps / ${current_per_hz}, ${lowest}, samplerate * ${highest});
${p}_feedback_gain = ${numerator} / (${loop_ohms} + ${pot_ohms_per_taper_step} * (pow(${taper_base}, 1 - clamp(${emphasis}, 0, 1)) - 1));
${p}_warp = tan(pi * ${p}_cutoff_hz / (samplerate * ${steps}));
${p}_drive_per_volt = ${drive_per_volt};
${p}_offset_drive = ${offset_drive};
""", current_at_zero=character.ladder_current_at_zero_control_volts_amps,
            volts_per_octave=character.volts_per_octave,
            current_per_hz=8 * math.pi * character.ladder_capacitance_farads * character.thermal_voltage_volts,
            lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_CUTOFF_OF_SAMPLE_RATE,
            numerator=regeneration_numerator(character),
            loop_ohms=character.regeneration_fixed_ohms + character.regeneration_trim_ohms,
            pot_ohms_per_taper_step=character.emphasis_pot_ohms / (emphasis_taper_base(character) - 1),
            taper_base=emphasis_taper_base(character), steps=str(self.oversampling),
            drive_per_volt=character.base_volts_per_input_volt / (2 * character.thermal_voltage_volts),
            offset_drive=character.input_pair_offset_volts / (2 * character.thermal_voltage_volts))
        if self.oversampling == 1:
            text += self._step(1, f"{p}_input", f"{p}_warp", f"{p}_feedback_gain") + \
                self.substituted("${p}_x4_out = ${p}_x4_step_1;\n")
        else:
            text += self.upsampler.statements() + "\n" + self.controls_at_the_steps.statements() + "\n"
            text += self._step(1, f"{p}_up_first", f"{p}_controls_warp_step_1", f"{p}_controls_feedback_gain_step_1")
            text += self._step(2, f"{p}_up_second", f"{p}_controls_warp_step_2", f"{p}_controls_feedback_gain_step_2")
            text += self.downsampler.statements() + self.substituted("\n${p}_x4_out = ${p}_down_out;\n")
        text += self.substituted("""// the output buffer: the last stage's volts (2 VT x4) back to the input's scale
${p}_ladder_volts = ${p}_x4_out * ${volts_out_per_x4};
""", volts_out_per_x4=2 * character.thermal_voltage_volts / character.base_volts_per_input_volt)
        text += self.output_coupling.statements() + self.substituted("\n${p}_out = ${p}_coupling_highpass;")
        return text

    def reset_statements(self):
        """The ladder's capacitors and the coupling capacitor empty (a Stop)."""
        return self.substituted("${p}_s1 = 0;\n${p}_s2 = 0;\n${p}_s3 = 0;\n${p}_s4 = 0;\n${p}_x1 = 0;\n${p}_x2 = 0;\n"
                                "${p}_x3 = 0;\n${p}_x4 = 0;\n") + self.output_coupling.reset_statements() + "".join(
            "\n" + block.reset_statements() for block in (self.upsampler, self.downsampler) if block is not None)

    def response_script_code(self):
        """ES5 for a display: `<name>_feedback_gain(emphasis)` (k at a rotation 0..1, the circuit's law) and
        `<name>_response(frequencyHz, cutoffHz, emphasis, sampleRate)`, |small_signal_response| of this instance (its
        stages' capacitors, its oversampling and the halfband pair's response, its clamps), before the output coupling
        (templates/moog-transistor-ladder-response.template.js)."""
        from m4l_dev.generated_scripts import fill_template, kit_template_text
        character = self.character
        return fill_template(kit_template_text("moog-transistor-ladder-response.template.js"), {
            "NAME": self.instance_name,
            "REGENERATION_NUMERATOR": repr(regeneration_numerator(character)),
            "LOOP_OHMS": repr(character.regeneration_fixed_ohms + character.regeneration_trim_ohms),
            "POT_OHMS": repr(character.emphasis_pot_ohms),
            "TAPER_BASE": repr(emphasis_taper_base(character)),
            "LOWEST_CUTOFF_HZ": repr(LOWEST_CUTOFF_HZ),
            "HIGHEST_CUTOFF_OF_SAMPLE_RATE": repr(HIGHEST_CUTOFF_OF_SAMPLE_RATE),
            "OVERSAMPLING": str(self.oversampling),
            "STAGE_CAPACITANCE_RATIOS": "[" + ", ".join(repr(float(r)) for r in stage_capacitance_ratios(character)) + "]",
            "HALFBAND_COEFFICIENTS": "[" + ", ".join(repr(a) for a in halfband_coefficients()) + "]"},
            "moog-transistor-ladder-response.template.js")
