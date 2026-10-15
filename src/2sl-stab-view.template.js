// 2sl stab: everything drawn (jsui), in the 2sl-ui look. One file, several views, chosen by jsarguments:
//   chrome  the device background: rules between sections, labels and hints (per page)
//   link    the 2sl wordmark chip: hover shows 2sl.to, click opens it
//   chord   big chord name, its notes, a lit keyboard            (from the chord brain)
//   steps   the machine's 16 steps: click to edit; playhead, hits, throws, status line
//   echo    the dub echo as measured: its last time rounds and the one now, throws, freeze, live level
//   pump    the duck curve over a beat, with a moving playhead
//   sub     the sub oscillator: its wave for Sub Mode, over DCO 1's two cycles
//   osc1    DCO 1: its waveform (saw, pulse, both), pulse width, PWM
//   osc2    DCO 2: its waveform (saw, pulse, triangle), interval and detune
//   lfo     the LFO and where it goes
//   filter  the low-pass response, and how far the envelope opens it
//   env     the envelope shape (Length macro applied)
//   drive   the saturation curve
// Text is Cozette, drawn from its bitmaps (13 px; 26 px doubled). Colours are the 2sl-ui tokens, dark or
// light to match Live's theme. Generated from src/2sl-stab-view.template.js by src/2sl-stab.py; edit there.
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
inlets = 1;
outlets = 1;

var MODE = jsarguments.length > 1 ? String(jsarguments[1]) : "steps";

/*COZETTE*/

// ---- 2sl-ui tokens -----------------------------------------------------------------------------
/*THEME_FROM_LIVE*/
var T = THEMES.dark;
function pickTheme() { T = themeFromLive("the " + MODE + " display"); }
pickTheme();

// What this display draws from. The controls' values start as the Init preset (BASE) sends them, written
// in by the build per display, so a display is right before Live recalls the controls (and they agree after).
var S = {
  page: 0,
  name: "", pitches: [], notice: "",
  pattern: "X..x..x.........", pos: -1, machine: 0, latch: 0, held: "-", flash: {}, throwflash: {},
  throwAt: 0, phase: 0,
  tempo: 120                        // Live's tempo (the pump), until Live reports it
};
var VIEW_DEFAULTS = /*VIEW_DEFAULTS*/;
(function () {
  var defaults = VIEW_DEFAULTS[MODE] || {};
  for (var key in defaults) S[key] = defaults[key];
})();

var anim = new Task(function () { mgraphics.redraw(); }, this);
anim.interval = 33;
if (MODE === "steps" || MODE === "echo" || MODE === "pump" || MODE === "lfo" || MODE === "osc1" || MODE === "osc2") anim.repeat();

function now() { return new Date().getTime(); }

// ---- messages ----------------------------------------------------------------------------------

function anything() {
  var a = arrayfromargs(arguments);
  var m = messagename;
  if (m === "theme") pickTheme();
  else if (m === "chord") { S.name = String(a[0]); S.pitches = a.slice(1); }
  else if (m === "clear") { S.name = ""; S.pitches = []; }
  else if (m === "notice") S.notice = a.join(" ");
  else if (m === "pattern") S.pattern = String(a[0]);
  else if (m === "held") S.held = String(a[0]);
  else if (m === "hit") { S.flash[a[0]] = now(); if (a[1]) { S.throwflash[a[0]] = now(); S.throwAt = now(); } }
  else if (m === "throw") S.throwAt = now();
  else if (m === "lfophase") recordLfoReading(a[0]);
  else if (m === "echo") recordEchoReading(a);
  else if (m in S) S[m] = a[0];
  else error("2sl stab: the " + MODE + " display doesn't take '" + m + "' (a wiring error): ignored\n");
  mgraphics.redraw();
}
function bang() { pickTheme(); mgraphics.redraw(); }

// ---- drawing: shapes ---------------------------------------------------------------------------

