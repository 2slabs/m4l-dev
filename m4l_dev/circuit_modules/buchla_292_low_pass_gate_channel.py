"""The Buchla 292 low pass gate, one channel (a circuit module): the vactrol (an LED lighting a photocell, the
VTL5C3/2) and the audio network around the photocell, after Parker & D'Angelo, "A Digital Model of the Buchla
Lowpass-Gate", DAFx-13, with the measured VTL5C3/2 turn-off (Najnudel et al., DAFx-23)
(references/circuits/buchla-292-low-pass-gate.md).

The vactrol (§5). State: the effective LED current I (amps). The LED's drive current `led_current_amps` comes from
the channel's control circuit (a log-amp LED driver, held to [10.1 uA, 40 mA]: the character's floor and ceiling).
- Turn-on (drive > I): a one-pole toward the drive with time constant `attack_ms` (the cell's turn-on: 2.5-3 ms to 63 %
  at full drive, longer at reduced drive: catalog note 4; the instrument gives the time).
- Turn-off (drive <= I): dI/dt = -c (I^2 - drive^2), stepped semi-implicitly (stable, monotone, never past the
  drive). After a pulse 1/I grows linearly in time, so Rf = A (1/I0 + c t)^1.4 + B: the power law the measured
  VTL5C3/2 turn-off follows (within a factor of 1.06 with `decay_ms` 185 ms). `decay_ms` is the time a drive at the
  ceiling takes to reach DECAY_END_RESISTANCE (1 MOhm), c = RELEASE_SPAN / decay.
- The photocell: Rf = A I^-1.4 + B (DAFx-13 eq. 39, a fit to the VTL5C3/2; the character's fit), never darker than
  the floor's.

The network (§2): H(s) = 1 / (alpha1 + alpha2 s + alpha3 s^2), DAFx-13 eqs. 7-8 with Table 1's parts, one two-pole
branch for the three modes (`mode` 0 VCA: R alpha 5 kOhm and the mode's x1.6 input gain; 1 both: 5 MOhm; 2 lowpass:
5 MOhm, C3 4.7 nF in the feedback path and the feedback gain a from `resonance`, 0..1: a = 1 at 0, the character's
share of a_max (eq. 11, where it would ring) at 1). It runs on the kit's zero-delay state-variable filter (a technique)
at the natural frequency sqrt(alpha1 / alpha3) and Q sqrt(alpha1 alpha3) / alpha2, its low-pass x 1 / alpha1,
prewarped at the analog -3 dB corner (exact there), held at PREWARP_HIGHEST_HZ (Zavalishin's bounded prewarping,
eq. 3.21): VCA and both are overdamped, heard far below the natural frequency, which passes Nyquist at bright
drives. The construction checks that the lowpass mode at full `resonance` stays damped at every Rf the cell reaches.

Inputs: `input` (the audio, in its own units: the network is linear), `led_current_amps`, `attack_ms`, `decay_ms`,
`mode`, `resonance`. Outputs: `<name>_out` (the channel's output), `<name>_resistance_ohms` (Rf), `<name>_dc_gain`
(1 / alpha1) and `<name>_corner_hz` (the -3 dB corner: what a display draws). `reset_statements()` darkens the cell
and empties the network (a Stop).
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.zero_delay_state_variable_filter import ZeroDelayStateVariableFilter

# DAFx-13 Table 1
C1, C2, C3_LOWPASS = 1e-9, 220e-12, 4.7e-9
MODE_NAMES = ("vca", "both", "lowpass")                    # `mode` 0, 1, 2
R_ALPHA = {"vca": 5e3, "both": 5e6, "lowpass": 5e6}
VCA_MODE_INPUT_GAIN = 1.6                                  # the VCA mode's 4-5 dB of input gain (DAFx-13 §2)
PREWARP_HIGHEST_HZ = 16000.0                               # Zavalishin eq. 3.21: "some point around 16kHz"
DECAY_END_RESISTANCE = 1e6                                 # `decay_ms` is the time from the ceiling to here


@dataclasses.dataclass(frozen=True)
class Buchla292LowPassGateChannelCharacter:
    """One channel's build character; the defaults are DAFx-13's VTL5C3/2 and its control circuit."""
    photocell_fit_scale: float = 3.464                     # A, ohm amps^1.4 (DAFx-13 eq. 39)
    photocell_fit_floor_ohms: float = 1136.212             # B
    photocell_fit_exponent: float = 1.4
    led_current_floor_amps: float = 10.1e-6                # the driver's floor, the codebox's Ifmin (dark)
    led_current_ceiling_amps: float = 40e-3                # its ceiling, Ifmax: the VTL5C3/2's rated LED current
    highest_resonance_share_of_stable: float = 0.92        # `resonance` 1: a at this share of a_max [DESIGN]


def photocell_resistance(current, character):
    """Rf (ohms) at an effective LED current (amps), never darker than the driver's floor."""
    return (character.photocell_fit_scale * max(current, character.led_current_floor_amps)
            ** -character.photocell_fit_exponent + character.photocell_fit_floor_ohms)


