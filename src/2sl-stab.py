#!/usr/bin/env python3
"""2sl stab: a dub techno chord stab instrument for Max for Live.

  python3 src/2sl-stab.py   # writes src/2sl-stab.maxpat, devices/2sl-stab/2sl-stab.amxd (for development, scripts
                            # and Live presets alongside), and the release: dist/2sl-stab-<version>/ (the frozen
                            # 2sl-stab-<version>.amxd, one self-contained file, with Live presets made for it) and
                            # that folder zipped, dist/2sl-stab-<version>.zip

Signal flow (from the research in devices/2sl-stab/README.md):
  MIDI -> chord memory (js) -> mc.noteallocator~ (16 voices)
       -> mc.gen~ voice: detuned saw + pulse + noise, 24 dB ladder low-pass with
          envelope / key / velocity, analog-style ADSR
       -> mono sum -> gen~ FX: tape drive, then a stereo dub delay synced to Live's tempo
          with high- and low-pass *in the feedback loop* (each repeat darker and thinner),
          saturation and diffusion in the loop, wow/flutter, slightly offset L/R times
       -> plugout~
"""
import gzip, json, os, re, shutil, struct, subprocess, sys, zipfile
import xml.etree.ElementTree as ElementTree

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---- DSP (genexpr) -------------------------------------------------------------------

# Every per-sample smoother is a one-pole with a time constant in ms, converted with the sample rate here,
# so it sounds the same at 44.1 and 192 kHz. Written into both gen~ patches (gen wants functions first).
GEN_SMOOTHING_FUNCTION = r"""
// one-pole smoothing coefficient for a time constant in ms (63% of the way there in that time)
smoothing_coefficient(time_constant_ms, sample_rate) {
	return 1 - exp(-1000 / (max(time_constant_ms, 0.001) * sample_rate));
}
"""

VOICE = GEN_SMOOTHING_FUNCTION + r"""
// One voice. in1: frequency (Hz). in2: gate = velocity 0..1, 0 = release. in3: the LFO (-1..1, shared).
// in4: the note-on count: a new number on every note-on (the patch counts them), so a note-on always starts the
// envelope, even when it changes no other value (a voice stolen for its own pitch at the same velocity).
// out1: the voice's sound. out2: busy, 1 from its note-on until its envelope has finished (its release, or Stop's
// 20 ms ramp), 0 otherwise: mc.noteallocator~ reads it to know when a released voice is free again.
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

Param wave1(2, min=0, max=2);           // DCO 1: 0 saw, 1 pulse, 2 saw + pulse
Param oct1(0, min=-1, max=1);           // 16' 8' 4'
Param pw(0.7, min=0.5, max=0.95);       // pulse width (both DCOs)
Param wave2(0, min=0, max=2);           // DCO 2: 0 saw, 1 pulse, 2 triangle
Param oct2(0, min=-1, max=1);
Param semi(0, min=-12, max=12);         // DCO 2 interval: 7 = a fifth up
Param fine(10, min=0, max=50);          // DCO 2 detune, cents
Param lvl1(0.8, min=0, max=1);          // mixer
Param lvl2(0.8, min=0, max=1);
Param sublvl(0, min=0, max=1);          // the sub: DCO 1 divided down
Param submode(0, min=0, max=2);         // 0 square -1 oct, 1 square -2 oct, 2 25% pulse -2 oct
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
Param panic(0);                         // Stop: every new number ramps the voice to silence

History env(0), stage(0), lastgate(0), velo(0), last_note_on_count(0), lastpanic(0), fadeleft(0), fadestep(0);
History velo_smoothed(0);   // velo, glided: a stolen voice's new velocity mustn't jump the gain (a click)
History ph1(0), ph2(0), dco1_cycle_count(0), s1(0), s2(0), s3(0), s4(0);

lfo = in3;
note = max(in1, 1);                    // the played pitch (vibrato is applied on top)
freq = note * pow(2, vibamt * lfo * 0.5 / 12);
gatein = in2;
note_on_count = in4;
sr = samplerate;

// A note-on is a new count with the gate up: start the envelope. The gate falling is the note-off. Values alone
// can't be the note-on: messages within one vector reach gen~ as their last value, so a voice stolen for the same
// pitch and velocity (note-off, note-on: gate v, 0, v) would see nothing change.
if (note_on_count != last_note_on_count && gatein > 0) {
	stage = 1;
	velo = gatein;
} else if (gatein <= 0 && lastgate > 0) {
	stage = 3;
}
lastgate = gatein;
last_note_on_count = note_on_count;

// Stop: ramp to exactly 0 over 20 ms, whatever the release. A key pressed during the ramp starts when it ends.
if (panic != lastpanic) {
	lastpanic = panic;
	fadeleft = max(mstosamps(20), 1);
	fadestep = env / fadeleft;
}
if (fadeleft > 0) {
	fadeleft = fadeleft - 1;
	stage = 0;
	env = fadeleft > 0 ? max(env - fadestep, 0) : 0;
	lastgate = 0;
	last_note_on_count = -1;           // the counts start at 1: a key held through the ramp starts when it ends
}

// the velocity glides to a new value over ~2 ms (time constant 0.5 ms: 98% there in 2 ms)
velo_smoothed = velo_smoothed + (velo - velo_smoothed) * smoothing_coefficient(0.5, sr);

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
dco1_phase_unwrapped = ph1 + dt1;
if (dco1_phase_unwrapped >= 1) {       // DCO 1 completed a cycle: clock the sub's divider (0..3)
	dco1_cycle_count = wrap(dco1_cycle_count + 1, 0, 4);
}
ph1 = wrap(dco1_phase_unwrapped, 0, 1);
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

// sub: DCO 1 divided by 2 or 4 (like a flip-flop divider), so it stays locked to DCO 1 and follows its
// footage. Its phase is DCO 1's phase plus the cycles counted so far. Square -1 oct, square -2 oct, or a
// 25% pulse -2 oct (DC removed, so switching doesn't shift the level). Edges band-limited with blep.
sub_phase_1oct = (wrap(dco1_cycle_count, 0, 2) + ph1) * 0.5;
sub_dt_1oct = dt1 * 0.5;
sub_phase_2oct = (dco1_cycle_count + ph1) * 0.25;
sub_dt_2oct = dt1 * 0.25;
sub_square_1oct = (sub_phase_1oct < 0.5 ? 1 : -1) + blep(sub_phase_1oct, sub_dt_1oct)
	- blep(wrap(sub_phase_1oct + 0.5, 0, 1), sub_dt_1oct);
sub_square_2oct = (sub_phase_2oct < 0.5 ? 1 : -1) + blep(sub_phase_2oct, sub_dt_2oct)
	- blep(wrap(sub_phase_2oct + 0.5, 0, 1), sub_dt_2oct);
sub_pulse_2oct = (sub_phase_2oct < 0.25 ? 1 : -1) + 0.5 + blep(sub_phase_2oct, sub_dt_2oct)
	- blep(wrap(sub_phase_2oct + 0.75, 0, 1), sub_dt_2oct);
subosc = submode < 0.5 ? sub_square_1oct : (submode < 1.5 ? sub_square_2oct : sub_pulse_2oct);

osc = (o1 * lvl1 + o2 * lvl2 + subosc * sublvl) * 0.5 + noise() * noiseamt * 0.4;

// 4-pole ladder low-pass with saturated feedback
vel_env = clamp(envamt + 0.25 * tonemac, 0, 1) * (1 - velfilt + velfilt * velo_smoothed);
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

out1 = y * env * (0.35 + 0.65 * velo_smoothed) * level;
out2 = (stage > 0 || fadeleft > 0) ? 1 : 0;
"""

# The echo's longest time: 1/2 note at Live's slowest tempo, 20 BPM (Live Object Model, Song.tempo: "20.0 ...
# 999.0"), is 6000 ms. The left side runs 3.1% long and wow adds up to 0.12%: 6193 ms, plus the cubic read's
# 3 samples. The gen docs give a Delay's size in samples but don't say it may be an expression of samplerate, so
# the sizes are fixed numbers of samples, enough at the highest sample rate Live runs at: 192 kHz (Ableton, Live
# editions: "Multitrack recording up to 32-bit/192 kHz"). At lower rates the buffers are just longer than needed.
HIGHEST_SAMPLE_RATE = 192000
ECHO_BUFFER_SAMPLES = int(HIGHEST_SAMPLE_RATE * 6.25)
DIFFUSION_BUFFER_SAMPLES = int(HIGHEST_SAMPLE_RATE * 0.02)   # the diffusion allpasses read up to 14 ms
ECHO_LONGEST_MS = 60000.0 / 20.0 * 2.0
if HIGHEST_SAMPLE_RATE * ECHO_LONGEST_MS * 1.031 * 1.0012 / 1000.0 + 4 >= ECHO_BUFFER_SAMPLES:
    raise SystemExit("2sl-stab.py: the echo buffer is shorter than the longest echo time at the highest sample rate")
if HIGHEST_SAMPLE_RATE * 13.900 / 1000.0 >= DIFFUSION_BUFFER_SAMPLES:
    raise SystemExit("2sl-stab.py: the diffusion buffers are shorter than the longest allpass at the highest sample rate")
# The Echo display draws the loop's last ECHO_ROUNDS_KEPT whole time rounds, as the FX measured them, and the round
# it is in now. The FX keeps them (the display reads all of them at once), so no round is lost between reads.
ECHO_ROUNDS_KEPT = 10

