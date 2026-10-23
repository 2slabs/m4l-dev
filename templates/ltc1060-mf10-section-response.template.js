// The kit's LTC1060 / MF10 section (twosl_dsp/circuit_modules/ltc1060_mf10_section.py) as a display draws it: the section's
// small-signal response at its three pins, the tick sequence's z-domain response at the clock (z = e^(j 2 pi f /
// f_clock)), no Q enhancement, no images. The constants are the module's, filled in by the build.
var LTC1060_MF10_LOWEST_CENTER_HZ = /*LTC1060_MF10_LOWEST_CENTER_HZ*/;
var LTC1060_MF10_HIGHEST_CENTER_HZ = /*LTC1060_MF10_HIGHEST_CENTER_HZ*/;
var LTC1060_MF10_LOWEST_DAMPING = /*LTC1060_MF10_LOWEST_DAMPING*/;
var LTC1060_MF10_DAMPING_MARGIN = /*LTC1060_MF10_DAMPING_MARGIN*/;
// F = 2 sin(pi / clock ratio) by clock ratio, as the module's code holds it
var LTC1060_MF10_TICK_COEFFICIENTS = /*LTC1060_MF10_TICK_COEFFICIENTS*/;

/** The section's pins at frequencyHz, for a clock (Hz, at the CLK pin), a damping (q = 1/Q) and the clock ratio (50 or 100):
 * {lpRe, lpIm, bpRe, bpIm, hpRe, hpIm}. Per tick: hp = x - z^-1 (lp + q bp), bp = F/(1 - z^-1) hp,
 * lp = F/(1 - z^-1) bp; the HP pin between ticks is x z^(1/2) - lp - q bp (ltc1060_mf10_section.py). */
function ltc1060Mf10SectionResponse(frequencyHz, clockHz, damping, clockRatio) {
  var F = LTC1060_MF10_TICK_COEFFICIENTS[clockRatio];
  if (F === undefined) throw new Error("ltc1060Mf10SectionResponse: no clock ratio " + clockRatio + " (50 or 100)");
  var clock = Math.min(Math.max(clockHz, clockRatio * LTC1060_MF10_LOWEST_CENTER_HZ),
    clockRatio * LTC1060_MF10_HIGHEST_CENTER_HZ);
  var q = Math.min(Math.max(damping, LTC1060_MF10_LOWEST_DAMPING), 2 - F - LTC1060_MF10_DAMPING_MARGIN);
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
  // the HP pin: the live input, on average half a tick after the tick, against the held states
  return {lpRe: lpRe, lpIm: lpIm, bpRe: bpRe, bpIm: bpIm,
    hpRe: Math.cos(w / 2) - lpRe - q * bpRe, hpIm: Math.sin(w / 2) - lpIm - q * bpIm};
}
