"""The LED-driven photocell (a technique): an LED's drive current to a CdS cell's resistance, with the cell's
asymmetric memory: quick to light, slow to go dark (references/dsp.md, "LED-driven photocell"). The physics of a
vactrol, a Bi-Phase "photo-mod", a Uni-Vibe's lamp-lit cells: no part is claimed here; the law's constants and the
times are the caller's (a circuit module's character).

State: the cell's effective LED current I (amps), starting dark (`darkest_current_amps`). The drive is the caller's
(a driver's current, >= 0); the resistance reads I no darker than `darkest_current_amps` (a driver's floor, the dark
end of the law), while I itself goes on falling undriven (the cell keeps darkening, catalog note 3).
- Light rising (drive Id > I): a one-pole toward Id with time constant `attack_ms` (2sl gate 0.3.2's vactrol attack).
- Light falling (Id <= I): dI/dt = -c (I^2 - Id^2), stepped semi-implicitly, I <- (I + c dt Id^2) / (1 + c dt I):
  unconditionally stable, monotone, never past Id. Released from I0 into the dark, 1/I = 1/I0 + c t, so with the law
  below R(t) = A (1/I0 + c t)^p + B: the power-law turn-off measured on a VTL5C3/2 (Najnudel et al., DAFx-23, Fig. 7a:
  R(t) = 3.4 kOhm (1 + t / 3 ms)^1.35 within +-5 % over 2-185 ms) with the law's own exponent. Faster when bright,
  slower the darker it gets, still rising after seconds (the cell catalog's notes 3 and 4).
- `release_ms` is the time the cell takes, released with no drive, from `release_from_amps` to `release_to_amps`:
  c = (1 / release_to - 1 / release_from) / release_ms.
- Resistance: R = A I^-p + B (Parker & D'Angelo, DAFx-13, eq. 39: A = 3.464, p = 1.4, B = 1136.2 Ohm fit to the
  VTL5C3/2); `law_scale_ohms` A (Ohm A^p), `law_exponent` p, `law_floor_ohms` B.

The drive, the attack and the release time are GenExpr inputs (a caller may move them: a hit's strength, a Decay
knob); the law and the release span are numbers fixed at build. Outputs: `<name>_current` (A), `<name>_resistance`
(Ohm). The Buchla 292 module's vactrol and the Mu-Tron Bi-Phase's cells are this block, each with its own constants.
"""
from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique


def _positive_number(instance_name, name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0:
        raise BuildError(f"LedDrivenPhotocell {instance_name}: {name} must be a number above 0, got {value!r}")
    return float(value)


class LedDrivenPhotocell(Technique):
    """`<name>_current`, `<name>_resistance`: the cell lit by `drive_current_amps`, rising with `attack_ms`, falling
    with `release_ms` (from `release_from_amps` to `release_to_amps`, no drive); R = law_scale_ohms I^-law_exponent
    + law_floor_ohms; I never below `darkest_current_amps`."""

    def __init__(self, instance_name, *, drive_current_amps, attack_ms, release_ms, law_scale_ohms, law_exponent,
                 law_floor_ohms, darkest_current_amps, release_from_amps, release_to_amps):
        super().__init__(instance_name, drive_current_amps=drive_current_amps, attack_ms=attack_ms,
                         release_ms=release_ms)
        self.law_scale_ohms = _positive_number(instance_name, "law_scale_ohms", law_scale_ohms)
        self.law_exponent = _positive_number(instance_name, "law_exponent", law_exponent)
        if isinstance(law_floor_ohms, bool) or not isinstance(law_floor_ohms, (int, float)) or law_floor_ohms < 0:
            raise BuildError(f"LedDrivenPhotocell {instance_name}: law_floor_ohms must be a number >= 0, "
                             f"got {law_floor_ohms!r}")
        self.law_floor_ohms = float(law_floor_ohms)
        self.darkest_current_amps = _positive_number(instance_name, "darkest_current_amps", darkest_current_amps)
        release_from_amps = _positive_number(instance_name, "release_from_amps", release_from_amps)
        release_to_amps = _positive_number(instance_name, "release_to_amps", release_to_amps)
        if not release_to_amps < release_from_amps:
            raise BuildError(f"LedDrivenPhotocell {instance_name}: the release span runs from a brighter current to a "
                             f"darker one, got {release_from_amps!r} A to {release_to_amps!r} A")
        self.release_span = 1 / release_to_amps - 1 / release_from_amps

    def declarations(self):
        return self.substituted("History ${p}_current(${dark});", dark=self.darkest_current_amps)

    def statements(self):
        return self.substituted("""// ${p}: LED-driven photocell (kit technique: LED-driven photocell)
${p}_drive = ${drive_current_amps};
// its effective LED current, toward the drive (turn-on) or recombining (turn-off)
if (${p}_drive > ${p}_current) {
	${p}_current = ${p}_current + (${p}_drive - ${p}_current) * smoothing_coefficient(${attack_ms}, samplerate);
} else {
	// dI/dt = -c (I^2 - Id^2), semi-implicit: stable, monotone, never past the drive
	${p}_release_step = ${span} / mstosamps(${release_ms});
	${p}_current = (${p}_current + ${p}_release_step * ${p}_drive * ${p}_drive) / (1 + ${p}_release_step * ${p}_current);
}
${p}_resistance = ${scale} * pow(max(${p}_current, ${dark}), -${exponent}) + ${floor};""",
                                dark=self.darkest_current_amps, span=self.release_span, scale=self.law_scale_ohms,
                                exponent=self.law_exponent, floor=self.law_floor_ohms)

    def reset_statements(self):
        """The cell dark."""
        return self.substituted("${p}_current = ${dark};\n", dark=self.darkest_current_amps)

    def resistance_at(self, current_amps):
        """The steady resistance (Ohm) at a constant drive."""
        return self.law_scale_ohms * max(current_amps, self.darkest_current_amps) ** -self.law_exponent \
            + self.law_floor_ohms
