"""The Altec 9069B passive high-pass (a circuit module): King Tubby's "Big Knob", a ten-step constant-K T section
for 600 ohms (references/circuits/altec-9069b.md: the steps, the parts, what is computed and what is unknown).

The circuit, per step: the source (its resistance `source_ohms`) into two equal capacitors in series, an inductor
from their junction to ground, the load (`load_ohms`) across the output. The switch picks a tap of one multitap
inductor and a pair of capacitors: STEP_PARTS, the parts a builder measured, whose corners 1 / (2 pi sqrt(2 L C)) land
on the replica's 70 Hz to 7.5 kHz within 2 %. Driven from 600 ohms into 600 ohms each step is a third-order
Butterworth high-pass with no peak, and the terminations halve the voltage: 6 dB of insertion loss. From a low
source into a high load the same parts peak (+15.9 dB at 1.42 x the corner from 50 ohms into 10k): the character.

The network is solved as it is, one node equation each, with each reactive part a trapezoidal companion model (its
conductance and a history current), prewarped at the step's corner so the corner is exact at every sample rate. The
parts' own voltages and currents are the state, so a step change keeps the charge on the network and changes the
parts around it: the change makes its own transient, the knob's click, with no crossfade added (how a real switch
lands, bridging or breaking, is unknown: the reference says so). Step 0 is the switch's flat position: the
terminations alone, the network out and emptied.

Inputs, GenExpr expressions in the circuit's units: `input_volts` (the source's open-circuit voltage), `step`
(0 flat, 1..10 the steps from the lowest corner; rounded, held to 0..10).
Outputs: `<name>_out` (volts across the load), `<name>_corner_hz` (the step's corner now, 0 when flat).
`passband_gain` (Python) is the terminations' division, load / (source + load): a device that makes the loss up
divides by it. `small_signal_response(step, frequency_hz)` is the analogue network's response, for a display and the
tests.
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.generated_numbers import generated_number

# The ten steps' parts (references/circuits/altec-9069b.md §2): (inductor tap, henries; each series capacitor, farads)
STEP_PARTS = ((0.698, 3.77e-6), (0.481, 2.67e-6), (0.330, 1.68e-6), (0.200, 1.00e-6), (0.092, 550e-9),
              (0.046, 267e-9), (0.0235, 133e-9), (0.0154, 90e-9), (0.0093, 53.8e-9), (0.0063, 35.2e-9))
STEP_CORNERS_HZ = tuple(1 / (2 * math.pi * math.sqrt(2 * henries * farads)) for henries, farads in STEP_PARTS)
# the prewarp's tangent stays finite: a step's corner held under this share of the sample rate
HIGHEST_PREWARP_OF_SAMPLE_RATE = 0.45


@dataclasses.dataclass(frozen=True)
class Altec9069BHighPassCharacter:
    """The terminations: what drives the filter and what it drives. 600 / 600 is the design (references §3); how
    Tubby's MCI drove and loaded it is UNVERIFIED."""
    source_ohms: float = 600.0
    load_ohms: float = 600.0


