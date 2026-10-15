#!/usr/bin/env python3
"""2sl drums: a 909-style drum machine instrument for Max for Live, built for trying patterns.

  python3 src/2sl-drums.py   # writes src/2sl-drums.maxpat, devices/2sl-drums/ (the .amxd and its scripts) and
                             # dist/2sl-drums-<version>.amxd (frozen: one file to share)

Needs references/drums/mirror/patterns/grids_resources.cc (run references/drums/mirror_patterns.sh): the Grids
pattern map is read from it at build time and embedded in the device's brain.

Signal flow:
  Live's transport (16th clock) -> js 2sl-drums.js (the pattern engine: canned / generated patterns, Grids
  density and variation, fills, swing) -> gen~ (seven voices: BD SD RS CP CH/OH RD) -> plugout~
  MIDI notes on the track also play the voices (GM drum notes).
Sources: references/drums/ (patterns.md, voices.md, production.md); devices/2sl-drums/README.md cites them.
"""
import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
kit = importlib.import_module("2sl_kit")
dsp = importlib.import_module("2sl_drums_dsp")
sys.path.insert(0, os.path.join(ROOT, "tools"))
genexpr = importlib.import_module("genexpr")
try:
    # our GenExpr subset checker (tools/genexpr.py): syntax, scoping, names; not Max's compiler
    genexpr.check(dsp.KIT, num_inputs=0, num_outputs=2)
except genexpr.GenExprError as problem:
    raise kit.BuildError(f"2sl-drums.py: the gen~ voices (src/2sl_drums_dsp.py KIT): {problem}")

VERSION = "0.1.0"
DEVICE_DIRECTORY = os.path.join(ROOT, "devices", "2sl-drums")
GRIDS_RESOURCES = os.path.join(ROOT, "references", "drums", "mirror", "patterns", "grids_resources.cc")
GRIDS_PATTERN_GENERATOR = os.path.join(ROOT, "references", "drums", "mirror", "patterns", "grids_pattern_generator.cc")

# ---- the voices ------------------------------------------------------------------------------------------
# notes: GM drum notes that play the voice from a clip. fills: gets phrase-end fill hits. grids: which Grids
# channel (0 BD, 1 SD, 2 HH) gives the Grids style's row, and what of it is kept (Grids has 3 channels; the
# clap and open hat rows from them are this device's choice, the README lists it).
VOICES = [
    {"id": "bd", "name": "bd", "notes": [36, 35], "fills": False, "grids": {"instrument": 0, "keep": "all"}},
    {"id": "sd", "name": "sd", "notes": [38, 40], "fills": True, "grids": {"instrument": 1, "keep": "all"}},
    {"id": "rs", "name": "rs", "notes": [37], "fills": True, "grids": None},
    {"id": "cp", "name": "cp", "notes": [39], "fills": True, "grids": {"instrument": 1, "keep": "accents"}},
    {"id": "ch", "name": "ch", "notes": [42, 44], "fills": False, "grids": {"instrument": 2, "keep": "all"}},
    {"id": "oh", "name": "oh", "notes": [46], "fills": False, "grids": {"instrument": 2, "keep": "offbeat eighths"}},
    {"id": "rd", "name": "rd", "notes": [51, 59], "fills": False, "grids": None},
]
VOICE_IDS = [v["id"] for v in VOICES]
if VOICE_IDS != dsp.VOICE_IDS:
    raise kit.BuildError(f"2sl-drums.py: the voices {VOICE_IDS} and the DSP's {dsp.VOICE_IDS} differ")

# a grade's Grids level: patterns.md F's legend (X > 192, x 100-192, o 40-99, . < 40), one level inside each
GRADE_LEVELS = [0, 72, 144, 224]
GRADE_CHARACTERS = ".oxX"
# the 909's shuffle 1-7 (patterns.md B4: 7 levels at the 16th scale, 1 = none). No source maps a level to a
# percent; this reads each level as 2 more 96-ppqn ticks of delay on every second 16th (unsourced, README).
SWING_PERCENT = [50 + (level * 2 / 24) * 50 for level in range(7)]

FOUR_ON_THE_FLOOR = "x...x...x...x..."
REST = "................"

