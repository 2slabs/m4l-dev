#!/usr/bin/env python3
"""2sl stab: a dub techno chord stab instrument for Max for Live.

  python3 src/2sl-stab.py   # writes src/2sl-stab.maxpat, devices/2sl-stab/2sl-stab.amxd (for development,
                            # scripts alongside) and dist/2sl-stab-<version>.amxd (frozen: one file to share)

Signal flow (from the research in devices/2sl-stab/README.md):
  MIDI -> chord memory (js) -> mc.noteallocator~ (16 voices)
       -> mc.gen~ voice: detuned saw + pulse + noise, 24 dB ladder low-pass with
          envelope / key / velocity, analog-style ADSR
       -> mono sum -> gen~ FX: tape drive, then a stereo dub delay synced to Live's tempo
          with high- and low-pass *in the feedback loop* (each repeat darker and thinner),
          saturation and diffusion in the loop, wow/flutter, slightly offset L/R times
       -> plugout~
"""
import json, os, subprocess, sys

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---- DSP (genexpr) -------------------------------------------------------------------

VOICE = r"""
// One voice. in1: frequency (Hz). in2: gate = velocity 0..1, 0 = release. in3: the LFO (-1..1, shared).
// Two oscillators, a sub and noise into a mixer, like the Juno / Jupiter / Prophet voices of the time.
// (gen requires functions before everything else, declarations included.)
// polyBLEP: removes the aliasing from a saw's jump
blep(t, dt) {
	if (t < dt) {
		x = t / dt;
		return x + x - x * x - 1;
	} else if (t > 1 - dt) {
		x = (t - 1) / dt;
		return x * x + x + x + 1;
	}
	return 0;
}

Param wave1(0, min=0, max=2);           // DCO 1: 0 saw, 1 pulse, 2 saw + pulse
Param oct1(0, min=-1, max=1);           // 16' 8' 4'
Param pw(0.7, min=0.5, max=0.95);       // pulse width (both DCOs)
Param wave2(0, min=0, max=2);           // DCO 2: 0 saw, 1 pulse, 2 triangle
Param oct2(0, min=-1, max=1);
Param semi(0, min=-12, max=12);         // DCO 2 interval: 7 = a fifth up
Param fine(10, min=0, max=50);          // DCO 2 detune, cents
Param lvl1(0.8, min=0, max=1);          // mixer
Param lvl2(0.8, min=0, max=1);
Param sublvl(0, min=0, max=1);          // square, an octave below DCO 1
Param noiseamt(0.08, min=0, max=1);
Param pwmamt(0, min=0, max=1);          // LFO -> pulse width
Param lfofilt(0, min=0, max=1);         // LFO -> cutoff, up to +-3 octaves
Param vibamt(0, min=0, max=1);          // LFO -> pitch, up to +-50 cents
Param cutoff(700, min=40, max=12000);   // Hz
Param reso(0.3, min=0, max=1);
Param envamt(0.5, min=0, max=1);        // envelope -> cutoff, up to +6 octaves
Param keytrack(0.5, min=0, max=1);
Param velfilt(0.5, min=0, max=1);       // velocity -> envelope amount
Param atk(2, min=0.5, max=4000);        // ms
Param dec(260, min=5, max=6000);        // ms to -40 dB
Param sus(0, min=0, max=1);
Param rel(240, min=5, max=6000);        // ms to -40 dB
Param level(0.22, min=0, max=1);
Param tonemac(0, min=-1, max=1);        // Play page Tone: cutoff and envelope up or down
Param lenmac(0, min=-1, max=1);         // Play page Length: decay and release x0.25..x4
Param hush(0, min=0, max=1);            // Stop: fade out now, whatever the release

History env(0), stage(0), lastgate(0), velo(0), lastfreq(0);
History ph1(0), ph2(0), phs(0), s1(0), s2(0), s3(0), s4(0);

lfo = in3;
note = max(in1, 1);                    // the played pitch (vibrato is applied on top)
freq = note * pow(2, vibamt * lfo * 0.5 / 12);
gatein = in2;
sr = samplerate;

// gate edges; a new velocity or pitch while held = a stolen voice: start again
if (gatein > 0 && (lastgate <= 0 || gatein != lastgate || note != lastfreq)) {
	stage = 1;
	velo = gatein;
} else if (gatein <= 0 && lastgate > 0) {
	stage = 3;
}
lastgate = gatein;
lastfreq = note;

if (hush > 0) {
	stage = 0;
	env = env * 0.996;   // about 20 ms to silence
}

// analog-style ADSR: the attack aims past 1, decay and release are exponential
stretch = pow(4, lenmac);
ka = 1 - exp(-1.47 / max(atk * 0.001 * sr, 1));
kd = 1 - exp(-4.6 / max(dec * stretch * 0.001 * sr, 1));
kr = 1 - exp(-4.6 / max(rel * stretch * 0.001 * sr, 1));
if (stage == 1) {
	env = env + (1.3 - env) * ka;
	if (env >= 1) {
		env = 1;
		stage = 2;
	}
} else if (stage == 2) {
	env = env + (sus - env) * kd;
} else if (stage == 3) {
	env = env + (0 - env) * kr;
	if (env < 0.0005) {
		env = 0;
		stage = 0;
	}
}

width = clamp(pw + pwmamt * 0.35 * lfo, 0.05, 0.95);

// DCO 1
f1 = freq * pow(2, oct1);
dt1 = f1 / sr;
ph1 = wrap(ph1 + dt1, 0, 1);
saw1 = 2 * ph1 - 1 - blep(ph1, dt1);
p1b = wrap(ph1 + width, 0, 1);
pulse1 = saw1 - (2 * p1b - 1 - blep(p1b, dt1));
o1 = wave1 < 0.5 ? saw1 : (wave1 < 1.5 ? pulse1 : (saw1 + pulse1) * 0.6);

// DCO 2
f2 = freq * pow(2, oct2 + semi / 12 + fine / 1200);
dt2 = f2 / sr;
ph2 = wrap(ph2 + dt2, 0, 1);
saw2 = 2 * ph2 - 1 - blep(ph2, dt2);
p2b = wrap(ph2 + width, 0, 1);
pulse2 = saw2 - (2 * p2b - 1 - blep(p2b, dt2));
tri2 = 2 * abs(2 * ph2 - 1) - 1;
o2 = wave2 < 0.5 ? saw2 : (wave2 < 1.5 ? pulse2 : tri2);

// sub: a square an octave below DCO 1
dts = dt1 * 0.5;
phs = wrap(phs + dts, 0, 1);
subosc = (phs < 0.5 ? 1 : -1) + blep(phs, dts) - blep(wrap(phs + 0.5, 0, 1), dts);

osc = (o1 * lvl1 + o2 * lvl2 + subosc * sublvl) * 0.5 + noise() * noiseamt * 0.4;

// 4-pole ladder low-pass with saturated feedback
vel_env = clamp(envamt + 0.25 * tonemac, 0, 1) * (1 - velfilt + velfilt * velo);
fc = cutoff * pow(2, 2.5 * tonemac) * pow(2, keytrack * log2(note / 261.63)) * pow(2, 6 * vel_env * env)
	* pow(2, 3 * lfofilt * lfo);
fc = clamp(fc, 20, sr * 0.45);
g = 1 - exp(-twopi * fc / sr);
k = reso * 3.8;
x0 = tanh(osc - k * s4);
s1 = s1 + g * (x0 - s1);
s2 = s2 + g * (s1 - s2);
s3 = s3 + g * (s2 - s3);
s4 = s4 + g * (s3 - s4);
y = s4 * (1 + k * 0.4);

out1 = y * env * (0.35 + 0.65 * velo) * level;
"""