function rgba(c, alpha) { mgraphics.set_source_rgba(c[0], c[1], c[2], alpha === undefined ? c[3] : alpha); }
function mix(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, 1]; }
function rect(x, y, w, h, c, alpha) { rgba(c, alpha); mgraphics.rectangle(x, y, w, h); mgraphics.fill(); }
function frame(x, y, w, h, c, lw) { rgba(c); mgraphics.set_line_width(lw || 1); mgraphics.rectangle(x + 0.5, y + 0.5, w - 1, h - 1); mgraphics.stroke(); }
function tanh(x) { var e = Math.exp(2 * Math.max(-20, Math.min(20, x))); return (e - 1) / (e + 1); }  // jsui has no Math.tanh
function fade(t, ms) { return Math.max(0, 1 - (now() - t) / ms); }

// ---- drawing: Cozette text ---------------------------------------------------------------------

var missingGlyphsReported = {};
/** The Cozette bitmap for a codepoint. One that tools/bdf2js.py didn't embed draws as "?", and says so once. */
function glyph(codepoint) {
  var found = COZETTE[codepoint];
  if (found) return found;
  if (!missingGlyphsReported[codepoint]) {
    missingGlyphsReported[codepoint] = 1;
    error("2sl stab: the " + MODE + " display has no Cozette glyph for U+" + codepoint.toString(16).toUpperCase() +
          " (add it to tools/bdf2js.py's list): drawn as ?\n");
  }
  return COZETTE[63];
}

/** Width of `str` in pixels at scale 1 (13 px) or 2 (26 px). */
function measure(str, scale) {
  var w = 0;
  for (var i = 0; i < str.length; i++) { var g = glyph(str.charCodeAt(i)); w += g[0]; }
  return w * (scale || 1);
}

/** Draw `str` with its baseline at y (Cozette: ascent 10, descent 3). */
function text(str, x, y, c, scale) {
  str = String(str);
  var k = scale || 1;
  rgba(c);
  var pen = Math.round(x);
  for (var i = 0; i < str.length; i++) {
    var g = glyph(str.charCodeAt(i));
    var w = g[1], h = g[2], xo = g[3], yo = g[4];
    var nb = Math.ceil(w / 8) * 8;
    var top = Math.round(y) - (yo + h) * k;
    for (var r = 0; r < h; r++) {
      var bits = g[5 + r];
      if (!bits) continue;
      var runStart = -1;
      for (var px = 0; px <= w; px++) {
        var on = px < w && (bits >> (nb - 1 - px)) & 1;
        if (on && runStart < 0) runStart = px;
        if (!on && runStart >= 0) {
          mgraphics.rectangle(pen + (xo + runStart) * k, top + r * k, (px - runStart) * k, k);
          runStart = -1;
        }
      }
    }
    pen += g[0] * k;
  }
  mgraphics.fill();
}

/** An inverted 2sl label chip: ink background, pad text. */
function chip(str, x, y, fg, bg) {
  var w = measure(str) + 8;
  rect(x, y, w, 15, bg || T.ink);
  text(str, x + 4, y + 12, fg || T.pad);
  return w;
}

// ---- views --------------------------------------------------------------------------------------

function paint() {
  var w = mgraphics.size[0], h = mgraphics.size[1];
  rect(0, 0, w, h, MODE === "chrome" ? T.pad : T.well);
  if (MODE === "chrome") chromeView(w, h);
  else if (MODE === "link") linkView(w, h);
  else if (MODE === "chord") chordView(w, h);
  else if (MODE === "steps") stepsView(w, h);
  else if (MODE === "echo") echoView(w, h);
  else if (MODE === "pump") pumpView(w, h);
  else if (MODE === "env") envView(w, h);
  else if (MODE === "filter") filterView(w, h);
  else if (MODE === "sub") subView(w, h);
  else if (MODE === "osc1") oscView(w, h, 1);
  else if (MODE === "osc2") oscView(w, h, 2);
  else if (MODE === "lfo") lfoView(w, h);
  else if (MODE === "drive") driveView(w, h);
  else if (!unknownModeReported) {
    unknownModeReported = true;
    error("2sl stab: a display was given the unknown mode '" + MODE + "' (jsarguments): it draws nothing\n");
  }
}
var unknownModeReported = false;

