"""Tests for twosl_dsp/generated_numbers.py: the rule every number a build writes follows, the check that holds a build
to it, and what it is for: the kit writes the same bytes whatever the machine's maths library rounds.

The perturbation test simulates another maths library: a child Python process has every math / cmath function
(sin, cos, tan, exp, log, pow, atan, ... and their complex twins) return its result moved some units in the last place
(away from or toward 0, or by a count fixed by the arguments' magnitudes, so f(-x) = -f(x) still holds, as in every
real libm), before the kit is imported, so module constants move too. It writes the gen~ code of every gen block in
the kit (each technique and circuit module with its functions, declarations, statements and display script) and the
fixture device's whole build; every byte has to be the same as with the machine's own maths library.

    python3 tests/test_generated_numbers.py --probe up4    # the probe itself: prints the sha256 of each output
"""
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import unittest
from fractions import Fraction

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.dirname(os.path.abspath(__file__))

LIBM_FUNCTIONS = {
    "math": "sin cos tan asin acos atan atan2 sinh cosh tanh asinh acosh atanh exp expm1 exp2 log log2 log10 log1p "
            "pow hypot erf erfc gamma lgamma cbrt".split(),
    "cmath": "sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh exp log log10 sqrt phase".split(),
}


def install_perturbed_libm(mode):
    """Every LIBM_FUNCTIONS result moved: "up<k>" k units in the last place away from 0, "down<k>" toward it,
    "random<k>" by a count in [-k, k] fixed by the arguments' magnitudes."""
    import cmath
    steps_of_mode = int(mode.lstrip("updownrandom"))

    def steps_for(arguments):
        if mode.startswith("up"):
            return steps_of_mode
        if mode.startswith("down"):
            return -steps_of_mode
        key = repr(tuple(abs(a) if isinstance(a, (int, float, complex)) else a for a in arguments))
        return random.Random(key).randint(-steps_of_mode, steps_of_mode)

    def nudged(value, arguments):
        if isinstance(value, complex):
            return complex(nudged(value.real, arguments + ("real",)), nudged(value.imag, arguments + ("imaginary",)))
        if not isinstance(value, float) or not math.isfinite(value) or value == 0:
            return value
        steps = steps_for(arguments)
        away = math.copysign(math.inf, value)
        for _ in range(abs(steps)):
            value = math.nextafter(value, away if steps > 0 else 0.0)
        return value

    for module in (math, cmath):
        for name in LIBM_FUNCTIONS[module.__name__]:
            if hasattr(module, name):
                setattr(module, name, (lambda f: lambda *a: nudged(f(*a), a))(getattr(module, name)))


