"""The echo block: a stereo tape echo with filters, diffusion and saturation in its loop (references/dsp.md, "Echo").

What it promises (tests/test_dsp_blocks.py checks each):
- **On the grid.** Both sides loop at one time T (the glided Time). Each side's loop re-reads its tape at T - D, D
  being the loop's own delay (the diffusion allpasses' lengths, the loop low-pass's group delay at DC, the
  saturator's half sample), so every repeat lands at n T: the left output reads at T, the right at T + `right_lag_ms`
  (a fixed Haas offset that doesn't add up). Nothing compounds per round.
- **Tape glide.** Time glides like a tape's speed: a one-pole toward the new time (TIME_GLIDE_UP_MS longer,
  TIME_GLIDE_DOWN_MS shorter: the RE-201's ballistics, 1.89 s / 1.07 s, scaled down for a synced echo) whose step is
  limited to HIGHEST_TIME_CHANGE ms per ms, so the read head's speed stays in [0.5, 1.5]: never backwards.
- **Howl.** `feedback` is the loop's gain (small signals): above the loop filters' loss it self-oscillates, held at
  a bounded level by the saturator (tanh(g x) / g: |loop| <= 1 / `saturation_gain`).
- **Wow and flutter as pitch.** `wow_cents` is the RMS pitch deviation of the wow (noise low-passed at WOW_HZ, as the
  RE-201 study models drift); `flutter_cents` the RMS of a FLUTTER_HZ wobble. The delay moves by the integral of
  that pitch, so the pitch is the same at every Time.
- **Stop.** On `stop_pressed` (true for one sample), what is on the tape is from before: the old echo fades out over
  2 ms and nothing written before then is read again (a position, not a time, so a gliding read can't find it).
- **Rounds** (for a display): the peak of each of its last `rounds_kept` time rounds and of the round it is in.

Outputs: `<name>_left`, `<name>_right` (the repeats), `<name>_level` (a falling peak meter of both),
`<name>_round_peak_so_far`, `<name>_round_peak_1` .. `_<rounds_kept>` (newest first), `<name>_loop_samples` (T).
"""
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import GenBlock
from m4l_dev.gen_saturator import AntiderivativeTanhSaturator

# Live's highest sample rate (Ableton, Live editions: "Multitrack recording up to 32-bit/192 kHz"): the Delay sizes
# are fixed numbers of samples (gen's Delay takes a sample count), enough at 192 kHz.
HIGHEST_SAMPLE_RATE = 192000
TIME_GLIDE_UP_MS = 300.0
TIME_GLIDE_DOWN_MS = 200.0
HIGHEST_TIME_CHANGE = 0.5                # ms of delay per ms: read speed 1 -+ 0.5, i.e. -12 / +7 semitones at most
WOW_HZ = 1.0
FLUTTER_HZ = 6.5
HIGHEST_WOW_CENTS = 40.0                 # the inputs are clamped to these
HIGHEST_FLUTTER_CENTS = 15.0
WOBBLE_LIMIT_MS = 25.0                   # the delay's wow + flutter offset is clamped here (40 cents of wow is
                                         # 0.0231 / (2 pi 1 Hz) = 3.7 ms RMS: the limit is > 6 sigma)
DIFFUSION_ALLPASS_MS = {"left": (8.458, 13.311), "right": (9.093, 13.9)}   # 2sl stab's
LEVEL_METER_FALL_MS = 75.6
STOP_FADE_MS = 2.0
NATURAL_LOG_OF_2 = math.log(2.0)


