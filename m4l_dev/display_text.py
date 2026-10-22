"""The text a device's displays draw, read by running its views script: each display (a jsui box running the views
script in a mode) painted once in Duktape (m4l_dev/es5.py, an ES5 engine as Max's [jsui] is) with Max's jsui globals
stubbed, every call of the kit's text() recorded with where its glyphs land.

    display_texts(views_script_text, mode, width, height) -> [DrawnText]   (in the display's own pixels)

A display is painted as a fresh device shows it before any message reaches it: its views code's own starting state.
What it draws after messages (longer readings, other choices) isn't seen here; a device's script tests paint those.
The stubs draw nothing: mgraphics takes every call and ignores it, max.getcolor gives Live's dark surface, a Task
never runs, a Buffer is empty. A paint that throws fails the build with Duktape's message.
"""
import collections
import json

from m4l_dev.build_error import BuildError
from m4l_dev.es5 import evaluate

# a text a display drew: `extent` (x, y, w, h) the box its glyphs cover; the call that drew it: `x`, `baseline`, `scale`
DrawnText = collections.namedtuple("DrawnText", "text extent x baseline scale")

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

# after the views script: text() recorded (the glyphs' boxes, from the same COZETTE table it draws from), then paint()
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
paint();
JSON.stringify({ drawn: __drawn, errors: __errors });
"""


def display_texts(views_script_text, mode, width, height):
    """[DrawnText]: every text the display in `mode`, `width` x `height` px, draws when first painted. Fails
    (BuildError) when the paint throws or says error()."""
    prelude = (JSUI_GLOBALS_ES5.replace("__WIDTH__", repr(float(width))).replace("__HEIGHT__", repr(float(height)))
               .replace("__MODE__", json.dumps(mode)))
    try:
        painted = json.loads(evaluate(prelude + views_script_text + "\n" + RECORD_AND_PAINT_ES5))
    except BuildError as failure:
        raise BuildError(f"the {mode!r} display ({width:g} x {height:g}) couldn't be painted to read its text: "
                         f"{failure}") from failure
    if painted["errors"]:
        raise BuildError(f"the {mode!r} display ({width:g} x {height:g}) said error() when first painted: "
                         + " | ".join(message.strip() for message in painted["errors"]))
    return [DrawnText(text, (left, top, w, h), x, baseline, scale)
            for text, left, top, w, h, x, baseline, scale in painted["drawn"]]
