"""SeededRandom: one seeded generator per device, with its Seed and Loop controls (architecture/seeded-random.md).

Everything random a device does is `randomNext()` in its brain: the next number of the sequence Seed starts
(templates/seeded-random.template.js, mulberry32). Loop starts the sequence over at every Loop boundary of the song
position while Live plays, and at transport start. The kit owns the two controls' names and Info text, so every
device's Seed and Loop mean the same.

    random = SeededRandom(patch, brain, brain_control_inlet)
    random.seed_control(x, y, w, page)          # a live.numbox: Seed, 0-999
    random.seed_dial(x, y, page)                 # or Seed as a live.dial (one form a device)
    random.loop_control(x, y, w, page)          # a live.menu: Loop, off / 1 bar ... 64 bars
    brain_code = random.brain_code()             # fills the device brain's /*SEEDED_RANDOM*/
    SeededRandom.sequence_code()                 # the generator alone, for a device that only needs numbers from
                                                 # a seed (2sl drums' random function)
"""
import json

from twosl_dsp.build_error import BuildError
from twosl_dsp.generated_scripts import fill_template, kit_template_text

SEED_NAME = "Seed"
LOOP_NAME = "Loop"
# Seed is a float with Live's Int unit style, the brain taking the nearest whole number: the kit's Live preset writer
# knows only float and enum parameters (an Int's form hasn't been seen in a file Live wrote), and Live's Int type
# would hold only 256 seeds.
SEED_HIGHEST = 999
SEED_UNIT_STYLE = 0                  # Live's Int unit style: whole numbers shown
# the neutral values (a double-click's target, the kit's for every device): Seed 0, Loop off (never starts over)
SEED_NEUTRAL = 0
LOOP_NEUTRAL_INDEX = 0
LOOP_CHOICES = [("off", 0), ("1 bar", 1), ("2 bars", 2), ("4 bars", 4), ("8 bars", 8), ("16 bars", 16),
                ("32 bars", 32), ("64 bars", 64)]
INFO = {
    SEED_NAME: ("Seed", "Where the device's random choices start: the same Seed makes the same choices in the same "
                        "order, so a part plays back the way you heard it. Loop starts them over. 0 to 999; double-click: 0."),
    LOOP_NAME: ("Loop", "How often the random choices start over from Seed while Live plays: every 1 to 64 bars of "
                        "4 beats, counted from the song's start, so the randomness repeats. Off: it never starts "
                        "over. Pressing play also starts it from Seed. Stopped, it keeps going. Double-click: off."),
}


class SeededRandom:
    def __init__(self, patch, brain, brain_control_inlet):
        """The device's seeded random, in `brain` (a js box): its controls are told to `brain_control_inlet`."""
        for name, text in INFO.items():
            if name in patch.info:
                patch.fail(f"the info has {name!r}, which the kit's seeded random names: leave it to the kit")
            patch.info[name] = text
        self.patch, self.brain, self.brain_control_inlet = patch, brain, brain_control_inlet
        self.made = set()

    def seed_control(self, x, y, w, page, group=None):
        """Seed as a live.numbox, `w` px wide in the row band (seed_dial: as a dial)."""
        if SEED_NAME in self.made:
            raise BuildError(f"{self.patch.device_name}: Seed is made twice (seed_control or seed_dial: one)")
        box_id = self.patch.numbox(SEED_NAME, SEED_NAME, self.brain, "random_seed", 0, SEED_HIGHEST, SEED_UNIT_STYLE,
                                   x, y, w, page, inlet=self.brain_control_inlet, group=group, kit_neutral=SEED_NEUTRAL)
        self.made.add(SEED_NAME)
        return box_id

    def seed_dial(self, x, y, page, group=None):
        """Seed as a live.dial (DIAL_WIDTH x DIAL_HEIGHT, the dial band): the same parameter as seed_control's number
        box (a float 0-999 with Live's Int unit style, so it shows whole numbers; the brain takes the nearest), so
        Live keeps a set's Seed, its automation and its mappings when a device moves from one to the other (they go
        by its long name and range: architecture/live-parameter-identity.md); only the lock's maxclass changes."""
        if SEED_NAME in self.made:
            raise BuildError(f"{self.patch.device_name}: Seed is made twice (seed_control or seed_dial: one)")
        box_id = self.patch.dial(SEED_NAME, SEED_NAME, self.brain, "random_seed", 0, SEED_HIGHEST, SEED_UNIT_STYLE, x, y,
                                 page, inlet=self.brain_control_inlet, group=group, kit_neutral=SEED_NEUTRAL)
        self.made.add(SEED_NAME)
        return box_id

    def loop_control(self, x, y, w, page, group=None):
        box_id = self.patch.menu(LOOP_NAME, LOOP_NAME, [name for name, _ in LOOP_CHOICES], x, y, w, page, group=group,
                                 kit_neutral=LOOP_NEUTRAL_INDEX)
        self.patch.tell(box_id, "random_loop", self.brain, self.brain_control_inlet)
        self.made.add(LOOP_NAME)
        return box_id

    @staticmethod
    def sequence_code():
        return kit_template_text("seeded-sequence.template.js").strip()

    def brain_code(self):
        """The seeded random for the device's brain, starting where the Init values put Seed and Loop."""
        missing = sorted({SEED_NAME, LOOP_NAME} - self.made)
        if missing:
            raise BuildError(f"{self.patch.device_name}: the seeded random's brain code needs its controls first: "
                             f"make {missing} (seed_control, loop_control)")
        return fill_template(kit_template_text("seeded-random.template.js"), {
            "SEEDED_SEQUENCE": self.sequence_code(),
            "LOOP_BARS": json.dumps([bars for _, bars in LOOP_CHOICES]),
            "SEED_HIGHEST": str(SEED_HIGHEST),
            "INITIAL_SEED": str(int(self.patch.initial_values[SEED_NAME])),
            "INITIAL_LOOP": str(self.patch.initial_values[LOOP_NAME])}, "the kit's seeded random template").strip()