/*LAYOUT*/

var hover = 0;
var SITE = "https://2sl.to";

function linkView(w, h) {
  rect(0, 0, w, h, T.pad);
  // the 2sl wordmark; on hover it becomes the link
  chip(hover ? "2sl.to \u2192" : "2sl stab", 0, 0, hover ? T.inverse : T.pad, hover ? T.now : T.ink);
}
function onidle(x, y) {
  if (MODE !== "link" || hover) return;
  hover = 1;
  mgraphics.redraw();
}
function onidleout() {
  if (MODE !== "link") return;
  hover = 0;
  mgraphics.redraw();
}

function chromeView(w, h) {
  rect(0, 21, w, 1, T.unlit, 0.6);
  var page = LAYOUT.pages[Math.max(0, Math.min(LAYOUT.pages.length - 1, S.page | 0))];
  // hairline rules between sections
  for (var i = 0; i < page.rules.length; i++) rect(page.rules[i], 28, 1, h - 36, T.unlit, 0.35);
  for (var j = 0; j < page.labels.length; j++) {
    var L = page.labels[j];
    text(L[0], L[1], L[2], L[3] === "hint" ? T.unlit : T.label);
  }
  var sub = "dub chord machine  v" + LAYOUT.version;
  text(sub, LAYOUT.subtitle, 15, T.label);
}

// Every display: a small label at the top left, the drawing below.
function viewLabel(str, w) { text(str, 4, 12, T.label); }

var NOTE = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

function chordView(w, h) {
  // a notice from the brain (In Key falling back to the fixed shapes) takes the top line, in warm
  if (S.notice) text(S.notice, 4, 12, T.warm);
  else viewLabel("chord");
  if (!S.pitches.length) {
    text("play a key", 4, 36, T.unlit, 2);
  } else {
    text(S.name, 4, 38, T.ink, 2);
    var notes = S.pitches.slice().sort(function (a, b) { return a - b; }).map(function (p) { return NOTE[p % 12]; });
    if (!S.notice) text(notes.join(" "), w - measure(notes.join(" ")) - 4, 12, T.label);
  }
  // two octaves of keys, from the C at or below the lowest note
  var lit = {};
  S.pitches.forEach(function (p) { lit[p] = 1; });
  var low = S.pitches.length ? Math.min.apply(null, S.pitches) : 48;
  var start = low - (low % 12);
  var top = 46, kh = h - top - 3, whites = [0, 2, 4, 5, 7, 9, 11], blacks = [1, 3, 6, 8, 10];
  var n = 14, kw = (w - 8) / n;
  for (var i = 0; i < n; i++) {
    var p = start + 12 * Math.floor(i / 7) + whites[i % 7];
    rect(4 + i * kw, top, kw - 1, kh, lit[p] ? T.mint : T.key);
  }
  var bx = [0.62, 1.62, 3.62, 4.62, 5.62];
  for (var o = 0; o < 2; o++) {
    for (var j = 0; j < 5; j++) {
      var pb = start + 12 * o + blacks[j];
      rect(4 + (o * 7 + bx[j]) * kw, top, kw * 0.7, kh * 0.62, lit[pb] ? T.mint : T.keyBlack);
    }
  }
}