def led_current_at_resistance(resistance, character):
    """The effective LED current (amps) at which the photocell is at `resistance` ohms (photocell_resistance's
    inverse)."""
    if resistance <= character.photocell_fit_floor_ohms:
        raise BuildError(f"Buchla 292: no LED current makes Rf {resistance} ohms (the fit's floor is "
                         f"{character.photocell_fit_floor_ohms})")
    return (character.photocell_fit_scale / (resistance - character.photocell_fit_floor_ohms)) ** (
        1 / character.photocell_fit_exponent)


def release_span(character):
    """c x decay (seconds): 1/I climbs from the ceiling's to DECAY_END_RESISTANCE's over the decay."""
    return 1 / led_current_at_resistance(DECAY_END_RESISTANCE, character) - 1 / character.led_current_ceiling_amps


def network_coefficients(rf, mode, resonance, character):
    """The network's (alpha1, alpha2, alpha3) at Rf in `mode` (0 VCA, 1 both, 2 lowpass), `resonance` 0..1 (lowpass
    only)."""
    mode_name = MODE_NAMES[mode]
    r_alpha = R_ALPHA[mode_name]
    c3 = C3_LOWPASS if mode_name == "lowpass" else 0.0
    feedback = 1.0
    if mode_name == "lowpass":
        a_max = (2 * C1 * r_alpha + (C2 + c3) * (r_alpha + rf)) / (c3 * r_alpha)
        feedback = 1 + resonance * (character.highest_resonance_share_of_stable * a_max - 1)
    alpha1 = 1 + 2 * rf / r_alpha
    alpha2 = rf * (2 * C1 + C2 - c3 * (feedback - 1) + (C2 + c3) * rf / r_alpha)
    alpha3 = rf * rf * C1 * (C2 + c3)
    return alpha1, alpha2, alpha3


def network_response(rf, mode, resonance, character):
    """(DC gain, -3 dB corner in Hz) of the network at Rf, as the module reads them out: the corner is where the
    analog response is 3 dB under its DC gain, in every mode (the cancellation-free root of |H|^2 = 1 / (2 alpha1^2))."""
    alpha1, alpha2, alpha3 = network_coefficients(rf, mode, resonance, character)
    squared_term = alpha2 * alpha2 - 2 * alpha1 * alpha3
    corner = math.sqrt(2 * alpha1 * alpha1 / (squared_term + math.sqrt(squared_term * squared_term
                                                                      + 4 * alpha1 * alpha1 * alpha3 * alpha3)))
    return 1 / alpha1, corner / (2 * math.pi)


def check_the_lowpass_mode_stays_damped(character):
    """At full resonance the lowpass mode's alpha2 must stay positive (a below a_max) at every Rf the cell reaches, or
    the network would ring on by itself. Fails the build otherwise."""
    for decade in range(3, 9):
        for step in (1.2, 2, 5):
            rf = step * 10 ** decade
            if network_coefficients(rf, MODE_NAMES.index("lowpass"), 1.0, character)[1] <= 0:
                raise BuildError(f"Buchla 292: the lowpass mode at full resonance is undamped at Rf {rf:g} ohms "
                                 f"(highest_resonance_share_of_stable {character.highest_resonance_share_of_stable})")


