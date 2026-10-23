"""A small drum voice for the patch matcher's tests (architecture/patch-matcher.md): a sine with an exponential pitch
sweep and an exponential amp decay, plus white noise through two one-pole low-passes with its own decay, into a
normalised tanh drive. Eight parameters, the shape of a kick / tom / snare voice, so the matcher can be validated on
hits whose parameters are known before any real target exists.

    --voice tests/fixture_drum_voice.py:FIXTURE_DRUM_VOICE      (tools/match_patch.py)
"""
import os
import sys

KIT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KIT_DIRECTORY not in sys.path:
    sys.path.insert(0, KIT_DIRECTORY)

from twosl_dsp.patch_match_voice import MatchedParameter, MatchedVoice, MatchTrigger  # noqa: E402

FIXTURE_DRUM_CODE = """
decay_coefficient(milliseconds) {
\treturn exp(-1 / (milliseconds * 0.001 * samplerate));
}
one_pole_coefficient(hertz) {
\treturn 1 - exp(-twopi * hertz / samplerate);
}

Param pitch_hz(55, min=20, max=1000);
Param sweep_semitones(24, min=0, max=60);
Param sweep_ms(20, min=0.5, max=500);
Param decay_ms(300, min=5, max=5000);
Param noise_level(0.2, min=0, max=1);
Param noise_cutoff_hz(4000, min=50, max=20000);
Param noise_decay_ms(40, min=1, max=2000);
Param drive(2, min=1, max=50);
History phase(0), sweep_envelope(0), amp_envelope(0), noise_envelope(0), low_pass_1(0), low_pass_2(0);

if (in1 > 0) {
\tphase = 0;
\tsweep_envelope = 1;
\tamp_envelope = 1;
\tnoise_envelope = 1;
}
frequency = pitch_hz * pow(2, sweep_semitones * sweep_envelope / 12);
tone = sin(twopi * phase) * amp_envelope;
phase = wrap(phase + frequency / samplerate, 0, 1);
noise_coefficient = one_pole_coefficient(min(noise_cutoff_hz, 0.45 * samplerate));
low_pass_1 = low_pass_1 + noise_coefficient * (noise() - low_pass_1);
low_pass_2 = low_pass_2 + noise_coefficient * (low_pass_1 - low_pass_2);
noisy = low_pass_2 * noise_level * noise_envelope;
sweep_envelope = sweep_envelope * decay_coefficient(sweep_ms);
amp_envelope = amp_envelope * decay_coefficient(decay_ms);
noise_envelope = noise_envelope * decay_coefficient(noise_decay_ms);
out1 = tanh(drive * (tone + noisy)) / tanh(drive);
"""

FIXTURE_DRUM_VOICE = MatchedVoice(
    name="fixture drum",
    gen_code=FIXTURE_DRUM_CODE,
    num_inputs=1,
    num_outputs=1,
    parameters=(
        MatchedParameter.continuous("pitch_hz", 30, 400, "log"),
        MatchedParameter.continuous("sweep_semitones", 0, 48),
        MatchedParameter.continuous("sweep_ms", 2, 100, "log"),
        MatchedParameter.continuous("decay_ms", 30, 1500, "log"),
        MatchedParameter.continuous("noise_level", 0, 1),
        MatchedParameter.continuous("noise_cutoff_hz", 200, 15000, "log"),
        MatchedParameter.continuous("noise_decay_ms", 5, 300, "log"),
        MatchedParameter.continuous("drive", 1, 20, "log"),
    ),
    trigger=MatchTrigger(input_number=1),
)