function stepsView(w, h) {
  viewLabel("pattern");
  var status, col = T.label;
  if (!S.machine) status = "machine off";
  else if (S.held === "-") status = S.latch ? "tap a chord" : "hold a chord";
  else { status = (S.latch ? "latched " : "playing ") + S.held; col = T.ink; }
  text(status, w - measure(status) - 4, 12, col);
  var top = 18, cw = (w - 8) / 16, ch = h - top - 4;
  for (var i = 0; i < 16; i++) {
    var x = 4 + i * cw, c = S.pattern.charAt(i);
    var fill = c === "X" ? T.mint : c === "x" ? mix(T.mint, T.well, 0.55) : (i % 4 === 0 ? T.beat : T.rest);
    rect(x + 1, top, cw - 2, ch, fill);
    if (c === "X") rect(x + 1, top, cw - 2, 3, T.ink);           // accents carry a bar on top
    var f = S.flash[i] ? fade(S.flash[i], 220) : 0;
    if (f > 0) rect(x + 1, top, cw - 2, ch, T.ink, f * 0.8);
    var tf = S.throwflash[i] ? fade(S.throwflash[i], 600) : 0;
    if (tf > 0) frame(x, top - 1, cw, ch + 2, T.warm, 2);
    if (S.machine && i === S.pos) frame(x, top - 1, cw, ch + 2, T.now, 2);
  }
}

function onclick(x, y) {
  if (MODE === "link") {
    max.launchbrowser(SITE);
    return;
  }
  if (MODE !== "steps") return;
  var w = mgraphics.size[0];
  if (y < 16) return;
  outlet(0, "edit", Math.max(0, Math.min(15, Math.floor((x - 4) / ((w - 8) / 16)))));
}

// The echo as the FX measured it (|left| + |right|), read every 33 ms in one message: its level now, its peak so far
// in the time round it is in, then its peaks over its last whole rounds, the newest first. The FX keeps those rounds
// itself, so a reading always has all of them, however short the rounds or late the reading. Frozen or not, this is
// what the display draws: what the loop really did, round by round, its filters and saturation and all. Stop
// empties them in the FX (rounds since Stop read 0).
var echoReading = { level: 0, roundNow: 0, wholeRounds: [] };    // nothing drawn until the first reading
function recordEchoReading(values) {
  for (var i = 0; i < values.length; i++) {
    if (!(values[i] >= 0)) {
      error("2sl stab: the echo display got a reading of " + values.join(" ") + " (not all levels): ignored\n");
      return;
    }
  }
  if (values.length < 3) {
    error("2sl stab: the echo display got " + values.length + " values, not the level, the round now and whole " +
          "rounds (a wiring error): ignored\n");
    return;
  }
  echoReading = { level: values[0], roundNow: values[1], wholeRounds: values.slice(2) };
}
// Heights are in dB below the most the loop can carry: each side writes tanh(...) / 1.1 back, under 1 / 1.1, so
// |left| + |right| stays under 2 / 1.1 (fresh sound sent in can go over: drawn full). ECHO_RANGE_DB below is the bottom.
var ECHO_LOOP_CEILING = 2 / 1.1;
var ECHO_RANGE_DB = 48;
function echoRoundHeight(peak) {
  var db = 20 * Math.log(Math.max(peak, 1e-9) / ECHO_LOOP_CEILING) / Math.LN10;
  return Math.max(0, Math.min(1, 1 + db / ECHO_RANGE_DB));
}

function echoView(w, h) {
  var thrown = fade(S.throwAt, 900);
  viewLabel("echo");
  var state = S.freeze ? "frozen" : thrown > 0.05 ? "throw" : S.dub > 0 ? "dub " + Math.round(S.dub * 100) : "throws only";
  text(state, w - measure(state) - 4, 12, thrown > 0.05 ? T.warm : S.freeze ? T.mint : T.label);
  // the whole rounds, oldest on the left, then the round now on the far right, outlined (it is still growing)
  var rounds = echoReading.wholeRounds.slice().reverse().concat([echoReading.roundNow]);
  var top = 18, base = h - 8, gap = (w - 20) / Math.max(1, rounds.length - 1);
  for (var i = 0; i < rounds.length; i++) {
    var x = 6 + i * gap, bh = (base - top) * echoRoundHeight(rounds[i]);
    var isRoundNow = i === rounds.length - 1;
    if (bh < 1) rect(x, base - 1, 6, 1, T.rest);                  // silent: a dash
    else if (isRoundNow) frame(x, base - bh, 6, bh, T.mint);
    else rect(x, base - bh, 6, bh, T.mint);
  }
  rect(4, h - 4, (w - 8) * Math.min(1, echoReading.level * 3), 2, thrown > 0 ? T.warm : T.mint);  // tape level
  if (thrown > 0) frame(0, 0, w, h, T.warm, 2 * thrown);
}