FX = GEN_SMOOTHING_FUNCTION + r"""
// in1: the voices, mono. in2: Live's beat ramp (plugphasor~). out1/out2: left/right. out3: the echo's level (a
// meter). For the Echo display: out4, the echo's peak so far in the time round it is in; out5 on, its peaks over the
// last whole rounds, the newest first (ECHO_ROUNDS_KEPT of them; 0 for rounds since Stop or not yet played).
// soft clip: clean below 0.8, rounding off above (gen needs functions first)
sclip(v) {
	a = abs(v);
	y = v;
	if (a > 0.8) {
		y = (v < 0 ? -1 : 1) * (0.8 + 0.2 * tanh((a - 0.8) / 0.2));
	}
	return y;
}

// the pump's duck (0..1) at phase ph of a division: a sine ramp in over atkf, then a recovery shaped by curve
pump_duck(ph, atkf, release_end, curve) {
	duck = 0;
	if (ph < atkf) {
		duck = sin(1.5707963 * ph / atkf);
	} else {
		duck = pow(1 - clamp((ph - atkf) / (release_end - atkf), 0, 1), 1 + curve * 3);
	}
	return duck;
}

// The echo is only for throws: silent until Send, Throw or Freeze feeds it.
Param drive(0.25, min=0, max=1);        // tape saturation
Param dtime(363, min=20, max=ECHO_LONGEST_MS);  // ms (Live's tempo x the Time menu): 1/2 at 20 BPM is the longest
Param echosend(0, min=0, max=1);        // the level every stab goes into the echo at
Param dub(0, min=0, max=1);             // the echo's character: feedback, darker, smeared
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
Param panic(0);                         // Stop: every new number empties the echo

Delay dl(ECHO_BUFFER_SAMPLES);          // samples: the longest echo at the highest sample rate (see the build)
Delay dr(ECHO_BUFFER_SAMPLES);
Delay al1(DIFFUSION_BUFFER_SAMPLES);    // the diffusion allpasses: up to 14 ms
Delay al2(DIFFUSION_BUFFER_SAMPLES);
Delay ar1(DIFFUSION_BUFFER_SAMPLES);
Delay ar2(DIFFUSION_BUFFER_SAMPLES);
History ts(363), wph(0), wph2(0), sendsm(0), fbsm(0.4), frz(0);
History lpl1(0), lpl2(0), hpl(0), lpr1(0), lpr2(0), hpr(0), lvl(0), ownph(0), gsm(1);
History lastpanic(0), elapsed(1e9), pressfade(0);
History live_clock_weight(0);           // 0 = the pump runs on its own clock, 1 = on Live's beat
History echo_round_elapsed(0), echo_round_peak_so_far(0);
History ECHO_ROUND_HISTORIES;           // the last whole rounds' peaks, echo_round_peak_1 the newest

sr = samplerate;
// Smoothing time constants in ms (each was a per-sample coefficient; the times are what it gave at 44.1 kHz).
freeze_glide = smoothing_coefficient(11.3, sr);
send_rise = smoothing_coefficient(1.12, sr);
send_fall = smoothing_coefficient(15.1, sr);
feedback_rise = smoothing_coefficient(2.26, sr);
feedback_fall = smoothing_coefficient(567, sr);
echo_time_glide = smoothing_coefficient(56.7, sr);
level_meter_fall = smoothing_coefficient(75.6, sr);
pump_gain_glide = smoothing_coefficient(0.442, sr);
gain = 1 + drive * 5;
x = tanh(in1 * gain) / (1 + drive * 2.2);

// what goes into the echo, and how long it rings
frz = frz + (freeze - frz) * freeze_glide;
target_send = max(echosend, throwgate) * (1 - freeze);
sendsm = sendsm + (target_send - sendsm) * (target_send > sendsm ? send_rise : send_fall);
target_fb = max(0.3 + dub * 0.62, throwgate * 0.9);
fbsm = fbsm + (target_fb - fbsm) * (target_fb > fbsm ? feedback_rise : feedback_fall);
fb = fbsm * (1 - frz) + 1.05 * frz;
looplp = (4500 - dub * 3100) * (1 - frz) + 9000 * frz;
loophp = (90 + dub * 160) * (1 - frz) + 50 * frz;
diffuse = 0.2 + dub * 0.45;

// tape echo: time glides when it changes, wow and flutter, L/R slightly apart
ts = ts + (dtime - ts) * echo_time_glide;
wph = wrap(wph + 0.53 / sr, 0, 1);
wph2 = wrap(wph2 + 0.137 / sr, 0, 1);
wow = (sin(twopi * wph) * 0.6 + sin(twopi * wph2) * 0.4) * 0.0012;
tl = clamp(mstosamps(ts * 1.031 * (1 + wow)), 2, ECHO_BUFFER_SAMPLES - 4);   // -4: room for the cubic read
tr = clamp(mstosamps(ts * 0.979 * (1 - 0.8 * wow)), 2, ECHO_BUFFER_SAMPLES - 4);

// Stop: everything in the buffers is from before it. `clean` is a gain by where the longest read lands:
// 0 on audio from before Stop, rising to 1 over the 2 ms of audio written after it. It is a position, not
// a time, so a read gliding back past the Stop point (Time changed) is silent however fast it moves.
// The old echo fades out over 2 ms at the press, so no click. New sound goes in straight away.
// The Echo display's rounds are emptied with it, and a new round starts: it shows the loop as Stop left it, empty.
if (panic != lastpanic) {
	lastpanic = panic;
	elapsed = 0;
	pressfade = 1;
	echo_round_elapsed = 0;
	echo_round_peak_so_far = 0;
	ECHO_ROUNDS_CLEARED
}
elapsed = min(elapsed + 1, 1e9);       // capped far past any read, so `clean` stays 1 long after Stop
clean = clamp((elapsed - max(tl, tr) - 3) / mstosamps(2), 0, 1);   // -3: the cubic read's reach
pressfade = max(pressfade - 1 / mstosamps(2), 0);
keep = max(clean, pressfade);
rl = dl.read(tl, interp="cubic") * keep;
rr = dr.read(tr, interp="cubic") * keep;
if (clean <= 0) {                      // empty the loop filters too
	lpl1 = 0;
	lpl2 = 0;
	hpl = 0;
	lpr1 = 0;
	lpr2 = 0;
	hpr = 0;
}

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
d1 = al1.read(mstosamps(8.458));          // 373, 587, 401 and 613 samples at 44.1 kHz
v1 = fl + diffuse * d1;
al1.write(v1 * clean);
fl = d1 - diffuse * v1;
d2 = al2.read(mstosamps(13.311));
v2 = fl + diffuse * d2;
al2.write(v2 * clean);
fl = d2 - diffuse * v2;
d3 = ar1.read(mstosamps(9.093));
v3 = fr + diffuse * d3;
ar1.write(v3 * clean);
fr = d3 - diffuse * v3;
d4 = ar2.read(mstosamps(13.900));
v4 = fr + diffuse * d4;
ar2.write(v4 * clean);
fr = d4 - diffuse * v4;

dl.write(x * sendsm + clean * tanh(fl * fb * 1.1) / 1.1);
dr.write(x * sendsm + clean * tanh(fr * fb * 1.1) / 1.1);

// pump: a sidechain-style duck on every beat division. Live's beat while it plays, our own clock when
// stopped. The duck ramps in over Attack (never a jump, so no click), recovers over Release with Curve.
// The two clocks are at different places in the beat, so Live starting or stopping hands over from one to
// the other with a 20 ms crossfade of their ducks, not a switch (which jumped the gain).
ownph = wrap(ownph + bpm / 60 / sr, 0, 1);
divms = 60000 / max(bpm, 20) / pumprate;
atkf = clamp(pumpatk / divms, 0.001, 0.3);
rl_end = max(pumprel, atkf + 0.05);
live_clock_weight = live_clock_weight + ((transport > 0.5 ? 1 : 0) - live_clock_weight) * smoothing_coefficient(20, sr);
duck_on_live_beat = pump_duck(wrap(in2 * pumprate, 0, 1), atkf, rl_end, pumpcurve);
duck_on_own_clock = pump_duck(wrap(ownph * pumprate, 0, 1), atkf, rl_end, pumpcurve);
duck = duck_on_own_clock + (duck_on_live_beat - duck_on_own_clock) * live_clock_weight;
target_g = 1 - pumpdepth * duck;
gsm = gsm + (target_g - gsm) * pump_gain_glide;   // ~1 ms to 90%: no steps, ever

lvl = max(abs(rl) + abs(rr), lvl * (1 - level_meter_fall));
out3 = lvl;
// The echo's peak over each time round (the left side's time, the longer, so a round holds both sides' repeat):
// what the loop really does round by round, filters, saturation and all, for the Echo display. The 2 ms fade of
// the old echo at Stop isn't counted: it is the echo being emptied.
if (pressfade <= 0) {
	echo_round_peak_so_far = max(echo_round_peak_so_far, abs(rl) + abs(rr));
}
echo_round_elapsed = echo_round_elapsed + 1;
if (echo_round_elapsed >= tl) {
	ECHO_ROUNDS_SHIFTED
	echo_round_peak_1 = echo_round_peak_so_far;
	echo_round_peak_so_far = 0;
	echo_round_elapsed = 0;
}
out4 = echo_round_peak_so_far;
ECHO_ROUND_OUTPUTS
gain = dbtoa(volume) * 2;              // +6 dB over the old level; the soft clip catches overs
out1 = sclip((x + rl * 1.2) * gsm * gain);
out2 = sclip((x + rr * 1.2) * gsm * gain);
"""

ECHO_ROUND_NUMBERS = range(1, ECHO_ROUNDS_KEPT + 1)
FX_SUBSTITUTIONS = {
    "ECHO_ROUND_HISTORIES": ", ".join(f"echo_round_peak_{n}(0)" for n in ECHO_ROUND_NUMBERS),
    "ECHO_ROUNDS_CLEARED": "\n\t".join(f"echo_round_peak_{n} = 0;" for n in ECHO_ROUND_NUMBERS),
    "ECHO_ROUNDS_SHIFTED": "\n\t".join(f"echo_round_peak_{n} = echo_round_peak_{n - 1};"
                                       for n in reversed(ECHO_ROUND_NUMBERS) if n > 1),
    "ECHO_ROUND_OUTPUTS": "\n".join(f"out{4 + n} = echo_round_peak_{n};" for n in ECHO_ROUND_NUMBERS),
    "ECHO_ROUNDS_KEPT": str(ECHO_ROUNDS_KEPT),
    "ECHO_LONGEST_MS": repr(ECHO_LONGEST_MS),
    "DIFFUSION_BUFFER_SAMPLES": str(DIFFUSION_BUFFER_SAMPLES),
    "ECHO_BUFFER_SAMPLES": str(ECHO_BUFFER_SAMPLES),
}
for placeholder, genexpr in FX_SUBSTITUTIONS.items():
    if placeholder not in FX:
        raise SystemExit(f"2sl-stab.py: the FX code has no {placeholder} to fill in")
    FX = FX.replace(placeholder, genexpr)
FX_OUTLETS = 4 + ECHO_ROUNDS_KEPT        # left, right, level, the round now, the whole rounds

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


