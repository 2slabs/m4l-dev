"""What the patch matcher searches (architecture/patch-matcher.md): a voice (any GenExpr program the kit renders, its
parameters' search ranges, how it is triggered) and the map from the search's unit cube to parameter values.

A voice is plain data (picklable: the search's worker processes get it whole). Rendering one hit: a fresh GenProgram
(no state from the hit before; built at -O2, genexpr.OPTIMISED_COMPILER_FLAGS: a match renders one program thousands
of times), the fixed values, the searched values, the noise seed (gen~'s noise() and, through the
voice's seed Param, the kit's seeded techniques), the trigger on its input, the other inputs at zero, the audio
output's samples.
"""
import math
from dataclasses import dataclass, field

from twosl_dsp.genexpr import GenProgram, analyze
from twosl_dsp.build_error import BuildError

SCALES = ("linear", "log")
KINDS = ("continuous", "integer", "enum")


@dataclass(frozen=True)
class MatchedParameter:
    """One searched Param: a continuous range on a linear or log scale, integers in a range (an ordered count: searched
    with the continuous ones, rounded), or an enum (the Param values it takes: choices in no order of sound, each
    tried in turn by the search's sweep, patch_match_search.py). Make one with `continuous`, `integer` or `enum`."""
    name: str
    minimum: float
    maximum: float
    scale: str = "linear"
    kind: str = "continuous"
    choices: tuple = ()

    @classmethod
    def continuous(cls, name, minimum, maximum, scale="linear"):
        return cls(name, float(minimum), float(maximum), scale, "continuous")

    @classmethod
    def integer(cls, name, minimum, maximum):
        return cls(name, float(minimum), float(maximum), "linear", "integer")

    @classmethod
    def enum(cls, name, choices):
        choices = tuple(float(choice) for choice in choices)
        if not choices:
            raise BuildError(f"parameter '{name}': an enum needs at least one choice")
        return cls(name, min(choices), max(choices), "linear", "enum", choices)

    def __post_init__(self):
        where = f"parameter '{self.name}'"
        if self.scale not in SCALES:
            raise BuildError(f"{where}: scale '{self.scale}' is not one of {SCALES}")
        if self.kind not in KINDS:
            raise BuildError(f"{where}: kind '{self.kind}' is not one of {KINDS}")
        if not (math.isfinite(self.minimum) and math.isfinite(self.maximum)):
            raise BuildError(f"{where}: the range [{self.minimum}, {self.maximum}] is not finite")
        if self.kind != "enum" and not self.minimum < self.maximum:
            raise BuildError(f"{where}: minimum {self.minimum} is not under maximum {self.maximum}")
        if self.scale == "log" and self.minimum <= 0:
            raise BuildError(f"{where}: a log scale needs a positive minimum, not {self.minimum}")
        if self.kind == "integer" and (self.minimum != int(self.minimum) or self.maximum != int(self.maximum)):
            raise BuildError(f"{where}: an integer range needs integer ends, not [{self.minimum}, "
                                  f"{self.maximum}]")
        if self.kind == "enum" and len(set(self.choices)) != len(self.choices):
            raise BuildError(f"{where}: the enum's choices repeat: {self.choices}")

    def value_of_unit(self, unit):
        """The Param value at `unit` in [0, 1] (clamped): linear or log between the ends; an integer rounds; an enum
        takes the choice whose equal share of [0, 1] holds `unit`."""
        unit = min(1.0, max(0.0, float(unit)))
        if self.kind == "enum":
            return self.choices[min(len(self.choices) - 1, int(unit * len(self.choices)))]
        if self.scale == "log":
            value = self.minimum * (self.maximum / self.minimum) ** unit
        else:
            value = self.minimum + (self.maximum - self.minimum) * unit
        if self.kind == "integer":
            value = float(min(self.maximum, max(self.minimum, round(value))))
        return min(self.maximum, max(self.minimum, value))

    def unit_of_value(self, value):
        """The inverse: where `value` sits in [0, 1] (an enum: the middle of its choice's share). A value outside the
        range or not a choice raises."""
        value = float(value)
        if self.kind == "enum":
            if value not in self.choices:
                raise BuildError(f"parameter '{self.name}': {value} is not one of its choices {self.choices}")
            return (self.choices.index(value) + 0.5) / len(self.choices)
        if not self.minimum <= value <= self.maximum:
            raise BuildError(f"parameter '{self.name}': {value} is outside [{self.minimum}, {self.maximum}]")
        if self.scale == "log":
            return math.log(value / self.minimum) / math.log(self.maximum / self.minimum)
        return (value - self.minimum) / (self.maximum - self.minimum)


@dataclass(frozen=True)
class MatchTrigger:
    """How a hit starts: `value` on input `input_number` for `held_seconds` (0: one sample, an impulse), then 0."""
    input_number: int = 1
    value: float = 1.0
    held_seconds: float = 0.0


