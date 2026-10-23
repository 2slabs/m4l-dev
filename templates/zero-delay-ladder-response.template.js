// The kit's zero-delay ladder filter (twosl_dsp/techniques/zero_delay_ladder_filter.py) as a display draws it: its
// small-signal response, the analog ladder 1 / ((1 + s)^4 + k) at s = j tan(pi f / sr) / tan(pi fc / sr) (the
// technique's prewarped bilinear transform), and each form's k (the saturating ladder's, the linear one's). The
// constants are the technique's, filled in by the build.
var LADDER_FEEDBACK_AT_FULL_RESONANCE = /*LADDER_FEEDBACK_AT_FULL_RESONANCE*/;
var LADDER_LINEAR_FEEDBACK_AT_FULL_RESONANCE = /*LADDER_LINEAR_FEEDBACK_AT_FULL_RESONANCE*/;
var LADDER_HIGHEST_CUTOFF_OF_SAMPLE_RATE = /*LADDER_HIGHEST_CUTOFF_OF_SAMPLE_RATE*/;
var LADDER_LOWEST_CUTOFF_HZ = /*LADDER_LOWEST_CUTOFF_HZ*/;

/** k, the ladder's loop gain, at Resonance 0..1 (clamped) for its form (linear: the technique's linear=True). */
function ladderFeedbackGain(resonance, linear) {
  return Math.min(Math.max(resonance, 0), 1) *
    (linear ? LADDER_LINEAR_FEEDBACK_AT_FULL_RESONANCE : LADDER_FEEDBACK_AT_FULL_RESONANCE);
}

/** |H| of the ladder at frequencyHz, for a cutoff (Hz, clamped as the technique clamps it) and loop gain k. */
function ladderResponse(frequencyHz, cutoffHz, feedbackGain, sampleRate) {
  var cutoff = Math.min(Math.max(cutoffHz, LADDER_LOWEST_CUTOFF_HZ), LADDER_HIGHEST_CUTOFF_OF_SAMPLE_RATE * sampleRate);
  var x = Math.tan(Math.PI * Math.min(frequencyHz, 0.4999 * sampleRate) / sampleRate) /
    Math.tan(Math.PI * cutoff / sampleRate);
  // (1 + jx)^4 by repeated multiplication
  var re = 1, im = 0;
  for (var i = 0; i < 4; i++) { var t = re - im * x; im = re * x + im; re = t; }
  re += feedbackGain;
  return 1 / Math.sqrt(re * re + im * im);
}