# ---- styles: canned kits from patterns.md, and what Generate / Reroll draw from ------------------------------
# "kits" are the patterns as their sources give them (placements marked `mine` follow the source's text where
# its grid is a screenshot; the README lists them). "extra" rows join the kits' rows in the style's pool.
STYLES = [
    {"name": "dub techno", "kind": "canned", "tempo": "120-145 bpm", "swing": "none: the groove is in the delay",
     "kits": [
         {"name": "P1 basic channel", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "cp": "....x.......x...",
                                               "oh": "..x...x...x...x."}},
         {"name": "P8 4 ingredients", "rows": {"bd": FOUR_ON_THE_FLOOR, "oh": "..x...x...x...x."}},
         # P1's percussion: "a couple hits exactly on offbeat 16th notes" (placement mine)
         {"name": "P1 + rim 16ths", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "cp": "....x.......x...",
                                             "oh": "..x...x...x...x.", "rs": ".......x.......x"}},
     ],
     "extra": {"rs": [(".x.........x....", "P1 text, mine"), ("...x.......x....", "P1 text, mine"), (REST, "rest")],
               "ch": [(REST, "rest")], "rd": [(REST, "rest")]}},
    {"name": "deep house", "kind": "canned", "tempo": "120-127 bpm", "swing": "50-60%",
     "kits": [
         {"name": "P3 minimal house", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "cp": "....x.......x...",
                                               "ch": "..x...x...x...x.", "rs": "..x...x...x...x."}},
         {"name": "P7 house 124", "rows": {"bd": FOUR_ON_THE_FLOOR, "cp": "....x.......x...", "ch": "..x...x...x...x.",
                                           "oh": "......x.......x."}},
         # P4: "off-beat clap" (on 2 and 4 as P7), closed hat "shuffle on the 8th and 16th divisions" (placement mine)
         {"name": "P4 deep house", "rows": {"bd": FOUR_ON_THE_FLOOR, "cp": "....x.......x...", "oh": "..x...x...x...x.",
                                            "ch": ".x.x.x.x.x.x.x.x"}},
     ],
     "extra": {"sd": [(REST, "rest")], "rs": [(REST, "rest")], "rd": [(REST, "rest")]}},
    {"name": "detroit", "kind": "canned", "tempo": "120-125 bpm", "swing": "55-60%",
     "kits": [
         # P2: snare and rim "work against each other", the rim "doesn't ever hit on the same beat as a kick" (placement mine)
         {"name": "P2 motor city", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "rs": "...x..x....x..x.",
                                            "oh": "..x...x...x...x.", "ch": ".x.x.x.x.x.x.x.x"}},
         {"name": "P2 rim answer", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x..x", "rs": "..x....x..x....x",
                                            "oh": "..x...x...x...x.", "ch": "xxx.xxx.xxx.xxx."}},
     ],
     "extra": {"cp": [(REST, "rest"), ("....x.......x...", "P3")], "rd": [(REST, "rest")]}},
    {"name": "dark techno", "kind": "canned", "tempo": "128-137 bpm", "swing": "50-54%",
     "kits": [
         # P7 techno 130: hat on every 16th low, accents on the offbeats; ride 8ths; rim on 2 and 4
         {"name": "P7 techno 130", "rows": {"bd": FOUR_ON_THE_FLOOR, "ch": "xxXxxxXxxxXxxxXx", "rd": "x.x.x.x.x.x.x.x.",
                                            "rs": "....x.......x..."}},
         # P9: offbeat open hat, the ride on the same notes
         {"name": "P9 mills 137", "rows": {"bd": FOUR_ON_THE_FLOOR, "oh": "..x...x...x...x.", "rd": "..x...x...x...x."}},
         # P5: ride 8ths "with a shorter, quieter note on every second hit"; closed hat around the offbeat
         {"name": "P5 dark rumble", "rows": {"bd": FOUR_ON_THE_FLOOR, "rd": "X.x.X.x.X.x.X.x.", "ch": "..x...x...x...x."}},
         # P6: ghost kicks just before beats 2 and 4 (approx), offbeat open hat
         {"name": "P6 rolling", "rows": {"bd": "x..ox...x..ox...", "oh": "..x...x...x...x."}},
     ],
     # P10: 3- and 5-16th loops repeated across the bar
     "extra": {"ch": [("x..x..x..x..x..x", "P10 3-loop"), ("x....x....x....x", "P10 5-loop"), (REST, "rest")],
               "sd": [(REST, "rest")], "cp": [(REST, "rest")], "oh": [(REST, "rest")]}},
    {"name": "euclid", "kind": "euclid", "tempo": "any", "swing": "any",
     "kits": [
         {"name": "P11 tresillo", "rows": {"bd": FOUR_ON_THE_FLOOR, "rs": "x..x..x.x..x..x.", "ch": "..x...x...x...x."}},
         {"name": "P11 bossa", "rows": {"bd": FOUR_ON_THE_FLOOR, "rs": "x..x..x...x..x..", "oh": "..x...x...x...x."}},
         {"name": "P11 son clave", "rows": {"bd": FOUR_ON_THE_FLOOR, "cp": "x..x..x...x.x...", "ch": "x.xx.xx.x.xx.xx."}},
     ],
     # Generate / Reroll: E(k, 16) with k in this range and a random rotation (Ableton's Euclidean rotates, B3);
     # the ranges are mine
     "euclid": {"bd": [3, 5], "sd": [1, 3], "rs": [2, 7], "cp": [1, 3], "ch": [4, 11], "oh": [2, 5], "rd": [3, 8]}},
    {"name": "grids", "kind": "grids", "tempo": "any", "swing": "any",
     # canned: points of the Grids map (x, y 0-255); 0, 64, 128, 192 land on nodes exactly
     "kits": [{"name": "grids 128,128", "x": 128, "y": 128}, {"name": "grids 0,0", "x": 0, "y": 0},
              {"name": "grids 64,64", "x": 64, "y": 64}, {"name": "grids 192,192", "x": 192, "y": 192},
              {"name": "grids 0,128", "x": 0, "y": 128}]},
]
STYLE_NAMES = [s["name"] for s in STYLES]