@dataclass(frozen=True)
class MatchedVoice:
    """A voice to match: its GenExpr code, inputs / outputs, the searched parameters, the fixed values of others,
    its trigger, which output is the audio, and the noise seed every render uses (a hit is a function of its
    parameters). The seed reaches gen~'s noise() (the renderer's seed) and, when `noise_seed_param` names one, the
    voice's Param that seeds its kit techniques (SeededWhiteNoise, PitchModulator's random: architecture/
    seeded-random.md), set to `noise_seed` on every render."""
    name: str
    gen_code: str
    num_inputs: int
    num_outputs: int
    parameters: tuple
    trigger: MatchTrigger = MatchTrigger()
    audio_output: int = 1
    fixed_values: tuple = field(default_factory=tuple)   # ((name, value), ...)
    noise_seed: int = 1
    noise_seed_param: str = ""                           # the Param the voice's seeded techniques read ("": none)

    def __post_init__(self):
        where = f"voice '{self.name}'"
        if not self.parameters:
            raise BuildError(f"{where}: no parameters to search")
        names = [parameter.name for parameter in self.parameters]
        if len(set(names)) != len(names):
            raise BuildError(f"{where}: a parameter is searched twice: {names}")
        _, info = analyze(self.gen_code, self.num_inputs, self.num_outputs)
        for parameter in self.parameters:
            if parameter.name not in info.params:
                raise BuildError(f"{where}: searches '{parameter.name}', which the code does not declare as a "
                                      f"Param (it declares: {', '.join(info.params) or 'none'})")
            declared = info.params[parameter.name]
            if ((declared.minimum is not None and parameter.minimum < declared.minimum)
                    or (declared.maximum is not None and parameter.maximum > declared.maximum)):
                raise BuildError(f"{where}: '{parameter.name}' is searched over [{parameter.minimum}, "
                                      f"{parameter.maximum}], outside its Param's [{declared.minimum}, "
                                      f"{declared.maximum}]: the renderer would clamp it")
        for fixed_name, _ in self.fixed_values:
            if fixed_name not in info.params:
                raise BuildError(f"{where}: fixes '{fixed_name}', which the code does not declare as a Param")
            if fixed_name in names:
                raise BuildError(f"{where}: '{fixed_name}' is both fixed and searched")
        if self.noise_seed_param:
            if self.noise_seed_param not in info.params:
                raise BuildError(f"{where}: its noise seed Param '{self.noise_seed_param}' is not declared by the code")
            if self.noise_seed_param in names or self.noise_seed_param in dict(self.fixed_values):
                raise BuildError(f"{where}: its noise seed Param '{self.noise_seed_param}' is also searched or fixed")
            declared = info.params[self.noise_seed_param]
            if ((declared.minimum is not None and self.noise_seed < declared.minimum)
                    or (declared.maximum is not None and self.noise_seed > declared.maximum)):
                raise BuildError(f"{where}: noise seed {self.noise_seed} is outside its Param's "
                                 f"[{declared.minimum}, {declared.maximum}]: the renderer would clamp it")
        given_a_value = set(names) | {fixed_name for fixed_name, _ in self.fixed_values} | {self.noise_seed_param}
        without_a_value = [name for name, declared in info.params.items()
                           if declared.default is None and name not in given_a_value]
        if without_a_value:
            raise BuildError(f"{where}: Params {without_a_value} have no default in the code and are neither searched "
                             "nor fixed: fix them (fixed_values)")
        if not 1 <= self.trigger.input_number <= self.num_inputs:
            raise BuildError(f"{where}: the trigger is on input {self.trigger.input_number}, the voice has "
                                  f"{self.num_inputs}")
        if not 1 <= self.audio_output <= self.num_outputs:
            raise BuildError(f"{where}: audio output {self.audio_output}, the voice has {self.num_outputs}")

    @property
    def dimension(self):
        return len(self.parameters)

    def values_of_units(self, units):
        if len(units) != self.dimension:
            raise BuildError(f"voice '{self.name}': {len(units)} unit values for {self.dimension} parameters")
        return {parameter.name: parameter.value_of_unit(unit) for parameter, unit in zip(self.parameters, units)}

    def units_of_values(self, values_by_name):
        missing = [parameter.name for parameter in self.parameters if parameter.name not in values_by_name]
        if missing:
            raise BuildError(f"voice '{self.name}': no value for {missing}")
        return [parameter.unit_of_value(values_by_name[parameter.name]) for parameter in self.parameters]

    def render(self, values_by_name, num_samples, rate):
        """One hit: `num_samples` of the audio output at `rate`, the searched Params at `values_by_name`."""
        program = GenProgram(self.gen_code, self.num_inputs, self.num_outputs, samplerate=rate, seed=self.noise_seed,
                             optimised=True)
        for fixed_name, fixed_value in self.fixed_values:
            program.set_param(fixed_name, fixed_value)
        if self.noise_seed_param:
            program.set_param(self.noise_seed_param, self.noise_seed)
        for parameter in self.parameters:
            if parameter.name not in values_by_name:
                raise BuildError(f"voice '{self.name}': no value for '{parameter.name}'")
            program.set_param(parameter.name, values_by_name[parameter.name])
        held_samples = max(1, int(round(self.trigger.held_seconds * rate)))
        trigger_samples = [self.trigger.value] * min(held_samples, num_samples) + [0.0] * max(0, num_samples - held_samples)
        inputs = [0.0] * self.num_inputs
        inputs[self.trigger.input_number - 1] = trigger_samples
        return program.run(num_samples, inputs)[self.audio_output - 1]