def find_box_by_text(text):
    """The one box with this text (fails the build if there are none or several)."""
    found = [x["box"]["id"] for x in boxes if x["box"].get("text") == text]
    if len(found) != 1:
        raise SystemExit(f"2sl-stab.py: expected one box {text!r}, found {len(found)}")
    return found[0]


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
    # views
    "Steps view": ("Pattern", "The machine's 16 steps, as Shift places them. Click a step to cycle rest, hit, "
                   "accent. Bright with a bar on top: accent (full velocity, fires at Density x1.4). Dim: hit (softer, fires at Density). Empty "
                   "steps: the lighter ones start each beat. Blue outline: the step playing now. Orange outline: "
                   "that stab was thrown into the echo."),
    "Link view": ("2sl.to", "Opens 2sl.to in your browser."),
    "Chord view": ("Chord", "The chord sounding now: its name, its notes (top right), and two octaves of keys with "
                   "those notes lit mint. With Machine on, the last stab the machine played. In orange on top: "
                   "In Key is on but Live's scale has under 5 notes, so chords use the fixed shapes."),
    "Echo view": ("Echo", f"What the echo really did, measured from its sound: its last {ECHO_ROUNDS_KEPT} time rounds, the newest on "
                  "the right, each bar that round's peak on a 48 dB scale up to the most the loop can carry; the outlined "
                  "bar at the far right is the round it is in now, growing. Repeats fall away round by round as the "
                  "filters and feedback take them; frozen, they rise while it swells and flatten where tape saturation "
                  "holds it. A throw shows as its repeats, with an orange frame. A dash: a silent round. Stop empties "
                  "it. The line along the bottom is the echo's level now. Top right: Send (\"throws only\" at 0), "
                  "or throw or frozen."),
    "Pump view": ("Pump", "The output level over two beats at Live's tempo: each dip is a duck, mint while Depth "
                  "is above 0. The blue line is Live's position in the beat. Top right: Depth."),
    "Sub view": ("Sub", "The sub as the voice makes it for Sub Mode, in mint: DCO 1 divided by 2 or 4, drawn over "
                 "the same time as DCO 1's two cycles, so -1 oct is one cycle and -2 oct half of one (shown across an "
                 "edge). The 25% pulse sits off centre (+1.5 / -0.5) as in the voice. Top right: the mode. Its level is "
                 "Sub in the mixer."),
    "DCO1 view": ("DCO 1", "Two cycles of DCO 1's waveform as the voice makes it (saw, pulse or both), in mint. "
                  "Top right: the wave and pulse width. With PWM up, the pulse width moves with the LFO, in step with it."),
    "DCO2 view": ("DCO 2", "DCO 2's waveform (saw, pulse or triangle) over the same time as DCO 1's two cycles, "
                  "so Semi shows as more or fewer cycles. Its pulse has PW's width and moves with PWM, as DCO 1's. "
                  "Top right: the wave, pulse width (on pulse), Semi and Fine."),
    "LFO view": ("LFO", "The LFO's last two seconds, scrolling, in mint, as the sound had it (drawn from readings of "
                 "the LFO itself, so a Rate change shows where it happened); its rate top right. Along the bottom, where it goes: pwm, "
                 "vibrato, filter, bright with the amount when on, dim when off."),
    "Filter view": ("Filter", "The low-pass response from 20 Hz to 20 kHz in mint, with the resonance peak, at the "
                    "cutoff (top right, Tone included). Grey: how far the envelope opens it at full velocity."),
    "Envelope view": ("Envelope", "The envelope in mint: attack, decay to Sustain, a held stretch, then release. "
                      "Times are on a squashed scale and include the Length macro."),
    "Drive view": ("Drive", "The saturation curve in mint: input level across (-1 to +1, full scale), output up on "
                   "the same scale. More Drive bends it into a steeper middle and flatter ends, and turns the output "
                   "down to keep the level about even."),
    # header
    "Page": ("Page", "Shows the play, osc or shape page. Controls on hidden pages keep working. The device opens on play."),
    "Volume": ("Volume", "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs. "
               "Presets set it to match their loudness."),
    "Stop": ("Stop", "Panic: releases every note, clears a latched chord, ramps the voices to silence in 20 ms, "
             "empties the echo and turns Freeze off. Stopping Live doesn't run it: tails ring out."),
    # play: chord
    "Chord": ("Chord", "What each key plays: poly plays your notes as they are; the others stack a chord on each key "
              "(minor, m7, m9, m11, sus4, fifths, dark = 0-5-8). Default minor."),
    "In Key": ("In Key", "Builds chords from the scale set in Live (its root and scale): each key snaps down into the "
               "scale and the chord stacks scale tones on it. Scales under 5 notes fall back to the fixed shapes, "
               "and the chord display says so."),
    "Tone": ("Tone", "Brighter or darker: moves the cutoff up to 2.5 octaves either way, and the filter envelope with it. "
             "-100 to +100, default 0."),
    "Length": ("Length", "Shorter or longer tails: scales Decay and Release from x0.25 (-100) to x4 (+100). Default 0."),
    "Drift": ("Drift", "Chance each chord gets another voicing of the same chord (inverted, top note dropped, "
              "middle spread, or octave added). 0 = always the same."),
    # play: machine
    "Machine": ("Machine", "With Machine on, keys don't play directly: they pick the chord the pattern plays, on 16th steps. "
                "Follows Live's transport. With Live stopped it plays only keys you hold, at Live's tempo."),
    "Latch": ("Latch", "With Machine on, the chord keeps playing after you let go, while Live plays. "
              "A new chord replaces it; Stop clears it."),
    "Pattern": ("Pattern", "Loads a 16-step stab pattern as a starting point. Click steps in the display to cycle "
                "rest, hit, accent; edited steps are saved with the set."),
    "Density": ("Density", "Each step fires by chance: hits at Density, accents at Density x1.4. Above 70%, empty "
                "offbeat 16ths also fire now and then (up to 15% at 100). Default 80%."),
    "Throws": ("Throws", "Chance each machine stab is also thrown into the echo (opens the echo for an 8th at 90% feedback)."),
    "Gate": ("Gate", "How long each machine stab is held, in 16th notes (1-4). Default 1."),
    "Shift": ("Shift", "Rotates the pattern later by 0-15 16ths without changing it; the display shows the shifted "
              "pattern. Default 0."),
    # play: dub
    "Send": ("Send", "How much of every stab goes into the echo (100% = as much as a throw). The dial's travel is "
             "squared, so the low end is fine. 0 = no echo except throws. Freeze closes it. Default 0."),
    "Dub": ("Dub", "The echo's character: longer feedback (30% to 92%), each repeat darker and more smeared. "
            "Sends nothing in: Send, Throw and Throws do."),
    "Throw": ("Throw", "Throws the sound into the echo now: opens the echo for an 8th at 90% feedback."),
    "Freeze": ("Freeze", "Holds the echo loop: nothing new goes in, and each time round it gets a little louder, "
               "so it swells over tens of seconds until tape saturation holds it just under full level. "
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
    "Sub": ("Sub Level", "Level of the sub: DCO 1 divided down, an octave or two below it (Sub Mode). Default 0."),
    "Sub Mode": ("Sub Mode", "The sub's wave: a square 1 octave below DCO 1, a square 2 octaves "
                 "below, or a 25% pulse 2 octaves below (keeps a strong -1 octave). Default -1 oct square."),
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


# ---- the Init values and the presets: src/2sl-stab-presets.json -----------------------------
# "init": every saved control's initial value. A fresh device is the Init sound: each control's initial value is
# read from here, and so are the gen~ Param defaults and the displays' starting values (checked or written at
# build time). "presets": the sounds, each the Init values with some changed; the build writes each as a Live
# preset (see LIVE PRESETS below). Values are in each control's own units: a dial's number, a menu's or tab's item
# name, a toggle's "off" / "on". The build fails on an unknown control, a control without an Init value, or a
# value out of its control's range.
PRESET_DATA_PATH = os.path.join(HERE, "2sl-stab-presets.json")
PRESET_DATA_NAME = os.path.relpath(PRESET_DATA_PATH, ROOT)   # for the build's messages
with open(PRESET_DATA_PATH) as preset_data_file:
    PRESET_DATA = json.load(preset_data_file)
if set(PRESET_DATA) != {"init", "presets"}:
    raise SystemExit(f"2sl-stab.py: {PRESET_DATA_NAME} must hold exactly 'init' and 'presets', not {sorted(PRESET_DATA)}")
INIT_IN_OWN_UNITS = PRESET_DATA["init"]
SAVED_CONTROLS = {}   # control (parameter long name) -> {"varname", "items" (None for a number), "minimum", "maximum"}
INIT_VALUE = {}       # control -> its initial value as the control holds it (a number; a menu, tab or toggle's index)


def value_as_held(control_name, value_in_own_units, where):
    """`value_in_own_units` as control `control_name` holds it (an item name becomes its index), or fail the build."""
    spec = SAVED_CONTROLS[control_name]
    if spec["items"] is not None:
        if value_in_own_units not in spec["items"]:
            raise SystemExit(f"2sl-stab.py: {where}: {control_name} is {value_in_own_units!r}, not one of {spec['items']}")
        return spec["items"].index(value_in_own_units)
    if isinstance(value_in_own_units, bool) or not isinstance(value_in_own_units, (int, float)):
        raise SystemExit(f"2sl-stab.py: {where}: {control_name} is {value_in_own_units!r}, not a number")
    if not spec["minimum"] <= value_in_own_units <= spec["maximum"]:
        raise SystemExit(f"2sl-stab.py: {where}: {control_name} is {value_in_own_units}, outside "
                         f"{spec['minimum']:g} to {spec['maximum']:g}")
    return value_in_own_units


def saved_control(name, varname, items=None, minimum=None, maximum=None):
    """Registers a control Live saves with the set and in presets; returns its initial value (from the Init values)."""
    if name in SAVED_CONTROLS:
        raise SystemExit(f"2sl-stab.py: two saved controls are called {name!r}")
    if items is not None:
        minimum, maximum = 0, len(items) - 1
    SAVED_CONTROLS[name] = {"varname": varname, "items": items, "minimum": minimum, "maximum": maximum}
    if name not in INIT_IN_OWN_UNITS:
        raise SystemExit(f"2sl-stab.py: {name!r} has no Init value: add it to 'init' in {PRESET_DATA_NAME}")
    INIT_VALUE[name] = value_as_held(name, INIT_IN_OWN_UNITS[name], "init")
    return INIT_VALUE[name]


CONTROL_BY_BOX = {}       # box id -> (control name, how its value is transformed on the way: v -> v)
VIEW_MODE_BY_BOX = {}     # jsui box id -> its view mode
VIEW_DEFAULTS = {}        # view mode -> {message: the value it gets from the Init values}
GEN_PARAM_FROM_INIT = []  # (gen box id, Param name, the value the Init values send it, control name)

# Parameter Visibility (the parameter_invisible attribute; Cycling '74, Parameter Mode / live.* references):
# "Stored Only" is stored with the set and in presets but not automatable; "Hidden" is "Not stored in the Live Set
# or presets, not visible to control surfaces, and not recorded in Live's undo history". The docs give no numbers:
# 1 is Stored Only (a Live preset of this device has the Steps / Accents values in its blob and not among the
# automatable parameters: references/ableton/example-2sl-stab-preset.xml); 2 for Hidden is the inspector's order,
# not yet seen in a saved file (see references/README.md).
PARAMETER_VISIBILITY_STORED_ONLY = 1
PARAMETER_VISIBILITY_HIDDEN = 2


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
        # text / texton are only the button's label; the names Live shows for its two states (automation lanes,
        # Push, presets) are the box's automation / automationon attributes, default "val1" / "val2" (Cycling '74,
        # live.text reference). Max saves them on the box and mirrors them in parameter_enum (references/README.md,
        # "Live presets"): a parameter_enum without them is overridden by the defaults.
        extra = {"text": short.lower(), "texton": short.lower(), "mode": v.pop("_mode", 1),
                 "automation": TOGGLE_ITEMS[0], "automationon": TOGGLE_ITEMS[1]}
        vals = {k: x for k, x in vals.items() if k != "_mode"}
        vals.update(parameter_enum=TOGGLE_ITEMS, parameter_mmax=1)
    b_id = box(cls=cls, rect=rect, ins=1, outs=outs[0], outtype=outs[1], varname=name.lower().replace(" ", "_"),
               parameter_enable=1, presentation=1, presentation_rect=[float(x) for x in prect],
               saved_attribute_attributes={"valueof": vals}, **annotation, **extra)
    CONTROL_BY_BOX[b_id] = (name, lambda value: value)
    return b_id


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

# note-on: pitch -> frequency target, velocity -> gate target, THEN a new note-on count -> its target (the voice
# starts on a new count, so it must already have the new pitch and velocity); note-off: gate 0. The trigger fixes
# the order (right outlet first). The count is what makes every note-on start: see the voice's in4.
on_order = box("t b l l", rect=(30, 215, 60, 22), ins=1, outs=3, outtype=["bang", "", ""])
on_pitch = box("unpack 0 0", rect=(30, 240, 80, 22), ins=1, outs=2, outtype=["int", "int"])
on_velocity = box("unpack 0 0", rect=(120, 240, 80, 22), ins=1, outs=2, outtype=["int", "int"])
mtof = box("mtof", rect=(30, 270, 40, 22), outtype=["float"])
vel = box("/ 127.", rect=(120, 270, 50, 22), ins=2, outtype=["float"])
offmsg = box("t 0", rect=(200, 270, 30, 22), outtype=["int"])
tgt_f = box("mc.target", rect=(30, 300, 70, 22), ins=2, outs=2)
tgt_g = box("mc.target", rect=(120, 300, 70, 22), ins=2, outs=2)
note_on_counter = box("counter 1 1000000", rect=(260, 240, 110, 22), ins=3, outs=4, outtype=["int", "", "", "int"])
tgt_note_on = box("mc.target", rect=(260, 270, 70, 22), ins=2, outs=2)
wire(on_order, note_on_counter, 0, 0)
wire(note_on_counter, tgt_note_on)
wire(alloc, on_order, 0, 0)
wire(on_order, on_pitch, 2, 0)
wire(on_order, on_velocity, 1, 0)
wire(on_pitch, mtof, 0, 0)
wire(on_velocity, vel, 1, 0)
wire(mtof, tgt_f)
wire(vel, tgt_g)
wire(alloc, offmsg, 1, 0)
wire(offmsg, tgt_g)
wire(alloc, tgt_f, 5, 1)
wire(alloc, tgt_g, 5, 1)
wire(alloc, tgt_note_on, 5, 1)

voice = box("mc.gen~ @chans 16", rect=(30, 350, 160, 22), ins=4, outs=2, outtype=["multichannelsignal"] * 2,
            patcher=gen_patcher(VOICE, 4, 2))
# the LFO: a cosine of a phasor~'s phase (cos~: "the cosine of 2pi times the input"), so the displays can read
# the phase itself (snapshot~ below) and draw the LFO in step with the sound
lfo_phase = box(f"phasor~ {INIT_IN_OWN_UNITS['LFO Rate']}", rect=(220, 300, 80, 22), ins=2, outs=1, outtype=["signal"])
lfo = box("cos~", rect=(220, 325, 40, 22), ins=1, outs=1, outtype=["signal"])
wire(lfo_phase, lfo)
wire(lfo, voice, 0, 2)
wire(tgt_f, voice, 0, 0)
wire(tgt_g, voice, 0, 1)
wire(tgt_note_on, voice, 0, 3)
# Busy: mc.noteallocator~ frees a voice when it has had its note-off and "the corresponding audio signal in the
# multichannel input goes to zero" (Cycling '74, MC Managed Polyphony). Not the sound, which crosses zero while it
# plays: the voice's own busy state, 1 until its envelope has finished.
wire(voice, alloc, 1, 0)

mix = box("mc.mixdown~ 1 @autogain 0", rect=(30, 390, 170, 22), ins=2, outs=1, outtype=["multichannelsignal"])
fx = box("gen~", rect=(30, 430, 120, 22), ins=2, outs=FX_OUTLETS, outtype=["signal"] * FX_OUTLETS,
         patcher=gen_patcher(FX, 2, FX_OUTLETS))
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
    if msg != "playing":
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

# the stab machine's clock: a 16th metro that follows Live's transport. Each bang asks [transport] for Live's
# song position in ticks (its 8th outlet); the brain plays the 16th it lands on, once (see tick() there).
metro = box("metro 16n @quantize 16n", rect=(30, 520, 160, 22), ins=2, outs=1, outtype=["bang"])
# Live playing or not, in a set order (trigger: right to left): the brain hears it first, then the FX, and
# only then does the metro start (its immediate bang must find the brain playing)
playing_order = box("t i i i", rect=(940, 210, 60, 22), ins=1, outs=3, outtype=["int", "int", "int"])
wire(observers[2], playing_order)
wire(playing_order, find_box_by_text("prepend playing"), 2, 0)
ptransport = box("prepend transport", rect=(720, 250, 110, 22))
wire(playing_order, ptransport, 1, 0)
wire(ptransport, fx)
wire(playing_order, metro, 0, 0)
# the machine also needs the tempo, for its own clock when Live is stopped
pbpm = box("prepend bpm", rect=(620, 250, 80, 22))
wire(obs, pbpm)
wire(pbpm, fx)
ptempo = box("prepend tempo", rect=(520, 250, 90, 22))
wire(obs, ptempo)
wire(ptempo, memory, 0, 1)
trans = box("transport", rect=(30, 550, 70, 22), ins=2, outs=9)
ptick = box("prepend tick", rect=(30, 610, 80, 22))
wire(metro, trans)
wire(trans, ptick, 7, 0)          # raw ticks: 480 per quarter note
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


def view(mode, x, y, w, h, page, background=False, info=None):
    # background=True: Max's "Include in Background", so it always sits behind every other object
    extra = {"ignoreclick": 1, "background": 1} if background else {}
    if info:
        # info: an INFO key, shown in Live's Info View on hover (as for parameters)
        title, text = INFO[info]
        INFO_USED.add(info)
        extra.update(annotation_name=title, annotation=text)
    elif not background:
        # only the background (it ignores clicks, so it is never hovered) may go without
        raise SystemExit(f"2sl-stab.py: view {mode!r} has no Info View text: pass info= with an INFO key")
    b = box(cls="jsui", rect=(1500 + x, 1000 + y, w, h), ins=1, outs=1, filename="2sl-stab-view.js",
            jsarguments=[mode], presentation=1, presentation_rect=[float(x), float(y), float(w), float(h)], border=0,
            **extra)
    VIEWS.append(f"view_{mode}")
    VIEW_MODE_BY_BOX[b] = mode
    return on_page(page, b, f"view_{mode}")


def derived(b_id, control_name, transform):
    """`b_id` passes on control `control_name`'s value transformed (e.g. [- 1], an [expr] lookup)."""
    CONTROL_BY_BOX[b_id] = (control_name, transform)
    return b_id


def tell(src, msg, dst, inlet=0, scale=None):
    if src in CONTROL_BY_BOX and msg is not None:
        control_name, transform = CONTROL_BY_BOX[src]
        if control_name in INIT_VALUE:
            sent = transform(INIT_VALUE[control_name]) * (scale if scale is not None else 1)
            if dst in VIEW_MODE_BY_BOX:
                VIEW_DEFAULTS.setdefault(VIEW_MODE_BY_BOX[dst], {})[msg] = sent
            elif dst in (voice, fx):
                GEN_PARAM_FROM_INIT.append((dst, msg, sent, control_name))
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


def dial(name, short, target, msg, mmin, mmax, unit, x, y, page, exp=1.0, scale=1.0, inlet=0, views=()):
    vn = name.lower().replace(" ", "_")
    initial_value = saved_control(name, vn, minimum=mmin, maximum=mmax)
    pid = param("live.dial", name, short, (1500 + x, 700 + y, DW, DH), 0, (x, y, DW, DH),
                parameter_mmin=float(mmin), parameter_mmax=float(mmax), parameter_initial_enable=1,
                parameter_initial=[float(initial_value)], parameter_unitstyle=unit, parameter_exponent=float(exp))
    on_page(page, pid, vn)
    CONTROLS["dial"].append(vn)
    if target is not None:
        tell(pid, msg, target, inlet, scale if scale != 1.0 else None)
    for v, vmsg in views:
        tell(pid, vmsg, v, 0, scale if scale != 1.0 else None)
    return pid


def menu(name, short, items, x, y, w, page):
    vn = name.lower().replace(" ", "_")
    pid = param("live.menu", name, short, (1500 + x, 640 + y, w, 15), 2, (x, y, w, 15),
                parameter_enum=items, parameter_mmax=len(items) - 1, parameter_initial_enable=1,
                parameter_initial=[saved_control(name, vn, items=items)])
    CONTROLS["menu"].append(vn)
    return on_page(page, pid, vn)


def tabs(name, short, items, x, y, w, page, h=15, lines=1):
    """Selector buttons (a live.tab), like the waveform and footage switches on a Jupiter or Juno.
    lines = len(items) stacks them vertically, like a slide switch."""
    vn = name.lower().replace(" ", "_")
    pid = param("live.tab", name, short, (1500 + x, 600 + y, w, h), 2, (x, y, w, h),
                parameter_enum=items, parameter_mmax=len(items) - 1, parameter_initial_enable=1,
                parameter_initial=[saved_control(name, vn, items=items)])
    find(pid).update(num_lines_patching=lines, num_lines_presentation=lines)
    CONTROLS["tab"].append(vn)
    return on_page(page, pid, vn)


TOGGLE_ITEMS = ["off", "on"]      # a live.text's state names in Live (param() sets automation / automationon)


def toggle(name, short, x, y, w, h, page, mode=1):
    """A live.text: a toggle (mode 1, saved, with an Init value) or a button (mode 0)."""
    vn = name.lower().replace(" ", "_")
    kw = ({"parameter_initial_enable": 1, "parameter_initial": [saved_control(name, vn, items=TOGGLE_ITEMS)]}
          if mode == 1 else {})
    pid = param("live.text", name, short, (1500 + x, 660 + y, w, h), 2, (x, y, w, h), _mode=mode, **kw)
    CONTROLS["text"].append(vn)
    return on_page(page, pid, vn)


def stored(name, init):
    """A parameter Live stores with the set but doesn't show or automate.

    Float type with an Int unit style: Live's Int type holds only 256 values (0-255), which cut a 16-step
    bit mask down to its first 8 steps. Cycling '74's param reference gives this pattern for bigger integers."""
    pid = param("live.numbox", name, name, (1500, 1400 + (30 * len(boxes)) % 300, 60, 15), 0, (0, 0, 60, 15),
                parameter_mmin=0.0, parameter_mmax=65535.0, parameter_initial_enable=1, parameter_initial=[float(init)],
                parameter_unitstyle=0, parameter_invisible=PARAMETER_VISIBILITY_STORED_ONLY)
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
link = view("link", 12, 3, 56, 15, None, info="Link view")
# The page switch is Hidden (Parameter Visibility): not saved with the set or in presets, not in Live's undo history,
# not automatable, so only a click turns the page. The device always opens on the play page (its initial value).
page_tabs = param("live.tab", "Page", "Page", (1500, 560, 144, 15), 2, (80.0, 3.0, 144.0, 15.0),
                  parameter_enum=PAGE_NAMES, parameter_mmax=2, parameter_initial_enable=1, parameter_initial=[0],
                  parameter_invisible=PARAMETER_VISIBILITY_HIDDEN)
find(page_tabs).update(num_lines_patching=1, num_lines_presentation=1, varname="page")
CONTROLS["tab"].append("page")
tell(page_tabs, "page", ui)
vol = param("live.numbox", "Volume", "Volume", (1500, 520, 64, 15), 0, (824.0, 3.0, 64.0, 15.0),
            parameter_mmin=-36.0, parameter_mmax=12.0, parameter_initial_enable=1,
            parameter_initial=[float(saved_control("Volume", "volume", minimum=-36.0, maximum=12.0))],
            parameter_unitstyle=4)
find(vol).update(varname="volume")
CONTROLS["numbox"].append("volume")
tell(vol, "volume", fx)
stop_btn = param("live.text", "Stop", "Stop", (1500, 540, 48, 15), 2, (900.0, 3.0, 48.0, 15.0), _mode=0)
find(stop_btn).update(varname="stop")
CONTROLS["text"].append("stop")

# ---- Stop: the panic button. Notes off and latch cleared (brain), Freeze off (ui), and a new `panic`
# number to the voices (ramp to silence) and the echo (muted until it has emptied). Live's transport
# stopping doesn't run it: like any instrument, the device just stops getting notes and rings out.
stopt = box("t b b", rect=(1100, 200, 40, 22), outs=2, outtype=["bang", "bang"])
stopmsg = box(cls="message", text="stop", rect=(1230, 230, 40, 22), ins=2, outs=1)
panics = box("counter 1 1000000", rect=(1100, 230, 110, 22), ins=3, outs=4, outtype=["int", "", "", "int"])
panicmsg = box("prepend panic", rect=(1100, 260, 90, 22))
wire(stop_btn, stopt)
wire(stopt, stopmsg, 1, 0)
wire(stopmsg, memory, 0, 1)
wire(stopmsg, ui)
wire(stopt, panics, 0, 0)
wire(panics, panicmsg)
for dst in (voice, fx):
    wire(panicmsg, dst)



# ================= PLAY: chord | machine | dub | pump =================
C1, C2, C3, C4 = 12, 220, 524, 732
v_chord = view("chord", C1, VIEW_Y, 184, VIEW_H, "play", info="Chord view")
chordm = menu("Chord", "Chord", ["poly", "minor", "m7", "m9", "m11", "sus4", "fifths", "dark"], C1, ROW_Y, 112, "play")
tell(chordm, "shape", memory, 1)
ink = toggle("In Key", "In Key", C1 + 116, ROW_Y, 68, 15, "play")
tell(ink, "inkey", memory, 1)
dial("Tone", "Tone", voice, "tonemac", -100, 100, 5, C1, DIAL_Y, "play", scale=0.01)
dial("Length", "Length", voice, "lenmac", -100, 100, 5, C1 + 70, DIAL_Y, "play", scale=0.01)
dial("Drift", "Drift", memory, "drift", 0, 100, 5, C1 + 140, DIAL_Y, "play", scale=0.01, inlet=1)

v_steps = view("steps", C2, VIEW_Y, 280, VIEW_H, "play", info="Steps view")
wire(memory, v_steps, 2, 0)
wire(v_steps, memory, 0, 1)          # clicks edit steps
wire(memory, v_chord, 3, 0)
mach = toggle("Machine", "Machine", C2, ROW_Y, 72, 15, "play")
tell(mach, "machine", memory, 1)
lat = toggle("Latch", "Latch", C2 + 76, ROW_Y, 56, 15, "play")
tell(lat, "latch", memory, 1)
BRAIN_PATH = os.path.join(ROOT, "devices", "2sl-stab", "2sl-stab.js")


def brain_patterns():
    """The machine's patterns as the brain defines them (its PATTERNS, one `"X..x...", // name` line each):
    [(name, steps)], steps 16 of 0 rest, 1 hit, 2 accent. The Pattern menu and the presets' stored steps use them."""
    with open(BRAIN_PATH) as brain_file:
        found = re.search(r"var PATTERNS = \[\n(.*?)\n\];", brain_file.read(), re.S)
    if not found:
        raise SystemExit(f"2sl-stab.py: no `var PATTERNS = [ ... ];` block in {BRAIN_PATH}")
    patterns = []
    for line in found.group(1).split("\n"):
        pattern_line = re.fullmatch(r'\s*"([Xx.]{16})",?\s*//\s*(\S.*?)(?:\s*\(.*\))?\s*', line)
        if not pattern_line:
            raise SystemExit(f"2sl-stab.py: can't read this PATTERNS line in {BRAIN_PATH}: {line!r}")
        patterns.append((pattern_line.group(2), [{"X": 2, "x": 1, ".": 0}[c] for c in pattern_line.group(1)]))
    return patterns


MACHINE_PATTERNS = brain_patterns()
pat = menu("Pattern", "Pattern", [name for name, _ in MACHINE_PATTERNS], C2 + 136, ROW_Y, 144, "play")
tell(pat, "pattern", memory, 1)
dial("Density", "Density", memory, "density", 0, 100, 5, C2, DIAL_Y, "play", scale=0.01, inlet=1)
dial("Throws", "Throws", memory, "throws", 0, 100, 5, C2 + 56, DIAL_Y, "play", scale=0.01, inlet=1)
dial("Gate", "Gate", memory, "length", 1, 4, 0, C2 + 112, DIAL_Y, "play", inlet=1)
dial("Shift", "Shift", memory, "shift", 0, 15, 0, C2 + 168, DIAL_Y, "play", inlet=1)



def pattern_bits(steps):
    """A pattern as the brain stores it (its store()): bit i of the hits for a hit or accent on step i, of the
    accents for an accent."""
    hit_bits = sum(1 << i for i, step in enumerate(steps) if step >= 1)
    accent_bits = sum(1 << i for i, step in enumerate(steps) if step == 2)
    return hit_bits, accent_bits


# the machine's steps as saved with the set (Stored Only): they start as the Init pattern
init_hit_bits, init_accent_bits = pattern_bits(MACHINE_PATTERNS[INIT_VALUE["Pattern"]][1])
sbits = stored("Steps", init_hit_bits)
abits = stored("Accents", init_accent_bits)
tell(sbits, "stepbits", memory, 1)
tell(abits, "accbits", memory, 1)
bitroute = box("route stepbits accbits", rect=(1100, 120, 140, 22), ins=1, outs=3)
wire(memory, bitroute, 4, 0)
wire(bitroute, sbits, 0, 0)
wire(bitroute, abits, 1, 0)

v_echo = view("echo", C3, VIEW_Y, 184, VIEW_H, "play", info="Echo view")
# Every 33 ms, one reading of the echo: its level (the clock), then the round it is in now and its last whole
# rounds (the FX keeps them, so none is lost between readings), as one message:
#   echo <level> <round now> <newest whole round> ... <oldest>
# The trigger fires right to left: the banged snapshot~s fill pack's cold inlets, then the level its hot one.
# (A bang, never a number, into those snapshot~s: a number into the left inlet would switch on their own clock.)
echo_rounds_read = 1 + ECHO_ROUNDS_KEPT
lvl_snap = box("snapshot~ 33", rect=(160, 470, 80, 22), ins=2, outs=1, outtype=["float"])
wire(fx, lvl_snap, 2, 0)
echo_reading_order = box("t f" + " b" * echo_rounds_read, rect=(160, 495, 200, 22), ins=1, outs=1 + echo_rounds_read,
                         outtype=["float"] + ["bang"] * echo_rounds_read)
echo_reading = box("pack" + " 0." * (1 + echo_rounds_read), rect=(160, 560, 260, 22), ins=1 + echo_rounds_read, outs=1)
wire(lvl_snap, echo_reading_order)
wire(echo_reading_order, echo_reading, 0, 0)
for k in range(1, 1 + echo_rounds_read):      # k = 1: the round now (out4); 2 on: the whole rounds, newest first
    round_snap = box("snapshot~", rect=(160 + 30 * k, 525, 70, 22), ins=2, outs=1, outtype=["float"])
    wire(echo_reading_order, round_snap, k, 0)
    wire(fx, round_snap, 2 + k, 0)
    wire(round_snap, echo_reading, 0, k)
tell(echo_reading, "echo", v_echo)
throw_btn = toggle("Throw", "Throw", C3, ROW_Y, 88, 15, "play", mode=0)
wire(throw_btn, tthrow)
throwmsg = box(cls="message", text="throw", rect=(300, 520, 45, 22), ins=2, outs=1)
wire(tthrow, throwmsg, 0, 0)
wire(throwmsg, v_echo)
frz = toggle("Freeze", "Freeze", C3 + 96, ROW_Y, 88, 15, "play")
tell(frz, "freeze", fx)
tell(frz, "freeze", v_echo)
dial("Dub", "Dub", fx, "dub", 0, 100, 5, C3 + 56, DIAL_Y, "play", scale=0.01)
divs = menu("Echo Time", "Time", ["1/16", "1/8", "1/8d", "1/4", "1/4d", "1/2"], C3 + 120, DIAL_Y + 17, 64, "play")
beats = box("expr ($i1==0)*0.25 + ($i1==1)*0.5 + ($i1==2)*0.75 + ($i1==3)*1. + ($i1==4)*1.5 + ($i1==5)*2.",
            rect=(1100, 700, 400, 22), ins=1, outs=1)
wire(divs, beats)
wire(beats, pak, 0, 1)
# Send: the echo's level as the dial shows it (gain = Send / 100); exponent 2 squares the dial's travel, the curve
# the echo send had when Dub set it (0.9 dub^2), so the low end is as fine as before
dial("Send", "Send", fx, "echosend", 0, 100, 5, C3, DIAL_Y, "play", exp=2.0, scale=0.01, views=[(v_echo, "send")])

v_pump = view("pump", C4, VIEW_Y, 216, VIEW_H, "play", info="Pump view")
ph_snap = box("snapshot~ 33", rect=(250, 430, 80, 22), ins=2, outs=1, outtype=["float"])
wire(beat, ph_snap)
tell(ph_snap, "phase", v_pump)
tell(obs, "tempo", v_pump)            # Live's tempo: the pump's attack is in ms, so its shape depends on it
prate = menu("Pump Rate", "Rate", ["1/4", "1/8", "1/16"], C4, ROW_Y, 96, "play")
rmult = derived(box("expr ($i1==0)*1. + ($i1==1)*2. + ($i1==2)*4.", rect=(1100, 760, 260, 22), ins=1, outs=1),
                "Pump Rate", lambda v: [1.0, 2.0, 4.0][v])
wire(prate, rmult)
tell(rmult, "pumprate", fx)
tell(rmult, "rate", v_pump)
dial("Pump", "Depth", fx, "pumpdepth", 0, 100, 5, C4, DIAL_Y, "play", scale=0.01, views=[(v_pump, "depth")])
dial("Pump Attack", "Attack", fx, "pumpatk", 1, 40, 2, C4 + 56, DIAL_Y, "play", exp=2.0, views=[(v_pump, "atk")])
dial("Pump Release", "Release", fx, "pumprel", 10, 95, 5, C4 + 112, DIAL_Y, "play", scale=0.01, views=[(v_pump, "rel")])
dial("Pump Curve", "Curve", fx, "pumpcurve", 0, 100, 5, C4 + 168, DIAL_Y, "play", scale=0.01, views=[(v_pump, "curve")])

# ================= OSC: sub | DCO 1 | DCO 2 | mixer | LFO =================
# Sections 24 px apart with the page rule in the middle of each gap, 12 px margins: 12 + 112 + 24 + 196 + 24 + 196
# + 24 + 96 + 24 + 240 + 12 = 960. The mixer is two columns of dials (44 + 8 + 44).
SUB_W, DCO_W, MIX_W, LFO_W, SECTION_GAP = 112, 196, 96, 240, 24
OS = 12
O1 = OS + SUB_W + SECTION_GAP
O2 = O1 + DCO_W + SECTION_GAP
O3 = O2 + DCO_W + SECTION_GAP
O4 = O3 + MIX_W + SECTION_GAP
if O4 + LFO_W != W - 12:
    raise SystemExit(f"2sl-stab.py: the osc page's sections end at {O4 + LFO_W}, not {W - 12}")
OSC_RULES = [x - SECTION_GAP // 2 for x in (O1, O2, O3, O4)]
DCO_WAVE_TABS_W, DCO_OCT_TABS_W = 120, 72                    # + 4 between = DCO_W

# the sub: DCO 1 divided down (its level is in the mixer)
v_sub = view("sub", OS, VIEW_Y, SUB_W, VIEW_H, "osc", info="Sub view")
sub_mode_tab = tabs("Sub Mode", "Sub", ["-1 sq", "-2 sq", "-2 pls"], OS, ROW_Y, SUB_W, "osc")
tell(sub_mode_tab, "submode", voice)
tell(sub_mode_tab, "submode", v_sub)

v_osc1 = view("osc1", O1, VIEW_Y, DCO_W, VIEW_H, "osc", info="DCO1 view")
w1 = tabs("DCO1 Wave", "Wave 1", ["saw", "pulse", "both"], O1, ROW_Y, DCO_WAVE_TABS_W, "osc")
tell(w1, "wave1", voice)
tell(w1, "wave1", v_osc1)
o1 = tabs("DCO1 Octave", "Oct 1", ["16'", "8'", "4'"], O1 + DCO_WAVE_TABS_W + 4, ROW_Y, DCO_OCT_TABS_W, "osc")
o1m = derived(box("- 1", rect=(1100, 820, 40, 22), ins=2, outtype=["int"]), "DCO1 Octave", lambda v: v - 1)
wire(o1, o1m)
tell(o1m, "oct1", voice)
pw_dial = dial("PW", "PW", voice, "pw", 50, 95, 5, O1, DIAL_Y, "osc", scale=0.01, views=[(v_osc1, "pw")])
pwm_dial = dial("PWM", "PWM", voice, "pwmamt", 0, 100, 5, O1 + 56, DIAL_Y, "osc", scale=0.01, views=[(v_osc1, "pwm")])

v_osc2 = view("osc2", O2, VIEW_Y, DCO_W, VIEW_H, "osc", info="DCO2 view")
w2 = tabs("DCO2 Wave", "Wave 2", ["saw", "pulse", "tri"], O2, ROW_Y, DCO_WAVE_TABS_W, "osc")
tell(w2, "wave2", voice)
tell(w2, "wave2", v_osc2)
o2 = tabs("DCO2 Octave", "Oct 2", ["16'", "8'", "4'"], O2 + DCO_WAVE_TABS_W + 4, ROW_Y, DCO_OCT_TABS_W, "osc")
o2m = derived(box("- 1", rect=(1150, 820, 40, 22), ins=2, outtype=["int"]), "DCO2 Octave", lambda v: v - 1)
wire(o2, o2m)
tell(o2m, "oct2", voice)
dial("Semi", "Semi", voice, "semi", -12, 12, 7, O2, DIAL_Y, "osc", views=[(v_osc2, "semi")])
dial("Fine", "Fine", voice, "fine", 0, 50, 1, O2 + 56, DIAL_Y, "osc", views=[(v_osc2, "fine")])

# the mixer: four levels as a square of dials. No display.
MIX_TOP_Y, MIX_COL2 = 64, O3 + 52
dial("OSC 1", "OSC 1", voice, "lvl1", 0, 100, 5, O3, MIX_TOP_Y, "osc", scale=0.01)
dial("OSC 2", "OSC 2", voice, "lvl2", 0, 100, 5, MIX_COL2, MIX_TOP_Y, "osc", scale=0.01)
dial("Sub", "Sub", voice, "sublvl", 0, 100, 5, O3, DIAL_Y, "osc", scale=0.01)
dial("Noise", "Noise", voice, "noiseamt", 0, 100, 5, MIX_COL2, DIAL_Y, "osc", scale=0.01)

v_lfo = view("lfo", O4, VIEW_Y, LFO_W, VIEW_H, "osc", info="LFO view")
tell(pwm_dial, "pwm", v_lfo, 0, 0.01)
# PW and PWM shape both DCOs' pulse (the voice's `width`), so DCO 2's display gets them too
tell(pw_dial, "pw", v_osc2, 0, 0.01)
tell(pwm_dial, "pwm", v_osc2, 0, 0.01)
# the LFO's phase, read from the audio, for every display that draws the LFO moving
lfo_snap = box("snapshot~ 33", rect=(310, 300, 80, 22), ins=2, outs=1, outtype=["float"])
wire(lfo_phase, lfo_snap)
for lfo_view in (v_lfo, v_osc1, v_osc2):
    tell(lfo_snap, "lfophase", lfo_view)
dial("LFO Rate", "Rate", lfo_phase, None, 0.05, 12, 3, O4, DIAL_Y, "osc", exp=3.0,
     views=[(v_lfo, "lforate"), (v_osc1, "lforate"), (v_osc2, "lforate")])   # the DCOs' PWM follows the LFO too
dial("Vibrato", "Vibrato", voice, "vibamt", 0, 100, 5, O4 + 64, DIAL_Y, "osc", scale=0.01, views=[(v_lfo, "vib")])
dial("LFO Filter", "Filter", voice, "lfofilt", 0, 100, 5, O4 + 128, DIAL_Y, "osc", scale=0.01, views=[(v_lfo, "lfofilt")])

# ================= SHAPE: filter | envelope | drive =================
F, E, D = 12, 376, 680
v_filter = view("filter", F, VIEW_Y, 340, VIEW_H, "shape", info="Filter view")
dial("Cutoff", "Cutoff", voice, "cutoff", 40, 12000, 3, F, DIAL_Y, "shape", exp=3.0, views=[(v_filter, "cutoff")])
dial("Resonance", "Reso", voice, "reso", 0, 100, 5, F + 68, DIAL_Y, "shape", scale=0.01, views=[(v_filter, "reso")])
dial("Env Amount", "Env", voice, "envamt", 0, 100, 5, F + 136, DIAL_Y, "shape", scale=0.01, views=[(v_filter, "envamt")])
dial("Key Track", "Key", voice, "keytrack", 0, 100, 5, F + 204, DIAL_Y, "shape", scale=0.01)
dial("Velocity Filter", "Vel", voice, "velfilt", 0, 100, 5, F + 272, DIAL_Y, "shape", scale=0.01)

v_env = view("env", E, VIEW_Y, 280, VIEW_H, "shape", info="Envelope view")
dial("Attack", "Attack", voice, "atk", 0.5, 4000, 2, E, DIAL_Y, "shape", exp=3.0, views=[(v_env, "atk")])
dial("Decay", "Decay", voice, "dec", 5, 6000, 2, E + 70, DIAL_Y, "shape", exp=3.0, views=[(v_env, "dec")])
dial("Sustain", "Sustain", voice, "sus", 0, 100, 5, E + 140, DIAL_Y, "shape", scale=0.01, views=[(v_env, "sus")])
dial("Release", "Release", voice, "rel", 5, 6000, 2, E + 210, DIAL_Y, "shape", exp=3.0, views=[(v_env, "rel")])

v_drive = view("drive", D, VIEW_Y, 268, VIEW_H, "shape", info="Drive view")
dial("Drive", "Drive", fx, "drive", 0, 100, 5, D, DIAL_Y, "shape", scale=0.01, views=[(v_drive, "drive")])

width = W

# Play-page macros also drive the shape-page displays
for name, v, m in [("Tone", v_filter, "tone"), ("Length", v_env, "len")]:
    src = next(x["box"]["id"] for x in boxes if x["box"].get("varname") == SAVED_CONTROLS[name]["varname"])
    tell(src, m, v, 0, 0.01)
# the page tab also tells the chrome which rules and labels to draw
tell(page_tabs, "page", chrome)

# what the chrome draws per page: rules between sections, labels and hints (text, x, baseline, kind)
HEADER = [["out", 800, 15, "label"]]
LAYOUT = {
    "subtitle": 236,               # 12 px after the page tabs (80 + 144)
    "version": VERSION,
    "pages": [
        {"rules": [208, 512, 720],
         "labels": HEADER + [["echo time", C3 + 120, DIAL_Y + 12, "label"], ["pump rate", C4 + 104, ROW_Y + 12, "hint"]]},
        {"rules": OSC_RULES,
         "labels": HEADER + [["dco 1 divided down", OS, DIAL_Y + 24, "hint"],
                             ["pw: pulse width", O1 + 108, DIAL_Y + 24, "hint"], ["pwm: lfo on pw", O1 + 108, DIAL_Y + 38, "hint"],
                             ["semi 7:", O2 + 108, DIAL_Y + 24, "hint"], ["a fifth up", O2 + 108, DIAL_Y + 38, "hint"],
                             ["mixer", O3, VIEW_Y + 12, "label"],
                             ["one lfo for all voices", O4, ROW_Y + 12, "hint"]]},
        {"rules": [364, 668],
         "labels": HEADER + [["grey: where the envelope opens it", F, ROW_Y + 12, "hint"],
                             ["one envelope: amp and filter", E, ROW_Y + 12, "hint"],
                             ["tape saturation, before the echo", D, ROW_Y + 12, "hint"]]},
    ],
}

# ---- presets: src/2sl-stab-presets.json, checked against the controls --------------------------
unknown_init_controls = set(INIT_IN_OWN_UNITS) - set(SAVED_CONTROLS)
if unknown_init_controls:
    raise SystemExit(f"2sl-stab.py: 'init' in {PRESET_DATA_NAME} names no saved control: {sorted(unknown_init_controls)}")
PRESET_FIELDS = {"name", "group", "idea", "values"}
PRESETS = []              # (name, group, idea, {control: value as the control holds it}), every control set
for preset_number, preset in enumerate(PRESET_DATA["presets"]):
    where = f"{PRESET_DATA_NAME}, preset {preset_number + 1} ({preset.get('name')!r})"
    if set(preset) != PRESET_FIELDS:
        raise SystemExit(f"2sl-stab.py: {where} must have exactly {sorted(PRESET_FIELDS)}, not {sorted(preset)}")
    if not all(isinstance(preset[field], str) and preset[field] for field in ("name", "group", "idea")):
        raise SystemExit(f"2sl-stab.py: {where}: name, group and idea must be non-empty text")
    unknown_controls = set(preset["values"]) - set(SAVED_CONTROLS)
    if unknown_controls:
        raise SystemExit(f"2sl-stab.py: {where} sets controls the device doesn't have: {sorted(unknown_controls)}")
    values_as_held = dict(INIT_VALUE)
    for control_name, value in preset["values"].items():
        values_as_held[control_name] = value_as_held(control_name, value, where)
    PRESETS.append((preset["name"], preset["group"], preset["idea"], values_as_held))
preset_names = [name for name, _, _, _ in PRESETS]
if len(set(preset_names)) != len(preset_names):
    raise SystemExit(f"2sl-stab.py: preset names used twice in {PRESET_DATA_NAME}: "
                     f"{sorted({n for n in preset_names if preset_names.count(n) > 1})}")

# the gen~ Param defaults must be what the Init values send them (the sound before Live recalls the controls)
GEN_CODE = {voice: VOICE, fx: FX}
gen_param_mismatches = []
for gen_box, param_name, sent, control_name in GEN_PARAM_FROM_INIT:
    declared = re.search(r"Param " + param_name + r"\(([^,)]+)", GEN_CODE[gen_box])
    if not declared:
        gen_param_mismatches.append(f"{control_name} -> {param_name}: no such Param")
    elif abs(float(declared.group(1)) - sent) > 1e-9:
        gen_param_mismatches.append(f"{control_name} -> Param {param_name}({declared.group(1)}), the Init values send {sent:g}")
if gen_param_mismatches:
    raise SystemExit("2sl-stab.py: gen~ Param defaults disagree with the Init values:\n  "
                     + "\n  ".join(gen_param_mismatches))

if set(INFO) - INFO_USED:
    raise SystemExit(f"2sl-stab.py: INFO has text for no parameter or view: {sorted(set(INFO) - INFO_USED)}")

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
# Light or dark, from Live's theme: shared by the displays and the UI script (both are generated with it).
THEME_FROM_LIVE_JS = """
var THEMES = %s;
var liveColourMissingReported = false;
/** The 2sl tokens for Live's theme: light when Live's surface colour (live_surface_bg) is light. If Max can't
 *  give that colour, dark, and the Max window says which colour was missing (once, until it is back). */
function themeFromLive(who) {
  var surface = null, failure = "";
  try { surface = max.getcolor("live_surface_bg"); } catch (e) { failure = String(e); }
  var usable = surface && surface.length >= 3 && isFinite(surface[0]) && isFinite(surface[1]) && isFinite(surface[2]);
  if (!usable) {
    if (!liveColourMissingReported) {
      liveColourMissingReported = true;
      error("2sl stab (" + who + "): Live colour live_surface_bg is missing (max.getcolor gave " +
            (failure || JSON.stringify(surface)) + "): drawing in the dark theme\\n");
    }
    return THEMES.dark;
  }
  liveColourMissingReported = false;
  var luminance = 0.2126 * surface[0] + 0.7152 * surface[1] + 0.0722 * surface[2];
  return luminance > 0.5 ? THEMES.light : THEMES.dark;
}""".strip() % json.dumps(THEMES)
view_js = open(os.path.join(HERE, "2sl-stab-view.template.js")).read()
glyphs = open(os.path.join(HERE, "cozette-glyphs.js")).read()
view_js = (view_js.replace("/*COZETTE*/", glyphs.strip()).replace("/*THEME_FROM_LIVE*/", THEME_FROM_LIVE_JS)
           .replace("/*VIEW_DEFAULTS*/", json.dumps(VIEW_DEFAULTS)).replace("/*LAYOUT*/", "var LAYOUT = " + json.dumps(LAYOUT) + ";"))
open(os.path.join(ROOT, "devices", "2sl-stab", "2sl-stab-view.js"), "w").write(view_js)
ui_js = open(os.path.join(HERE, "2sl-stab-ui.template.js")).read()
ui_js = (ui_js.replace("/*PAGES*/", json.dumps(PAGES))
         .replace("/*CONTROLS*/", json.dumps(CONTROLS)).replace("/*VIEWS*/", json.dumps(VIEWS)).replace("/*THEME_FROM_LIVE*/", THEME_FROM_LIVE_JS))
open(os.path.join(ROOT, "devices", "2sl-stab", "2sl-stab-ui.js"), "w").write(ui_js)

# every name the UI script looks up must name exactly one box (it errors at run time otherwise)
BOX_VARNAMES = [x["box"]["varname"] for x in boxes if "varname" in x["box"]]
UI_LOOKUPS = ({n for k in CONTROLS for n in CONTROLS[k]} | set(VIEWS)
              | {n for k in PAGES for n in PAGES[k]} | {"freeze"})
if UI_LOOKUPS - set(BOX_VARNAMES):
    raise SystemExit(f"2sl-stab.py: the UI script looks up names no box has: {sorted(UI_LOOKUPS - set(BOX_VARNAMES))}")
if len(BOX_VARNAMES) != len(set(BOX_VARNAMES)):
    raise SystemExit(f"2sl-stab.py: varnames used twice: {sorted({n for n in BOX_VARNAMES if BOX_VARNAMES.count(n) > 1})}")

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

# ---- LIVE PRESETS: one Live device preset (.adv) per sound, next to the device ------------------------------
# A Live preset of a Max device is gzipped XML: the device's file reference and every parameter's value, not the
# device itself. The schema here is the one Live 12.4.6 wrote for this device (references/ableton/
# example-2sl-stab-preset.xml), used as the template: everything but the file reference, the parameter list and
# the stored-only blob is kept as Live wrote it. See references/README.md, "Live presets", for each choice below.

LIVE_PRESET_TEMPLATE_PATH = os.path.join(ROOT, "references", "ableton", "example-2sl-stab-preset.xml")
PARAMETER_TYPE_FLOAT, PARAMETER_TYPE_ENUM = 0, 2            # Max's parameter_type (live.* references)
AMXD_CRC_BYTES = 16384                                      # OriginalCrc covers the file's first 16 KB


def amxd_crc(path):
    """Live's OriginalCrc of a device file: CRC-16 (poly 0x8005, init 0, not reflected, the "BUYPASS" variant) of
    its first 16384 bytes. Matches Live's own value for this device (19576) and for Ableton's OSC Leap Motion.amxd."""
    with open(path, "rb") as device_file:
        crc = 0
        for byte in device_file.read(AMXD_CRC_BYTES):
            crc ^= byte << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def live_number(value):
    """A number as Live writes it: whole numbers bare, others as a 32-bit float to 9 significant digits."""
    if float(value).is_integer():
        return str(int(value))
    return "%.9g" % struct.unpack("f", struct.pack("f", value))[0]


def set_value(element, path, value):
    found = element.find(path)
    if found is None:
        raise SystemExit(f"2sl-stab.py: the Live preset template has no {path} in <{element.tag}>")
    found.set("Value", value)


# Every parameter in the patch: automated-and-stored ones go in the parameter list, Stored Only ones in the blob,
# Hidden ones nowhere (as in Live's own file). The list is ordered by name, as Live wrote it.
listed_parameters, stored_only_parameter_names = [], []
for patch_box in (x["box"] for x in boxes):
    valueof = patch_box.get("saved_attribute_attributes", {}).get("valueof")
    if not patch_box.get("parameter_enable") or not valueof:
        continue
    visibility = valueof.get("parameter_invisible", 0)
    if visibility == PARAMETER_VISIBILITY_HIDDEN:
        continue
    if visibility == PARAMETER_VISIBILITY_STORED_ONLY:
        stored_only_parameter_names.append(valueof["parameter_longname"])
    elif visibility == 0:
        if valueof["parameter_type"] not in (PARAMETER_TYPE_FLOAT, PARAMETER_TYPE_ENUM):
            raise SystemExit(f"2sl-stab.py: Live presets: {valueof['parameter_longname']!r} has parameter_type "
                             f"{valueof['parameter_type']}; only float (0) and enum (2) have a known preset form")
        item_names_in_live = valueof.get("parameter_enum")
        if patch_box["maxclass"] == "live.text":
            # a live.text's state names in Live are its automation / automationon attributes (see param())
            item_names_in_live = [patch_box.get("automation"), patch_box.get("automationon")]
            if item_names_in_live != valueof.get("parameter_enum"):
                raise SystemExit(f"2sl-stab.py: Live presets: live.text {valueof['parameter_longname']!r} has "
                                 f"automation / automationon {item_names_in_live}, parameter_enum "
                                 f"{valueof.get('parameter_enum')}: Max keeps them the same")
        listed_parameters.append(dict(valueof, item_names_in_live=item_names_in_live))
    else:
        raise SystemExit(f"2sl-stab.py: Live presets: {valueof['parameter_longname']!r} has Parameter Visibility "
                         f"{visibility}, with no known preset form")
listed_parameters.sort(key=lambda valueof: valueof["parameter_longname"])
if sorted(stored_only_parameter_names) != ["Accents", "Steps"]:
    raise SystemExit(f"2sl-stab.py: Live presets know how to fill Steps and Accents, not {stored_only_parameter_names}")
unlisted_controls = set(SAVED_CONTROLS) - {valueof["parameter_longname"] for valueof in listed_parameters}
if unlisted_controls:
    raise SystemExit(f"2sl-stab.py: Live presets: saved controls missing from the parameter list: {sorted(unlisted_controls)}")

template_root = ElementTree.parse(LIVE_PRESET_TEMPLATE_PATH).getroot()
template_device = template_root.find("MxDeviceInstrument")
template_parameter_list = template_device.find("ParameterList/ParameterList")
PARAMETER_PROTOTYPE = {tag: template_parameter_list.find(tag) for tag in ("MxDFloatParameter", "MxDEnumParameter")}
if None in PARAMETER_PROTOTYPE.values():
    raise SystemExit(f"2sl-stab.py: {LIVE_PRESET_TEMPLATE_PATH} needs a float and an enum parameter to copy")
FIRST_PARAMETER_ID = min(int(p.get("Id")) for p in template_parameter_list)


def live_parameter_element(parameter_id, index, valueof, value):
    """One parameter as Live lists it, copied from the template's element of its type. Live holds a float's values
    (Default and the Manual value alike) as the dial's position spread linearly over [min, max], not in the dial's
    units: min + (max - min) * normalised^(1/exponent). A float's MIDI controller range is [max(min, 0), max(min, 1)].
    All as Live wrote them for all 51 of this device's (e.g. Decay 260 ms is saved as 2097.7)."""
    is_enum = valueof["parameter_type"] == PARAMETER_TYPE_ENUM
    element = ElementTree.fromstring(ElementTree.tostring(PARAMETER_PROTOTYPE["MxDEnumParameter" if is_enum else "MxDFloatParameter"]))
    element.set("Id", str(parameter_id))
    minimum = float(valueof.get("parameter_mmin", 0.0))
    maximum = float(len(valueof["parameter_enum"]) - 1) if is_enum else float(valueof.get("parameter_mmax", 127.0))
    initial_value = float((valueof.get("parameter_initial") or [minimum])[0])
    exponent = float(valueof.get("parameter_exponent", 1.0))

    def value_as_live_holds_it(value_in_dial_units):
        if is_enum:
            return value_in_dial_units
        return minimum + (maximum - minimum) * ((value_in_dial_units - minimum) / (maximum - minimum)) ** (1.0 / exponent)
    for path, text in [("Index", str(index)), ("Type", str(valueof["parameter_type"])), ("Name", valueof["parameter_longname"]),
                       ("ShortName", valueof["parameter_shortname"]), ("MinValue", live_number(minimum)),
                       ("MaxValue", live_number(maximum)), ("Default", live_number(value_as_live_holds_it(initial_value))),
                       ("Timeable/Manual", live_number(value_as_live_holds_it(float(value))))]:
        set_value(element, path, text)
    if is_enum:
        names = element.find("Names")
        for old_name in list(names):
            names.remove(old_name)
        for item_index, item in enumerate(valueof["item_names_in_live"]):
            name_element = ElementTree.SubElement(names, "Name", Id=str(item_index))
            ElementTree.SubElement(name_element, "Name", Value=item)
    else:
        set_value(element, "Timeable/MidiControllerRange/Min", live_number(max(minimum, 0.0)))
        set_value(element, "Timeable/MidiControllerRange/Max", live_number(max(minimum, 1.0)))
    return element


def stored_only_blob_text(values):
    """The Stored Only parameters as Live keeps them: JSON (4-space indent, names sorted), a NUL, as hex in lines of
    80 digits (decoded from Live's file: {"Accents": [ 1 ], "Steps": [ 73 ]})."""
    json_text = "{\n" + ",\n".join(f'    "{name}": [ {live_number(values[name])} ]' for name in sorted(values)) + "\n}"
    hex_digits = (json_text.encode() + b"\0").hex().upper()
    blob_indent = "\t" * 6
    return "\n" + "".join(blob_indent + hex_digits[i:i + 80] + "\n" for i in range(0, len(hex_digits), 80)) + "\t" * 5


def live_preset_file_name(name, group):
    file_name = (name if group == "init" else f"{group} - {name}") + ".adv"
    if re.search(r'[/\\:*?"<>|]', file_name):
        raise SystemExit(f"2sl-stab.py: preset {name!r} makes a file name with a character macOS or Windows refuses")
    return file_name


def write_live_presets(device_path):
    """Every preset as a Live preset next to the device file `device_path`, made for that exact file: it refers to it
    by its file name in the same folder (RelativePathType 1) with its size and OriginalCrc. Removes other .adv files
    there. Returns the file names written."""
    preset_folder = os.path.dirname(device_path)
    device_size, device_crc = os.path.getsize(device_path), amxd_crc(device_path)
    written_presets = []
    for preset_name, preset_group, preset_idea, preset_values in PRESETS:
        root = ElementTree.fromstring(ElementTree.tostring(template_root))
        device = root.find("MxDeviceInstrument")
        # the device file: relative to the preset (RelativePathType 1), so the presets work wherever the folder goes;
        # no absolute Path (the template's is a path on one Mac)
        file_ref = device.find("PatchSlot/Value/MxPatchRef/FileRef")
        set_value(file_ref, "RelativePathType", "1")
        set_value(file_ref, "RelativePath", os.path.basename(device_path))
        file_ref.remove(file_ref.find("Path"))
        set_value(file_ref, "OriginalFileSize", str(device_size))
        set_value(file_ref, "OriginalCrc", str(device_crc))
        set_value(device, "PatchSlot/Value/MxPatchRef/LastModDate", "0")      # a fixed date: the build is repeatable
        set_value(device, "LastSelectedTimeableIndex", "0")
        set_value(device, "LastSelectedClipEnvelopeIndex", "0")
        parameter_list = device.find("ParameterList/ParameterList")
        for old_parameter in list(parameter_list):
            parameter_list.remove(old_parameter)
        for index, valueof in enumerate(listed_parameters):
            value = preset_values.get(valueof["parameter_longname"], 0)         # Stop and Throw: buttons, at rest
            parameter_list.append(live_parameter_element(FIRST_PARAMETER_ID + index, index, valueof, value))
        hit_bits, accent_bits = pattern_bits(MACHINE_PATTERNS[preset_values["Pattern"]][1])
        blob = device.find("BlobSlot/Value/MxDBlob/Blob")
        if blob is None:
            raise SystemExit(f"2sl-stab.py: {LIVE_PRESET_TEMPLATE_PATH} has no stored-only blob")
        ElementTree.indent(root, space="\t")
        blob.text = stored_only_blob_text({"Steps": hit_bits, "Accents": accent_bits})   # after indent(): its own layout
        xml_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(root, encoding="unicode") + "\n"
        file_name = live_preset_file_name(preset_name, preset_group)
        with open(os.path.join(preset_folder, file_name), "wb") as preset_file:
            preset_file.write(gzip.compress(xml_text.encode(), mtime=0))       # mtime 0: the same bytes every build
        written_presets.append(file_name)
    for stale in sorted(set(f for f in os.listdir(preset_folder) if f.endswith(".adv")) - set(written_presets)):
        os.remove(os.path.join(preset_folder, stale))
        print(f"removed {stale}: no preset of that name in {PRESET_DATA_NAME}")
    print(f"wrote {len(written_presets)} Live presets next to {os.path.relpath(device_path, ROOT)} "
          f"({len(listed_parameters)} parameters each; device {device_size} bytes, CRC {device_crc})")
    return written_presets


# the development device: scripts and presets alongside it, in the repo
write_live_presets(amxd)

# The release: one folder, the frozen device (one self-contained file, the scripts embedded) with the presets made
# for that file, and the folder zipped to download as one file. Made fresh every build (dist/ is not in git).
RELEASE_NAME = f"2sl-stab-{VERSION}"
release_folder = os.path.join(ROOT, "dist", RELEASE_NAME)
if os.path.exists(release_folder):
    shutil.rmtree(release_folder)
os.makedirs(release_folder)
frozen = os.path.join(release_folder, f"{RELEASE_NAME}.amxd")
scripts = [os.path.join(ROOT, "devices", "2sl-stab", n) for n in ("2sl-stab.js", "2sl-stab-ui.js", "2sl-stab-view.js")]
subprocess.run([sys.executable, os.path.join(ROOT, "tools", "amxd.py"), "freeze", maxpat, frozen, "--type", "instrument",
                "--embed", *scripts], check=True)
print(f"froze {os.path.relpath(frozen, ROOT)} ({os.path.getsize(frozen) // 1024} KB, scripts embedded)")
release_presets = write_live_presets(frozen)
release_zip = os.path.join(ROOT, "dist", f"{RELEASE_NAME}.zip")
with zipfile.ZipFile(release_zip, "w", zipfile.ZIP_DEFLATED) as release_archive:
    for file_name in [os.path.basename(frozen)] + sorted(release_presets):
        release_archive.write(os.path.join(release_folder, file_name), f"{RELEASE_NAME}/{file_name}")
print(f"zipped {os.path.relpath(release_folder, ROOT)} as {os.path.relpath(release_zip, ROOT)} "
      f"({os.path.getsize(release_zip) // 1024} KB)")