def check_row(row, where):
    if len(row) != 16 or set(row) - set(GRADE_CHARACTERS):
        raise kit.BuildError(f"2sl-drums.py: {where}: row {row!r} must be 16 of {GRADE_CHARACTERS!r}")
    return row


for style in STYLES:
    if style["kind"] in ("canned", "euclid"):
        pool = {voice_id: [] for voice_id in VOICE_IDS}
        for kit_entry in style["kits"]:
            for voice_id, row in kit_entry["rows"].items():
                if voice_id not in VOICE_IDS:
                    raise kit.BuildError(f"2sl-drums.py: {style['name']} / {kit_entry['name']}: no voice {voice_id!r}")
                check_row(row, f"{style['name']} / {kit_entry['name']} / {voice_id}")
            for voice_id in VOICE_IDS:
                row = kit_entry["rows"].get(voice_id, REST)
                if row not in [p["row"] for p in pool[voice_id]]:
                    pool[voice_id].append({"row": row, "source": kit_entry["name"] if row != REST else "rest"})
        for voice_id, extras in style.get("extra", {}).items():
            for row, source in extras:
                check_row(row, f"{style['name']} extra / {voice_id}")
                if row not in [p["row"] for p in pool[voice_id]]:
                    pool[voice_id].append({"row": row, "source": source})
        style["pool"] = pool


# ---- Grids: the map, read from the mirrored firmware source --------------------------------------------------

def read_grids():
    for path in (GRIDS_RESOURCES, GRIDS_PATTERN_GENERATOR):
        if not os.path.isfile(path):
            raise kit.BuildError(f"2sl-drums.py: {os.path.relpath(path, ROOT)} is missing: run "
                                 "references/drums/mirror_patterns.sh (the Grids map is read from it)")
    resources = open(GRIDS_RESOURCES, encoding="utf-8").read()
    nodes = []
    for index in range(25):
        found = re.search(r"node_%d\[\] PROGMEM = \{([^}]*)\}" % index, resources)
        if not found:
            raise kit.BuildError(f"2sl-drums.py: grids_resources.cc has no node_{index}")
        values = [int(v) for v in re.findall(r"\d+", found.group(1))]
        if len(values) != 96 or not all(0 <= v <= 255 for v in values):
            raise kit.BuildError(f"2sl-drums.py: grids node_{index} has {len(values)} values, expected 96 bytes")
        nodes.append(values)
    generator = open(GRIDS_PATTERN_GENERATOR, encoding="utf-8").read()
    found = re.search(r"drum_map\[5\]\[5\] = \{(.*?)\};", generator, re.S)
    if not found:
        raise kit.BuildError("2sl-drums.py: grids_pattern_generator.cc has no drum_map[5][5]")
    rows = re.findall(r"\{([^{}]*)\}", found.group(1))
    drum_map = [[int(n) for n in re.findall(r"node_(\d+)", row)] for row in rows]
    if len(drum_map) != 5 or any(len(r) != 5 for r in drum_map):
        raise kit.BuildError(f"2sl-drums.py: grids drum_map is {drum_map}, expected 5 x 5")
    return nodes, drum_map


GRIDS_NODES, GRIDS_DRUM_MAP = read_grids()