class Altec9069BHighPass(CircuitModule):
    """See the module docstring."""

    references_entry = "references/circuits/altec-9069b.md"
    character_type = Altec9069BHighPassCharacter

    def __init__(self, instance_name, *, input_volts, step, character=None):
        super().__init__(instance_name, character=character, input_volts=input_volts, step=step)
        if not (self.character.source_ohms > 0 and self.character.load_ohms > 0):
            raise BuildError(f"Altec9069BHighPass {instance_name}: the terminations must be > 0 ohms")
        self.latency_samples = 0       # a minimum-phase filter: no delay of its own in the pass band (above 1.5 x)
        self.passband_gain = self.character.load_ohms / (self.character.source_ohms + self.character.load_ohms)

    def small_signal_response(self, step, frequency_hz):
        """The analogue network's voltage gain (complex) at `frequency_hz` on `step` (0: flat)."""
        return small_signal_response(self.character, step, frequency_hz)

    def declarations(self):
        return self.substituted("History ${p}_c1_volts(0), ${p}_c1_amps(0), ${p}_inductor_volts(0), "
                                "${p}_inductor_amps(0), ${p}_c2_volts(0), ${p}_c2_amps(0);")

    def statements(self):
        p = self.instance_name
        def chosen(values):
            text = repr(generated_number(values[-1]))
            for number in range(len(values) - 1, 0, -1):
                text = f"({p}_step <= {number} ? {generated_number(values[number - 1])!r} : {text})"
            return text
        source_siemens = generated_number(1 / self.character.source_ohms)
        load_siemens = generated_number(1 / self.character.load_ohms)
        return self.substituted(f"""// ${{p}}: the Altec 9069B high-pass (kit circuit module), one step of its T section
${{p}}_step = clamp(floor(${{step}} + 0.5), 0, 10);
${{p}}_corner_hz = ${{p}}_step >= 1 ? {chosen(STEP_CORNERS_HZ)} : 0;
// flat: the terminations alone, the network out of circuit and emptied
${{p}}_out = ${{input_volts}} * {generated_number(self.passband_gain)!r};
if (${{p}}_step < 1) {{
	${{p}}_c1_volts = 0;
	${{p}}_c1_amps = 0;
	${{p}}_inductor_volts = 0;
	${{p}}_inductor_amps = 0;
	${{p}}_c2_volts = 0;
	${{p}}_c2_amps = 0;
}}
else {{
	// each part a trapezoidal companion (2 / T prewarped at the corner): a capacitor's current Gc v - J, the
	// inductor's Gl v + K, J and K from its voltage and current last sample
	${{p}}_henries = {chosen([henries for henries, _ in STEP_PARTS])};
	${{p}}_farads = {chosen([farads for _, farads in STEP_PARTS])};
	${{p}}_warp_w = twopi * min(${{p}}_corner_hz, samplerate * {HIGHEST_PREWARP_OF_SAMPLE_RATE!r});
	${{p}}_two_over_t = ${{p}}_warp_w / tan(${{p}}_warp_w / (2 * samplerate));
	${{p}}_gc = ${{p}}_farads * ${{p}}_two_over_t;
	${{p}}_gl = 1 / (${{p}}_henries * ${{p}}_two_over_t);
	${{p}}_j1 = ${{p}}_gc * ${{p}}_c1_volts + ${{p}}_c1_amps;
	${{p}}_k = ${{p}}_inductor_amps + ${{p}}_gl * ${{p}}_inductor_volts;
	${{p}}_j2 = ${{p}}_gc * ${{p}}_c2_volts + ${{p}}_c2_amps;
	// the node equations, solved: the source's node A, the junction B, the output C
	${{p}}_a = ${{p}}_gc / ({source_siemens!r} + ${{p}}_gc);
	${{p}}_b = ${{p}}_gc / (${{p}}_gc + {load_siemens!r});
	${{p}}_junction = (${{p}}_a * {source_siemens!r} * ${{input_volts}} + (${{p}}_a - 1) * ${{p}}_j1 - ${{p}}_k + (1 - ${{p}}_b) * ${{p}}_j2)
		/ (${{p}}_a * {source_siemens!r} + ${{p}}_gl + ${{p}}_b * {load_siemens!r});
	${{p}}_source_node = ({source_siemens!r} * ${{input_volts}} + ${{p}}_gc * ${{p}}_junction + ${{p}}_j1) / ({source_siemens!r} + ${{p}}_gc);
	${{p}}_out = (${{p}}_gc * ${{p}}_junction - ${{p}}_j2) / (${{p}}_gc + {load_siemens!r});
	// the parts' voltages and currents now: the state
	${{p}}_c1_volts = ${{p}}_source_node - ${{p}}_junction;
	${{p}}_c1_amps = ${{p}}_gc * ${{p}}_c1_volts - ${{p}}_j1;
	${{p}}_inductor_volts = ${{p}}_junction;
	${{p}}_inductor_amps = ${{p}}_gl * ${{p}}_junction + ${{p}}_k;
	${{p}}_c2_volts = ${{p}}_junction - ${{p}}_out;
	${{p}}_c2_amps = ${{p}}_gc * ${{p}}_c2_volts - ${{p}}_j2;
}}""")


def small_signal_response(character, step, frequency_hz):
    """The network's voltage gain at `frequency_hz` on `step`: the source's open-circuit voltage to the load's."""
    source, load = character.source_ohms, character.load_ohms
    if step < 1:
        return load / (source + load)
    henries, farads = STEP_PARTS[int(step) - 1]
    s = 2j * math.pi * frequency_hz
    capacitor = 1 / (s * farads)
    # the output branch (C2 then the load) in parallel with the inductor, at the junction
    branch = capacitor + load
    junction_load = 1 / (1 / (s * henries) + 1 / branch)
    junction = junction_load / (source + capacitor + junction_load)
    return junction * load / branch


def magnitude_db(response):
    return 20 * math.log10(abs(response))
