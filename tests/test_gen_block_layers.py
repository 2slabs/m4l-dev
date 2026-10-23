"""The gen block layers (architecture/dsp-blocks.md), checked on the kit's source: every gen block is a technique
(twosl_dsp/techniques/) or a circuit module (twosl_dsp/circuit_modules/), techniques never use circuit modules, each file
imports only what its layer may, every block cites its references/ entry, a module's character is a frozen dataclass
of numbers. And the gen block pattern's build rules (twosl_dsp/gen_blocks.py). Standard library only."""
import ast
import dataclasses
import importlib
import inspect
import os
import re
import sys
import unittest

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT_ROOT)
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.gen_blocks import CircuitModule, GenBlock, Technique, gen_code_with_blocks  # noqa: E402
from twosl_dsp.techniques.zero_delay_ladder_filter import ZeroDelayLadderFilter  # noqa: E402

PACKAGE_DIRECTORY = os.path.join(KIT_ROOT, "twosl_dsp")
LAYERS = {"techniques": Technique, "circuit_modules": CircuitModule}
# What a block file may import from the kit, by layer (the standard library is always allowed).
KIT_IMPORTS_ALLOWED = {
    "techniques": ("twosl_dsp.gen_blocks", "twosl_dsp.build_error", "twosl_dsp.generated_scripts",
                   "twosl_dsp.generated_numbers", "twosl_dsp.techniques"),
    "circuit_modules": ("twosl_dsp.gen_blocks", "twosl_dsp.build_error", "twosl_dsp.generated_scripts",
                        "twosl_dsp.generated_numbers", "twosl_dsp.techniques"),
}


def layer_files(layer):
    directory = os.path.join(PACKAGE_DIRECTORY, layer)
    return sorted(name for name in os.listdir(directory) if name.endswith(".py") and name != "__init__.py")


def kit_imports(path):
    """Every twosl_dsp module the file imports (absolute names), with line numbers."""
    tree = ast.parse(open(path).read(), path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(alias.name, node.lineno) for alias in node.names if alias.name.startswith("twosl_dsp")]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                found.append((f"(relative import, level {node.level}) {node.module}", node.lineno))
            elif node.module and node.module.startswith("twosl_dsp"):
                found += [(node.module if node.module != "twosl_dsp" else f"twosl_dsp.{alias.name}", node.lineno)
                          for alias in node.names]
    return found


def block_classes_defined_in(module):
    return [value for value in vars(module).values()
            if inspect.isclass(value) and issubclass(value, GenBlock) and value.__module__ == module.__name__]


def headings_of(references_path):
    return [line for line in open(os.path.join(KIT_ROOT, references_path)) if line.startswith("## ")]


class GenBlockLayerTests(unittest.TestCase):
    def test_every_gen_block_is_filed_in_a_layer(self):
        # no GenBlock subclass outside the two layer packages (the bases themselves live in gen_blocks.py)
        for directory, _, files in os.walk(PACKAGE_DIRECTORY):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(directory, name)
                relative = os.path.relpath(path, KIT_ROOT)
                layer = os.path.relpath(directory, PACKAGE_DIRECTORY)
                module = importlib.import_module(relative[:-3].replace(os.sep, "."))
                for block_class in block_classes_defined_in(module):
                    if relative == os.path.join("twosl_dsp", "gen_blocks.py"):
                        self.assertIn(block_class, (GenBlock, Technique, CircuitModule), relative)
                        continue
                    self.assertIn(layer, LAYERS, f"{relative}: {block_class.__name__} is a gen block outside "
                                                 "twosl_dsp/techniques/ and twosl_dsp/circuit_modules/")
                    self.assertTrue(issubclass(block_class, LAYERS[layer]),
                                    f"{relative}: {block_class.__name__} is in {layer}/ but not a "
                                    f"{LAYERS[layer].__name__}")
                    self.assertFalse(issubclass(block_class, Technique) and issubclass(block_class, CircuitModule),
                                     f"{relative}: {block_class.__name__} is in both layers")

    def test_each_layer_imports_only_what_it_may(self):
        for layer, allowed in KIT_IMPORTS_ALLOWED.items():
            for name in layer_files(layer):
                path = os.path.join(PACKAGE_DIRECTORY, layer, name)
                for imported, line in kit_imports(path):
                    self.assertTrue(any(imported == prefix or imported.startswith(prefix + ".") for prefix in allowed),
                                    f"twosl_dsp/{layer}/{name}:{line} imports {imported}; a {layer[:-1].replace('_', ' ')}"
                                    f" may import only {', '.join(allowed)} and the standard library")

    def test_techniques_never_use_a_circuit_module(self):
        for name in layer_files("techniques"):
            for imported, line in kit_imports(os.path.join(PACKAGE_DIRECTORY, "techniques", name)):
                self.assertFalse(imported.startswith("twosl_dsp.circuit_modules"),
                                 f"twosl_dsp/techniques/{name}:{line} imports the circuit module {imported}")

    def test_every_block_file_cites_its_references_entry(self):
        for layer, base in LAYERS.items():
            for name in layer_files(layer):
                module = importlib.import_module(f"twosl_dsp.{layer}.{name[:-3]}")
                classes = block_classes_defined_in(module)
                self.assertTrue(classes, f"twosl_dsp/{layer}/{name} defines no {base.__name__}")
                source_path = f"twosl_dsp/{layer}/{name}"
                for block_class in classes:
                    entry = block_class.references_entry
                    self.assertIsInstance(entry, str, f"{source_path}: {block_class.__name__} cites nothing")
                    if layer == "circuit_modules":
                        self.assertTrue(re.fullmatch(r"references/circuits/[a-z0-9-]+\.md", entry),
                                        f"{source_path}: a circuit module cites its own references/circuits/ file, "
                                        f"not {entry}")
                    self.assertTrue(os.path.isfile(os.path.join(KIT_ROOT, entry)), f"{source_path}: {entry} is missing")
                    self.assertTrue(any(source_path in heading for heading in headings_of(entry)),
                                    f"{entry} has no `## ` heading naming {source_path}")
                    self.assertIn(entry, module.__doc__ or "", f"{source_path}: its docstring doesn't name {entry}")

    def test_a_circuit_module_file_is_one_piece_of_hardware_with_its_character(self):
        for name in layer_files("circuit_modules"):
            module = importlib.import_module(f"twosl_dsp.circuit_modules.{name[:-3]}")
            modules = [c for c in block_classes_defined_in(module) if issubclass(c, CircuitModule)]
            self.assertEqual(len(modules), 1, f"twosl_dsp/circuit_modules/{name}: one circuit module a file")
            character_type = modules[0].character_type
            self.assertTrue(dataclasses.is_dataclass(character_type) and character_type.__dataclass_params__.frozen,
                            f"{name}: character_type must be a frozen dataclass")
            for field in dataclasses.fields(character_type):
                self.assertTrue(isinstance(field.default, (int, float)) and not isinstance(field.default, bool),
                                f"{name}: character field {field.name} must default to a number (the datasheet's "
                                "typical unit)")


