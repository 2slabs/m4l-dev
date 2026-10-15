// 2sl stab: everything drawn (jsui), in the 2sl-ui look. One file, several views, chosen by jsarguments:
//   chrome  the device background: rules between sections, labels and hints (per page)
//   link    the 2sl wordmark chip: hover shows 2sl.to, click opens it
//   chord   big chord name, its notes, a lit keyboard            (from the chord brain)
//   steps   the machine's 16 steps: click to edit; playhead, hits, throws, status line
//   echo    the dub echo: repeats decaying (more and darker with Dub), throws, freeze, live level
//   pump    the duck curve over a beat, with a moving playhead
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
  level: 0, throwAt: 0, phase: 0,
  tempo: 120,                       // Live's tempo (the pump), until Live reports it
  lfophase: 0, lfophaseAt: 0        // the LFO's phase (0..1) as last read from the audio, and when
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
  else if (m === "lfophase") { S.lfophase = a[0]; S.lfophaseAt = now(); }
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

// Frozen, the loop feeds back at 105% through tape saturation, tanh(1.05 x 1.1 a) / 1.1 per time round: it
// swells until it holds where that equals a. The level the loop settles at, in the echo's own units:
var FROZEN_LOOP_HOLD = (function () {
  var a = 1;
  for (var i = 0; i < 200; i++) a = tanh(1.05 * 1.1 * a) / 1.1;
  return a;
})();

function echoView(w, h) {
  var thrown = fade(S.throwAt, 900);
  var fb = Math.max(0.3 + S.dub * 0.62, thrown * 0.9);
  var on = S.dub > 0 || thrown > 0 || S.freeze;
  viewLabel("echo");
  var state = S.freeze ? "frozen" : thrown > 0.05 ? "throw" : S.dub > 0 ? "dub " + Math.round(S.dub * 100) : "throws only";
  text(state, w - measure(state) - 4, 12, thrown > 0.05 ? T.warm : S.freeze ? T.mint : T.label);
  var top = 18, base = h - 8, n = 10, gap = (w - 20) / n;
  rect(6, top, 6, base - top, T.ink);                          // the stab
  // frozen: the repeats from the loop's level now (the level line: both sides, so 2 x the loop's amplitude),
  // each time round a little louder, to full height where saturation holds it
  var amp = S.freeze ? Math.max(0.05, Math.min(1, S.level / (2 * FROZEN_LOOP_HOLD))) : 1;
  for (var i = 1; i <= n; i++) {                                // its repeats, darker each time round
    if (S.freeze) amp = tanh(1.05 * 1.1 * amp * FROZEN_LOOP_HOLD) / 1.1 / FROZEN_LOOP_HOLD;
    else amp *= fb;
    var x = 6 + i * gap, bh = Math.max(1, (base - top) * amp);
    var col = S.freeze ? T.mint : mix(T.mint, T.rest, Math.min(1, i / (2 + S.dub * 8)));
    if (on) rect(x, base - bh, 6, bh, col);
    else frame(x, base - bh, 6, bh, T.rest);
  }
  rect(4, h - 4, (w - 8) * Math.min(1, S.level * 3), 2, thrown > 0 ? T.warm : T.mint);  // tape level
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

/** The LFO's phase `secondsAgo` before now: its phase as last read from the audio (snapshot~ of the LFO's
 *  phasor~, every 33 ms), carried on at its rate. The LFO itself is cos~ of that phase. */
function lfoPhase(secondsAgo) {
  var since = (now() - S.lfophaseAt) / 1000 - (secondsAgo || 0);
  var phase = S.lfophase + S.lforate * since;
  return phase - Math.floor(phase);
}
function lfoNow() { return Math.cos(2 * Math.PI * lfoPhase(0)); }

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

/** The LFO moving, and how much goes where. */
function lfoView(w, h) {
  viewLabel("lfo");
  var r = S.lforate < 1 ? S.lforate.toFixed(2) : S.lforate.toFixed(1);
  var info = r + " Hz";
  text(info, w - measure(info) - 4, 12, T.label);
  var top = 20, bot = h - 18, mid = (top + bot) / 2, amp = (bot - top) / 2;
  rgba(T.mint);
  mgraphics.set_line_width(2);
  for (var x = 4; x <= w - 4; x++) {
    var secondsAgo = (w - 4 - x) / (w - 8) * 2;                      // the last two seconds, scrolling
    var y = mid - amp * Math.cos(2 * Math.PI * lfoPhase(secondsAgo));
    if (x === 4) mgraphics.move_to(x, y); else mgraphics.line_to(x, y);
  }
  mgraphics.stroke();
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
