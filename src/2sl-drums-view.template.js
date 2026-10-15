// 2sl drums' displays (inserted into the kit view template by src/2sl-drums.py):
//   grid    the pattern: a row per voice, 16 steps, the rows Voice picks lit; click a step to edit it, a name to
//           pick that row (Voice)
//   status  voice, function, Seed; the settings; what is shown (or a warning); where the history is
//   mix     each voice's level, flashing on its hits, dimmed when the mixer's mute / solo silence it
//   bd sd rs cp hats rd   each voice's envelope as the voice makes it (src/2sl_drums_dsp.py), flashing on hits
var VOICE_NAMES = /*VOICE_NAMES*/;
var VOICE_IDS = /*VOICE_IDS*/;                 // the mixer's messages are <id>_level, <id>_mute, <id>_solo
var MIX_STRIP_W = /*MIX_STRIP_W*/;             // the mixer's strip pitch, as the generator lays out its dials
var STEPS = 16;
var GRADE_CHARACTERS = ".oxX";
var VOICE_OF_MODE = /*VOICE_OF_MODE*/;         // a voice display's mode -> the voices (VOICES order) it flashes for

var DEVICE_STATE = {
  rows: [], chosen: VOICE_NAMES.length, pos: -1, flash: {}, head: "", settings: "", note: "", noteLoud: 0,
  historyAt: 0, historyLength: 0, historyLabel: "",
  hitAt: {}, hitVelocity: {}
};
(function () {
  for (var v = 0; v < VOICE_IDS.length; v++) {
    DEVICE_STATE[VOICE_IDS[v] + "_mute"] = 0;
    DEVICE_STATE[VOICE_IDS[v] + "_solo"] = 0;
  }
})();
var ANIMATED_MODES = ["grid", "mix", "bd", "sd", "rs", "cp", "hats", "rd"];

function deviceMessage(m, a) {
  if (m === "rows") { S.rows = a.map(String); return true; }
  if (m === "chosen") { S.chosen = a[0]; return true; }                // a voice, or VOICE_NAMES.length: all
  if (m === "pos") { S.pos = a[0]; return true; }
  if (m === "head") { S.head = a.join(" "); return true; }
  if (m === "settings") { S.settings = a.join(" "); return true; }
  if (m === "note") { S.note = String(a[0]); S.noteLoud = a[1] ? 1 : 0; return true; }
  if (m === "history") { S.historyAt = a[0]; S.historyLength = a[1]; S.historyLabel = a.slice(2).join(" "); return true; }
  if (m === "hit") {
    if (MODE === "grid") S.flash[a[0] * STEPS + a[1]] = now();    // hit voice step
    else { S.hitAt[a[0]] = now(); S.hitVelocity[a[0]] = a[1]; }   // hit voice velocity
    return true;
  }
  return false;
}

// ---- the grid -------------------------------------------------------------------------------------------
var GRID_LABEL_W = 24;
function gridGeometry(w, h) {
  var rowH = Math.floor((h - 1) / VOICE_NAMES.length);
  var cellW = Math.floor((w - GRID_LABEL_W - 2) / STEPS);
  return { rowH: rowH, cellW: cellW, stepsX: GRID_LABEL_W };
}

function gridView(w, h) {
  var g = gridGeometry(w, h);
  for (var v = 0; v < VOICE_NAMES.length; v++) {
    var y = 1 + v * g.rowH, row = S.rows[v] || "", chosen = S.chosen === v || S.chosen === VOICE_NAMES.length;
    // the rows Voice picks: their names are lit chips
    if (chosen) chip(VOICE_NAMES[v], 1, y + Math.floor((g.rowH - 2 - 15) / 2), T.inverse, T.ink);
    else text(VOICE_NAMES[v], 5, y + Math.floor((g.rowH - 2 - 15) / 2) + 12, T.label);
    for (var s = 0; s < STEPS; s++) {
      var grade = GRADE_CHARACTERS.indexOf(row.charAt(s)), x = g.stepsX + s * g.cellW;
      var fill = grade === 3 ? T.mint : grade === 2 ? mix(T.mint, T.well, 0.45) : grade === 1 ? mix(T.mint, T.well, 0.78)
               : (s % 4 === 0 ? T.beat : T.rest);
      rect(x + 1, y, g.cellW - 2, g.rowH - 2, fill);
      if (grade === 3) rect(x + 1, y, g.cellW - 2, 2, T.ink);              // accents carry a bar on top
      var flashed = S.flash[v * STEPS + s] ? fade(S.flash[v * STEPS + s], 200) : 0;
      if (flashed > 0) rect(x + 1, y, g.cellW - 2, g.rowH - 2, T.ink, flashed * 0.7);
    }
  }
  if (S.pos >= 0) frame(g.stepsX + S.pos * g.cellW, 0, g.cellW, g.rowH * VOICE_NAMES.length + 1, T.now, 2);
}

