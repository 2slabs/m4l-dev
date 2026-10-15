#!/usr/bin/env python3
"""2sl drums: a 909-style drum machine instrument for Max for Live, built for trying patterns.

  python3 src/2sl-drums.py   # writes src/2sl-drums.maxpat, devices/2sl-drums/ (the .amxd and its scripts) and
                             # dist/2sl-drums-<version>.amxd (frozen: one file to share)

Needs references/drums/mirror/patterns/grids_resources.cc (run references/drums/mirror_patterns.sh): the Grids
pattern map is read from it at build time and embedded in the device's brain.

Signal flow:
  Live's transport (16th clock) -> js 2sl-drums.js (the pattern engine: the functions on Voice / Function / Seed,
  applied live, Undo and the history, playback with the 909's shuffle) -> gen~ (seven voices: BD SD RS CP CH/OH RD, and the mixer's mute / solo)
  -> plugout~. MIDI notes on the track also play the voices (GM drum notes).

The functions (generators and modifiers) are written once, in src/2sl-drums-functions.js: this script reads their
registry through Duktape (tools/es5check.py evaluate) and makes every function's Live parameters from it.
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
es5 = importlib.import_module("es5check")
try:
    # our GenExpr subset checker (tools/genexpr.py): syntax, scoping, names; not Max's compiler
    genexpr.check(dsp.KIT, num_inputs=0, num_outputs=2)
except genexpr.GenExprError as problem:
    raise kit.BuildError(f"2sl-drums.py: the gen~ voices (src/2sl_drums_dsp.py KIT): {problem}")


VERSION = "0.3.0"
DEVICE_DIRECTORY = os.path.join(ROOT, "devices", "2sl-drums")
FUNCTIONS_SOURCE = os.path.join(HERE, "2sl-drums-functions.js")
GRIDS_RESOURCES = os.path.join(ROOT, "references", "drums", "mirror", "patterns", "grids_resources.cc")
GRIDS_PATTERN_GENERATOR = os.path.join(ROOT, "references", "drums", "mirror", "patterns", "grids_pattern_generator.cc")
# the history Undo walks back through: the last 100 patterns (one pattern is 7 x 16 numbers)
HISTORY_LIMIT = 100

# ---- the voices ------------------------------------------------------------------------------------------
# notes: GM drum notes that play the voice from a clip. grids: which Grids channel (0 BD, 1 SD, 2 HH) the grids
# function takes the voice's row from, and what of it is kept (Grids has 3 channels; the clap and open hat rows
# from them are this device's choice, the README lists it).
VOICES = [
    {"id": "bd", "name": "bd", "notes": [36, 35], "grids": {"instrument": 0, "keep": "all"}},
    {"id": "sd", "name": "sd", "notes": [38, 40], "grids": {"instrument": 1, "keep": "all"}},
    {"id": "rs", "name": "rs", "notes": [37], "grids": None},
    {"id": "cp", "name": "cp", "notes": [39], "grids": {"instrument": 1, "keep": "accents"}},
    {"id": "ch", "name": "ch", "notes": [42, 44], "grids": {"instrument": 2, "keep": "all"}},
    {"id": "oh", "name": "oh", "notes": [46], "grids": {"instrument": 2, "keep": "offbeat eighths"}},
    {"id": "rd", "name": "rd", "notes": [51, 59], "grids": None},
]
VOICE_IDS = [v["id"] for v in VOICES]
if VOICE_IDS != dsp.VOICE_IDS:
    raise kit.BuildError(f"2sl-drums.py: the voices {VOICE_IDS} and the DSP's {dsp.VOICE_IDS} differ")

GRADE_CHARACTERS = ".oxX"
# the velocity each grade plays at: rest, ghost (patterns.md B5: ghost notes at 15-35 of 127, so 25/127), hit
# (0.7, unsourced), accent (1: the 909's accent, which Accent then scales in the voices)
GRADE_VELOCITY = [0, 0.2, 0.7, 1]
# the 909's shuffle 1-7 (patterns.md B4: 7 levels at the 16th scale, 1 = none). No source maps a level to a
# percent; this reads each level as 2 more 96-ppqn ticks of delay on every second 16th (unsourced, README).
SWING_PERCENT = [50 + (level * 2 / 24) * 50 for level in range(7)]

FOUR_ON_THE_FLOOR = "x...x...x...x..."
REST = "................"

# ---- the canned kits: patterns.md's grids, as their sources give them ------------------------------------------
# Placements marked `mine` follow the source's text where its grid is a screenshot (the README lists them).
CANNED_KITS = [
    {"name": "P1 basic channel", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "cp": "....x.......x...",
                                          "oh": "..x...x...x...x."}},
    {"name": "P8 4 ingredients", "rows": {"bd": FOUR_ON_THE_FLOOR, "oh": "..x...x...x...x."}},
    # P1's percussion: "a couple hits exactly on offbeat 16th notes" (placement mine)
    {"name": "P1 + rim 16ths", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "cp": "....x.......x...",
                                        "oh": "..x...x...x...x.", "rs": ".......x.......x"}},
    {"name": "P3 minimal house", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "cp": "....x.......x...",
                                          "ch": "..x...x...x...x.", "rs": "..x...x...x...x."}},
    {"name": "P7 house 124", "rows": {"bd": FOUR_ON_THE_FLOOR, "cp": "....x.......x...", "ch": "..x...x...x...x.",
                                      "oh": "......x.......x."}},
    # P4: "off-beat clap" (on 2 and 4 as P7), closed hat "shuffle on the 8th and 16th divisions" (placement mine)
    {"name": "P4 deep house", "rows": {"bd": FOUR_ON_THE_FLOOR, "cp": "....x.......x...", "oh": "..x...x...x...x.",
                                       "ch": ".x.x.x.x.x.x.x.x"}},
    # P2: snare and rim "work against each other", the rim "doesn't ever hit on the same beat as a kick" (mine)
    {"name": "P2 motor city", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x...", "rs": "...x..x....x..x.",
                                       "oh": "..x...x...x...x.", "ch": ".x.x.x.x.x.x.x.x"}},
    {"name": "P2 rim answer", "rows": {"bd": FOUR_ON_THE_FLOOR, "sd": "....x.......x..x", "rs": "..x....x..x....x",
                                       "oh": "..x...x...x...x.", "ch": "xxx.xxx.xxx.xxx."}},
    # P7 techno 130: hat on every 16th low, accents on the offbeats; ride 8ths; rim on 2 and 4
    {"name": "P7 techno 130", "rows": {"bd": FOUR_ON_THE_FLOOR, "ch": "xxXxxxXxxxXxxxXx", "rd": "x.x.x.x.x.x.x.x.",
                                       "rs": "....x.......x..."}},
    # P9: offbeat open hat, the ride on the same notes
    {"name": "P9 mills 137", "rows": {"bd": FOUR_ON_THE_FLOOR, "oh": "..x...x...x...x.", "rd": "..x...x...x...x."}},
    # P5: ride 8ths "with a shorter, quieter note on every second hit"; closed hat around the offbeat
    {"name": "P5 dark rumble", "rows": {"bd": FOUR_ON_THE_FLOOR, "rd": "X.x.X.x.X.x.X.x.", "ch": "..x...x...x...x."}},
    # P6: ghost kicks just before beats 2 and 4 (approx), offbeat open hat
    {"name": "P6 rolling", "rows": {"bd": "x..ox...x..ox...", "oh": "..x...x...x...x."}},
    # P11: Toussaint's rhythms on the rim and clap over a four-on-the-floor kick
    {"name": "P11 tresillo", "rows": {"bd": FOUR_ON_THE_FLOOR, "rs": "x..x..x.x..x..x.", "ch": "..x...x...x...x."}},
    {"name": "P11 bossa", "rows": {"bd": FOUR_ON_THE_FLOOR, "rs": "x..x..x...x..x..", "oh": "..x...x...x...x."}},
    {"name": "P11 son clave", "rows": {"bd": FOUR_ON_THE_FLOOR, "cp": "x..x..x...x.x...", "ch": "x.xx.xx.x.xx.xx."}},
]
for canned_kit in CANNED_KITS:
    for voice_id, row in canned_kit["rows"].items():
        if voice_id not in VOICE_IDS:
            raise kit.BuildError(f"2sl-drums.py: canned kit {canned_kit['name']}: no voice {voice_id!r}")
        if len(row) != 16 or set(row) - set(GRADE_CHARACTERS):
            raise kit.BuildError(f"2sl-drums.py: canned kit {canned_kit['name']} / {voice_id}: row {row!r} must be "
                                 f"16 of {GRADE_CHARACTERS!r}")
# the Init pattern: the first canned kit (P1, Basic Channel-style dub techno)
INITIAL_PATTERN = [CANNED_KITS[0]["rows"].get(voice_id, REST) for voice_id in VOICE_IDS]


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

# ---- the functions: their registry, read from the script that runs them ---------------------------------------
FUNCTIONS_CODE = open(FUNCTIONS_SOURCE, encoding="utf-8").read()


def read_function_registry():
    """FUNCTIONS' entries without their code: [{name, kind, info, params: [{name, min, max, initial, unit, info}],
    order, variants (how many Seed walks), initial_seed (Seed for the initial settings)}]. Evaluated as ES5
    (Duktape) with the data the registry refers to; the script checks itself."""
    prefix = (f"var DEVICE_NAME = {json.dumps('2sl drums')}; var VOICES = {json.dumps(VOICES)}; "
              f"var CANNED_KITS = {json.dumps(CANNED_KITS)}; var GRIDS_NODES = []; var GRIDS_DRUM_MAP = [];\n")
    extract = ("\nJSON.stringify(FUNCTIONS.map(function (f) { return { name: f.name, kind: f.kind, info: f.info, "
               "params: f.params, order: f.order, variants: variantCount(f), initial_seed: seedOfPosition(f, "
               "variantPosition(f, f.params.map(function (p) { return p.initial; }))) }; }))")
    try:
        return json.loads(es5.evaluate(prefix + FUNCTIONS_CODE + extract))
    except es5.EvaluationError as problem:
        raise kit.BuildError(f"2sl-drums.py: src/2sl-drums-functions.js doesn't evaluate as ES5: {problem}")


FUNCTION_REGISTRY = read_function_registry()
FUNCTION_NAMES = [entry["name"] for entry in FUNCTION_REGISTRY]
UNIT_STYLES = {"int": 0, "%": 5}               # Live's parameter_unitstyle: Int, Percent
VOICE_CHOICES = [v["name"] for v in VOICES] + ["all"]     # Voice: one row, or all (the last)
INITIAL_VOICE = len(VOICES)                      # all
INITIAL_FUNCTION = 0


def function_parameter_name(entry, param):
    """The Live parameter of a function's setting: "Euclid Hits"."""
    return f"{entry['name'][0].upper()}{entry['name'][1:]} {param['name'].capitalize()}"


