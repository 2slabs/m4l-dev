"""The multi-head tape echo (a technique): one stereo tape loop, written once at the record head and read by three
playback heads at fractions of its time, with the tape's own losses in the loop, all following a virtual tape speed
worked out from the time (references/dsp.md, "Multi-head tape echo"; its sources are 2sl dub's references/tape.md
and references/multihead.md).

A technique, not a circuit module: it models no machine. Its heads sit at exact fractions of the time unless the
device moves them; its losses are the formulas' shapes (spacing loss, the head bump) at a speed it picks, not a
measured machine's.

What it promises (tests/test_multi_head_tape_echo.py checks each):
- **Heads on the grid.** Head 3 reads at T (the glided time), heads 1 and 2 at `head_1` x T and `head_2` x T. What is
  heard is the heads weighted by `heard_1..3` (each 0..1, glided over HEAD_FADE_MS so a change crossfades and never
  clicks); what feeds back is the same heads. The loop re-reads each head D early, D being the loop's own delay (its
  filters' group delay in the middle of their band, the saturator's half sample, `insert_delay_samples`), so every
  repeat of every head lands on a sum of head times: on the grid when the heads are.
- **Dub the same on every head set.** The heads fed back are divided by their summed weight (at least 1), so the
  loop's gain at 0 Hz is `feedback` whichever heads are on (references/multihead.md §3: three heads would triple it).
- **Tape speed.** v = HEAD_3_DISTANCE_M / T, clamped to [LOWEST_SPEED, HIGHEST_SPEED] m/s: a longer time is slower
  tape. The losses and the flutter read v.
- **Losses in the loop, each round** (`tape` 1; at 0, clean, they open to nothing): spacing loss as two one-pole
  low-passes whose -3 dB point is spacing loss's (3 v / (54.6 d) Hz, references/tape.md §2.1, §2.4); the head bump, a
  bell of HEAD_BUMP_DB at v / BUMP_WAVELENGTH_M, and two one-pole high-passes an octave under it. `tone` (-1..1) is the
  tape's age: left, the spacing d grows to OLDEST_SPACING_M (darker each round); right, the bump shrinks and the low
  cut rises (thinner each round).
- **Hiss** (`hiss`, a level) written into the loop each round in front of the losses, so it builds with the feedback
  as tape hiss does (references/tape.md §5).
- **Wow and flutter.** `wow` (0..1) sets both: wow (noise under WOW_HZ) to WOW_CENTS_AT_FULL, flutter to
  FLUTTER_CENTS_AT_FULL, at v / (pi CAPSTAN_DIAMETER_M) with harmonics 2 and 3 at ChowTape's 230 : 80 : 99. Both are
  scaled by `tape` (none on clean).
- **Howl** held by the saturator, tanh(g x) / g, as the kit's tape-style echo.
- **Stop**, **rounds** and the **Time glide**: as TapeStyleEcho's.
- **Stereo** (`stereo_mode`: 0 stereo, 1 ping-pong, 2 heads, 3 mono; STEREO_MODES): stereo is two tapes side by side,
  the right heard `right_lag_ms` late. Ping-pong crosses them (the input into the left, each repeat onto the other).
  Heads gives each head a place, head 1 left, head 2 right, head 3 centre (both tapes then carry the inputs' mean).
  Mono: both tapes the mean, both outputs the same.
- **The device's processing in the loop** (always): it leaves what goes onto each tape in `<name>_left_into_tape` /
  `<name>_right_into_tape`; a MultiHeadTapeEchoTapeWriter writes what the device made of it.

Outputs: `<name>_left`, `<name>_right`, `<name>_level`, `<name>_round_peak_so_far`, `<name>_round_peak_1..`,
`<name>_loop_samples` (T), `<name>_speed` (m/s), `<name>_left_into_tape`, `<name>_right_into_tape`.
"""
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.generated_numbers import generated_number
from m4l_dev.techniques.antiderivative_tanh_saturator import AntiderivativeTanhSaturator
from m4l_dev.techniques.histories_start_at_their_targets import HistoriesStartAtTheirTargets
from m4l_dev.techniques.tape_style_echo import (HIGHEST_SAMPLE_RATE, HIGHEST_TIME_CHANGE, LEVEL_METER_FALL_MS,
                                                STOP_FADE_MS, TIME_GLIDE_DOWN_MS, TIME_GLIDE_UP_MS)