// The pump's gain over a division: the same shape as the DSP (sine ramp in over Attack, recover over
// Release with Curve). Pump attack arrives in ms, release as a fraction of the division.
function pumpGain(ph) {
  var divms = 60000 / Math.max(20, S.tempo) / S.rate;     // at Live's tempo, as the DSP
  var atkf = Math.max(0.001, Math.min(0.3, (S.atk === undefined ? 6 : S.atk) / divms));
  var relEnd = Math.max(S.rel === undefined ? 0.55 : S.rel, atkf + 0.05);
  var duck;
  if (ph < atkf) duck = Math.sin(Math.PI / 2 * ph / atkf);
  else duck = Math.pow(1 - Math.max(0, Math.min(1, (ph - atkf) / (relEnd - atkf))), 1 + S.curve * 3);
  return 1 - S.depth * duck;
}

function pumpView(w, h) {
  viewLabel("pump");
  var pct = Math.round(S.depth * 100) + "%";
  text(pct, w - measure(pct) - 4, 12, S.depth > 0 ? T.ink : T.label);
  var top = 20, bot = h - 6;
  rgba(S.depth > 0 ? T.mint : T.rest);
  mgraphics.set_line_width(2);
  // two beats, so the duck reads as a repeating pump
  for (var x = 4; x <= w - 4; x++) {
    var ph = (((x - 4) / (w - 8)) * 2 * S.rate) % 1;
    var y = bot - (bot - top) * pumpGain(ph);
    if (x === 4) mgraphics.move_to(x, y); else mgraphics.line_to(x, y);
  }
  mgraphics.stroke();
  // Live's beat ramp is 0..1 per beat: mark the position in both beats
  var p = (S.phase % 1) / 2;
  rect(4 + p * (w - 8), top, 2, bot - top, T.now);
  rect(4 + (p + 0.5) * (w - 8), top, 2, bot - top, T.now, 0.45);
}

function envView(w, h) {
  viewLabel("envelope");
  var stretch = Math.pow(4, S.len);
  var a = Math.sqrt(S.atk), d = Math.sqrt(S.dec * stretch), r = Math.sqrt(S.rel * stretch), hold = 25;
  var total = a + d + hold + r, top = 20, bot = h - 6, H = bot - top, sx = (w - 12) / total;
  var x0 = 6, x1 = x0 + a * sx, x2 = x1 + d * sx, x3 = x2 + hold * sx, x4 = x3 + r * sx, sy = bot - H * S.sus;
  mgraphics.move_to(x0, bot);
  mgraphics.line_to(x1, top);
  mgraphics.curve_to(x1 + (x2 - x1) * 0.2, sy, x1 + (x2 - x1) * 0.5, sy, x2, sy);
  mgraphics.line_to(x3, sy);
  mgraphics.curve_to(x3 + (x4 - x3) * 0.2, bot, x3 + (x4 - x3) * 0.5, bot, x4, bot);
  rgba(T.mint, 0.22);
  mgraphics.fill_preserve();
  rgba(T.mint);
  mgraphics.set_line_width(2);
  mgraphics.stroke();
}

/** |H| of a 4-pole ladder with feedback k at frequency ratio x = f / fc. */
function ladder(x, k) {
  var re = 1, im = 0, gr = 1 / (1 + x * x), gi = -x / (1 + x * x);
  for (var i = 0; i < 4; i++) { var t = re * gr - im * gi; im = re * gi + im * gr; re = t; }
  var dr = 1 + k * re, di = k * im;
  return Math.sqrt((re * re + im * im) / (dr * dr + di * di)) * (1 + k * 0.4);
}

