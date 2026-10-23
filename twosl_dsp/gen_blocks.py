"""Gen blocks: GenExpr code the kit provides and a device's gen~ code includes (architecture/dsp-blocks.md).

Every gen block is in one of two layers, each a package with its base class here:
- a **technique** (`twosl_dsp/techniques/`, `Technique`): a way to do DSP well, with no circuit identity;
- a **circuit module** (`twosl_dsp/circuit_modules/`, `CircuitModule`): one modelled piece of hardware, built from
  techniques; its inputs are the circuit's controls and CV in the circuit's units, its build character a setting.
The third layer, the instruments, are the devices (their own repositories).

A block instance is made with a name (its prefix: every History, Delay and local it makes starts with `<name>_`) and
the GenExpr expressions it reads (its inputs, evaluated once each sample where the block's statements stand). It gives
- `functions()`: {name: GenExpr function definition}, shared by every instance (gen wants functions first);
- `declarations()`: its History and Delay lines;
- `statements()`: its per-sample code, which leaves its outputs in locals named in its docstring;
- `latency_samples`: an instance attribute, how late its output is against its input, in host samples (fractions
  allowed; 0 for none; a block run at steps converts its steps by its `oversampling`), so a device sums its paths'
  blocks and declares its Defined Latency by the rule (twosl_dsp/techniques/defined_latency_pad.py). Every block sets
  it, including 0 (tests/test_gen_block_layers.py); `gen_code_with_blocks` fails a block without it.

A device's gen~ template holds `/*GEN_BLOCK_FUNCTIONS*/` (first: before the device's own functions),
`/*GEN_BLOCK_DECLARATIONS*/` (among its declarations) and one `/*<NAME>*/` per instance (where its statements go,
after the device has computed its inputs). `gen_code_with_blocks` fills them; a missing or extra marker, a name that
isn't an identifier, two instances of one name and one function name with two bodies all fail the build.
"""
import math
import re
import string

from twosl_dsp.build_error import BuildError
from twosl_dsp.generated_numbers import generated_number
from twosl_dsp.generated_scripts import fill_template

GEN_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")

# Every per-sample smoother in the kit's blocks and the devices' gen~ code: a one-pole with a time constant in ms,
# converted with the sample rate, so it sounds the same at 44.1 and 192 kHz.
SMOOTHING_FUNCTION = """// one-pole smoothing coefficient for a time constant in ms (63% of the way there in that time)
smoothing_coefficient(time_constant_ms, sample_rate) {
\treturn 1 - exp(-1000 / (max(time_constant_ms, 0.001) * sample_rate));
}"""


class GenBlock:
    """One instance of a kit gen block. Not subclassed directly: a block is a `Technique` or a `CircuitModule`
    (tests/test_gen_block_layers.py holds the kit to that). `substituted` fills string.Template text: `${p}` is the
    instance name, `${<input>}` each input expression; a number given as a constant is written through
    generated_number (twosl_dsp/generated_numbers.py)."""

    # The references/ file whose `## ` heading names the block's source file: where its sources are quoted.
    references_entry = None

    def __init__(self, instance_name, **input_expressions):
        if not GEN_IDENTIFIER.match(instance_name):
            raise BuildError(f"{type(self).__name__}: the instance name {instance_name!r} must be a lower-case GenExpr "
                             "identifier (it prefixes every name the block makes)")
        self.instance_name = instance_name
        self.input_expressions = {}
        for input_name, expression in input_expressions.items():
            if not isinstance(expression, str) or not expression.strip():
                raise BuildError(f"{type(self).__name__} {instance_name}: input {input_name} must be a GenExpr "
                                 f"expression, got {expression!r}")
            self.input_expressions[input_name] = f"({expression})"

    @property
    def marker(self):
        return self.instance_name.upper()

    def substituted(self, template_text, **constants):
        values = dict(self.input_expressions, p=self.instance_name)
        values.update({name: repr(generated_number(float(value))) if isinstance(value, (int, float)) else value
                       for name, value in constants.items()})
        try:
            return string.Template(template_text).substitute(values)
        except (KeyError, ValueError) as problem:
            raise BuildError(f"{type(self).__name__} {self.instance_name}: its code names ${{{problem}}}, which "
                             "is neither an input nor a constant it was given") from problem

    def check_latency_samples(self):
        """The block's `latency_samples` (host samples, a finite number >= 0), or a BuildError naming the block."""
        latency_samples = getattr(self, "latency_samples", None)
        if isinstance(latency_samples, bool) or not isinstance(latency_samples, (int, float)) \
                or not math.isfinite(latency_samples) or latency_samples < 0:
            raise BuildError(f"{type(self).__name__} {self.instance_name}: every gen block reports latency_samples (how "
                             f"late its output is, in host samples, a finite number >= 0, 0 for none); got "
                             f"{latency_samples!r}")
        return latency_samples

    def functions(self):
        return {}

    def declarations(self):
        return ""

    def statements(self):
        raise NotImplementedError


