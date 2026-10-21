"""Draw a built device's pages as Live shows them, to PNG, from what the build wrote (devices/<name>/): the patcher's
presentation boxes at their exact rects, the chrome's rules and labels (the views script's LAYOUT), and which boxes
each page and each group choice shows (the UI script's PAGE_NAMES / PAGES / GROUPS).

    python3 tools/render_pages.py <device folder> <output folder> [--scale 2] [--theme dark|light]

One image per page and per choice of its group selectors: `<page>.png` is the page as it opens (every group on its
first choice), `<page>--<selector>-<item>.png` each other choice. Plus `layout.txt`: per image, every shown box by
band (x, width, the gap before it) and where a box leaves the layout contract (m4l_dev/layout_rules.py).

Positions, sizes, labels and colours (m4l_dev/themes.py) are exact; the controls' insides are drawn the plain way
(Live's own drawing isn't), and a display (jsui) is its frame and its name, not its drawing. Cozette text is drawn
from the glyphs the views use (templates/cozette-glyphs.js); Live's own font, which no source gives, is
the first of LIVE_FONT_CANDIDATES at the size where it is layout_rules.LIVE_TEXT_PIXELS_PER_CHARACTER a character.

Fails, saying why, when a shown box leaves the device or overlaps another shown with it (layout_rules), a control
has no text to show, or a chrome label runs into a box or off the device. Whether text fits its box is the build's
rule (layout_rules.live_text_problem), not this stand-in font's.
"""
import argparse
import itertools
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

KIT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT_DIRECTORY)
from m4l_dev import layout_rules  # noqa: E402
from m4l_dev.themes import THEMES  # noqa: E402

COZETTE_GLYPHS_PATH = os.path.join(KIT_DIRECTORY, "templates", "cozette-glyphs.js")
LIVE_FONT_CANDIDATES = ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf")
LIVE_DIAL_KNOB_DIAMETER = 22          # drawn size of a live.dial's knob, centred in its box (not a Live metric)


class RenderFailure(Exception):
    """A device whose pages can't be drawn, or don't lay out: the message says which and why."""


def read_js_assignment(script_text, variable_name, script_path):
    """The JSON value of `var <variable_name> = <json>;` on one line of a generated script."""
    found = re.search(r"^var " + re.escape(variable_name) + r" = (.*?);[ \t]*(//.*)?$", script_text, re.MULTILINE)
    if not found:
        raise RenderFailure(f"{script_path} has no line `var {variable_name} = ...;`: not a script the kit generated?")
    try:
        return json.loads(found.group(1))
    except json.JSONDecodeError as error:
        raise RenderFailure(f"{script_path}: {variable_name} isn't JSON ({error})") from error


def load_cozette():
    with open(COZETTE_GLYPHS_PATH, encoding="utf-8") as glyph_file:
        glyphs = read_js_assignment(glyph_file.read(), "COZETTE", COZETTE_GLYPHS_PATH)
    return {int(codepoint): bitmap for codepoint, bitmap in glyphs.items()}


def load_live_font():
    for path in LIVE_FONT_CANDIDATES:
        if os.path.exists(path):
            for size in range(14, 5, -1):          # the size whose average lowercase advance is closest to the rule
                font = ImageFont.truetype(path, size)
                if font.getlength("abcdefghijklmnopqrstuvwxyz") / 26 <= layout_rules.LIVE_TEXT_PIXELS_PER_CHARACTER:
                    return font
    raise RenderFailure(f"no stand-in for Live's font: none of {LIVE_FONT_CANDIDATES} exists")


