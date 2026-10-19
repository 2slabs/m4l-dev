"""DSP blocks: GenExpr code the kit provides and a device's gen~ code includes (architecture/dsp-blocks.md).

A block instance is made with a name (its prefix: every History, Delay and local it makes starts with `<name>_`) and
the GenExpr expressions it reads (its inputs, evaluated once each sample where the block's statements stand). It gives
- `functions()`: {name: GenExpr function definition}, shared by every instance (gen wants functions first);
- `declarations()`: its History and Delay lines;
- `statements()`: its per-sample code, which leaves its outputs in locals named in its docstring.

A device's gen~ template holds `/*GEN_BLOCK_FUNCTIONS*/` (first: before the device's own functions),
`/*GEN_BLOCK_DECLARATIONS*/` (among its declarations) and one `/*<NAME>*/` per instance (where its statements go,
after the device has computed its inputs). `gen_code_with_blocks` fills them; a missing or extra marker, a name that
isn't an identifier, two instances of one name and one function name with two bodies all fail the build.
"""
import re
import string

from m4l_dev.build_error import BuildError
from m4l_dev.generated_scripts import fill_template

GEN_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")

# Every per-sample smoother in the kit's blocks and the devices' gen~ code: a one-pole with a time constant in ms,
# converted with the sample rate, so it sounds the same at 44.1 and 192 kHz.
SMOOTHING_FUNCTION = """// one-pole smoothing coefficient for a time constant in ms (63% of the way there in that time)
smoothing_coefficient(time_constant_ms, sample_rate) {
\treturn 1 - exp(-1000 / (max(time_constant_ms, 0.001) * sample_rate));
}"""


class GenBlock:
    """One instance of a kit DSP block. Subclasses set `code_template` (string.Template text: `${p}` is the
    instance name, `${<input>}` each input expression) or override `statements`."""

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
        values.update({name: repr(float(value)) if isinstance(value, (int, float)) else value
                       for name, value in constants.items()})
        try:
            return string.Template(template_text).substitute(values)
        except (KeyError, ValueError) as problem:
            raise BuildError(f"{type(self).__name__} {self.instance_name}: its code names ${{{problem}}}, which "
                             "is neither an input nor a constant it was given") from problem

    def functions(self):
        return {}

    def declarations(self):
        return ""

    def statements(self):
        raise NotImplementedError


def gen_code_with_blocks(template_text, blocks, template_name, other_replacements=None):
    """The device's gen~ code: `template_text` with the blocks' functions, declarations and statements (and
    `other_replacements`, {MARKER: text}) filled in by marker."""
    replacements = dict(other_replacements or {})
    functions = {"smoothing_coefficient": SMOOTHING_FUNCTION}
    declarations = []
    for block in blocks:
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