# ---- what Live's Info View shows -----------------------------------------------------------------------------
LEVEL_INFO = "Level of the {} in the mix. 909 accents still play louder (Accent)."
INFO = {
    # views
    "Link view": ("2sl.to", "Opens 2sl.to in your browser."),
    "Grid view": ("Pattern", "The pattern: a row per voice, 16 steps. Click a step: rest, hit, accent (bright with a bar "
                  "on top). Shift-click: a ghost (dim; plays only at high Density or with Variation). Left: the voice "
                  "name, click to mute (struck through). Right: L locks the row (Generate, Reroll, Style and Canned "
                  "leave it), R rerolls it. Blue outline: the step playing. Warm: a fill bar."),
    "Style view": ("Style", "The style's name, the tempo and swing its sources use, the canned kit loaded last, and "
                   "(with Fill on) the bar in the fill phrase, warm on the fill bar."),
    "Mix view": ("Mix", "Each voice's level as a bar, flashing as it plays (taller for louder hits)."),
    "BD view": ("BD", "The kick's level (mint) and pitch (grey) over its decay, as the voice makes them. Top right: "
                "the pitch it settles to and the decay."),
    "SD view": ("SD", "The snare's drum (mint) and snappy noise (grey) envelopes. Top right: VCO 1's pitch."),
    "RS view": ("RS", "The rim shot's envelope: three rings at 500, 220 and 1000 Hz, clipped, short."),
    "CP view": ("CP", "The clap's envelope: four claps 11 ms apart, then the softer tail."),
    "Hats view": ("Hats", "Closed (mint) and open (grey) hat envelopes. They are one voice, as on the 909: a closed "
                  "hit cuts an open one. Top right: the ROM clock and bits."),
    "RD view": ("RD", "The ride's envelope; its length follows Tune, as the 909's ROM clock does."),
    # header
    "Page": ("Page", "Shows the play, bd sd rs or cp hats rd page. Controls on hidden pages keep working."),
    "Preset": ("Preset", "Sets every control to a preset and loads its style's first kit; tweak from there. "
               "When Live reopens a set, your saved pattern and tweaks win."),
    "Volume": ("Volume", "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs."),
    "Stop": ("Stop", "Panic: fades every voice out in 20 ms. Live's transport stopping doesn't run it."),
    # play: pattern
    "Variation": ("Variation", "Grids' randomness: every bar, each voice gets a random push to all its steps' levels "
                  "(up to about 62 of 255), so weaker steps come and go a bar at a time. With Fill on it also adds "
                  "phrase-end fills. 0 = the pattern repeats exactly."),
    "Density": ("Density", "Grids' density: a step plays when its level is above 255 - Density. At 50% (default) "
                "accents and hits play, ghosts don't; lower thins to accents, higher brings ghosts in."),
    "Accent": ("Accent", "How much quieter a normal hit is than an accent, like the 909's Total Accent. 0 = all "
               "the same. Default 70%."),
    "Swing": ("Swing", "The 909's shuffle, 1 (none) to 7: every second 16th later, 50% to 75% of the 8th. "
              "Sample-accurate in the voices."),
    "Fill": ("Fill", "Phrase-end fills: off, or in the last beat of every 4 or 8 bars. Snare, rim and clap get extra "
             "hits and an open hat may close. Scaled by Variation (none at 0)."),
    # play: style
    "Style": ("Style", "Where patterns come from: dub techno, deep house, detroit, dark techno (sourced grids), "
              "euclid (Toussaint's rhythms) or grids (the Mutable Instruments Grids map). Loads its first kit."),
    "Generate": ("Generate", "A new kit pattern from the style for every unlocked voice: rows from the style's "
                 "sources, a new Euclidean row, or a new point on the Grids map."),
    "Canned": ("Canned", "The style's next canned kit, as its source has it (unlocked voices)."),
    # play: mix
}
for voice in VOICES:
    INFO[f"{voice['name'].upper()} Level"] = (f"{voice['name'].upper()} Level", LEVEL_INFO.format(voice["name"]))