class TapeEcho(GenBlock):
    """See the module docstring. Inputs are GenExpr expressions; `diffusion` (allpass gain, 0..0.7) is None for an
    echo without the allpasses. `initial_time_ms`, `longest_time_ms`, `right_lag_ms` and `rounds_kept` are numbers."""

    def __init__(self, instance_name, *, left_input, right_input, time_ms, feedback, loop_lowpass_hz,
                 loop_highpass_hz, saturation_gain, wow_cents, flutter_cents, stop_pressed, diffusion=None,
                 initial_time_ms, longest_time_ms, right_lag_ms, rounds_kept):
        inputs = dict(left_input=left_input, right_input=right_input, time_ms=time_ms, feedback=feedback,
                      loop_lowpass_hz=loop_lowpass_hz, loop_highpass_hz=loop_highpass_hz,
                      saturation_gain=saturation_gain, wow_cents=wow_cents, flutter_cents=flutter_cents,
                      stop_pressed=stop_pressed)
        if diffusion is not None:
            inputs["diffusion"] = diffusion
        super().__init__(instance_name, **inputs)
        self.has_diffusion = diffusion is not None
        if not 0 < initial_time_ms <= longest_time_ms:
            raise BuildError(f"TapeEcho {instance_name}: initial time {initial_time_ms} ms outside (0, {longest_time_ms}]")
        if right_lag_ms < 0 or rounds_kept < 0 or int(rounds_kept) != rounds_kept:
            raise BuildError(f"TapeEcho {instance_name}: right_lag_ms must be >= 0, rounds_kept a whole number >= 0")
        self.initial_time_ms = float(initial_time_ms)
        self.longest_time_ms = float(longest_time_ms)
        self.right_lag_ms = float(right_lag_ms)
        self.rounds_kept = int(rounds_kept)
        # the longest read: the longest time, the wobble's limit, the right side's lag, the spline's reach (3)
        self.tape_samples = int(math.ceil(HIGHEST_SAMPLE_RATE * (self.longest_time_ms + WOBBLE_LIMIT_MS
                                                                 + self.right_lag_ms) / 1000.0)) + 8
        self.diffusion_samples = int(math.ceil(HIGHEST_SAMPLE_RATE * max(max(v) for v in DIFFUSION_ALLPASS_MS.values())
                                               / 1000.0)) + 4
        self.saturators = {side: AntiderivativeTanhSaturator(
            f"{instance_name}_{side}_saturator",
            input=f"{instance_name}_{side}_filtered * {instance_name}_feedback * {instance_name}_saturation_gain")
            for side in ("left", "right")}

    def functions(self):
        functions = {}
        for saturator in self.saturators.values():
            functions.update(saturator.functions())
        return functions

    def declarations(self):
        lines = [self.substituted("Delay ${p}_left_tape(${size}, 2);\nDelay ${p}_right_tape(${size}, 2);",
                                  size=str(self.tape_samples))]
        if self.has_diffusion:
            for side in ("left", "right"):
                for number in (1, 2):
                    lines.append(self.substituted(f"Delay ${{p}}_{side}_diffuser_{number}(${{size}});",
                                                  size=str(self.diffusion_samples)))
        histories = ["${p}_time_ms(${initial})", "${p}_wow_1(0)", "${p}_wow_2(0)", "${p}_flutter_phase(0)",
                     "${p}_left_lowpass_1(0)", "${p}_left_lowpass_2(0)", "${p}_left_highpass(0)",
                     "${p}_right_lowpass_1(0)", "${p}_right_lowpass_2(0)", "${p}_right_highpass(0)",
                     "${p}_since_stop(1e9)", "${p}_stop_fade(0)", "${p}_level(0)",
                     "${p}_round_elapsed(0)", "${p}_round_peak_so_far(0)"]
        histories += [f"${{p}}_round_peak_{n}(0)" for n in range(1, self.rounds_kept + 1)]
        lines.append(self.substituted("History " + ", ".join(histories) + ";", initial=self.initial_time_ms))
        lines += [saturator.declarations() for saturator in self.saturators.values()]
        return "\n".join(lines)

    def statements(self):
        p = self.instance_name
        rounds = range(1, self.rounds_kept + 1)
        diffusion_delay = {"left": "0", "right": "0"}
        diffusion_code = {"left": "", "right": ""}
        diffuser_lengths = ""
        if self.has_diffusion:
            # The allpasses' lengths are whole samples (an allpass read between samples isn't an allpass: its
            # interpolation filters the loop inside it, and its repeats drift). They shrink, all in proportion,
            # when the loop is too short for them (under a quarter of it), so the loop re-read stays ahead.
            diffusion_delay = {side: " + ".join(f"{p}_{side}_diffuser_{number}_samples" for number in (1, 2))
                               for side in DIFFUSION_ALLPASS_MS}
            diffuser_lengths = "\n".join(
                f"{p}_{side}_diffuser_{number}_samples = max(1, floor({p}_diffuser_scale * mstosamps({length_ms!r}) + 0.5));"
                for side, lengths in DIFFUSION_ALLPASS_MS.items() for number, length_ms in enumerate(lengths, start=1))
            for side, lengths in DIFFUSION_ALLPASS_MS.items():
                code = []
                for number, length_ms in enumerate(lengths, start=1):
                    line = f"{p}_{side}_diffuser_{number}"
                    code.append(f"""{line}_read = {line}.read({line}_samples, interp="none");
{line}_in = {p}_{side}_filtered + {p}_diffusion * {line}_read;
{line}.write({line}_in * {p}_clean);
{p}_{side}_filtered = {line}_read - {p}_diffusion * {line}_in;""")
                diffusion_code[side] = "\n".join(code)
        clear_rounds = "".join(f"\n\t{p}_round_peak_{n} = 0;" for n in rounds)
        shift_rounds = "".join(f"\n\t{p}_round_peak_{n} = {p}_round_peak_{n - 1};" for n in reversed(rounds) if n > 1)
        if self.rounds_kept:
            shift_rounds += f"\n\t{p}_round_peak_1 = {p}_round_peak_so_far;"
        diffuser_scale = (f"min(1, {p}_steady_samples / (4 * mstosamps({max(sum(v) for v in DIFFUSION_ALLPASS_MS.values())!r})))"
                          if self.has_diffusion else "0")
        diffusion_amount = "clamp(${diffusion}, 0, 0.7)" if self.has_diffusion else "0"
        loop_upper_bound = self.tape_samples - 8 - math.ceil(HIGHEST_SAMPLE_RATE * self.right_lag_ms / 1000)
        reset_saturators = "\n\t".join(s.reset_statements().replace("\n", "\n\t") for s in self.saturators.values())
        code = f"""// {p}: tape echo (kit echo block)
// Stop: everything on the tape is from before it
if (${{stop_pressed}}) {{
	{p}_since_stop = 0;
	{p}_stop_fade = 1;
	{p}_round_elapsed = 0;
	{p}_round_peak_so_far = 0;{clear_rounds}
}}

// Time glides like a tape's speed, never past HIGHEST_TIME_CHANGE ms a ms: the read never runs backwards
{p}_target_ms = ${{time_ms}};
{p}_glide = ({p}_target_ms - {p}_time_ms) * smoothing_coefficient({p}_target_ms > {p}_time_ms ? {TIME_GLIDE_UP_MS!r} : {TIME_GLIDE_DOWN_MS!r}, samplerate);
{p}_time_ms = {p}_time_ms + clamp({p}_glide, -{HIGHEST_TIME_CHANGE!r} * 1000 / samplerate, {HIGHEST_TIME_CHANGE!r} * 1000 / samplerate);

// Wow and flutter, as pitch. The delay offset z (s) has pitch deviation dz/dt. Wow: z = sigma x (white noise
// through two one-poles at WOW_HZ, scaled to unit RMS), whose derivative's RMS is 2 pi WOW_HZ sigma. Flutter: a
// sine of peak sqrt 2 x its RMS pitch / (2 pi FLUTTER_HZ).
{p}_wow_pole = 1 - exp(-twopi * {WOW_HZ!r} / samplerate);
{p}_wow_1 = {p}_wow_1 + {p}_wow_pole * (noise() - {p}_wow_1);
{p}_wow_2 = {p}_wow_2 + {p}_wow_pole * ({p}_wow_1 - {p}_wow_2);
{p}_wow_pole_rest_2 = (1 - {p}_wow_pole) * (1 - {p}_wow_pole);
{p}_wow_unit = {p}_wow_2 / sqrt((1 / 3) * pow({p}_wow_pole, 4) * (1 + {p}_wow_pole_rest_2) / pow(1 - {p}_wow_pole_rest_2, 3));
{p}_wow_seconds = clamp(${{wow_cents}}, 0, {HIGHEST_WOW_CENTS!r}) * {NATURAL_LOG_OF_2 / 1200!r} / (twopi * {WOW_HZ!r}) * {p}_wow_unit;
{p}_flutter_phase = wrap({p}_flutter_phase + {FLUTTER_HZ!r} / samplerate, 0, 1);
{p}_flutter_seconds = clamp(${{flutter_cents}}, 0, {HIGHEST_FLUTTER_CENTS!r}) * {NATURAL_LOG_OF_2 / 1200 * math.sqrt(2) / (2 * math.pi * FLUTTER_HZ)!r} * sin(twopi * {p}_flutter_phase);
{p}_wobble_samples = clamp({p}_wow_seconds + {p}_flutter_seconds, -{WOBBLE_LIMIT_MS / 1000!r}, {WOBBLE_LIMIT_MS / 1000!r}) * samplerate;

// the loop's own delay D: re-reading the tape D early puts every repeat on n T
{p}_feedback = ${{feedback}};
{p}_saturation_gain = max(${{saturation_gain}}, 1);
{p}_steady_samples = mstosamps({p}_time_ms);
{p}_diffuser_scale = {diffuser_scale};
{p}_diffusion = {diffusion_amount};
{diffuser_lengths}
// the filters' group delay at the middle of the loop's band (f_mid = sqrt(f_low-pass f_high-pass)): two one-pole
// low-passes, 1 / (w_lp (1 + (f_mid / f_lp)^2)) each, and the one-pole high-pass, 1 / (w_hp (1 + (f_mid / f_hp)^2))
{p}_lowpass_hz = clamp(${{loop_lowpass_hz}}, 20, samplerate * 0.45);
{p}_highpass_hz = clamp(${{loop_highpass_hz}}, 1, samplerate * 0.45);
{p}_filters_delay = 2 * samplerate / (twopi * {p}_lowpass_hz * (1 + {p}_highpass_hz / {p}_lowpass_hz))
	+ samplerate / (twopi * {p}_highpass_hz * (1 + {p}_lowpass_hz / {p}_highpass_hz)) + {AntiderivativeTanhSaturator.LATENCY_SAMPLES!r};
{p}_lowpass_pole = 1 - exp(-twopi * {p}_lowpass_hz / samplerate);
{p}_highpass_pole = 1 - exp(-twopi * {p}_highpass_hz / samplerate);
{p}_left_loop_delay = {diffusion_delay["left"]} + {p}_filters_delay;
{p}_right_loop_delay = {diffusion_delay["right"]} + {p}_filters_delay;
{p}_loop_samples = clamp({p}_steady_samples + {p}_wobble_samples, max({p}_left_loop_delay, {p}_right_loop_delay) + 2, {loop_upper_bound});
{p}_right_lag_samples = mstosamps({self.right_lag_ms!r});

// Stop: `{p}_clean` is 0 where the longest read lands on audio from before Stop, rising to 1 over the 2 ms after
{p}_since_stop = min({p}_since_stop + 1, 1e9);
{p}_clean = clamp(({p}_since_stop - {p}_loop_samples - {p}_right_lag_samples - 3) / mstosamps({STOP_FADE_MS!r}), 0, 1);
{p}_stop_fade = max({p}_stop_fade - 1 / mstosamps({STOP_FADE_MS!r}), 0);
{p}_keep = max({p}_clean, {p}_stop_fade);
{p}_left = {p}_left_tape.read({p}_loop_samples, interp="spline") * {p}_keep;
{p}_right = {p}_right_tape.read({p}_loop_samples + {p}_right_lag_samples, interp="spline") * {p}_keep;
{p}_left_return = {p}_left_tape.read({p}_loop_samples - {p}_left_loop_delay, interp="spline") * {p}_keep;
{p}_right_return = {p}_right_tape.read({p}_loop_samples - {p}_right_loop_delay, interp="spline") * {p}_keep;
if ({p}_clean <= 0) {{
	{p}_left_lowpass_1 = 0;
	{p}_left_lowpass_2 = 0;
	{p}_left_highpass = 0;
	{p}_right_lowpass_1 = 0;
	{p}_right_lowpass_2 = 0;
	{p}_right_highpass = 0;
	{reset_saturators}
}}
"""
        for side in ("left", "right"):
            code += f"""
// {side}: low-pass (12 dB), high-pass (6 dB), diffusion (if any), saturation, back onto the tape
{p}_{side}_lowpass_1 = {p}_{side}_lowpass_1 + {p}_lowpass_pole * ({p}_{side}_return - {p}_{side}_lowpass_1);
{p}_{side}_lowpass_2 = {p}_{side}_lowpass_2 + {p}_lowpass_pole * ({p}_{side}_lowpass_1 - {p}_{side}_lowpass_2);
{p}_{side}_highpass = {p}_{side}_highpass + {p}_highpass_pole * ({p}_{side}_lowpass_2 - {p}_{side}_highpass);
{p}_{side}_filtered = {p}_{side}_lowpass_2 - {p}_{side}_highpass;
{diffusion_code[side]}
{self.saturators[side].statements()}
{p}_{side}_tape.write({self.input_expressions[side + "_input"]} + {p}_clean * {p}_{side}_saturator_out / {p}_saturation_gain);
"""
        code += f"""
// the meter and the rounds: what the loop really did, round by round (the 2 ms fade at Stop isn't counted)
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