# ---- what Live's Info View shows -----------------------------------------------------------------------------
INFO = {
    # views
    "Link view": ("2sl.to", "Opens 2sl.to in your browser."),
    "Grid view": ("Pattern", "The pattern: a row per voice, 16 steps. Click a step: rest, hit, accent (bright, with a "
                  "bar on top); shift-click: a ghost (dim). The lit names are the rows Voice picks; click a name to pick "
                  "that row (Voice moves; the row it already picks: all). Blue outline: the step playing. While "
                  "Seed or a setting is being turned, this is the live result."),
    "Status view": ("Status", "Line 1: Voice, Function and where Seed is in the function's variants. Line 2: the "
                    "function's settings. Line 3: what is shown (the base, or live), or a warning in blue (open hh "
                    "on a row other than oh, a row grids has nothing for). Line 4: where you are in the history "
                    "(Undo steps back) and what made the pattern."),
    "Mix view": ("Mix", "Each voice's level as a bar, flashing as it plays; dimmed when it doesn't sound (muted, or "
                 "another voice is soloed)."),
    "BD view": ("BD", "The kick's level (mint) and pitch (grey) over its decay, as the voice makes them. Top right: "
                "the pitch it settles to and the decay."),
    "SD view": ("SD", "The snare's drum (mint) and snappy noise (grey) envelopes. Top right: VCO 1's pitch."),
    "RS view": ("RS", "The rim shot's envelope: three rings at 500, 220 and 1000 Hz, clipped, short."),
    "CP view": ("CP", "The clap's envelope: four claps 11 ms apart, then the softer tail."),
    "Hats view": ("Hats", "Closed (mint) and open (grey) hat envelopes. They are one voice, as on the 909: a closed "
                  "hit cuts an open one. Top right: the ROM clock and bits."),
    "RD view": ("RD", "The ride's envelope; its length follows Tune, as the 909's ROM clock does."),
    # header
    "Page": ("Page", "Shows the pattern or the kit page. Controls on the hidden page keep working."),
    "Preset": ("Preset", "Kit sounds: sets every voice, level and Accent (not the pattern, the mixer's mutes and "
               "solos, or the functions). When Live reopens a set, your saved tweaks win."),
    "Volume": ("Volume", "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs."),
    "Stop": ("Stop", "Panic: fades every voice out in 20 ms. Live's transport stopping doesn't run it."),
    # pattern
    "Voice": ("Voice", "The row the function changes: " + ", ".join(v["name"] for v in VOICES) + ", or all (the "
              "last). On all, generators make the whole kit and modifiers change every row. Moving Voice commits "
              "what is shown as one history step."),
    "Function": ("Function", "The function Seed and the settings walk, applied live. Generators make new rows: " +
                 ", ".join(e["name"] for e in FUNCTION_REGISTRY if e["kind"] == "generator") + ". Modifiers change "
                 "the rows there are: " + ", ".join(e["name"] for e in FUNCTION_REGISTRY if e["kind"] == "modifier") +
                 ". Only its own settings show; each remembers its own. Moving Function commits what is shown as one "
                 "history step."),
    "Seed": ("Seed", "Walks every combination of the function's settings (its variants), the finest setting changing "
             "fastest, neighbours one step apart; turning it moves the settings, turning a setting moves it. Shown at "
             "once: the first turn after a commit takes the pattern as it is as the base; Undo brings the base back. "
             "0-100% of the way through this function's variants (the status line shows which)."),
    "Clear": ("Clear", "Clears the row Voice picks (every row, on all): all rests. Commits what is being turned "
              "first; the clear is one history step (Undo brings the row back). A clear that changes nothing is no step."),
    "Undo": ("Undo", f"Drops what Seed and the settings show that isn't committed (back to the base, the settings "
             f"back where they were). Else steps back one commit (a Voice or Function move, or a hand edit). The last "
             f"{HISTORY_LIMIT} patterns are kept; the history isn't saved with the set (the pattern playing is)."),
    "Swing": ("Swing", "The 909's shuffle, 1 (none) to 7: every second 16th later, 50% to 75% of the 8th. "
              "Sample-accurate in the voices."),
    # kit
    "Kit Voice": ("Kit Voice", "Which voice's sound controls show: bd, sd, rs, cp, the hats (ch and oh) or rd."),
    "Accent": ("Accent", "How much quieter a normal hit (and a ghost) is than an accent, like the 909's Total Accent. "
               "0 = all the same. Default 70%."),
}
for entry in FUNCTION_REGISTRY:
    for param in entry["params"]:
        name = function_parameter_name(entry, param)
        INFO[name] = (name, f"{entry['name'].capitalize()}: {entry['info']} {param['name'].capitalize()}: {param['info']}")