function gridClick(x, y, modifiers) {
  var g = gridGeometry(mgraphics.size[0], mgraphics.size[1]);
  var v = Math.floor((y - 1) / g.rowH);
  if (v < 0 || v >= VOICE_NAMES.length) return;
  if (x < g.stepsX) outlet(0, "name_click", v);                        // the brain moves Voice
  else if (x < g.stepsX + STEPS * g.cellW) {
    var s = Math.max(0, Math.min(STEPS - 1, Math.floor((x - g.stepsX) / g.cellW)));
    if (modifiers.shift) outlet(0, "edit", v, s, 1);                     // shift-click: a ghost
    else outlet(0, "edit", v, s);
  }
}

// ---- the status line ---------------------------------------------------------------------------------------------
/** `str` cut to fit `w` px, with an ellipsis-like ".." when cut (Cozette is 6 px a character). */
function fitted(str, w) {
  str = String(str);
  if (measure(str) <= w) return str;
  while (str.length > 0 && measure(str + "..") > w) str = str.slice(0, -1);
  return str + "..";
}
function statusView(w, h) {
  text(fitted(S.head, w - 8), 4, 13, T.ink);
  text(fitted(S.settings, w - 8), 4, 28, T.ink);
  text(fitted(S.note, w - 8), 4, 43, S.noteLoud ? T.now : T.label);
  var where = S.historyLength ? "history " + S.historyAt + "/" + S.historyLength + "  " : "";
  text(fitted(where + S.historyLabel, w - 8), 4, 58, T.label);
}

// ---- mix -------------------------------------------------------------------------------------------------------
/** Whether voice v sounds: the mixer's rule in the voices (a mute wins; while any is soloed, only soloed ones). */
function sounds(v) {
  var anySolo = false;
  for (var i = 0; i < VOICE_IDS.length; i++) if (S[VOICE_IDS[i] + "_solo"] > 0) anySolo = true;
  var id = VOICE_IDS[v];
  return !(S[id + "_mute"] > 0) && (!anySolo || S[id + "_solo"] > 0);
}
function mixView(w, h) {
  viewLabel("mix");
  var top = 18, bottom = h - 16;
  for (var v = 0; v < VOICE_NAMES.length; v++) {
    var level = S[VOICE_IDS[v] + "_level"] || 0, x = v * MIX_STRIP_W + 22, live = sounds(v);
    var flashed = S.hitAt[v] && live ? fade(S.hitAt[v], 180) : 0;
    rect(x - 6, top, 12, bottom - top, T.rest);
    var levelTop = bottom - (bottom - top) * Math.max(0, Math.min(1, level));
    rect(x - 6, levelTop, 12, bottom - levelTop, live ? mix(T.unlit, T.mint, flashed > 0 ? 1 : 0.35) : T.beat);
    if (flashed > 0) rect(x - 6, bottom - (bottom - top) * level * (S.hitVelocity[v] || 1), 12, 2, T.ink, flashed);
    text(VOICE_NAMES[v], x - measure(VOICE_NAMES[v]) / 2, h - 3, live ? T.label : T.rest);
  }
}

// ---- the voices: their envelopes, as src/2sl_drums_dsp.py makes them -----------------------------------------
/** An exponential decay that falls 40 dB in `decayMs`, at `ms`. */
function decayAt(ms, decayMs) { return Math.exp(-4.6 * ms / Math.max(decayMs, 0.001)); }