INFO.update({
    # bd sd rs
    "BD Tune": ("BD Tune", "The pitch the kick settles to, 30-90 Hz (default 50)."),
    "BD Sweep": ("BD Sweep", "How far above Tune the kick starts: up to 4x, falling in about 30 ms. Default 50%."),
    "BD Decay": ("BD Decay", "Time to -40 dB, 60 ms to 2 s (default 450 ms). Flat at first, like the 909's ENV-1."),
    "BD Attack": ("BD Attack", "The click: a short pulse and low-passed noise, as the 909's Attack knob. Default 50%."),
    "BD Soft": ("BD Soft", "0 = 909 punch. Up: a sine instead of the clipped triangle, less and slower sweep, "
                "no click, a slower start and a darker low-pass, for a soft, round, muffled kick."),
    "BD Bits": ("BD Bits", "Bit reduction on the kick, 16 (clean) down to 3."),
    "SD Tune": ("SD Tune", "VCO 1's pitch, 120-320 Hz (default 180); VCO 2 follows at x1.83. Both bend for 20 ms."),
    "SD Tone": ("SD Tone", "Decay of the main snappy noise after its 24 ms hold, 40-500 ms (default 160)."),
    "SD Snappy": ("SD Snappy", "The snare's noise level; 0 = drum only. Default 60%."),
    "SD Bits": ("SD Bits", "Bit reduction on the snare, 16 (clean) down to 3."),
    "RS Bits": ("RS Bits", "Bit reduction on the rim shot, 16 (clean) down to 3."),
    # cp hats rd
    "CP Bits": ("CP Bits", "Bit reduction on the clap, 16 (clean) down to 3. Attack's dub techno clap uses 6."),
    "Hat Tune": ("Hat Tune", "The hat ROM's clock, x0.43 to x1.7 (Whittle's tune mod range): pitch and grit."),
    "Hat Bits": ("Hat Bits", "The hat ROM's bit depth: 6 on the 909 (default). Lower is grittier."),
    "CH Decay": ("CH Decay", "Closed hat decay to -40 dB, 10-300 ms (default 60)."),
    "OH Decay": ("OH Decay", "Open hat decay to -40 dB, 80 ms to 2 s (default 500). A closed hit cuts it."),
    "RD Tune": ("RD Tune", "The ride ROM's clock, x0.6 to x1.5: pitch and length together, as on the 909 (no decay knob)."),
    "RD Bits": ("RD Bits", "The ride ROM's bit depth: 6 on the 909 (default)."),
})

# ---- BASE: the Init preset, every control's initial value -----------------------------------------------------
BASE = {"Style": 0, "Variation": 0, "Density": 50, "Accent": 70, "Swing": 0, "Fill": 0, "Volume": 0,
        "BD Level": 80, "SD Level": 70, "RS Level": 50, "CP Level": 60, "CH Level": 50, "OH Level": 50, "RD Level": 40,
        "BD Tune": 50, "BD Sweep": 50, "BD Decay": 450, "BD Attack": 50, "BD Soft": 0, "BD Bits": 16,
        "SD Tune": 180, "SD Tone": 160, "SD Snappy": 60, "SD Bits": 16, "RS Bits": 16, "CP Bits": 16,
        "Hat Tune": 1, "Hat Bits": 6, "CH Decay": 60, "OH Decay": 500, "RD Tune": 1, "RD Bits": 6}

PAGE_NAMES = ["play", "bd sd rs", "cp hats rd"]
patch = kit.DevicePatchBuilder(device_name="2sl drums", script_name="2sl-drums", version=VERSION,
                               subtitle="909-style drum machine", page_names=PAGE_NAMES, info=INFO, base=BASE,
                               link_chip_text="2sl drums")
VIEW_Y, VIEW_H, ROW_Y, DIAL_Y, W = kit.VIEW_Y, kit.VIEW_H, kit.ROW_Y, kit.DIAL_Y, kit.DEVICE_WIDTH

# ---- the engine, the voices, the output ----------------------------------------------------------------------
midi_in = patch.box("midiin", rect=(30, 30, 50, 22), ins=1, outs=1, outtype=["int"])
midi_parse = patch.box("midiparse", rect=(30, 60, 90, 22), ins=1, outs=8)
brain = patch.box("js 2sl-drums.js", rect=(30, 120, 110, 22), ins=2, outs=5)
patch.wire(midi_in, midi_parse)
patch.wire(midi_parse, brain)
voices = patch.gen_box(dsp.KIT, 1, 2, rect=(30, 350, 160, 22))
patch.wire(brain, voices, 0, 0)
plugout = patch.box("plugout~", rect=(30, 470, 70, 22), ins=2, outs=2, outtype=["signal", "signal"])
patch.wire(voices, plugout, 0, 0)
patch.wire(voices, plugout, 1, 1)

header = patch.header(volume_target=voices, preset_x=360, preset_w=180)
patch.wire(header["ready"], brain, 0, 1)
patch.live_transport(header["thisdevice"], brain, 1)

# Stop: a new `panic` number fades the voices out; the brain clears the playhead
stop_order = patch.box("t b b", rect=(1100, 200, 40, 22), outs=2, outtype=["bang", "bang"])
stop_message = patch.box(cls="message", text="stop", rect=(1230, 230, 40, 22), ins=2, outs=1)
panic_counter = patch.box("counter 1 1000000", rect=(1100, 230, 110, 22), ins=3, outs=4, outtype=["int", "", "", "int"])
panic_message = patch.box("prepend panic", rect=(1100, 260, 90, 22))
patch.wire(header["stop"], stop_order)
patch.wire(stop_order, stop_message, 1, 0)
patch.wire(stop_message, brain, 0, 1)
patch.wire(stop_order, panic_counter, 0, 0)
patch.wire(panic_counter, panic_message)
patch.wire(panic_message, voices)

