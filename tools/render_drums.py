#!/usr/bin/env python3
"""Render 2sl drums' presets offline and measure their loudness, to match the presets' Volume.

  python3 src/2sl-drums.py            # first: writes dist/2sl-drums-render.json (what each preset sends)
  python3 tools/render_drums.py       # renders every preset: dist/renders/<preset>.wav, and a loudness table

Every preset plays the Init pattern (P1; presets are kit sounds), from the device's own brain
(devices/2sl-drums/2sl-drums.js, run in node by tools/drums_hits.js); the sound from the device's own gen~ code (src/2sl_drums_dsp.py), run by tools/genexpr.py
(our GenExpr subset, not Max's compiler: close to what Max does, not proven identical). Params change between
64-sample blocks, as gen~'s do. Each preset plays 4 bars at 120 bpm with Volume at 0 dB; the table gives the
Volume that puts its RMS level at the Init preset's.
"""
import importlib
import json
import math
import os
import struct
import subprocess
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "tools")]
genexpr = importlib.import_module("genexpr")
dsp = importlib.import_module("2sl_drums_dsp")
NODE = os.environ.get("NODE", "node")
SAMPLE_RATE = 44100.0
BLOCK = 64
TEMPO = 120.0
BARS = 4


def init_pattern_hits():
    """What the brain sends gen~ on every 16th of BARS bars of the Init pattern."""
    request = json.dumps({"bars": BARS, "tempo": TEMPO, "seed": 1})
    result = subprocess.run([NODE, os.path.join(ROOT, "tools", "drums_hits.js"), request], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"render_drums.py: drums_hits.js failed:\n{result.stderr}")
    return json.loads(result.stdout)


def render(preset, sixteenths):
    program = genexpr.GenProgram(dsp.KIT, 0, 2, samplerate=SAMPLE_RATE, seed=1)
    for name, value in preset["gen"].items():
        program.set_param(name, 0.0 if name == "volume" else value)     # measured at 0 dB
    samples_per_sixteenth = SAMPLE_RATE * 60 / TEMPO / 4
    total = int(samples_per_sixteenth * 16 * BARS + SAMPLE_RATE)        # plus a second of tails
    left = []
    rendered = 0
    for entry in sixteenths + [{"sixteenth": None, "messages": []}]:
        until = total if entry["sixteenth"] is None else int(round(entry["sixteenth"] * samples_per_sixteenth))
        while rendered < until:
            count = min(BLOCK, until - rendered)
            left.extend(program.run(count)[0])
            rendered += count
        for name, value in entry["messages"]:
            program.set_param(name, value)
    return left


def loudness(samples):
    peak = max(abs(x) for x in samples)
    rms = math.sqrt(sum(x * x for x in samples) / len(samples))
    if not all(math.isfinite(x) for x in samples):
        raise SystemExit("render_drums.py: the render has non-finite samples")
    return 20 * math.log10(max(peak, 1e-9)), 20 * math.log10(max(rms, 1e-9))


def write_wav(path, samples):
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(SAMPLE_RATE))
        handle.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x)) * 32767)) for x in samples))


if __name__ == "__main__":
    render_list = os.path.join(ROOT, "dist", "2sl-drums-render.json")
    if not os.path.isfile(render_list):
        raise SystemExit("render_drums.py: dist/2sl-drums-render.json is missing: run python3 src/2sl-drums.py first")
    presets = json.load(open(render_list))
    sixteenths = init_pattern_hits()
    os.makedirs(os.path.join(ROOT, "dist", "renders"), exist_ok=True)
    results = []
    for preset in presets:
        samples = render(preset, sixteenths)
        write_wav(os.path.join(ROOT, "dist", "renders", preset["name"].replace(" ", "-") + ".wav"), samples)
        results.append((preset["name"], *loudness(samples), preset["gen"].get("volume", 0)))
    reference_rms = results[0][2]
    print("4 bars of the Init pattern at 120 bpm, Volume 0 dB, mono. Fixed: pattern, tempo, seed. Varies: the preset. dBFS levels; "
          "'match' = the Volume that puts its RMS at the Init preset's; 'now' = its Volume in the presets file")
    print(f"{'preset':<14}{'peak':>8}{'rms':>8}{'match':>8}{'now':>8}")
    for name, peak, rms, now in results:
        print(f"{name:<14}{peak:8.1f}{rms:8.1f}{reference_rms - rms:8.1f}{now:8.1f}")