def every_block_text():
    """{block class name: the text it writes}: every technique and circuit module in the kit, made with plain
    expressions for its inputs and its default design and character."""
    from twosl_dsp.generated_numbers import generated_number
    from twosl_dsp.circuit_modules.buchla_259_modulation_oscillator import Buchla259ModulationOscillator
    from twosl_dsp.circuit_modules.buchla_259_principal_oscillator import Buchla259PrincipalOscillator
    from twosl_dsp.circuit_modules.buchla_259_timbre_section import Buchla259TimbreSection
    from twosl_dsp.circuit_modules.buchla_292_low_pass_gate_channel import Buchla292LowPassGateChannel
    from twosl_dsp.circuit_modules import ltc1060_mf10_section, moog_transistor_ladder, mutron_bi_phase
    from twosl_dsp.techniques import sidechain_style_pump, zero_delay_ladder_filter
    from twosl_dsp.techniques.antiderivative_antialiasing_equaliser import AntiderivativeAntialiasingEqualiser
    from twosl_dsp.techniques.antiderivative_piecewise_linear_shaper import (AntiderivativePiecewiseLinearShaper,
                                                                          PiecewiseLinearTable)
    from twosl_dsp.techniques.antiderivative_tanh_saturator import (AntiderivativeTanhSaturator,
                                                                  AntiderivativeTanhSaturatorLinearTwin)
    from twosl_dsp.techniques.band_limited_edges import BandLimitedEdges
    from twosl_dsp.techniques.bell_equalizer import BellEqualizer
    from twosl_dsp.techniques.defined_latency_pad import DefinedLatency, DefinedLatencyPad
    from twosl_dsp.techniques.drum_envelope import DrumEnvelope
    from twosl_dsp.techniques.halfband_oversampler import (ControlsAtTheUpsampledSteps, HalfbandDownsampler,
                                                         HalfbandLinearPhaseDownsampler, HalfbandUpsampler)
    from twosl_dsp.techniques.histories_start_at_their_targets import HistoriesStartAtTheirTargets
    from twosl_dsp.techniques.knee_soft_clip import KneeSoftClip
    from twosl_dsp.techniques.led_driven_photocell import LedDrivenPhotocell
    from twosl_dsp.techniques.metallic_noise import LfsrMetallicNoise
    from twosl_dsp.techniques.pitch_modulator import PitchModulator
    from twosl_dsp.techniques.seeded_white_noise import SeededWhiteNoise
    from twosl_dsp.techniques.tape_style_echo import TapeStyleEcho
    from twosl_dsp.techniques.zero_delay_allpass_cascade import FirstOrderAllpassStage, ZeroDelayAllpassCascade
    from twosl_dsp.techniques.zero_delay_one_pole_filter import ZeroDelayOnePoleFilter
    from twosl_dsp.techniques.zero_delay_state_variable_filter import ZeroDelayStateVariableFilter

    upsampler = HalfbandUpsampler("up", input="in1")
    # a curve measured from a model: pieces whose numbers carry the maths library's last bits
    curve = [(-math.inf, 0.0, -math.tanh(1.0))] + [
        (x, (math.tanh(x + 0.5) - math.tanh(x)) / 0.5, math.tanh(x) - x * (math.tanh(x + 0.5) - math.tanh(x)) / 0.5)
        for x in (-1.0, -0.5, 0.0, 0.5)] + [(1.0, 0.0, math.tanh(1.0))]
    timbre = Buchla259TimbreSection("timbre", drive_volts="drive", symmetry_offset_volts="offset", frequency_hz="f",
                                    oversampling=2)
    mutron = mutron_bi_phase.MutronBiPhase(
        "unit", input_a_volts="in1", input_b_volts="in1", rate_1_hz="r1", rate_2_hz="r2", shape_1="s1", shape_2="s2",
        depth_a="da", depth_b="db", feedback_a="fa", feedback_b="fb", sweep_a_source="sa", sweep_b_source="sb",
        sweep_sync="sync", phasor_b_input="pb", foot_switch_a="fsa", foot_switch_b="fsb", pedal_volts="pedal")
    moog = moog_transistor_ladder.MoogTransistorLadder("moog", input_volts="in1", control_volts="cv",
                                                       emphasis="emphasis", oversampling=2)
    latency = DefinedLatency("probe", {"one": upsampler.latency_samples + 1.3, "two": math.pi})
    edges = BandLimitedEdges("edges", naive="naive", oversampling=1)
    edges.add_jump("jumped", "fraction", "size")
    edges.add_corner("cornered", "fraction", "size")
    blocks = [
        AntiderivativeAntialiasingEqualiser("eq1", order=1, oversampling=2, raw_mean="m"),
        AntiderivativeAntialiasingEqualiser("eq2", order=2, oversampling=2, raw_mean="m"),
        AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=PiecewiseLinearTable("curve", curve),
                                            oversampling=2, order=2),
        AntiderivativeTanhSaturator("tanh", input="in1", oversampling=2, bias="bias"),
        AntiderivativeTanhSaturatorLinearTwin("twin", input="in1", oversampling=2),
        edges,
        BellEqualizer("bell", input="in1", frequency_hz="f", gain_db="g", q="q"),
        DefinedLatencyPad("pad", input="in1", pad_samples=math.exp(1.0), oversampling=2),
        latency.pad("one", "pad_one", "in1"), latency.pad("two", "pad_two", "in1"),
        DrumEnvelope("env", hit="in1", mode="mode", attack_ms="a", decay_ms="d"),
        upsampler, ControlsAtTheUpsampledSteps("controls", upsampler=upsampler, controls={"cutoff": "c"}),
        HalfbandDownsampler("down", first="x1", second="x2"),
        HalfbandLinearPhaseDownsampler("fir", first="x1", second="x2"),
        HistoriesStartAtTheirTargets("start", targets={"h": "in1"}),
        KneeSoftClip("knee", input="in1", knee=math.sin(1.0)),
        LedDrivenPhotocell("cell", drive_current_amps="in1", attack_ms="3", release_ms="50", law_scale_ohms=math.exp(9),
                           law_exponent=math.log(3), law_floor_ohms=100.0, darkest_current_amps=math.exp(-15),
                           release_from_amps=math.exp(-5), release_to_amps=math.exp(-15)),
        LfsrMetallicNoise("metal", hit="in1", tune_hz="tune", pattern="pattern"),
        PitchModulator("pitch", hit="in1", shape="shape", amount="amount", decay_ms="d", rate_hz="r", seed="1"),
        SeededWhiteNoise("noise", seed="1"),
        sidechain_style_pump.SidechainStylePump("pump", live_beat_position="in1", following_live="0", bpm="120",
                                                division_beats="1", depth="1", attack_ms="6", release_fraction="0.5",
                                                curve="0.5"),
        TapeStyleEcho("echo", left_input="in1", right_input="in1", time_ms="t", feedback="fb", loop_lowpass_hz="lp",
                      loop_highpass_hz="hp", saturation_gain="sat", wow_cents="w", flutter_cents="fl",
                      stop_pressed="stop", diffusion="diff", longest_time_ms=6000.0, right_lag_ms=math.pi,
                      rounds_kept=3),
        ZeroDelayAllpassCascade("cascade", input="in1", stages=[FirstOrderAllpassStage("1000"),
                                                                FirstOrderAllpassStage("2000")],
                                feedback="fb", loop_limit=math.sqrt(2) * math.cos(0.3)),
        ZeroDelayOnePoleFilter("onepole", input="in1", cutoff_hz="f"),
        ZeroDelayStateVariableFilter("svf", input="in1", cutoff_hz="f", q="q"),
        zero_delay_ladder_filter.ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="f", resonance="r"),
        Buchla259ModulationOscillator("modosc", frequency_hz="f", wave="w", oversampling=2),
        Buchla259PrincipalOscillator("principal", frequency_hz="f", frequency_modulation_hz="fm", oversampling=2),
        Buchla292LowPassGateChannel("lpg", input="in1", led_current_amps="led", attack_ms="a", decay_ms="d",
                                    mode="m", resonance="r"),
        ltc1060_mf10_section.Ltc1060Mf10Section("sc", input_volts="in1", clock_hz="c", damping="q", hold="0",
                                                clock_feedthrough="0", lowpass_gain="1", bandpass_gain="0",
                                                highpass_gain="0"),
        moog, mutron]
    texts = {}
    for block in blocks:
        # the latency as a device sums it into its Defined Latency (overview.md), and the block's code
        parts = [repr(generated_number(block.latency_samples)), "\n".join(block.functions().values()),
                 block.declarations()]
        try:
            parts.append(block.statements())
        except NotImplementedError:
            pass
        texts[f"{type(block).__name__} {block.instance_name}"] = "\n".join(parts)
    texts["timbre"] = "\n".join(["\n".join(timbre.functions().values()), timbre.declarations(),
                                 timbre.point_statements("pt", "sine"), timbre.output_statements("pt"),
                                 timbre.remember_statements("pt"), repr(timbre.output_peak_volts)])
    texts["scripts"] = "\n".join([ltc1060_mf10_section.response_script_code(), moog.response_script_code(),
                                  mutron.response_script_code(), sidechain_style_pump.response_script_code(),
                                  zero_delay_ladder_filter.response_script_code()])
    return texts