/** Draw `curve(ms)` (0..1) over `windowMs` across the display, in `colour`. */
function drawCurve(w, h, windowMs, curve, colour, lineWidth) {
  var top = 18, bottom = h - 4;
  rgba(colour);
  mgraphics.set_line_width(lineWidth || 2);
  for (var x = 4; x <= w - 4; x++) {
    var ms = (x - 4) / (w - 8) * windowMs;
    var y = bottom - (bottom - top) * Math.max(0, Math.min(1, curve(ms)));
    if (x === 4) mgraphics.move_to(x, y); else mgraphics.line_to(x, y);
  }
  mgraphics.stroke();
}
function hitFrame(w, h) {
  var voicesHere = VOICE_OF_MODE[MODE] || [];
  for (var i = 0; i < voicesHere.length; i++) {
    var flashed = S.hitAt[voicesHere[i]] ? fade(S.hitAt[voicesHere[i]], 200) : 0;
    if (flashed > 0) frame(0, 0, w, h, T.ink, 2 * flashed);
  }
}
function milliseconds(ms) { return ms < 1000 ? Math.round(ms) + " ms" : (ms / 1000).toFixed(1) + " s"; }

function bdView(w, h) {
  viewLabel("bd");
  viewInfo(Math.round(S.bd_tune) + " Hz  " + milliseconds(S.bd_decay) + (S.bd_bits < 16 ? "  " + Math.round(S.bd_bits) + " bit" : ""), w);
  var windowMs = S.bd_decay * 1.2, soft = S.bd_soft;
  var sweep = S.bd_sweep * (1 - 0.75 * soft), pitchDecay = 30 + 90 * soft, fadeMs = 0.05 + 5 * soft;
  drawCurve(w, h, windowMs, function (ms) { return (1 + 3 * sweep * decayAt(ms, pitchDecay)) / 4; }, T.unlit, 1);
  drawCurve(w, h, windowMs, function (ms) {
    var e = decayAt(ms, S.bd_decay);
    return (1 - (1 - e) * (1 - e)) * Math.min(1, ms / fadeMs);
  }, T.mint, 2);
  hitFrame(w, h);
}

function sdView(w, h) {
  viewLabel("sd");
  viewInfo(Math.round(S.sd_tune) + " Hz  tone " + milliseconds(S.sd_tone), w);
  var windowMs = Math.max(260, S.sd_tone + 120);
  drawCurve(w, h, windowMs, function (ms) {
    return S.sd_snappy * (ms < 24 ? 1 : decayAt(ms - 24, S.sd_tone));
  }, T.unlit, 1);
  drawCurve(w, h, windowMs, function (ms) { return 0.6 * decayAt(ms, 180) + 0.4 * decayAt(ms, 90); }, T.mint, 2);
  hitFrame(w, h);
}

function rsView(w, h) {
  viewLabel("rs");
  viewInfo("500 220 1000 Hz", w);
  drawCurve(w, h, 100, function (ms) { return decayAt(ms, 40); }, T.mint, 2);
  hitFrame(w, h);
}

function cpView(w, h) {
  viewLabel("cp");
  var spacing = 11;
  drawCurve(w, h, 260, function (ms) {
    var claps = ms < 3 * spacing ? Math.pow(1 - (ms / spacing - Math.floor(ms / spacing)), 3)
                                 : Math.exp(-(ms - 3 * spacing) / 20);
    return (claps + 0.4 * Math.exp(-ms / 150)) / 1.4;
  }, T.mint, 2);
  hitFrame(w, h);
}

function hatsView(w, h) {
  viewLabel("hats");
  viewInfo(Math.round(30 * S.hat_tune) + " kHz rom  " + Math.round(S.hat_bits) + " bit", w);
  var windowMs = S.oh_decay * 1.1;
  drawCurve(w, h, windowMs, function (ms) { return decayAt(ms, S.oh_decay); }, T.unlit, 1);
  drawCurve(w, h, windowMs, function (ms) { return decayAt(ms, S.ch_decay); }, T.mint, 2);
  hitFrame(w, h);
}

function rdView(w, h) {
  var lengthMs = 1600 / S.rd_tune;
  viewLabel("rd");
  viewInfo(milliseconds(lengthMs) + "  " + Math.round(S.rd_bits) + " bit", w);
  drawCurve(w, h, lengthMs * 1.1, function (ms) { return decayAt(ms, lengthMs); }, T.mint, 2);
  hitFrame(w, h);
}

var VIEW_PAINTERS = { grid: gridView, status: statusView, mix: mixView, bd: bdView, sd: sdView, rs: rsView, cp: cpView,
                      hats: hatsView, rd: rdView };
var VIEW_CLICKS = { grid: gridClick };