STEREO_MODES = ("stereo", "ping-pong", "heads", "mono")
HEADS = 3
HEAD_FADE_MS = 6.0                       # a change of heads crossfades over this (Shift: no glide, no click)
HEAD_GLIDE_MS = 120.0                    # heads 1 and 2 moving (Spacing): they glide, as a head being moved would
STEREO_MODE_GLIDE_MS = 50.0
# The virtual tape (references/tape.md §2.3, design 1): record head to head 3. 5.5 cm puts 1/8d at 120 BPM (375 ms) at
# 14.7 cm/s, the middle of the bracket the references give an RE-201 (7.5-30 cm/s)
HEAD_3_DISTANCE_M = 0.055
LOWEST_SPEED = 0.05
HIGHEST_SPEED = 0.40
# spacing loss: -3 dB at 3 v / (54.6 d) Hz (54.6 d / lambda dB; references/tape.md §2.1); two one-poles reach -3 dB
# at 0.642 of their corner (20 log10(1 + x^2) = 3: x^2 = 0.4125)
SPACING_M = 3.0e-6
OLDEST_SPACING_M = 10.0e-6
TWO_POLE_THREE_DB_RATIO = 0.642
# the head bump (references/tape.md §2.2): about +2 to +3 dB at v / 4 mm, the roll-off an octave under it
HEAD_BUMP_DB = 2.5
BUMP_WAVELENGTH_M = 0.004
BUMP_Q = 2.0
CLEAN_LOWCUT_HZ = 5.0                   # clean: only a DC guard
CLEAN_BAND_TOP_HZ = 20000.0             # clean: the band whose middle the loop's delay is taken at
THINNEST_LOWCUT_OCTAVES = 4.0           # Tone +1 moves the low cut up 4 octaves (about 18 Hz to 300 Hz at 1/8d)
THINNEST_BUMP_SHARE = 0.2               # and keeps a fifth of the bump
# wow and flutter (references/tape.md §4): a real machine stays under ~10 cents; the flutter follows speed
WOW_HZ = 1.0
WOW_CENTS_AT_FULL = 8.0
FLUTTER_CENTS_AT_FULL = 3.0
CAPSTAN_DIAMETER_M = 0.005
FLUTTER_HARMONICS = (230.0, 80.0, 99.0)  # ChowTape's TC-260 measurement, f, 2f, 3f (references/tape.md §4)
FLUTTER_PHASES = (0.0, 0.6, 1.3)
WOBBLE_LIMIT_MS = 10.0
NATURAL_LOG_OF_2 = math.log(2.0)


