// The kit's Moog transistor ladder (m4l_dev/circuit_modules/moog_transistor_ladder.py), one instance of it, as a
// display draws it: its Emphasis law and its small-signal response (the module's small_signal_response, magnitude,
// before the output's coupling capacitor). The constants are the instance's, filled in by the build.

/** k, the loop's gain, at an Emphasis rotation 0..1 (clamped): tap (R76 + w R73) / (R76 + R73 + Rtop), the pot's
 * resistance above its wiper from its reverse-audio taper (feedback_gain_at_emphasis). */
function /*NAME*/_feedback_gain(emphasis) {
  var rotation = Math.min(Math.max(emphasis, 0), 1);
  return /*REGENERATION_NUMERATOR*/ / (/*LOOP_OHMS*/ + /*POT_OHMS*/ * (Math.pow(/*TAPER_BASE*/, 1 - rotation) - 1) /
    (/*TAPER_BASE*/ - 1));
}

/** |H| at frequencyHz for a cutoff (Hz, clamped as the module clamps it) and an Emphasis rotation 0..1: the TPT
 * ladder at the module's oversampled rate, each stage the bilinear one-pole at tan(pi fc / (N sr)) over its
 * capacitor's ratio, the loop 1 / (P^-1 + k); at 2x times the halfband low-pass squared at f / (2 sr). */
function /*NAME*/_response(frequencyHz, cutoffHz, emphasis, sampleRate) {
  var steps = /*OVERSAMPLING*/, ratios = /*STAGE_CAPACITANCE_RATIOS*/;
  var cutoff = Math.min(Math.max(cutoffHz, /*LOWEST_CUTOFF_HZ*/), /*HIGHEST_CUTOFF_OF_SAMPLE_RATE*/ * sampleRate);
  var warp = Math.tan(Math.PI * cutoff / (sampleRate * steps));
  var t = Math.tan(Math.PI * frequencyHz / (sampleRate * steps));   // the bilinear s = j t
  // P^-1 = prod (1 + j t r / warp), then + k
  var re = 1, im = 0;
  for (var i = 0; i < ratios.length; i++) {
    var x = t * ratios[i] / warp, nextRe = re - im * x;
    im = re * x + im; re = nextRe;
  }
  re += /*NAME*/_feedback_gain(emphasis);
  var magnitude = 1 / Math.sqrt(re * re + im * im);
  if (steps === 1) return magnitude;
  // the halfband pair: (A0(z^2) + z^-1 A1(z^2)) / 2 at f / (2 sr), A = prod (a + z^-2) / (1 + a z^-2) per path
  var coefficients = /*HALFBAND_COEFFICIENTS*/, w = 2 * Math.PI * frequencyHz / (2 * sampleRate);
  var vRe = Math.cos(2 * w), vIm = -Math.sin(2 * w);                // z^-2
  var pathRe = [1, 1], pathIm = [0, 0];
  for (var j = 0; j < coefficients.length; j++) {
    var a = coefficients[j];
    var nRe = a + vRe, nIm = vIm, dRe = 1 + a * vRe, dIm = a * vIm, dd = dRe * dRe + dIm * dIm;
    var qRe = (nRe * dRe + nIm * dIm) / dd, qIm = (nIm * dRe - nRe * dIm) / dd;
    var p = j % 2, pRe = pathRe[p] * qRe - pathIm[p] * qIm;
    pathIm[p] = pathRe[p] * qIm + pathIm[p] * qRe; pathRe[p] = pRe;
  }
  var uRe = Math.cos(w), uIm = -Math.sin(w);                        // z^-1
  var hRe = (pathRe[0] + pathRe[1] * uRe - pathIm[1] * uIm) / 2, hIm = (pathIm[0] + pathRe[1] * uIm + pathIm[1] * uRe) / 2;
  return magnitude * (hRe * hRe + hIm * hIm);
}
