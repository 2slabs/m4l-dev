"""The text a device's displays draw, read by running its views script: each display (a jsui box running the views
script in a mode) painted in Duktape (twosl_dsp/es5.py, an ES5 engine as Max's [jsui] is) with Max's jsui globals
stubbed, every call of the kit's text() recorded with where its glyphs land.

    display_texts(views_script_text, mode, width, height) -> [DrawnText]   (first paint, in the display's own pixels)
    display_paints(views_script_text, mode, width, height, inputs) -> [Painted]   (first paint, then driven)

First paint: a fresh device before any message reaches it, its views code's own starting state. Driven: the display
is sent its inputs (`message value`, through the views script's own anything(), as Live's patch sends them) and
painted again, searching for the widest text it can draw. One search (an ascent): from a starting state, each input in
turn is swept through all its values (the others held) and kept at the one whose paint's texts are widest in total;
the sweeps repeat until no input moves. A search runs from the inputs' start values, and again from there with each
value of each switch (an input of SWITCH_VALUES values or fewer: a mode, an on/off, a source) held fixed, for every
switch whose sweeps in the first search changed what the display drew: a switch changes which texts a display draws,
so the widest total may hide a narrower mode's overlap. Every distinct
paint met on the way is returned: the overlap rule sees the widest reading each text can show, and every one-input
change from there and from the start.
The stubs draw nothing: mgraphics takes every call and ignores it, max.getcolor gives Live's dark surface, a Task
never runs, a Buffer is empty. A paint that throws or says error() fails the build with the message and what the
display had been sent.
"""
import collections
import json

from twosl_dsp.build_error import BuildError
from twosl_dsp.es5 import evaluate

# a text a display drew: `extent` (x, y, w, h) the box its glyphs cover; the call that drew it: `x`, `baseline`, `scale`
DrawnText = collections.namedtuple("DrawnText", "text extent x baseline scale")
SWITCH_VALUES = 4         # an input with this many values or fewer is a switch: each of its values gets its own search
# a paint: `sent` {message: value} the inputs as sent ({} for the first paint), `drawn` [DrawnText]
Painted = collections.namedtuple("Painted", "sent drawn")

# Max's jsui globals as the views script uses them (templates/views.template.js and the devices' views code)
JSUI_GLOBALS_ES5 = """
var __errors = [];
function error(s) { __errors.push(String(s)); }
function post(s) {}
function outlet() {}
function arrayfromargs(a) { return Array.prototype.slice.call(a); }
var inlets = 0, outlets = 0, inlet = 0, messagename = "";
var mgraphics = { size: [__WIDTH__, __HEIGHT__] };
(function () {
  var calls = ["init", "set_source_rgba", "rectangle", "fill", "fill_preserve", "stroke", "set_line_width", "move_to",
               "line_to", "curve_to", "close_path", "redraw", "arc", "translate", "save", "restore", "rotate", "scale",
               "set_font_size", "select_font_face", "show_text", "rel_line_to", "rel_move_to", "fill_with_alpha"];
  for (var i = 0; i < calls.length; i++) mgraphics[calls[i]] = function () {};
})();
var jsarguments = ["views.js", __MODE__];
var max = { getcolor: function () { return [0.149, 0.149, 0.149, 1]; }, launchbrowser: function () {}, apply: function () {} };
function Task(callback, owner) { this.interval = 0; }
Task.prototype.repeat = function () {};
Task.prototype.schedule = function () {};
Task.prototype.cancel = function () {};
function Buffer(name) { this.name = name; }
Buffer.prototype.framecount = function () { return 0; };
Buffer.prototype.peek = function () { return []; };
"""

