// 2sl meter: set a target, press measure, play the loudest part.
//   measure  arm: wait for audio, then measure for `length` seconds, then hold
//   peak f   max sample peak (both channels) since the last report, 0..1+
//   rms f f  per-channel short-term RMS, 0..1
//   length f window in seconds
//   target f target master peak in dB
// Out 0: peak over the window, dB (Peak param)
// Out 1: RMS over the window, dB (RMS param)
// Out 2: status text ("set ...")
// Out 3: change needed, text ("set ...")
// Out 4: state for the extension: 0 idle, 1 armed, 2 measuring, 3 held (State param)
inlets = 1;
outlets = 5;

var FLOOR = -70;
var SIGNAL = 0.001; // −60 dBFS: anything above starts the window
var windowSec = 5;
var targetDb = -6;
var state = 0;
var start = 0;
var hold = 0;
var sumsq = 0;
var count = 0;
var lastStatus = 0;

function todb(a) {
  return a <= 0.0000001 ? FLOOR : Math.max(FLOOR, (20 * Math.log(a)) / Math.LN10);
}
function round1(x) {
  return Math.round(x * 10) / 10;
}
function fmt(db) {
  var v = round1(db);
  return (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1) + " dB";
}

function setState(s) {
  state = s;
  outlet(4, s);
}

function showChange() {
  if (hold <= 0) {
    outlet(3, "set", "change: –");
    return;
  }
  var change = round1(targetDb - todb(hold));
  outlet(3, "set", "change: " + (change === 0 ? "on target" : fmt(change)));
}

function tick() {
  if (state !== 2) return;
  var t = (Date.now() - start) / 1000;
  if (t >= windowSec) {
    setState(3);
    outlet(2, "set", "held → gain stage mix");
  } else if (Date.now() - lastStatus > 100) {
    lastStatus = Date.now();
    outlet(2, "set", "measuring " + t.toFixed(1) + " / " + windowSec + " s");
  }
}

function peak(a) {
  if (state === 1 && a > SIGNAL) {
    setState(2);
    start = Date.now();
  }
  if (state !== 2) return;
  if (a > hold) {
    hold = a;
    outlet(0, round1(todb(hold)));
    showChange();
  }
  tick();
}

function rms(l, r) {
  if (state !== 2) return;
  sumsq += (l * l + r * r) / 2;
  count++;
  outlet(1, round1(todb(Math.sqrt(sumsq / count))));
  tick();
}

function length(s) {
  windowSec = Math.max(1, Math.min(30, Math.round(s)));
}

function target(db) {
  targetDb = db;
  showChange();
}

function measure() {
  setState(1);
  hold = 0;
  sumsq = 0;
  count = 0;
  outlet(0, FLOOR);
  outlet(1, FLOOR);
  showChange();
  outlet(2, "set", "armed: play the loudest part");
}

function loadbang() {
  setState(0);
  showChange();
  outlet(2, "set", "set target, press measure");
}