class Technique(GenBlock):
    """A way to do DSP well, with no circuit identity (antialiasing, zero-delay structures, a soft clip, an echo's
    loop): its inputs are signals and the method's own quantities (Hz, Q, gains), its constants the method's, sourced
    in references/dsp.md. A technique may be built from other techniques, never from a circuit module."""

    references_entry = "references/dsp.md"


class CircuitModule(GenBlock):
    """One modelled piece of hardware (a chip, a section of one, a circuit block of an instrument), built from
    techniques. Its inputs are the real circuit's controls and CV in the circuit's units (volts at its pins, its clock
    in Hz); its build character (rails, trims, tolerances, a unit's leakage) is `character`, an instance of the
    module's `character_type` (a frozen dataclass of numbers whose defaults are the datasheet's typical unit), so two
    instances can be two different units. An instrument that exposes a unit's character (2sl phaser's Cells page) moves
    some fields at run time: `character_inputs` {field: GenExpr expression}, only the module's
    `runtime_character_fields`; `character` still holds the numbers (its Python model, the parts it keeps fixed). Subclasses set `references_entry` to the circuit's own file in
    references/circuits/ (schematic, datasheet: quoted, with pages) and `character_type`."""

    character_type = None
    # The character fields an instrument may move at run time (`character_inputs`); a module lists the ones its code
    # reads through `character_term` and whose run-time motion it keeps sound.
    runtime_character_fields = ()

    def __init__(self, instance_name, character=None, character_inputs=None, **input_expressions):
        super().__init__(instance_name, **input_expressions)
        if character is None:
            character = self.character_type()
        if not isinstance(character, self.character_type):
            raise BuildError(f"{type(self).__name__} {instance_name}: its character must be a "
                             f"{self.character_type.__name__}, got {character!r}")
        self.character = character
        self.character_inputs = {}
        for field_name, expression in (character_inputs or {}).items():
            if field_name not in self.runtime_character_fields:
                raise BuildError(f"{type(self).__name__} {instance_name}: character_inputs names {field_name!r}, "
                                 f"which is not one of its run-time character fields {list(self.runtime_character_fields)}")
            if not isinstance(expression, str) or not expression.strip():
                raise BuildError(f"{type(self).__name__} {instance_name}: character input {field_name} must be a "
                                 f"GenExpr expression, got {expression!r}")
            self.character_inputs[field_name] = f"({expression})"

    def character_term(self, field_name):
        """A character field as the module's code reads it: the instrument's GenExpr expression when it moves the field
        at run time (`character_inputs`), else the build's number."""
        if field_name in self.character_inputs:
            return self.character_inputs[field_name]
        return getattr(self.character, field_name)


def gen_code_with_blocks(template_text, blocks, template_name, other_replacements=None):
    """The device's gen~ code: `template_text` with the blocks' functions, declarations and statements (and
    `other_replacements`, {MARKER: text}) filled in by marker."""
    replacements = dict(other_replacements or {})
    functions = {"smoothing_coefficient": SMOOTHING_FUNCTION}
    declarations = []
    for block in blocks:
        block.check_latency_samples()
        if block.marker in replacements:
            raise BuildError(f"{template_name}: two things fill /*{block.marker}*/ (block instance names must be unique)")
        for function_name, text in block.functions().items():
            if functions.get(function_name, text) != text:
                raise BuildError(f"{template_name}: two blocks define the GenExpr function {function_name} differently")
            functions[function_name] = text
        declarations.append(block.declarations().strip())
        replacements[block.marker] = block.statements().strip()
    for reserved in ("GEN_BLOCK_FUNCTIONS", "GEN_BLOCK_DECLARATIONS"):
        if reserved in replacements:
            raise BuildError(f"{template_name}: /*{reserved}*/ is filled by the kit, not by the device")
    # in the order the blocks gave them: a function is defined before any function that calls it
    replacements["GEN_BLOCK_FUNCTIONS"] = "\n".join(functions.values())
    replacements["GEN_BLOCK_DECLARATIONS"] = "\n".join(text for text in declarations if text)
    return fill_template(template_text, replacements, template_name)