# ---- the stored pattern: two hidden values per voice (steps 1-8, 9-16; 2 bits a step), locks, mutes ------------
initial_kit = STYLES[BASE["Style"]]["kits"][0]["rows"]
store_route_names = []
for voice_id in VOICE_IDS:
    row = initial_kit.get(voice_id, REST)
    grades = [GRADE_CHARACTERS.index(c) for c in row]
    for half, name in ((0, "a"), (1, "b")):
        value = sum(grades[half * 8 + s] << (2 * s) for s in range(8))
        stored = patch.stored(f"steps_{voice_id}_{name}", value)
        patch.tell(stored, f"steps_{voice_id}_{name}", brain, 1)
        store_route_names.append((f"steps_{voice_id}_{name}", stored))
for flags_name in ("locks", "mutes"):
    stored = patch.stored(flags_name, 0)
    patch.tell(stored, flags_name, brain, 1)
    store_route_names.append((flags_name, stored))
store_route = patch.box("route " + " ".join(n for n, _ in store_route_names), rect=(1100, 120, 600, 22), ins=1,
                        outs=len(store_route_names) + 1)
patch.wire(brain, store_route, 4, 0)
for outlet_index, (_, stored) in enumerate(store_route_names):
    patch.wire(store_route, stored, outlet_index, 0)


# ---- layout ---------------------------------------------------------------------------------------------------
# 960 x 169 on a 4 px grid; sections keep the three bands (display, chips/menus, dials). The grid is the one
# display that takes two bands (display + chips): seven rows need its height.
DIAL_STEP = 56


def voice_dials(page, x, dials, view_box):
    """A voice section's dials, left to right; each also tells the section's display (same message)."""
    for index, (name, short, message, minimum, maximum, unit, exponent, scale) in enumerate(dials):
        patch.dial(name, short, voices, message, minimum, maximum, unit, x + index * DIAL_STEP, DIAL_Y, page,
                   exponent=exponent, scale=scale, views=[(view_box, message)])


# ================= PLAY: pattern | style | mix =================
P_GRID, P_GRID_W = 12, 384
P_STYLE, P_STYLE_W = 420, 172
P_MIX, P_MIX_W = 616, 332
v_grid = patch.view("grid", P_GRID, VIEW_Y, P_GRID_W, ROW_Y + kit.ROW_H - VIEW_Y, "play", info="Grid view")
patch.wire(brain, v_grid, 1, 0)
patch.wire(v_grid, brain, 0, 1)                 # clicks: edit, mute, lock, reroll
patch.dial("Variation", "Variation", brain, "variation", 0, 100, 5, P_GRID, DIAL_Y, "play", scale=0.01, inlet=1)
patch.dial("Density", "Density", brain, "density", 0, 100, 5, P_GRID + DIAL_STEP, DIAL_Y, "play", scale=0.01, inlet=1)
patch.dial("Accent", "Accent", voices, "accent", 0, 100, 5, P_GRID + 2 * DIAL_STEP, DIAL_Y, "play", scale=0.01)
swing_items = [f"{level + 1}: {percent:.0f}%" for level, percent in enumerate(SWING_PERCENT)]
swing_menu = patch.menu("Swing", "Swing", swing_items, P_GRID + 3 * DIAL_STEP + 4, DIAL_Y + 17, 88, "play")
patch.tell(swing_menu, "swing", brain, 1)
fill_menu = patch.menu("Fill", "Fill", ["off", "4 bars", "8 bars"], P_GRID + 3 * DIAL_STEP + 96, DIAL_Y + 17, 80, "play")
patch.tell(fill_menu, "fill", brain, 1)

v_style = patch.view("style", P_STYLE, VIEW_Y, P_STYLE_W, VIEW_H, "play", info="Style view")
patch.wire(brain, v_style, 2, 0)
style_menu = patch.menu("Style", "Style", STYLE_NAMES, P_STYLE, ROW_Y, P_STYLE_W, "play")
patch.tell(style_menu, "style", brain, 1)
generate_button = patch.toggle("Generate", "Generate", P_STYLE, DIAL_Y + 17, 84, 15, "play", mode=0)
canned_button = patch.toggle("Canned", "Canned", P_STYLE + 88, DIAL_Y + 17, 84, 15, "play", mode=0)
# a press goes straight to its message (as 2sl stab's buttons do)
for button, message in ((generate_button, "generate"), (canned_button, "canned")):
    button_message = patch.box(cls="message", text=message, rect=(1100, 300 + 2 * len(patch.boxes), 70, 22), ins=2, outs=1)
    patch.wire(button, button_message)
    patch.wire(button_message, brain, 0, 1)

