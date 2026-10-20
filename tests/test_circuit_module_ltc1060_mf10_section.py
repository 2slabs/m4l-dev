"""The LTC1060 / MF10 section module (m4l_dev/circuit_modules/ltc1060_mf10_section.py): its claims, rendered through
our GenExpr renderer (ours, not Max's compiler), each on a small harness (tests/gen_block_harness.py) at the lowest
length that still tests it. The claims are stated in fractions of the chip's full scale: the harness feeds the section
volts (in1 x full scale) and reads its output back in full scale. Standard library only."""
import cmath
import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev import es5  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.circuit_modules.ltc1060_mf10_section import (Q_ENHANCEMENT_FITS, Ltc1060Mf10Character,  # noqa: E402
                                                          Ltc1060Mf10Section, response_script_code,
                                                          small_signal_response)
from gen_block_harness import (amplitude_at, complex_amplitude_at, frequency_by_zero_crossings,  # noqa: E402
                               harness)

SAMPLERATE = 44100.0
FULL_SCALE_VOLTS = Ltc1060Mf10Character().full_scale_volts
FEEDTHROUGH_AMPLITUDE = Ltc1060Mf10Character().clock_feedthrough_of_full_scale
OUTPUT_MIX = {"lowpass": ("1", "0", "0"), "bandpass": ("0", "1", "0"), "highpass": ("0", "0", "1")}


def section_block(name="sc", output="lowpass", **arguments):
    lowpass, bandpass, highpass = OUTPUT_MIX[output]
    return Ltc1060Mf10Section(name, input_volts=f"in1 * {FULL_SCALE_VOLTS!r}", clock_hz="cutoff * 100",
                              damping="damping", hold="hold", clock_feedthrough="feedthrough", lowpass_gain=lowpass,
                              bandpass_gain=bandpass, highpass_gain=highpass, **arguments)


def section(output="lowpass", divided=False, **params):
    """A harness around one section (and, `divided`, a second one divided from it). Params: cutoff, damping,
    hold, feedthrough (and cutoff_2, division). Outputs: out, ticked (, the second's out, ticked)."""
    params = dict({"cutoff": 1000.0, "damping": 1.0, "hold": 0.0, "feedthrough": 0.0}, **params)
    lowpass, bandpass, highpass = OUTPUT_MIX[output]
    volts = f"in1 * {FULL_SCALE_VOLTS!r}"
    blocks = [Ltc1060Mf10Section("sc", input_volts=volts, clock_hz="cutoff * 100", damping="damping", hold="hold",
                                 clock_feedthrough="feedthrough", lowpass_gain=lowpass, bandpass_gain=bandpass,
                                 highpass_gain=highpass)]
    outputs = [f"sc_out / {FULL_SCALE_VOLTS!r}", "sc_ticked"]
    if divided:
        params = dict({"cutoff_2": 1000.0, "division": 2.0}, **params)
        blocks.append(Ltc1060Mf10Section("sd", input_volts=volts, clock_hz="cutoff_2 * 100", damping="damping",
                                         hold="hold", clock_feedthrough="feedthrough", lowpass_gain=lowpass,
                                         bandpass_gain=bandpass, highpass_gain=highpass,
                                         divided_from=blocks[0], division="division"))
        outputs += [f"sd_out / {FULL_SCALE_VOLTS!r}", "sd_ticked"]
    return harness(blocks, params, outputs, samplerate=SAMPLERATE)


def sine(frequency, samples, amplitude=0.05):
    return [amplitude * math.sin(2 * math.pi * frequency * i / SAMPLERATE) for i in range(samples)]


def kicked(samples):
    return [0.02] * 4 + [0.0] * (samples - 4)


def rms(signal):
    return math.sqrt(sum(v * v for v in signal) / len(signal))


def db(ratio):
    return 20 * math.log10(ratio)