function filterView(w, h) {
  viewLabel("filter");
  var fc = S.cutoff * Math.pow(2, 2.5 * S.tone);
  var open = fc * Math.pow(2, 6 * Math.max(0, Math.min(1, S.envamt + 0.25 * S.tone)));
  var hz = fc < 1000 ? Math.round(fc) + " Hz" : (fc / 1000).toFixed(1) + " kHz";
  text(hz, w - measure(hz) - 4, 12, T.label);
  var k = S.reso * 3.8, top = 20, bot = h - 4;
  var curve = function (cut, col, lw, fill) {
    for (var x = 4; x <= w - 4; x++) {
      var f = 20 * Math.pow(1000, (x - 4) / (w - 8));
      var db = 20 * Math.log(Math.max(1e-6, ladder(f / Math.min(cut, 20000), k))) / Math.LN10;
      var y = top + (bot - top) * (12 - Math.max(-48, Math.min(12, db))) / 60;
      if (x === 4) mgraphics.move_to(x, y); else mgraphics.line_to(x, y);
    }
    if (fill) { mgraphics.line_to(w - 4, bot); mgraphics.line_to(4, bot); mgraphics.close_path(); rgba(col, 0.22); mgraphics.fill(); }
    else { rgba(col); mgraphics.set_line_width(lw); mgraphics.stroke(); }
  };
  curve(open, T.unlit, 1, false);
  curve(fc, T.mint, 0, true);
  curve(fc, T.mint, 2, false);
}

// The LFO's phase as read from the audio (snapshot~ of its phasor~, every 33 ms), with when each reading came,
// kept for the last few seconds: the LFO display draws its history from these, so a Rate change shows from where
// it happened. Phases are stored unwrapped (whole cycles counted), so the phase between two readings is a straight
// line between them, as the phasor~ runs at a steady rate. A ring of fixed arrays: nothing allocated per frame.
var LFO_READINGS_KEPT = 128;              // 4.2 s of readings at one per 33 ms: the display shows 2 s
var LFO_READINGS_STALE_MS = 250;          // no reading for this long: the audio is off, so the LFO is not running
var lfoReadingPhase = new Array(LFO_READINGS_KEPT);   // unwrapped, in cycles
var lfoReadingTime = new Array(LFO_READINGS_KEPT);    // ms (now())
var lfoReadingsCount = 0, lfoNewestReading = -1;

function recordLfoReading(phase) {
  if (!(phase >= 0 && phase <= 1)) {
    error("2sl stab: the " + MODE + " display got an LFO phase of " + phase + ", outside 0..1 (a wiring error): ignored\n");
    return;
  }
  var time = now(), unwrapped = phase;
  if (lfoReadingsCount > 0) {
    var previousPhase = lfoReadingPhase[lfoNewestReading], previousTime = lfoReadingTime[lfoNewestReading];
    var forward = phase - (previousPhase - Math.floor(previousPhase));
    forward -= Math.floor(forward);                       // 0..1: how far the phasor moved, less whole cycles
    // Whole cycles between readings: none at 33 ms and up to 12 Hz (0.4 of a cycle). After a longer gap (the UI
    // held up), the current Rate says how many went by.
    var wholeCycles = Math.max(0, Math.round(S.lforate * (time - previousTime) / 1000 - forward));
    unwrapped = previousPhase + forward + wholeCycles;
  }
  lfoNewestReading = (lfoNewestReading + 1) % LFO_READINGS_KEPT;
  lfoReadingPhase[lfoNewestReading] = unwrapped;
  lfoReadingTime[lfoNewestReading] = time;
  lfoReadingsCount = Math.min(lfoReadingsCount + 1, LFO_READINGS_KEPT);
}

/** The LFO's unwrapped phase at `time` (ms), from the readings: between two readings, the line between them;
 *  after the newest, carried on at the current Rate (it is at most a reading old), and held where it was if the
 *  readings stopped (the audio is off and the phasor~ with it). Before the oldest reading: null, nothing known. */