v_mix = patch.view("mix", P_MIX, VIEW_Y, P_MIX_W, VIEW_H, "play", info="Mix view")
patch.wire(brain, v_mix, 3, 0)
MIX_DIAL_STEP = (P_MIX_W - kit.DIAL_WIDTH) // (len(VOICES) - 1)
for index, voice in enumerate(VOICES):
    patch.dial(f"{voice['name'].upper()} Level", voice["name"].upper(), voices, f"{voice['id']}_level", 0, 100, 5,
               P_MIX + index * MIX_DIAL_STEP, DIAL_Y, "play", scale=0.01, views=[(v_mix, f"{voice['id']}_level")])

# ================= BD SD RS =================
B_BD, B_BD_W = 12, 5 * DIAL_STEP + kit.DIAL_WIDTH
B_SD, B_SD_W = B_BD + B_BD_W + 24, 3 * DIAL_STEP + kit.DIAL_WIDTH
B_RS, B_RS_W = B_SD + B_SD_W + 24, W - 12 - (B_SD + B_SD_W + 24)
v_bd = patch.view("bd", B_BD, VIEW_Y, B_BD_W, VIEW_H, "bd sd rs", info="BD view")
voice_dials("bd sd rs", B_BD, [("BD Tune", "Tune", "bd_tune", 30, 90, 3, 1.0, 1.0),
                               ("BD Sweep", "Sweep", "bd_sweep", 0, 100, 5, 1.0, 0.01),
                               ("BD Decay", "Decay", "bd_decay", 60, 2000, 2, 2.0, 1.0),
                               ("BD Attack", "Attack", "bd_attack", 0, 100, 5, 1.0, 0.01),
                               ("BD Soft", "Soft", "bd_soft", 0, 100, 5, 1.0, 0.01),
                               ("BD Bits", "Bits", "bd_bits", 3, 16, 1, 1.0, 1.0)], v_bd)
v_sd = patch.view("sd", B_SD, VIEW_Y, B_SD_W, VIEW_H, "bd sd rs", info="SD view")
voice_dials("bd sd rs", B_SD, [("SD Tune", "Tune", "sd_tune", 120, 320, 3, 1.0, 1.0),
                               ("SD Tone", "Tone", "sd_tone", 40, 500, 2, 1.5, 1.0),
                               ("SD Snappy", "Snappy", "sd_snappy", 0, 100, 5, 1.0, 0.01),
                               ("SD Bits", "Bits", "sd_bits", 3, 16, 1, 1.0, 1.0)], v_sd)
v_rs = patch.view("rs", B_RS, VIEW_Y, B_RS_W, VIEW_H, "bd sd rs", info="RS view")
voice_dials("bd sd rs", B_RS, [("RS Bits", "Bits", "rs_bits", 3, 16, 1, 1.0, 1.0)], v_rs)

# ================= CP HATS RD =================
C_CP, C_CP_W = 12, 2 * DIAL_STEP + kit.DIAL_WIDTH
C_HAT, C_HAT_W = C_CP + C_CP_W + 24, 3 * DIAL_STEP + kit.DIAL_WIDTH + 112
C_RD, C_RD_W = C_HAT + C_HAT_W + 24, W - 12 - (C_HAT + C_HAT_W + 24)
v_cp = patch.view("cp", C_CP, VIEW_Y, C_CP_W, VIEW_H, "cp hats rd", info="CP view")
voice_dials("cp hats rd", C_CP, [("CP Bits", "Bits", "cp_bits", 3, 16, 1, 1.0, 1.0)], v_cp)
v_hats = patch.view("hats", C_HAT, VIEW_Y, C_HAT_W, VIEW_H, "cp hats rd", info="Hats view")
voice_dials("cp hats rd", C_HAT, [("Hat Tune", "Tune", "hat_tune", 0.43, 1.7, 1, 1.0, 1.0),
                                  ("CH Decay", "CH Decay", "ch_decay", 10, 300, 2, 1.5, 1.0),
                                  ("OH Decay", "OH Decay", "oh_decay", 80, 2000, 2, 2.0, 1.0),
                                  ("Hat Bits", "Bits", "hat_bits", 2, 12, 1, 1.0, 1.0)], v_hats)