for voice in VOICES:
    upper = voice["name"].upper()
    INFO[f"{upper} Level"] = (f"{upper} Level", f"Level of the {voice['name']} in the mix. Accents still play louder (Accent).")
    INFO[f"{upper} Mute"] = (f"{upper} Mute", f"Mutes the {voice['name']}: its pattern keeps running, it doesn't sound "
                             "(MIDI notes neither). Saved with the set, not in presets.")
    INFO[f"{upper} Solo"] = (f"{upper} Solo", f"Solo: while any voice is soloed, only soloed voices sound (a mute still "
                             "wins). Saved with the set, not in presets.")
INFO.update({
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
    "RS Bits": ("RS Bits", "Bit reduction on the rim shot, 16 (clean) down to 3. Level only on the 909."),
    "CP Bits": ("CP Bits", "Bit reduction on the clap, 16 (clean) down to 3. Attack's dub techno clap uses 6. "
                "Level only on the 909."),
    "Hat Tune": ("Hat Tune", "The hat ROM's clock, x0.43 to x1.7 (Whittle's tune mod range): pitch and grit."),
    "Hat Bits": ("Hat Bits", "The hat ROM's bit depth: 6 on the 909 (default). Lower is grittier."),
    "CH Decay": ("CH Decay", "Closed hat decay to -40 dB, 10-300 ms (default 60)."),
    "OH Decay": ("OH Decay", "Open hat decay to -40 dB, 80 ms to 2 s (default 500). A closed hit cuts it."),
    "RD Tune": ("RD Tune", "The ride ROM's clock, x0.6 to x1.5: pitch and length together, as on the 909 (no decay knob)."),
    "RD Bits": ("RD Bits", "The ride ROM's bit depth: 6 on the 909 (default)."),
})

