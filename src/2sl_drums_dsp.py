"""2sl drums: the gen~ voices, as GenExpr. Imported by src/2sl-drums.py (and by the tests and the level render).

One gen~ for the whole kit. Each voice is triggered by two Params the pattern engine sets per hit:
`delay_<voice>` (ms, the swing delay; sent first) and `trig_<voice>` = serial + velocity / 2 (a new number
every hit, so even two equal hits are two triggers). The voice waits the delay in samples, then fires.

The mixer's Mute and Solo are gates per voice (`<voice>_mute`, `<voice>_solo`, 0/1): a voice sounds when it isn't
muted and either nothing is soloed or it is. Mute wins over Solo. Each gate is smoothed over 5 ms so a mute
doesn't click. CH and OH are one hat voice but have their own levels and gates.

Topologies follow references/drums/voices.md; every number that has no source there is marked
"(unsourced)" here and listed in devices/2sl-drums/README.md.
"""

VOICE_IDS = ["bd", "sd", "rs", "cp", "ch", "oh", "rd"]

FUNCTIONS = r"""
// bit reduction: `bits` of resolution over -1..+1 (16 = clean)
crush(signal, bits) {
	steps = pow(2, bits - 1);
	return floor(signal * steps + 0.5) / steps;
}
// the 909's back-to-back diodes after a triangle VCO: round it towards a sine (Whittle; network-909)
diode_round(signal, drive) {
	return tanh(signal * drive) / tanh(drive);
}
// a triangle that starts at 0 and rises, from a 0..1 phase (the VCO restarts at every trigger)
triangle_from_phase(phase) {
	return 1 - 4 * abs(wrap(phase + 0.25, 0, 1) - 0.5);
}
// a square from a 0..1 phase
square_from_phase(phase) {
	return phase < 0.5 ? 1 : -1;
}
// one-pole low-pass coefficient for a cutoff in Hz
onepole_coefficient(cutoff_hz, sample_rate) {
	return 1 - exp(-twopi * min(cutoff_hz, sample_rate * 0.45) / sample_rate);
}
// per-sample multiplier of an exponential decay that falls 40 dB in `time_ms`
decay_multiplier(time_ms, sample_rate) {
	return exp(-4.6 / max(time_ms * 0.001 * sample_rate, 1));
}
// two-pole resonator feedback for a ring at `frequency_hz` decaying 40 dB in `time_ms` (bridged-T stand-in)
resonator_radius(time_ms, sample_rate) {
	return decay_multiplier(time_ms, sample_rate);
}
// the 909's accent: a hit below full velocity plays quieter by Accent (Total Accent knob)
accent_gain(velocity, accent_amount) {
	return 1 - accent_amount * (1 - velocity);
}
// soft clip: clean below 0.8, rounding off above (2sl stab's output stage)
soft_clip(signal) {
	magnitude = abs(signal);
	shaped = signal;
	if (magnitude > 0.8) {
		shaped = (signal < 0 ? -1 : 1) * (0.8 + 0.2 * tanh((magnitude - 0.8) / 0.2));
	}
	return shaped;
}
"""


def trigger_declarations(voice):
    return (f"Param trig_{voice}(0);\nParam delay_{voice}(0, min=0, max=500);\n"
            f"History {voice}_last_trigger(0), {voice}_wait(0), {voice}_waiting(0), {voice}_pending_velocity(0);\n")


def trigger_code(voice):
    """Sets `<voice>_fire` to 1 on the sample a hit lands (after its swing delay)."""
    return f"""
if (trig_{voice} != {voice}_last_trigger) {{
	{voice}_last_trigger = trig_{voice};
	{voice}_pending_velocity = clamp(fract(trig_{voice}) * 2, 0.001, 1);
	{voice}_wait = mstosamps(delay_{voice});
	{voice}_waiting = 1;
}}
{voice}_fire = 0;
if ({voice}_waiting > 0) {{
	if ({voice}_wait < 1) {{
		{voice}_fire = 1;
		{voice}_waiting = 0;
	}} else {{
		{voice}_wait = {voice}_wait - 1;
	}}
}}
"""


