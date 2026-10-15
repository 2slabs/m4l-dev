// 2sl stab: pages and theme. Generated from src/2sl-stab-ui.template.js by src/2sl-stab.py; edit there.
//   page i      show the play (0), osc (1) or shape (2) page
//   ready       sent once the device has loaded: show the page, colour the controls
//   theme       Live's colour theme changed (from live.colors): recolour controls, redraw displays
//   stop        turn Freeze off (part of the Stop action)
// out 0: messages for [thispatcher]
inlets = 1;
outlets = 1;

var PAGES = {"play": ["view_chord", "chord", "in_key", "tone", "length", "drift", "view_steps", "machine", "latch", "pattern", "density", "throws", "gate", "shift", "view_echo", "throw", "freeze", "dub", "echo_time", "view_pump", "pump_rate", "pump", "pump_attack", "pump_release", "pump_curve"], "osc": ["view_sub", "sub_mode", "view_osc1", "dco1_wave", "dco1_octave", "pw", "pwm", "view_osc2", "dco2_wave", "dco2_octave", "semi", "fine", "osc_1", "osc_2", "sub", "noise", "view_lfo", "lfo_rate", "vibrato", "lfo_filter"], "shape": ["view_filter", "cutoff", "resonance", "env_amount", "key_track", "velocity_filter", "view_env", "attack", "decay", "sustain", "release", "view_drive", "drive"]};
var CONTROLS = {"dial": ["tone", "length", "drift", "density", "throws", "gate", "shift", "dub", "pump", "pump_attack", "pump_release", "pump_curve", "pw", "pwm", "semi", "fine", "osc_1", "osc_2", "sub", "noise", "lfo_rate", "vibrato", "lfo_filter", "cutoff", "resonance", "env_amount", "key_track", "velocity_filter", "attack", "decay", "sustain", "release", "drive"], "text": ["stop", "in_key", "machine", "latch", "throw", "freeze"], "menu": ["chord", "pattern", "echo_time", "pump_rate"], "tab": ["page", "sub_mode", "dco1_wave", "dco1_octave", "dco2_wave", "dco2_octave"], "numbox": ["volume"]};
var VIEWS = ["view_chrome", "view_link", "view_chord", "view_steps", "view_echo", "view_pump", "view_sub", "view_osc1", "view_osc2", "view_lfo", "view_filter", "view_env", "view_drive"];
var THEMES = {"dark": {"pad": [0.149, 0.149, 0.149, 1], "well": [0.106, 0.106, 0.11, 1], "ink": [0.835, 0.847, 0.859, 1], "inverse": [0.149, 0.149, 0.149, 1], "label": [0.557, 0.58, 0.608, 1], "unlit": [0.494, 0.518, 0.545, 1], "mint": [0.447, 0.871, 0.761, 1], "now": [0.176, 0.357, 1.0, 1], "warm": [1.0, 0.55, 0.2, 1], "rest": [0.2, 0.2, 0.21, 1], "beat": [0.26, 0.27, 0.28, 1], "key": [0.72, 0.73, 0.74, 1], "keyBlack": [0.07, 0.07, 0.08, 1]}, "light": {"pad": [0.835, 0.847, 0.859, 1], "well": [0.77, 0.78, 0.79, 1], "ink": [0.0, 0.0, 0.0, 1], "inverse": [1.0, 1.0, 1.0, 1], "label": [0.349, 0.369, 0.396, 1], "unlit": [0.451, 0.475, 0.502, 1], "mint": [0.12, 0.55, 0.45, 1], "now": [0.176, 0.357, 1.0, 1], "warm": [0.85, 0.38, 0.0, 1], "rest": [0.7, 0.71, 0.73, 1], "beat": [0.62, 0.63, 0.65, 1], "key": [0.97, 0.97, 0.97, 1], "keyBlack": [0.12, 0.12, 0.13, 1]}};
var liveColourMissingReported = false;
/** The 2sl tokens for Live's theme: light when Live's surface colour (live_surface_bg) is light. If Max can't
 *  give that colour, dark, and the Max window says which colour was missing (once, until it is back). */
function themeFromLive(who) {
  var surface = null, failure = "";
  try { surface = max.getcolor("live_surface_bg"); } catch (e) { failure = String(e); }
  var usable = surface && surface.length >= 3 && isFinite(surface[0]) && isFinite(surface[1]) && isFinite(surface[2]);
  if (!usable) {
    if (!liveColourMissingReported) {
      liveColourMissingReported = true;
      error("2sl stab (" + who + "): Live colour live_surface_bg is missing (max.getcolor gave " +
            (failure || JSON.stringify(surface)) + "): drawing in the dark theme\n");
    }
    return THEMES.dark;
  }
  liveColourMissingReported = false;
  var luminance = 0.2126 * surface[0] + 0.7152 * surface[1] + 0.0722 * surface[2];
  return luminance > 0.5 ? THEMES.light : THEMES.dark;
}
var current = 0;

function show() {
  var names = ["play", "osc", "shape"];
  for (var i = 0; i < names.length; i++) {
    var list = PAGES[names[i]];
    for (var k = 0; k < list.length; k++) outlet(0, "script", "sendbox", list[k], "hidden", i === current ? 0 : 1);
  }
}

function page(i) {
  if (!(i >= 0 && i <= 2)) error("2sl stab: page " + i + " doesn't exist (0-2): showing the nearest\n");
  current = Math.max(0, Math.min(2, Math.round(i))) || 0;
  show();
}

/** The patch object named `name` (its scripting name). The names come from the build, which checks them
 *  against the patch, so a missing one is a broken build: say which. */
function named(name, purpose) {
  var obj = this.patcher.getnamed(name);
  if (!obj) error("2sl stab: no object named '" + name + "' in the patch (" + purpose + ")\n");
  return obj;
}

// ---- 2sl colours on Live's controls ---------------------------------------------------------

function paint(name, attrs) {
  var obj = named(name, "recolouring");
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
    var v = named(VIEWS[i], "redrawing for the theme");
    if (v) v.message("theme");
  }
}

function anything() {
  if (messagename === "stop") {
    var f = named("freeze", "Stop turns Freeze off");
    if (f) f.message(0);
    return;
  }
  if (messagename === "theme") {
    recolor();
    return;
  }
  if (messagename === "ready") {
    show();
    recolor();
  }
}
