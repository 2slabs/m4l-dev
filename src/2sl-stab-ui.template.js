// 2sl stab: pages, presets and theme. Generated from src/2sl-stab-ui.template.js by src/2sl-stab.py; edit there.
//   page i      show the play (0), osc (1) or shape (2) page
//   int i       Preset menu: set every control to preset i
//   ready       sent once the device has loaded (Live has restored the saved values by then)
//   theme       Live's colour theme changed (from live.colors): recolour controls, redraw displays
//   stop        turn Freeze off (part of the Stop action)
// out 0: messages for [thispatcher]
inlets = 1;
outlets = 1;

var PAGES = /*PAGES*/;
var PRESETS = /*PRESETS*/;
var CONTROLS = /*CONTROLS*/;
var VIEWS = /*VIEWS*/;
/*THEME_FROM_LIVE*/
var current = 0;
var ready = 0;

function show() {
  var names = ["play", "osc", "shape"];
  for (var i = 0; i < names.length; i++) {
    var list = PAGES[names[i]];
    for (var k = 0; k < list.length; k++) outlet(0, "script", "sendbox", list[k], "hidden", i === current ? 0 : 1);
  }
}

function page(i) {
  current = Math.max(0, Math.min(2, Math.round(i)));
  show();
}

function msg_int(i) {
  // Ignore the Preset menu while Live restores the set, so saved tweaks win.
  if (!ready || i < 0 || i >= PRESETS.length) return;
  var p = PRESETS[i];
  for (var name in p) {
    var obj = this.patcher.getnamed(name);
    if (obj) obj.message(p[name]);
  }
}

function msg_float(v) {
  msg_int(Math.round(v));
}

// ---- 2sl colours on Live's controls ---------------------------------------------------------

function paint(name, attrs) {
  var obj = this.patcher.getnamed(name);
  if (!obj) return;
  for (var a in attrs) obj.message([a].concat(attrs[a]));
}

function recolor() {
  var t = themeFromLive("controls");
  var clear = [0, 0, 0, 0];
  var i;
  // dials: an ink arc on an unlit track, labels in the label colour, focus in "now" blue
  for (i = 0; i < CONTROLS.dial.length; i++) paint(CONTROLS.dial[i], {
    activedialcolor: t.ink, dialcolor: t.rest, activeneedlecolor: t.ink, needlecolor: t.unlit,
    activefgdialcolor: t.ink, fgdialcolor: t.unlit, textcolor: t.label, panelcolor: clear, focusbordercolor: t.now
  });
  // toggles and buttons: 2sl chips, inverted when on
  for (i = 0; i < CONTROLS.text.length; i++) paint(CONTROLS.text[i], {
    activebgcolor: t.pad, activebgoncolor: t.ink, activetextcolor: t.ink, activetextoncolor: t.inverse,
    bgcolor: t.pad, bgoncolor: t.unlit, textcolor: t.label, textoffcolor: t.label, bordercolor: t.ink,
    focusbordercolor: t.now
  });
  for (i = 0; i < CONTROLS.menu.length; i++) paint(CONTROLS.menu[i], {
    activebgcolor: t.pad, textcolor: t.ink, tricolor: t.ink, bordercolor: t.ink, focusbordercolor: t.now,
    hltcolor: t.now, hlttextcolor: t.inverse
  });
  for (i = 0; i < CONTROLS.tab.length; i++) paint(CONTROLS.tab[i], {
    activebgcolor: t.pad, activebgoncolor: t.ink, textcolor: t.ink, textoncolor: t.inverse,
    bgcolor: t.pad, bgoncolor: t.unlit, inactivetextoffcolor: t.label, inactivetextoncolor: t.inverse,
    bordercolor: t.ink, focusbordercolor: t.now
  });
  for (i = 0; i < CONTROLS.numbox.length; i++) paint(CONTROLS.numbox[i], {
    activebgcolor: t.pad, textcolor: t.ink, bordercolor: t.ink, activeslidercolor: t.now, tricolor: t.ink,
    activetricolor: t.ink, focusbordercolor: t.now
  });
  for (i = 0; i < VIEWS.length; i++) {
    var v = this.patcher.getnamed(VIEWS[i]);
    if (v) v.message("theme");
  }
}

function anything() {
  if (messagename === "stop") {
    var f = this.patcher.getnamed("freeze");
    if (f) f.message(0);
    return;
  }
  if (messagename === "theme") {
    recolor();
    return;
  }
  if (messagename === "ready") {
    ready = 1;
    show();
    recolor();
  }
}
