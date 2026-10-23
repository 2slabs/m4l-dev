"""The 2sl colours, dark and light, and the ES5 function every generated script picks them with from Live's theme.

The tokens are 2sl-ui's (2sl-ui/max/2sl-colors.json: pad well ink inverse label unlit mint now), plus the few the
devices draw with: rest and beat (empty steps), warm (throws, notices), key and keyBlack (a keyboard).
"""
import json

THEMES = {
    "dark": {"pad": [0.149, 0.149, 0.149, 1], "well": [0.106, 0.106, 0.11, 1], "ink": [0.835, 0.847, 0.859, 1],
             "inverse": [0.149, 0.149, 0.149, 1], "label": [0.557, 0.58, 0.608, 1], "unlit": [0.494, 0.518, 0.545, 1],
             "mint": [0.447, 0.871, 0.761, 1], "now": [0.176, 0.357, 1.0, 1], "warm": [1.0, 0.55, 0.2, 1],
             "rest": [0.2, 0.2, 0.21, 1], "beat": [0.26, 0.27, 0.28, 1], "key": [0.72, 0.73, 0.74, 1],
             "keyBlack": [0.07, 0.07, 0.08, 1]},
    "light": {"pad": [0.835, 0.847, 0.859, 1], "well": [0.77, 0.78, 0.79, 1], "ink": [0.0, 0.0, 0.0, 1],
              "inverse": [1.0, 1.0, 1.0, 1], "label": [0.349, 0.369, 0.396, 1], "unlit": [0.451, 0.475, 0.502, 1],
              "mint": [0.12, 0.55, 0.45, 1], "now": [0.176, 0.357, 1.0, 1], "warm": [0.85, 0.38, 0.0, 1],
              "rest": [0.7, 0.71, 0.73, 1], "beat": [0.62, 0.63, 0.65, 1], "key": [0.97, 0.97, 0.97, 1],
              "keyBlack": [0.12, 0.12, 0.13, 1]},
}

# Light or dark, from Live's theme: shared by the displays and the UI script (both are generated with it).
_THEME_FROM_LIVE_JS = """
var THEMES = %(themes)s;
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
      error(DEVICE_NAME + " (" + who + "): Live colour live_surface_bg is missing (max.getcolor gave " +
            (failure || JSON.stringify(surface)) + "): drawing in the dark theme\\n");
    }
    return THEMES.dark;
  }
  liveColourMissingReported = false;
  var luminance = 0.2126 * surface[0] + 0.7152 * surface[1] + 0.0722 * surface[2];
  return luminance > 0.5 ? THEMES.light : THEMES.dark;
}""".strip()


def theme_from_live_js():
    """The THEMES table and themeFromLive(who), as ES5. The script it goes in defines DEVICE_NAME."""
    return _THEME_FROM_LIVE_JS % {"themes": json.dumps(THEMES)}