FX = r"""
// in1: the voices, mono. in2: Live's beat ramp (plugphasor~). out1/out2: left/right.
// soft clip: clean below 0.8, rounding off above (gen needs functions first)
sclip(v) {
	a = abs(v);
	y = v;
	if (a > 0.8) {
		y = (v < 0 ? -1 : 1) * (0.8 + 0.2 * tanh((a - 0.8) / 0.2));
	}
	return y;
}

// The echo is only for throws: silent until Dub, Throw or Freeze feeds it.
Param drive(0.25, min=0, max=1);        // tape saturation
Param dtime(363, min=20, max=1900);     // ms (Live's tempo x the Time menu)
Param dub(0, min=0, max=1);             // the dub macro: send, feedback, darker, smeared
Param throwgate(0, min=0, max=1);       // 1 while a throw is open
Param freeze(0, min=0, max=1);          // hold the loop
Param pumpdepth(0, min=0, max=1);
Param pumprate(1, min=0.25, max=4);     // ducks per beat
Param pumpatk(6, min=1, max=40);        // ms to full duck
Param pumprel(0.55, min=0.1, max=0.95); // fraction of the division to recover
Param pumpcurve(0.5, min=0, max=1);     // recovery: 0 linear .. 1 snappy
Param bpm(120, min=20, max=999);        // Live's tempo, for the pump's own clock when stopped
Param transport(0, min=0, max=1);       // 1 while Live plays: lock to its beat
Param volume(0, min=-60, max=12);       // output, dB
Param hush(0, min=0, max=1);            // Stop: empty the echo

Delay dl(200000);
Delay dr(200000);
Delay al1(2000);
Delay al2(2000);
Delay ar1(2000);
Delay ar2(2000);
History ts(363), wph(0), wph2(0), sendsm(0), fbsm(0.4), frz(0);
History lpl1(0), lpl2(0), hpl(0), lpr1(0), lpr2(0), hpr(0), lvl(0), hsm(0), ownph(0), gsm(1);

sr = samplerate;
gain = 1 + drive * 5;
x = tanh(in1 * gain) / (1 + drive * 2.2);

// what goes into the echo, and how long it rings
frz = frz + (freeze - frz) * 0.002;
target_send = max(dub * dub * 0.9, throwgate) * (1 - freeze);
sendsm = sendsm + (target_send - sendsm) * (target_send > sendsm ? 0.02 : 0.0015);
target_fb = max(0.3 + dub * 0.62, throwgate * 0.9);
fbsm = fbsm + (target_fb - fbsm) * (target_fb > fbsm ? 0.01 : 0.00004);
fb = fbsm * (1 - frz) + 1.05 * frz;
looplp = (4500 - dub * 3100) * (1 - frz) + 9000 * frz;
loophp = (90 + dub * 160) * (1 - frz) + 50 * frz;
diffuse = 0.2 + dub * 0.45;

// tape echo: time glides when it changes, wow and flutter, L/R slightly apart
ts = ts + (dtime - ts) * 0.0004;
wph = wrap(wph + 0.53 / sr, 0, 1);
wph2 = wrap(wph2 + 0.137 / sr, 0, 1);
wow = (sin(twopi * wph) * 0.6 + sin(twopi * wph2) * 0.4) * 0.0012;
tl = clamp(mstosamps(ts * 1.031 * (1 + wow)), 2, 199000);
tr = clamp(mstosamps(ts * 0.979 * (1 - 0.8 * wow)), 2, 199000);
rl = dl.read(tl, interp="cubic");
rr = dr.read(tr, interp="cubic");

// in the loop: low-pass (12 dB) and high-pass, compounding on every repeat
lpk = 1 - exp(-twopi * looplp / sr);
hpk = 1 - exp(-twopi * loophp / sr);
lpl1 = lpl1 + lpk * (rl - lpl1);
lpl2 = lpl2 + lpk * (lpl1 - lpl2);
hpl = hpl + hpk * (lpl2 - hpl);
fl = lpl2 - hpl;
lpr1 = lpr1 + lpk * (rr - lpr1);
lpr2 = lpr2 + lpk * (lpr1 - lpr2);
hpr = hpr + hpk * (lpr2 - hpr);
fr = lpr2 - hpr;

// diffusion: two allpasses per side
d1 = al1.read(373);
v1 = fl + diffuse * d1;
al1.write(v1);
fl = d1 - diffuse * v1;
d2 = al2.read(587);
v2 = fl + diffuse * d2;
al2.write(v2);
fl = d2 - diffuse * v2;
d3 = ar1.read(401);
v3 = fr + diffuse * d3;
ar1.write(v3);
fr = d3 - diffuse * v3;
d4 = ar2.read(613);
v4 = fr + diffuse * d4;
ar2.write(v4);
fr = d4 - diffuse * v4;

hsm = hsm + (hush - hsm) * 0.01;
keep = 1 - hsm;
dl.write((x * sendsm + tanh(fl * fb * 1.1) / 1.1) * keep);
dr.write((x * sendsm + tanh(fr * fb * 1.1) / 1.1) * keep);

// pump: a sidechain-style duck on every beat division. Live's beat while it plays, our own clock when
// stopped. The duck ramps in over Attack (never a jump, so no click), recovers over Release with Curve.
ownph = wrap(ownph + bpm / 60 / sr, 0, 1);
beatph = transport > 0.5 ? in2 : ownph;
ph = wrap(beatph * pumprate, 0, 1);
divms = 60000 / max(bpm, 20) / pumprate;
atkf = clamp(pumpatk / divms, 0.001, 0.3);
rl_end = max(pumprel, atkf + 0.05);
duck = 0;                              // declared out here: gen scopes variables to the block they start in
r = 0;
if (ph < atkf) {
	duck = sin(1.5707963 * ph / atkf);
} else {
	r = clamp((ph - atkf) / (rl_end - atkf), 0, 1);
	duck = pow(1 - r, 1 + pumpcurve * 3);
}
target_g = 1 - pumpdepth * duck;
gsm = gsm + (target_g - gsm) * 0.05;   // ~1 ms smoother: no steps, ever

lvl = max(abs(rl) + abs(rr), lvl * 0.9997);
out3 = lvl;
gain = dbtoa(volume) * 2;              // +6 dB over the old level; the soft clip catches overs
out1 = sclip((x + rl * 1.2 * keep) * gsm * gain);
out2 = sclip((x + rr * 1.2 * keep) * gsm * gain);
"""

# ---- patch building ----------------------------------------------------------------

boxes, lines = [], []
_n = [0]


def box(text=None, cls="newobj", rect=(0, 0, 80, 22), ins=1, outs=1, outtype=None, **extra):
    _n[0] += 1
    b = {"id": f"obj-{_n[0]}", "maxclass": cls, "numinlets": ins, "numoutlets": outs,
         "patching_rect": [float(v) for v in rect]}
    if text is not None:
        b["text"] = text
    if outs:
        b["outlettype"] = outtype or [""] * outs
    b.update(extra)
    boxes.append({"box": b})
    return b["id"]


def wire(src, dst, so=0, di=0):
    lines.append({"patchline": {"source": [src, so], "destination": [dst, di]}})