class MultiHeadTapeEcho(Technique):
    """See the module docstring. Inputs are GenExpr expressions; `longest_time_ms`, `right_lag_ms` and `rounds_kept`
    are numbers."""

    def __init__(self, instance_name, *, left_input, right_input, time_ms, head_1, head_2, heard_1, heard_2, heard_3,
                 feedback, saturation_gain, tape, tone, wow, hiss, stereo_mode, stop_pressed, insert_delay_samples,
                 longest_time_ms, right_lag_ms, rounds_kept):
        super().__init__(instance_name, left_input=left_input, right_input=right_input, time_ms=time_ms,
                         head_1=head_1, head_2=head_2, heard_1=heard_1, heard_2=heard_2, heard_3=heard_3,
                         feedback=feedback, saturation_gain=saturation_gain, tape=tape, tone=tone, wow=wow, hiss=hiss,
                         stereo_mode=stereo_mode, stop_pressed=stop_pressed,
                         insert_delay_samples=insert_delay_samples)
        self.latency_samples = 0       # the repeats land on sums of head times: the loop's own delays are taken out
        if not longest_time_ms > 0:
            raise BuildError(f"MultiHeadTapeEcho {instance_name}: longest time {longest_time_ms} ms must be > 0")
        if right_lag_ms < 0 or rounds_kept < 0 or int(rounds_kept) != rounds_kept:
            raise BuildError(f"MultiHeadTapeEcho {instance_name}: right_lag_ms must be >= 0, rounds_kept a whole "
                             "number >= 0")
        self.longest_time_ms = float(longest_time_ms)
        self.right_lag_ms = generated_number(float(right_lag_ms))
        self.rounds_kept = int(rounds_kept)
        self.tape_samples = int(math.ceil(HIGHEST_SAMPLE_RATE * (self.longest_time_ms + WOBBLE_LIMIT_MS
                                                                 + self.right_lag_ms) / 1000.0)) + 8
        self.saturators = {side: AntiderivativeTanhSaturator(
            f"{instance_name}_{side}_saturator",
            input=f"{instance_name}_{side}_filtered * {instance_name}_loop_gain * {instance_name}_saturation_gain",
            oversampling=1)
            for side in ("left", "right")}
        self.starts_at_targets = HistoriesStartAtTheirTargets(
            f"{instance_name}_start", targets={f"{instance_name}_time_ms": time_ms,
                                               f"{instance_name}_head_1": f"clamp({head_1}, 0.02, 0.98)",
                                               f"{instance_name}_head_2": f"clamp({head_2}, 0.02, 0.98)",
                                               f"{instance_name}_heard_1": heard_1,
                                               f"{instance_name}_heard_2": heard_2,
                                               f"{instance_name}_heard_3": heard_3,
                                               f"{instance_name}_tape": tape})

    def functions(self):
        functions = {}
        for saturator in self.saturators.values():
            functions.update(saturator.functions())
        return functions

    def declarations(self):
        p = self.instance_name
        reads = 2 * HEADS
        lines = [f"Delay {p}_left_tape({self.tape_samples}, {reads});",
                 f"Delay {p}_right_tape({self.tape_samples}, {reads});"]
        histories = [f"{p}_time_ms(0)", f"{p}_head_1(0)", f"{p}_head_2(0)", f"{p}_heard_1(0)", f"{p}_heard_2(0)",
                     f"{p}_heard_3(0)", f"{p}_tape(0)", f"{p}_cross(0)", f"{p}_pan(0)", f"{p}_mono(0)",
                     f"{p}_wow_1(0)", f"{p}_wow_2(0)", f"{p}_flutter_phase(0)",
                     f"{p}_since_stop(1e9)", f"{p}_stop_fade(0)", f"{p}_level(0)",
                     f"{p}_round_elapsed(0)", f"{p}_round_peak_so_far(0)"]
        for side in ("left", "right"):
            histories += [f"{p}_{side}_{name}(0)" for name in ("lowpass_1", "lowpass_2", "lowcut_1", "lowcut_2",
                                                               "bump_1", "bump_2")]
        histories += [f"{p}_round_peak_{n}(0)" for n in range(1, self.rounds_kept + 1)]
        lines.append("History " + ", ".join(histories) + ";")
        lines.append(self.starts_at_targets.declarations())
        lines += [saturator.declarations() for saturator in self.saturators.values()]
        return "\n".join(lines)

    def statements(self):
        p = self.instance_name
        rounds = range(1, self.rounds_kept + 1)
        clear_rounds = "".join(f"\n\t{p}_round_peak_{n} = 0;" for n in rounds)
        shift_rounds = "".join(f"\n\t{p}_round_peak_{n} = {p}_round_peak_{n - 1};" for n in reversed(rounds) if n > 1)
        if self.rounds_kept:
            shift_rounds += f"\n\t{p}_round_peak_1 = {p}_round_peak_so_far;"
        reset_saturators = "\n\t".join(s.reset_statements().replace("\n", "\n\t") for s in self.saturators.values())
        reset_filters = "\n\t".join(f"{p}_{side}_{name} = 0;" for side in ("left", "right")
                                    for name in ("lowpass_1", "lowpass_2", "lowcut_1", "lowcut_2", "bump_1", "bump_2"))
        loop_upper_bound = self.tape_samples - 8 - math.ceil(HIGHEST_SAMPLE_RATE * self.right_lag_ms / 1000)
        saturator_latency = repr(generated_number(self.saturators["left"].latency_samples))
        harmonics_rms = math.sqrt(sum(a * a for a in FLUTTER_HARMONICS) / 2)
        flutter_terms = " + ".join(
            f"{generated_number(a / harmonics_rms / h)!r} * sin({h} * twopi * {p}_flutter_phase + {phase!r})"
            for h, (a, phase) in enumerate(zip(FLUTTER_HARMONICS, FLUTTER_PHASES), start=1))
        heads = range(1, HEADS + 1)
        head_position = {1: f"{p}_head_1 * {p}_steady_samples", 2: f"{p}_head_2 * {p}_steady_samples",
                         3: f"{p}_steady_samples"}
        reads = []
        for head in heads:
            for side, tape_side, lag in (("left", "left", ""), ("right", "right", f" + {p}_right_lag_samples")):
                reads.append(f"{p}_{side}_head_{head} = {p}_{tape_side}_tape.read(clamp({head_position[head]} + "
                             f"{p}_wobble_samples{lag} - {p}_insert, 1, {loop_upper_bound}), interp=\"spline\") * {p}_keep;")
                reads.append(f"{p}_{side}_return_{head} = {p}_{tape_side}_tape.read(clamp({head_position[head]} + "
                             f"{p}_wobble_samples - {p}_loop_delay, 1, {loop_upper_bound}), interp=\"spline\") * {p}_keep;")
        reads = "\n".join(reads)
        heard = {side: " + ".join(f"{p}_heard_{head} * {p}_{side}_head_{head}" for head in heads)
                 for side in ("left", "right")}
        returned = {side: " + ".join(f"{p}_heard_{head} * {p}_{side}_return_{head}" for head in heads)
                    for side in ("left", "right")}
        code = f"""// {p}: multi-head tape echo (kit technique)
// Stop: everything on the tape is from before it
if (${{stop_pressed}}) {{
	{p}_since_stop = 0;
	{p}_stop_fade = 1;
	{p}_round_elapsed = 0;
	{p}_round_peak_so_far = 0;{clear_rounds}
}}

// Time and the heads start at their targets, then glide: Time like tape speed (never past HIGHEST_TIME_CHANGE ms a
// ms), heads 1 and 2 as moved heads, the heads heard crossfading, Echo Type's tape share gliding
{self.starts_at_targets.statements()}
{p}_target_ms = ${{time_ms}};
{p}_glide = ({p}_target_ms - {p}_time_ms) * smoothing_coefficient({p}_target_ms > {p}_time_ms ? {TIME_GLIDE_UP_MS!r} : {TIME_GLIDE_DOWN_MS!r}, samplerate);
{p}_time_ms = {p}_time_ms + clamp({p}_glide, -{HIGHEST_TIME_CHANGE!r} * 1000 / samplerate, {HIGHEST_TIME_CHANGE!r} * 1000 / samplerate);
{p}_head_glide = smoothing_coefficient({HEAD_GLIDE_MS!r}, samplerate);
{p}_head_1 = {p}_head_1 + {p}_head_glide * (clamp(${{head_1}}, 0.02, 0.98) - {p}_head_1);
{p}_head_2 = {p}_head_2 + {p}_head_glide * (clamp(${{head_2}}, 0.02, 0.98) - {p}_head_2);
{p}_fade = smoothing_coefficient({HEAD_FADE_MS!r}, samplerate);
{p}_heard_1 = {p}_heard_1 + {p}_fade * (clamp(${{heard_1}}, 0, 1) - {p}_heard_1);
{p}_heard_2 = {p}_heard_2 + {p}_fade * (clamp(${{heard_2}}, 0, 1) - {p}_heard_2);
{p}_heard_3 = {p}_heard_3 + {p}_fade * (clamp(${{heard_3}}, 0, 1) - {p}_heard_3);
{p}_heads_on = max({p}_heard_1 + {p}_heard_2 + {p}_heard_3, 1);
{p}_mode_glide = smoothing_coefficient({STEREO_MODE_GLIDE_MS!r}, samplerate);
{p}_tape = {p}_tape + {p}_mode_glide * (clamp(${{tape}}, 0, 1) - {p}_tape);
{p}_cross = {p}_cross + {p}_mode_glide * ((${{stereo_mode}} == 1) - {p}_cross);
{p}_pan = {p}_pan + {p}_mode_glide * ((${{stereo_mode}} == 2) - {p}_pan);
{p}_mono = {p}_mono + {p}_mode_glide * ((${{stereo_mode}} == 3) - {p}_mono);

// the tape's speed, from Time (head 3): slower tape for a longer echo
{p}_speed = clamp({HEAD_3_DISTANCE_M!r} / max({p}_time_ms * 0.001, 0.001), {LOWEST_SPEED!r}, {HIGHEST_SPEED!r});

// Wow (noise under WOW_HZ, unit RMS) and flutter (the capstan's turn and two harmonics), both as pitch, both off on
// clean. Each moves the read by the integral of its pitch, so the pitch is the same at every time.
{p}_wow_pole = 1 - exp(-twopi * {WOW_HZ!r} / samplerate);
{p}_wow_1 = {p}_wow_1 + {p}_wow_pole * (noise() - {p}_wow_1);
{p}_wow_2 = {p}_wow_2 + {p}_wow_pole * ({p}_wow_1 - {p}_wow_2);
{p}_wow_pole_rest_2 = (1 - {p}_wow_pole) * (1 - {p}_wow_pole);
{p}_wow_unit = {p}_wow_2 / sqrt((1 / 3) * pow({p}_wow_pole, 4) * (1 + {p}_wow_pole_rest_2) / pow(1 - {p}_wow_pole_rest_2, 3));
{p}_wobble_amount = clamp(${{wow}}, 0, 1) * {p}_tape * {generated_number(NATURAL_LOG_OF_2 / 1200)!r};
{p}_wow_seconds = {p}_wobble_amount * {WOW_CENTS_AT_FULL!r} / (twopi * {WOW_HZ!r}) * {p}_wow_unit;
{p}_flutter_hz = {p}_speed / {generated_number(math.pi * CAPSTAN_DIAMETER_M)!r};
{p}_flutter_phase = wrap({p}_flutter_phase + {p}_flutter_hz / samplerate, 0, 1);
{p}_flutter_seconds = {p}_wobble_amount * {FLUTTER_CENTS_AT_FULL!r} / (twopi * {p}_flutter_hz) * ({flutter_terms});
{p}_wobble_samples = clamp({p}_wow_seconds + {p}_flutter_seconds, -{WOBBLE_LIMIT_MS / 1000!r}, {WOBBLE_LIMIT_MS / 1000!r}) * samplerate;

// the tape's losses at this speed (tape share 1; at 0 they open): spacing loss's -3 dB point, the bump, the low cut
{p}_age = clamp(${{tone}}, -1, 1);
{p}_spacing = {SPACING_M!r} * pow({generated_number(OLDEST_SPACING_M / SPACING_M)!r}, max(-{p}_age, 0));
{p}_spacing_hz = 3 * {p}_speed / ({generated_number(54.6)!r} * {p}_spacing) / {TWO_POLE_THREE_DB_RATIO!r};
{p}_lowpass_hz = clamp({p}_spacing_hz, 200, samplerate * 0.45);
{p}_bump_hz = {p}_speed / {BUMP_WAVELENGTH_M!r};
{p}_lowcut_hz = clamp({p}_bump_hz * 0.5 * pow(2, {THINNEST_LOWCUT_OCTAVES!r} * max({p}_age, 0)) * {p}_tape
	+ {CLEAN_LOWCUT_HZ!r} * (1 - {p}_tape), 5, 2000);
{p}_bump_gain = dbtoa({HEAD_BUMP_DB!r} * (1 - {generated_number(1 - THINNEST_BUMP_SHARE)!r} * max({p}_age, 0)) * {p}_tape) - 1;
// clean: the low-passes open all the way (their pole 1: no filter, no delay)
{p}_lowpass_pole = 1 - exp(-twopi * {p}_lowpass_hz / samplerate) * {p}_tape;
{p}_lowcut_pole = 1 - exp(-twopi * {p}_lowcut_hz / samplerate);
{p}_bump_g = tan(pi * min({p}_bump_hz, samplerate * 0.45) / samplerate);
{p}_bump_k = 1 / {BUMP_Q!r};
{p}_bump_a1 = 1 / (1 + {p}_bump_g * ({p}_bump_g + {p}_bump_k));
{p}_bump_a2 = {p}_bump_g * {p}_bump_a1;
{p}_bump_a3 = {p}_bump_g * {p}_bump_a2;
// the loop's own delay D: two low-passes and two low cuts' group delay in the middle of the band, the saturator's,
// the device's processing. Re-reading every head D early puts each repeat on its head's time.
{p}_middle_hz = sqrt(({p}_lowpass_hz * {p}_tape + {CLEAN_BAND_TOP_HZ!r} * (1 - {p}_tape)) * {p}_lowcut_hz);
{p}_insert = max(${{insert_delay_samples}}, 0);
{p}_loop_delay = {p}_tape * 2 * samplerate / (twopi * {p}_lowpass_hz * (1 + ({p}_middle_hz / {p}_lowpass_hz) * ({p}_middle_hz / {p}_lowpass_hz)))
	+ 2 * samplerate / (twopi * {p}_lowcut_hz * (1 + ({p}_middle_hz / {p}_lowcut_hz) * ({p}_middle_hz / {p}_lowcut_hz)))
	+ {saturator_latency} + {p}_insert;
{p}_steady_samples = clamp(mstosamps({p}_time_ms), {p}_loop_delay + 2, {loop_upper_bound} - 16);
{p}_loop_samples = {p}_steady_samples;
{p}_right_lag_samples = mstosamps({self.right_lag_ms!r}) * max(1 - {p}_cross - {p}_pan - {p}_mono, 0);
{p}_feedback = ${{feedback}};
{p}_loop_gain = {p}_feedback / {p}_heads_on;
{p}_saturation_gain = max(${{saturation_gain}}, 1);

// Stop: `{p}_clean` is 0 where the longest read lands on audio from before Stop, rising to 1 over the 2 ms after
{p}_since_stop = min({p}_since_stop + 1, 1e9);
{p}_clean = clamp(({p}_since_stop - {p}_steady_samples - mstosamps({WOBBLE_LIMIT_MS!r}) - {p}_right_lag_samples - 3) / mstosamps({STOP_FADE_MS!r}), 0, 1);
{p}_stop_fade = max({p}_stop_fade - 1 / mstosamps({STOP_FADE_MS!r}), 0);
{p}_keep = max({p}_clean, {p}_stop_fade);
if ({p}_clean <= 0) {{
	{reset_filters}
	{reset_saturators}
}}

// the heads: each read where it is heard (the device's processing taken out) and D early for the loop
{reads}
"""
        for side in ("left", "right"):
            code += f"""
// {side}: the heads fed back, hiss, the tape's losses (spacing, low cut, bump), saturation
{p}_{side}_return = ({returned[side]}) + ${{hiss}} * {p}_tape * noise();
{p}_{side}_lowpass_1 = {p}_{side}_lowpass_1 + {p}_lowpass_pole * ({p}_{side}_return - {p}_{side}_lowpass_1);
{p}_{side}_lowpass_2 = {p}_{side}_lowpass_2 + {p}_lowpass_pole * ({p}_{side}_lowpass_1 - {p}_{side}_lowpass_2);
{p}_{side}_lowcut_1 = {p}_{side}_lowcut_1 + {p}_lowcut_pole * ({p}_{side}_lowpass_2 - {p}_{side}_lowcut_1);
{p}_{side}_cut_1 = {p}_{side}_lowpass_2 - {p}_{side}_lowcut_1;
{p}_{side}_lowcut_2 = {p}_{side}_lowcut_2 + {p}_lowcut_pole * ({p}_{side}_cut_1 - {p}_{side}_lowcut_2);
{p}_{side}_cut_2 = {p}_{side}_cut_1 - {p}_{side}_lowcut_2;
{p}_{side}_bump_v3 = {p}_{side}_cut_2 - {p}_{side}_bump_2;
{p}_{side}_bump_v1 = {p}_bump_a1 * {p}_{side}_bump_1 + {p}_bump_a2 * {p}_{side}_bump_v3;
{p}_{side}_bump_v2 = {p}_{side}_bump_2 + {p}_bump_a2 * {p}_{side}_bump_1 + {p}_bump_a3 * {p}_{side}_bump_v3;
{p}_{side}_bump_1 = 2 * {p}_{side}_bump_v1 - {p}_{side}_bump_1;
{p}_{side}_bump_2 = 2 * {p}_{side}_bump_v2 - {p}_{side}_bump_2;
{p}_{side}_filtered = {p}_{side}_cut_2 + {p}_bump_gain * {p}_bump_k * {p}_{side}_bump_v1;
{self.saturators[side].statements()}
{p}_{side}_fed = {p}_{side}_saturator_out / {p}_saturation_gain;
"""
        code += f"""
// what goes onto each tape: stereo side by side; ping-pong crosses (the inputs into the left); heads and mono put the
// inputs' mean on both
{p}_left_sent = ${{left_input}};
{p}_right_sent = ${{right_input}};
{p}_both_sent = 0.5 * ({p}_left_sent + {p}_right_sent);
{p}_shared = min({p}_mono + {p}_pan, 1);
{p}_left_into_tape = (1 - {p}_shared) * ({p}_left_sent + {p}_cross * {p}_right_sent) + {p}_shared * {p}_both_sent
	+ {p}_clean * ((1 - {p}_cross) * {p}_left_fed + {p}_cross * {p}_right_fed);
{p}_right_into_tape = (1 - {p}_shared) * (1 - {p}_cross) * {p}_right_sent + {p}_shared * {p}_both_sent
	+ {p}_clean * ((1 - {p}_cross) * {p}_right_fed + {p}_cross * {p}_left_fed);

// what is heard: the heads, their sum held near one head's level; heads mode places them (1 left, 2 right, 3 centre);
// mono gives both sides their mean
{p}_heard_scale = 1 / sqrt({p}_heads_on);
{p}_left_plain = {heard["left"]};
{p}_right_plain = {heard["right"]};
{p}_left_placed = {p}_heard_1 * {p}_left_head_1 + {generated_number(math.sqrt(0.5))!r} * {p}_heard_3 * {p}_left_head_3;
{p}_right_placed = {p}_heard_2 * {p}_right_head_2 + {generated_number(math.sqrt(0.5))!r} * {p}_heard_3 * {p}_right_head_3;
{p}_left = {p}_heard_scale * ({p}_left_plain + {p}_pan * ({p}_left_placed - {p}_left_plain));
{p}_right = {p}_heard_scale * ({p}_right_plain + {p}_pan * ({p}_right_placed - {p}_right_plain));
{p}_left_heard = {p}_left;
{p}_left = {p}_left + 0.5 * {p}_mono * ({p}_right - {p}_left);
{p}_right = {p}_right + 0.5 * {p}_mono * ({p}_left_heard - {p}_right);

// the meter and the rounds (a round is Time, head 3's)
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


class MultiHeadTapeEchoTapeWriter(Technique):
    """Writes a MultiHeadTapeEcho's tapes: `left` and `right` are what the device made of `<echo>_left_into_tape`
    and `<echo>_right_into_tape`. Its marker goes after that processing. No outputs."""

    def __init__(self, echo, *, left, right):
        if not isinstance(echo, MultiHeadTapeEcho):
            raise BuildError("MultiHeadTapeEchoTapeWriter: it writes the tapes of a MultiHeadTapeEcho")
        super().__init__(f"{echo.instance_name}_tape_writer", left=left, right=right)
        self.echo_name = echo.instance_name
        self.latency_samples = 0

    def statements(self):
        return self.substituted(f"""// {self.echo_name}'s tapes: what the device made of what goes onto them
{self.echo_name}_left_tape.write(${{left}});
{self.echo_name}_right_tape.write(${{right}});""")
