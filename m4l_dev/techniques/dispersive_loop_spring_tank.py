"""The dispersive-loop spring tank (a technique): a spring tank as one feedback loop per spring, each a delay read
at the spring's round trip, a loop low-pass for brightness, a DC blocker, a chain of first-order all-passes for the
dispersion and a tanh where the loop writes back (references/dsp.md, "Dispersive-loop spring tank").

2sl gate's spring (its `_spring_code`, gate's src/gate_dsp.py) is one setting of it: two springs of 33.7 and 41.3 ms,
eight all-passes of 0.62, the DC blocker at gate's corner, cleared for 60 ms. The kit's circuit module
`Buchla208SpringReverb` is that setting with the 208's driver in front; tests/test_circuit_module_buchla_208_spring_reverb.py
holds it to gate's own code.

Each spring's loop, every sample (`a` the all-pass coefficient, `n` the round trip in samples):
- read the spring's line `n` samples back (linear interpolation, as gate);
- a one-pole low-pass at `lowpass_hz` (y += k (x - y), k = 1 - exp(-2 pi f / sr)), then a one-pole DC blocker at
  `dc_block_hz` (the low-pass of it subtracted): this is the spring's output, `<name>_spring_<i>`;
- the loop gain g = 10^(-3 T / Length), T the round trip in seconds: -60 dB over `length_s`, counted on the loop's
  gain alone (the low-pass and the blocker take their own share on top, and the all-passes' delay, 8 x (1 - a) /
  (1 + a) samples at DC for gate's, is not taken out of the round trip: gate's isn't);
- the input plus g times the output, through `allpasses` first-order all-passes (a + z^-1) / (1 + a z^-1) (each
  delays the top of the band most: (1 + a) / (1 - a) samples at Nyquist against (1 - a) / (1 + a) at DC, so eight of
  0.62 spread an echo over 32 samples, 0.7 ms at 44.1 kHz: a dispersive comb, not a long chirp; the parametric
  spring reverb is the technique for that), then tanh, written to the line.

`clear`, true on a sample, starts a window of `clear_ms` (longer than the longest round trip, or the build fails) in
which nothing is read from or written to the lines and the blockers are held at 0, as gate's Stop does: after it the
lines hold only what came in after. The low-passes and the all-passes are not emptied (gate's aren't): they ring out
of what they held, into lines that are muted for the window.

Inputs: `input` (into every spring's loop), `lowpass_hz`, `length_s`, `clear`. Outputs: `<name>_spring_1` ..
`<name>_spring_<n>` (each spring's output, in the order of `round_trips_ms`), `<name>_clean` (0 inside the clear
window, 1 outside). No sample of latency: the springs are the wet, with no direct path through them.
"""
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.generated_numbers import generated_number

# Live's highest sample rate: the lines are sized for it (gen's Delay takes a fixed sample count).
HIGHEST_SAMPLE_RATE = 192000


