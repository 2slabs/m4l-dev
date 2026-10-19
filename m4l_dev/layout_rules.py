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

# live.tab splits its width equally between its buttons; each needs its longest name in Cozette plus this. Calibrated
# from what 2sl stab ships and has been seen in Live: Sub Mode's "-2 pls" in a 37 px button is the tightest
# (37 = 6 x 6 + 1); a tighter button has not been seen.
LIVE_TAB_BUTTON_SLACK = 1
# Live draws a live.dial's short name, a live.menu's item and a live.text's text in its own font, inside the box (not
# Cozette). No source gives that font's metrics (the Max reference lists live.dial's fontname / fontsize with no
# default). Calibrated from what 2sl gate played in Live: v0.5's 8-character dial names ("Pressure", "Symmetry",
# "Velocity", "Feedback") in 44 px dials: 5.5 px a character (SHORTCUTS.md).
LIVE_TEXT_PIXELS_PER_CHARACTER = 5.5
LIVE_MENU_ARROW_PIXELS = 12           # a live.menu's arrow, beside its item
LIVE_MENU_MINIMUM_WIDTH = 40
LIVE_TOGGLE_PADDING_PIXELS = 8        # a live.text's text needs this much more than its characters
# the header's page tabs are drawn at least this wide each, and wide enough for the longest page name + 12
PAGE_TAB_MINIMUM_WIDTH = 48


def check_on_grid(what, value):
    if value % GRID:
        raise BuildError(f"{what} {value} is off the {GRID} px grid")


def on_grid(pixels):
    """`pixels` rounded up to the GRID."""
    return int(math.ceil(pixels / GRID) * GRID)


def live_dial_width(short_name):
    """The narrowest live.dial that holds its short name: at least DIAL_WIDTH, on the grid."""
    return max(DIAL_WIDTH, on_grid(LIVE_TEXT_PIXELS_PER_CHARACTER * len(short_name)))


def live_menu_width(items):
    """The narrowest live.menu that holds its longest item and its arrow, on the grid."""
    return max(LIVE_MENU_MINIMUM_WIDTH,
               on_grid(LIVE_TEXT_PIXELS_PER_CHARACTER * max(len(item) for item in items) + LIVE_MENU_ARROW_PIXELS))


def live_toggle_width(text):
    """The narrowest live.text that holds `text`, on the grid."""
    return on_grid(LIVE_TEXT_PIXELS_PER_CHARACTER * len(text) + LIVE_TOGGLE_PADDING_PIXELS)


def live_tabs_width(items, rows=1):
    """The narrowest live.tab the button rule (live_tab_button_problem) allows, on the grid."""
    per_row = -(-len(items) // rows)
    return on_grid(per_row * (COZETTE_ADVANCE * max(len(item) for item in items) + LIVE_TAB_BUTTON_SLACK))


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
    button_width = width // buttons_per_row
    longest = max(len(item) for item in items)
    needed = COZETTE_ADVANCE * longest + LIVE_TAB_BUTTON_SLACK
    if button_width < needed:
        return (f"{buttons_per_row} buttons a row in {width} px leave {button_width} px each; the longest name "
                f"({longest} characters) needs {needed}")
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