def mixer_declarations(voice):
    return (f"Param {voice}_mute(0, min=0, max=1);\nParam {voice}_solo(0, min=0, max=1);\n"
            f"History {voice}_gate(1);\n")


def mixer_code():
    """Sets `<voice>_gate` (0..1, smoothed) from the mixer's Mute and Solo (the rule is in the docstring above)."""
    any_solo = " + ".join(f"{voice}_solo" for voice in VOICE_IDS)
    code = f"\n// the mixer: mute and solo gates, smoothed over 5 ms\nany_solo = ({any_solo}) > 0 ? 1 : 0;\n"
    code += "gate_coefficient = 1 - exp(-1000 / (5 * samplerate));\n"
    for voice in VOICE_IDS:
        code += (f"{voice}_gate = {voice}_gate + gate_coefficient * ((1 - {voice}_mute) * (any_solo > 0 ? {voice}_solo : 1)"
                 f" - {voice}_gate);\n")
    return code


DECLARATIONS = "".join(trigger_declarations(v) + mixer_declarations(v) for v in VOICE_IDS) + r"""
Param accent(0.7, min=0, max=1);         // how much quieter a normal hit is than an accent
Param volume(0, min=-36, max=12);        // output, dB
Param panic(0);                          // Stop: every new number fades the kit out in 20 ms

// BD
Param bd_tune(50, min=30, max=90);       // Hz the pitch settles to (unsourced range)
Param bd_sweep(0.5, min=0, max=1);       // pitch envelope depth: starts up to 4x higher
Param bd_decay(450, min=60, max=2000);   // ms to -40 dB
Param bd_attack(0.5, min=0, max=1);      // the click: pulse + low-passed noise
Param bd_soft(0, min=0, max=1);          // 0 = 909 punch, 1 = soft and round
Param bd_bits(16, min=3, max=16);
Param bd_level(0.8, min=0, max=1);
History bd_phase(0), bd_pitch_envelope(0), bd_amp_envelope(0), bd_pulse_envelope(0), bd_click_envelope(0);
History bd_velocity(1), bd_fade_in(1), bd_click_noise(0), bd_output_lowpass(0);

// SD
Param sd_tune(180, min=120, max=320);    // Hz of VCO 1; VCO 2 is x1.83
Param sd_tone(160, min=40, max=500);     // ms: the main snappy noise's decay (Whittle: Tone = ENV4 decay)
Param sd_snappy(0.6, min=0, max=1);      // the noise level
Param sd_bits(16, min=3, max=16);
Param sd_level(0.7, min=0, max=1);
History sd_phase1(0), sd_phase2(0), sd_envelope1(0), sd_envelope2(0), sd_bend(0), sd_velocity(1);
History sd_noise_hold(0), sd_noise_envelope4(0), sd_noise_envelope5(0), sd_noise_lowpass(0), sd_noise_highpass_lowpass(0);

// RS
Param rs_bits(16, min=3, max=16);
Param rs_level(0.5, min=0, max=1);
History rs_ring_a1(0), rs_ring_a2(0), rs_ring_b1(0), rs_ring_b2(0), rs_ring_c1(0), rs_ring_c2(0);
History rs_envelope(0), rs_velocity(1), rs_highpass_lowpass(0);

// CP
Param cp_bits(16, min=3, max=16);
Param cp_level(0.6, min=0, max=1);
History cp_time(1000000000), cp_velocity(1), cp_band_highpass_lowpass(0), cp_band_lowpass(0);

// CH and OH: one voice, as on the 909 (a closed hit cuts the open hat)
Param hat_tune(1, min=0.43, max=1.7);    // the sample ROM's clock, x (Whittle's tune mod range)
Param hat_bits(6, min=2, max=12);        // the ROM's bits: 6 on the 909
Param ch_decay(60, min=10, max=300);     // ms to -40 dB
Param oh_decay(500, min=80, max=2000);   // ms to -40 dB
Param ch_level(0.5, min=0, max=1);
Param oh_level(0.5, min=0, max=1);
History hat_envelope(0), hat_open(0), hat_velocity(1), hat_clock(0), hat_held(0);
History hat_osc1(0), hat_osc2(0), hat_osc3(0), hat_osc4(0), hat_osc5(0), hat_osc6(0);
History hat_highpass1_lowpass(0), hat_highpass2_lowpass(0), hat_output_lowpass1(0), hat_output_lowpass2(0);

// RD
Param rd_tune(1, min=0.6, max=1.5);      // the ROM's clock, x: pitch and length together (no decay knob)
Param rd_bits(6, min=2, max=12);
Param rd_level(0.4, min=0, max=1);
History rd_envelope(0), rd_velocity(1), rd_clock(0), rd_held(0);
History rd_osc1(0), rd_osc2(0), rd_osc3(0), rd_osc4(0), rd_osc5(0), rd_osc6(0);
History rd_highpass_lowpass(0), rd_output_lowpass1(0), rd_output_lowpass2(0);

// Stop
History last_panic(0), hush_left(0);
"""

