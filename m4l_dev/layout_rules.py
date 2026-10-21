"""The 2sl layout contract (from 2sl stab) and the checks the build runs on it.

A device is DEVICE_HEIGHT px high, as wide as it needs, on a GRID px grid. A header row (HEADER_Y), then every
section has three bands aligned across the device: a display (VIEW_Y, VIEW_H), a row of chips, menus and tabs
(ROW_Y, ROW_H high) and dials (DIAL_Y). Text is Cozette, COZETTE_ADVANCE px a character.
"""
import math

from m4l_dev.build_error import BuildError

DEVICE_HEIGHT = 169
GRID = 4
DIAL_WIDTH, DIAL_HEIGHT = 44, 48
VIEW_Y, VIEW_H, ROW_Y, DIAL_Y = 28, 64, 98, 119
ROW_H = 15
HEADER_Y = 3
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


def overlap_problems(shown_boxes, page_names, boxes_on_page, groups, device_width):
    """Two things shown at the same time that overlap, or one leaving the device: for every page and every choice
    of its group selectors, the header and the page's visible boxes.

    shown_boxes: presentation boxes (not the background); boxes_on_page: page -> varnames on it (a varname on no
    page is in the header, shown on every page); groups: selector varname -> {"page", "members": [[varnames]]}."""
    on_some_page = {n for names in boxes_on_page.values() for n in names}
    problems = []
    for box in shown_boxes:
        x, y, w, h = box["presentation_rect"]
        if x < 0 or y < 0 or x + w > device_width or y + h > DEVICE_HEIGHT:
            problems.append(f"{box.get('varname', box['id'])} at {box['presentation_rect']} leaves the "
                            f"{device_width} x {DEVICE_HEIGHT} device")
    for page in page_names:
        selectors = [s for s, g in groups.items() if g["page"] == page]
        choices = [[]]
        for selector in selectors:
            choices = [c + [(selector, i)] for c in choices for i in range(len(groups[selector]["members"]))]
        for choice in choices:
            hidden = {n for selector, picked in choice
                      for i, members in enumerate(groups[selector]["members"]) if i != picked for n in members}
            visible = [b for b in shown_boxes if (b.get("varname") not in on_some_page or b["varname"] in boxes_on_page[page])
                       and b.get("varname") not in hidden]
            for i, a in enumerate(visible):
                ax, ay, aw, ah = a["presentation_rect"]
                for b in visible[i + 1:]:
                    bx, by, bw, bh = b["presentation_rect"]
                    if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                        problems.append(f"page {page!r} {dict(choice) or ''}: {a.get('varname', a['id'])} "
                                        f"{a['presentation_rect']} overlaps {b.get('varname', b['id'])} "
                                        f"{b['presentation_rect']}")
    return sorted(set(problems))
