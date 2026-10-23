"""The 2sl layout contract (from 2sl stab) and the checks the build runs on it.

A device is DEVICE_HEIGHT px high, as wide as it needs, on a GRID px grid. A header row (HEADER_Y), then every
section has three bands aligned across the device: a display (VIEW_Y, VIEW_H), a row of chips, menus and tabs
(ROW_Y, ROW_H high) and dials (DIAL_Y). Text is Cozette, COZETTE_ADVANCE px a character.
"""
import math

from twosl_dsp.build_error import BuildError

DEVICE_HEIGHT = 169
GRID = 4
DIAL_WIDTH, DIAL_HEIGHT = 44, 48
VIEW_Y, VIEW_H, ROW_Y, DIAL_Y = 28, 64, 98, 119
ROW_H = 15
HEADER_Y = 3
SUBTITLE_BASELINE = 15          # the header's subtitle, drawn by the chrome after the page tabs
HEADER_GAP = 12                 # px between header items, and the margin at either end of the device
COZETTE_ADVANCE = 6
CHIP_PADDING = 4                # px of chip either side of its text (the link chip)

# Live draws a live.dial's short name, a live.menu's item, a live.text's text and a live.tab's names in its own font,
# inside the box. No source gives that font's metrics (references/README.md, "Live's control font"; SHORTCUTS.md). The
# kit measures text with a stand-in: Liberation Sans Regular (metric-compatible with Arial) at 11 px, the size whose
# average lowercase letter is 5.5 px, the width calibrated from what 2sl gate played in Live (v0.5's 8-character dial
# names in 44 px dials). Each character's advance at that size (from the font file, tools/render_pages.py draws with
# the same font and checks this table against it), so "FM amount" (capitals) measures wider than "Velocity":
LIVE_FONT_FILE_NAME = "LiberationSans-Regular.ttf"
LIVE_FONT_PIXELS = 11
LIVE_TEXT_PIXELS_PER_CHARACTER = 5.5          # the stand-in's size: its average lowercase advance
LIVE_FONT_ADVANCES = {' ': 3.0625, '!': 3.0625, '"': 3.90625, '#': 6.125, '$': 6.125, '%': 9.78125, '&': 7.34375, "'": 2.09375, '(': 3.65625, ')': 3.65625, '*': 4.28125, '+': 6.421875, ',': 3.0625, '-': 3.65625, '.': 3.0625, '/': 3.0625, '0': 6.125, '1': 6.125, '2': 6.125, '3': 6.125, '4': 6.125, '5': 6.125, '6': 6.125, '7': 6.125, '8': 6.125, '9': 6.125, ':': 3.0625, ';': 3.0625, '<': 6.421875, '=': 6.421875, '>': 6.421875, '?': 6.125, '@': 11.171875, 'A': 7.34375, 'B': 7.34375, 'C': 7.9375, 'D': 7.9375, 'E': 7.34375, 'F': 6.71875, 'G': 8.5625, 'H': 7.9375, 'I': 3.0625, 'J': 5.5, 'K': 7.34375, 'L': 6.125, 'M': 9.15625, 'N': 7.9375, 'O': 8.5625, 'P': 7.34375, 'Q': 8.5625, 'R': 7.9375, 'S': 7.34375, 'T': 6.71875, 'U': 7.9375, 'V': 7.34375, 'W': 10.375, 'X': 7.34375, 'Y': 7.34375, 'Z': 6.71875, '[': 3.0625, '\\': 3.0625, ']': 3.0625, '^': 5.15625, '_': 6.125, '`': 3.65625, 'a': 6.125, 'b': 6.125, 'c': 5.5, 'd': 6.125, 'e': 6.125, 'f': 3.0625, 'g': 6.125, 'h': 6.125, 'i': 2.4375, 'j': 2.4375, 'k': 5.5, 'l': 2.4375, 'm': 9.15625, 'n': 6.125, 'o': 6.125, 'p': 6.125, 'q': 6.125, 'r': 3.65625, 's': 5.5, 't': 3.0625, 'u': 6.125, 'v': 5.5, 'w': 7.9375, 'x': 5.5, 'y': 5.5, 'z': 5.5, '{': 3.671875, '|': 2.859375, '}': 3.671875, '~': 6.421875, '×': 6.421875, '½': 9.171875, '—': 11.0, '→': 11.0, '√': 6.03125, '·': 3.65625, '°': 4.40625, '–': 6.125, '…': 11.0, '÷': 6.03125}
# Room a control leaves its text, so a text never touches its box or its neighbour's text (2026-10-21: renders showed
# "FM amountAM amount" and tab names touching their borders, "246248", with the old flat 5.5 px rule and 1 px of tab
# slack): a dial's name 2 px a side; a menu's item 2 px in from its left, its arrow the room on its right; a live.text
# 4 px a side; a tab button 3.
LIVE_TEXT_PADDING_PIXELS = 4
LIVE_MENU_TEXT_INSET_PIXELS = 2
LIVE_MENU_ARROW_PIXELS = 12           # a live.menu's arrow, beside its item
LIVE_MENU_MINIMUM_WIDTH = 40
LIVE_TOGGLE_PADDING_PIXELS = 8        # a live.text's text needs this much more than its characters
LIVE_TAB_BUTTON_PADDING_PIXELS = 6    # a live.tab button's text needs this much more than its characters
# the header's page tabs are drawn at least this wide each, and wide enough for the longest page name + 12
PAGE_TAB_MINIMUM_WIDTH = 48