# after the views script: text() recorded (the glyphs' boxes, from the same COZETTE table it draws from), then the first
# paint, then the driven search (the module's docstring) over __INPUTS: [[message, [values], start index]]
RECORD_AND_PAINT_ES5 = """
var __drawn = [];
var __drawText = text;
text = function (str, x, y, c, scale) {
  var s = String(str), k = scale || 1, pen = Math.round(x), left = null, right = null, top = null, bottom = null;
  for (var i = 0; i < s.length; i++) {
    var g = glyph(s.charCodeAt(i));
    if (g[1] > 0 && g[2] > 0) {
      var gl = pen + g[3] * k, gr = gl + g[1] * k, gt = Math.round(y) - (g[4] + g[2]) * k, gb = Math.round(y) - g[4] * k;
      left = left === null ? gl : Math.min(left, gl); right = right === null ? gr : Math.max(right, gr);
      top = top === null ? gt : Math.min(top, gt); bottom = bottom === null ? gb : Math.max(bottom, gb);
    }
    pen += g[0] * k;
  }
  if (left !== null) __drawn.push([s, left, top, right - left, bottom - top, Math.round(x), Math.round(y), k]);
  return __drawText.apply(this, arguments);
};
var __painted = [], __seen = {}, __sent = {}, __failure = null, __totals = {}, __drawnBy = {}, __changes = {};
function __paint() {
  var state = JSON.stringify(__sent);
  if (__totals.hasOwnProperty(state)) { __drawn = __drawnBy[state]; return __totals[state]; }
  __drawn = [];
  paint();
  if (__errors.length) throw { said: "said error() " + (__painted.length ? "sent " + state : "when first painted") + ": " + __errors.join(" | ") };
  var key = JSON.stringify(__drawn);
  __drawnBy[state] = key;
  if (!__seen[key]) {
    __seen[key] = 1;
    __painted.push({ sent: JSON.parse(state), drawn: __drawn });
  }
  var total = 0;
  for (var k = 0; k < __drawn.length; k++) total += __drawn[k][3];
  if (__painted.length > 1) __totals[state] = total;
  __drawn = key;
  return total;
}
function __send(message, value) {
  __sent[message] = value;
  messagename = message;
  anything.apply(this, value instanceof Array ? value : [value]);
  if (__errors.length) throw { said: "said error() when sent " + JSON.stringify(__sent) + ": " + __errors.join(" | ") };
}
/** One search: from `at` (an index per input), with input `pinned` (or -1) held; leaves the display at the widest. */
function __ascend(at, pinned) {
  for (var i = 0; i < __INPUTS.length; i++) __send(__INPUTS[i][0], __INPUTS[i][1][at[i]]);
  var widest = __paint(), held = __drawn, moved = true, sweeps = 0;
  while (moved) {
    if (++sweeps > 100) throw { said: "the widest-text search didn't settle in 100 sweeps" };
    moved = false;
    for (var i = 0; i < __INPUTS.length; i++) {
      if (i === pinned) continue;
      var values = __INPUTS[i][1], kept = at[i];
      for (var j = 0; j < values.length; j++) {
        if (j === at[i]) continue;
        __send(__INPUTS[i][0], values[j]);
        var total = __paint();
        if (__drawn !== held) __changes[i] = 1;
        if (total > widest) { widest = total; kept = j; }
      }
      if (kept !== at[i]) moved = true;
      at[i] = kept;
      __send(__INPUTS[i][0], values[kept]);
      __paint();
      held = __drawn;
    }
  }
}
try {
  __paint();
  if (__INPUTS.length) {
    var __start = [];
    for (var __i = 0; __i < __INPUTS.length; __i++) __start.push(__INPUTS[__i][2]);
    __ascend(__start.slice(), -1);
    for (var __i = 0; __i < __INPUTS.length; __i++) {
      if (__INPUTS[__i][1].length > __SWITCH_VALUES || !__changes[__i]) continue;
      for (var __j = 0; __j < __INPUTS[__i][1].length; __j++) {
        var __from = __start.slice();
        __from[__i] = __j;
        __ascend(__from, __i);
      }
    }
  }
} catch (failure) {
  __failure = failure.said || ("couldn't be painted to read its text" + (__painted.length ? " (sent " + JSON.stringify(__sent) + ")" : "") + ": " + failure);
}
JSON.stringify({ painted: __painted, failure: __failure });
"""


def display_paints(views_script_text, mode, width, height, inputs=()):
    """[Painted]: the display in `mode`, `width` x `height` px, as first painted, then driven by `inputs` [(message,
    [values it can be sent], the index of the one it starts with)] (the module's docstring), each distinct paint once.
    Fails (BuildError) when a paint throws or says error()."""
    inputs_json = json.dumps([[message, list(values), start] for message, values, start in inputs])
    prelude = (JSUI_GLOBALS_ES5.replace("__WIDTH__", repr(float(width))).replace("__HEIGHT__", repr(float(height)))
               .replace("__MODE__", json.dumps(mode))
               + f"var __INPUTS = {inputs_json}, __SWITCH_VALUES = {SWITCH_VALUES};\n")
    where = f"the {mode!r} display ({width:g} x {height:g})"
    try:
        painted = json.loads(evaluate(prelude + views_script_text + "\n" + RECORD_AND_PAINT_ES5))
    except BuildError as failure:
        raise BuildError(f"{where} couldn't be painted to read its text: {failure}") from failure
    if painted["failure"]:
        raise BuildError(f"{where}: {painted['failure']}")
    return [Painted(paint["sent"], [DrawnText(text, (left, top, w, h), x, baseline, scale)
                                    for text, left, top, w, h, x, baseline, scale in paint["drawn"]])
            for paint in painted["painted"]]


def display_texts(views_script_text, mode, width, height):
    """[DrawnText]: every text the display in `mode`, `width` x `height` px, draws when first painted."""
    return display_paints(views_script_text, mode, width, height)[0].drawn