def assigns_latency_samples(class_definition):
    """Whether a class body sets `latency_samples`: `self.latency_samples = ...` in its __init__, or a class-level
    `latency_samples` (an assignment or a property)."""
    for statement in class_definition.body:
        if isinstance(statement, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "latency_samples"
                                                     for target in statement.targets):
            return True
        if isinstance(statement, ast.FunctionDef) and statement.name == "latency_samples":
            return True
        if isinstance(statement, ast.FunctionDef) and statement.name == "__init__":
            for node in ast.walk(statement):
                if isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Attribute) and target.attr == "latency_samples"
                        and isinstance(target.value, ast.Name) and target.value.id == "self" for target in node.targets):
                    return True
    return False


class GenBlockLatencyTests(unittest.TestCase):
    def test_every_gen_block_reports_its_latency_in_host_samples(self):
        # every Technique and CircuitModule subclass in the kit sets latency_samples (0 included), itself or through
        # a kit base class of its own (the linear twin is its saturator's); GenBlock, Technique, CircuitModule don't
        for layer in LAYERS:
            for name in layer_files(layer):
                module = importlib.import_module(f"twosl_dsp.{layer}.{name[:-3]}")
                for block_class in block_classes_defined_in(module):
                    kit_bases = [base for base in block_class.__mro__
                                 if issubclass(base, GenBlock) and base not in (GenBlock, Technique, CircuitModule)]
                    self.assertTrue(any(assigns_latency_samples(ast.parse(inspect.getsource(base)).body[0])
                                        for base in kit_bases),
                                    f"twosl_dsp/{layer}/{name}: {block_class.__name__} does not set latency_samples "
                                    "(how late its output is, host samples, 0 for none)")

    def test_a_block_without_a_latency_fails_the_build(self):
        class Silent(Technique):
            def statements(self):
                return "silent_out = 0;"
        for bad in (None, -1, float("nan"), True, "0"):
            block = Silent("silent")
            if bad is not None:
                block.latency_samples = bad
            with self.assertRaisesRegex(BuildError, "latency_samples"):
                gen_code_with_blocks("/*GEN_BLOCK_FUNCTIONS*/\n/*GEN_BLOCK_DECLARATIONS*/\n/*SILENT*/", [block], "t")


class GenBlockPatternTests(unittest.TestCase):
    def test_markers_must_match(self):
        ladder = ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="1000", resonance="0")
        with self.assertRaises(BuildError):
            gen_code_with_blocks("/*GEN_BLOCK_FUNCTIONS*/\n/*GEN_BLOCK_DECLARATIONS*/\nout1 = 0;", [ladder], "t")
        with self.assertRaises(BuildError):
            gen_code_with_blocks("/*GEN_BLOCK_FUNCTIONS*/\n/*LADDER*/\nout1 = 0;", [ladder], "t")

    def test_instance_names(self):
        with self.assertRaises(BuildError):
            ZeroDelayLadderFilter("Ladder", input="in1", cutoff_hz="1000", resonance="0")
        with self.assertRaises(BuildError):
            ZeroDelayLadderFilter("ladder", input="", cutoff_hz="1000", resonance="0")
        twice = [ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="1", resonance="0")] * 2
        with self.assertRaises(BuildError):
            gen_code_with_blocks("/*GEN_BLOCK_FUNCTIONS*/\n/*GEN_BLOCK_DECLARATIONS*/\n/*LADDER*/", twice, "t")

    def test_one_function_name_one_body(self):
        class Clash(Technique):
            latency_samples = 0

            def functions(self):
                return {"smoothing_coefficient": "smoothing_coefficient(a, b) { return 0; }"}

            def statements(self):
                return ""
        with self.assertRaises(BuildError):
            gen_code_with_blocks("/*GEN_BLOCK_FUNCTIONS*/\n/*GEN_BLOCK_DECLARATIONS*/\n/*CLASH*/", [Clash("clash")], "t")


if __name__ == "__main__":
    unittest.main(verbosity=2)