def gen_patcher(code, ins, outs):
    sub_boxes, sub_lines = [], []
    sub_boxes.append({"box": {"id": "cb", "maxclass": "codebox", "code": code.strip() + "\n",
                              "fontname": "<Monospaced>", "fontsize": 12.0, "numinlets": ins, "numoutlets": outs,
                              "outlettype": [""] * outs, "patching_rect": [20.0, 60.0, 700.0, 600.0]}})
    for i in range(ins):
        sub_boxes.append({"box": {"id": f"in{i+1}", "maxclass": "newobj", "text": f"in {i+1}", "numinlets": 0,
                                  "numoutlets": 1, "outlettype": [""], "patching_rect": [20.0 + 80 * i, 20.0, 40.0, 22.0]}})
        sub_lines.append({"patchline": {"source": [f"in{i+1}", 0], "destination": ["cb", i]}})
    for o in range(outs):
        sub_boxes.append({"box": {"id": f"out{o+1}", "maxclass": "newobj", "text": f"out {o+1}", "numinlets": 1,
                                  "numoutlets": 0, "patching_rect": [20.0 + 80 * o, 680.0, 45.0, 22.0]}})
        sub_lines.append({"patchline": {"source": ["cb", o], "destination": [f"out{o+1}", 0]}})
    return {"fileversion": 1, "appversion": {"major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1},
            "classnamespace": "dsp.gen", "rect": [100.0, 100.0, 760.0, 740.0], "boxes": sub_boxes, "lines": sub_lines}


# What Live's Info View shows when a control is hovered: parameter long name -> (title, text).
# Every visible parameter must have an entry and every entry must name a parameter (checked at build time).
# The text says what the code does; keep it short, the Info View is small.
INFO = {
    # header
    "Page": ("Page", "Shows the play, osc or shape page. Controls on hidden pages keep working."),
    "Preset": ("Preset", "Sets every control (and the machine's pattern) to a preset; tweak from there. "
               "When Live reopens a set, your saved tweaks win."),
    "Volume": ("Volume", "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs. "
               "Presets set it to match their loudness."),
    "Stop": ("Stop", "Releases every note, clears a latched chord, fades the voices out in about 20 ms, "
             "empties the echo and turns Freeze off. Runs by itself when Live's transport stops."),
    # play: chord
    "Chord": ("Chord", "What each key plays: poly plays your notes as they are; the others stack a chord on each key "
              "(minor, m7, m9, m11, sus4, fifths, dark = 0-5-8). Default minor."),
    "In Key": ("In Key", "Builds chords from the scale set in Live (its root and scale): each key snaps down into the "
               "scale and the chord stacks scale tones on it. Scales under 5 notes fall back to the fixed shapes."),
    "Tone": ("Tone", "Brighter or darker: moves the cutoff up to 2.5 octaves either way, and the filter envelope with it. "
             "-100 to +100, default 0."),
    "Length": ("Length", "Shorter or longer tails: scales Decay and Release from x0.25 (-100) to x4 (+100). Default 0."),
    "Drift": ("Drift", "Chance each chord gets another voicing of the same chord (inverted, top note dropped, "
              "middle spread, or octave added). 0 = always the same."),
    # play: machine
    "Machine": ("Machine", "With Machine on, keys don't play directly: they pick the chord the pattern plays, on 16th steps. "
                "Follows Live's transport; with Live stopped it runs on its own clock at Live's tempo."),
    "Latch": ("Latch", "With Machine on, the chord keeps playing after you let go. A new chord replaces it; Stop clears it."),
    "Pattern": ("Pattern", "Loads a 16-step stab pattern as a starting point. Click steps in the display to cycle "
                "rest, hit, accent; edited steps are saved with the set."),
    "Density": ("Density", "Each step fires by chance: hits at Density, accents at Density x1.4. Above 70%, empty "
                "offbeat 16ths also fire now and then (up to 15% at 100). Default 80%."),
    "Throws": ("Throws", "Chance each machine stab is also thrown into the echo (opens the echo for an 8th at 90% feedback)."),
    "Gate": ("Gate", "How long each machine stab is held, in 16th notes (1-4). Default 1."),
    # play: dub
    "Dub": ("Dub", "The echo amount: more sound sent in, longer feedback (30% to 92%), each repeat darker and more smeared. "
            "0 = no echo except throws."),
    "Throw": ("Throw", "Throws the sound into the echo now: opens the echo for an 8th at 90% feedback."),
    "Freeze": ("Freeze", "Holds the echo loop: nothing new goes in, and the repeats go round without fading. "
               "Stop turns it off."),
    "Echo Time": ("Echo Time", "Echo time, synced to Live's tempo: 1/16 to 1/2 (default 1/8 dotted). "
                  "Left and right run slightly apart; a change glides like tape."),
    # play: pump
    "Pump": ("Pump Depth", "How deep the output ducks on every Pump Rate step; 100% ducks to silence. "
             "Locks to Live's beat while it plays. Default 0."),
    "Pump Rate": ("Pump Rate", "How often the pump ducks: every quarter, 8th or 16th note."),
    "Pump Attack": ("Pump Attack", "Time to full duck, in ms (1-40, default 6). A ramp, never a jump, so no click."),
    "Pump Release": ("Pump Release", "How much of each step the pump takes to come back up (10% to 95%, default 55%)."),
    "Pump Curve": ("Pump Curve", "Shape of the recovery: 0 = linear, 100 = snappy (comes back fast, then eases in). Default 50."),
    # osc
    "DCO1 Wave": ("DCO 1 Wave", "DCO 1 waveform: saw, pulse (width from PW), or both mixed."),
    "DCO1 Octave": ("DCO 1 Octave", "DCO 1 footage: 16' an octave down, 8' as played, 4' an octave up. The sub follows it."),
    "PW": ("Pulse Width", "Pulse width of both DCOs' pulse waves, 50% (square) to 95% (thin). Default 70%."),
    "PWM": ("PWM", "How much the LFO moves the pulse width (up to +-35%): the Juno shimmer. Only heard on pulse waves."),
    "DCO2 Wave": ("DCO 2 Wave", "DCO 2 waveform: saw, pulse (width from PW), or triangle."),
    "DCO2 Octave": ("DCO 2 Octave", "DCO 2 footage: 16' an octave down, 8' as played, 4' an octave up."),
    "Semi": ("DCO 2 Semi", "DCO 2 interval in semitones, -12 to +12 (default 0). 7 = a fifth up."),
    "Fine": ("DCO 2 Fine", "Detunes DCO 2 upward, in cents (0-50, default 10)."),
    "OSC 1": ("OSC 1 Level", "DCO 1 level in the mixer. Default 80%."),
    "OSC 2": ("OSC 2 Level", "DCO 2 level in the mixer. Default 80%."),
    "Sub": ("Sub Level", "Level of the sub: a square wave an octave below DCO 1. Default 0."),
    "Noise": ("Noise Level", "Level of white noise in the mix (the 'chuff'). Default 8%."),
    "LFO Rate": ("LFO Rate", "Speed of the sine LFO, 0.05 to 12 Hz (default 0.5). One LFO for all voices."),
    "Vibrato": ("Vibrato", "LFO to pitch, up to +-50 cents."),
    "LFO Filter": ("LFO Filter", "LFO to cutoff, up to +-3 octaves."),
    # shape
    "Cutoff": ("Cutoff", "Low-pass cutoff (24 dB ladder), 40 Hz to 12 kHz, default 700 Hz. "
               "The envelope, key, Tone and LFO move it from here."),
    "Resonance": ("Resonance", "Filter resonance: a peak at the cutoff. Default 30%."),
    "Env Amount": ("Env Amount", "How far the envelope opens the cutoff: up to +6 octaves at 100%. Default 50%."),
    "Key Track": ("Key Track", "How much the cutoff follows the note played, around middle C; 100% = fully. Default 50%."),
    "Velocity Filter": ("Velocity Filter", "How much velocity scales Env Amount: 0 = not at all, 100% = fully. "
                        "Velocity always sets the loudness. Default 50%."),
    "Attack": ("Attack", "Envelope attack, 0.5 ms to 4 s (default 2 ms). One envelope for amp and filter."),
    "Decay": ("Decay", "Envelope decay to Sustain, 5 ms to 6 s (default 260 ms). Length scales it."),
    "Sustain": ("Sustain", "Envelope level while the note is held. Default 0: a stab."),
    "Release": ("Release", "Envelope fade after the note ends, 5 ms to 6 s (default 240 ms). Length scales it."),
    "Drive": ("Drive", "Tape saturation on the voices, before the echo. Default 25%."),
}
INFO_USED = set()


def param(cls, name, short, rect, kind, prect, **v):
    """A Live parameter (live.dial / live.menu), shown in presentation at `prect`, with its INFO text."""
    vals = {"parameter_longname": name, "parameter_shortname": short, "parameter_type": kind}
    vals.update(v)
    annotation = {}
    if name in INFO:
        title, text = INFO[name]
        INFO_USED.add(name)
        # Max saves these on the box and mirrors them in the parameter's saved values (as it writes them itself)
        annotation = {"annotation_name": title, "annotation": text}
        vals.update(parameter_annotation_name=title, parameter_info=text)
    elif not v.get("parameter_invisible"):
        raise SystemExit(f"2sl-stab.py: parameter {name!r} has no Info View text: add it to INFO")
    outs = {"live.dial": (2, ["", "float"]), "live.menu": (3, ["", "", "float"]), "live.tab": (3, ["", "", "float"]), "live.text": (2, ["", ""]), "live.numbox": (2, ["", "float"])}[cls]
    extra = {}
    if cls == "live.text":
        extra = {"text": short.lower(), "texton": short.lower(), "mode": v.pop("_mode", 1)}
        vals = {k: x for k, x in vals.items() if k != "_mode"}
        vals.update(parameter_enum=["off", "on"], parameter_mmax=1)
    return box(cls=cls, rect=rect, ins=1, outs=outs[0], outtype=outs[1], varname=name.lower().replace(" ", "_"),
               parameter_enable=1, presentation=1, presentation_rect=[float(x) for x in prect],
               saved_attribute_attributes={"valueof": vals}, **annotation, **extra)


# MIDI in -> chord memory -> voice allocation
midiin = box("midiin", rect=(30, 30, 50, 22), ins=1, outs=1, outtype=["int"])
parse = box("midiparse", rect=(30, 60, 90, 22), ins=1, outs=8)
memory = box("js 2sl-stab.js", rect=(30, 120, 110, 22), ins=2, outs=5)
fmt = box("midiformat", rect=(30, 150, 90, 22), ins=7, outs=2)
alloc = box("mc.noteallocator~ @voices 16 @steal 1", rect=(30, 190, 190, 22), ins=1, outs=6)
wire(midiin, parse)
wire(parse, memory)
wire(memory, fmt)
wire(fmt, alloc, 1, 0)

# note-on: pitch -> frequency target, velocity -> gate target; note-off: gate 0
on = box("unpack 0 0", rect=(30, 230, 80, 22), ins=1, outs=2, outtype=["int", "int"])
mtof = box("mtof", rect=(30, 260, 40, 22), outtype=["float"])
vel = box("/ 127.", rect=(120, 260, 50, 22), ins=2, outtype=["float"])
offmsg = box("t 0", rect=(200, 260, 30, 22), outtype=["int"])
tgt_f = box("mc.target", rect=(30, 300, 70, 22), ins=2, outs=2)
tgt_g = box("mc.target", rect=(120, 300, 70, 22), ins=2, outs=2)
wire(alloc, on, 0, 0)
wire(on, mtof, 0, 0)
wire(on, vel, 1, 0)
wire(mtof, tgt_f)
wire(vel, tgt_g)
wire(alloc, offmsg, 1, 0)
wire(offmsg, tgt_g)
wire(alloc, tgt_f, 5, 1)
wire(alloc, tgt_g, 5, 1)

voice = box("mc.gen~ @chans 16", rect=(30, 350, 160, 22), ins=3, outs=1, outtype=["multichannelsignal"],
            patcher=gen_patcher(VOICE, 3, 1))
lfo = box("cycle~ 0.5", rect=(220, 320, 70, 22), ins=2, outs=1, outtype=["signal"])
wire(lfo, voice, 0, 2)
wire(tgt_f, voice, 0, 0)
wire(tgt_g, voice, 0, 1)
wire(voice, alloc)  # busy state: a voice stays allocated until its release has faded

mix = box("mc.mixdown~ 1 @autogain 0", rect=(30, 390, 170, 22), ins=2, outs=1, outtype=["multichannelsignal"])
fx = box("gen~", rect=(30, 430, 120, 22), ins=2, outs=3, outtype=["signal", "signal", "signal"], patcher=gen_patcher(FX, 2, 3))
beat = box("plugphasor~", rect=(160, 400, 80, 22), ins=1, outs=2, outtype=["signal", ""])
wire(beat, fx, 0, 1)
out = box("plugout~", rect=(30, 470, 70, 22), ins=2, outs=2, outtype=["signal", "signal"])
wire(voice, mix)
wire(mix, fx)
wire(fx, out, 0, 0)
wire(fx, out, 1, 1)

# Live's tempo -> delay time in ms
thisdev = box("live.thisdevice", rect=(420, 30, 100, 22), ins=1, outs=3, outtype=["bang", "int", "int"])
tbb = box("t b b", rect=(420, 60, 40, 22), outs=2, outtype=["bang", "bang"])
# Live's Scale Mode key, for In Key
props = [("root_note", "root"), ("scale_intervals", "intervals"), ("is_playing", "playing")]
for i, (prop_name, msg) in enumerate(props):
    pm = box(cls="message", text=f"property {prop_name}", rect=(620 + 160 * i, 90, 140, 22), ins=2, outs=1)
    ob = box("live.observer", rect=(620 + 160 * i, 150, 90, 22), ins=2, outs=2)
    pp = box(f"prepend {msg}", rect=(620 + 160 * i, 180, 110, 22))
    wire(tbb, pm, 1, 0)
    wire(pm, ob)
    wire(ob, pp)
    wire(pp, memory, 0, 1)
    observers = locals().setdefault("observers", [])
    observers.append(ob)
prop = box(cls="message", text="property tempo", rect=(470, 90, 100, 22), ins=2, outs=1)
pathmsg = box(cls="message", text="path live_set", rect=(420, 90, 90, 22), ins=2, outs=1)
lpath = box("live.path", rect=(420, 120, 70, 22), ins=1, outs=3)
obs = box("live.observer", rect=(420, 150, 90, 22), ins=2, outs=2)
pak = box("pak 120. 0.75", rect=(420, 220, 90, 22), ins=2, outs=1)
ms = box("expr 60000. / $f1 * $f2", rect=(420, 250, 150, 22), ins=2, outs=1)
ptime = box("prepend dtime", rect=(420, 280, 80, 22))
wire(thisdev, tbb)
wire(tbb, prop, 1, 0)
wire(tbb, pathmsg, 0, 0)
wire(prop, obs)
wire(pathmsg, lpath)
wire(lpath, obs, 0, 1)
for ob in observers:
    wire(lpath, ob, 0, 1)

# the stab machine's clock: a 16th metro that follows Live's transport
metro = box("metro 16n @quantize 16n", rect=(30, 520, 160, 22), ins=2, outs=1, outtype=["bang"])
# run it whenever Live is playing (also if it already was when the device loaded)
wire(observers[2], metro, 0, 0)
# the machine also needs the tempo, for its own clock when Live is stopped
pbpm = box("prepend bpm", rect=(620, 250, 80, 22))
wire(obs, pbpm)
wire(pbpm, fx)
ptransport = box("prepend transport", rect=(720, 250, 110, 22))
wire(observers[2], ptransport)
wire(ptransport, fx)
ptempo = box("prepend tempo", rect=(520, 250, 90, 22))
wire(obs, ptempo)
wire(ptempo, memory, 0, 1)
trans = box("transport", rect=(30, 550, 70, 22), ins=2, outs=9)
tpack = box("pack 0 0 0", rect=(30, 580, 80, 22), ins=3, outs=1)
ptick = box("prepend tick", rect=(30, 610, 80, 22))
wire(metro, trans)
wire(trans, tpack, 0, 0)
wire(trans, tpack, 1, 1)
wire(trans, tpack, 2, 2)
wire(tpack, ptick)
wire(ptick, memory, 0, 1)

# throws: the Throw button or the machine opens the echo for an 8th
tthrow = box("t b b", rect=(250, 520, 40, 22), outs=2, outtype=["bang", "bang"])
open1 = box(cls="message", text="throwgate 1", rect=(250, 550, 55, 22), ins=2, outs=1)
close_delay = box("delay 8n", rect=(320, 550, 60, 22), ins=2, outs=1, outtype=["bang"])
close0 = box(cls="message", text="throwgate 0", rect=(320, 580, 55, 22), ins=2, outs=1)
wire(memory, tthrow, 1, 0)
wire(tthrow, close_delay, 0, 0)
wire(tthrow, open1, 1, 0)
wire(open1, fx)
wire(close_delay, close0)
wire(close0, fx)
wire(obs, pak, 0, 0)
wire(pak, ms)
wire(ms, ptime)
wire(ptime, fx)

# ---- parameters and presentation -------------------------------------------------------
# 960 x 169, on a 4 px grid: a header, then sections in three bands (display, chips/menus, dials).
# Three pages: PLAY (chord, machine, dub, pump), OSC (two DCOs, mixer, LFO), SHAPE (filter, envelope, drive).
# Everything drawn is 2sl-ui (Cozette, tokens); Live's controls are recoloured from the same tokens.
W = 960
DW, DH = 44, 48
VIEW_Y, VIEW_H, ROW_Y, DIAL_Y = 28, 64, 98, 119
PAGE_NAMES = ["play", "osc", "shape"]
PAGES = {n: [] for n in PAGE_NAMES}
VALUES = {}                                   # parameter long name -> varname (for presets)
CONTROLS = {"dial": [], "text": [], "menu": [], "tab": [], "numbox": []}
VIEWS = []


def find(b_id):
    return next(x["box"] for x in boxes if x["box"]["id"] == b_id)


def on_page(page, b_id, varname):
    if page:
        PAGES[page].append(varname)
    b = find(b_id)
    b["varname"] = varname
    if page and page != "play":
        b["hidden"] = 1
    return b_id


def view(mode, x, y, w, h, page, background=False):
    # background=True: Max's "Include in Background", so it always sits behind every other object
    extra = {"ignoreclick": 1, "background": 1} if background else {}
    b = box(cls="jsui", rect=(1500 + x, 1000 + y, w, h), ins=1, outs=1, filename="2sl-stab-view.js",
            jsarguments=[mode], presentation=1, presentation_rect=[float(x), float(y), float(w), float(h)], border=0,
            **extra)
    VIEWS.append(f"view_{mode}")
    return on_page(page, b, f"view_{mode}")


def tell(src, msg, dst, inlet=0, scale=None):
    chain = src
    if scale is not None:
        sc = box(f"* {scale}", rect=(1300, 900 + 2 * len(boxes), 50, 22), ins=2, outtype=["float"])
        wire(chain, sc)
        chain = sc
    if msg is None:
        wire(chain, dst, 0, inlet)      # the raw value (e.g. into a cycle~)
        return
    pp = box(f"prepend {msg}", rect=(1360, 900 + 2 * len(boxes), 100, 22))
    wire(chain, pp)
    wire(pp, dst, 0, inlet)


def dial(name, short, target, msg, mmin, mmax, init, unit, x, y, page, exp=1.0, scale=1.0, inlet=0, views=()):
    pid = param("live.dial", name, short, (1500 + x, 700 + y, DW, DH), 0, (x, y, DW, DH),
                parameter_mmin=float(mmin), parameter_mmax=float(mmax), parameter_initial_enable=1,
                parameter_initial=[float(init)], parameter_unitstyle=unit, parameter_exponent=float(exp))
    vn = name.lower().replace(" ", "_")
    on_page(page, pid, vn)
    VALUES[name] = vn
    CONTROLS["dial"].append(vn)
    if target is not None:
        tell(pid, msg, target, inlet, scale if scale != 1.0 else None)
    for v, vmsg in views:
        tell(pid, vmsg, v, 0, scale if scale != 1.0 else None)
    return pid


def menu(name, short, items, init, x, y, w, page):
    pid = param("live.menu", name, short, (1500 + x, 640 + y, w, 15), 2, (x, y, w, 15),
                parameter_enum=items, parameter_mmax=len(items) - 1, parameter_initial_enable=1, parameter_initial=[init])
    vn = name.lower().replace(" ", "_")
    VALUES[name] = vn
    CONTROLS["menu"].append(vn)
    return on_page(page, pid, vn)


def tabs(name, short, items, init, x, y, w, page):
    """Selector buttons (a live.tab), like the waveform and footage switches on a Jupiter or Juno."""
    pid = param("live.tab", name, short, (1500 + x, 600 + y, w, 15), 2, (x, y, w, 15),
                parameter_enum=items, parameter_mmax=len(items) - 1, parameter_initial_enable=1, parameter_initial=[init])
    vn = name.lower().replace(" ", "_")
    find(pid).update(num_lines_patching=1, num_lines_presentation=1)
    VALUES[name] = vn
    CONTROLS["tab"].append(vn)
    return on_page(page, pid, vn)


def toggle(name, short, x, y, w, h, page, mode=1):
    kw = {"parameter_initial_enable": 1, "parameter_initial": [0]} if mode == 1 else {}
    pid = param("live.text", name, short, (1500 + x, 660 + y, w, h), 2, (x, y, w, h), _mode=mode, **kw)
    vn = name.lower().replace(" ", "_")
    if mode == 1:
        VALUES[name] = vn
    CONTROLS["text"].append(vn)
    return on_page(page, pid, vn)


def stored(name, init):
    """A parameter Live stores with the set but doesn't show or automate.

    Float type with an Int unit style: Live's Int type holds only 256 values (0-255), which cut a 16-step
    bit mask down to its first 8 steps. Cycling '74's param reference gives this pattern for bigger integers."""
    pid = param("live.numbox", name, name, (1500, 1400 + (30 * len(boxes)) % 300, 60, 15), 0, (0, 0, 60, 15),
                parameter_mmin=0.0, parameter_mmax=65535.0, parameter_initial_enable=1, parameter_initial=[float(init)],
                parameter_unitstyle=0, parameter_invisible=1)
    b = find(pid)
    b["presentation"] = 0
    del b["presentation_rect"]
    return pid


# the device background, drawn first so everything sits on top of it
chrome = view("chrome", 0, 0, W, 169, None, background=True)

ui = box("js 2sl-stab-ui.js", rect=(1100, 30, 120, 22), ins=1, outs=1)
tp = box("thispatcher", rect=(1100, 60, 80, 22), ins=1, outs=2)
wire(ui, tp)
uiready = box("delay 800", rect=(1100, 0, 70, 22), ins=2, outs=1, outtype=["bang"])
readymsg = box(cls="message", text="ready", rect=(1180, 0, 50, 22), ins=2, outs=1)
wire(thisdev, uiready)
wire(uiready, readymsg)
wire(readymsg, ui)
wire(readymsg, memory, 0, 1)
colors = box("live.colors", rect=(1250, 30, 70, 22), ins=1, outs=2, outtype=["", "bang"])
thememsg = box(cls="message", text="theme", rect=(1250, 60, 45, 22), ins=2, outs=1)
wire(colors, thememsg, 1, 0)
wire(thememsg, ui)

# ---- header (all pages) ----
# the 2sl wordmark chip, a link back to 2sl.to (hover shows it, click opens it)
link = view("link", 12, 3, 56, 15, None)
page_tabs = param("live.tab", "Page", "Page", (1500, 560, 144, 15), 2, (80.0, 3.0, 144.0, 15.0),
                  parameter_enum=PAGE_NAMES, parameter_mmax=2, parameter_initial_enable=1, parameter_initial=[0])
find(page_tabs).update(num_lines_patching=1, num_lines_presentation=1, varname="page")
CONTROLS["tab"].append("page")
tell(page_tabs, "page", ui)
preset = menu("Preset", "Preset", ["-"], 0, 284, 3, 200, None)  # items set with the presets below
wire(preset, ui)
vol = param("live.numbox", "Volume", "Volume", (1500, 520, 64, 15), 0, (824.0, 3.0, 64.0, 15.0),
            parameter_mmin=-36.0, parameter_mmax=12.0, parameter_initial_enable=1, parameter_initial=[0.0],
            parameter_unitstyle=4)
find(vol).update(varname="volume")
VALUES["Volume"] = "volume"
CONTROLS["numbox"].append("volume")
tell(vol, "volume", fx)
stop_btn = param("live.text", "Stop", "Stop", (1500, 540, 48, 15), 2, (900.0, 3.0, 48.0, 15.0), _mode=0)
find(stop_btn).update(varname="stop")
CONTROLS["text"].append("stop")

# ---- Stop: release everything, fade the voices, empty the echo, Freeze off ----
stopt = box("t b b b", rect=(1100, 200, 60, 22), outs=3, outtype=["bang", "bang", "bang"])
hush1 = box(cls="message", text="hush 1", rect=(1100, 230, 50, 22), ins=2, outs=1)
hushd = box("delay 250", rect=(1160, 230, 60, 22), ins=2, outs=1, outtype=["bang"])
hush0 = box(cls="message", text="hush 0", rect=(1160, 260, 50, 22), ins=2, outs=1)
stopmsg = box(cls="message", text="stop", rect=(1230, 230, 40, 22), ins=2, outs=1)
wire(stop_btn, stopt)
wire(stopt, stopmsg, 2, 0)      # brain: notes off, latch cleared; ui: Freeze off
wire(stopmsg, memory, 0, 1)
wire(stopmsg, ui)
wire(stopt, hush1, 1, 0)
for dst in (voice, fx):
    wire(hush1, dst)
    wire(hush0, dst)
wire(stopt, hushd, 0, 0)
wire(hushd, hush0)
# Live's transport stopping runs the same stop
chg = box("change", rect=(1100, 170, 50, 22), ins=1, outs=3)
sel0 = box("sel 0", rect=(1160, 170, 40, 22), ins=2, outs=2, outtype=["bang", ""])
wire(observers[2], chg)
wire(chg, sel0)
wire(sel0, stopt)



# ================= PLAY: chord | machine | dub | pump =================
C1, C2, C3, C4 = 12, 220, 524, 732
v_chord = view("chord", C1, VIEW_Y, 184, VIEW_H, "play")
chordm = menu("Chord", "Chord", ["poly", "minor", "m7", "m9", "m11", "sus4", "fifths", "dark"], 1, C1, ROW_Y, 112, "play")
tell(chordm, "shape", memory, 1)
ink = toggle("In Key", "In Key", C1 + 116, ROW_Y, 68, 15, "play")
tell(ink, "inkey", memory, 1)
dial("Tone", "Tone", voice, "tonemac", -100, 100, 0, 5, C1, DIAL_Y, "play", scale=0.01)
dial("Length", "Length", voice, "lenmac", -100, 100, 0, 5, C1 + 70, DIAL_Y, "play", scale=0.01)
dial("Drift", "Drift", memory, "drift", 0, 100, 0, 5, C1 + 140, DIAL_Y, "play", scale=0.01, inlet=1)

v_steps = view("steps", C2, VIEW_Y, 280, VIEW_H, "play")
wire(memory, v_steps, 2, 0)
wire(v_steps, memory, 0, 1)          # clicks edit steps
wire(memory, v_chord, 3, 0)
mach = toggle("Machine", "Machine", C2, ROW_Y, 72, 15, "play")
tell(mach, "machine", memory, 1)
lat = toggle("Latch", "Latch", C2 + 76, ROW_Y, 56, 15, "play")
tell(lat, "latch", memory, 1)
pat = menu("Pattern", "Pattern", ["dub dotted", "one & three+", "offbeat chops", "skank", "deep stab", "3-3-2"],
           0, C2 + 136, ROW_Y, 144, "play")
tell(pat, "pattern", memory, 1)
dial("Density", "Density", memory, "density", 0, 100, 80, 5, C2, DIAL_Y, "play", scale=0.01, inlet=1)
dial("Throws", "Throws", memory, "throws", 0, 100, 0, 5, C2 + 56, DIAL_Y, "play", scale=0.01, inlet=1)
dial("Gate", "Gate", memory, "length", 1, 4, 1, 0, C2 + 112, DIAL_Y, "play", inlet=1)

sbits = stored("Steps", 73)      # dub dotted: hits on 1, 4, 7
abits = stored("Accents", 1)
tell(sbits, "stepbits", memory, 1)
tell(abits, "accbits", memory, 1)
bitroute = box("route stepbits accbits", rect=(1100, 120, 140, 22), ins=1, outs=3)
wire(memory, bitroute, 4, 0)
wire(bitroute, sbits, 0, 0)
wire(bitroute, abits, 1, 0)

v_echo = view("echo", C3, VIEW_Y, 184, VIEW_H, "play")
lvl_snap = box("snapshot~ 33", rect=(160, 470, 80, 22), ins=2, outs=1, outtype=["float"])
wire(fx, lvl_snap, 2, 0)
tell(lvl_snap, "level", v_echo)
throw_btn = toggle("Throw", "Throw", C3, ROW_Y, 88, 15, "play", mode=0)
wire(throw_btn, tthrow)
throwmsg = box(cls="message", text="throw", rect=(300, 520, 45, 22), ins=2, outs=1)
wire(tthrow, throwmsg, 0, 0)
wire(throwmsg, v_echo)
frz = toggle("Freeze", "Freeze", C3 + 96, ROW_Y, 88, 15, "play")
tell(frz, "freeze", fx)
tell(frz, "freeze", v_echo)
dial("Dub", "Dub", fx, "dub", 0, 100, 0, 5, C3, DIAL_Y, "play", scale=0.01, views=[(v_echo, "dub")])
divs = menu("Echo Time", "Time", ["1/16", "1/8", "1/8d", "1/4", "1/4d", "1/2"], 2, C3 + 64, DIAL_Y + 17, 64, "play")
beats = box("expr ($i1==0)*0.25 + ($i1==1)*0.5 + ($i1==2)*0.75 + ($i1==3)*1. + ($i1==4)*1.5 + ($i1==5)*2.",
            rect=(1100, 700, 400, 22), ins=1, outs=1)
wire(divs, beats)
wire(beats, pak, 0, 1)

v_pump = view("pump", C4, VIEW_Y, 216, VIEW_H, "play")
ph_snap = box("snapshot~ 33", rect=(250, 430, 80, 22), ins=2, outs=1, outtype=["float"])
wire(beat, ph_snap)
tell(ph_snap, "phase", v_pump)
prate = menu("Pump Rate", "Rate", ["1/4", "1/8", "1/16"], 0, C4, ROW_Y, 96, "play")
rmult = box("expr ($i1==0)*1. + ($i1==1)*2. + ($i1==2)*4.", rect=(1100, 760, 260, 22), ins=1, outs=1)
wire(prate, rmult)
tell(rmult, "pumprate", fx)
tell(rmult, "rate", v_pump)
dial("Pump", "Depth", fx, "pumpdepth", 0, 100, 0, 5, C4, DIAL_Y, "play", scale=0.01, views=[(v_pump, "depth")])
dial("Pump Attack", "Attack", fx, "pumpatk", 1, 40, 6, 2, C4 + 56, DIAL_Y, "play", exp=2.0, views=[(v_pump, "atk")])
dial("Pump Release", "Release", fx, "pumprel", 10, 95, 55, 5, C4 + 112, DIAL_Y, "play", scale=0.01, views=[(v_pump, "rel")])
dial("Pump Curve", "Curve", fx, "pumpcurve", 0, 100, 50, 5, C4 + 168, DIAL_Y, "play", scale=0.01, views=[(v_pump, "curve")])

# ================= OSC: DCO 1 | DCO 2 | mixer | LFO =================
O1, O2, O3, O4 = 12, 240, 468, 696
v_osc1 = view("osc1", O1, VIEW_Y, 204, VIEW_H, "osc")
w1 = tabs("DCO1 Wave", "Wave 1", ["saw", "pulse", "both"], 0, O1, ROW_Y, 124, "osc")
tell(w1, "wave1", voice)
tell(w1, "wave1", v_osc1)
o1 = tabs("DCO1 Octave", "Oct 1", ["16'", "8'", "4'"], 1, O1 + 128, ROW_Y, 76, "osc")
o1m = box("- 1", rect=(1100, 820, 40, 22), ins=2, outtype=["int"])
wire(o1, o1m)
tell(o1m, "oct1", voice)
dial("PW", "PW", voice, "pw", 50, 95, 70, 5, O1, DIAL_Y, "osc", scale=0.01, views=[(v_osc1, "pw")])
pwm_dial = dial("PWM", "PWM", voice, "pwmamt", 0, 100, 0, 5, O1 + 56, DIAL_Y, "osc", scale=0.01, views=[(v_osc1, "pwm")])

v_osc2 = view("osc2", O2, VIEW_Y, 204, VIEW_H, "osc")
w2 = tabs("DCO2 Wave", "Wave 2", ["saw", "pulse", "tri"], 0, O2, ROW_Y, 124, "osc")
tell(w2, "wave2", voice)
tell(w2, "wave2", v_osc2)
o2 = tabs("DCO2 Octave", "Oct 2", ["16'", "8'", "4'"], 1, O2 + 128, ROW_Y, 76, "osc")
o2m = box("- 1", rect=(1150, 820, 40, 22), ins=2, outtype=["int"])
wire(o2, o2m)
tell(o2m, "oct2", voice)
dial("Semi", "Semi", voice, "semi", -12, 12, 0, 7, O2, DIAL_Y, "osc", views=[(v_osc2, "semi")])
dial("Fine", "Fine", voice, "fine", 0, 50, 10, 1, O2 + 56, DIAL_Y, "osc", views=[(v_osc2, "fine")])

v_mix = view("mixer", O3, VIEW_Y, 204, VIEW_H, "osc")
dial("OSC 1", "OSC 1", voice, "lvl1", 0, 100, 80, 5, O3, DIAL_Y, "osc", scale=0.01, views=[(v_mix, "lvl1")])
dial("OSC 2", "OSC 2", voice, "lvl2", 0, 100, 80, 5, O3 + 54, DIAL_Y, "osc", scale=0.01, views=[(v_mix, "lvl2")])
dial("Sub", "Sub", voice, "sublvl", 0, 100, 0, 5, O3 + 108, DIAL_Y, "osc", scale=0.01, views=[(v_mix, "sub")])
dial("Noise", "Noise", voice, "noiseamt", 0, 100, 8, 5, O3 + 160, DIAL_Y, "osc", scale=0.01, views=[(v_mix, "noise")])

v_lfo = view("lfo", O4, VIEW_Y, 252, VIEW_H, "osc")
tell(pwm_dial, "pwm", v_lfo, 0, 0.01)
dial("LFO Rate", "Rate", lfo, None, 0.05, 12, 0.5, 3, O4, DIAL_Y, "osc", exp=3.0, views=[(v_lfo, "lforate")])
dial("Vibrato", "Vibrato", voice, "vibamt", 0, 100, 0, 5, O4 + 64, DIAL_Y, "osc", scale=0.01, views=[(v_lfo, "vib")])
dial("LFO Filter", "Filter", voice, "lfofilt", 0, 100, 0, 5, O4 + 128, DIAL_Y, "osc", scale=0.01, views=[(v_lfo, "lfofilt")])

# ================= SHAPE: filter | envelope | drive =================
F, E, D = 12, 376, 680
v_filter = view("filter", F, VIEW_Y, 340, VIEW_H, "shape")
dial("Cutoff", "Cutoff", voice, "cutoff", 40, 12000, 700, 3, F, DIAL_Y, "shape", exp=3.0, views=[(v_filter, "cutoff")])
dial("Resonance", "Reso", voice, "reso", 0, 100, 30, 5, F + 68, DIAL_Y, "shape", scale=0.01, views=[(v_filter, "reso")])
dial("Env Amount", "Env", voice, "envamt", 0, 100, 50, 5, F + 136, DIAL_Y, "shape", scale=0.01, views=[(v_filter, "envamt")])
dial("Key Track", "Key", voice, "keytrack", 0, 100, 50, 5, F + 204, DIAL_Y, "shape", scale=0.01)
dial("Velocity Filter", "Vel", voice, "velfilt", 0, 100, 50, 5, F + 272, DIAL_Y, "shape", scale=0.01)

v_env = view("env", E, VIEW_Y, 280, VIEW_H, "shape")
dial("Attack", "Attack", voice, "atk", 0.5, 4000, 2, 2, E, DIAL_Y, "shape", exp=3.0, views=[(v_env, "atk")])
dial("Decay", "Decay", voice, "dec", 5, 6000, 260, 2, E + 70, DIAL_Y, "shape", exp=3.0, views=[(v_env, "dec")])
dial("Sustain", "Sustain", voice, "sus", 0, 100, 0, 5, E + 140, DIAL_Y, "shape", scale=0.01, views=[(v_env, "sus")])
dial("Release", "Release", voice, "rel", 5, 6000, 240, 2, E + 210, DIAL_Y, "shape", exp=3.0, views=[(v_env, "rel")])

v_drive = view("drive", D, VIEW_Y, 268, VIEW_H, "shape")
dial("Drive", "Drive", fx, "drive", 0, 100, 25, 5, D, DIAL_Y, "shape", scale=0.01, views=[(v_drive, "drive")])

width = W

# Play-page macros also drive the shape-page displays
for name, v, m in [("Tone", v_filter, "tone"), ("Length", v_env, "len")]:
    src = next(x["box"]["id"] for x in boxes if x["box"].get("varname") == VALUES[name])
    tell(src, m, v, 0, 0.01)
# the page tab also tells the chrome which rules and labels to draw
tell(page_tabs, "page", chrome)

# what the chrome draws per page: rules between sections, labels and hints (text, x, baseline, kind)
HEADER = [["preset", 240, 15, "label"], ["out", 800, 15, "label"]]
LAYOUT = {
    "subtitle": 500,
    "version": VERSION,
    "pages": [
        {"rules": [208, 512, 720],
         "labels": HEADER + [["click a step", C2 + 172, DIAL_Y + 17, "hint"], ["to change it", C2 + 172, DIAL_Y + 31, "hint"],
                             ["echo time", C3 + 64, DIAL_Y + 12, "label"], ["pump rate", C4 + 104, ROW_Y + 12, "hint"]]},
        {"rules": [228, 456, 684],
         "labels": HEADER + [["pw: pulse width", O1 + 116, DIAL_Y + 24, "hint"], ["pwm: lfo on pw", O1 + 116, DIAL_Y + 38, "hint"],
                             ["semi 7:", O2 + 116, DIAL_Y + 24, "hint"], ["a fifth up", O2 + 116, DIAL_Y + 38, "hint"],
                             ["sub: square, 1 oct down", O3, ROW_Y + 12, "hint"],
                             ["one lfo for all voices", O4, ROW_Y + 12, "hint"]]},
        {"rules": [364, 668],
         "labels": HEADER + [["grey: where the envelope opens it", F, ROW_Y + 12, "hint"],
                             ["one envelope: amp and filter", E, ROW_Y + 12, "hint"],
                             ["tape saturation, before the echo", D, ROW_Y + 12, "hint"]]},
    ],
}

# ---- presets: values in each control's own units ---------------------------------------
BASE = {"Chord": 1, "In Key": 0, "Tone": 0, "Length": 0, "Drift": 0, "Machine": 0, "Latch": 0, "Pattern": 0,
        "Density": 80, "Throws": 0, "Gate": 1, "Dub": 0, "Freeze": 0, "Echo Time": 2,
        "Pump": 0, "Pump Rate": 0, "Pump Attack": 6, "Pump Release": 55, "Pump Curve": 50,
        "DCO1 Wave": 2, "DCO1 Octave": 1, "PW": 70, "PWM": 0, "DCO2 Wave": 0, "DCO2 Octave": 1, "Semi": 0, "Fine": 10,
        "OSC 1": 80, "OSC 2": 80, "Sub": 0, "Noise": 8, "LFO Rate": 0.5, "Vibrato": 0, "LFO Filter": 0,
        "Cutoff": 700, "Resonance": 30, "Env Amount": 50, "Key Track": 50, "Velocity Filter": 50,
        "Attack": 2, "Decay": 260, "Sustain": 0, "Release": 240, "Drive": 25, "Volume": 0}
# Pattern: 0 dub dotted, 1 one & three+, 2 offbeat chops, 3 skank, 4 deep stab, 5 3-3-2
# Echo Time: 0 1/16, 1 1/8, 2 1/8d, 3 1/4, 4 1/4d, 5 1/2.  Chord: 0 poly, 1 minor, 2 m7, 3 m9, 4 m11, 5 sus4, 6 fifths, 7 dark
# DCO1 Wave: 0 saw, 1 pulse, 2 both.  DCO2 Wave: 0 saw, 1 pulse, 2 tri.  Octave: 0 16', 1 8', 2 4'.  Pump Rate: 0 1/4, 1 1/8, 2 1/16
# Volume is set afterwards from measured loudness (see LOUDNESS below).
PRESETS = [
    ("init", {}),

    # ---- dub ----
    # Basic Channel-style: saw + pulse with a detuned saw, noise chuff, dark filter opened by a short envelope
    ("chain stab", {"DCO1 Wave": 2, "Fine": 12, "Noise": 10, "Cutoff": 650, "Resonance": 35, "Env Amount": 55,
                    "Decay": 220, "Release": 300, "Drift": 15, "Dub": 45, "Pump": 25, "Pump Attack": 8,
                    "Pump Release": 60, "Drive": 30, "Volume": 0.0}),
    # Maurizio-style: punchier m7, brighter attack, a little sub under it, wetter echo
    ("m-stab", {"Chord": 2, "DCO1 Wave": 2, "Fine": 9, "Sub": 20, "Noise": 12, "Cutoff": 900, "Resonance": 30,
                "Env Amount": 65, "Decay": 160, "Release": 220, "Dub": 50, "Pump": 30, "Pump Attack": 6,
                "Pump Curve": 60, "Drive": 35, "Volume": -1.5}),
    # Deepchord / Echospace-style haze: soft pulses shimmering with PWM, slow attack, long tail, slow filter drift
    ("deep haze", {"Chord": 3, "DCO1 Wave": 1, "PW": 60, "PWM": 45, "DCO2 Wave": 0, "Fine": 20, "OSC 2": 60,
                   "Noise": 18, "LFO Rate": 0.25, "LFO Filter": 15, "Key Track": 40, "Cutoff": 420, "Resonance": 20,
                   "Env Amount": 30, "Velocity Filter": 40, "Attack": 25, "Decay": 900, "Sustain": 30,
                   "Release": 1400, "Drift": 30, "Dub": 70, "Echo Time": 4, "Pump": 30, "Pump Attack": 12,
                   "Pump Release": 70, "Pump Curve": 30, "Drive": 35, "Volume": -6.0}),
    # Echospace-style fog: darker still, triangle body an octave down, noisy, dissolving into the echo
    ("fog", {"Chord": 3, "Tone": -20, "DCO1 Wave": 0, "DCO2 Wave": 2, "DCO2 Octave": 0, "Fine": 22, "OSC 2": 70,
             "Noise": 25, "LFO Rate": 0.12, "LFO Filter": 25, "Cutoff": 350, "Resonance": 20, "Env Amount": 20,
             "Attack": 60, "Decay": 1200, "Sustain": 40, "Release": 2000, "Drift": 40, "Dub": 80, "Echo Time": 4,
             "Pump": 20, "Pump Attack": 15, "Pump Release": 75, "Pump Curve": 25, "Drive": 40, "Volume": -4.0}),
    # Chain Reaction-style wash: an m7 swelling into a long echo, the filter breathing with the LFO
    ("wash", {"Chord": 2, "DCO1 Wave": 2, "Fine": 15, "Noise": 15, "LFO Rate": 0.3, "LFO Filter": 30,
              "Cutoff": 500, "Resonance": 40, "Env Amount": 45, "Attack": 15, "Decay": 700, "Sustain": 20,
              "Release": 900, "Drift": 20, "Dub": 65, "Pump": 35, "Pump Attack": 10, "Pump Release": 65,
              "Pump Curve": 40, "Volume": -5.0}),
    # Rhythm & Sound-style skank: pulse-heavy offbeat chops from the latched machine
    ("skank", {"Machine": 1, "Latch": 1, "Pattern": 3, "Density": 90, "DCO1 Wave": 1, "PW": 55, "Fine": 8,
               "Noise": 6, "Cutoff": 900, "Resonance": 25, "Env Amount": 60, "Decay": 120, "Release": 140,
               "Dub": 35, "Pump": 15, "Drive": 20, "Volume": 1.0}),
    # Rhythm & Sound-style roots: two chops a bar, quarter-note echo, the odd throw, a touch of sub
    ("roots chop", {"Machine": 1, "Latch": 1, "Pattern": 2, "Density": 100, "Throws": 20, "DCO1 Wave": 2,
                    "Sub": 25, "Cutoff": 750, "Resonance": 25, "Env Amount": 60, "Decay": 100, "Release": 120,
                    "Dub": 55, "Echo Time": 3, "Drive": 25, "Volume": 1.0}),
    # Low and warm: the sub carrying it, triangle on top, more key tracking
    ("sub stab", {"DCO1 Wave": 0, "OSC 1": 50, "DCO2 Wave": 2, "Fine": 6, "OSC 2": 70, "Sub": 70, "Noise": 4,
                  "Key Track": 70, "Cutoff": 300, "Resonance": 15, "Env Amount": 35, "Decay": 300, "Release": 400,
                  "Dub": 40, "Pump": 25, "Pump Attack": 8, "Drive": 30, "Volume": 0.5}),
    # Worn tape: m9 through heavy drive and hiss, a little wobble in the pitch
    ("tape chord", {"Chord": 3, "DCO1 Wave": 2, "Fine": 16, "Noise": 30, "LFO Rate": 0.6, "Vibrato": 12,
                    "Cutoff": 700, "Resonance": 25, "Env Amount": 45, "Decay": 400, "Release": 500, "Drift": 15,
                    "Dub": 50, "Echo Time": 4, "Drive": 70, "Volume": -2.5}),
    # Breakdown pad: an m11 blooming slowly into a half-note echo, PWM shimmer
    ("ambient dub", {"Chord": 4, "DCO1 Wave": 1, "PWM": 40, "LFO Rate": 0.2, "LFO Filter": 15, "Fine": 25,
                     "Noise": 20, "Cutoff": 600, "Resonance": 20, "Env Amount": 15, "Attack": 800, "Decay": 3000,
                     "Sustain": 60, "Release": 3000, "Drift": 25, "Dub": 60, "Echo Time": 5, "Volume": -3.0}),
    # No echo until it throws: sparse latched stabs, every other one thrown
    ("throw dub", {"Machine": 1, "Latch": 1, "Pattern": 1, "Density": 100, "Throws": 50, "DCO1 Wave": 2,
                   "Cutoff": 800, "Env Amount": 55, "Decay": 200, "Release": 260, "Dub": 0, "Echo Time": 4,
                   "Pump": 20, "Volume": 0.5}),

    # ---- techno ----
    # Hypnotic: a sus4 stab off the kick, resonant, a slow filter sweep, pumping, latched
    ("hypnotic loop", {"Chord": 5, "Machine": 1, "Latch": 1, "Pattern": 4, "Density": 85, "Throws": 10,
                       "DCO1 Wave": 0, "DCO2 Wave": 1, "Fine": 12, "Noise": 10, "LFO Rate": 0.15, "LFO Filter": 20,
                       "Cutoff": 650, "Resonance": 45, "Env Amount": 55, "Decay": 130, "Release": 160, "Dub": 25,
                       "Pump": 40, "Pump Attack": 5, "Pump Release": 55, "Pump Curve": 60, "Volume": 0.0}),
    # The dark shape, resonant and short, 3-3-2, a triangle an octave down for weight
    ("dark machine", {"Chord": 7, "Machine": 1, "Latch": 1, "Pattern": 5, "Density": 70, "Throws": 15,
                      "DCO1 Wave": 2, "DCO2 Wave": 2, "DCO2 Octave": 0, "Fine": 14, "Noise": 12, "Cutoff": 480,
                      "Resonance": 50, "Env Amount": 70, "Velocity Filter": 60, "Decay": 150, "Release": 180,
                      "Dub": 30, "Pump": 35, "Pump Attack": 5, "Pump Curve": 65, "Volume": 3.0}),
    # UR-style chord memory: a bright m7 stab with DCO 2 a fifth up for that stacked sound
    ("chord memory", {"Chord": 2, "DCO1 Wave": 2, "DCO2 Wave": 0, "Semi": 7, "Fine": 6, "OSC 2": 50, "Noise": 5,
                      "Cutoff": 1800, "Resonance": 20, "Env Amount": 40, "Decay": 250, "Release": 300, "Dub": 20,
                      "Pump": 20, "Drive": 25, "Volume": -0.5}),
    # Warehouse: harder, brighter, driven, 16th echo, a fast snappy pump
    ("warehouse", {"Chord": 1, "DCO1 Wave": 1, "PW": 60, "DCO2 Wave": 0, "Fine": 18, "Sub": 30, "Noise": 18,
                   "Cutoff": 1400, "Resonance": 35, "Env Amount": 60, "Decay": 110, "Release": 140, "Dub": 30,
                   "Echo Time": 0, "Pump": 45, "Pump Attack": 3, "Pump Release": 45, "Pump Curve": 80, "Drive": 65, "Volume": 0.0}),
    # Chain Reaction-style minimal dub pulse: harsh pulse fifths, 3-3-2, throws
    ("pulse", {"Chord": 6, "Machine": 1, "Latch": 1, "Pattern": 5, "Density": 75, "Throws": 25, "DCO1 Wave": 1,
               "PW": 80, "PWM": 20, "LFO Rate": 2, "Noise": 20, "Cutoff": 1100, "Resonance": 55, "Env Amount": 50,
               "Decay": 90, "Release": 150, "Dub": 45, "Drive": 55, "Volume": 1.0}),
    # Rolling: every step and the extras, very short, pumping on 8ths
    ("rolling", {"Machine": 1, "Latch": 1, "Pattern": 5, "Density": 100, "DCO1 Wave": 2, "Cutoff": 800,
                 "Env Amount": 50, "Decay": 80, "Release": 100, "Dub": 20, "Pump": 50, "Pump Rate": 1,
                 "Pump Attack": 4, "Pump Release": 50, "Pump Curve": 70, "Volume": 3.0}),
    # Dark fifths: low, resonant, held like a drone, with the sub and a slow filter breath
    ("dark fifths", {"Chord": 6, "DCO1 Wave": 0, "DCO1 Octave": 0, "Fine": 8, "Sub": 40, "Noise": 10,
                     "LFO Rate": 0.1, "LFO Filter": 25, "Cutoff": 380, "Resonance": 60, "Env Amount": 40,
                     "Attack": 5, "Decay": 600, "Sustain": 30, "Release": 700, "Dub": 35, "Pump": 30, "Volume": -3.0}),
    # The machine throwing its own dubs
    ("throw machine", {"Machine": 1, "Latch": 1, "Pattern": 0, "Density": 60, "Throws": 35, "DCO1 Wave": 2,
                       "Cutoff": 700, "Env Amount": 55, "Decay": 200, "Release": 260, "Dub": 20, "Pump": 20, "Volume": 0.5}),

    # ---- other ----
    # Strings: two saws wide apart, PWM-free, a little vibrato
    ("detroit strings", {"Chord": 3, "DCO1 Wave": 0, "DCO2 Wave": 0, "Fine": 24, "Noise": 4, "LFO Rate": 5,
                         "Vibrato": 8, "Key Track": 60, "Cutoff": 1600, "Resonance": 15, "Env Amount": 15,
                         "Velocity Filter": 30, "Attack": 450, "Decay": 2000, "Sustain": 70, "Release": 1800,
                         "Drive": 15, "Volume": -1.5}),
    # For chord progressions' clips (poly): pulse keys, velocity opens the filter
    ("deep house keys", {"Chord": 0, "DCO1 Wave": 1, "PW": 55, "DCO2 Wave": 2, "Fine": 6, "OSC 2": 50, "Noise": 3,
                         "Cutoff": 1200, "Resonance": 20, "Env Amount": 40, "Velocity Filter": 70, "Decay": 350,
                         "Sustain": 10, "Release": 350, "Dub": 15, "Pump": 20, "Drive": 20, "Volume": 0.0}),
    # A sustained m7 pad breathing with the beat: long, soft pump on 8ths
    ("pump pad", {"Chord": 2, "DCO1 Wave": 1, "PWM": 35, "LFO Rate": 0.4, "Fine": 18, "Cutoff": 900,
                  "Env Amount": 20, "Attack": 10, "Decay": 1500, "Sustain": 80, "Release": 600, "Pump": 70,
                  "Pump Rate": 1, "Pump Attack": 10, "Pump Release": 80, "Pump Curve": 30, "Volume": -6.5}),
]
# the Preset menu's items
pbox = next(x["box"] for x in boxes if x["box"]["id"] == preset)
pbox["saved_attribute_attributes"]["valueof"].update(parameter_enum=[n for n, _ in PRESETS], parameter_mmax=len(PRESETS) - 1)

if set(INFO) - INFO_USED:
    raise SystemExit(f"2sl-stab.py: INFO has text for no parameter: {sorted(set(INFO) - INFO_USED)}")

presets_js = [{VALUES[k]: v for k, v in {**BASE, **p}.items()} for _, p in PRESETS]

# 2sl-ui tokens, dark and light (2sl-ui/max/2sl-colors.json), plus the few this device needs
THEMES = {
    "dark": {"pad": [0.149, 0.149, 0.149, 1], "well": [0.106, 0.106, 0.11, 1], "ink": [0.835, 0.847, 0.859, 1],
             "inverse": [0.149, 0.149, 0.149, 1], "label": [0.557, 0.58, 0.608, 1], "unlit": [0.494, 0.518, 0.545, 1],
             "mint": [0.447, 0.871, 0.761, 1], "now": [0.176, 0.357, 1.0, 1], "warm": [1.0, 0.55, 0.2, 1],
             "rest": [0.2, 0.2, 0.21, 1], "beat": [0.26, 0.27, 0.28, 1], "key": [0.72, 0.73, 0.74, 1],
             "keyBlack": [0.07, 0.07, 0.08, 1]},
    "light": {"pad": [0.835, 0.847, 0.859, 1], "well": [0.77, 0.78, 0.79, 1], "ink": [0.0, 0.0, 0.0, 1],
              "inverse": [1.0, 1.0, 1.0, 1], "label": [0.349, 0.369, 0.396, 1], "unlit": [0.451, 0.475, 0.502, 1],
              "mint": [0.12, 0.55, 0.45, 1], "now": [0.176, 0.357, 1.0, 1], "warm": [0.85, 0.38, 0.0, 1],
              "rest": [0.7, 0.71, 0.73, 1], "beat": [0.62, 0.63, 0.65, 1], "key": [0.97, 0.97, 0.97, 1],
              "keyBlack": [0.12, 0.12, 0.13, 1]},
}
view_js = open(os.path.join(HERE, "2sl-stab-view.template.js")).read()
glyphs = open(os.path.join(HERE, "cozette-glyphs.js")).read()
view_js = (view_js.replace("/*COZETTE*/", glyphs.strip()).replace("/*THEMES*/", json.dumps(THEMES))
           .replace("/*LAYOUT*/", "var LAYOUT = " + json.dumps(LAYOUT) + ";"))
open(os.path.join(ROOT, "devices", "2sl-stab", "2sl-stab-view.js"), "w").write(view_js)
ui_js = open(os.path.join(HERE, "2sl-stab-ui.template.js")).read()
ui_js = (ui_js.replace("/*PAGES*/", json.dumps(PAGES)).replace("/*PRESETS*/", json.dumps(presets_js, indent=1))
         .replace("/*CONTROLS*/", json.dumps(CONTROLS)).replace("/*VIEWS*/", json.dumps(VIEWS)).replace("/*THEMES*/", json.dumps(THEMES)))
open(os.path.join(ROOT, "devices", "2sl-stab", "2sl-stab-ui.js"), "w").write(ui_js)

patch = {"patcher": {
    "fileversion": 1,
    "appversion": {"major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1},
    "classnamespace": "box", "rect": [80.0, 80.0, 1300.0, 900.0],
    "openinpresentation": 1, "devicewidth": float(width),
    "boxes": boxes, "lines": lines,
}}

maxpat = os.path.join(HERE, "2sl-stab.maxpat")
json.dump(patch, open(maxpat, "w"), indent="\t")
amxd = os.path.join(ROOT, "devices", "2sl-stab", "2sl-stab.amxd")
subprocess.run([sys.executable, os.path.join(ROOT, "tools", "amxd.py"), "pack", maxpat, amxd, "--type", "instrument"], check=True)
print(f"wrote {os.path.relpath(maxpat, ROOT)} and {os.path.relpath(amxd, ROOT)} ({len(boxes)} boxes, {width}px wide)")

# the frozen release: one self-contained file with the scripts embedded
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
frozen = os.path.join(ROOT, "dist", f"2sl-stab-{VERSION}.amxd")
scripts = [os.path.join(ROOT, "devices", "2sl-stab", n) for n in ("2sl-stab.js", "2sl-stab-ui.js", "2sl-stab-view.js")]
subprocess.run([sys.executable, os.path.join(ROOT, "tools", "amxd.py"), "freeze", maxpat, frozen, "--type", "instrument",
                "--embed", *scripts], check=True)
print(f"froze {os.path.relpath(frozen, ROOT)} ({os.path.getsize(frozen) // 1024} KB, scripts embedded)")