function lfoPhaseAt(time) {
  if (lfoReadingsCount === 0) return null;
  var newestTime = lfoReadingTime[lfoNewestReading];
  if (time >= newestTime) {
    var carried = Math.min(time, newestTime + LFO_READINGS_STALE_MS) - newestTime;
    return lfoReadingPhase[lfoNewestReading] + S.lforate * carried / 1000;
  }
  // newest to oldest: the first reading at or before `time`, and the one after it
  for (var back = 1; back < lfoReadingsCount; back++) {
    var earlier = (lfoNewestReading - back + LFO_READINGS_KEPT) % LFO_READINGS_KEPT;
    if (lfoReadingTime[earlier] > time) continue;
    var later = (earlier + 1) % LFO_READINGS_KEPT;
    var span = lfoReadingTime[later] - lfoReadingTime[earlier];
    var along = span > 0 ? (time - lfoReadingTime[earlier]) / span : 1;
    return lfoReadingPhase[earlier] + (lfoReadingPhase[later] - lfoReadingPhase[earlier]) * along;
  }
  return null;
}
/** The LFO now, as cos~ makes it from the phase (the DCO displays' PWM). Before any reading: phase 0. */
function lfoNow() {
  var phase = lfoPhaseAt(now());
  return Math.cos(2 * Math.PI * (phase === null ? 0 : phase));
}

/** DCO 1 or 2 as the voice makes it (without its anti-aliasing): two cycles of DCO 1, and DCO 2 over the same
 *  time, so Semi shows as more or fewer cycles. Pulse is the voice's saw minus a saw shifted by the pulse width
 *  (no DC: high 2 - 2w for a fraction w of the cycle, low -2w), and the width moves with PWM, on both DCOs. */
function oscView(w, h, n) {
  var names1 = ["saw", "pulse", "saw + pulse"], names2 = ["saw", "pulse", "triangle"];
  viewLabel(n === 1 ? "dco 1" : "dco 2");
  var wave = n === 1 ? S.wave1 | 0 : S.wave2 | 0;
  var usesWidth = n === 1 ? wave !== 0 : wave === 1;
  var pwText = usesWidth ? "  pw " + Math.round(S.pw * 100) : "";
  var info = n === 1 ? names1[wave] + pwText : names2[wave] + pwText +
    (S.semi ? "  " + (S.semi > 0 ? "+" : "") + S.semi + " st" : "") + "  +" + Math.round(S.fine) + " ct";
  text(info, w - measure(info) - 4, 12, T.label);
  var mid = 20 + (h - 24) / 2, amp = (h - 30) / 2;
  var width = Math.max(0.05, Math.min(0.95, S.pw + S.pwm * 0.35 * lfoNow()));
  rgba(T.mint);
  mgraphics.set_line_width(2);
  var cycles = n === 2 ? 2 * Math.pow(2, S.semi / 12) : 2;
  for (var x = 4; x <= w - 4; x++) {
    var ph = (((x - 4) / (w - 8)) * cycles) % 1, v;
    var saw = 2 * ph - 1, shifted = (ph + width) % 1, pulse = saw - (2 * shifted - 1), tri = 2 * Math.abs(2 * ph - 1) - 1;
    if (wave === 0) v = saw;
    else if (wave === 1) v = pulse;
    else v = n === 1 ? (saw + pulse) * 0.6 : tri;
    var y = mid - amp * v / 2;                                     // +-2: the pulse's widest swing
    if (x === 4) mgraphics.move_to(x, y); else mgraphics.line_to(x, y);
  }
  mgraphics.stroke();
}

/** The sub as the voice makes it: DCO 1 divided by 2 (-1 oct square) or 4 (-2 oct square, 25% pulse, the pulse
 *  +1 for a quarter and -1 the rest, plus 0.5 as in the voice), over the same time as DCO 1's display (two DCO 1
 *  cycles), so -1 oct shows one cycle and -2 oct half of one. The window starts on the DCO 1 cycle that puts
 *  an edge of the sub in the middle, so the half cycle reads as the wave it is. */