# ---- BASE: the Init preset, every kit-sound control's initial value ---------------------------------------------
# (the pattern tools, Swing, the mixer's mutes and solos and the Voice buttons are saved with the set but not in
# presets: they have their own initial values)
BASE = {"Accent": 70, "Volume": 0,
        "BD Level": 80, "SD Level": 70, "RS Level": 50, "CP Level": 60, "CH Level": 50, "OH Level": 50, "RD Level": 40,
        "BD Tune": 50, "BD Sweep": 50, "BD Decay": 450, "BD Attack": 50, "BD Soft": 0, "BD Bits": 16,
        "SD Tune": 180, "SD Tone": 160, "SD Snappy": 60, "SD Bits": 16, "RS Bits": 16, "CP Bits": 16,
        "Hat Tune": 1, "Hat Bits": 6, "CH Decay": 60, "OH Decay": 500, "RD Tune": 1, "RD Bits": 6}

# ---- layout: 169 px high on a 4 px grid, as wide as the widest page (and the header) needs --------------------
PAGE_NAMES = ["pattern", "kit"]
DIAL_STEP = 56
SETTINGS_SHOWN = 3                              # setting dials a function can show (one row of them)
STEP_W, LABEL_W = 16, 24                        # the grid: a 16 px column per step after the voice names
P_GRID, P_GRID_W = 12, LABEL_W + 16 * STEP_W + 2
P_KNOBS = P_GRID + P_GRID_W + 20                # Voice, Function, Seed; then the function's settings
# Function: a button per function (a live.tab, one enum parameter, so a MIDI knob sweeps it), in two rows, between
# the Voice and Seed dials; a button is as wide as the longest name needs (the kit's live.tab rule)
FUNCTION_ROWS = 2
FUNCTION_BUTTON_W = 6 * max(len(entry["name"]) for entry in FUNCTION_REGISTRY) + 12
FUNCTION_TABS_X = P_KNOBS + DIAL_STEP
FUNCTION_TABS_W = FUNCTION_BUTTON_W * -(-len(FUNCTION_REGISTRY) // FUNCTION_ROWS)
FUNCTION_TABS_Y = kit.DIAL_Y + (kit.DIAL_HEIGHT - FUNCTION_ROWS * kit.ROW_H) // 2
P_SEED = FUNCTION_TABS_X + FUNCTION_TABS_W + 12
P_SETTINGS = P_SEED + DIAL_STEP + 12
PATTERN_PAGE_W = P_SETTINGS + (SETTINGS_SHOWN - 1) * DIAL_STEP + kit.DIAL_WIDTH + 12
for entry in FUNCTION_REGISTRY:
    if len(entry["params"]) > SETTINGS_SHOWN:
        raise kit.BuildError(f"2sl-drums.py: {entry['name']} has {len(entry['params'])} settings; the pattern page "
                             f"shows {SETTINGS_SHOWN}")
    for param in entry["params"]:
        if 6 * len(param["name"]) > kit.DIAL_WIDTH + 8:
            raise kit.BuildError(f"2sl-drums.py: {entry['name']}'s setting name {param['name']!r} is too long for a dial")
# the kit page: a voice's sound (room for the BD's six dials) | the mixer | Accent
K_VOICE, K_VOICE_W = 12, 5 * DIAL_STEP + kit.DIAL_WIDTH
K_MIX = K_VOICE + K_VOICE_W + 24
STRIP_W = 48
K_MIX_W = (len(VOICES) - 1) * STRIP_W + kit.DIAL_WIDTH
K_ACCENT = K_MIX + K_MIX_W + 24
KIT_PAGE_W = K_ACCENT + kit.DIAL_WIDTH + 12
# the header: the subtitle (drawn by the chrome, from x 420) must end before "out", 160 px from the right edge
SUBTITLE = "909-style drum machine"
SUBTITLE_X = 420
HEADER_W = SUBTITLE_X + 6 * len(f"{SUBTITLE}  v{VERSION}") + 12 + 160
W = max(PATTERN_PAGE_W, KIT_PAGE_W, HEADER_W)
W += (-W) % 4

patch = kit.DevicePatchBuilder(device_name="2sl drums", script_name="2sl-drums", version=VERSION,
                               subtitle=SUBTITLE, page_names=PAGE_NAMES, info=INFO, base=BASE,
                               link_chip_text="2sl drums", device_width=W)
VIEW_Y, VIEW_H, ROW_Y, DIAL_Y = kit.VIEW_Y, kit.VIEW_H, kit.ROW_Y, kit.DIAL_Y

# ---- the engine, the voices, the output ----------------------------------------------------------------------
midi_in = patch.box("midiin", rect=(30, 30, 50, 22), ins=1, outs=1, outtype=["int"])
midi_parse = patch.box("midiparse", rect=(30, 60, 90, 22), ins=1, outs=8)
brain = patch.box("js 2sl-drums.js", rect=(30, 120, 110, 22), ins=2, outs=6)
patch.wire(midi_in, midi_parse)
patch.wire(midi_parse, brain)
voices = patch.gen_box(dsp.KIT, 1, 2, rect=(30, 350, 160, 22))
patch.wire(brain, voices, 0, 0)
plugout = patch.box("plugout~", rect=(30, 470, 70, 22), ins=2, outs=2, outtype=["signal", "signal"])
patch.wire(voices, plugout, 0, 0)
patch.wire(voices, plugout, 1, 1)

header = patch.header(volume_target=voices, preset_x=244, preset_w=160)
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

# ---- stored with the set: two hidden values per voice (steps 1-8, 9-16; 2 bits a step) ---------------------------
store_route_names = []
for voice_id, row in zip(VOICE_IDS, INITIAL_PATTERN):
    grades = [GRADE_CHARACTERS.index(c) for c in row]
    for half, name in ((0, "a"), (1, "b")):
        value = sum(grades[half * 8 + s] << (2 * s) for s in range(8))
        stored = patch.stored(f"steps_{voice_id}_{name}", value)
        patch.tell(stored, f"steps_{voice_id}_{name}", brain, 1)
        store_route_names.append((f"steps_{voice_id}_{name}", stored))
store_route = patch.box("route " + " ".join(n for n, _ in store_route_names), rect=(1100, 120, 600, 22), ins=1,
                        outs=len(store_route_names) + 1)
patch.wire(brain, store_route, 4, 0)
for outlet_index, (_, stored) in enumerate(store_route_names):
    patch.wire(store_route, stored, outlet_index, 0)

# ================= PATTERN: the grid | the status line, Undo, Swing; Voice, Function, Seed, the settings ============
v_grid = patch.view("grid", P_GRID, VIEW_Y, P_GRID_W, kit.DEVICE_HEIGHT - 4 - VIEW_Y, "pattern", info="Grid view")
patch.wire(brain, v_grid, 1, 0)
patch.wire(v_grid, brain, 0, 1)                 # clicks: edit, name_click
v_status = patch.view("status", P_KNOBS, VIEW_Y, W - 12 - P_KNOBS, VIEW_H, "pattern", info="Status view")
patch.wire(brain, v_status, 2, 0)


voice_dial = patch.dial("Voice", "Voice", brain, "voice", 0, 0, 0, P_KNOBS, DIAL_Y, "pattern", items=VOICE_CHOICES, inlet=1,
           initial_outside_presets=INITIAL_VOICE)
function_tabs = patch.tabs("Function", "Function", FUNCTION_NAMES, FUNCTION_TABS_X, FUNCTION_TABS_Y, FUNCTION_TABS_W,
                           "pattern", initial_outside_presets=INITIAL_FUNCTION, rows=FUNCTION_ROWS)
patch.tell(function_tabs, "function", brain, 1)
patch.groups_selected_by(function_tabs, len(FUNCTION_REGISTRY), "pattern")
# Seed: a float, 0-100% of the way through the active function's variants (Live's Int type holds 256 values; the
# functions have up to millions, and one parameter serves every function: the brain scales it)
seed_dial = patch.dial("Seed", "Seed", brain, "seed", 0, 100, UNIT_STYLES["%"], P_SEED, DIAL_Y,
                       "pattern", inlet=1,
                       initial_outside_presets=FUNCTION_REGISTRY[INITIAL_FUNCTION]["initial_seed"])
# the brain sets Seed and the settings (outlet 5: `<scripting name> value`); each echoes back, which it ignores
parameter_targets = [(kit.varname_for("Voice"), voice_dial), (kit.varname_for("Seed"), seed_dial)]
setting_parameters = []
for function_index, entry in enumerate(FUNCTION_REGISTRY):
    varnames = []
    for param_index, param in enumerate(entry["params"]):
        name = function_parameter_name(entry, param)
        setting_dial = patch.dial(name, param["name"].capitalize(), brain, f"param {function_index} {param_index}",
                                  param["min"], param["max"], UNIT_STYLES[param["unit"]],
                                  P_SETTINGS + param_index * DIAL_STEP, DIAL_Y, "pattern",
                                  integer=param["max"] - param["min"] <= 255, inlet=1,
                                  initial_outside_presets=param["initial"], group=("function", function_index))
        varnames.append(kit.varname_for(name))
        parameter_targets.append((kit.varname_for(name), setting_dial))
    setting_parameters.append(varnames)
parameter_route = patch.box("route " + " ".join(n for n, _ in parameter_targets), rect=(1100, 160, 900, 22), ins=1,
                            outs=len(parameter_targets) + 1)
patch.wire(brain, parameter_route, 5, 0)
for outlet_index, (_, target_dial) in enumerate(parameter_targets):
    patch.wire(parameter_route, target_dial, outlet_index, 0)

# Undo and Clear: a press goes straight to its message (as 2sl stab's buttons do)
for button_index, (button_name, message) in enumerate((("Undo", "undo"), ("Clear", "clear"))):
    button = patch.toggle(button_name, button_name, P_KNOBS + button_index * DIAL_STEP, ROW_Y, 48, 15, "pattern", mode=0)
    button_message = patch.box(cls="message", text=message, rect=(1100, 300 + 30 * button_index, 70, 22), ins=2, outs=1)
    patch.wire(button, button_message)
    patch.wire(button_message, brain, 0, 1)
SWING_W = 72
swing_x = W - 12 - SWING_W
swing_items = [f"{level + 1}: {percent:.0f}%" for level, percent in enumerate(SWING_PERCENT)]
swing_menu = patch.menu("Swing", "Swing", swing_items, swing_x, ROW_Y, SWING_W, "pattern",
                        initial_outside_presets=0)
patch.tell(swing_menu, "swing", brain, 1)

# ================= KIT: a voice's sound (picked by Voice) | the mixer =================
VOICE_SECTIONS = [  # (Voice button, display mode, Info key, dials: (name, short, message, min, max, unit, exponent, scale))
    ("bd", "bd", "BD view", [("BD Tune", "Tune", "bd_tune", 30, 90, 3, 1.0, 1.0),
                             ("BD Sweep", "Sweep", "bd_sweep", 0, 100, 5, 1.0, 0.01),
                             ("BD Decay", "Decay", "bd_decay", 60, 2000, 2, 2.0, 1.0),
                             ("BD Attack", "Attack", "bd_attack", 0, 100, 5, 1.0, 0.01),
                             ("BD Soft", "Soft", "bd_soft", 0, 100, 5, 1.0, 0.01),
                             ("BD Bits", "Bits", "bd_bits", 3, 16, 1, 1.0, 1.0)]),
    ("sd", "sd", "SD view", [("SD Tune", "Tune", "sd_tune", 120, 320, 3, 1.0, 1.0),
                             ("SD Tone", "Tone", "sd_tone", 40, 500, 2, 1.5, 1.0),
                             ("SD Snappy", "Snappy", "sd_snappy", 0, 100, 5, 1.0, 0.01),
                             ("SD Bits", "Bits", "sd_bits", 3, 16, 1, 1.0, 1.0)]),
    ("rs", "rs", "RS view", [("RS Bits", "Bits", "rs_bits", 3, 16, 1, 1.0, 1.0)]),
    ("cp", "cp", "CP view", [("CP Bits", "Bits", "cp_bits", 3, 16, 1, 1.0, 1.0)]),
    ("hats", "hats", "Hats view", [("Hat Tune", "Tune", "hat_tune", 0.43, 1.7, 1, 1.0, 1.0),
                                   ("CH Decay", "CH Decay", "ch_decay", 10, 300, 2, 1.5, 1.0),
                                   ("OH Decay", "OH Decay", "oh_decay", 80, 2000, 2, 2.0, 1.0),
                                   ("Hat Bits", "Bits", "hat_bits", 2, 12, 1, 1.0, 1.0)]),
    ("rd", "rd", "RD view", [("RD Tune", "Tune", "rd_tune", 0.6, 1.5, 1, 1.0, 1.0),
                             ("RD Bits", "Bits", "rd_bits", 2, 12, 1, 1.0, 1.0)]),
]
# the voices each section's display flashes for (the hats section is CH and OH, one voice on the 909)
VOICES_OF_SECTION = {mode: (["ch", "oh"] if mode == "hats" else [mode]) for _, mode, _, _ in VOICE_SECTIONS}
voice_selector = patch.group_selector("Kit Voice", "Voice", [section[0] for section in VOICE_SECTIONS], K_VOICE, ROW_Y,
                                      K_VOICE_W, "kit")
voice_views = []
for group_index, (button, mode, info_key, dials) in enumerate(VOICE_SECTIONS):
    group = ("kit_voice", group_index)
    voice_view = patch.view(mode, K_VOICE, VIEW_Y, K_VOICE_W, VIEW_H, "kit", info=info_key, group=group)
    voice_views.append(voice_view)
    for index, (name, short, message, minimum, maximum, unit, exponent, scale) in enumerate(dials):
        patch.dial(name, short, voices, message, minimum, maximum, unit, K_VOICE + index * DIAL_STEP, DIAL_Y, "kit",
                   exponent=exponent, scale=scale, views=[(voice_view, message)], group=group)

v_mix = patch.view("mix", K_MIX, VIEW_Y, K_MIX_W, VIEW_H, "kit", info="Mix view")
for index, voice in enumerate(VOICES):
    x, upper = K_MIX + index * STRIP_W, voice["name"].upper()
    patch.dial(f"{upper} Level", upper, voices, f"{voice['id']}_level", 0, 100, 5, x, DIAL_Y, "kit", scale=0.01,
               views=[(v_mix, f"{voice['id']}_level")])
    for chip_x, kind in ((x, "Mute"), (x + 24, "Solo")):
        chip = patch.toggle(f"{upper} {kind}", kind[0], chip_x, ROW_Y, 20, 15, "kit", initial_outside_presets=0)
        patch.tell(chip, f"{voice['id']}_{kind.lower()}", voices)
        patch.tell(chip, f"{voice['id']}_{kind.lower()}", v_mix)
patch.dial("Accent", "Accent", voices, "accent", 0, 100, 5, K_ACCENT, DIAL_Y, "kit", scale=0.01)

# every voice display and the mixer flash on hits (the brain's outlet 3 carries them all)
for flashing_view in voice_views + [v_mix]:
    patch.wire(brain, flashing_view, 3, 0)

# the chrome: rules between sections, labels and hints (text, x, baseline, kind)
HEADER_LABELS = [["preset", patch.header_preset_x - 40, 15, "label"], ["out", patch.header_volume_x - 24, 15, "label"]]
LAYOUT = {
    "subtitle": SUBTITLE_X,
    "pages": [
        {"rules": [P_KNOBS - 10, P_SETTINGS - 6],
         "labels": HEADER_LABELS + [["swing", swing_x - 36, ROW_Y + 12, "label"],
                                    ["function", FUNCTION_TABS_X, FUNCTION_TABS_Y - 3, "label"]]},
        {"rules": [K_MIX - 12, K_ACCENT - 12],
         "labels": HEADER_LABELS},
    ],
}

# ---- presets: kit sounds (values in each control's own units, on top of BASE) --------------------------------------
# Volume: set from the offline render (tools/render_drums.py), so presets switch without jumping in level.
PRESETS = json.load(open(os.path.join(HERE, "2sl-drums-presets.json")))
PRESETS = [(entry["name"], entry["values"]) for entry in PRESETS]

# ---- scripts ----------------------------------------------------------------------------------------------------
brain_template = open(os.path.join(HERE, "2sl-drums-brain.template.js")).read()
clock_snippet = open(os.path.join(HERE, "2sl-kit-clock.template.js")).read()
brain_js = patch.fill_template(brain_template, {
    "/*DEVICE_NAME*/": patch.device_name, "/*VOICES*/": json.dumps(VOICES), "/*CANNED_KITS*/": json.dumps(CANNED_KITS),
    "/*GRIDS_NODES*/": json.dumps(GRIDS_NODES, separators=(",", ":")), "/*GRIDS_DRUM_MAP*/": json.dumps(GRIDS_DRUM_MAP),
    "/*SWING_PERCENT*/": json.dumps(SWING_PERCENT), "/*GRADE_VELOCITY*/": json.dumps(GRADE_VELOCITY),
    "/*INITIAL_PATTERN*/": json.dumps(INITIAL_PATTERN), "/*HISTORY_LIMIT*/": str(HISTORY_LIMIT),
    "/*INITIAL_VOICE*/": str(INITIAL_VOICE), "/*INITIAL_FUNCTION*/": str(INITIAL_FUNCTION),
    "/*VOICE_PARAMETER*/": json.dumps(kit.varname_for("Voice")), "/*SEED_PARAMETER*/": json.dumps(kit.varname_for("Seed")), "/*SETTING_PARAMETERS*/": json.dumps(setting_parameters),
    "/*FUNCTIONS*/": FUNCTIONS_CODE.strip(), "/*KIT_CLOCK*/": clock_snippet.strip()}, "the brain template")
VIEW_CODE = open(os.path.join(HERE, "2sl-drums-view.template.js")).read()
VIEW_CODE = patch.fill_template(VIEW_CODE, {"/*VOICE_NAMES*/": json.dumps([v["name"] for v in VOICES]),
                                            "/*VOICE_IDS*/": json.dumps(VOICE_IDS), "/*MIX_STRIP_W*/": str(STRIP_W),
                                            "/*VOICE_OF_MODE*/": json.dumps({mode: [VOICE_IDS.index(i) for i in ids]
                                                                             for mode, ids in VOICES_OF_SECTION.items()})},
                                 "the view template")

# for tools/render_drums.py: what each preset sends the voices (dist/ is a build output)
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
with open(os.path.join(ROOT, "dist", "2sl-drums-render.json"), "w") as handle:
    json.dump([{"name": name, "gen": patch.messages_for({**BASE, **values}, voices)} for name, values in PRESETS],
              handle, indent=1)

patch.finish(PRESETS, LAYOUT, VIEW_CODE,
             {os.path.join(DEVICE_DIRECTORY, "2sl-drums.js"): brain_js},
             ["2sl-drums.js", "2sl-drums-ui.js", "2sl-drums-view.js"])
