// The kit's switched-capacitor block (m4l_dev/gen_switched_capacitor.py) as a display draws it: the section's
// small-signal response at its three pins, the tick sequence's z-domain response at the clock (z = e^(j 2 pi f /
// f_clock)), no Q enhancement, no images. The constants are the block's, filled in by the build.
var SWITCHED_CAPACITOR_LOWEST_CUTOFF_HZ = /*SWITCHED_CAPACITOR_LOWEST_CUTOFF_HZ*/;
var SWITCHED_CAPACITOR_HIGHEST_CUTOFF_HZ = /*SWITCHED_CAPACITOR_HIGHEST_CUTOFF_HZ*/;
var SWITCHED_CAPACITOR_LOWEST_DAMPING = /*SWITCHED_CAPACITOR_LOWEST_DAMPING*/;
var SWITCHED_CAPACITOR_DAMPING_MARGIN = /*SWITCHED_CAPACITOR_DAMPING_MARGIN*/;

/** The section's pins at frequencyHz, for a cutoff (Hz), a damping (q = 1/Q) and the clock ratio (50 or 100):
 * {lpRe, lpIm, bpRe, bpIm, hpRe, hpIm}. Per tick: hp = x - z^-1 (lp + q bp), bp = F/(1 - z^-1) hp,
 * lp = F/(1 - z^-1) bp; the HP pin between ticks is x - lp - q bp. */
function switchedCapacitorResponse(frequencyHz, cutoffHz, damping, clockRatio) {
  var F = 2 * Math.sin(Math.PI / clockRatio);
  var clock = clockRatio * Math.min(Math.max(cutoffHz, SWITCHED_CAPACITOR_LOWEST_CUTOFF_HZ),
    SWITCHED_CAPACITOR_HIGHEST_CUTOFF_HZ);
  var q = Math.min(Math.max(damping, SWITCHED_CAPACITOR_LOWEST_DAMPING), 2 - F - SWITCHED_CAPACITOR_DAMPING_MARGIN);
  var w = 2 * Math.PI * frequencyHz / clock;
  var zRe = Math.cos(w), zIm = -Math.sin(w);                       // z^-1
  // the integrator F / (1 - z^-1)
  var dRe = 1 - zRe, dIm = -zIm, dd = dRe * dRe + dIm * dIm;
  var iRe = F * dRe / dd, iIm = -F * dIm / dd;
  // the loop: 1 + z^-1 (I^2 + q I)
  var i2Re = iRe * iRe - iIm * iIm, i2Im = 2 * iRe * iIm;
  var sRe = i2Re + q * iRe, sIm = i2Im + q * iIm;
  var lRe = 1 + zRe * sRe - zIm * sIm, lIm = zRe * sIm + zIm * sRe;
  var ll = lRe * lRe + lIm * lIm;
  var hRe = lRe / ll, hIm = -lIm / ll;                               // the tick's hp
  var bpRe = iRe * hRe - iIm * hIm, bpIm = iRe * hIm + iIm * hRe;
  var lpRe = iRe * bpRe - iIm * bpIm, lpIm = iRe * bpIm + iIm * bpRe;
  return {lpRe: lpRe, lpIm: lpIm, bpRe: bpRe, bpIm: bpIm,
    hpRe: 1 - lpRe - q * bpRe, hpIm: -lpIm - q * bpIm};
}
