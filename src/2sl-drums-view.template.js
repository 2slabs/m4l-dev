// 2sl drums' displays (inserted into the kit view template by src/2sl-drums.py):
//   grid    the pattern: a row per voice, 16 steps; click to edit, mute (name), lock (L), reroll (R)
//   style   the style, its sources' tempo and swing, the canned kit, where the rows came from, the fill phrase
//   mix     each voice's level, flashing on its hits
//   bd sd rs cp hats rd   each voice's envelope as the voice makes it (src/2sl_drums_dsp.py), flashing on hits
var VOICE_NAMES = /*VOICE_NAMES*/;
var STEPS = 16;
var GRADE_CHARACTERS = ".oxX";
var VOICE_OF_MODE = { bd: [0], sd: [1], rs: [2], cp: [3], hats: [4, 5], rd: [6] };

var DEVICE_STATE = {
  rows: [], locks: [], mutes: [], sources: [], pos: -1, fillbar: 0, flash: {},
  styleName: "", styleTempo: "", styleSwing: "", kitName: "", bar: 0, barsInPhrase: 0,
  hitAt: {}, hitVelocity: {}
};
var ANIMATED_MODES = ["grid", "mix", "bd", "sd", "rs", "cp", "hats", "rd"];

function deviceMessage(m, a) {
  if (m === "rows") { S.rows = a.map(String); return true; }
  if (m === "locks") { S.locks = a; return true; }
  if (m === "mutes") { S.mutes = a; return true; }
  if (m === "sources") { S.sources = a.map(String); return true; }
  if (m === "pos") { S.pos = a[0]; return true; }
  if (m === "fillbar") { S.fillbar = a[0]; return true; }
  if (m === "style") {
    S.styleName = String(a[0]); S.styleTempo = String(a[1]); S.styleSwing = String(a[2]); S.kitName = String(a[3]);
    return true;
  }
  if (m === "bar") { S.bar = a[0]; S.barsInPhrase = a[1]; return true; }
  if (m === "hit") {
    if (MODE === "grid") S.flash[a[0] * STEPS + a[1]] = now();    // hit voice step
    else { S.hitAt[a[0]] = now(); S.hitVelocity[a[0]] = a[1]; }   // hit voice velocity
    return true;
  }
  return false;
}

// ---- the grid -------------------------------------------------------------------------------------------
var GRID_LABEL_W = 24, GRID_SIDE_W = 18;
function gridGeometry(w, h) {
  var rowH = Math.floor((h - 1) / VOICE_NAMES.length);
  var cellW = Math.floor((w - GRID_LABEL_W - 2 * GRID_SIDE_W - 4) / STEPS);
  var stepsX = GRID_LABEL_W, lockX = stepsX + cellW * STEPS + 4;
  return { rowH: rowH, cellW: cellW, stepsX: stepsX, lockX: lockX, rerollX: lockX + GRID_SIDE_W };
}

function gridView(w, h) {
  var g = gridGeometry(w, h);
  for (var v = 0; v < VOICE_NAMES.length; v++) {
    var y = 1 + v * g.rowH, row = S.rows[v] || "", muted = S.mutes[v] > 0;
    text(VOICE_NAMES[v], 4, y + 10, muted ? T.rest : T.ink);
    if (muted) rect(3, y + 6, measure(VOICE_NAMES[v]) + 2, 1, T.warm);
    for (var s = 0; s < STEPS; s++) {
      var grade = GRADE_CHARACTERS.indexOf(row.charAt(s)), x = g.stepsX + s * g.cellW;
      var fill = grade === 3 ? T.mint : grade === 2 ? mix(T.mint, T.well, 0.45) : grade === 1 ? mix(T.mint, T.well, 0.78)
               : (s % 4 === 0 ? T.beat : T.rest);
      if (muted && grade > 0) fill = mix(fill, T.well, 0.6);
      rect(x + 1, y, g.cellW - 2, g.rowH - 2, fill);
      if (grade === 3) rect(x + 1, y, g.cellW - 2, 2, T.ink);              // accents carry a bar on top
      var flashed = S.flash[v * STEPS + s] ? fade(S.flash[v * STEPS + s], 200) : 0;
      if (flashed > 0) rect(x + 1, y, g.cellW - 2, g.rowH - 2, T.ink, flashed * 0.7);
    }
    if (S.locks[v] > 0) chip("L", g.lockX, y - 2, T.pad, T.ink);
    else text("L", g.lockX + 4, y + 10, T.unlit);
    text("R", g.rerollX + 4, y + 10, S.locks[v] > 0 ? T.rest : T.label);
  }
  if (S.pos >= 0) frame(g.stepsX + S.pos * g.cellW, 0, g.cellW, g.rowH * VOICE_NAMES.length + 1, T.now, 2);
  if (S.fillbar) frame(0, 0, w, h, T.warm, 1);
}

function gridClick(x, y, modifiers) {
  var g = gridGeometry(mgraphics.size[0], mgraphics.size[1]);
  var v = Math.floor((y - 1) / g.rowH);
  if (v < 0 || v >= VOICE_NAMES.length) return;
  if (x < g.stepsX) outlet(0, "mute", v);
  else if (x < g.stepsX + STEPS * g.cellW) {
    var s = Math.max(0, Math.min(STEPS - 1, Math.floor((x - g.stepsX) / g.cellW)));
    if (modifiers.shift) outlet(0, "edit", v, s, 1);                     // shift-click: a ghost
    else outlet(0, "edit", v, s);
  } else if (x < g.rerollX) outlet(0, "lock", v);
  else outlet(0, "reroll", v);
}

// ---- style ---------------------------------------------------------------------------------------------------
function styleView(w, h) {
  viewLabel("style");
  if (S.barsInPhrase > 0) viewInfo("bar " + S.bar + "/" + S.barsInPhrase, w, S.fillbar ? T.warm : T.label);
  text(S.styleName, 4, 28, T.ink);
  text(S.styleTempo + "  swing " + S.styleSwing, 4, 42, T.label);
  text("kit: " + S.kitName, 4, 56, T.label);
}

// ---- mix -------------------------------------------------------------------------------------------------------
function mixView(w, h) {
  viewLabel("mix");
  var top = 18, bottom = h - 16, columnW = (w - 8) / VOICE_NAMES.length;
  for (var v = 0; v < VOICE_NAMES.length; v++) {
    var level = S[VOICE_IDS_FOR_LEVEL[v] + "_level"] || 0, x = 4 + v * columnW + columnW / 2;
    var flashed = S.hitAt[v] ? fade(S.hitAt[v], 180) : 0;
    rect(x - 6, top, 12, bottom - top, T.rest);
    var levelTop = bottom - (bottom - top) * Math.max(0, Math.min(1, level));
    rect(x - 6, levelTop, 12, bottom - levelTop, mix(T.unlit, T.mint, flashed > 0 ? 1 : 0.35));
    if (flashed > 0) rect(x - 6, bottom - (bottom - top) * level * (S.hitVelocity[v] || 1), 12, 2, T.ink, flashed);
    text(VOICE_NAMES[v], x - measure(VOICE_NAMES[v]) / 2, h - 3, T.label);
  }
}
var VOICE_IDS_FOR_LEVEL = ["bd", "sd", "rs", "cp", "ch", "oh", "rd"];

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

var VIEW_PAINTERS = { grid: gridView, style: styleView, mix: mixView, bd: bdView, sd: sdView, rs: rsView, cp: cpView,
                      hats: hatsView, rd: rdView };
var VIEW_CLICKS = { grid: gridClick };