def check_on_grid(what, value):
    if value % GRID:
        raise BuildError(f"{what} {value} is off the {GRID} px grid")


def on_grid(pixels):
    """`pixels` rounded up to the GRID."""
    return int(math.ceil(pixels / GRID) * GRID)


def live_text_width(text):
    """`text`'s width in Live's font, as the stand-in measures it (LIVE_FONT_ADVANCES). Fails on a character the table
    doesn't hold (add it from the font file)."""
    missing = sorted({character for character in str(text) if character not in LIVE_FONT_ADVANCES})
    if missing:
        raise BuildError(f"the text {text!r} has characters layout_rules.LIVE_FONT_ADVANCES doesn't measure: {missing} "
                         f"(add them from {LIVE_FONT_FILE_NAME} at {LIVE_FONT_PIXELS} px)")
    return sum(LIVE_FONT_ADVANCES[character] for character in str(text))


def live_dial_width(short_name):
    """The narrowest live.dial that holds its short name with its padding: at least DIAL_WIDTH, on the grid."""
    return max(DIAL_WIDTH, on_grid(live_text_width(short_name) + LIVE_TEXT_PADDING_PIXELS))


def live_menu_width(items):
    """The narrowest live.menu that holds its longest item, its inset and its arrow, on the grid."""
    return max(LIVE_MENU_MINIMUM_WIDTH, on_grid(max(live_text_width(item) for item in items)
                                                + LIVE_MENU_TEXT_INSET_PIXELS + LIVE_MENU_ARROW_PIXELS))


def live_toggle_width(text):
    """The narrowest live.text that holds `text`, on the grid."""
    return on_grid(live_text_width(text) + LIVE_TOGGLE_PADDING_PIXELS)


def live_tab_button_width(items):
    """What one live.tab button needs: its longest name and its padding."""
    return max(live_text_width(item) for item in items) + LIVE_TAB_BUTTON_PADDING_PIXELS


