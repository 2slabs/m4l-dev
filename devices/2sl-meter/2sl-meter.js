// 2sl meter: measures a window of the mix after "reset".
//   reset   arm: wait for audio, then measure for `length` seconds, then hold.
//   peak f  max sample peak (both channels) since the last report, 0..1+
//   rms f f per-channel short-term RMS, 0..1
//   length f window in seconds
// Out 0: peak in dB over the window (Peak Hold). Out 1: RMS in dB over the window.
// Out 2: status text for a comment ("set ...").
inlets = 1;
outlets = 3;

var FLOOR = -70;
var SIGNAL = 0.001; // −60 dBFS: anything above starts the window
var windowSec = 5;
var state = "idle"; // idle | armed | measuring | held
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

function status(text) {
  outlet(2, "set", text);
}

function tick() {
  if (state !== "measuring") return;
  var t = (Date.now() - start) / 1000;
  if (t >= windowSec) {
    state = "held";
    status("held: " + windowSec + " s of audio");
  } else if (Date.now() - lastStatus > 100) {
    lastStatus = Date.now();
    status("measuring " + t.toFixed(1) + " / " + windowSec + " s");
  }
}

function peak(a) {
  if (state === "armed" && a > SIGNAL) {
    state = "measuring";
    start = Date.now();
  }
  if (state !== "measuring") return;
  if (a > hold) {
    hold = a;
    outlet(0, round1(todb(hold)));
  }
  tick();
}

function rms(l, r) {
  if (state !== "measuring") return;
  sumsq += (l * l + r * r) / 2;
  count++;
  outlet(1, round1(todb(Math.sqrt(sumsq / count))));
  tick();
}

function length(s) {
  windowSec = Math.max(1, Math.min(30, Math.round(s)));
  if (state === "idle") status("press reset, then play");
}

function reset() {
  state = "armed";
  hold = 0;
  sumsq = 0;
  count = 0;
  outlet(0, FLOOR);
  outlet(1, FLOOR);
  status("armed: play the loudest part");
}

function loadbang() {
  status("press reset, then play");
}