function subView(w, h) {
  var names = ["-1 oct square", "-2 oct square", "-2 oct 25% pulse"];
  var mode = Math.max(0, Math.min(2, S.submode | 0));
  viewLabel("sub");
  text(names[mode], w - measure(names[mode]) - 4, 12, T.label);
  var mid = 20 + (h - 24) / 2, amp = (h - 30) / 2;
  var division = mode === 0 ? 2 : 4;                      // DCO 1 cycles per sub cycle
  var firstCycle = mode === 0 ? 0 : mode === 1 ? 1 : 3;    // where the window starts (in DCO 1 cycles)
  rgba(T.mint);
  mgraphics.set_line_width(2);
  for (var x = 4; x <= w - 4; x++) {
    var dco1Cycles = firstCycle + ((x - 4) / (w - 8)) * 2;
    var phase = (dco1Cycles / division) % 1, v;
    if (mode === 2) v = (phase < 0.25 ? 1 : -1) + 0.5;
    else v = phase < 0.5 ? 1 : -1;
    var y = mid - amp * v / 2;                             // +-2, the DCO displays' scale
    if (x === 4) mgraphics.move_to(x, y); else mgraphics.line_to(x, y);
  }
  mgraphics.stroke();
}

/** The LFO moving, and how much goes where. */
function lfoView(w, h) {
  viewLabel("lfo");
  var r = S.lforate < 1 ? S.lforate.toFixed(2) : S.lforate.toFixed(1);
  var info = r + " Hz";
  text(info, w - measure(info) - 4, 12, T.label);
  var top = 20, bot = h - 18, mid = (top + bot) / 2, amp = (bot - top) / 2;
  rgba(T.mint);
  mgraphics.set_line_width(2);
  var drawingNow = now(), lineStarted = false;
  for (var x = 4; x <= w - 4; x++) {
    var secondsAgo = (w - 4 - x) / (w - 8) * 2;                      // the last two seconds, scrolling
    var phase = lfoPhaseAt(drawingNow - secondsAgo * 1000);
    if (phase === null) continue;                                     // before the first reading: nothing known
    var y = mid - amp * Math.cos(2 * Math.PI * phase);
    if (!lineStarted) { mgraphics.move_to(x, y); lineStarted = true; } else mgraphics.line_to(x, y);
  }
  if (lineStarted) mgraphics.stroke();
  var targets = [["pwm", S.pwm], ["vibrato", S.vib], ["filter", S.lfofilt]];
  var x0 = 4;
  for (var i = 0; i < targets.length; i++) {
    var on = targets[i][1] > 0;
    var label = targets[i][0] + (on ? " " + Math.round(targets[i][1] * 100) : "");
    text(label, x0, h - 3, on ? T.ink : T.rest);
    x0 += measure(label) + 12;
  }
}

/** The FX's drive as the DSP does it: out = tanh(in x (1 + 5 Drive)) / (1 + 2.2 Drive), for an input from -1 to
 *  +1 (full scale) across and the output on the same scale up, so turning Drive up also shows it turning down. */
function driveView(w, h) {
  viewLabel("drive");
  var top = 20, bot = h - 6, H = bot - top, x0 = 6, x1 = w - 6;
  rect(x0, top + H / 2, x1 - x0, 1, T.rest);
  rgba(T.mint);
  mgraphics.set_line_width(2);
  var g = 1 + S.drive * 5, norm = 1 / (1 + S.drive * 2.2);
  for (var x = x0; x <= x1; x++) {
    var vin = ((x - x0) / (x1 - x0)) * 2 - 1;
    var vout = tanh(vin * g) * norm;
    var y = top + H / 2 - vout * (H / 2);
    if (x === x0) mgraphics.move_to(x, y); else mgraphics.line_to(x, y);
  }
  mgraphics.stroke();
}