class Device:
    """What the build wrote for one device, as the renderer needs it."""

    def __init__(self, device_folder):
        self.folder = os.path.abspath(device_folder)
        self.name = os.path.basename(self.folder.rstrip("/"))
        patcher_path = os.path.join(self.folder, f"{self.name}.maxpat")
        if not os.path.exists(patcher_path):
            raise RenderFailure(f"{patcher_path} doesn't exist: give the built device folder (devices/<name>/)")
        with open(patcher_path, encoding="utf-8") as patcher_file:
            patcher = json.load(patcher_file)["patcher"]
        self.width = int(patcher["devicewidth"])
        boxes = [entry["box"] for entry in patcher["boxes"]]
        self.shown_boxes = [b for b in boxes if b.get("presentation") == 1]
        self.foreground_boxes = [b for b in self.shown_boxes if not b.get("background")]
        views_scripts = {b["filename"] for b in self.shown_boxes if b["maxclass"] == "jsui"}
        if len(views_scripts) != 1:
            raise RenderFailure(f"{patcher_path}: expected one views script behind every display, found {views_scripts}")
        views_path = os.path.join(self.folder, views_scripts.pop())
        ui_path = os.path.join(self.folder, f"{self.name}-ui.js")
        with open(ui_path, encoding="utf-8") as ui_file:
            ui_text = ui_file.read()
        with open(views_path, encoding="utf-8") as views_file:
            self.layout = read_js_assignment(views_file.read(), "LAYOUT", views_path)
        self.page_names = read_js_assignment(ui_text, "PAGE_NAMES", ui_path)
        self.pages = read_js_assignment(ui_text, "PAGES", ui_path)
        self.groups = read_js_assignment(ui_text, "GROUPS", ui_path)
        self.boxes_by_varname = {b["varname"]: b for b in boxes if b.get("varname")}

    def views(self):
        """(page index, page, {selector: choice}, file stem) for every page and every choice of its selectors."""
        for page_index, page in enumerate(self.page_names):
            selectors = sorted(s for s, g in self.groups.items() if g["page"] == page)
            for picks in itertools.product(*(range(len(self.groups[s]["members"])) for s in selectors)):
                choice = dict(zip(selectors, picks))
                stem = page + "".join(f"--{s}-{self.choice_name(s, i)}" for s, i in choice.items() if i)
                yield page_index, page, choice, stem

    def choice_name(self, selector, index):
        box = self.boxes_by_varname.get(selector)
        items = (box or {}).get("saved_attribute_attributes", {}).get("valueof", {}).get("parameter_enum")
        name = items[index] if items and index < len(items) else str(index)
        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    def visible(self, page, choice):
        """The boxes shown on `page` with `choice`, as layout_rules.overlap_problems decides it."""
        on_some_page = {n for names in self.pages.values() for n in names}
        hidden = {n for selector, picked in choice.items()
                  for i, members in enumerate(self.groups[selector]["members"]) if i != picked for n in members}
        return [b for b in self.shown_boxes
                if (b.get("varname") not in on_some_page or b["varname"] in self.pages[page])
                and b.get("varname") not in hidden]


def values_of(box):
    return box.get("saved_attribute_attributes", {}).get("valueof", {})


def shown_value(box):
    values = values_of(box)
    initial = (values.get("parameter_initial") or [values.get("parameter_mmin", 0)])[0]
    items = values.get("parameter_enum")
    if items:
        return items[max(0, min(len(items) - 1, int(initial)))]
    return f"{initial:g}"