class DispersiveLoopSpringTank(Technique):
    """See the module docstring. `round_trips_ms` (one per spring), `allpasses`, `allpass_coefficient`,
    `dc_block_hz` and `clear_ms` are numbers; the inputs are GenExpr expressions."""

    def __init__(self, instance_name, *, input, lowpass_hz, length_s, clear, round_trips_ms, allpasses,
                 allpass_coefficient, dc_block_hz, clear_ms):
        super().__init__(instance_name, input=input, lowpass_hz=lowpass_hz, length_s=length_s, clear=clear)
        self.latency_samples = 0       # a reverb's wet: its echoes come round the loops, nothing passes straight through
        self.round_trips_ms = tuple(float(value) for value in round_trips_ms)
        if not self.round_trips_ms or any(not value > 0 for value in self.round_trips_ms):
            raise BuildError(f"DispersiveLoopSpringTank {instance_name}: round_trips_ms must be one or more times "
                             f"above 0 ms, got {round_trips_ms!r}")
        if isinstance(allpasses, bool) or not isinstance(allpasses, int) or allpasses < 0:
            raise BuildError(f"DispersiveLoopSpringTank {instance_name}: allpasses must be a whole number >= 0, "
                             f"got {allpasses!r}")
        if not -1 < allpass_coefficient < 1:
            raise BuildError(f"DispersiveLoopSpringTank {instance_name}: the all-pass coefficient must be inside "
                             f"(-1, 1) to be stable, got {allpass_coefficient!r}")
        if not dc_block_hz > 0:
            raise BuildError(f"DispersiveLoopSpringTank {instance_name}: dc_block_hz must be above 0, got "
                             f"{dc_block_hz!r}")
        if not clear_ms > max(self.round_trips_ms):
            raise BuildError(f"DispersiveLoopSpringTank {instance_name}: the clear window ({clear_ms} ms) must be "
                             f"longer than the longest round trip ({max(self.round_trips_ms)} ms), or a line keeps "
                             "what came before it")
        self.allpasses = allpasses
        self.allpass_coefficient = allpass_coefficient
        self.dc_block_hz = dc_block_hz
        self.clear_ms = clear_ms
        self.line_samples = int(HIGHEST_SAMPLE_RATE * max(self.round_trips_ms) / 1000.0) + 4

    @property
    def springs(self):
        return range(1, len(self.round_trips_ms) + 1)

    def declarations(self):
        lines = [self.substituted(f"Delay ${{p}}_line_{i}(${{size}});", size=str(self.line_samples))
                 for i in self.springs]
        histories = ["${p}_clear_left(0)"]
        for i in self.springs:
            histories += [f"${{p}}_lowpass_{i}(0)", f"${{p}}_dc_{i}(0)"]
            histories += [f"${{p}}_allpass_{i}_{n}_in(0), ${{p}}_allpass_{i}_{n}_out(0)"
                          for n in range(1, self.allpasses + 1)]
        lines.append(self.substituted("History " + ", ".join(histories) + ";"))
        return "\n".join(lines)

    def statements(self):
        a = self.allpass_coefficient
        code = [self.substituted("""// ${p}: a dispersive loop per spring (kit technique: dispersive-loop spring tank)
// clear: a window longer than the longest loop with nothing read or written, so the lines hold only what comes after
if (${clear}) {
	${p}_clear_left = mstosamps(${clear_ms});
}
if (${p}_clear_left > 0) {
	${p}_clear_left = ${p}_clear_left - 1;
}
${p}_clean = ${p}_clear_left > 0 ? 0 : 1;
${p}_lowpass_k = 1 - exp(-6.283185307 * ${lowpass_hz} / samplerate);
${p}_dc_block_k = 1 - exp(-6.283185307 * ${dc_block_hz} / samplerate);""", clear_ms=self.clear_ms,
                                 dc_block_hz=self.dc_block_hz)]
        for i, round_trip_ms in zip(self.springs, self.round_trips_ms):
            s = f"{self.instance_name}_{i}"
            p = self.instance_name
            lines = [f"// spring {i}: {generated_number(round_trip_ms)!r} ms round trip",
                     f"{p}_read_{i} = {p}_line_{i}.read(mstosamps({generated_number(round_trip_ms)!r}), "
                     f"interp=\"linear\") * {p}_clean;",
                     f"{p}_lowpass_{i} = {p}_lowpass_{i} + {p}_lowpass_k * ({p}_read_{i} - {p}_lowpass_{i});",
                     f"{p}_dc_{i} = ({p}_dc_{i} + {p}_dc_block_k * ({p}_lowpass_{i} - {p}_dc_{i})) * {p}_clean;",
                     f"{p}_spring_{i} = {p}_lowpass_{i} - {p}_dc_{i};",
                     f"{p}_gain_{i} = pow(10, -3 * {generated_number(round_trip_ms / 1000)!r} / "
                     f"{self.input_expressions['length_s']});",
                     f"{s}_x0 = {self.input_expressions['input']} + {p}_spring_{i} * {p}_gain_{i};"]
            for n in range(1, self.allpasses + 1):
                before = f"{s}_x{n - 1}"
                lines += [f"{s}_x{n} = {a!r} * {before} + {p}_allpass_{i}_{n}_in - {a!r} * {p}_allpass_{i}_{n}_out;",
                          f"{p}_allpass_{i}_{n}_in = {before};",
                          f"{p}_allpass_{i}_{n}_out = {s}_x{n};"]
            lines.append(f"{p}_line_{i}.write(tanh({s}_x{self.allpasses}) * {p}_clean);")
            code.append("\n".join(lines))
        return "\n".join(code)


def allpass_chain_group_delay_samples(frequency_hz, sample_rate, allpasses, coefficient):
    """The all-pass chain's group delay in samples at `frequency_hz`: `allpasses` x (1 - a^2) / (1 + 2 a cos w + a^2)
    (Parker 2011 eq. 5, for one first-order section)."""
    w = 2 * math.pi * frequency_hz / sample_rate
    return allpasses * (1 - coefficient ** 2) / (1 + 2 * coefficient * math.cos(w) + coefficient ** 2)
