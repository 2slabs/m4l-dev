"""The drum envelope (a technique): a hit's amplitude envelope, attack then decay, in three modes: exponential,
linear ("gated") and clap burst (references/dsp.md, "Drum envelope"). Microtonic's oscillator and noise envelopes
(Sonic Charge, Microtonic User Guide v3.3.4, pp. 18-20) are the laws it follows where the guide gives them.

Modes (`mode`, read at the hit and held until the next one):
- 0 exponential: the attack is the decay reversed in time (MT-UG p. 18: the attack "is always exponential" and
  "suggests a sound that has been reversed in time"): level = rise(progress), rise(u) = (exp(-a (1 - u)) - f) /
  (1 - f), f = exp(-a), slow at first, fastest at the top. The decay is a true exponential from 1 (MT-UG p. 18: "an
  exponential decay never reaches zero ... the time setting is only an approximate"): it falls by DECAY_SPAN_DB over
  `decay_ms`, and is called silent (0, the envelope idle) under SILENT_LEVEL. The curvature a = ln(1000) (60 dB) and
  the 60 dB that `decay_ms` spans are ours: the guide gives neither [UNVERIFIED].
- 1 linear: a straight attack from the level at the hit to 1 over `attack_ms`, a straight decay from 1 to 0 over
  `decay_ms` (MT-UG p. 19: "The Linear Mode creates a more conventional attack, but its decay acquires a 'gated'
  effect").
- 2 clap burst: `clap_burst_count` pulses `clap_burst_spacing_ms` apart, each an instant jump to 1 that decays
  exponentially (as mode 0) over one spacing; the last pulse decays over `decay_ms`. MT-UG p. 19 says only that the
  mode "works by retriggering the envelope in rapid successions before going into the decay phase" and that its
  attack sets "the time until the decay phase by changing the number of triggers and the time between them": the
  count and the spacing are the caller's here, and the pulse shape is ours [UNVERIFIED: no source gives the law].

A hit (`hit` true for one sample) restarts the envelope from where it is: the attack starts at the present level (the
inverse of the attack curve finds its progress), so a restart never drops the level, and with an attack above zero
the level is continuous through it. `attack_ms` 0 jumps to 1 at the hit (MT-UG p. 18: "the oscillator triggers at
full force directly. This causes a sharp transient with a distinct clicking sound"): that jump is the drum's own,
not the restart's.
"""
import math

from m4l_dev.gen_blocks import Technique
from m4l_dev.generated_numbers import generated_number

ATTACK_CURVATURE = generated_number(math.log(1000.0))    # a: the exponential attack spans 60 dB of exp(-a (1 - u)) [UNVERIFIED]
DECAY_SPAN_DB = 60.0                   # the exponential decay falls this far over decay_ms [UNVERIFIED]
SILENT_LEVEL = 1e-6                    # -120 dB: under it the exponential decay ends (the envelope is idle)
SHORTEST_TIME_MS = 0.1                 # decay and spacing times are held above this (a step a sample at most)
MODES = {"exponential": 0, "linear": 1, "clap_burst": 2}
STAGE_IDLE, STAGE_ATTACK, STAGE_DECAY = 0, 1, 2

RISE_FUNCTION = f"""// the exponential rise (kit technique: drum envelope): 0 at u = 0, 1 at u = 1, an exponential decay reversed in time
drum_envelope_exponential_rise(progress) {{
\tfloor_level = exp(-{ATTACK_CURVATURE!r});
\treturn (exp(-{ATTACK_CURVATURE!r} * (1 - clamp(progress, 0, 1))) - floor_level) / (1 - floor_level);
}}"""
RISE_INVERSE_FUNCTION = f"""// the progress at which the exponential rise reaches a level (kit technique: drum envelope)
drum_envelope_exponential_rise_progress(level) {{
\tfloor_level = exp(-{ATTACK_CURVATURE!r});
\treturn 1 + log(clamp(level, 0, 1) * (1 - floor_level) + floor_level) / {ATTACK_CURVATURE!r};
}}"""
FUNCTIONS = {"drum_envelope_exponential_rise": RISE_FUNCTION,
             "drum_envelope_exponential_rise_progress": RISE_INVERSE_FUNCTION}


def exponential_rise(progress):
    """The Python model of drum_envelope_exponential_rise."""
    floor_level = math.exp(-ATTACK_CURVATURE)
    progress = min(max(progress, 0.0), 1.0)
    return (math.exp(-ATTACK_CURVATURE * (1 - progress)) - floor_level) / (1 - floor_level)


def exponential_decay_factor_per_sample(decay_ms, sample_rate):
    """The exponential decay's factor a sample: DECAY_SPAN_DB over decay_ms."""
    decay_samples = max(decay_ms, SHORTEST_TIME_MS) * sample_rate / 1000
    return 10 ** (-DECAY_SPAN_DB / 20 / decay_samples)


