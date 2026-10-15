// 2sl stab: pages and theme. Generated from src/2sl-stab-ui.template.js by src/2sl-stab.py; edit there.
//   page i      show the play (0), osc (1) or shape (2) page
//   ready       sent once the device has loaded: show the page, colour the controls
//   theme       Live's colour theme changed (from live.colors): recolour controls, redraw displays
//   stop        turn Freeze off (part of the Stop action)
// out 0: messages for [thispatcher]
inlets = 1;
outlets = 1;

var PAGES = /*PAGES*/;
var CONTROLS = /*CONTROLS*/;
var VIEWS = /*VIEWS*/;
/*THEME_FROM_LIVE*/
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
