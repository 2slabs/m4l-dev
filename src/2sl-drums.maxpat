{
	"patcher": {
		"fileversion": 1,
		"appversion": {
			"major": 9,
			"minor": 1,
			"revision": 5,
			"architecture": "x64",
			"modernui": 1
		},
		"classnamespace": "box",
		"rect": [
			80.0,
			80.0,
			1300.0,
			900.0
		],
		"openinpresentation": 1,
		"devicewidth": 960.0,
		"boxes": [
			{
				"box": {
					"id": "obj-1",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						30.0,
						30.0,
						50.0,
						22.0
					],
					"text": "midiin",
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "obj-2",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 8,
					"patching_rect": [
						30.0,
						60.0,
						90.0,
						22.0
					],
					"text": "midiparse",
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-3",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 5,
					"patching_rect": [
						30.0,
						120.0,
						110.0,
						22.0
					],
					"text": "js 2sl-drums.js",
					"outlettype": [
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-4",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						30.0,
						350.0,
						160.0,
						22.0
					],
					"text": "gen~",
					"outlettype": [
						"signal",
						"signal"
					],
					"patcher": {
						"fileversion": 1,
						"appversion": {
							"major": 9,
							"minor": 1,
							"revision": 5,
							"architecture": "x64",
							"modernui": 1
						},
						"classnamespace": "dsp.gen",
						"rect": [
							100.0,
							100.0,
							760.0,
							740.0
						],
						"boxes": [
							{
								"box": {
									"id": "cb",
									"maxclass": "codebox",
									"code": "// bit reduction: `bits` of resolution over -1..+1 (16 = clean)\ncrush(signal, bits) {\n\tsteps = pow(2, bits - 1);\n\treturn floor(signal * steps + 0.5) / steps;\n}\n// the 909's back-to-back diodes after a triangle VCO: round it towards a sine (Whittle; network-909)\ndiode_round(signal, drive) {\n\treturn tanh(signal * drive) / tanh(drive);\n}\n// a triangle that starts at 0 and rises, from a 0..1 phase (the VCO restarts at every trigger)\ntriangle_from_phase(phase) {\n\treturn 1 - 4 * abs(wrap(phase + 0.25, 0, 1) - 0.5);\n}\n// a square from a 0..1 phase\nsquare_from_phase(phase) {\n\treturn phase < 0.5 ? 1 : -1;\n}\n// one-pole low-pass coefficient for a cutoff in Hz\nonepole_coefficient(cutoff_hz, sample_rate) {\n\treturn 1 - exp(-twopi * min(cutoff_hz, sample_rate * 0.45) / sample_rate);\n}\n// per-sample multiplier of an exponential decay that falls 40 dB in `time_ms`\ndecay_multiplier(time_ms, sample_rate) {\n\treturn exp(-4.6 / max(time_ms * 0.001 * sample_rate, 1));\n}\n// two-pole resonator feedback for a ring at `frequency_hz` decaying 40 dB in `time_ms` (bridged-T stand-in)\nresonator_radius(time_ms, sample_rate) {\n\treturn decay_multiplier(time_ms, sample_rate);\n}\n// the 909's accent: a hit below full velocity plays quieter by Accent (Total Accent knob)\naccent_gain(velocity, accent_amount) {\n\treturn 1 - accent_amount * (1 - velocity);\n}\n// soft clip: clean below 0.8, rounding off above (2sl stab's output stage)\nsoft_clip(signal) {\n\tmagnitude = abs(signal);\n\tshaped = signal;\n\tif (magnitude > 0.8) {\n\t\tshaped = (signal < 0 ? -1 : 1) * (0.8 + 0.2 * tanh((magnitude - 0.8) / 0.2));\n\t}\n\treturn shaped;\n}\nParam trig_bd(0);\nParam delay_bd(0, min=0, max=500);\nHistory bd_last_trigger(0), bd_wait(0), bd_waiting(0), bd_pending_velocity(0);\nParam trig_sd(0);\nParam delay_sd(0, min=0, max=500);\nHistory sd_last_trigger(0), sd_wait(0), sd_waiting(0), sd_pending_velocity(0);\nParam trig_rs(0);\nParam delay_rs(0, min=0, max=500);\nHistory rs_last_trigger(0), rs_wait(0), rs_waiting(0), rs_pending_velocity(0);\nParam trig_cp(0);\nParam delay_cp(0, min=0, max=500);\nHistory cp_last_trigger(0), cp_wait(0), cp_waiting(0), cp_pending_velocity(0);\nParam trig_ch(0);\nParam delay_ch(0, min=0, max=500);\nHistory ch_last_trigger(0), ch_wait(0), ch_waiting(0), ch_pending_velocity(0);\nParam trig_oh(0);\nParam delay_oh(0, min=0, max=500);\nHistory oh_last_trigger(0), oh_wait(0), oh_waiting(0), oh_pending_velocity(0);\nParam trig_rd(0);\nParam delay_rd(0, min=0, max=500);\nHistory rd_last_trigger(0), rd_wait(0), rd_waiting(0), rd_pending_velocity(0);\n\nParam accent(0.7, min=0, max=1);         // how much quieter a normal hit is than an accent\nParam volume(0, min=-36, max=12);        // output, dB\nParam panic(0);                          // Stop: every new number fades the kit out in 20 ms\n\n// BD\nParam bd_tune(50, min=30, max=90);       // Hz the pitch settles to (unsourced range)\nParam bd_sweep(0.5, min=0, max=1);       // pitch envelope depth: starts up to 4x higher\nParam bd_decay(450, min=60, max=2000);   // ms to -40 dB\nParam bd_attack(0.5, min=0, max=1);      // the click: pulse + low-passed noise\nParam bd_soft(0, min=0, max=1);          // 0 = 909 punch, 1 = soft and round\nParam bd_bits(16, min=3, max=16);\nParam bd_level(0.8, min=0, max=1);\nHistory bd_phase(0), bd_pitch_envelope(0), bd_amp_envelope(0), bd_pulse_envelope(0), bd_click_envelope(0);\nHistory bd_velocity(1), bd_fade_in(1), bd_click_noise(0), bd_output_lowpass(0);\n\n// SD\nParam sd_tune(180, min=120, max=320);    // Hz of VCO 1; VCO 2 is x1.83\nParam sd_tone(160, min=40, max=500);     // ms: the main snappy noise's decay (Whittle: Tone = ENV4 decay)\nParam sd_snappy(0.6, min=0, max=1);      // the noise level\nParam sd_bits(16, min=3, max=16);\nParam sd_level(0.7, min=0, max=1);\nHistory sd_phase1(0), sd_phase2(0), sd_envelope1(0), sd_envelope2(0), sd_bend(0), sd_velocity(1);\nHistory sd_noise_hold(0), sd_noise_envelope4(0), sd_noise_envelope5(0), sd_noise_lowpass(0), sd_noise_highpass_lowpass(0);\n\n// RS\nParam rs_bits(16, min=3, max=16);\nParam rs_level(0.5, min=0, max=1);\nHistory rs_ring_a1(0), rs_ring_a2(0), rs_ring_b1(0), rs_ring_b2(0), rs_ring_c1(0), rs_ring_c2(0);\nHistory rs_envelope(0), rs_velocity(1), rs_highpass_lowpass(0);\n\n// CP\nParam cp_bits(16, min=3, max=16);\nParam cp_level(0.6, min=0, max=1);\nHistory cp_time(1000000000), cp_velocity(1), cp_band_highpass_lowpass(0), cp_band_lowpass(0);\n\n// CH and OH: one voice, as on the 909 (a closed hit cuts the open hat)\nParam hat_tune(1, min=0.43, max=1.7);    // the sample ROM's clock, x (Whittle's tune mod range)\nParam hat_bits(6, min=2, max=12);        // the ROM's bits: 6 on the 909\nParam ch_decay(60, min=10, max=300);     // ms to -40 dB\nParam oh_decay(500, min=80, max=2000);   // ms to -40 dB\nParam ch_level(0.5, min=0, max=1);\nParam oh_level(0.5, min=0, max=1);\nHistory hat_envelope(0), hat_open(0), hat_velocity(1), hat_clock(0), hat_held(0);\nHistory hat_osc1(0), hat_osc2(0), hat_osc3(0), hat_osc4(0), hat_osc5(0), hat_osc6(0);\nHistory hat_highpass1_lowpass(0), hat_highpass2_lowpass(0), hat_output_lowpass1(0), hat_output_lowpass2(0);\n\n// RD\nParam rd_tune(1, min=0.6, max=1.5);      // the ROM's clock, x: pitch and length together (no decay knob)\nParam rd_bits(6, min=2, max=12);\nParam rd_level(0.4, min=0, max=1);\nHistory rd_envelope(0), rd_velocity(1), rd_clock(0), rd_held(0);\nHistory rd_osc1(0), rd_osc2(0), rd_osc3(0), rd_osc4(0), rd_osc5(0), rd_osc6(0);\nHistory rd_highpass_lowpass(0), rd_output_lowpass1(0), rd_output_lowpass2(0);\n\n// Stop\nHistory last_panic(0), hush_left(0);\n\nif (trig_bd != bd_last_trigger) {\n\tbd_last_trigger = trig_bd;\n\tbd_pending_velocity = clamp(fract(trig_bd) * 2, 0.001, 1);\n\tbd_wait = mstosamps(delay_bd);\n\tbd_waiting = 1;\n}\nbd_fire = 0;\nif (bd_waiting > 0) {\n\tif (bd_wait < 1) {\n\t\tbd_fire = 1;\n\t\tbd_waiting = 0;\n\t} else {\n\t\tbd_wait = bd_wait - 1;\n\t}\n}\n\nif (trig_sd != sd_last_trigger) {\n\tsd_last_trigger = trig_sd;\n\tsd_pending_velocity = clamp(fract(trig_sd) * 2, 0.001, 1);\n\tsd_wait = mstosamps(delay_sd);\n\tsd_waiting = 1;\n}\nsd_fire = 0;\nif (sd_waiting > 0) {\n\tif (sd_wait < 1) {\n\t\tsd_fire = 1;\n\t\tsd_waiting = 0;\n\t} else {\n\t\tsd_wait = sd_wait - 1;\n\t}\n}\n\nif (trig_rs != rs_last_trigger) {\n\trs_last_trigger = trig_rs;\n\trs_pending_velocity = clamp(fract(trig_rs) * 2, 0.001, 1);\n\trs_wait = mstosamps(delay_rs);\n\trs_waiting = 1;\n}\nrs_fire = 0;\nif (rs_waiting > 0) {\n\tif (rs_wait < 1) {\n\t\trs_fire = 1;\n\t\trs_waiting = 0;\n\t} else {\n\t\trs_wait = rs_wait - 1;\n\t}\n}\n\nif (trig_cp != cp_last_trigger) {\n\tcp_last_trigger = trig_cp;\n\tcp_pending_velocity = clamp(fract(trig_cp) * 2, 0.001, 1);\n\tcp_wait = mstosamps(delay_cp);\n\tcp_waiting = 1;\n}\ncp_fire = 0;\nif (cp_waiting > 0) {\n\tif (cp_wait < 1) {\n\t\tcp_fire = 1;\n\t\tcp_waiting = 0;\n\t} else {\n\t\tcp_wait = cp_wait - 1;\n\t}\n}\n\nif (trig_ch != ch_last_trigger) {\n\tch_last_trigger = trig_ch;\n\tch_pending_velocity = clamp(fract(trig_ch) * 2, 0.001, 1);\n\tch_wait = mstosamps(delay_ch);\n\tch_waiting = 1;\n}\nch_fire = 0;\nif (ch_waiting > 0) {\n\tif (ch_wait < 1) {\n\t\tch_fire = 1;\n\t\tch_waiting = 0;\n\t} else {\n\t\tch_wait = ch_wait - 1;\n\t}\n}\n\nif (trig_oh != oh_last_trigger) {\n\toh_last_trigger = trig_oh;\n\toh_pending_velocity = clamp(fract(trig_oh) * 2, 0.001, 1);\n\toh_wait = mstosamps(delay_oh);\n\toh_waiting = 1;\n}\noh_fire = 0;\nif (oh_waiting > 0) {\n\tif (oh_wait < 1) {\n\t\toh_fire = 1;\n\t\toh_waiting = 0;\n\t} else {\n\t\toh_wait = oh_wait - 1;\n\t}\n}\n\nif (trig_rd != rd_last_trigger) {\n\trd_last_trigger = trig_rd;\n\trd_pending_velocity = clamp(fract(trig_rd) * 2, 0.001, 1);\n\trd_wait = mstosamps(delay_rd);\n\trd_waiting = 1;\n}\nrd_fire = 0;\nif (rd_waiting > 0) {\n\tif (rd_wait < 1) {\n\t\trd_fire = 1;\n\t\trd_waiting = 0;\n\t} else {\n\t\trd_wait = rd_wait - 1;\n\t}\n}\n\nsr = samplerate;\n// the analog voices share one noise source, as on the 909 (snare and clap phase together)\nanalog_noise = noise();\n\n// ---- Stop: fade everything out in 20 ms, then silence the voices ----\nhush_samples = mstosamps(20);\nif (panic != last_panic) {\n\tlast_panic = panic;\n\thush_left = hush_samples;\n}\nhush_gain = 1;\nsilence_now = 0;\nif (hush_left > 0) {\n\thush_left = hush_left - 1;\n\thush_gain = hush_left / max(hush_samples, 1);\n\tif (hush_left < 1) {\n\t\tsilence_now = 1;\n\t}\n}\n\n// ================= BD: triangle VCO + diode clipper, pitch sweep, compressed-looking ENV-1, click =================\nif (bd_fire > 0) {\n\tbd_velocity = bd_pending_velocity;\n\tbd_phase = 0;                  // TRIG restarts the VCO (network-909: Q11 discharges C14)\n\tbd_pitch_envelope = 1;\n\tbd_amp_envelope = 1;\n\tbd_pulse_envelope = 1;\n\tbd_click_envelope = 1;\n\tbd_fade_in = 0;\n}\nbd_accented = bd_velocity > 0.95 ? 1 : 0;\nbd_sweep_now = bd_sweep * (1 - 0.75 * bd_soft);\nbd_frequency = bd_tune * (1 + 3 * bd_sweep_now * bd_pitch_envelope);\nbd_pitch_envelope = bd_pitch_envelope * decay_multiplier(30 + 90 * bd_soft, sr);       // (unsourced)\nbd_phase = wrap(bd_phase + bd_frequency / sr, 0, 1);\nbd_body = mix(diode_round(triangle_from_phase(bd_phase), 1.8), sin(twopi * bd_phase), bd_soft);\n// accent: more attack amplitude and a longer decay (SOS's BD diagram)\nbd_amp_envelope = bd_amp_envelope * decay_multiplier(bd_decay * (1 + 0.15 * bd_accented), sr);\nbd_amp_shape = 1 - (1 - bd_amp_envelope) * (1 - bd_amp_envelope);    // flat at first: \"looks compressed\"\nbd_fade_in = min(1, bd_fade_in + 1 / max(mstosamps(0.05 + 5 * bd_soft), 1));            // soft: no transient\nbd_pulse_envelope = bd_pulse_envelope * decay_multiplier(1.5, sr);                     // (unsourced)\nbd_click_envelope = bd_click_envelope * decay_multiplier(6, sr);                       // (unsourced)\nbd_click_noise = bd_click_noise + onepole_coefficient(2500, sr) * (analog_noise - bd_click_noise);\nbd_click = (bd_pulse_envelope + 2 * bd_click_noise * bd_click_envelope) * bd_attack * (1 - 0.85 * bd_soft);\nbd_raw = bd_body * bd_amp_shape * bd_fade_in + bd_click;\nbd_output_lowpass = bd_output_lowpass + onepole_coefficient(mix(9000, 350, bd_soft), sr) * (bd_raw - bd_output_lowpass);\nif (silence_now > 0) {\n\tbd_amp_envelope = 0;\n\tbd_pulse_envelope = 0;\n\tbd_click_envelope = 0;\n}\nbd_out = crush(bd_output_lowpass, bd_bits) * bd_level * accent_gain(bd_velocity, accent);\n\n// ================= SD: two triangle VCOs with a 20 ms pitch bend, noise through LPF -> ENV4 / HPF -> ENV5 =================\nif (sd_fire > 0) {\n\tsd_velocity = sd_pending_velocity;\n\tsd_phase1 = 0;                 // VCO 1 restarts so VCO 2 starts in phase (service notes)\n\tsd_phase2 = 0;\n\tsd_envelope1 = 1;\n\tsd_envelope2 = 1;\n\tsd_bend = 1;\n\tsd_noise_hold = mstosamps(24); // ENV4 holds about 24 ms before it decays (Whittle)\n\tsd_noise_envelope4 = 1;\n\tsd_noise_envelope5 = 1;\n}\nsd_accented = sd_velocity > 0.95 ? 1 : 0;\nsd_bend = sd_bend * decay_multiplier(20, sr);                     // the pitch bend lasts about 20 ms\nsd_frequency1 = sd_tune * (1 + 0.4 * sd_bend);                     // bend depth (unsourced)\nsd_phase1 = wrap(sd_phase1 + sd_frequency1 / sr, 0, 1);\nsd_phase2 = wrap(sd_phase2 + sd_frequency1 * 1.83 / sr, 0, 1);      // VCO 2 \"somewhat higher\" (ratio unsourced)\n// accent: the VCO envelopes start higher and last longer (Whittle)\nsd_envelope1 = sd_envelope1 * decay_multiplier(180 * (1 + 0.25 * sd_accented), sr);   // lower VCO longer (unsourced)\nsd_envelope2 = sd_envelope2 * decay_multiplier(90 * (1 + 0.25 * sd_accented), sr);\nsd_drum = diode_round(triangle_from_phase(sd_phase1), 1.6) * sd_envelope1 * 0.6\n\t+ diode_round(triangle_from_phase(sd_phase2), 1.6) * sd_envelope2 * 0.4;\nsd_noise_lowpass = sd_noise_lowpass + onepole_coefficient(7000, sr) * (analog_noise - sd_noise_lowpass);\nsd_noise_highpass_lowpass = sd_noise_highpass_lowpass + onepole_coefficient(1800, sr) * (sd_noise_lowpass - sd_noise_highpass_lowpass);\nsd_noise_highpass = sd_noise_lowpass - sd_noise_highpass_lowpass;\nif (sd_noise_hold > 0) {\n\tsd_noise_hold = sd_noise_hold - 1;\n} else {\n\tsd_noise_envelope4 = sd_noise_envelope4 * decay_multiplier(sd_tone, sr);\n}\nsd_noise_envelope5 = sd_noise_envelope5 * decay_multiplier(90, sr);           // (unsourced)\nsd_snappy_noise = (sd_noise_lowpass * sd_noise_envelope4 + sd_noise_highpass * sd_noise_envelope5) * sd_snappy;\nif (silence_now > 0) {\n\tsd_envelope1 = 0;\n\tsd_envelope2 = 0;\n\tsd_noise_envelope4 = 0;\n\tsd_noise_envelope5 = 0;\n\tsd_noise_hold = 0;\n}\nsd_out = crush(sd_drum + sd_snappy_noise, sd_bits) * sd_level * accent_gain(sd_velocity, accent);\n\n// ================= RS: three bridged-T rings at 500 / 220 / 1000 Hz, a diode clipper, a short VCA, a high-pass =================\nrs_kick = 0;\nif (rs_fire > 0) {\n\trs_velocity = rs_pending_velocity;\n\trs_kick = 1;\n\trs_envelope = 1;\n}\nrs_radius_a = resonator_radius(28, sr);\nrs_radius_b = resonator_radius(36, sr);\nrs_radius_c = resonator_radius(18, sr);                         // ring times (unsourced)\nrs_ring_a = 2 * rs_radius_a * cos(twopi * 500 / sr) * rs_ring_a1 - rs_radius_a * rs_radius_a * rs_ring_a2 + rs_kick * sin(twopi * 500 / sr);\nrs_ring_a2 = rs_ring_a1;\nrs_ring_a1 = rs_ring_a;\nrs_ring_b = 2 * rs_radius_b * cos(twopi * 220 / sr) * rs_ring_b1 - rs_radius_b * rs_radius_b * rs_ring_b2 + rs_kick * sin(twopi * 220 / sr);\nrs_ring_b2 = rs_ring_b1;\nrs_ring_b1 = rs_ring_b;\nrs_ring_c = 2 * rs_radius_c * cos(twopi * 1000 / sr) * rs_ring_c1 - rs_radius_c * rs_radius_c * rs_ring_c2 + rs_kick * sin(twopi * 1000 / sr);\nrs_ring_c2 = rs_ring_c1;\nrs_ring_c1 = rs_ring_c;\nrs_envelope = rs_envelope * decay_multiplier(40, sr);                       // the VCA's envelope (unsourced)\nrs_clipped = diode_round((rs_ring_a + rs_ring_b * 0.8 + rs_ring_c * 0.7) * 1.5, 2);\nrs_highpass_lowpass = rs_highpass_lowpass + onepole_coefficient(250, sr) * (rs_clipped - rs_highpass_lowpass);\nif (silence_now > 0) {\n\trs_envelope = 0;\n}\nrs_out = crush((rs_clipped - rs_highpass_lowpass) * rs_envelope, rs_bits) * rs_level * accent_gain(rs_velocity, accent);\n\n// ================= CP: noise -> band-pass -> four chained claps, plus the \"pseudo-reverb\" tail =================\nif (cp_fire > 0) {\n\tcp_velocity = cp_pending_velocity;\n\tcp_time = 0;\n}\ncp_time = cp_time + 1;\ncp_spacing = mstosamps(11);                                     // clap to clap (unsourced)\ncp_claps = 0;\nif (cp_time < 3 * cp_spacing) {\n\tcp_claps = pow(1 - fract(cp_time / cp_spacing), 3);         // each clap snaps, then falls (a sawtooth's shape)\n} else {\n\tcp_claps = exp(-(cp_time - 3 * cp_spacing) / mstosamps(20));  // the fourth rings a little longer\n}\ncp_tail = 0.4 * exp(-cp_time / mstosamps(150));                  // longer, softer, slower (tail time unsourced)\ncp_band_highpass_lowpass = cp_band_highpass_lowpass + onepole_coefficient(800, sr) * (analog_noise - cp_band_highpass_lowpass);\ncp_band_lowpass = cp_band_lowpass + onepole_coefficient(2400, sr) * ((analog_noise - cp_band_highpass_lowpass) - cp_band_lowpass);\nif (silence_now > 0) {\n\tcp_time = 1000000000;\n}\ncp_out = crush(cp_band_lowpass * (cp_claps + cp_tail) * 1.6, cp_bits) * cp_level * accent_gain(cp_velocity, accent);\n\n// ================= CH / OH: a 6-bit \"sample\" ROM at 30 kHz, then the VCA, then two low-passes =================\n// We have no samples: the \"ROM\" is metallic noise (six squares + noise, high-passed), held at the ROM's clock and\n// quantized to hat_bits, flat like the 909's compressed sample; the VCA puts the decay on after, so the grit\n// decays with the hat.\nhat_level_now = ch_level;\nif (ch_fire > 0) {\n\that_velocity = ch_pending_velocity;\n\that_envelope = 1;\n\that_open = 0;                  // closed cuts open: one voice\n}\nif (oh_fire > 0) {\n\that_velocity = oh_pending_velocity;\n\that_envelope = 1;\n\that_open = 1;\n}\nif (hat_open > 0) {\n\that_level_now = oh_level;\n}\nhat_osc1 = wrap(hat_osc1 + 2520 * hat_tune / sr, 0, 1);           // the six frequencies (unsourced)\nhat_osc2 = wrap(hat_osc2 + 3390 * hat_tune / sr, 0, 1);\nhat_osc3 = wrap(hat_osc3 + 4150 * hat_tune / sr, 0, 1);\nhat_osc4 = wrap(hat_osc4 + 5380 * hat_tune / sr, 0, 1);\nhat_osc5 = wrap(hat_osc5 + 6840 * hat_tune / sr, 0, 1);\nhat_osc6 = wrap(hat_osc6 + 8260 * hat_tune / sr, 0, 1);\nhat_metal = (square_from_phase(hat_osc1) + square_from_phase(hat_osc2) + square_from_phase(hat_osc3)\n\t+ square_from_phase(hat_osc4) + square_from_phase(hat_osc5) + square_from_phase(hat_osc6)) / 6 * 0.6 + noise() * 0.5;\nhat_highpass1_lowpass = hat_highpass1_lowpass + onepole_coefficient(5000, sr) * (hat_metal - hat_highpass1_lowpass);\nhat_highpass1 = hat_metal - hat_highpass1_lowpass;\nhat_highpass2_lowpass = hat_highpass2_lowpass + onepole_coefficient(5000, sr) * (hat_highpass1 - hat_highpass2_lowpass);\nhat_rom_signal = clamp((hat_highpass1 - hat_highpass2_lowpass) * 1.6, -1, 1);\nhat_clock = hat_clock + 30000 * hat_tune / sr;                    // 60 kHz / 2 (service notes) = 30 kHz (SOS)\nif (hat_clock >= 1) {\n\that_clock = hat_clock - floor(hat_clock);\n\that_held = crush(hat_rom_signal, hat_bits);\n}\n// CH decays through about 1/10 of OH's resistance (network-909); here each has its own Decay\nhat_envelope = hat_envelope * decay_multiplier(hat_open > 0 ? oh_decay : ch_decay, sr);\nhat_output_lowpass1 = hat_output_lowpass1 + onepole_coefficient(11000, sr) * (hat_held * hat_envelope - hat_output_lowpass1);\nhat_output_lowpass2 = hat_output_lowpass2 + onepole_coefficient(11000, sr) * (hat_output_lowpass1 - hat_output_lowpass2);\nif (silence_now > 0) {\n\that_envelope = 0;\n}\nhat_out = hat_output_lowpass2 * 2.5 * hat_level_now * accent_gain(hat_velocity, accent);   // voice balance (unsourced)\n\n// ================= RD: the same ROM idea; the decay follows the clock (Tone changes pitch and length) =================\nif (rd_fire > 0) {\n\trd_velocity = rd_pending_velocity;\n\trd_envelope = 1;\n}\nrd_osc1 = wrap(rd_osc1 + 1630 * rd_tune / sr, 0, 1);             // (unsourced)\nrd_osc2 = wrap(rd_osc2 + 2210 * rd_tune / sr, 0, 1);\nrd_osc3 = wrap(rd_osc3 + 2870 * rd_tune / sr, 0, 1);\nrd_osc4 = wrap(rd_osc4 + 3530 * rd_tune / sr, 0, 1);\nrd_osc5 = wrap(rd_osc5 + 4790 * rd_tune / sr, 0, 1);\nrd_osc6 = wrap(rd_osc6 + 6120 * rd_tune / sr, 0, 1);\nrd_metal = (square_from_phase(rd_osc1) + square_from_phase(rd_osc2) + square_from_phase(rd_osc3)\n\t+ square_from_phase(rd_osc4) + square_from_phase(rd_osc5) + square_from_phase(rd_osc6)) / 6 * 0.8 + noise() * 0.25;\nrd_highpass_lowpass = rd_highpass_lowpass + onepole_coefficient(2500, sr) * (rd_metal - rd_highpass_lowpass);\nrd_rom_signal = clamp((rd_metal - rd_highpass_lowpass) * 1.4, -1, 1);\nrd_clock = rd_clock + 30000 * rd_tune / sr;\nif (rd_clock >= 1) {\n\trd_clock = rd_clock - floor(rd_clock);\n\trd_held = crush(rd_rom_signal, rd_bits);\n}\nrd_envelope = rd_envelope * decay_multiplier(1600 / rd_tune, sr);      // ROM length at the nominal clock (unsourced)\nrd_output_lowpass1 = rd_output_lowpass1 + onepole_coefficient(10000, sr) * (rd_held * rd_envelope - rd_output_lowpass1);\nrd_output_lowpass2 = rd_output_lowpass2 + onepole_coefficient(10000, sr) * (rd_output_lowpass1 - rd_output_lowpass2);\nif (silence_now > 0) {\n\trd_envelope = 0;\n}\nrd_out = rd_output_lowpass2 * rd_level * accent_gain(rd_velocity, accent);\n\n// ================= out: the mono kit on both sides, through the soft clip =================\n// x0.4 (-8 dB): headroom, so the Init kit peaks about 3 dB under full scale (tools/render_drums.py measures it)\nkit = (bd_out + sd_out + rs_out + cp_out + hat_out + rd_out) * 0.4 * hush_gain;\nkit_out = soft_clip(kit * dbtoa(volume));\nout1 = kit_out;\nout2 = kit_out;\n",
									"fontname": "<Monospaced>",
									"fontsize": 12.0,
									"numinlets": 0,
									"numoutlets": 2,
									"outlettype": [
										"",
										""
									],
									"patching_rect": [
										20.0,
										60.0,
										700.0,
										600.0
									]
								}
							},
							{
								"box": {
									"id": "out1",
									"maxclass": "newobj",
									"text": "out 1",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										20.0,
										680.0,
										45.0,
										22.0
									]
								}
							},
							{
								"box": {
									"id": "out2",
									"maxclass": "newobj",
									"text": "out 2",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										100.0,
										680.0,
										45.0,
										22.0
									]
								}
							}
						],
						"lines": [
							{
								"patchline": {
									"source": [
										"cb",
										0
									],
									"destination": [
										"out1",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"cb",
										1
									],
									"destination": [
										"out2",
										0
									]
								}
							}
						]
					}
				}
			},
			{
				"box": {
					"id": "obj-5",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						30.0,
						470.0,
						70.0,
						22.0
					],
					"text": "plugout~",
					"outlettype": [
						"signal",
						"signal"
					]
				}
			},
			{
				"box": {
					"id": "obj-6",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1500.0,
						1000.0,
						960.0,
						169.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"chrome"
					],
					"presentation": 1,
					"presentation_rect": [
						0.0,
						0.0,
						960.0,
						169.0
					],
					"border": 0,
					"ignoreclick": 1,
					"background": 1,
					"varname": "view_chrome"
				}
			},
			{
				"box": {
					"id": "obj-7",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						30.0,
						120.0,
						22.0
					],
					"text": "js 2sl-drums-ui.js",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-8",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1100.0,
						60.0,
						80.0,
						22.0
					],
					"text": "thispatcher",
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-9",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						420.0,
						30.0,
						100.0,
						22.0
					],
					"text": "live.thisdevice",
					"outlettype": [
						"bang",
						"int",
						"int"
					]
				}
			},
			{
				"box": {
					"id": "obj-10",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						0.0,
						70.0,
						22.0
					],
					"text": "delay 800",
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "obj-11",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1180.0,
						0.0,
						50.0,
						22.0
					],
					"text": "ready",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-12",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1250.0,
						30.0,
						70.0,
						22.0
					],
					"text": "live.colors",
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "obj-13",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1250.0,
						60.0,
						45.0,
						22.0
					],
					"text": "theme",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-14",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1003.0,
						62.0,
						15.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"link"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						3.0,
						62.0,
						15.0
					],
					"border": 0,
					"annotation_name": "2sl.to",
					"annotation": "Opens 2sl.to in your browser.",
					"varname": "view_link"
				}
			},
			{
				"box": {
					"id": "obj-15",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1500.0,
						560.0,
						216.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "page",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						82.0,
						3.0,
						216.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Page",
							"parameter_shortname": "Page",
							"parameter_type": 2,
							"parameter_enum": [
								"play",
								"bd sd rs",
								"cp hats rd"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Page",
							"parameter_info": "Shows the play, bd sd rs or cp hats rd page. Controls on hidden pages keep working."
						}
					},
					"annotation_name": "Page",
					"annotation": "Shows the play, bd sd rs or cp hats rd page. Controls on hidden pages keep working.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1
				}
			},
			{
				"box": {
					"id": "obj-16",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						930.0,
						100.0,
						22.0
					],
					"text": "prepend page",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-17",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						932.0,
						100.0,
						22.0
					],
					"text": "prepend page",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-18",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1860.0,
						643.0,
						180.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "preset",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						360.0,
						3.0,
						180.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Preset",
							"parameter_shortname": "Preset",
							"parameter_type": 2,
							"parameter_enum": [
								"init",
								"basic dub",
								"deep haze",
								"detroit 909",
								"deep house",
								"dark rolling",
								"grids drift",
								"euclid"
							],
							"parameter_mmax": 7,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Preset",
							"parameter_info": "Sets every control to a preset and loads its style's first kit; tweak from there. When Live reopens a set, your saved pattern and tweaks win."
						}
					},
					"annotation_name": "Preset",
					"annotation": "Sets every control to a preset and loads its style's first kit; tweak from there. When Live reopens a set, your saved pattern and tweaks win."
				}
			},
			{
				"box": {
					"id": "obj-19",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						520.0,
						64.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "volume",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						824.0,
						3.0,
						64.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Volume",
							"parameter_shortname": "Volume",
							"parameter_type": 0,
							"parameter_mmin": -36.0,
							"parameter_mmax": 12.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 4,
							"parameter_annotation_name": "Volume",
							"parameter_info": "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs."
						}
					},
					"annotation_name": "Volume",
					"annotation": "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs."
				}
			},
			{
				"box": {
					"id": "obj-20",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						938.0,
						100.0,
						22.0
					],
					"text": "prepend volume",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-21",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						540.0,
						48.0,
						15.0
					],
					"text": "stop",
					"outlettype": [
						"",
						""
					],
					"varname": "stop",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						900.0,
						3.0,
						48.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Stop",
							"parameter_shortname": "Stop",
							"parameter_type": 2,
							"parameter_annotation_name": "Stop",
							"parameter_info": "Panic: fades every voice out in 20 ms. Live's transport stopping doesn't run it.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Stop",
					"annotation": "Panic: fades every voice out in 20 ms. Live's transport stopping doesn't run it.",
					"texton": "stop",
					"mode": 0
				}
			},
			{
				"box": {
					"id": "obj-22",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						420.0,
						60.0,
						40.0,
						22.0
					],
					"text": "t b b",
					"outlettype": [
						"bang",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "obj-23",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						420.0,
						90.0,
						90.0,
						22.0
					],
					"text": "path live_set",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-24",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						420.0,
						120.0,
						70.0,
						22.0
					],
					"text": "live.path",
					"outlettype": [
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-25",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						520.0,
						90.0,
						120.0,
						22.0
					],
					"text": "property tempo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-26",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						520.0,
						150.0,
						90.0,
						22.0
					],
					"text": "live.observer",
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-27",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						680.0,
						90.0,
						120.0,
						22.0
					],
					"text": "property is_playing",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-28",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						680.0,
						150.0,
						90.0,
						22.0
					],
					"text": "live.observer",
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-29",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						520.0,
						250.0,
						90.0,
						22.0
					],
					"text": "prepend tempo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-30",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						30.0,
						520.0,
						160.0,
						22.0
					],
					"text": "metro 16n @quantize 16n",
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "obj-31",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						940.0,
						210.0,
						60.0,
						22.0
					],
					"text": "t i i i",
					"outlettype": [
						"int",
						"int",
						"int"
					]
				}
			},
			{
				"box": {
					"id": "obj-32",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						940.0,
						240.0,
						100.0,
						22.0
					],
					"text": "prepend playing",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-33",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 9,
					"patching_rect": [
						30.0,
						550.0,
						70.0,
						22.0
					],
					"text": "transport",
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-34",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						30.0,
						610.0,
						80.0,
						22.0
					],
					"text": "prepend tick",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-35",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1100.0,
						200.0,
						40.0,
						22.0
					],
					"text": "t b b",
					"outlettype": [
						"bang",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "obj-36",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1230.0,
						230.0,
						40.0,
						22.0
					],
					"text": "stop",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-37",
					"maxclass": "newobj",
					"numinlets": 3,
					"numoutlets": 4,
					"patching_rect": [
						1100.0,
						230.0,
						110.0,
						22.0
					],
					"text": "counter 1 1000000",
					"outlettype": [
						"int",
						"",
						"",
						"int"
					]
				}
			},
			{
				"box": {
					"id": "obj-38",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						260.0,
						90.0,
						22.0
					],
					"text": "prepend panic",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-39",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1640.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_bd_a",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_bd_a",
							"parameter_shortname": "steps_bd_a",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								514.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-40",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						978.0,
						100.0,
						22.0
					],
					"text": "prepend steps_bd_a",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-41",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1400.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_bd_b",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_bd_b",
							"parameter_shortname": "steps_bd_b",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								514.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-42",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						982.0,
						100.0,
						22.0
					],
					"text": "prepend steps_bd_b",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-43",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1460.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_sd_a",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_sd_a",
							"parameter_shortname": "steps_sd_a",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								512.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-44",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						986.0,
						100.0,
						22.0
					],
					"text": "prepend steps_sd_a",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-45",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1520.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_sd_b",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_sd_b",
							"parameter_shortname": "steps_sd_b",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								512.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-46",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						990.0,
						100.0,
						22.0
					],
					"text": "prepend steps_sd_b",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-47",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1580.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_rs_a",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_rs_a",
							"parameter_shortname": "steps_rs_a",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-48",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						994.0,
						100.0,
						22.0
					],
					"text": "prepend steps_rs_a",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-49",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1640.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_rs_b",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_rs_b",
							"parameter_shortname": "steps_rs_b",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-50",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						998.0,
						100.0,
						22.0
					],
					"text": "prepend steps_rs_b",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-51",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1400.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_cp_a",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_cp_a",
							"parameter_shortname": "steps_cp_a",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								512.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-52",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1002.0,
						100.0,
						22.0
					],
					"text": "prepend steps_cp_a",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-53",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1460.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_cp_b",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_cp_b",
							"parameter_shortname": "steps_cp_b",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								512.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-54",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1006.0,
						100.0,
						22.0
					],
					"text": "prepend steps_cp_b",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-55",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1520.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_ch_a",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_ch_a",
							"parameter_shortname": "steps_ch_a",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-56",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1010.0,
						100.0,
						22.0
					],
					"text": "prepend steps_ch_a",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-57",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1580.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_ch_b",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_ch_b",
							"parameter_shortname": "steps_ch_b",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-58",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1014.0,
						100.0,
						22.0
					],
					"text": "prepend steps_ch_b",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-59",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1640.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_oh_a",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_oh_a",
							"parameter_shortname": "steps_oh_a",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								8224.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-60",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1018.0,
						100.0,
						22.0
					],
					"text": "prepend steps_oh_a",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-61",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1400.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_oh_b",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_oh_b",
							"parameter_shortname": "steps_oh_b",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								8224.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-62",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1022.0,
						100.0,
						22.0
					],
					"text": "prepend steps_oh_b",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-63",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1460.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_rd_a",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_rd_a",
							"parameter_shortname": "steps_rd_a",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-64",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1026.0,
						100.0,
						22.0
					],
					"text": "prepend steps_rd_a",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-65",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1520.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "steps_rd_b",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "steps_rd_b",
							"parameter_shortname": "steps_rd_b",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-66",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1030.0,
						100.0,
						22.0
					],
					"text": "prepend steps_rd_b",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-67",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1580.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "locks",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "locks",
							"parameter_shortname": "locks",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-68",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1034.0,
						100.0,
						22.0
					],
					"text": "prepend locks",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-69",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1640.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "mutes",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "mutes",
							"parameter_shortname": "mutes",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-70",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1038.0,
						100.0,
						22.0
					],
					"text": "prepend mutes",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-71",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 17,
					"patching_rect": [
						1100.0,
						120.0,
						600.0,
						22.0
					],
					"text": "route steps_bd_a steps_bd_b steps_sd_a steps_sd_b steps_rs_a steps_rs_b steps_cp_a steps_cp_b steps_ch_a steps_ch_b steps_oh_a steps_oh_b steps_rd_a steps_rd_b locks mutes",
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-72",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1028.0,
						384.0,
						85.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"grid"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						384.0,
						85.0
					],
					"border": 0,
					"annotation_name": "Pattern",
					"annotation": "The pattern: a row per voice, 16 steps. Click a step: rest, hit, accent (bright with a bar on top). Shift-click: a ghost (dim; plays only at high Density or with Variation). Left: the voice name, click to mute (struck through). Right: L locks the row (Generate, Reroll, Style and Canned leave it), R rerolls it. Blue outline: the step playing. Warm: a fill bar.",
					"varname": "view_grid"
				}
			},
			{
				"box": {
					"id": "obj-73",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1512.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "variation",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						12.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Variation",
							"parameter_shortname": "Variation",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Variation",
							"parameter_info": "Grids' randomness: every bar, each voice gets a random push to all its steps' levels (up to about 62 of 255), so weaker steps come and go a bar at a time. With Fill on it also adds phrase-end fills. 0 = the pattern repeats exactly."
						}
					},
					"annotation_name": "Variation",
					"annotation": "Grids' randomness: every bar, each voice gets a random push to all its steps' levels (up to about 62 of 255), so weaker steps come and go a bar at a time. With Fill on it also adds phrase-end fills. 0 = the pattern repeats exactly."
				}
			},
			{
				"box": {
					"id": "obj-74",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1046.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-75",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1048.0,
						100.0,
						22.0
					],
					"text": "prepend variation",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-76",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1568.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "density",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						68.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Density",
							"parameter_shortname": "Density",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Density",
							"parameter_info": "Grids' density: a step plays when its level is above 255 - Density. At 50% (default) accents and hits play, ghosts don't; lower thins to accents, higher brings ghosts in."
						}
					},
					"annotation_name": "Density",
					"annotation": "Grids' density: a step plays when its level is above 255 - Density. At 50% (default) accents and hits play, ghosts don't; lower thins to accents, higher brings ghosts in."
				}
			},
			{
				"box": {
					"id": "obj-77",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1052.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-78",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1054.0,
						100.0,
						22.0
					],
					"text": "prepend density",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-79",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1624.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "accent",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						124.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Accent",
							"parameter_shortname": "Accent",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								70.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Accent",
							"parameter_info": "How much quieter a normal hit is than an accent, like the 909's Total Accent. 0 = all the same. Default 70%."
						}
					},
					"annotation_name": "Accent",
					"annotation": "How much quieter a normal hit is than an accent, like the 909's Total Accent. 0 = all the same. Default 70%."
				}
			},
			{
				"box": {
					"id": "obj-80",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1058.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-81",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1060.0,
						100.0,
						22.0
					],
					"text": "prepend accent",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-82",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1684.0,
						776.0,
						88.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "swing",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						184.0,
						136.0,
						88.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Swing",
							"parameter_shortname": "Swing",
							"parameter_type": 2,
							"parameter_enum": [
								"1: 50%",
								"2: 54%",
								"3: 58%",
								"4: 62%",
								"5: 67%",
								"6: 71%",
								"7: 75%"
							],
							"parameter_mmax": 6,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Swing",
							"parameter_info": "The 909's shuffle, 1 (none) to 7: every second 16th later, 50% to 75% of the 8th. Sample-accurate in the voices."
						}
					},
					"annotation_name": "Swing",
					"annotation": "The 909's shuffle, 1 (none) to 7: every second 16th later, 50% to 75% of the 8th. Sample-accurate in the voices."
				}
			},
			{
				"box": {
					"id": "obj-83",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1064.0,
						100.0,
						22.0
					],
					"text": "prepend swing",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-84",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1776.0,
						776.0,
						80.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "fill",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						276.0,
						136.0,
						80.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Fill",
							"parameter_shortname": "Fill",
							"parameter_type": 2,
							"parameter_enum": [
								"off",
								"4 bars",
								"8 bars"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Fill",
							"parameter_info": "Phrase-end fills: off, or in the last beat of every 4 or 8 bars. Snare, rim and clap get extra hits and an open hat may close. Scaled by Variation (none at 0)."
						}
					},
					"annotation_name": "Fill",
					"annotation": "Phrase-end fills: off, or in the last beat of every 4 or 8 bars. Snare, rim and clap get extra hits and an open hat may close. Scaled by Variation (none at 0)."
				}
			},
			{
				"box": {
					"id": "obj-85",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1068.0,
						100.0,
						22.0
					],
					"text": "prepend fill",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-86",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1920.0,
						1028.0,
						172.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"style"
					],
					"presentation": 1,
					"presentation_rect": [
						420.0,
						28.0,
						172.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Style",
					"annotation": "The style's name, the tempo and swing its sources use, the canned kit loaded last, and (with Fill on) the bar in the fill phrase, warm on the fill bar.",
					"varname": "view_style"
				}
			},
			{
				"box": {
					"id": "obj-87",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1920.0,
						738.0,
						172.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "style",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						420.0,
						98.0,
						172.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Style",
							"parameter_shortname": "Style",
							"parameter_type": 2,
							"parameter_enum": [
								"dub techno",
								"deep house",
								"detroit",
								"dark techno",
								"euclid",
								"grids"
							],
							"parameter_mmax": 5,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Style",
							"parameter_info": "Where patterns come from: dub techno, deep house, detroit, dark techno (sourced grids), euclid (Toussaint's rhythms) or grids (the Mutable Instruments Grids map). Loads its first kit."
						}
					},
					"annotation_name": "Style",
					"annotation": "Where patterns come from: dub techno, deep house, detroit, dark techno (sourced grids), euclid (Toussaint's rhythms) or grids (the Mutable Instruments Grids map). Loads its first kit."
				}
			},
			{
				"box": {
					"id": "obj-88",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1074.0,
						100.0,
						22.0
					],
					"text": "prepend style",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-89",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1920.0,
						796.0,
						84.0,
						15.0
					],
					"text": "generate",
					"outlettype": [
						"",
						""
					],
					"varname": "generate",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						420.0,
						136.0,
						84.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Generate",
							"parameter_shortname": "Generate",
							"parameter_type": 2,
							"parameter_annotation_name": "Generate",
							"parameter_info": "A new kit pattern from the style for every unlocked voice: rows from the style's sources, a new Euclidean row, or a new point on the Grids map.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Generate",
					"annotation": "A new kit pattern from the style for every unlocked voice: rows from the style's sources, a new Euclidean row, or a new point on the Grids map.",
					"texton": "generate",
					"mode": 0
				}
			},
			{
				"box": {
					"id": "obj-90",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2008.0,
						796.0,
						84.0,
						15.0
					],
					"text": "canned",
					"outlettype": [
						"",
						""
					],
					"varname": "canned",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						508.0,
						136.0,
						84.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Canned",
							"parameter_shortname": "Canned",
							"parameter_type": 2,
							"parameter_annotation_name": "Canned",
							"parameter_info": "The style's next canned kit, as its source has it (unlocked voices).",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Canned",
					"annotation": "The style's next canned kit, as its source has it (unlocked voices).",
					"texton": "canned",
					"mode": 0
				}
			},
			{
				"box": {
					"id": "obj-91",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						480.0,
						70.0,
						22.0
					],
					"text": "generate",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-92",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						482.0,
						70.0,
						22.0
					],
					"text": "canned",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-93",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						2116.0,
						1028.0,
						332.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"mix"
					],
					"presentation": 1,
					"presentation_rect": [
						616.0,
						28.0,
						332.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Mix",
					"annotation": "Each voice's level as a bar, flashing as it plays (taller for louder hits).",
					"varname": "view_mix"
				}
			},
			{
				"box": {
					"id": "obj-94",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2116.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "bd_level",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						616.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Level",
							"parameter_shortname": "BD",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								80.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "BD Level",
							"parameter_info": "Level of the bd in the mix. 909 accents still play louder (Accent)."
						}
					},
					"annotation_name": "BD Level",
					"annotation": "Level of the bd in the mix. 909 accents still play louder (Accent)."
				}
			},
			{
				"box": {
					"id": "obj-95",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1088.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-96",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1090.0,
						100.0,
						22.0
					],
					"text": "prepend bd_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-97",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1092.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-98",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1094.0,
						100.0,
						22.0
					],
					"text": "prepend bd_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-99",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2164.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "sd_level",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						664.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Level",
							"parameter_shortname": "SD",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								70.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "SD Level",
							"parameter_info": "Level of the sd in the mix. 909 accents still play louder (Accent)."
						}
					},
					"annotation_name": "SD Level",
					"annotation": "Level of the sd in the mix. 909 accents still play louder (Accent)."
				}
			},
			{
				"box": {
					"id": "obj-100",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1098.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-101",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1100.0,
						100.0,
						22.0
					],
					"text": "prepend sd_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-102",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1102.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-103",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1104.0,
						100.0,
						22.0
					],
					"text": "prepend sd_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-104",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2212.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "rs_level",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						712.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RS Level",
							"parameter_shortname": "RS",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RS Level",
							"parameter_info": "Level of the rs in the mix. 909 accents still play louder (Accent)."
						}
					},
					"annotation_name": "RS Level",
					"annotation": "Level of the rs in the mix. 909 accents still play louder (Accent)."
				}
			},
			{
				"box": {
					"id": "obj-105",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1108.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-106",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1110.0,
						100.0,
						22.0
					],
					"text": "prepend rs_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-107",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1112.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-108",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1114.0,
						100.0,
						22.0
					],
					"text": "prepend rs_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-109",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2260.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "cp_level",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						760.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CP Level",
							"parameter_shortname": "CP",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								60.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "CP Level",
							"parameter_info": "Level of the cp in the mix. 909 accents still play louder (Accent)."
						}
					},
					"annotation_name": "CP Level",
					"annotation": "Level of the cp in the mix. 909 accents still play louder (Accent)."
				}
			},
			{
				"box": {
					"id": "obj-110",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1118.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-111",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1120.0,
						100.0,
						22.0
					],
					"text": "prepend cp_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-112",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1122.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-113",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1124.0,
						100.0,
						22.0
					],
					"text": "prepend cp_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-114",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2308.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "ch_level",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						808.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH Level",
							"parameter_shortname": "CH",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "CH Level",
							"parameter_info": "Level of the ch in the mix. 909 accents still play louder (Accent)."
						}
					},
					"annotation_name": "CH Level",
					"annotation": "Level of the ch in the mix. 909 accents still play louder (Accent)."
				}
			},
			{
				"box": {
					"id": "obj-115",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1128.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-116",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1130.0,
						100.0,
						22.0
					],
					"text": "prepend ch_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-117",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1132.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-118",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1134.0,
						100.0,
						22.0
					],
					"text": "prepend ch_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-119",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2356.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "oh_level",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						856.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "OH Level",
							"parameter_shortname": "OH",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "OH Level",
							"parameter_info": "Level of the oh in the mix. 909 accents still play louder (Accent)."
						}
					},
					"annotation_name": "OH Level",
					"annotation": "Level of the oh in the mix. 909 accents still play louder (Accent)."
				}
			},
			{
				"box": {
					"id": "obj-120",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1138.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-121",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1140.0,
						100.0,
						22.0
					],
					"text": "prepend oh_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-122",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1142.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-123",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1144.0,
						100.0,
						22.0
					],
					"text": "prepend oh_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-124",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2404.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "rd_level",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						904.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RD Level",
							"parameter_shortname": "RD",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								40.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RD Level",
							"parameter_info": "Level of the rd in the mix. 909 accents still play louder (Accent)."
						}
					},
					"annotation_name": "RD Level",
					"annotation": "Level of the rd in the mix. 909 accents still play louder (Accent)."
				}
			},
			{
				"box": {
					"id": "obj-125",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1148.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-126",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1150.0,
						100.0,
						22.0
					],
					"text": "prepend rd_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-127",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1152.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-128",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1154.0,
						100.0,
						22.0
					],
					"text": "prepend rd_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-129",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1028.0,
						324.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"bd"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						324.0,
						64.0
					],
					"border": 0,
					"annotation_name": "BD",
					"annotation": "The kick's level (mint) and pitch (grey) over its decay, as the voice makes them. Top right: the pitch it settles to and the decay.",
					"varname": "view_bd",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-130",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1512.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "bd_tune",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						12.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Tune",
							"parameter_shortname": "Tune",
							"parameter_type": 0,
							"parameter_mmin": 30.0,
							"parameter_mmax": 90.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 3,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "BD Tune",
							"parameter_info": "The pitch the kick settles to, 30-90 Hz (default 50)."
						}
					},
					"annotation_name": "BD Tune",
					"annotation": "The pitch the kick settles to, 30-90 Hz (default 50).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-131",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1160.0,
						100.0,
						22.0
					],
					"text": "prepend bd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-132",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1162.0,
						100.0,
						22.0
					],
					"text": "prepend bd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-133",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1568.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "bd_sweep",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						68.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Sweep",
							"parameter_shortname": "Sweep",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "BD Sweep",
							"parameter_info": "How far above Tune the kick starts: up to 4x, falling in about 30 ms. Default 50%."
						}
					},
					"annotation_name": "BD Sweep",
					"annotation": "How far above Tune the kick starts: up to 4x, falling in about 30 ms. Default 50%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-134",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1166.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-135",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1168.0,
						100.0,
						22.0
					],
					"text": "prepend bd_sweep",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-136",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1170.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-137",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1172.0,
						100.0,
						22.0
					],
					"text": "prepend bd_sweep",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-138",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1624.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "bd_decay",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						124.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Decay",
							"parameter_shortname": "Decay",
							"parameter_type": 0,
							"parameter_mmin": 60.0,
							"parameter_mmax": 2000.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								450.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 2.0,
							"parameter_annotation_name": "BD Decay",
							"parameter_info": "Time to -40 dB, 60 ms to 2 s (default 450 ms). Flat at first, like the 909's ENV-1."
						}
					},
					"annotation_name": "BD Decay",
					"annotation": "Time to -40 dB, 60 ms to 2 s (default 450 ms). Flat at first, like the 909's ENV-1.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-139",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1176.0,
						100.0,
						22.0
					],
					"text": "prepend bd_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-140",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1178.0,
						100.0,
						22.0
					],
					"text": "prepend bd_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-141",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1680.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "bd_attack",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						180.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Attack",
							"parameter_shortname": "Attack",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "BD Attack",
							"parameter_info": "The click: a short pulse and low-passed noise, as the 909's Attack knob. Default 50%."
						}
					},
					"annotation_name": "BD Attack",
					"annotation": "The click: a short pulse and low-passed noise, as the 909's Attack knob. Default 50%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-142",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1182.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-143",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1184.0,
						100.0,
						22.0
					],
					"text": "prepend bd_attack",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-144",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1186.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-145",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1188.0,
						100.0,
						22.0
					],
					"text": "prepend bd_attack",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-146",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1736.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "bd_soft",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						236.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Soft",
							"parameter_shortname": "Soft",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "BD Soft",
							"parameter_info": "0 = 909 punch. Up: a sine instead of the clipped triangle, less and slower sweep, no click, a slower start and a darker low-pass, for a soft, round, muffled kick."
						}
					},
					"annotation_name": "BD Soft",
					"annotation": "0 = 909 punch. Up: a sine instead of the clipped triangle, less and slower sweep, no click, a slower start and a darker low-pass, for a soft, round, muffled kick.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-147",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1192.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-148",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1194.0,
						100.0,
						22.0
					],
					"text": "prepend bd_soft",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-149",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1196.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-150",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1198.0,
						100.0,
						22.0
					],
					"text": "prepend bd_soft",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-151",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1792.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "bd_bits",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						292.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "BD Bits",
							"parameter_info": "Bit reduction on the kick, 16 (clean) down to 3."
						}
					},
					"annotation_name": "BD Bits",
					"annotation": "Bit reduction on the kick, 16 (clean) down to 3.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-152",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1202.0,
						100.0,
						22.0
					],
					"text": "prepend bd_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-153",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1204.0,
						100.0,
						22.0
					],
					"text": "prepend bd_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-154",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1860.0,
						1028.0,
						212.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"sd"
					],
					"presentation": 1,
					"presentation_rect": [
						360.0,
						28.0,
						212.0,
						64.0
					],
					"border": 0,
					"annotation_name": "SD",
					"annotation": "The snare's drum (mint) and snappy noise (grey) envelopes. Top right: VCO 1's pitch.",
					"varname": "view_sd",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-155",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1860.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "sd_tune",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						360.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Tune",
							"parameter_shortname": "Tune",
							"parameter_type": 0,
							"parameter_mmin": 120.0,
							"parameter_mmax": 320.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								180.0
							],
							"parameter_unitstyle": 3,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "SD Tune",
							"parameter_info": "VCO 1's pitch, 120-320 Hz (default 180); VCO 2 follows at x1.83. Both bend for 20 ms."
						}
					},
					"annotation_name": "SD Tune",
					"annotation": "VCO 1's pitch, 120-320 Hz (default 180); VCO 2 follows at x1.83. Both bend for 20 ms.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-156",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1210.0,
						100.0,
						22.0
					],
					"text": "prepend sd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-157",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1212.0,
						100.0,
						22.0
					],
					"text": "prepend sd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-158",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1916.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "sd_tone",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						416.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Tone",
							"parameter_shortname": "Tone",
							"parameter_type": 0,
							"parameter_mmin": 40.0,
							"parameter_mmax": 500.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								160.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 1.5,
							"parameter_annotation_name": "SD Tone",
							"parameter_info": "Decay of the main snappy noise after its 24 ms hold, 40-500 ms (default 160)."
						}
					},
					"annotation_name": "SD Tone",
					"annotation": "Decay of the main snappy noise after its 24 ms hold, 40-500 ms (default 160).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-159",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1216.0,
						100.0,
						22.0
					],
					"text": "prepend sd_tone",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-160",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1218.0,
						100.0,
						22.0
					],
					"text": "prepend sd_tone",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-161",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1972.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "sd_snappy",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						472.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Snappy",
							"parameter_shortname": "Snappy",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								60.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "SD Snappy",
							"parameter_info": "The snare's noise level; 0 = drum only. Default 60%."
						}
					},
					"annotation_name": "SD Snappy",
					"annotation": "The snare's noise level; 0 = drum only. Default 60%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-162",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1222.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-163",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1224.0,
						100.0,
						22.0
					],
					"text": "prepend sd_snappy",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-164",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1226.0,
						50.0,
						22.0
					],
					"text": "* 0.01",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-165",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1228.0,
						100.0,
						22.0
					],
					"text": "prepend sd_snappy",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-166",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2028.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "sd_bits",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						528.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "SD Bits",
							"parameter_info": "Bit reduction on the snare, 16 (clean) down to 3."
						}
					},
					"annotation_name": "SD Bits",
					"annotation": "Bit reduction on the snare, 16 (clean) down to 3.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-167",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1232.0,
						100.0,
						22.0
					],
					"text": "prepend sd_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-168",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1234.0,
						100.0,
						22.0
					],
					"text": "prepend sd_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-169",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						2096.0,
						1028.0,
						352.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"rs"
					],
					"presentation": 1,
					"presentation_rect": [
						596.0,
						28.0,
						352.0,
						64.0
					],
					"border": 0,
					"annotation_name": "RS",
					"annotation": "The rim shot's envelope: three rings at 500, 220 and 1000 Hz, clipped, short.",
					"varname": "view_rs",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-170",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2096.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "rs_bits",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						596.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RS Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RS Bits",
							"parameter_info": "Bit reduction on the rim shot, 16 (clean) down to 3."
						}
					},
					"annotation_name": "RS Bits",
					"annotation": "Bit reduction on the rim shot, 16 (clean) down to 3.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-171",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1240.0,
						100.0,
						22.0
					],
					"text": "prepend rs_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-172",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1242.0,
						100.0,
						22.0
					],
					"text": "prepend rs_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-173",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1028.0,
						156.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"cp"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						156.0,
						64.0
					],
					"border": 0,
					"annotation_name": "CP",
					"annotation": "The clap's envelope: four claps 11 ms apart, then the softer tail.",
					"varname": "view_cp",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-174",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1512.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "cp_bits",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						12.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CP Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "CP Bits",
							"parameter_info": "Bit reduction on the clap, 16 (clean) down to 3. Attack's dub techno clap uses 6."
						}
					},
					"annotation_name": "CP Bits",
					"annotation": "Bit reduction on the clap, 16 (clean) down to 3. Attack's dub techno clap uses 6.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-175",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1248.0,
						100.0,
						22.0
					],
					"text": "prepend cp_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-176",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1250.0,
						100.0,
						22.0
					],
					"text": "prepend cp_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-177",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1692.0,
						1028.0,
						324.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"hats"
					],
					"presentation": 1,
					"presentation_rect": [
						192.0,
						28.0,
						324.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Hats",
					"annotation": "Closed (mint) and open (grey) hat envelopes. They are one voice, as on the 909: a closed hit cuts an open one. Top right: the ROM clock and bits.",
					"varname": "view_hats",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-178",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1692.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "hat_tune",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						192.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Hat Tune",
							"parameter_shortname": "Tune",
							"parameter_type": 0,
							"parameter_mmin": 0.43,
							"parameter_mmax": 1.7,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Hat Tune",
							"parameter_info": "The hat ROM's clock, x0.43 to x1.7 (Whittle's tune mod range): pitch and grit."
						}
					},
					"annotation_name": "Hat Tune",
					"annotation": "The hat ROM's clock, x0.43 to x1.7 (Whittle's tune mod range): pitch and grit.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-179",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1256.0,
						100.0,
						22.0
					],
					"text": "prepend hat_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-180",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1258.0,
						100.0,
						22.0
					],
					"text": "prepend hat_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-181",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1748.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "ch_decay",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						248.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH Decay",
							"parameter_shortname": "CH Decay",
							"parameter_type": 0,
							"parameter_mmin": 10.0,
							"parameter_mmax": 300.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								60.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 1.5,
							"parameter_annotation_name": "CH Decay",
							"parameter_info": "Closed hat decay to -40 dB, 10-300 ms (default 60)."
						}
					},
					"annotation_name": "CH Decay",
					"annotation": "Closed hat decay to -40 dB, 10-300 ms (default 60).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-182",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1262.0,
						100.0,
						22.0
					],
					"text": "prepend ch_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-183",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1264.0,
						100.0,
						22.0
					],
					"text": "prepend ch_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-184",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1804.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "oh_decay",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						304.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "OH Decay",
							"parameter_shortname": "OH Decay",
							"parameter_type": 0,
							"parameter_mmin": 80.0,
							"parameter_mmax": 2000.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								500.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 2.0,
							"parameter_annotation_name": "OH Decay",
							"parameter_info": "Open hat decay to -40 dB, 80 ms to 2 s (default 500). A closed hit cuts it."
						}
					},
					"annotation_name": "OH Decay",
					"annotation": "Open hat decay to -40 dB, 80 ms to 2 s (default 500). A closed hit cuts it.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-185",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1268.0,
						100.0,
						22.0
					],
					"text": "prepend oh_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-186",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1270.0,
						100.0,
						22.0
					],
					"text": "prepend oh_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-187",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1860.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "hat_bits",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						360.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Hat Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_mmin": 2.0,
							"parameter_mmax": 12.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								6.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Hat Bits",
							"parameter_info": "The hat ROM's bit depth: 6 on the 909 (default). Lower is grittier."
						}
					},
					"annotation_name": "Hat Bits",
					"annotation": "The hat ROM's bit depth: 6 on the 909 (default). Lower is grittier.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-188",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1274.0,
						100.0,
						22.0
					],
					"text": "prepend hat_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-189",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1276.0,
						100.0,
						22.0
					],
					"text": "prepend hat_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-190",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						2040.0,
						1028.0,
						408.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"rd"
					],
					"presentation": 1,
					"presentation_rect": [
						540.0,
						28.0,
						408.0,
						64.0
					],
					"border": 0,
					"annotation_name": "RD",
					"annotation": "The ride's envelope; its length follows Tune, as the 909's ROM clock does.",
					"varname": "view_rd",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-191",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2040.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "rd_tune",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						540.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RD Tune",
							"parameter_shortname": "Tune",
							"parameter_type": 0,
							"parameter_mmin": 0.6,
							"parameter_mmax": 1.5,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RD Tune",
							"parameter_info": "The ride ROM's clock, x0.6 to x1.5: pitch and length together, as on the 909 (no decay knob)."
						}
					},
					"annotation_name": "RD Tune",
					"annotation": "The ride ROM's clock, x0.6 to x1.5: pitch and length together, as on the 909 (no decay knob).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-192",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1282.0,
						100.0,
						22.0
					],
					"text": "prepend rd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-193",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1284.0,
						100.0,
						22.0
					],
					"text": "prepend rd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-194",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2096.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "rd_bits",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						596.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RD Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_mmin": 2.0,
							"parameter_mmax": 12.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								6.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RD Bits",
							"parameter_info": "The ride ROM's bit depth: 6 on the 909 (default)."
						}
					},
					"annotation_name": "RD Bits",
					"annotation": "The ride ROM's bit depth: 6 on the 909 (default).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-195",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1288.0,
						100.0,
						22.0
					],
					"text": "prepend rd_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-196",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1290.0,
						100.0,
						22.0
					],
					"text": "prepend rd_bits",
					"outlettype": [
						""
					]
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"source": [
						"obj-1",
						0
					],
					"destination": [
						"obj-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-2",
						0
					],
					"destination": [
						"obj-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-4",
						0
					],
					"destination": [
						"obj-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-4",
						1
					],
					"destination": [
						"obj-5",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-7",
						0
					],
					"destination": [
						"obj-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-9",
						0
					],
					"destination": [
						"obj-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-10",
						0
					],
					"destination": [
						"obj-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-11",
						0
					],
					"destination": [
						"obj-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-12",
						1
					],
					"destination": [
						"obj-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-13",
						0
					],
					"destination": [
						"obj-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-15",
						0
					],
					"destination": [
						"obj-16",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-16",
						0
					],
					"destination": [
						"obj-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-15",
						0
					],
					"destination": [
						"obj-17",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-17",
						0
					],
					"destination": [
						"obj-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-18",
						0
					],
					"destination": [
						"obj-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-19",
						0
					],
					"destination": [
						"obj-20",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-20",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-11",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-9",
						0
					],
					"destination": [
						"obj-22",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-22",
						0
					],
					"destination": [
						"obj-23",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-23",
						0
					],
					"destination": [
						"obj-24",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-22",
						1
					],
					"destination": [
						"obj-25",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-25",
						0
					],
					"destination": [
						"obj-26",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-24",
						0
					],
					"destination": [
						"obj-26",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-22",
						1
					],
					"destination": [
						"obj-27",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-27",
						0
					],
					"destination": [
						"obj-28",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-24",
						0
					],
					"destination": [
						"obj-28",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-26",
						0
					],
					"destination": [
						"obj-29",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-29",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-28",
						0
					],
					"destination": [
						"obj-31",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-31",
						2
					],
					"destination": [
						"obj-32",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-32",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-31",
						0
					],
					"destination": [
						"obj-30",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-30",
						0
					],
					"destination": [
						"obj-33",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-33",
						7
					],
					"destination": [
						"obj-34",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-34",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-21",
						0
					],
					"destination": [
						"obj-35",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-35",
						1
					],
					"destination": [
						"obj-36",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-36",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-35",
						0
					],
					"destination": [
						"obj-37",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-37",
						0
					],
					"destination": [
						"obj-38",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-38",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-39",
						0
					],
					"destination": [
						"obj-40",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-40",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-41",
						0
					],
					"destination": [
						"obj-42",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-42",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-43",
						0
					],
					"destination": [
						"obj-44",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-44",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-45",
						0
					],
					"destination": [
						"obj-46",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-46",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-47",
						0
					],
					"destination": [
						"obj-48",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-48",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-49",
						0
					],
					"destination": [
						"obj-50",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-50",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-51",
						0
					],
					"destination": [
						"obj-52",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-52",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-53",
						0
					],
					"destination": [
						"obj-54",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-54",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-55",
						0
					],
					"destination": [
						"obj-56",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-56",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-57",
						0
					],
					"destination": [
						"obj-58",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-58",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-59",
						0
					],
					"destination": [
						"obj-60",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-60",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-61",
						0
					],
					"destination": [
						"obj-62",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-62",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-63",
						0
					],
					"destination": [
						"obj-64",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-64",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-65",
						0
					],
					"destination": [
						"obj-66",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-66",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-67",
						0
					],
					"destination": [
						"obj-68",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-68",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-69",
						0
					],
					"destination": [
						"obj-70",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-70",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						4
					],
					"destination": [
						"obj-71",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						0
					],
					"destination": [
						"obj-39",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						1
					],
					"destination": [
						"obj-41",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						2
					],
					"destination": [
						"obj-43",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						3
					],
					"destination": [
						"obj-45",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						4
					],
					"destination": [
						"obj-47",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						5
					],
					"destination": [
						"obj-49",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						6
					],
					"destination": [
						"obj-51",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						7
					],
					"destination": [
						"obj-53",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						8
					],
					"destination": [
						"obj-55",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						9
					],
					"destination": [
						"obj-57",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						10
					],
					"destination": [
						"obj-59",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						11
					],
					"destination": [
						"obj-61",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						12
					],
					"destination": [
						"obj-63",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						13
					],
					"destination": [
						"obj-65",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						14
					],
					"destination": [
						"obj-67",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-71",
						15
					],
					"destination": [
						"obj-69",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						1
					],
					"destination": [
						"obj-72",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-72",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-73",
						0
					],
					"destination": [
						"obj-74",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-74",
						0
					],
					"destination": [
						"obj-75",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-75",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-76",
						0
					],
					"destination": [
						"obj-77",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-77",
						0
					],
					"destination": [
						"obj-78",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-78",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-79",
						0
					],
					"destination": [
						"obj-80",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-80",
						0
					],
					"destination": [
						"obj-81",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-81",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-82",
						0
					],
					"destination": [
						"obj-83",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-83",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-84",
						0
					],
					"destination": [
						"obj-85",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-85",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						2
					],
					"destination": [
						"obj-86",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-87",
						0
					],
					"destination": [
						"obj-88",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-88",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-89",
						0
					],
					"destination": [
						"obj-91",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-91",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-90",
						0
					],
					"destination": [
						"obj-92",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-92",
						0
					],
					"destination": [
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-94",
						0
					],
					"destination": [
						"obj-95",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-95",
						0
					],
					"destination": [
						"obj-96",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-96",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-94",
						0
					],
					"destination": [
						"obj-97",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-97",
						0
					],
					"destination": [
						"obj-98",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-98",
						0
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-99",
						0
					],
					"destination": [
						"obj-100",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-100",
						0
					],
					"destination": [
						"obj-101",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-101",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-99",
						0
					],
					"destination": [
						"obj-102",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-102",
						0
					],
					"destination": [
						"obj-103",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-103",
						0
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-104",
						0
					],
					"destination": [
						"obj-105",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-105",
						0
					],
					"destination": [
						"obj-106",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-106",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-104",
						0
					],
					"destination": [
						"obj-107",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-107",
						0
					],
					"destination": [
						"obj-108",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-108",
						0
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-109",
						0
					],
					"destination": [
						"obj-110",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-110",
						0
					],
					"destination": [
						"obj-111",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-111",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-109",
						0
					],
					"destination": [
						"obj-112",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-112",
						0
					],
					"destination": [
						"obj-113",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-113",
						0
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-114",
						0
					],
					"destination": [
						"obj-115",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-115",
						0
					],
					"destination": [
						"obj-116",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-116",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-114",
						0
					],
					"destination": [
						"obj-117",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-117",
						0
					],
					"destination": [
						"obj-118",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-118",
						0
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-119",
						0
					],
					"destination": [
						"obj-120",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-120",
						0
					],
					"destination": [
						"obj-121",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-121",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-119",
						0
					],
					"destination": [
						"obj-122",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-122",
						0
					],
					"destination": [
						"obj-123",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-123",
						0
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-124",
						0
					],
					"destination": [
						"obj-125",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-125",
						0
					],
					"destination": [
						"obj-126",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-126",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-124",
						0
					],
					"destination": [
						"obj-127",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-127",
						0
					],
					"destination": [
						"obj-128",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-128",
						0
					],
					"destination": [
						"obj-93",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-130",
						0
					],
					"destination": [
						"obj-131",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-131",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-130",
						0
					],
					"destination": [
						"obj-132",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-132",
						0
					],
					"destination": [
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-133",
						0
					],
					"destination": [
						"obj-134",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-134",
						0
					],
					"destination": [
						"obj-135",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-135",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-133",
						0
					],
					"destination": [
						"obj-136",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-136",
						0
					],
					"destination": [
						"obj-137",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-137",
						0
					],
					"destination": [
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-138",
						0
					],
					"destination": [
						"obj-139",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-139",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-138",
						0
					],
					"destination": [
						"obj-140",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-140",
						0
					],
					"destination": [
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-141",
						0
					],
					"destination": [
						"obj-142",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-142",
						0
					],
					"destination": [
						"obj-143",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-143",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-141",
						0
					],
					"destination": [
						"obj-144",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-144",
						0
					],
					"destination": [
						"obj-145",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-145",
						0
					],
					"destination": [
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-146",
						0
					],
					"destination": [
						"obj-147",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-147",
						0
					],
					"destination": [
						"obj-148",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-148",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-146",
						0
					],
					"destination": [
						"obj-149",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-149",
						0
					],
					"destination": [
						"obj-150",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-150",
						0
					],
					"destination": [
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-151",
						0
					],
					"destination": [
						"obj-152",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-152",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-151",
						0
					],
					"destination": [
						"obj-153",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-153",
						0
					],
					"destination": [
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-155",
						0
					],
					"destination": [
						"obj-156",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-156",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-155",
						0
					],
					"destination": [
						"obj-157",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-157",
						0
					],
					"destination": [
						"obj-154",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-158",
						0
					],
					"destination": [
						"obj-159",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-159",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-158",
						0
					],
					"destination": [
						"obj-160",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-160",
						0
					],
					"destination": [
						"obj-154",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-161",
						0
					],
					"destination": [
						"obj-162",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-162",
						0
					],
					"destination": [
						"obj-163",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-163",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-161",
						0
					],
					"destination": [
						"obj-164",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-164",
						0
					],
					"destination": [
						"obj-165",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-165",
						0
					],
					"destination": [
						"obj-154",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-166",
						0
					],
					"destination": [
						"obj-167",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-167",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-166",
						0
					],
					"destination": [
						"obj-168",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-168",
						0
					],
					"destination": [
						"obj-154",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-170",
						0
					],
					"destination": [
						"obj-171",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-171",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-170",
						0
					],
					"destination": [
						"obj-172",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-172",
						0
					],
					"destination": [
						"obj-169",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-174",
						0
					],
					"destination": [
						"obj-175",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-175",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-174",
						0
					],
					"destination": [
						"obj-176",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-176",
						0
					],
					"destination": [
						"obj-173",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-178",
						0
					],
					"destination": [
						"obj-179",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-179",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-178",
						0
					],
					"destination": [
						"obj-180",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-180",
						0
					],
					"destination": [
						"obj-177",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-181",
						0
					],
					"destination": [
						"obj-182",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-182",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-181",
						0
					],
					"destination": [
						"obj-183",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-183",
						0
					],
					"destination": [
						"obj-177",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-184",
						0
					],
					"destination": [
						"obj-185",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-185",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-184",
						0
					],
					"destination": [
						"obj-186",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-186",
						0
					],
					"destination": [
						"obj-177",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-187",
						0
					],
					"destination": [
						"obj-188",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-188",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-187",
						0
					],
					"destination": [
						"obj-189",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-189",
						0
					],
					"destination": [
						"obj-177",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-191",
						0
					],
					"destination": [
						"obj-192",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-192",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-191",
						0
					],
					"destination": [
						"obj-193",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-193",
						0
					],
					"destination": [
						"obj-190",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-194",
						0
					],
					"destination": [
						"obj-195",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-195",
						0
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-194",
						0
					],
					"destination": [
						"obj-196",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-196",
						0
					],
					"destination": [
						"obj-190",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-154",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-169",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-173",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-177",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-190",
						0
					]
				}
			}
		]
	}
}