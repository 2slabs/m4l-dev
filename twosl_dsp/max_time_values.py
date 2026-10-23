"""Max's time values: the note values Max knows, and the check every tempo object's box text passes.

Source: the Max user guide, Time Value Syntax (references/README.md, "Time value syntax"). A note value Max doesn't
know (2sl gate shipped `metro 64nt @quantize 64nt`; there is no 64nt) is not an error in Max: the object is left
with a time nobody chose. So the build refuses it.
"""
import re

from twosl_dsp.build_error import BuildError

# Time Value Syntax, "Note Values in Ticks": every note value Max knows, and its length in ticks (480 a quarter note)
MAX_NOTE_VALUE_TICKS = {
    "1nd": 2880, "1n": 1920, "1nt": 1280,
    "2nd": 1440, "2n": 960, "2nt": 640,
    "4nd": 720, "4n": 480, "4nt": 320,
    "8nd": 360, "8n": 240, "8nt": 160,
    "16nd": 180, "16n": 120, "16nt": 80,
    "32nd": 90, "32n": 60, "32nt": 40,
    "64nd": 45, "64n": 30,
    "128n": 15,
}
# what a note value looks like: a number, n, and an optional d (dotted) or t (triplet)
NOTE_VALUE_SHAPE = re.compile(r"^\d+n[dt]?$")
# the objects that take a time value in their arguments or attributes (interval, quantize, ...): every token of
# their box text shaped like a note value is checked
TIME_VALUE_OBJECTS = frozenset({"metro", "qmetro", "delay", "del", "pipe", "line", "line~", "timer", "transport",
                                "translate", "snapshot~", "phasor~"})


def check_note_values_in_box_text(box_text, where):
    """Fail when `box_text` is a time-value object's ([metro], [delay], ...) and one of its tokens looks like a note
    value (16n, 8nt, 4nd) but is not one Max knows (MAX_NOTE_VALUE_TICKS)."""
    tokens = box_text.split()
    if not tokens or tokens[0] not in TIME_VALUE_OBJECTS:
        return
    unknown = [token for token in tokens[1:] if NOTE_VALUE_SHAPE.match(token) and token not in MAX_NOTE_VALUE_TICKS]
    if unknown:
        raise BuildError(f"{where}: [{box_text}]: " + "; ".join(
            f"{token!r} is not a Max note value (Time Value Syntax): Max knows {', '.join(MAX_NOTE_VALUE_TICKS)}"
            for token in unknown))