class DrumEnvelope(Technique):
    """`<name>_level` in [0, 1], `<name>_stage` (0 idle, 1 attack, 2 decay). Inputs: `hit` (true on a hit's sample),
    `mode` (0 exponential, 1 linear, 2 clap burst; held from the hit), `attack_ms` (>= 0), `decay_ms`,
    `clap_burst_count` (pulses, at least 1), `clap_burst_spacing_ms`. State: the level, the stage, the attack's
    progress, the latched mode, the clap's pulses left and samples to the next."""

    def __init__(self, instance_name, hit, mode, attack_ms, decay_ms, clap_burst_count="1",
                 clap_burst_spacing_ms="10"):
        super().__init__(instance_name, hit=hit, mode=mode, attack_ms=attack_ms, decay_ms=decay_ms,
                         clap_burst_count=clap_burst_count, clap_burst_spacing_ms=clap_burst_spacing_ms)
        self.latency_samples = 0       # a hit moves the envelope on the hit's own sample

    def functions(self):
        return dict(FUNCTIONS)

    def declarations(self):
        return self.substituted("History ${p}_level_state(0), ${p}_stage(0), ${p}_attack_progress(0), "
                                "${p}_latched_mode(0), ${p}_clap_pulses_left(0), ${p}_clap_samples_to_next(0);")

    def statements(self):
        return self.substituted("""// ${p}: drum envelope, exponential / linear / clap burst (kit technique: drum envelope)
${p}_attack_samples = max(${attack_ms}, 0) * samplerate / 1000;
${p}_decay_samples = max(${decay_ms}, ${shortest}) * samplerate / 1000;
${p}_spacing_samples = max(${clap_burst_spacing_ms}, ${shortest}) * samplerate / 1000;
if (${hit}) {
	${p}_latched_mode = clamp(floor(${mode} + 0.5), 0, 2);
	${p}_clap_pulses_left = 0;
	if (${p}_latched_mode == 2) {
		${p}_level_state = 1;
		${p}_stage = 2;
		${p}_clap_pulses_left = max(floor(${clap_burst_count} + 0.5), 1) - 1;
		${p}_clap_samples_to_next = ${p}_spacing_samples;
	} else if (${p}_attack_samples < 1) {
		${p}_level_state = 1;
		${p}_stage = 2;
	} else {
		${p}_stage = 1;
		${p}_attack_progress = ${p}_latched_mode == 1 ? ${p}_level_state : drum_envelope_exponential_rise_progress(${p}_level_state);
	}
}
${p}_level = ${p}_level_state;
${p}_exponential_mode = ${p}_latched_mode != 1;
${p}_clap_bursting = ${p}_clap_pulses_left > 0;
if (${p}_stage == 1) {
	// the progress's sum of 1 / samples may fall short of 1 by a rounding: the attack ends within 1e-9 of it
	${p}_attack_progress = min(${p}_attack_progress + 1 / max(${p}_attack_samples, 1), 1);
	${p}_level_state = ${p}_exponential_mode ? drum_envelope_exponential_rise(${p}_attack_progress) : ${p}_attack_progress;
	if (${p}_attack_progress >= ${nearly_one}) {
		${p}_level_state = 1;
		${p}_stage = 2;
	}
} else if (${p}_stage == 2) {
	${p}_fall_samples = ${p}_clap_bursting ? ${p}_spacing_samples : ${p}_decay_samples;
	if (${p}_exponential_mode) {
		${p}_level_state = ${p}_level_state * pow(10, -${span_db} / 20 / ${p}_fall_samples);
	} else {
		${p}_level_state = ${p}_level_state - 1 / ${p}_fall_samples;
	}
	if (${p}_clap_bursting) {
		${p}_clap_samples_to_next = ${p}_clap_samples_to_next - 1;
		if (${p}_clap_samples_to_next <= 0) {
			${p}_level_state = 1;
			${p}_clap_pulses_left = ${p}_clap_pulses_left - 1;
			${p}_clap_samples_to_next = ${p}_clap_samples_to_next + ${p}_spacing_samples;
		}
	} else if (${p}_level_state <= ${silent}) {
		${p}_level_state = 0;
		${p}_stage = 0;
	}
}""", shortest=SHORTEST_TIME_MS, span_db=DECAY_SPAN_DB, silent=SILENT_LEVEL,
                                nearly_one=1 - 1e-9)

    def reset_statements(self):
        """Statements that silence the envelope at once (a choke)."""
        return self.substituted("${p}_level_state = 0;\n${p}_stage = 0;\n${p}_clap_pulses_left = 0;")