def probe(mode):
    """{output: sha256} with the maths library perturbed by `mode` ("none": the machine's own), and every output
    held to the rule (check_generated_text)."""
    if mode != "none":
        install_perturbed_libm(mode)
    import contextlib
    import io
    import shutil
    import tempfile
    sys.path[:0] = [KIT_ROOT, TESTS]
    from twosl_dsp.generated_numbers import check_generated_text
    import fixture_device
    digests = {}
    for name, text in every_block_text().items():
        check_generated_text(text, name)
        digests[name] = hashlib.sha256(text.encode()).hexdigest()
    root = tempfile.mkdtemp(prefix="kit-generated-numbers-")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fixture_device.build_fixture_device(root)
        for directory, _, names in os.walk(root):
            for name in names:
                path = os.path.join(directory, name)
                with open(path, "rb") as handle:
                    digests[os.path.relpath(path, root)] = hashlib.sha256(handle.read()).hexdigest()
    finally:
        shutil.rmtree(root)
    return digests


def probe_in_a_child(mode):
    finished = subprocess.run([sys.executable, os.path.abspath(__file__), "--probe", mode], capture_output=True,
                              text=True, cwd=KIT_ROOT)
    if finished.returncode != 0:
        raise AssertionError(f"the probe ({mode}) failed:\n{finished.stderr}")
    return json.loads(finished.stdout)


class GeneratedNumberTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, KIT_ROOT)

    def test_a_float_is_rounded_to_ten_significant_digits(self):
        from twosl_dsp.generated_numbers import generated_number
        self.assertEqual(generated_number(0.9497427837050028), 0.9497427837)
        self.assertEqual(generated_number(0.9497427837050002), 0.9497427837)
        self.assertEqual(repr(generated_number(4.3583271392608154e-05)), "4.358327139e-05")
        self.assertEqual(generated_number(0.5000000000000001), 0.5)
        self.assertEqual(generated_number(3), 3.0)

    def test_a_fraction_keeps_every_digit_and_the_check_lets_it_through(self):
        from twosl_dsp.generated_numbers import check_generated_text, generated_number
        written = generated_number(Fraction(1, 24))
        self.assertEqual(written, 1 / 24)
        check_generated_text(f"y = {written!r} * x - {generated_number(-Fraction(7, 30))!r};", "a fraction")

    def test_anything_else_fails(self):
        from twosl_dsp.build_error import BuildError
        from twosl_dsp.generated_numbers import generated_number
        for bad in (math.inf, math.nan, "0.5", True, None):
            with self.assertRaises(BuildError, msg=bad):
                generated_number(bad)

    def test_the_check_fails_a_float_that_skipped_the_rule_and_says_where(self):
        from twosl_dsp.build_error import BuildError
        from twosl_dsp.generated_numbers import check_generated_text
        check_generated_text("a = 0.9497427837 * b + 52.0 - 1e-05; // 2.6.1, 0x1.921fb54442d18p+1, stage_12", "fine")
        for text in ("a = 0.9497427837050028 * b;", "x = 4.3583271392608154e-05;", "[0.30000000000000004]"):
            with self.assertRaises(BuildError, msg=text) as failure:
                check_generated_text(text, "some.maxpat")
            self.assertIn("some.maxpat", str(failure.exception))
            self.assertIn("generated_number", str(failure.exception))

    def test_a_number_the_live_parameter_lock_holds_is_let_through(self):
        from twosl_dsp.build_error import BuildError
        from twosl_dsp.generated_numbers import check_generated_text, literals_held_by_the_lock
        held = literals_held_by_the_lock('{"name": "LFO Rate", "minimum": 0.016666666666666666, "maximum": 3600.0}')
        check_generated_text('"parameter_mmin": 0.016666666666666666', "patch", held)
        with self.assertRaises(BuildError):
            check_generated_text('"parameter_mmin": 0.016666666666666666', "patch")

    def test_every_block_and_the_fixture_build_are_the_same_whatever_the_maths_library_rounds(self):
        own = probe_in_a_child("none")
        self.assertGreater(len(own), 35)
        for mode in ("up1", "down1", "up4", "down4", "random4", "random16"):
            perturbed = probe_in_a_child(mode)
            self.assertEqual(sorted(perturbed), sorted(own), mode)
            differing = [name for name in own if perturbed[name] != own[name]]
            self.assertEqual(differing, [], f"{mode}: these outputs follow the maths library's last bits")

    def test_the_perturbation_reaches_the_kit(self):
        # the probe's perturbation is real: unrounded, the half-band's coefficients move with it
        script = ("import sys; sys.path[:0] = [%r, %r]; import test_generated_numbers as t; t.install_perturbed_libm("
                  "'up4'); from twosl_dsp.techniques import halfband_oversampler as h; import math; "
                  "k, q = h._transition_parameters(0.04); print(repr(q))") % (KIT_ROOT, TESTS)
        moved = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=KIT_ROOT)
        own = subprocess.run([sys.executable, "-c", script.replace("t.install_perturbed_libm('up4'); ", "")],
                             capture_output=True, text=True, cwd=KIT_ROOT)
        self.assertEqual(moved.returncode, 0, moved.stderr)
        self.assertNotEqual(moved.stdout, own.stdout)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--probe"]:
        print(json.dumps(probe(sys.argv[2])))
    else:
        unittest.main(verbosity=2)
