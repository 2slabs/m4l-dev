// 2sl meter: holds the loudest sample peak (both channels) in dB.
// In: peak amplitudes (float, 0..1+) from peakamp~. "reset" clears the hold.
// Out 0: held peak in dB (to the Peak Hold parameter). Out 1: current peak in dB.
inlets = 1;
outlets = 2;
var hold = 0;
var FLOOR = -70;

function todb(a) {
  return a <= 0.0000001 ? FLOOR : Math.max(FLOOR, (20 * Math.log(a)) / Math.LN10);
}

function msg_float(a) {
  if (a > hold) {
    hold = a;
    outlet(0, Math.round(todb(hold) * 10) / 10);
  }
  outlet(1, Math.round(todb(a) * 10) / 10);
}

function reset() {
  hold = 0;
  outlet(0, FLOOR);
}