class Buchla292LowPassGateChannel(CircuitModule):
    """`<name>_out`: `input` through one 292 channel whose LED is driven at `led_current_amps`. See the module's
    docstring for every input and output."""

    references_entry = "references/circuits/buchla-292-low-pass-gate.md"
    character_type = Buchla292LowPassGateChannelCharacter

    def __init__(self, instance_name, *, input, led_current_amps, attack_ms, decay_ms, mode, resonance,
                 character=None):
        super().__init__(instance_name, character=character, input=input, led_current_amps=led_current_amps,
                         attack_ms=attack_ms, decay_ms=decay_ms, mode=mode, resonance=resonance)
        check_the_lowpass_mode_stays_damped(self.character)
        p = instance_name
        self.network = ZeroDelayStateVariableFilter(f"{p}_network", input=f"{p}_input", cutoff_hz=f"{p}_natural_hz",
                                                    q=f"{p}_q", prewarp_hz=f"{p}_prewarp_hz")

    def functions(self):
        return self.network.functions()

    def declarations(self):
        return self.substituted("History ${p}_current(${floor});\n",
                                floor=self.character.led_current_floor_amps) + self.network.declarations()

    def statements(self):
        character = self.character
        return self.substituted("""// ${p}: a Buchla 292 low pass gate channel (kit circuit module: Buchla 292 low pass gate channel)
${p}_input = ${input};
${p}_led_current = ${led_current_amps};
// the vactrol: its effective LED current, toward the drive (turn-on) or recombining (turn-off)
if (${p}_led_current > ${p}_current) {
	${p}_current = ${p}_current + (${p}_led_current - ${p}_current) * smoothing_coefficient(${attack_ms}, samplerate);
} else {
	${p}_release_step = ${release_span} / mstosamps(${decay_ms});
	${p}_current = (${p}_current + ${p}_release_step * ${p}_led_current * ${p}_led_current) / (1 + ${p}_release_step * ${p}_current);
}
${p}_resistance_ohms = ${fit_scale} * pow(max(${p}_current, ${floor}), -${fit_exponent}) + ${fit_floor};
// the network: H(s) = 1 / (alpha1 + alpha2 s + alpha3 s^2) in every mode
${p}_mode = ${mode};
${p}_r_alpha = ${p}_mode < 0.5 ? ${r_alpha_vca} : ${r_alpha_both};
${p}_c3 = ${p}_mode > 1.5 ? ${c3_lowpass} : 0;
${p}_feedback = 1;
if (${p}_mode > 1.5) {
	${p}_feedback_most = (2 * ${c1} * ${p}_r_alpha + (${c2} + ${p}_c3) * (${p}_r_alpha + ${p}_resistance_ohms)) / (${p}_c3 * ${p}_r_alpha);
	${p}_feedback = 1 + ${resonance} * (${resonance_share} * ${p}_feedback_most - 1);
}
${p}_alpha1 = 1 + 2 * ${p}_resistance_ohms / ${p}_r_alpha;
${p}_alpha2 = ${p}_resistance_ohms * (2 * ${c1} + ${c2} - ${p}_c3 * (${p}_feedback - 1) + (${c2} + ${p}_c3) * ${p}_resistance_ohms / ${p}_r_alpha);
${p}_alpha3 = ${p}_resistance_ohms * ${p}_resistance_ohms * ${c1} * (${c2} + ${p}_c3);
${p}_dc_gain = 1 / ${p}_alpha1;
${p}_natural_hz = sqrt(${p}_alpha1 / ${p}_alpha3) / 6.283185307;
${p}_q = sqrt(${p}_alpha1 * ${p}_alpha3) / ${p}_alpha2;
// the -3 dB corner: |H(jw)|^2 = 1 / (2 alpha1^2) at w^2 = 2 alpha1^2 / (b + sqrt(b^2 + 4 alpha1^2 alpha3^2)),
// b = alpha2^2 - 2 alpha1 alpha3 (the cancellation-free root); the network is prewarped there
${p}_corner_term = ${p}_alpha2 * ${p}_alpha2 - 2 * ${p}_alpha1 * ${p}_alpha3;
${p}_corner_hz = sqrt(2 * ${p}_alpha1 * ${p}_alpha1 / (${p}_corner_term + sqrt(${p}_corner_term * ${p}_corner_term + 4 * ${p}_alpha1 * ${p}_alpha1 * ${p}_alpha3 * ${p}_alpha3))) / 6.283185307;
${p}_prewarp_hz = min(${p}_corner_hz, ${prewarp_highest});
""", release_span=release_span(character), fit_scale=character.photocell_fit_scale,
            floor=character.led_current_floor_amps, fit_exponent=character.photocell_fit_exponent,
            fit_floor=character.photocell_fit_floor_ohms, r_alpha_vca=R_ALPHA["vca"], r_alpha_both=R_ALPHA["both"],
            c3_lowpass=C3_LOWPASS, c1=C1, c2=C2, resonance_share=character.highest_resonance_share_of_stable,
            prewarp_highest=PREWARP_HIGHEST_HZ) + self.network.statements() + self.substituted("""
${p}_out = ${p}_network_lowpass * ${p}_dc_gain * (${p}_mode < 0.5 ? ${vca_gain} : 1);""",
                                                                                   vca_gain=VCA_MODE_INPUT_GAIN)

    def reset_statements(self):
        """The cell dark and the network empty (a Stop)."""
        return self.substituted("${p}_current = ${floor};\n", floor=self.character.led_current_floor_amps) + \
            self.network.reset_statements()