class Painter:
    def __init__(self, device, theme_name, cozette, live_font):
        self.device, self.cozette, self.live_font = device, cozette, live_font
        self.theme = {k: tuple(round(c * 255) for c in v[:3]) for k, v in THEMES[theme_name].items()}
        self.image = Image.new("RGB", (device.width, layout_rules.DEVICE_HEIGHT), self.theme["pad"])
        self.draw = ImageDraw.Draw(self.image)

    def mix(self, colour, alpha):
        return tuple(round(c * alpha + p * (1 - alpha)) for c, p in zip(colour, self.theme["pad"]))

    def rect(self, x, y, w, h, colour):
        if w > 0 and h > 0:
            self.draw.rectangle([x, y, x + w - 1, y + h - 1], fill=colour)

    def frame(self, x, y, w, h, colour):
        self.draw.rectangle([x, y, x + w - 1, y + h - 1], outline=colour)

    def cozette_width(self, text):
        return sum(self.glyph(ord(c))[0] for c in text)

    def glyph(self, codepoint):
        if codepoint not in self.cozette:
            raise RenderFailure(f"Cozette has no glyph for U+{codepoint:04X} {chr(codepoint)!r} "
                                f"(templates/cozette-glyphs.js): the device would draw '?'")
        return self.cozette[codepoint]

    def cozette_text(self, text, x, baseline, colour):
        """As the views script's text(): `baseline` is the glyphs' baseline."""
        pen = round(x)
        for character in text:
            advance, w, h, x_offset, y_offset, *rows = self.glyph(ord(character))
            top = round(baseline) - (y_offset + h)
            for r, bits in enumerate(rows):
                padded = -(-w // 8) * 8
                for c in range(w):
                    if bits >> (padded - 1 - c) & 1:
                        self.draw.point((pen + x_offset + c, top + r), fill=colour)
            pen += advance

    def live_text(self, text, x, y, w, h, colour, align="centre"):
        """Text in the stand-in for Live's font, in the box (x, y, w, h)."""
        width = self.live_font.getlength(text)
        left = x + (w - width) / 2 if align == "centre" else x + 3
        ascent, descent = self.live_font.getmetrics()
        self.draw.text((left, y + (h - ascent - descent) / 2), text, font=self.live_font, fill=colour)

    def chrome(self, page_index):
        """As the views script's chromeView and linkView."""
        t, layout = self.theme, self.device.layout
        self.rect(0, 21, self.device.width, 1, self.mix(t["unlit"], 0.6))
        page = layout["pages"][max(0, min(len(layout["pages"]) - 1, page_index))]
        for rule_x in page["rules"]:
            self.rect(rule_x, 28, 1, layout_rules.DEVICE_HEIGHT - 36, self.mix(t["unlit"], 0.35))
        for text, x, baseline, kind in page["labels"]:
            self.cozette_text(text, x, baseline, t["unlit"] if kind == "hint" else t["label"])
        self.cozette_text(f"{layout['subtitle_text']}  v{layout['version']}", layout["subtitle"], 15, t["label"])

    def box(self, box, page_index, choice):
        t = self.theme
        x, y, w, h = box["presentation_rect"]
        kind, values = box["maxclass"], values_of(box)
        if kind == "jsui":
            mode = box.get("jsarguments", [""])[0]
            if mode == "link":
                chip_width = self.cozette_width(self.device.layout["link_chip_text"]) + 8
                self.rect(x, y, chip_width, 15, t["ink"])
                self.cozette_text(self.device.layout["link_chip_text"], x + 4, y + 12, t["pad"])
            else:
                self.rect(x, y, w, h, t["well"])
                self.frame(x, y, w, h, self.mix(t["unlit"], 0.5))
                name = box.get("annotation_name", mode).lower()
                self.cozette_text(name[:max(0, int(w - 8) // layout_rules.COZETTE_ADVANCE)], x + 4, y + 12, t["label"])
        elif kind == "live.dial":
            self.frame(x, y, w, h, self.mix(t["unlit"], 0.3))          # the box itself, so its width shows
            self.live_text(values["parameter_shortname"], x, y, w, 11, t["ink"])
            d = LIVE_DIAL_KNOB_DIAMETER
            cx, cy = x + w / 2, y + 24
            self.draw.arc([cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2], 135, 405, fill=t["unlit"], width=2)
            self.draw.line([cx, cy, cx, cy - d / 2 + 2], fill=t["ink"], width=2)
            self.live_text(shown_value(box), x, y + h - 11, w, 11, t["label"])
        elif kind == "live.tab":
            items = values["parameter_enum"]
            if items == self.device.page_names:
                picked = page_index
            else:
                picked = choice.get(box.get("varname"), items.index(shown_value(box)))
            rows = int(box.get("num_lines_presentation", 1))
            per_row = -(-len(items) // rows)
            button_w, button_h = w / per_row, h / rows
            for i, item in enumerate(items):
                bx, by = x + (i % per_row) * button_w, y + (i // per_row) * button_h
                selected = i == picked
                self.rect(round(bx), round(by), round(button_w), round(button_h), t["ink"] if selected else t["pad"])
                self.frame(round(bx), round(by), round(button_w), round(button_h), t["ink"])
                text_x = bx + (button_w - self.cozette_width(item)) / 2
                self.cozette_text(item, text_x, by + button_h - 3, t["inverse"] if selected else t["ink"])
        elif kind == "live.menu":
            self.rect(x, y, w, h, t["well"])
            self.frame(x, y, w, h, self.mix(t["unlit"], 0.6))
            arrow = layout_rules.LIVE_MENU_ARROW_PIXELS
            self.live_text(shown_value(box), x, y, w - arrow, h, t["ink"], align="left")
            ax, ay = x + w - arrow / 2 - 3, y + h / 2
            self.draw.polygon([(ax - 3, ay - 2), (ax + 3, ay - 2), (ax, ay + 2)], fill=t["ink"])
        elif kind == "live.text":
            self.frame(x, y, w, h, t["ink"])
            self.live_text(box.get("text") or values.get("parameter_shortname", ""), x, y, w, h, t["ink"])
        elif kind == "live.numbox":
            self.rect(x, y, w, h, t["well"])
            self.frame(x, y, w, h, self.mix(t["unlit"], 0.6))
            self.live_text(shown_value(box), x, y, w, h, t["ink"])
        else:
            self.frame(x, y, w, h, t["warm"])
            self.live_text(kind, x, y, w, min(h, 15), t["warm"])


def text_problems(device, page, visible):
    """A control with nothing to show, or a chrome label that runs off the device or into a box shown with it."""
    problems = []
    for box in visible:
        values = values_of(box)
        if box["maxclass"].startswith("live.") and not (box.get("text") or values.get("parameter_shortname")
                                                       or values.get("parameter_enum")):
            problems.append(f"{box.get('varname', box['id'])} ({box['maxclass']}) has no text to show")
    page_layout = device.layout["pages"][device.page_names.index(page)]
    for text, x, baseline, _ in page_layout["labels"]:
        left, top, right, bottom = x, baseline - 9, x + layout_rules.COZETTE_ADVANCE * len(text), baseline + 2
        if left < 0 or top < 0 or right > device.width or bottom > layout_rules.DEVICE_HEIGHT:
            problems.append(f"page {page!r}: label {text!r} at ({x}, {baseline}) leaves the device")
        for box in visible:
            if box.get("background"):
                continue
            bx, by, bw, bh = box["presentation_rect"]
            if left < bx + bw and bx < right and top < by + bh and by < bottom:
                problems.append(f"page {page!r}: label {text!r} at ({x}, {baseline}) runs into "
                                f"{box.get('varname', box['id'])} {box['presentation_rect']}")
    return problems


def layout_facts(visible):
    """Every shown box by band (its y), left to right: x, width, gap before it; and its breaks of the contract."""
    lines = []
    foreground = [b for b in visible if not b.get("background")]
    for band_y in sorted({b["presentation_rect"][1] for b in foreground}):
        row = sorted((b for b in foreground if b["presentation_rect"][1] == band_y), key=lambda b: b["presentation_rect"][0])
        cells, right = [], None
        for box in row:
            x, _, w, h = box["presentation_rect"]
            gap = "" if right is None else f" gap {x - right:g}"
            cells.append(f"{box.get('varname', box['id'])} [{box['maxclass']}] x {x:g} w {w:g} h {h:g}{gap}")
            right = x + w
        lines.append(f"  y {band_y:g}: " + "; ".join(cells))
    for box in foreground:
        x, y, w, h = box["presentation_rect"]
        name, notes = box.get("varname", box["id"]), []
        if box["maxclass"] == "live.dial" and (w, h) != (layout_rules.DIAL_WIDTH, layout_rules.DIAL_HEIGHT):
            notes.append(f"dial {w:g} x {h:g}, the contract's is {layout_rules.DIAL_WIDTH} x {layout_rules.DIAL_HEIGHT}")
        if box["maxclass"] in ("live.menu", "live.tab", "live.text", "live.numbox") and h == layout_rules.ROW_H \
                and y not in (layout_rules.HEADER_Y, layout_rules.ROW_Y):
            notes.append(f"a {layout_rules.ROW_H} px row control at y {y:g}, not in the row band (y {layout_rules.ROW_Y})")
        if any(v % layout_rules.GRID for v in (x, w)):
            notes.append(f"x {x:g} / w {w:g} off the {layout_rules.GRID} px grid")
        if notes:
            lines.append(f"  contract: {name}: " + "; ".join(notes))
    for view in (b for b in foreground if b["maxclass"] == "jsui" and b["presentation_rect"][1] == layout_rules.VIEW_Y):
        vx, _, vw, _ = view["presentation_rect"]
        under = [b for b in foreground if b is not view and b["presentation_rect"][1] > layout_rules.VIEW_Y
                 and vx <= b["presentation_rect"][0] < vx + vw]
        if under:
            used_right = max(b["presentation_rect"][0] + b["presentation_rect"][2] for b in under)
            lines.append(f"  section {view.get('varname')}: display x {vx:g}..{vx + vw:g} (w {vw:g}); the controls "
                         f"under it span x {vx:g}..{used_right:g} ({used_right - vx:g} px, {vx + vw - used_right:g} px "
                         f"of the display has none under it)")
    return lines


def render_device(device_folder, output_folder, scale=2, theme_name="dark"):
    """Render every page and group choice; returns the image paths. Raises RenderFailure on a layout problem."""
    device = Device(device_folder)
    problems = layout_rules.overlap_problems(device.foreground_boxes, device.page_names, device.pages, device.groups,
                                             device.width)
    cozette, live_font = load_cozette(), load_live_font()
    os.makedirs(output_folder, exist_ok=True)
    written, facts = [], [f"{device.name}: {device.width} x {layout_rules.DEVICE_HEIGHT} px, drawn x{scale}"]
    for page_index, page, choice, stem in device.views():
        visible = device.visible(page, choice)
        problems += text_problems(device, page, visible)
        painter = Painter(device, theme_name, cozette, live_font)
        if any(b.get("background") for b in visible):
            painter.chrome(page_index)
        for box in visible:
            if not box.get("background"):
                painter.box(box, page_index, choice)
        image = painter.image.resize((device.width * scale, layout_rules.DEVICE_HEIGHT * scale), Image.NEAREST)
        path = os.path.join(output_folder, f"{stem}.png")
        image.save(path)
        written.append(path)
        facts.append(f"\n{stem}.png (page {page!r}{', ' + str(choice) if choice else ''})")
        facts += layout_facts(visible)
    with open(os.path.join(output_folder, "layout.txt"), "w", encoding="utf-8") as facts_file:
        facts_file.write("\n".join(facts) + "\n")
    if problems:
        raise RenderFailure(f"{device.name}: the pages don't lay out:\n  " + "\n  ".join(sorted(set(problems))))
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("device_folder")
    parser.add_argument("output_folder")
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--theme", choices=sorted(THEMES), default="dark")
    arguments = parser.parse_args()
    try:
        written = render_device(arguments.device_folder, arguments.output_folder, arguments.scale, arguments.theme)
    except RenderFailure as failure:
        sys.exit(f"render_pages.py: {failure}")
    print("\n".join(written + [os.path.join(arguments.output_folder, "layout.txt")]))


if __name__ == "__main__":
    main()