v_rd = patch.view("rd", C_RD, VIEW_Y, C_RD_W, VIEW_H, "cp hats rd", info="RD view")
voice_dials("cp hats rd", C_RD, [("RD Tune", "Tune", "rd_tune", 0.6, 1.5, 1, 1.0, 1.0),
                                 ("RD Bits", "Bits", "rd_bits", 2, 12, 1, 1.0, 1.0)], v_rd)

# every voice display flashes on its own hits (the brain's mix outlet carries them all)
for voice_view in (v_bd, v_sd, v_rs, v_cp, v_hats, v_rd):
    patch.wire(brain, voice_view, 3, 0)

# the chrome: rules between sections, labels and hints (text, x, baseline, kind)
HEADER_LABELS = [["preset", 316, 15, "label"], ["out", 800, 15, "label"]]
LAYOUT = {
    "subtitle": 548,
    "pages": [
        {"rules": [P_STYLE - 12, P_MIX - 12],
         "labels": HEADER_LABELS + [["swing", P_GRID + 3 * DIAL_STEP + 4, DIAL_Y + 12, "label"],
                                    ["fill", P_GRID + 3 * DIAL_STEP + 96, DIAL_Y + 12, "label"],
                                    ["new kit", P_STYLE, DIAL_Y + 46, "hint"],
                                    ["source's", P_STYLE + 88, DIAL_Y + 46, "hint"],
                                    ["levels", P_MIX, ROW_Y + 12, "hint"]]},
        {"rules": [B_SD - 12, B_RS - 12],
         "labels": HEADER_LABELS + [["soft 0: 909 punch, 100: round, muffled", B_BD, ROW_Y + 12, "hint"],
                                    ["two vcos + snappy noise", B_SD, ROW_Y + 12, "hint"],
                                    ["level only on the 909", B_RS, ROW_Y + 12, "hint"]]},
        {"rules": [C_HAT - 12, C_RD - 12],
         "labels": HEADER_LABELS + [["level only on the 909", C_CP, ROW_Y + 12, "hint"],
                                    ["one voice: closed cuts open", C_HAT, ROW_Y + 12, "hint"],
                                    ["6-bit rom, no decay knob", C_RD, ROW_Y + 12, "hint"]]},
    ],
}

# ---- presets: style starting points (values in each control's own units, on top of BASE) ----------------------
# Volume: set from the offline render (tools/render_drums.py), so presets switch without jumping in level.
PRESETS = json.load(open(os.path.join(HERE, "2sl-drums-presets.json")))
PRESETS = [(entry["name"], entry["values"]) for entry in PRESETS]

# ---- scripts ----------------------------------------------------------------------------------------------------
brain_template = open(os.path.join(HERE, "2sl-drums-brain.template.js")).read()
clock_snippet = open(os.path.join(HERE, "2sl-kit-clock.template.js")).read()
brain_styles = [{k: style[k] for k in ("name", "kind", "tempo", "swing", "kits", "pool", "euclid") if k in style}
                for style in STYLES]
brain_js = patch.fill_template(brain_template, {
    "/*DEVICE_NAME*/": patch.device_name, "/*VOICES*/": json.dumps(VOICES), "/*STYLES*/": json.dumps(brain_styles),
    "/*GRIDS_NODES*/": json.dumps(GRIDS_NODES, separators=(",", ":")), "/*GRIDS_DRUM_MAP*/": json.dumps(GRIDS_DRUM_MAP),
    "/*GRADE_LEVELS*/": json.dumps(GRADE_LEVELS), "/*SWING_PERCENT*/": json.dumps(SWING_PERCENT),
    "/*INITIAL_STYLE*/": str(BASE["Style"]), "/*KIT_CLOCK*/": clock_snippet.strip()}, "the brain template")
VIEW_CODE = open(os.path.join(HERE, "2sl-drums-view.template.js")).read()
VIEW_CODE = VIEW_CODE.replace("/*VOICE_NAMES*/", json.dumps([v["name"] for v in VOICES]))

UI_HOOK = """
function deviceMessage(name, args) { return false; }    // 2sl drums' UI takes only the kit's messages
function devicePresetApplied(i) {}
"""

# for tools/render_drums.py: what each preset sends the voices and the brain (dist/ is a build output)
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
with open(os.path.join(ROOT, "dist", "2sl-drums-render.json"), "w") as handle:
    json.dump([{"name": name, "gen": patch.messages_for({**BASE, **values}, voices),
                "brain": patch.messages_for({**BASE, **values}, brain)} for name, values in PRESETS], handle, indent=1)

patch.finish(PRESETS, LAYOUT, VIEW_CODE, UI_HOOK,
             {os.path.join(DEVICE_DIRECTORY, "2sl-drums.js"): brain_js},
             ["2sl-drums.js", "2sl-drums-ui.js", "2sl-drums-view.js"])