class Ltc1060Mf10SectionTests(unittest.TestCase):
    def test_it_sings_at_the_clock_over_the_ratio(self):
        # just past oscillation, the section rings at clock / 100 = the cutoff, at a low and a high clock
        for cutoff in (300.0, 3000.0):
            out = section("bandpass", cutoff=cutoff, damping=-0.01).run(8820, [kicked(8820)])[0]
            measured = frequency_by_zero_crossings(out[4410:], SAMPLERATE)
            self.assertAlmostEqual(measured / cutoff, 1.0, delta=0.005, msg=f"{cutoff} Hz rings at {measured:.1f}")

    def test_small_signals_follow_the_display_response(self):
        for output, index in (("lowpass", 0), ("bandpass", 1), ("highpass", 2)):
            for frequency in (250.0, 1000.0, 4000.0):
                signal = sine(frequency, 4410)
                out = section(output, cutoff=1000.0, damping=0.7).run(4410, [signal])[0]
                measured = db(amplitude_at(out[2205:], frequency, SAMPLERATE) / 0.05)
                expected = db(abs(small_signal_response(frequency, 100 * 1000.0, 0.7)[index]))
                self.assertAlmostEqual(measured, expected, delta=0.3, msg=f"{output} at {frequency} Hz")

    def test_the_display_script_is_the_same_response(self):
        script = response_script_code()
        for frequency, cutoff, damping, ratio in ((100.0, 700.0, 0.3, 100), (700.0, 700.0, 0.05, 100),
                                                  (15000.0, 20000.0, 1.5, 50)):
            pins = small_signal_response(frequency, ratio * cutoff, damping, ratio)
            for pin, value in zip(("lp", "bp", "hp"), pins):
                for part, expected in (("Re", value.real), ("Im", value.imag)):
                    got = float(es5.evaluate(script + f"\nltc1060Mf10SectionResponse({frequency}, {ratio * cutoff}, {damping}, "
                                                      f"{ratio}).{pin}{part}"))
                    self.assertAlmostEqual(got, expected, places=9, msg=f"{pin}{part} at {frequency} Hz")

    def test_the_whistle_is_the_clock(self):
        # silence in, feedthrough at the datasheets' 10 mV p-p: a square at 100 x the cutoff (6 kHz at 60 Hz), its
        # fundamental 4/pi of the half-swing, times the 4-point polyBLEP's roll-off (its kernel is the cubic B-spline:
        # sinc^4); nothing at 50 x
        out = section(cutoff=60.0, feedthrough=1.0).run(4410, [[0.0] * 4410])[0]
        roll_off = (math.sin(math.pi * 6000 / SAMPLERATE) / (math.pi * 6000 / SAMPLERATE)) ** 4
        self.assertAlmostEqual(amplitude_at(out[441:], 6000.0, SAMPLERATE)
                               / (4 / math.pi * FEEDTHROUGH_AMPLITUDE * roll_off), 1.0, delta=0.03)
        self.assertLess(amplitude_at(out[441:], 3000.0, SAMPLERATE), FEEDTHROUGH_AMPLITUDE * 0.01)

    def test_no_whistle_once_the_clock_leaves_the_band(self):
        out = section(cutoff=600.0, feedthrough=1.0).run(4410, [[0.0] * 4410])[0]
        self.assertLess(max(abs(v) for v in out), 1e-12)

    def test_two_free_sections_beat_at_their_clock_difference(self):
        program = section(divided=True, cutoff=60.0, cutoff_2=61.0, division=0.0, feedthrough=1.0)
        first, _, second, _ = program.run(8820, [[0.0] * 8820])
        both = [a + b for a, b in zip(first, second)]
        for clock in (6000.0, 6100.0):
            self.assertGreater(amplitude_at(both[441:], clock, SAMPLERATE), FEEDTHROUGH_AMPLITUDE)
        # the beat: the summed whistle's level over each millisecond swings with the 100 Hz difference
        frames = [rms(both[start:start + 44]) for start in range(441, 8820 - 44, 44)]
        self.assertLess(min(frames), 0.35 * max(frames))

    def test_a_divided_section_ticks_on_every_division_th_tick(self):
        for division in (2.0, 1.5, 16.0):
            program = section(divided=True, cutoff=150.0, division=division)
            _, master_ticked, _, divided_ticked = program.run(4410, [[0.0] * 4410])
            master_ticks = [i for i, ticked in enumerate(master_ticked) if ticked]
            divided_ticks = [i for i, ticked in enumerate(divided_ticked) if ticked]
            self.assertAlmostEqual(len(divided_ticks), len(master_ticks) / division, delta=1)
            if division == 2.0:
                self.assertTrue(set(divided_ticks) <= set(master_ticks), "phase-locked: on the master's ticks")

    def test_past_oscillation_it_holds_steady_under_the_rail(self):
        for cutoff in (1000.0, 10000.0):
            out = section("bandpass", cutoff=cutoff, damping=-0.2).run(8820, [kicked(8820)])[0]
            # the integrators round off into the rail at 1; the band-limited edges overshoot it a little
            self.assertLessEqual(max(abs(v) for v in out), 1.3)
            self.assertAlmostEqual(db(rms(out[4410:6615]) / rms(out[6615:])), 0.0, delta=0.5)
            self.assertGreater(rms(out[6615:]), 0.3)

    def test_the_chips_q_enhancement_makes_it_sing_only_near_the_top(self):
        # damping 0.008: rings out at 300 Hz (a 30 kHz clock), sings at 12 kHz (1.2 MHz)
        low = section("bandpass", cutoff=300.0, damping=0.008).run(17640, [kicked(17640)])[0]
        self.assertLess(rms(low[-2205:]), 0.25 * rms(low[2205:4410]))
        high = section("bandpass", cutoff=12000.0, damping=0.008).run(17640, [kicked(17640)])[0]
        self.assertGreater(rms(high[-2205:]), 0.3)

    def test_the_q_enhancement_rings_down_at_the_fitted_laws_damping(self):
        # a ring at 12 kHz (1.2 MHz clock) decays per tick by sqrt(1 - F q'), q' = q - A exp(-a / f_clock): measured
        # over two 10 ms windows, against the law (and far from no enhancement: 7.5 and 18.9 nepers)
        amplitude, settling_clock_hz = Q_ENHANCEMENT_FITS[(3, 5.0, 100)]
        tick_coefficient = 2 * math.sin(math.pi / 100)
        for damping, without_enhancement in ((0.02, 7.54), (0.05, 18.88)):
            out = section("bandpass", cutoff=12000.0, damping=damping).run(2205, [kicked(2205)])[0]
            nepers_per_10_ms = math.log(rms(out[441:882]) / rms(out[882:1323]))
            enhanced = damping - amplitude * math.exp(-settling_clock_hz / 1.2e6)
            predicted = -1.2e6 * 0.5 * math.log(1 - tick_coefficient * enhanced) * 0.01
            self.assertAlmostEqual(nepers_per_10_ms, predicted, delta=0.01 * predicted)
            self.assertLess(nepers_per_10_ms, 0.75 * without_enhancement)

    def test_the_q_enhancement_fits_are_the_reference_readings(self):
        # Q_ENHANCEMENT_FITS is references/circuits/ltc1060-q-error-graphs/q-error-graphs.json's fits, to 4 digits
        reading = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "circuits",
                               "ltc1060-q-error-graphs", "q-error-graphs.json")
        with open(reading) as handle:
            graphs = json.load(handle)["graphs"]
        fitted = {}
        for graph in graphs:
            for fit in graph["fits"]:
                key = (int(graph["mode"][0]), float(fit["supply"].strip("±V")), fit["clock_ratio"])
                fitted[key] = (fit["amplitude"], fit["settling_clock_hz"])
        self.assertEqual(set(fitted), set(Q_ENHANCEMENT_FITS))
        for key, (amplitude, settling_clock_hz) in fitted.items():
            self.assertAlmostEqual(Q_ENHANCEMENT_FITS[key][0] / amplitude, 1, delta=5e-4, msg=str(key))
            self.assertAlmostEqual(Q_ENHANCEMENT_FITS[key][1] / settling_clock_hz, 1, delta=5e-4, msg=str(key))

    def test_its_latency_is_the_input_and_the_edges_three_samples(self):
        # latency_samples: one for the input's pre-emphasis, two for the edges' look-ahead; rendered: a 100 Hz sine
        # through the lowpass at 15 kHz comes out that many samples late, past the response's own phase
        self.assertEqual(section_block().latency_samples, 3)
        signal = sine(100.0, 8820, 0.05)
        out = section("lowpass", cutoff=15000.0, damping=1.0).run(8820, [signal])[0]
        ratio = complex_amplitude_at(out[4410:], 100.0, SAMPLERATE) / complex_amplitude_at(signal[4410:], 100.0,
                                                                                          SAMPLERATE)
        response = small_signal_response(100.0, 100 * 15000.0, 1.0)[0]
        samples_late = -(cmath.phase(ratio) - cmath.phase(response)) * SAMPLERATE / (2 * math.pi * 100.0)
        self.assertAlmostEqual(samples_late, section_block().latency_samples, delta=0.02)

    def test_hold_freezes_lowpass_and_bandpass(self):
        for output in ("lowpass", "bandpass"):
            program = section(output, cutoff=200.0, damping=0.7)
            signal = sine(150.0, 4410, 0.3)
            program.run(2205, [signal[:2205]])
            program.set_param("hold", 1.0)
            held = program.run(2205, [signal[2205:]])[0]
            frozen = held[section_block().latency_samples + 2:]
            self.assertLess(max(frozen) - min(frozen), 1e-9, f"{output} holds its last sample")

    def test_the_chips_own_images_stay_and_the_hosts_folds_go(self):
        # a 100 Hz sine through low-pass 100 Hz: the clock (10 kHz) is in band, its images at 10 kHz +- 100 Hz are
        # the chip's (zero-order hold: 100 / 9900 of the signal, -39.9 dB; the band-limiting takes ~3 dB at 10 kHz)
        out = section(cutoff=100.0, damping=1.414).run(8820, [sine(100.0, 8820)])[0]
        signal = amplitude_at(out[4410:], 100.0, SAMPLERATE)
        image = db(amplitude_at(out[4410:], 9900.0, SAMPLERATE) / signal)
        self.assertTrue(-45 < image < -37, f"the chip's image at 9.9 kHz: {image:.1f} dB")
        # 1 kHz through low-pass 300 Hz: the clock is 30 kHz, its images (29 and 31 kHz) are ultrasonic; read
        # naively they fold to 15.1 and 13.1 kHz at -30 dB (research 2026-10-19)
        out = section(cutoff=300.0, damping=1.0).run(8820, [sine(1000.0, 8820)])[0]
        signal = amplitude_at(out[4410:], 1000.0, SAMPLERATE)
        for fold in (15100.0, 13100.0):
            self.assertLess(db(amplitude_at(out[4410:], fold, SAMPLERATE) / signal), -45)

    def test_the_block_says_what_it_is_given_wrong(self):
        with self.assertRaises(BuildError):
            Ltc1060Mf10Section("sc", input_volts="in1", clock_hz="100", damping="1", hold="0", clock_feedthrough="0",
                               lowpass_gain="1", bandpass_gain="0", highpass_gain="0", clock_ratio=75)
        with self.assertRaises(BuildError):
            Ltc1060Mf10Section("sc", input_volts="in1", clock_hz="100", damping="1", hold="0", clock_feedthrough="0",
                               lowpass_gain="1", bandpass_gain="0", highpass_gain="0", division="2")
        with self.assertRaises(BuildError):
            Ltc1060Mf10Section("sc", input_volts="in1", clock_hz="100", damping="1", hold="0", clock_feedthrough="0",
                               lowpass_gain="1", bandpass_gain="0", highpass_gain="0", character=0.8)
        with self.assertRaises(BuildError):
            Ltc1060Mf10Section("sc", input_volts="in1", clock_hz="100", damping="1", hold="0", clock_feedthrough="0",
                               lowpass_gain="1", bandpass_gain="0", highpass_gain="0",
                               character=Ltc1060Mf10Character(supply_volts=6.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
