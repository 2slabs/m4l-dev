"""A small device built with the kit into a temporary device repository: the tests' fixture.

It has one of everything the kit makes (a gen~ with Params, a dial with a display, a toggle, a menu, tabs, a Stored
Only value, a button, the seeded random's Seed and Loop, the chord block with its display, a stored table with an
editor of each kind) and ships its two presets as Live preset files, so a build of it exercises every step of
build_device. `build_fixture_device(root)` builds it into `root` (made if needed) and returns the DeviceRepository.
"""
import json
import os
import sys

KIT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KIT_DIRECTORY not in sys.path:
    sys.path.insert(0, KIT_DIRECTORY)

from twosl_dsp import layout_rules  # noqa: E402
from twosl_dsp.chord_block import ChordBlock  # noqa: E402
from twosl_dsp.generated_scripts import fill_template  # noqa: E402
from twosl_dsp.device_build import build_device  # noqa: E402
from twosl_dsp.device_repository import DeviceRepository  # noqa: E402
from twosl_dsp.live_preset_files import LivePresetFiles  # noqa: E402
from twosl_dsp.patch_builder import DevicePatchBuilder  # noqa: E402
from twosl_dsp.preset_book import PresetBook  # noqa: E402
from twosl_dsp.seeded_random import SeededRandom  # noqa: E402
from twosl_dsp.stored_table import ChoiceField, ContinuousField, StoredTable, stored_tables_brain_code  # noqa: E402

FIXTURE_SCRIPT_NAME = "kit-fixture"
FIXTURE_PRESET_BOOK = {
    "neutral": {"Level": 0, "Bright": "off", "Shape": "round", "Mode": "a",
                "Stage": {"Pitch": 0, "Pulse": "off", "Wait": "go"}},
    "init": {"Level": 50, "Bright": "off", "Shape": "round", "Mode": "a", "Volume": 0, "Chord": "minor", "In key": "on",
             "Seed": 0, "Loop": "16 bars",
             "Stage": {"Pitch": [0, 7], "Pulse": ["off", "on"], "Wait": ["go", "keyed"]}},
    "presets": [
        {"name": "init", "group": "init", "idea": "the Init values", "values": {}},
        {"name": "loud", "group": "test", "idea": "louder, square", "values": {"Level": 90, "Shape": "square",
                                                                               "Bright": "on",
                                                                               "Stage": {"Pitch": [12, -24]}}},
    ],
}
FIXTURE_GEN_CODE = """
Param level(min=0, max=1);
Param volume(min=-36, max=12);
Param panic(0);
out1 = in1 * level * dbtoa(volume);
"""
FIXTURE_INFO = {name: (name, f"{name}: what it does.") for name in
                ("Link view", "Page", "Volume", "Stop", "Level", "Bright", "Shape", "Mode", "Kick", "Level view",
                 "Chord", "In key", "Chord view", "Stage Pitch edit 1", "Stage Pitch edit 2", "Stage Pulse edit 1",
                 "Stage Wait edit 2")}
FIXTURE_VIEWS_CODE = fill_template("""
var DEVICE_STATE = { kicks: 0 };
var ANIMATED_MODES = [];
/*CHORD_DISPLAY*/
function deviceMessage(m, a) {
  if (chordDisplayMessage(m, a)) return true;
  if (m === "kick") { S.kicks++; return true; }
  return false;
}
var VIEW_PAINTERS = { level: function (w, h) { rect(4, viewHeading("level", "", w) + 2, (w - 8) * S.level, 4, T.mint); },
                      chord: function (w, h) { chordDisplayView(w, h, "chord"); } };
var VIEW_CLICKS = {};
// the level display is dragged: its height sets the level, told out while held
var VIEW_DRAGS = { level: function (x, y, held) { if (held) outlet(0, "level", 1 - y / mgraphics.size[1]); } };
""", {"CHORD_DISPLAY": ChordBlock.display_code()}, "the fixture's views code")
# the fixture's brain: the kit's seeded random and chord block, a key playing its chord, the rest ignored
FIXTURE_BRAIN_TEMPLATE = """var DEVICE_NAME = "kit fixture";
inlets = 2;
outlets = 3;
/*SEEDED_RANDOM*/
/*CHORD_BLOCK*/
/*STORED_TABLES*/
var stageChanges = [];
storedTableListen("Stage", function (field, row, value) { stageChanges.push([field, row, value]); });
function list(key, velocity) {
  if (velocity > 0) { chordKeyDown(key, velocity); chordShow(chordDrifted(chordOnKey(key), 0)); }
  else if (chordKeyUp(key)) chordShow([]);
}
function anything() {
  var a = arrayfromargs(arguments);
  if (seededRandomMessage(messagename, a) || chordBlockMessage(messagename, a) || storedTableMessage(messagename, a)) return;
  if (messagename === "ready") storedTableReady();
  else if (messagename === "playing") seededRandomTransport(a[0]);
  else if (messagename === "tick") seededRandomAtSongSixteenth(Math.round(a[0] / 120));
}
"""