BODY = r"""
sr = samplerate;
// the analog voices share one noise source, as on the 909 (snare and clap phase together)
analog_noise = noise();

// ---- Stop: fade everything out in 20 ms, then silence the voices ----
hush_samples = mstosamps(20);
if (panic != last_panic) {
	last_panic = panic;
	hush_left = hush_samples;
}
hush_gain = 1;
silence_now = 0;
if (hush_left > 0) {
	hush_left = hush_left - 1;
	hush_gain = hush_left / max(hush_samples, 1);
	if (hush_left < 1) {
		silence_now = 1;
	}
}

// ================= BD: triangle VCO + diode clipper, pitch sweep, compressed-looking ENV-1, click =================
if (bd_fire > 0) {
	bd_velocity = bd_pending_velocity;
	bd_phase = 0;                  // TRIG restarts the VCO (network-909: Q11 discharges C14)
	bd_pitch_envelope = 1;
	bd_amp_envelope = 1;
	bd_pulse_envelope = 1;
	bd_click_envelope = 1;
	bd_fade_in = 0;
}
bd_accented = bd_velocity > 0.95 ? 1 : 0;
bd_sweep_now = bd_sweep * (1 - 0.75 * bd_soft);
bd_frequency = bd_tune * (1 + 3 * bd_sweep_now * bd_pitch_envelope);
bd_pitch_envelope = bd_pitch_envelope * decay_multiplier(30 + 90 * bd_soft, sr);       // (unsourced)
bd_phase = wrap(bd_phase + bd_frequency / sr, 0, 1);
bd_body = mix(diode_round(triangle_from_phase(bd_phase), 1.8), sin(twopi * bd_phase), bd_soft);
// accent: more attack amplitude and a longer decay (SOS's BD diagram)
bd_amp_envelope = bd_amp_envelope * decay_multiplier(bd_decay * (1 + 0.15 * bd_accented), sr);
bd_amp_shape = 1 - (1 - bd_amp_envelope) * (1 - bd_amp_envelope);    // flat at first: "looks compressed"
bd_fade_in = min(1, bd_fade_in + 1 / max(mstosamps(0.05 + 5 * bd_soft), 1));            // soft: no transient
bd_pulse_envelope = bd_pulse_envelope * decay_multiplier(1.5, sr);                     // (unsourced)
bd_click_envelope = bd_click_envelope * decay_multiplier(6, sr);                       // (unsourced)
bd_click_noise = bd_click_noise + onepole_coefficient(2500, sr) * (analog_noise - bd_click_noise);
bd_click = (bd_pulse_envelope + 2 * bd_click_noise * bd_click_envelope) * bd_attack * (1 - 0.85 * bd_soft);
bd_raw = bd_body * bd_amp_shape * bd_fade_in + bd_click;
bd_output_lowpass = bd_output_lowpass + onepole_coefficient(mix(9000, 350, bd_soft), sr) * (bd_raw - bd_output_lowpass);
if (silence_now > 0) {
	bd_amp_envelope = 0;
	bd_pulse_envelope = 0;
	bd_click_envelope = 0;
}
bd_out = crush(bd_output_lowpass, bd_bits) * bd_level * bd_gate * accent_gain(bd_velocity, accent);

// ================= SD: two triangle VCOs with a 20 ms pitch bend, noise through LPF -> ENV4 / HPF -> ENV5 =================
if (sd_fire > 0) {
	sd_velocity = sd_pending_velocity;
	sd_phase1 = 0;                 // VCO 1 restarts so VCO 2 starts in phase (service notes)
	sd_phase2 = 0;
	sd_envelope1 = 1;
	sd_envelope2 = 1;
	sd_bend = 1;
	sd_noise_hold = mstosamps(24); // ENV4 holds about 24 ms before it decays (Whittle)
	sd_noise_envelope4 = 1;
	sd_noise_envelope5 = 1;
}
sd_accented = sd_velocity > 0.95 ? 1 : 0;
sd_bend = sd_bend * decay_multiplier(20, sr);                     // the pitch bend lasts about 20 ms
sd_frequency1 = sd_tune * (1 + 0.4 * sd_bend);                     // bend depth (unsourced)
sd_phase1 = wrap(sd_phase1 + sd_frequency1 / sr, 0, 1);
sd_phase2 = wrap(sd_phase2 + sd_frequency1 * 1.83 / sr, 0, 1);      // VCO 2 "somewhat higher" (ratio unsourced)
// accent: the VCO envelopes start higher and last longer (Whittle)
sd_envelope1 = sd_envelope1 * decay_multiplier(180 * (1 + 0.25 * sd_accented), sr);   // lower VCO longer (unsourced)
sd_envelope2 = sd_envelope2 * decay_multiplier(90 * (1 + 0.25 * sd_accented), sr);
sd_drum = diode_round(triangle_from_phase(sd_phase1), 1.6) * sd_envelope1 * 0.6
	+ diode_round(triangle_from_phase(sd_phase2), 1.6) * sd_envelope2 * 0.4;
sd_noise_lowpass = sd_noise_lowpass + onepole_coefficient(7000, sr) * (analog_noise - sd_noise_lowpass);
sd_noise_highpass_lowpass = sd_noise_highpass_lowpass + onepole_coefficient(1800, sr) * (sd_noise_lowpass - sd_noise_highpass_lowpass);
sd_noise_highpass = sd_noise_lowpass - sd_noise_highpass_lowpass;
if (sd_noise_hold > 0) {
	sd_noise_hold = sd_noise_hold - 1;
} else {
	sd_noise_envelope4 = sd_noise_envelope4 * decay_multiplier(sd_tone, sr);
}
sd_noise_envelope5 = sd_noise_envelope5 * decay_multiplier(90, sr);           // (unsourced)
sd_snappy_noise = (sd_noise_lowpass * sd_noise_envelope4 + sd_noise_highpass * sd_noise_envelope5) * sd_snappy;
if (silence_now > 0) {
	sd_envelope1 = 0;
	sd_envelope2 = 0;
	sd_noise_envelope4 = 0;
	sd_noise_envelope5 = 0;
	sd_noise_hold = 0;
}
sd_out = crush(sd_drum + sd_snappy_noise, sd_bits) * sd_level * sd_gate * accent_gain(sd_velocity, accent);

// ================= RS: three bridged-T rings at 500 / 220 / 1000 Hz, a diode clipper, a short VCA, a high-pass =================
rs_kick = 0;
if (rs_fire > 0) {
	rs_velocity = rs_pending_velocity;
	rs_kick = 1;
	rs_envelope = 1;
}
rs_radius_a = resonator_radius(28, sr);
rs_radius_b = resonator_radius(36, sr);
rs_radius_c = resonator_radius(18, sr);                         // ring times (unsourced)
rs_ring_a = 2 * rs_radius_a * cos(twopi * 500 / sr) * rs_ring_a1 - rs_radius_a * rs_radius_a * rs_ring_a2 + rs_kick * sin(twopi * 500 / sr);
rs_ring_a2 = rs_ring_a1;
rs_ring_a1 = rs_ring_a;
rs_ring_b = 2 * rs_radius_b * cos(twopi * 220 / sr) * rs_ring_b1 - rs_radius_b * rs_radius_b * rs_ring_b2 + rs_kick * sin(twopi * 220 / sr);
rs_ring_b2 = rs_ring_b1;
rs_ring_b1 = rs_ring_b;
rs_ring_c = 2 * rs_radius_c * cos(twopi * 1000 / sr) * rs_ring_c1 - rs_radius_c * rs_radius_c * rs_ring_c2 + rs_kick * sin(twopi * 1000 / sr);
rs_ring_c2 = rs_ring_c1;
rs_ring_c1 = rs_ring_c;
rs_envelope = rs_envelope * decay_multiplier(40, sr);                       // the VCA's envelope (unsourced)
rs_clipped = diode_round((rs_ring_a + rs_ring_b * 0.8 + rs_ring_c * 0.7) * 1.5, 2);
rs_highpass_lowpass = rs_highpass_lowpass + onepole_coefficient(250, sr) * (rs_clipped - rs_highpass_lowpass);
if (silence_now > 0) {
	rs_envelope = 0;
}
rs_out = crush((rs_clipped - rs_highpass_lowpass) * rs_envelope, rs_bits) * rs_level * rs_gate * accent_gain(rs_velocity, accent);

// ================= CP: noise -> band-pass -> four chained claps, plus the "pseudo-reverb" tail =================
if (cp_fire > 0) {
	cp_velocity = cp_pending_velocity;
	cp_time = 0;
}
cp_time = cp_time + 1;
cp_spacing = mstosamps(11);                                     // clap to clap (unsourced)
cp_claps = 0;
if (cp_time < 3 * cp_spacing) {
	cp_claps = pow(1 - fract(cp_time / cp_spacing), 3);         // each clap snaps, then falls (a sawtooth's shape)
} else {
	cp_claps = exp(-(cp_time - 3 * cp_spacing) / mstosamps(20));  // the fourth rings a little longer
}
cp_tail = 0.4 * exp(-cp_time / mstosamps(150));                  // longer, softer, slower (tail time unsourced)
cp_band_highpass_lowpass = cp_band_highpass_lowpass + onepole_coefficient(800, sr) * (analog_noise - cp_band_highpass_lowpass);
cp_band_lowpass = cp_band_lowpass + onepole_coefficient(2400, sr) * ((analog_noise - cp_band_highpass_lowpass) - cp_band_lowpass);
if (silence_now > 0) {
	cp_time = 1000000000;
}
cp_out = crush(cp_band_lowpass * (cp_claps + cp_tail) * 1.6, cp_bits) * cp_level * cp_gate * accent_gain(cp_velocity, accent);

// ================= CH / OH: a 6-bit "sample" ROM at 30 kHz, then the VCA, then two low-passes =================
// We have no samples: the "ROM" is metallic noise (six squares + noise, high-passed), held at the ROM's clock and
// quantized to hat_bits, flat like the 909's compressed sample; the VCA puts the decay on after, so the grit
// decays with the hat.
hat_level_now = ch_level * ch_gate;
if (ch_fire > 0) {
	hat_velocity = ch_pending_velocity;
	hat_envelope = 1;
	hat_open = 0;                  // closed cuts open: one voice
}
if (oh_fire > 0) {
	hat_velocity = oh_pending_velocity;
	hat_envelope = 1;
	hat_open = 1;
}
if (hat_open > 0) {
	hat_level_now = oh_level * oh_gate;
}
hat_osc1 = wrap(hat_osc1 + 2520 * hat_tune / sr, 0, 1);           // the six frequencies (unsourced)
hat_osc2 = wrap(hat_osc2 + 3390 * hat_tune / sr, 0, 1);
hat_osc3 = wrap(hat_osc3 + 4150 * hat_tune / sr, 0, 1);
hat_osc4 = wrap(hat_osc4 + 5380 * hat_tune / sr, 0, 1);
hat_osc5 = wrap(hat_osc5 + 6840 * hat_tune / sr, 0, 1);
hat_osc6 = wrap(hat_osc6 + 8260 * hat_tune / sr, 0, 1);
hat_metal = (square_from_phase(hat_osc1) + square_from_phase(hat_osc2) + square_from_phase(hat_osc3)
	+ square_from_phase(hat_osc4) + square_from_phase(hat_osc5) + square_from_phase(hat_osc6)) / 6 * 0.6 + noise() * 0.5;
hat_highpass1_lowpass = hat_highpass1_lowpass + onepole_coefficient(5000, sr) * (hat_metal - hat_highpass1_lowpass);
hat_highpass1 = hat_metal - hat_highpass1_lowpass;
hat_highpass2_lowpass = hat_highpass2_lowpass + onepole_coefficient(5000, sr) * (hat_highpass1 - hat_highpass2_lowpass);
hat_rom_signal = clamp((hat_highpass1 - hat_highpass2_lowpass) * 1.6, -1, 1);
hat_clock = hat_clock + 30000 * hat_tune / sr;                    // 60 kHz / 2 (service notes) = 30 kHz (SOS)
if (hat_clock >= 1) {
	hat_clock = hat_clock - floor(hat_clock);
	hat_held = crush(hat_rom_signal, hat_bits);
}
// CH decays through about 1/10 of OH's resistance (network-909); here each has its own Decay
hat_envelope = hat_envelope * decay_multiplier(hat_open > 0 ? oh_decay : ch_decay, sr);
hat_output_lowpass1 = hat_output_lowpass1 + onepole_coefficient(11000, sr) * (hat_held * hat_envelope - hat_output_lowpass1);
hat_output_lowpass2 = hat_output_lowpass2 + onepole_coefficient(11000, sr) * (hat_output_lowpass1 - hat_output_lowpass2);
if (silence_now > 0) {
	hat_envelope = 0;
}
hat_out = hat_output_lowpass2 * 2.5 * hat_level_now * accent_gain(hat_velocity, accent);   // voice balance (unsourced)

// ================= RD: the same ROM idea; the decay follows the clock (Tone changes pitch and length) =================
if (rd_fire > 0) {
	rd_velocity = rd_pending_velocity;
	rd_envelope = 1;
}
rd_osc1 = wrap(rd_osc1 + 1630 * rd_tune / sr, 0, 1);             // (unsourced)
rd_osc2 = wrap(rd_osc2 + 2210 * rd_tune / sr, 0, 1);
rd_osc3 = wrap(rd_osc3 + 2870 * rd_tune / sr, 0, 1);
rd_osc4 = wrap(rd_osc4 + 3530 * rd_tune / sr, 0, 1);
rd_osc5 = wrap(rd_osc5 + 4790 * rd_tune / sr, 0, 1);
rd_osc6 = wrap(rd_osc6 + 6120 * rd_tune / sr, 0, 1);
rd_metal = (square_from_phase(rd_osc1) + square_from_phase(rd_osc2) + square_from_phase(rd_osc3)
	+ square_from_phase(rd_osc4) + square_from_phase(rd_osc5) + square_from_phase(rd_osc6)) / 6 * 0.8 + noise() * 0.25;
rd_highpass_lowpass = rd_highpass_lowpass + onepole_coefficient(2500, sr) * (rd_metal - rd_highpass_lowpass);
rd_rom_signal = clamp((rd_metal - rd_highpass_lowpass) * 1.4, -1, 1);
rd_clock = rd_clock + 30000 * rd_tune / sr;
if (rd_clock >= 1) {
	rd_clock = rd_clock - floor(rd_clock);
	rd_held = crush(rd_rom_signal, rd_bits);
}
rd_envelope = rd_envelope * decay_multiplier(1600 / rd_tune, sr);      // ROM length at the nominal clock (unsourced)
rd_output_lowpass1 = rd_output_lowpass1 + onepole_coefficient(10000, sr) * (rd_held * rd_envelope - rd_output_lowpass1);
rd_output_lowpass2 = rd_output_lowpass2 + onepole_coefficient(10000, sr) * (rd_output_lowpass1 - rd_output_lowpass2);
if (silence_now > 0) {
	rd_envelope = 0;
}
rd_out = rd_output_lowpass2 * rd_level * rd_gate * accent_gain(rd_velocity, accent);

// ================= out: the mono kit on both sides, through the soft clip =================
// x0.4 (-8 dB): headroom, so the Init kit peaks about 3 dB under full scale (tools/render_drums.py measures it)
kit = (bd_out + sd_out + rs_out + cp_out + hat_out + rd_out) * 0.4 * hush_gain;
kit_out = soft_clip(kit * dbtoa(volume));
out1 = kit_out;
out2 = kit_out;
"""

KIT = FUNCTIONS + DECLARATIONS + "".join(trigger_code(v) for v in VOICE_IDS) + mixer_code() + BODY