def live_tabs_width(items, rows=1):
    """The narrowest live.tab the button rule (live_tab_button_problem) allows, on the grid."""
    per_row = -(-len(items) // rows)
    return on_grid(per_row * live_tab_button_width(items))


def live_text_problem(maxclass, short_name, items, text, width):
    """None when a live.dial (its short name), live.menu (its longest item) or live.text (its text) `width` px wide
    holds its text; else why not. Other classes: None (live.tab has its own rule)."""
    needed = {"live.dial": lambda: live_dial_width(short_name), "live.menu": lambda: live_menu_width(items),
              "live.text": lambda: live_toggle_width(text)}.get(maxclass)
    if needed is not None and width < needed():
        return f"{width:g} px wide, its text needs {needed()}"
    return None


def live_tab_button_problem(items, width, rows):
    """None when every button of a live.tab `width` px wide, in `rows` rows, holds its longest name; else why not."""
    buttons_per_row = -(-len(items) // rows)
    button_width = width / buttons_per_row
    needed = live_tab_button_width(items)
    if button_width < needed:
        longest = max(items, key=live_text_width)
        return (f"{buttons_per_row} buttons a row in {width} px leave {button_width:g} px each; the longest name "
                f"({longest!r}) needs {needed:g}")
    return None


def page_tabs_width(page_names):
    return len(page_names) * max(PAGE_TAB_MINIMUM_WIDTH, COZETTE_ADVANCE * max(len(n) for n in page_names) + 12)


def link_chip_width(link_chip_text):
    return COZETTE_ADVANCE * len(link_chip_text) + 2 * CHIP_PADDING


def page_tabs_x(link_chip_text):
    """The page tabs' left edge: after the link chip, HEADER_GAP either side of it."""
    return HEADER_GAP + link_chip_width(link_chip_text) + HEADER_GAP


def subtitle_x(link_chip_text, page_names, preset_menu=None):
    """Where the chrome draws the header's subtitle: HEADER_GAP after the page tabs, or after the Preset menu
    (preset_menu=(x, w)) when a device has one. Every device's: a device doesn't place its subtitle."""
    header_items_end = page_tabs_x(link_chip_text) + page_tabs_width(page_names)
    if preset_menu is not None:
        header_items_end = max(header_items_end, preset_menu[0] + preset_menu[1])
    return header_items_end + HEADER_GAP


# ---- what each thing draws, and the rule that no two drawn things overlap ------------------------------------------

# Live's unit styles (parameter_unitstyle, the live.dial reference's "Unit Style": Int, Float, Time, Hertz, deciBel, %,
# Pan, Semitones, MIDI, Custom, Native, in that order)
UNIT_INT, UNIT_FLOAT, UNIT_TIME, UNIT_HERTZ, UNIT_DECIBEL, UNIT_PERCENT, UNIT_PAN, UNIT_SEMITONES, UNIT_MIDI, \
    UNIT_CUSTOM, UNIT_NATIVE = range(11)
PARAMETER_TYPE_INT = 1
LIVE_TEXT_LINE_PIXELS = 11            # a line of Live's text: a dial's name on its top line, its value on its bottom
DIAL_VALUE_SWEEP_STEPS = 1000         # a float dial's values looked at for its widest text: this many steps of its travel
DISPLAY_SWEEP_STEPS = 32              # a float control's values a display is driven through (its widest text): steps
COZETTE_ASCENT, COZETTE_DESCENT = 10, 3  # a chrome text's line above and below its baseline (the views script's text())
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def three_figures(value):
    """`value` to three significant figures as Live shows a quantity (2.00, 12.5, 125): a stand-in (SHORTCUTS.md)."""
    places = 2 if abs(value) < 10 else 1 if abs(value) < 100 else 0
    return f"{value:.{places}f}"


def live_value_text(value, unit_style, integer=False):
    """The text a live.dial or live.numbox shows for `value` in `unit_style`, as the kit's stand-in for Live's
    formatting (no source gives Live's; SHORTCUTS.md): a quantity to three figures with its unit (ms / s, Hz / kHz),
    dB to a tenth, an Int-type value whole."""
    number = (lambda v: str(int(round(v)))) if integer else three_figures
    if unit_style in (UNIT_TIME, UNIT_HERTZ):
        small, large = ("ms", "s") if unit_style == UNIT_TIME else ("Hz", "kHz")
        return f"{number(value / 1000)} {large}" if abs(value) >= 1000 else f"{number(value)} {small}"
    if unit_style == UNIT_DECIBEL:
        return f"{value:.1f} dB"
    if unit_style == UNIT_PERCENT:
        return f"{number(value)} %"
    if unit_style == UNIT_PAN:
        whole = int(round(value))
        return "C" if whole == 0 else f"{abs(whole)}{'L' if whole < 0 else 'R'}"
    if unit_style == UNIT_SEMITONES:
        text = number(value)
        return f"{'+' if value > 0 else ''}{text} st"
    if unit_style == UNIT_MIDI:
        note = int(round(value))
        return f"{NOTE_NAMES[note % 12]}{note // 12 - 2}"
    if unit_style == UNIT_INT or integer:
        return str(int(round(value)))
    if unit_style in (UNIT_FLOAT, UNIT_NATIVE):
        return f"{value:.2f}"
    raise BuildError(f"unit style {unit_style!r}: the kit has no stand-in for how Live shows it (a Custom unit's text "
                     "isn't read yet): add it to layout_rules.live_value_text")


def live_held_values(values, sweep_steps):
    """The values a control with these saved values (`saved_attribute_attributes.valueof`) can hold, as Live holds
    them: an enum's every index; an Int's every value; a float's at `sweep_steps` steps of its travel (Live's
    exponent), its ends included."""
    if values.get("parameter_enum"):
        return list(range(len(values["parameter_enum"])))
    low, high = float(values["parameter_mmin"]), float(values["parameter_mmax"])
    if values.get("parameter_type") == PARAMETER_TYPE_INT:
        return list(range(int(round(low)), int(round(high)) + 1))
    exponent = float(values.get("parameter_exponent", 1.0))
    return [low + (high - low) * (step / sweep_steps) ** exponent for step in range(sweep_steps + 1)]


def live_value_texts(values):
    """Every text a control with these saved values (`saved_attribute_attributes.valueof`) shows as its value: an
    enum's items; an Int's every value; a float's at DIAL_VALUE_SWEEP_STEPS steps of its travel (live_held_values)."""
    if values.get("parameter_enum"):
        return list(values["parameter_enum"])
    unit_style = values["parameter_unitstyle"]
    if values.get("parameter_type") == PARAMETER_TYPE_INT:
        return [live_value_text(v, unit_style, integer=True) for v in live_held_values(values, DIAL_VALUE_SWEEP_STEPS)]
    return sorted({live_value_text(v, unit_style) for v in live_held_values(values, DIAL_VALUE_SWEEP_STEPS)})


def widest_live_text(texts):
    return max(live_text_width(text) for text in texts)


def centred_line(x, w, line_y, text_width):
    """The extent of a line of text `text_width` wide centred over the box x..x+w."""
    return (x + (w - text_width) / 2, line_y, text_width, LIVE_TEXT_LINE_PIXELS)


def box_name(box):
    return box.get("varname", box.get("id"))


def drawn_parts(box):
    """[(what, (x, y, w, h))]: what a shown box draws, as far as it can reach: its box and the text Live draws on it,
    each as wide as the stand-in measures it. A live.dial: its name centred on its top line and its widest value
    centred on its bottom line; a live.numbox: its widest value; a live.menu: its longest item from its inset; a
    live.text: its text. Text may reach past the box, which is how two things come to overlap."""
    x, y, w, h = box["presentation_rect"]
    parts = [("box", (x, y, w, h))]
    values = box.get("saved_attribute_attributes", {}).get("valueof", {})
    kind = box["maxclass"]
    if kind == "live.dial":
        parts.append(("name", centred_line(x, w, y, live_text_width(values["parameter_shortname"]))))
        parts.append(("value", centred_line(x, w, y + h - LIVE_TEXT_LINE_PIXELS,
                                            widest_live_text(live_value_texts(values)))))
    elif kind == "live.numbox":
        parts.append(("value", centred_line(x, w, y + (h - LIVE_TEXT_LINE_PIXELS) / 2,
                                            widest_live_text(live_value_texts(values)))))
    elif kind == "live.menu":
        parts.append(("item", (x + LIVE_MENU_TEXT_INSET_PIXELS, y + (h - LIVE_TEXT_LINE_PIXELS) / 2,
                               widest_live_text(values["parameter_enum"]), LIVE_TEXT_LINE_PIXELS)))
    elif kind == "live.text":
        text = box.get("text") or values.get("parameter_shortname", "")
        parts.append(("text", centred_line(x, w, y + (h - LIVE_TEXT_LINE_PIXELS) / 2, live_text_width(text))))
    return parts


def chrome_text_extent(text, x, baseline):
    """A text the chrome draws in Cozette (a label, a hint, the subtitle) at (x, baseline): its extent."""
    return (x, baseline - COZETTE_ASCENT, COZETTE_ADVANCE * len(text), COZETTE_ASCENT + COZETTE_DESCENT)


def chrome_texts(layout, page_index):
    """[(what, (text, x, baseline))]: every text the chrome draws on page `page_index` of `layout` (the views script's
    LAYOUT: the header's labels already in each page's): the page's labels and the header's subtitle."""
    texts = [(f"{kind} {text!r}", (text, x, baseline)) for text, x, baseline, kind in layout["pages"][page_index]["labels"]]
    subtitle = f"{layout['subtitle_text']}  v{layout['version']}"
    texts.append((f"subtitle {subtitle!r}", (subtitle, layout["subtitle"], SUBTITLE_BASELINE)))
    return texts


def overlap_area(a, b):
    """(w, h) of where rects a and b overlap, or None."""
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return (w, h) if w > 0 and h > 0 else None


def rect_text(rect):
    x, y, w, h = rect
    return f"x {x:g}..{x + w:g}, y {y:g}..{y + h:g}"


def drawn_overlap_problems(boxes, layout, page_names, boxes_on_page, groups, device_width):
    """Two things drawn at the same time whose drawn extents overlap, or one reaching off the device: on every page
    and every choice of its group selectors, every shown box's drawn parts (drawn_parts) and every text the chrome
    draws (chrome_texts). A background box (Max's "Include in Background": the chrome) is what everything sits on, so
    it is exempt; a part never counts against another part of its own box.

    boxes: the presentation boxes; layout: the views script's LAYOUT (DevicePatchBuilder.full_layout);
    boxes_on_page: page -> varnames on it (a varname on no page is in the header, shown on every page); groups:
    selector varname -> {"page", "members": [[varnames]]}."""
    shown = [b for b in boxes if b.get("presentation") == 1 and not b.get("background")]
    parts_of = {id(b): drawn_parts(b) for b in shown}
    on_some_page = {n for names in boxes_on_page.values() for n in names}
    problems = []
    for page_index, page in enumerate(page_names):
        selectors = sorted(s for s, g in groups.items() if g["page"] == page)
        choices = [[]]
        for selector in selectors:
            choices = [c + [(selector, i)] for c in choices for i in range(len(groups[selector]["members"]))]
        for choice in choices:
            hidden = {n for selector, picked in choice
                      for i, members in enumerate(groups[selector]["members"]) if i != picked for n in members}
            elements = [(box_name(b), parts_of[id(b)]) for b in shown
                        if (b.get("varname") not in on_some_page or b["varname"] in boxes_on_page[page])
                        and b.get("varname") not in hidden]
            elements += [(what, [("text", chrome_text_extent(*placed))]) for what, placed in chrome_texts(layout, page_index)]
            where = f"page {page!r}" + (f" {dict(choice)}" if choice else "")
            for name, parts in elements:
                for part, rect in parts:
                    x, y, w, h = rect
                    if x < 0 or y < 0 or x + w > device_width or y + h > DEVICE_HEIGHT:
                        problems.append(f"{where}: {name}'s {part} ({rect_text(rect)}) reaches off the "
                                        f"{device_width} x {DEVICE_HEIGHT} device")
            for i, (name_a, parts_a) in enumerate(elements):
                for name_b, parts_b in elements[i + 1:]:
                    for part_a, rect_a in parts_a:
                        for part_b, rect_b in parts_b:
                            overlap = overlap_area(rect_a, rect_b)
                            if overlap:
                                problems.append(f"{where}: {name_a}'s {part_a} ({rect_text(rect_a)}) overlaps "
                                                f"{name_b}'s {part_b} ({rect_text(rect_b)}) by {overlap[0]:g} x "
                                                f"{overlap[1]:g} px")
    return sorted(set(problems))


def display_text_problems(display_name, drawn_texts, width, height):
    """Two texts one display draws over each other, or one reaching off it: `drawn_texts` [(text, (x, y, w, h))] in
    the display's own pixels (display_text.display_texts), on a display `width` x `height` px."""
    problems = []
    for text, extent in drawn_texts:
        x, y, w, h = extent
        if x < 0 or y < 0 or x + w > width or y + h > height:
            problems.append(f"display {display_name} ({width:g} x {height:g}): {text!r} ({rect_text(extent)}) reaches "
                            f"off the display")
    for i, (text_a, extent_a) in enumerate(drawn_texts):
        for text_b, extent_b in drawn_texts[i + 1:]:
            overlap = overlap_area(extent_a, extent_b)
            if overlap:
                problems.append(f"display {display_name}: {text_a!r} ({rect_text(extent_a)}) overlaps {text_b!r} "
                                f"({rect_text(extent_b)}) by {overlap[0]:g} x {overlap[1]:g} px")
    return problems