def fixture_patch(preset_book):
    patch = DevicePatchBuilder(device_name="kit fixture", script_name=FIXTURE_SCRIPT_NAME, version="1.2.3",
                               subtitle="a test", link_chip_text="kit fixture", device_type="instrument",
                               device_width=480, page_names=["one", "two"], info=dict(FIXTURE_INFO),
                               preset_book=preset_book, latency_samples=0)
    brain = patch.box(f"js {FIXTURE_SCRIPT_NAME}.js", rect=(30, 120, 110, 22), ins=2, outs=3)
    gen = patch.gen_box(FIXTURE_GEN_CODE, 1, 1, rect=(30, 350, 160, 22))
    header = patch.header(output_level_target=gen, output_level_name="Volume")
    patch.wire(header["ready"], brain, 0, 1)
    patch.live_transport(brain, 1)
    patch.stop_action(brain, 1, panic_destinations=[gen])
    level_view = patch.view("level", 12, layout_rules.VIEW_Y, 120, layout_rules.VIEW_H, "one", info="Level view")
    patch.dial("Level", "Level", gen, "level", 0, 100, 5, 12, layout_rules.DIAL_Y, "one", scale=0.01,
               views=[(level_view, "level")])
    bright = patch.toggle("Bright", "Bright", 12, layout_rules.ROW_Y, 60, 15, "one")
    patch.tell(bright, "bright", brain, 1)
    patch.turned_off_by_stop(bright)
    shape = patch.menu("Shape", "Shape", ["round", "square"], 76, layout_rules.ROW_Y, 56, "one")
    patch.tell(shape, "shape", brain, 1)
    mode = patch.tabs("Mode", "Mode", ["a", "b", "c"], 12, layout_rules.ROW_Y, 96, "two")
    patch.tell(mode, "mode", brain, 1)
    kick = patch.toggle("Kick", "Kick", 120, layout_rules.ROW_Y, 48, 15, "two", mode=0)
    patch.wire(kick, brain, 0, 1)
    stored = patch.stored("Memory", 7)
    patch.tell(stored, "memory", brain, 1)
    seeded_random = SeededRandom(patch, brain, 1)
    seeded_random.seed_control(180, layout_rules.DIAL_Y, 40, "two")
    seeded_random.loop_control(224, layout_rules.DIAL_Y, 56, "two")
    chord_view = patch.view("chord", 180, layout_rules.VIEW_Y, 184, layout_rules.VIEW_H, "two", info="Chord view")
    chords = ChordBlock(patch, seeded_random, brain, 1, 1, chord_view, most_notes_per_chord=4,
                        one_note=True)
    chords.chord_menu("Chord", "Chord", 180, layout_rules.ROW_Y, 80, "two")
    chords.in_key_toggle("In key", "In key", 264, layout_rules.ROW_Y, 52, 15, "two")
    stages = StoredTable(patch, "Stage", [ContinuousField("Pitch", -24, 24), ChoiceField("Pulse", ["off", "on"]),
                                          ChoiceField("Wait", ["go", "stop", "hold", "keyed"])],
                         row_count=2, brain=brain, brain_inlet=1, brain_outlet=2)
    stages.editor_dial("Pitch", 0, "Stage Pitch edit 1", "Pitch 1", 140, layout_rules.DIAL_Y, "one")
    stages.editor_dial("Pitch", 1, "Stage Pitch edit 2", "Pitch 2", 188, layout_rules.DIAL_Y, "one")
    stages.editor_toggle("Pulse", 0, "Stage Pulse edit 1", "Pulse 1", 140, layout_rules.ROW_Y, 48, "one")
    stages.editor_menu("Wait", 1, "Stage Wait edit 2", "Wait 2", 192, layout_rules.ROW_Y, 44, "one")
    patch.fixture_stages = stages
    patch.fixture_brain = fill_template(FIXTURE_BRAIN_TEMPLATE, {"SEEDED_RANDOM": seeded_random.brain_code(),
                                                                 "CHORD_BLOCK": chords.brain_code(),
                                                                 "STORED_TABLES": stored_tables_brain_code([stages])},
                                        "the fixture's brain")
    return patch


# the chrome's rules and labels per page (the kit places the subtitle: layout_rules.subtitle_x)
FIXTURE_LAYOUT = {"pages": [{"rules": [140], "labels": []}, {"rules": [], "labels": []}]}


def stored_memory_of_preset(preset_values):
    return {"Memory": 7 + preset_values["Level"]}


def make_fixture_repository(root, preset_book_data=None):
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    with open(os.path.join(root, "src", "presets.json"), "w", encoding="utf-8") as book_file:
        json.dump(preset_book_data or FIXTURE_PRESET_BOOK, book_file)
    return DeviceRepository(root)


def build_fixture_device(root, command_line_arguments=("--accept-live-parameter-changes",), patch_edit=None,
                         live_preset_files=True, views_code=FIXTURE_VIEWS_CODE):
    """Build the fixture into `root`. patch_edit(patch): a change made before the build (a test's breakage)."""
    repository = make_fixture_repository(root) if not os.path.isdir(os.path.join(root, "src")) else DeviceRepository(root)
    preset_book = PresetBook.from_file(repository.source_path("presets.json"), "src/presets.json")
    patch = fixture_patch(preset_book)
    if patch_edit is not None:
        patch_edit(patch)
    build_device(repository, patch, FIXTURE_LAYOUT, views_code, {f"{FIXTURE_SCRIPT_NAME}.js": patch.fixture_brain},
                 live_preset_files=LivePresetFiles(stored_memory_of_preset) if live_preset_files else None,
                 command_line_arguments=command_line_arguments)
    return repository
