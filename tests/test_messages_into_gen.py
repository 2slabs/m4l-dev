"""Two build checks of what a patch sends: Max time values are real (twosl_dsp/max_time_values.py, in
DevicePatchBuilder.box), and every message sent straight into a gen~ names a Param it declares: the patch's own
(check_messages_into_gen_name_params: tell's [prepend], message boxes) and its scripts' (check_script_messages_into_gen,
reading outlet() calls with twosl_dsp/script_outlet_calls.py). Builds small patches in memory; writes nothing."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.max_time_values import MAX_NOTE_VALUE_TICKS  # noqa: E402
from twosl_dsp.script_outlet_calls import outlet_calls  # noqa: E402
from test_patch_builder import builder  # noqa: E402  (its gen~, patch.target, declares a, b and volume)


class MaxTimeValueTests(unittest.TestCase):
    def test_64nt_is_not_a_max_note_value(self):
        with self.assertRaisesRegex(BuildError, "'64nt' is not a Max note value \\(Time Value Syntax\\)"):
            builder().box("metro 64nt @quantize 64nt")
        with self.assertRaisesRegex(BuildError, "'64nt' is not a Max note value"):
            builder().box("metro 16n @quantize 64nt")
        with self.assertRaisesRegex(BuildError, "'256n' is not a Max note value"):
            builder().box("delay 256n")

    def test_real_note_values_and_plain_numbers_pass(self):
        patch = builder()
        for text in ("metro 16n", "metro 64n @quantize 64n", "metro 128n", "delay 250", "metro 10.5 @interval 4nd",
                     "metro @interval 8nt", "pipe 32nd", "line 0 20"):
            patch.box(text)

    def test_the_table_is_the_reference_s(self):
        # Time Value Syntax: 480 ticks a quarter note; dotted is 3/2, triplet 2/3
        for name, ticks in MAX_NOTE_VALUE_TICKS.items():
            denominator = int(name.split("n")[0])
            plain = 1920 // denominator
            self.assertEqual(ticks, {"": plain, "d": plain * 3 // 2, "t": plain * 2 // 3}[name.split("n")[1]], name)
        self.assertEqual(len(MAX_NOTE_VALUE_TICKS), 21)

    def test_other_objects_are_not_read(self):
        builder().box("prepend 64nt")


def builder_with_script_into_gen():
    """The test builder with [js t.js]: outlet 0 wired straight into its gen~ (Params a, b, volume), outlet 1 not."""
    patch = builder()
    patch.script = patch.box("js t.js", ins=1, outs=2)
    patch.wire(patch.script, patch.target, 0, 0)
    patch.wire(patch.script, patch.box("print"), 1, 0)
    return patch


def check_script(script_text):
    builder_with_script_into_gen().check_script_messages_into_gen({"t.js": script_text})


class ScriptMessagesIntoGenTests(unittest.TestCase):
    def test_a_literal_that_is_a_param_passes(self):
        check_script('outlet(0, "a", 1);\noutlet(0, \'volume\', Math.max(0, (1 + 2)));')

    def test_a_literal_that_is_no_param_fails_naming_it(self):
        with self.assertRaisesRegex(BuildError, 't.js line 2: outlet\\(0, "hit_count", ...\\).*include no "hit_count"'):
            check_script('outlet(0, "a", 1);\noutlet(0, "hit_count", 1);')

    def test_a_concatenation_matching_a_param_passes(self):
        check_script('function f(n) { outlet(0, "vol" + n + "e", 1); outlet(0, "vo" + n, 2); }')

    def test_a_concatenation_matching_no_param_fails(self):
        with self.assertRaisesRegex(BuildError, 'no name matching "random_" \\+ n \\+ "_draw"'):
            check_script('function f(n) { outlet(0, "random_" + n + "_draw", 1); }')

    def test_a_bare_variable_fails_naming_the_line(self):
        with self.assertRaisesRegex(BuildError, "t.js line 3: outlet\\(0, name, ...\\).*can't be checked"):
            check_script('var name = "a";\n\nfunction f() { outlet(0, name, 1); }')

    def test_only_the_outlets_wired_into_the_gen_are_held(self):
        check_script('outlet(1, "anything", 1); outlet(1, someName);')

    def test_commented_out_calls_and_strings_are_not_calls(self):
        check_script('// outlet(0, "nope", 1);\n/* outlet(0, "nope"); */\nvar s = "outlet(0, \\"nope\\")";\n'
                     'var r = /outlet\\(0, "nope"\\)/;')

    def test_an_outlet_named_by_a_constant_is_resolved(self):
        with self.assertRaisesRegex(BuildError, 'outlet\\(GEN_OUTLET, "nope", ...\\)'):
            check_script('var GEN_OUTLET = 0;\noutlet(GEN_OUTLET, "nope", 1);')

    def test_an_outlet_the_text_cannot_say_fails_when_the_script_feeds_a_gen(self):
        with self.assertRaisesRegex(BuildError, "outlet\\(which.outlet, \"a\", ...\\): which outlet it sends from can't"):
            check_script('var which = {outlet: 0};\noutlet(which.outlet, "a", 1);')

    def test_a_script_the_build_does_not_have_fails(self):
        with self.assertRaisesRegex(BuildError, "t.js \\(box obj-\\d+\\) sends into a gen~, but the build has no such"):
            builder_with_script_into_gen().check_script_messages_into_gen({"other.js": ""})

    def test_a_blocks_outlet_is_known_and_must_not_feed_a_gen(self):
        patch = builder_with_script_into_gen()
        patch.script_outlet_of_block(patch.script, 1, "spec.outlet", "stored table 'T'")
        patch.check_script_messages_into_gen({"t.js": "outlet(spec.outlet, editor, 1);"})
        patch.script_outlet_of_block(patch.script, 0, "spec.outlet", "stored table 'U'")
        with self.assertRaisesRegex(BuildError, "stored table 'U''s outlet 0 is wired into"):
            patch.check_script_messages_into_gen({"t.js": "outlet(spec.outlet, editor, 1);"})

    def test_the_parser_reads_es5(self):
        calls = outlet_calls('obj.outlet(0, "x");\nfunction outlet(a) {}\noutlet(2, \'it\\\'s\' + (a ? "b" : "c"));\n'
                             'var x = 4 / 2 / 1; outlet(1, [1, 2].concat([3]));', "p.js")
        self.assertEqual([(call.line, call.outlet_index) for call in calls], [(3, 2), (4, 1)])
        self.assertEqual(calls[0].message.pattern, "it's.+")
        self.assertIsNone(calls[1].message)


class PatchMessagesIntoGenTests(unittest.TestCase):
    def test_tell_from_any_box_must_name_a_param(self):
        patch = builder()
        patch.tell(patch.box("t f"), "a", patch.target)
        patch.check_messages_into_gen_name_params()
        patch.tell(patch.box("t f"), "nope", patch.target)
        with self.assertRaisesRegex(BuildError, "\\[prepend nope\\] .* sends 'nope' into \\[gen~\\] .*no such Param"):
            patch.check_messages_into_gen_name_params()

    def test_a_message_box_into_a_gen_must_name_a_param(self):
        patch = builder()
        patch.wire(patch.box(cls="message", text="0.5", ins=2), patch.target)
        patch.wire(patch.box(cls="message", text="b 0.5", ins=2), patch.target)
        patch.check_messages_into_gen_name_params()
        patch.wire(patch.box(cls="message", text="nope 1", ins=2), patch.target)
        with self.assertRaisesRegex(BuildError, "message box \\[nope 1\\] .* sends 'nope'"):
            patch.check_messages_into_gen_name_params()


if __name__ == "__main__":
    unittest.main()
