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
		"devicewidth": 772.0,
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
					"numoutlets": 6,
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
									"code": "// bit reduction: `bits` of resolution over -1..+1 (16 = clean)\ncrush(signal, bits) {\n\tsteps = pow(2, bits - 1);\n\treturn floor(signal * steps + 0.5) / steps;\n}\n// the 909's back-to-back diodes after a triangle VCO: round it towards a sine (Whittle; network-909)\ndiode_round(signal, drive) {\n\treturn tanh(signal * drive) / tanh(drive);\n}\n// a triangle that starts at 0 and rises, from a 0..1 phase (the VCO restarts at every trigger)\ntriangle_from_phase(phase) {\n\treturn 1 - 4 * abs(wrap(phase + 0.25, 0, 1) - 0.5);\n}\n// a square from a 0..1 phase\nsquare_from_phase(phase) {\n\treturn phase < 0.5 ? 1 : -1;\n}\n// one-pole low-pass coefficient for a cutoff in Hz\nonepole_coefficient(cutoff_hz, sample_rate) {\n\treturn 1 - exp(-twopi * min(cutoff_hz, sample_rate * 0.45) / sample_rate);\n}\n// per-sample multiplier of an exponential decay that falls 40 dB in `time_ms`\ndecay_multiplier(time_ms, sample_rate) {\n\treturn exp(-4.6 / max(time_ms * 0.001 * sample_rate, 1));\n}\n// two-pole resonator feedback for a ring at `frequency_hz` decaying 40 dB in `time_ms` (bridged-T stand-in)\nresonator_radius(time_ms, sample_rate) {\n\treturn decay_multiplier(time_ms, sample_rate);\n}\n// the 909's accent: a hit below full velocity plays quieter by Accent (Total Accent knob)\naccent_gain(velocity, accent_amount) {\n\treturn 1 - accent_amount * (1 - velocity);\n}\n// soft clip: clean below 0.8, rounding off above (2sl stab's output stage)\nsoft_clip(signal) {\n\tmagnitude = abs(signal);\n\tshaped = signal;\n\tif (magnitude > 0.8) {\n\t\tshaped = (signal < 0 ? -1 : 1) * (0.8 + 0.2 * tanh((magnitude - 0.8) / 0.2));\n\t}\n\treturn shaped;\n}\nParam trig_bd(0);\nParam delay_bd(0, min=0, max=500);\nHistory bd_last_trigger(0), bd_wait(0), bd_waiting(0), bd_pending_velocity(0);\nParam bd_mute(0, min=0, max=1);\nParam bd_solo(0, min=0, max=1);\nHistory bd_gate(1);\nParam trig_sd(0);\nParam delay_sd(0, min=0, max=500);\nHistory sd_last_trigger(0), sd_wait(0), sd_waiting(0), sd_pending_velocity(0);\nParam sd_mute(0, min=0, max=1);\nParam sd_solo(0, min=0, max=1);\nHistory sd_gate(1);\nParam trig_rs(0);\nParam delay_rs(0, min=0, max=500);\nHistory rs_last_trigger(0), rs_wait(0), rs_waiting(0), rs_pending_velocity(0);\nParam rs_mute(0, min=0, max=1);\nParam rs_solo(0, min=0, max=1);\nHistory rs_gate(1);\nParam trig_cp(0);\nParam delay_cp(0, min=0, max=500);\nHistory cp_last_trigger(0), cp_wait(0), cp_waiting(0), cp_pending_velocity(0);\nParam cp_mute(0, min=0, max=1);\nParam cp_solo(0, min=0, max=1);\nHistory cp_gate(1);\nParam trig_ch(0);\nParam delay_ch(0, min=0, max=500);\nHistory ch_last_trigger(0), ch_wait(0), ch_waiting(0), ch_pending_velocity(0);\nParam ch_mute(0, min=0, max=1);\nParam ch_solo(0, min=0, max=1);\nHistory ch_gate(1);\nParam trig_oh(0);\nParam delay_oh(0, min=0, max=500);\nHistory oh_last_trigger(0), oh_wait(0), oh_waiting(0), oh_pending_velocity(0);\nParam oh_mute(0, min=0, max=1);\nParam oh_solo(0, min=0, max=1);\nHistory oh_gate(1);\nParam trig_rd(0);\nParam delay_rd(0, min=0, max=500);\nHistory rd_last_trigger(0), rd_wait(0), rd_waiting(0), rd_pending_velocity(0);\nParam rd_mute(0, min=0, max=1);\nParam rd_solo(0, min=0, max=1);\nHistory rd_gate(1);\n\nParam accent(0.7, min=0, max=1);         // how much quieter a normal hit is than an accent\nParam volume(0, min=-36, max=12);        // output, dB\nParam panic(0);                          // Stop: every new number fades the kit out in 20 ms\n\n// BD\nParam bd_tune(50, min=30, max=90);       // Hz the pitch settles to (unsourced range)\nParam bd_sweep(0.5, min=0, max=1);       // pitch envelope depth: starts up to 4x higher\nParam bd_decay(450, min=60, max=2000);   // ms to -40 dB\nParam bd_attack(0.5, min=0, max=1);      // the click: pulse + low-passed noise\nParam bd_soft(0, min=0, max=1);          // 0 = 909 punch, 1 = soft and round\nParam bd_bits(16, min=3, max=16);\nParam bd_level(0.8, min=0, max=1);\nHistory bd_phase(0), bd_pitch_envelope(0), bd_amp_envelope(0), bd_pulse_envelope(0), bd_click_envelope(0);\nHistory bd_velocity(1), bd_fade_in(1), bd_click_noise(0), bd_output_lowpass(0);\n\n// SD\nParam sd_tune(180, min=120, max=320);    // Hz of VCO 1; VCO 2 is x1.83\nParam sd_tone(160, min=40, max=500);     // ms: the main snappy noise's decay (Whittle: Tone = ENV4 decay)\nParam sd_snappy(0.6, min=0, max=1);      // the noise level\nParam sd_bits(16, min=3, max=16);\nParam sd_level(0.7, min=0, max=1);\nHistory sd_phase1(0), sd_phase2(0), sd_envelope1(0), sd_envelope2(0), sd_bend(0), sd_velocity(1);\nHistory sd_noise_hold(0), sd_noise_envelope4(0), sd_noise_envelope5(0), sd_noise_lowpass(0), sd_noise_highpass_lowpass(0);\n\n// RS\nParam rs_bits(16, min=3, max=16);\nParam rs_level(0.5, min=0, max=1);\nHistory rs_ring_a1(0), rs_ring_a2(0), rs_ring_b1(0), rs_ring_b2(0), rs_ring_c1(0), rs_ring_c2(0);\nHistory rs_envelope(0), rs_velocity(1), rs_highpass_lowpass(0);\n\n// CP\nParam cp_bits(16, min=3, max=16);\nParam cp_level(0.6, min=0, max=1);\nHistory cp_time(1000000000), cp_velocity(1), cp_band_highpass_lowpass(0), cp_band_lowpass(0);\n\n// CH and OH: one voice, as on the 909 (a closed hit cuts the open hat)\nParam hat_tune(1, min=0.43, max=1.7);    // the sample ROM's clock, x (Whittle's tune mod range)\nParam hat_bits(6, min=2, max=12);        // the ROM's bits: 6 on the 909\nParam ch_decay(60, min=10, max=300);     // ms to -40 dB\nParam oh_decay(500, min=80, max=2000);   // ms to -40 dB\nParam ch_level(0.5, min=0, max=1);\nParam oh_level(0.5, min=0, max=1);\nHistory hat_envelope(0), hat_open(0), hat_velocity(1), hat_clock(0), hat_held(0);\nHistory hat_osc1(0), hat_osc2(0), hat_osc3(0), hat_osc4(0), hat_osc5(0), hat_osc6(0);\nHistory hat_highpass1_lowpass(0), hat_highpass2_lowpass(0), hat_output_lowpass1(0), hat_output_lowpass2(0);\n\n// RD\nParam rd_tune(1, min=0.6, max=1.5);      // the ROM's clock, x: pitch and length together (no decay knob)\nParam rd_bits(6, min=2, max=12);\nParam rd_level(0.4, min=0, max=1);\nHistory rd_envelope(0), rd_velocity(1), rd_clock(0), rd_held(0);\nHistory rd_osc1(0), rd_osc2(0), rd_osc3(0), rd_osc4(0), rd_osc5(0), rd_osc6(0);\nHistory rd_highpass_lowpass(0), rd_output_lowpass1(0), rd_output_lowpass2(0);\n\n// Stop\nHistory last_panic(0), hush_left(0);\n\nif (trig_bd != bd_last_trigger) {\n\tbd_last_trigger = trig_bd;\n\tbd_pending_velocity = clamp(fract(trig_bd) * 2, 0.001, 1);\n\tbd_wait = mstosamps(delay_bd);\n\tbd_waiting = 1;\n}\nbd_fire = 0;\nif (bd_waiting > 0) {\n\tif (bd_wait < 1) {\n\t\tbd_fire = 1;\n\t\tbd_waiting = 0;\n\t} else {\n\t\tbd_wait = bd_wait - 1;\n\t}\n}\n\nif (trig_sd != sd_last_trigger) {\n\tsd_last_trigger = trig_sd;\n\tsd_pending_velocity = clamp(fract(trig_sd) * 2, 0.001, 1);\n\tsd_wait = mstosamps(delay_sd);\n\tsd_waiting = 1;\n}\nsd_fire = 0;\nif (sd_waiting > 0) {\n\tif (sd_wait < 1) {\n\t\tsd_fire = 1;\n\t\tsd_waiting = 0;\n\t} else {\n\t\tsd_wait = sd_wait - 1;\n\t}\n}\n\nif (trig_rs != rs_last_trigger) {\n\trs_last_trigger = trig_rs;\n\trs_pending_velocity = clamp(fract(trig_rs) * 2, 0.001, 1);\n\trs_wait = mstosamps(delay_rs);\n\trs_waiting = 1;\n}\nrs_fire = 0;\nif (rs_waiting > 0) {\n\tif (rs_wait < 1) {\n\t\trs_fire = 1;\n\t\trs_waiting = 0;\n\t} else {\n\t\trs_wait = rs_wait - 1;\n\t}\n}\n\nif (trig_cp != cp_last_trigger) {\n\tcp_last_trigger = trig_cp;\n\tcp_pending_velocity = clamp(fract(trig_cp) * 2, 0.001, 1);\n\tcp_wait = mstosamps(delay_cp);\n\tcp_waiting = 1;\n}\ncp_fire = 0;\nif (cp_waiting > 0) {\n\tif (cp_wait < 1) {\n\t\tcp_fire = 1;\n\t\tcp_waiting = 0;\n\t} else {\n\t\tcp_wait = cp_wait - 1;\n\t}\n}\n\nif (trig_ch != ch_last_trigger) {\n\tch_last_trigger = trig_ch;\n\tch_pending_velocity = clamp(fract(trig_ch) * 2, 0.001, 1);\n\tch_wait = mstosamps(delay_ch);\n\tch_waiting = 1;\n}\nch_fire = 0;\nif (ch_waiting > 0) {\n\tif (ch_wait < 1) {\n\t\tch_fire = 1;\n\t\tch_waiting = 0;\n\t} else {\n\t\tch_wait = ch_wait - 1;\n\t}\n}\n\nif (trig_oh != oh_last_trigger) {\n\toh_last_trigger = trig_oh;\n\toh_pending_velocity = clamp(fract(trig_oh) * 2, 0.001, 1);\n\toh_wait = mstosamps(delay_oh);\n\toh_waiting = 1;\n}\noh_fire = 0;\nif (oh_waiting > 0) {\n\tif (oh_wait < 1) {\n\t\toh_fire = 1;\n\t\toh_waiting = 0;\n\t} else {\n\t\toh_wait = oh_wait - 1;\n\t}\n}\n\nif (trig_rd != rd_last_trigger) {\n\trd_last_trigger = trig_rd;\n\trd_pending_velocity = clamp(fract(trig_rd) * 2, 0.001, 1);\n\trd_wait = mstosamps(delay_rd);\n\trd_waiting = 1;\n}\nrd_fire = 0;\nif (rd_waiting > 0) {\n\tif (rd_wait < 1) {\n\t\trd_fire = 1;\n\t\trd_waiting = 0;\n\t} else {\n\t\trd_wait = rd_wait - 1;\n\t}\n}\n\n// the mixer: mute and solo gates, smoothed over 5 ms\nany_solo = (bd_solo + sd_solo + rs_solo + cp_solo + ch_solo + oh_solo + rd_solo) > 0 ? 1 : 0;\ngate_coefficient = 1 - exp(-1000 / (5 * samplerate));\nbd_gate = bd_gate + gate_coefficient * ((1 - bd_mute) * (any_solo > 0 ? bd_solo : 1) - bd_gate);\nsd_gate = sd_gate + gate_coefficient * ((1 - sd_mute) * (any_solo > 0 ? sd_solo : 1) - sd_gate);\nrs_gate = rs_gate + gate_coefficient * ((1 - rs_mute) * (any_solo > 0 ? rs_solo : 1) - rs_gate);\ncp_gate = cp_gate + gate_coefficient * ((1 - cp_mute) * (any_solo > 0 ? cp_solo : 1) - cp_gate);\nch_gate = ch_gate + gate_coefficient * ((1 - ch_mute) * (any_solo > 0 ? ch_solo : 1) - ch_gate);\noh_gate = oh_gate + gate_coefficient * ((1 - oh_mute) * (any_solo > 0 ? oh_solo : 1) - oh_gate);\nrd_gate = rd_gate + gate_coefficient * ((1 - rd_mute) * (any_solo > 0 ? rd_solo : 1) - rd_gate);\n\nsr = samplerate;\n// the analog voices share one noise source, as on the 909 (snare and clap phase together)\nanalog_noise = noise();\n\n// ---- Stop: fade everything out in 20 ms, then silence the voices ----\nhush_samples = mstosamps(20);\nif (panic != last_panic) {\n\tlast_panic = panic;\n\thush_left = hush_samples;\n}\nhush_gain = 1;\nsilence_now = 0;\nif (hush_left > 0) {\n\thush_left = hush_left - 1;\n\thush_gain = hush_left / max(hush_samples, 1);\n\tif (hush_left < 1) {\n\t\tsilence_now = 1;\n\t}\n}\n\n// ================= BD: triangle VCO + diode clipper, pitch sweep, compressed-looking ENV-1, click =================\nif (bd_fire > 0) {\n\tbd_velocity = bd_pending_velocity;\n\tbd_phase = 0;                  // TRIG restarts the VCO (network-909: Q11 discharges C14)\n\tbd_pitch_envelope = 1;\n\tbd_amp_envelope = 1;\n\tbd_pulse_envelope = 1;\n\tbd_click_envelope = 1;\n\tbd_fade_in = 0;\n}\nbd_accented = bd_velocity > 0.95 ? 1 : 0;\nbd_sweep_now = bd_sweep * (1 - 0.75 * bd_soft);\nbd_frequency = bd_tune * (1 + 3 * bd_sweep_now * bd_pitch_envelope);\nbd_pitch_envelope = bd_pitch_envelope * decay_multiplier(30 + 90 * bd_soft, sr);       // (unsourced)\nbd_phase = wrap(bd_phase + bd_frequency / sr, 0, 1);\nbd_body = mix(diode_round(triangle_from_phase(bd_phase), 1.8), sin(twopi * bd_phase), bd_soft);\n// accent: more attack amplitude and a longer decay (SOS's BD diagram)\nbd_amp_envelope = bd_amp_envelope * decay_multiplier(bd_decay * (1 + 0.15 * bd_accented), sr);\nbd_amp_shape = 1 - (1 - bd_amp_envelope) * (1 - bd_amp_envelope);    // flat at first: \"looks compressed\"\nbd_fade_in = min(1, bd_fade_in + 1 / max(mstosamps(0.05 + 5 * bd_soft), 1));            // soft: no transient\nbd_pulse_envelope = bd_pulse_envelope * decay_multiplier(1.5, sr);                     // (unsourced)\nbd_click_envelope = bd_click_envelope * decay_multiplier(6, sr);                       // (unsourced)\nbd_click_noise = bd_click_noise + onepole_coefficient(2500, sr) * (analog_noise - bd_click_noise);\nbd_click = (bd_pulse_envelope + 2 * bd_click_noise * bd_click_envelope) * bd_attack * (1 - 0.85 * bd_soft);\nbd_raw = bd_body * bd_amp_shape * bd_fade_in + bd_click;\nbd_output_lowpass = bd_output_lowpass + onepole_coefficient(mix(9000, 350, bd_soft), sr) * (bd_raw - bd_output_lowpass);\nif (silence_now > 0) {\n\tbd_amp_envelope = 0;\n\tbd_pulse_envelope = 0;\n\tbd_click_envelope = 0;\n}\nbd_out = crush(bd_output_lowpass, bd_bits) * bd_level * bd_gate * accent_gain(bd_velocity, accent);\n\n// ================= SD: two triangle VCOs with a 20 ms pitch bend, noise through LPF -> ENV4 / HPF -> ENV5 =================\nif (sd_fire > 0) {\n\tsd_velocity = sd_pending_velocity;\n\tsd_phase1 = 0;                 // VCO 1 restarts so VCO 2 starts in phase (service notes)\n\tsd_phase2 = 0;\n\tsd_envelope1 = 1;\n\tsd_envelope2 = 1;\n\tsd_bend = 1;\n\tsd_noise_hold = mstosamps(24); // ENV4 holds about 24 ms before it decays (Whittle)\n\tsd_noise_envelope4 = 1;\n\tsd_noise_envelope5 = 1;\n}\nsd_accented = sd_velocity > 0.95 ? 1 : 0;\nsd_bend = sd_bend * decay_multiplier(20, sr);                     // the pitch bend lasts about 20 ms\nsd_frequency1 = sd_tune * (1 + 0.4 * sd_bend);                     // bend depth (unsourced)\nsd_phase1 = wrap(sd_phase1 + sd_frequency1 / sr, 0, 1);\nsd_phase2 = wrap(sd_phase2 + sd_frequency1 * 1.83 / sr, 0, 1);      // VCO 2 \"somewhat higher\" (ratio unsourced)\n// accent: the VCO envelopes start higher and last longer (Whittle)\nsd_envelope1 = sd_envelope1 * decay_multiplier(180 * (1 + 0.25 * sd_accented), sr);   // lower VCO longer (unsourced)\nsd_envelope2 = sd_envelope2 * decay_multiplier(90 * (1 + 0.25 * sd_accented), sr);\nsd_drum = diode_round(triangle_from_phase(sd_phase1), 1.6) * sd_envelope1 * 0.6\n\t+ diode_round(triangle_from_phase(sd_phase2), 1.6) * sd_envelope2 * 0.4;\nsd_noise_lowpass = sd_noise_lowpass + onepole_coefficient(7000, sr) * (analog_noise - sd_noise_lowpass);\nsd_noise_highpass_lowpass = sd_noise_highpass_lowpass + onepole_coefficient(1800, sr) * (sd_noise_lowpass - sd_noise_highpass_lowpass);\nsd_noise_highpass = sd_noise_lowpass - sd_noise_highpass_lowpass;\nif (sd_noise_hold > 0) {\n\tsd_noise_hold = sd_noise_hold - 1;\n} else {\n\tsd_noise_envelope4 = sd_noise_envelope4 * decay_multiplier(sd_tone, sr);\n}\nsd_noise_envelope5 = sd_noise_envelope5 * decay_multiplier(90, sr);           // (unsourced)\nsd_snappy_noise = (sd_noise_lowpass * sd_noise_envelope4 + sd_noise_highpass * sd_noise_envelope5) * sd_snappy;\nif (silence_now > 0) {\n\tsd_envelope1 = 0;\n\tsd_envelope2 = 0;\n\tsd_noise_envelope4 = 0;\n\tsd_noise_envelope5 = 0;\n\tsd_noise_hold = 0;\n}\nsd_out = crush(sd_drum + sd_snappy_noise, sd_bits) * sd_level * sd_gate * accent_gain(sd_velocity, accent);\n\n// ================= RS: three bridged-T rings at 500 / 220 / 1000 Hz, a diode clipper, a short VCA, a high-pass =================\nrs_kick = 0;\nif (rs_fire > 0) {\n\trs_velocity = rs_pending_velocity;\n\trs_kick = 1;\n\trs_envelope = 1;\n}\nrs_radius_a = resonator_radius(28, sr);\nrs_radius_b = resonator_radius(36, sr);\nrs_radius_c = resonator_radius(18, sr);                         // ring times (unsourced)\nrs_ring_a = 2 * rs_radius_a * cos(twopi * 500 / sr) * rs_ring_a1 - rs_radius_a * rs_radius_a * rs_ring_a2 + rs_kick * sin(twopi * 500 / sr);\nrs_ring_a2 = rs_ring_a1;\nrs_ring_a1 = rs_ring_a;\nrs_ring_b = 2 * rs_radius_b * cos(twopi * 220 / sr) * rs_ring_b1 - rs_radius_b * rs_radius_b * rs_ring_b2 + rs_kick * sin(twopi * 220 / sr);\nrs_ring_b2 = rs_ring_b1;\nrs_ring_b1 = rs_ring_b;\nrs_ring_c = 2 * rs_radius_c * cos(twopi * 1000 / sr) * rs_ring_c1 - rs_radius_c * rs_radius_c * rs_ring_c2 + rs_kick * sin(twopi * 1000 / sr);\nrs_ring_c2 = rs_ring_c1;\nrs_ring_c1 = rs_ring_c;\nrs_envelope = rs_envelope * decay_multiplier(40, sr);                       // the VCA's envelope (unsourced)\nrs_clipped = diode_round((rs_ring_a + rs_ring_b * 0.8 + rs_ring_c * 0.7) * 1.5, 2);\nrs_highpass_lowpass = rs_highpass_lowpass + onepole_coefficient(250, sr) * (rs_clipped - rs_highpass_lowpass);\nif (silence_now > 0) {\n\trs_envelope = 0;\n}\nrs_out = crush((rs_clipped - rs_highpass_lowpass) * rs_envelope, rs_bits) * rs_level * rs_gate * accent_gain(rs_velocity, accent);\n\n// ================= CP: noise -> band-pass -> four chained claps, plus the \"pseudo-reverb\" tail =================\nif (cp_fire > 0) {\n\tcp_velocity = cp_pending_velocity;\n\tcp_time = 0;\n}\ncp_time = cp_time + 1;\ncp_spacing = mstosamps(11);                                     // clap to clap (unsourced)\ncp_claps = 0;\nif (cp_time < 3 * cp_spacing) {\n\tcp_claps = pow(1 - fract(cp_time / cp_spacing), 3);         // each clap snaps, then falls (a sawtooth's shape)\n} else {\n\tcp_claps = exp(-(cp_time - 3 * cp_spacing) / mstosamps(20));  // the fourth rings a little longer\n}\ncp_tail = 0.4 * exp(-cp_time / mstosamps(150));                  // longer, softer, slower (tail time unsourced)\ncp_band_highpass_lowpass = cp_band_highpass_lowpass + onepole_coefficient(800, sr) * (analog_noise - cp_band_highpass_lowpass);\ncp_band_lowpass = cp_band_lowpass + onepole_coefficient(2400, sr) * ((analog_noise - cp_band_highpass_lowpass) - cp_band_lowpass);\nif (silence_now > 0) {\n\tcp_time = 1000000000;\n}\ncp_out = crush(cp_band_lowpass * (cp_claps + cp_tail) * 1.6, cp_bits) * cp_level * cp_gate * accent_gain(cp_velocity, accent);\n\n// ================= CH / OH: a 6-bit \"sample\" ROM at 30 kHz, then the VCA, then two low-passes =================\n// We have no samples: the \"ROM\" is metallic noise (six squares + noise, high-passed), held at the ROM's clock and\n// quantized to hat_bits, flat like the 909's compressed sample; the VCA puts the decay on after, so the grit\n// decays with the hat.\nhat_level_now = ch_level * ch_gate;\nif (ch_fire > 0) {\n\that_velocity = ch_pending_velocity;\n\that_envelope = 1;\n\that_open = 0;                  // closed cuts open: one voice\n}\nif (oh_fire > 0) {\n\that_velocity = oh_pending_velocity;\n\that_envelope = 1;\n\that_open = 1;\n}\nif (hat_open > 0) {\n\that_level_now = oh_level * oh_gate;\n}\nhat_osc1 = wrap(hat_osc1 + 2520 * hat_tune / sr, 0, 1);           // the six frequencies (unsourced)\nhat_osc2 = wrap(hat_osc2 + 3390 * hat_tune / sr, 0, 1);\nhat_osc3 = wrap(hat_osc3 + 4150 * hat_tune / sr, 0, 1);\nhat_osc4 = wrap(hat_osc4 + 5380 * hat_tune / sr, 0, 1);\nhat_osc5 = wrap(hat_osc5 + 6840 * hat_tune / sr, 0, 1);\nhat_osc6 = wrap(hat_osc6 + 8260 * hat_tune / sr, 0, 1);\nhat_metal = (square_from_phase(hat_osc1) + square_from_phase(hat_osc2) + square_from_phase(hat_osc3)\n\t+ square_from_phase(hat_osc4) + square_from_phase(hat_osc5) + square_from_phase(hat_osc6)) / 6 * 0.6 + noise() * 0.5;\nhat_highpass1_lowpass = hat_highpass1_lowpass + onepole_coefficient(5000, sr) * (hat_metal - hat_highpass1_lowpass);\nhat_highpass1 = hat_metal - hat_highpass1_lowpass;\nhat_highpass2_lowpass = hat_highpass2_lowpass + onepole_coefficient(5000, sr) * (hat_highpass1 - hat_highpass2_lowpass);\nhat_rom_signal = clamp((hat_highpass1 - hat_highpass2_lowpass) * 1.6, -1, 1);\nhat_clock = hat_clock + 30000 * hat_tune / sr;                    // 60 kHz / 2 (service notes) = 30 kHz (SOS)\nif (hat_clock >= 1) {\n\that_clock = hat_clock - floor(hat_clock);\n\that_held = crush(hat_rom_signal, hat_bits);\n}\n// CH decays through about 1/10 of OH's resistance (network-909); here each has its own Decay\nhat_envelope = hat_envelope * decay_multiplier(hat_open > 0 ? oh_decay : ch_decay, sr);\nhat_output_lowpass1 = hat_output_lowpass1 + onepole_coefficient(11000, sr) * (hat_held * hat_envelope - hat_output_lowpass1);\nhat_output_lowpass2 = hat_output_lowpass2 + onepole_coefficient(11000, sr) * (hat_output_lowpass1 - hat_output_lowpass2);\nif (silence_now > 0) {\n\that_envelope = 0;\n}\nhat_out = hat_output_lowpass2 * 2.5 * hat_level_now * accent_gain(hat_velocity, accent);   // voice balance (unsourced)\n\n// ================= RD: the same ROM idea; the decay follows the clock (Tone changes pitch and length) =================\nif (rd_fire > 0) {\n\trd_velocity = rd_pending_velocity;\n\trd_envelope = 1;\n}\nrd_osc1 = wrap(rd_osc1 + 1630 * rd_tune / sr, 0, 1);             // (unsourced)\nrd_osc2 = wrap(rd_osc2 + 2210 * rd_tune / sr, 0, 1);\nrd_osc3 = wrap(rd_osc3 + 2870 * rd_tune / sr, 0, 1);\nrd_osc4 = wrap(rd_osc4 + 3530 * rd_tune / sr, 0, 1);\nrd_osc5 = wrap(rd_osc5 + 4790 * rd_tune / sr, 0, 1);\nrd_osc6 = wrap(rd_osc6 + 6120 * rd_tune / sr, 0, 1);\nrd_metal = (square_from_phase(rd_osc1) + square_from_phase(rd_osc2) + square_from_phase(rd_osc3)\n\t+ square_from_phase(rd_osc4) + square_from_phase(rd_osc5) + square_from_phase(rd_osc6)) / 6 * 0.8 + noise() * 0.25;\nrd_highpass_lowpass = rd_highpass_lowpass + onepole_coefficient(2500, sr) * (rd_metal - rd_highpass_lowpass);\nrd_rom_signal = clamp((rd_metal - rd_highpass_lowpass) * 1.4, -1, 1);\nrd_clock = rd_clock + 30000 * rd_tune / sr;\nif (rd_clock >= 1) {\n\trd_clock = rd_clock - floor(rd_clock);\n\trd_held = crush(rd_rom_signal, rd_bits);\n}\nrd_envelope = rd_envelope * decay_multiplier(1600 / rd_tune, sr);      // ROM length at the nominal clock (unsourced)\nrd_output_lowpass1 = rd_output_lowpass1 + onepole_coefficient(10000, sr) * (rd_held * rd_envelope - rd_output_lowpass1);\nrd_output_lowpass2 = rd_output_lowpass2 + onepole_coefficient(10000, sr) * (rd_output_lowpass1 - rd_output_lowpass2);\nif (silence_now > 0) {\n\trd_envelope = 0;\n}\nrd_out = rd_output_lowpass2 * rd_level * rd_gate * accent_gain(rd_velocity, accent);\n\n// ================= out: the mono kit on both sides, through the soft clip =================\n// x0.4 (-8 dB): headroom, so the Init kit peaks about 3 dB under full scale (tools/render_drums.py measures it)\nkit = (bd_out + sd_out + rs_out + cp_out + hat_out + rd_out) * 0.4 * hush_gain;\nkit_out = soft_clip(kit * dbtoa(volume));\nout1 = kit_out;\nout2 = kit_out;\n",
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
						772.0,
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
						772.0,
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
						108.0,
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
						108.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Page",
							"parameter_shortname": "Page",
							"parameter_type": 2,
							"parameter_enum": [
								"pattern",
								"kit"
							],
							"parameter_mmax": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Page",
							"parameter_info": "Shows the pattern or the kit page. Controls on the hidden page keep working."
						}
					},
					"annotation_name": "Page",
					"annotation": "Shows the pattern or the kit page. Controls on the hidden page keep working.",
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
						1744.0,
						643.0,
						160.0,
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
						244.0,
						3.0,
						160.0,
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
								"soft grit"
							],
							"parameter_mmax": 6,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Preset",
							"parameter_info": "Kit sounds: sets every voice, level and Accent (not the pattern, the mixer's mutes and solos, or the functions). When Live reopens a set, your saved tweaks win."
						}
					},
					"annotation_name": "Preset",
					"annotation": "Kit sounds: sets every voice, level and Accent (not the pattern, the mixer's mutes and solos, or the functions). When Live reopens a set, your saved tweaks win."
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
						636.0,
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
						712.0,
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
					"numoutlets": 2,
					"patching_rect": [
						940.0,
						210.0,
						60.0,
						22.0
					],
					"text": "t i i",
					"outlettype": [
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
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 15,
					"patching_rect": [
						1100.0,
						120.0,
						600.0,
						22.0
					],
					"text": "route steps_bd_a steps_bd_b steps_sd_a steps_sd_b steps_rs_a steps_rs_b steps_cp_a steps_cp_b steps_ch_a steps_ch_b steps_oh_a steps_oh_b steps_rd_a steps_rd_b",
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
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-68",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1028.0,
						282.0,
						137.0
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
						282.0,
						137.0
					],
					"border": 0,
					"annotation_name": "Pattern",
					"annotation": "The pattern: a row per voice, 16 steps. Click a step: rest, hit, accent (bright, with a bar on top); shift-click: a ghost (dim). The lit names are the rows Voice picks. Blue outline: the step playing. While Seed or a setting is being turned, this is the live result.",
					"varname": "view_grid"
				}
			},
			{
				"box": {
					"id": "obj-69",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1814.0,
						1028.0,
						446.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-drums-view.js",
					"jsarguments": [
						"status"
					],
					"presentation": 1,
					"presentation_rect": [
						314.0,
						28.0,
						446.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Status",
					"annotation": "Line 1: Voice, Function and where Seed is in the function's variants. Line 2: the function's settings. Line 3: what is shown (the base, or live), or a warning in blue (open hh on a row other than oh, a row grids has nothing for). Line 4: where you are in the history (Undo steps back) and what made the pattern.",
					"varname": "view_status"
				}
			},
			{
				"box": {
					"id": "obj-70",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1814.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "voice",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						314.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Voice",
							"parameter_shortname": "Voice",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								7
							],
							"parameter_enum": [
								"bd",
								"sd",
								"rs",
								"cp",
								"ch",
								"oh",
								"rd",
								"all"
							],
							"parameter_mmax": 7,
							"parameter_annotation_name": "Voice",
							"parameter_info": "The row the function changes: bd, sd, rs, cp, ch, oh, rd, or all (the last). On all, generators make the whole kit and modifiers change every row. Moving Voice commits what is shown as one history step."
						}
					},
					"annotation_name": "Voice",
					"annotation": "The row the function changes: bd, sd, rs, cp, ch, oh, rd, or all (the last). On all, generators make the whole kit and modifiers change every row. Moving Voice commits what is shown as one history step."
				}
			},
			{
				"box": {
					"id": "obj-71",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1040.0,
						100.0,
						22.0
					],
					"text": "prepend voice",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-72",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1870.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "function",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						370.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Function",
							"parameter_shortname": "Function",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_enum": [
								"canned",
								"grids",
								"euclid",
								"random",
								"shift",
								"reverse",
								"thin",
								"ghosts",
								"fill",
								"open hh",
								"accent"
							],
							"parameter_mmax": 10,
							"parameter_annotation_name": "Function",
							"parameter_info": "The function Seed and the settings walk, applied live. Generators make new rows: canned, grids, euclid, random. Modifiers change the rows there are: shift, reverse, thin, ghosts, fill, open hh, accent. Only its own settings show; each remembers its own. Moving Function commits what is shown as one history step."
						}
					},
					"annotation_name": "Function",
					"annotation": "The function Seed and the settings walk, applied live. Generators make new rows: canned, grids, euclid, random. Modifiers change the rows there are: shift, reverse, thin, ghosts, fill, open hh, accent. Only its own settings show; each remembers its own. Moving Function commits what is shown as one history step."
				}
			},
			{
				"box": {
					"id": "obj-73",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1044.0,
						100.0,
						22.0
					],
					"text": "prepend function",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-74",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1046.0,
						100.0,
						22.0
					],
					"text": "prepend group function",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-75",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1926.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "seed",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						426.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Seed",
							"parameter_shortname": "Seed",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Seed",
							"parameter_info": "Walks every combination of the function's settings (its variants), the finest setting changing fastest, neighbours one step apart; turning it moves the settings, turning a setting moves it. Shown at once: the first turn after a commit takes the pattern as it is as the base; Undo brings the base back. 0-100% of the way through this function's variants (the status line shows which)."
						}
					},
					"annotation_name": "Seed",
					"annotation": "Walks every combination of the function's settings (its variants), the finest setting changing fastest, neighbours one step apart; turning it moves the settings, turning a setting moves it. Shown at once: the first turn after a commit takes the pattern as it is as the base; Undo brings the base back. 0-100% of the way through this function's variants (the status line shows which)."
				}
			},
			{
				"box": {
					"id": "obj-76",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1050.0,
						100.0,
						22.0
					],
					"text": "prepend seed",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-77",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "canned_kit",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Canned Kit",
							"parameter_shortname": "Kit",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_mmin": 1.0,
							"parameter_mmax": 15.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Canned Kit",
							"parameter_info": "Canned: Rows from a sourced kit (patterns.md P1-P11, as their sources give them). Kit: Which kit: 1 P1 basic channel, 2 P8 4 ingredients, 3 P1 + rim 16ths, 4 P3 minimal house, 5 P7 house 124, 6 P4 deep house, 7 P2 motor city, 8 P2 rim answer, 9 P7 techno 130, 10 P9 mills 137, 11 P5 dark rumble, 12 P6 rolling, 13 P11 tresillo, 14 P11 bossa, 15 P11 son clave."
						}
					},
					"annotation_name": "Canned Kit",
					"annotation": "Canned: Rows from a sourced kit (patterns.md P1-P11, as their sources give them). Kit: Which kit: 1 P1 basic channel, 2 P8 4 ingredients, 3 P1 + rim 16ths, 4 P3 minimal house, 5 P7 house 124, 6 P4 deep house, 7 P2 motor city, 8 P2 rim answer, 9 P7 techno 130, 10 P9 mills 137, 11 P5 dark rumble, 12 P6 rolling, 13 P11 tresillo, 14 P11 bossa, 15 P11 son clave."
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
					"text": "prepend param 0 0",
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
						2050.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "canned_from",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						550.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Canned From",
							"parameter_shortname": "From",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 7.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Canned From",
							"parameter_info": "Canned: Rows from a sourced kit (patterns.md P1-P11, as their sources give them). From: 0: each row gets its own voice's row from the kit. Else the row (or every row, on all) gets this voice's row: 1 bd, 2 sd, 3 rs, 4 cp, 5 ch, 6 oh, 7 rd."
						}
					},
					"annotation_name": "Canned From",
					"annotation": "Canned: Rows from a sourced kit (patterns.md P1-P11, as their sources give them). From: 0: each row gets its own voice's row from the kit. Else the row (or every row, on all) gets this voice's row: 1 bd, 2 sd, 3 rs, 4 cp, 5 ch, 6 oh, 7 rd."
				}
			},
			{
				"box": {
					"id": "obj-80",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1058.0,
						100.0,
						22.0
					],
					"text": "prepend param 0 1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-81",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "grids_x",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Grids X",
							"parameter_shortname": "X",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								128.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 255.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Grids X",
							"parameter_info": "Grids: Rows from Mutable Instruments Grids' pattern map (patterns.md P12, B1): BD, SD and HH from its three channels; CP takes the SD channel's accents, OH the HH channel's offbeat 8ths; RS and RD have no channel. X: The map's X, 0-255, as on Grids."
						}
					},
					"annotation_name": "Grids X",
					"annotation": "Grids: Rows from Mutable Instruments Grids' pattern map (patterns.md P12, B1): BD, SD and HH from its three channels; CP takes the SD channel's accents, OH the HH channel's offbeat 8ths; RS and RD have no channel. X: The map's X, 0-255, as on Grids.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-82",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1062.0,
						100.0,
						22.0
					],
					"text": "prepend param 1 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-83",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2050.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "grids_y",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						550.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Grids Y",
							"parameter_shortname": "Y",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								128.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 255.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Grids Y",
							"parameter_info": "Grids: Rows from Mutable Instruments Grids' pattern map (patterns.md P12, B1): BD, SD and HH from its three channels; CP takes the SD channel's accents, OH the HH channel's offbeat 8ths; RS and RD have no channel. Y: The map's Y, 0-255, as on Grids."
						}
					},
					"annotation_name": "Grids Y",
					"annotation": "Grids: Rows from Mutable Instruments Grids' pattern map (patterns.md P12, B1): BD, SD and HH from its three channels; CP takes the SD channel's accents, OH the HH channel's offbeat 8ths; RS and RD have no channel. Y: The map's Y, 0-255, as on Grids.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-84",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1066.0,
						100.0,
						22.0
					],
					"text": "prepend param 1 1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-85",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2106.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "grids_density",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						606.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Grids Density",
							"parameter_shortname": "Density",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Grids Density",
							"parameter_info": "Grids: Rows from Mutable Instruments Grids' pattern map (patterns.md P12, B1): BD, SD and HH from its three channels; CP takes the SD channel's accents, OH the HH channel's offbeat 8ths; RS and RD have no channel. Density: Grids' density: a step plays when its level is above 255 - density. Above 192 it is an accent."
						}
					},
					"annotation_name": "Grids Density",
					"annotation": "Grids: Rows from Mutable Instruments Grids' pattern map (patterns.md P12, B1): BD, SD and HH from its three channels; CP takes the SD channel's accents, OH the HH channel's offbeat 8ths; RS and RD have no channel. Density: Grids' density: a step plays when its level is above 255 - density. Above 192 it is an accent.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-86",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1070.0,
						100.0,
						22.0
					],
					"text": "prepend param 1 2",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-87",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "euclid_hits",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Euclid Hits",
							"parameter_shortname": "Hits",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								4.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 16.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Euclid Hits",
							"parameter_info": "Euclid: A Euclidean rhythm (Toussaint, patterns.md P11): hits spread as evenly as possible over a cycle of steps, rotated, repeated across the bar (P10's 3- and 5-step loops are E(1,3) and E(1,5)). Hits: Onsets in the cycle (no more than Steps)."
						}
					},
					"annotation_name": "Euclid Hits",
					"annotation": "Euclid: A Euclidean rhythm (Toussaint, patterns.md P11): hits spread as evenly as possible over a cycle of steps, rotated, repeated across the bar (P10's 3- and 5-step loops are E(1,3) and E(1,5)). Hits: Onsets in the cycle (no more than Steps).",
					"hidden": 1
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
					"text": "prepend param 2 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-89",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2050.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "euclid_rotation",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						550.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Euclid Rotation",
							"parameter_shortname": "Rotation",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 15.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Euclid Rotation",
							"parameter_info": "Euclid: A Euclidean rhythm (Toussaint, patterns.md P11): hits spread as evenly as possible over a cycle of steps, rotated, repeated across the bar (P10's 3- and 5-step loops are E(1,3) and E(1,5)). Rotation: Steps later the cycle starts, like Ableton's Euclidean rotation (B3)."
						}
					},
					"annotation_name": "Euclid Rotation",
					"annotation": "Euclid: A Euclidean rhythm (Toussaint, patterns.md P11): hits spread as evenly as possible over a cycle of steps, rotated, repeated across the bar (P10's 3- and 5-step loops are E(1,3) and E(1,5)). Rotation: Steps later the cycle starts, like Ableton's Euclidean rotation (B3).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-90",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1078.0,
						100.0,
						22.0
					],
					"text": "prepend param 2 1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-91",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2106.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "euclid_steps",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						606.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Euclid Steps",
							"parameter_shortname": "Steps",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_mmin": 1.0,
							"parameter_mmax": 16.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Euclid Steps",
							"parameter_info": "Euclid: A Euclidean rhythm (Toussaint, patterns.md P11): hits spread as evenly as possible over a cycle of steps, rotated, repeated across the bar (P10's 3- and 5-step loops are E(1,3) and E(1,5)). Steps: The cycle's length; it repeats across the 16 steps."
						}
					},
					"annotation_name": "Euclid Steps",
					"annotation": "Euclid: A Euclidean rhythm (Toussaint, patterns.md P11): hits spread as evenly as possible over a cycle of steps, rotated, repeated across the bar (P10's 3- and 5-step loops are E(1,3) and E(1,5)). Steps: The cycle's length; it repeats across the 16 steps.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-92",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1082.0,
						100.0,
						22.0
					],
					"text": "prepend param 2 2",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-93",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "random_density",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Random Density",
							"parameter_shortname": "Density",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								30.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Random Density",
							"parameter_info": "Random: Random hits: each step plays with Density's chance, and a hit is an accent with Accent's chance (Ableton's Seed density, Elektron's trig probability: patterns.md B2, B3). Density: The chance that a step is a hit."
						}
					},
					"annotation_name": "Random Density",
					"annotation": "Random: Random hits: each step plays with Density's chance, and a hit is an accent with Accent's chance (Ableton's Seed density, Elektron's trig probability: patterns.md B2, B3). Density: The chance that a step is a hit.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-94",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1086.0,
						100.0,
						22.0
					],
					"text": "prepend param 3 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-95",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2050.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "random_accent",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						550.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Random Accent",
							"parameter_shortname": "Accent",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								10.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Random Accent",
							"parameter_info": "Random: Random hits: each step plays with Density's chance, and a hit is an accent with Accent's chance (Ableton's Seed density, Elektron's trig probability: patterns.md B2, B3). Accent: The chance that a hit is an accent."
						}
					},
					"annotation_name": "Random Accent",
					"annotation": "Random: Random hits: each step plays with Density's chance, and a hit is an accent with Accent's chance (Ableton's Seed density, Elektron's trig probability: patterns.md B2, B3). Accent: The chance that a hit is an accent.",
					"hidden": 1
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
					"text": "prepend param 3 1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-97",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2106.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "random_seed",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						606.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Random Seed",
							"parameter_shortname": "Seed",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 999.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Random Seed",
							"parameter_info": "Random: Random hits: each step plays with Density's chance, and a hit is an accent with Accent's chance (Ableton's Seed density, Elektron's trig probability: patterns.md B2, B3). Seed: The same seed makes the same rows."
						}
					},
					"annotation_name": "Random Seed",
					"annotation": "Random: Random hits: each step plays with Density's chance, and a hit is an accent with Accent's chance (Ableton's Seed density, Elektron's trig probability: patterns.md B2, B3). Seed: The same seed makes the same rows.",
					"hidden": 1
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
					"text": "prepend param 3 2",
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
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "shift_steps",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Shift Steps",
							"parameter_shortname": "Steps",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": -15.0,
							"parameter_mmax": 15.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Shift Steps",
							"parameter_info": "Shift: Moves the rows by steps, later for positive, earlier for negative, wrapping around the bar (Ableton's Rhythm Shift, patterns.md B3). Steps: Steps to move: + later, - earlier."
						}
					},
					"annotation_name": "Shift Steps",
					"annotation": "Shift: Moves the rows by steps, later for positive, earlier for negative, wrapping around the bar (Ableton's Rhythm Shift, patterns.md B3). Steps: Steps to move: + later, - earlier.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-100",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1098.0,
						100.0,
						22.0
					],
					"text": "prepend param 4 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-101",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "reverse_span",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Reverse Span",
							"parameter_shortname": "Span",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_mmin": 1.0,
							"parameter_mmax": 16.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Reverse Span",
							"parameter_info": "Reverse: Plays each span of steps backwards from its first step: step 1 of the span stays, 2 swaps with the last, 3 with the one before ... (unsourced). Span 16 = the bar, so four on the floor and offbeats stay. Span: How many steps each reversed piece is, from the downbeat: 16 = the bar, 8 = each half bar, 4 = each beat. 1 and 2 change nothing."
						}
					},
					"annotation_name": "Reverse Span",
					"annotation": "Reverse: Plays each span of steps backwards from its first step: step 1 of the span stays, 2 swaps with the last, 3 with the one before ... (unsourced). Span 16 = the bar, so four on the floor and offbeats stay. Span: How many steps each reversed piece is, from the downbeat: 16 = the bar, 8 = each half bar, 4 = each beat. 1 and 2 change nothing.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-102",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1102.0,
						100.0,
						22.0
					],
					"text": "prepend param 5 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-103",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "thin_amount",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Thin Amount",
							"parameter_shortname": "Amount",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Thin Amount",
							"parameter_info": "Thin: Removes the weakest hits, as Grids' density keeps the strongest steps (patterns.md B1): ghosts first, then hits, then accents; within a grade the weakest place in the bar first. Amount: The share of each row's hits removed."
						}
					},
					"annotation_name": "Thin Amount",
					"annotation": "Thin: Removes the weakest hits, as Grids' density keeps the strongest steps (patterns.md B1): ghosts first, then hits, then accents; within a grade the weakest place in the bar first. Amount: The share of each row's hits removed.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-104",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1106.0,
						100.0,
						22.0
					],
					"text": "prepend param 6 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-105",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "ghosts_amount",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Ghosts Amount",
							"parameter_shortname": "Amount",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Ghosts Amount",
							"parameter_info": "Ghosts: Adds ghost notes (quiet hits, patterns.md B5) on rests: first just before a hit (as P6's ghost kicks before beats 2 and 4), then on the weakest places in the bar. Amount: The share of each row's rests that become ghosts."
						}
					},
					"annotation_name": "Ghosts Amount",
					"annotation": "Ghosts: Adds ghost notes (quiet hits, patterns.md B5) on rests: first just before a hit (as P6's ghost kicks before beats 2 and 4), then on the weakest places in the bar. Amount: The share of each row's rests that become ghosts.",
					"hidden": 1
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
					"text": "prepend param 7 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-107",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "fill_steps",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Fill Steps",
							"parameter_shortname": "Steps",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								4.0
							],
							"parameter_mmin": 1.0,
							"parameter_mmax": 16.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Fill Steps",
							"parameter_info": "Fill: A fill at the end of the bar (Elektron's FILL, patterns.md B2): hits on the rests of the last steps, spread evenly (Toussaint, P11). Steps: How many of the bar's last steps: 4 = the last beat, 8 = the last half bar."
						}
					},
					"annotation_name": "Fill Steps",
					"annotation": "Fill: A fill at the end of the bar (Elektron's FILL, patterns.md B2): hits on the rests of the last steps, spread evenly (Toussaint, P11). Steps: How many of the bar's last steps: 4 = the last beat, 8 = the last half bar.",
					"hidden": 1
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
					"text": "prepend param 8 0",
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
						2050.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "fill_density",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						550.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Fill Density",
							"parameter_shortname": "Density",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Fill Density",
							"parameter_info": "Fill: A fill at the end of the bar (Elektron's FILL, patterns.md B2): hits on the rests of the last steps, spread evenly (Toussaint, P11). Density: The share of those steps that get a hit."
						}
					},
					"annotation_name": "Fill Density",
					"annotation": "Fill: A fill at the end of the bar (Elektron's FILL, patterns.md B2): hits on the rests of the last steps, spread evenly (Toussaint, P11). Density: The share of those steps that get a hit.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-110",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1118.0,
						100.0,
						22.0
					],
					"text": "prepend param 8 1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-111",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "open_hh_amount",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Open hh Amount",
							"parameter_shortname": "Amount",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Open hh Amount",
							"parameter_info": "Open hh: Turns closed hats into open hats (the CH row's hits move to the OH row; patterns.md B5 swaps them for variation): offbeat 8ths first, where the sourced kits put the open hat (P1, P2), then the weakest places. On one row it reads CH and writes only OH, whichever row Voice picks; on all, the hits move. Amount: The share of the closed hat's hits that open."
						}
					},
					"annotation_name": "Open hh Amount",
					"annotation": "Open hh: Turns closed hats into open hats (the CH row's hits move to the OH row; patterns.md B5 swaps them for variation): offbeat 8ths first, where the sourced kits put the open hat (P1, P2), then the weakest places. On one row it reads CH and writes only OH, whichever row Voice picks; on all, the hits move. Amount: The share of the closed hat's hits that open.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-112",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1122.0,
						100.0,
						22.0
					],
					"text": "prepend param 9 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-113",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1994.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "accent_every",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						494.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Accent Every",
							"parameter_shortname": "Every",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								4.0
							],
							"parameter_mmin": 1.0,
							"parameter_mmax": 16.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Accent Every",
							"parameter_info": "Accent: Accents every Nth hit of each row, the others become plain hits; ghosts stay (Ableton's Rhythm Accent Frequency and Offset, patterns.md B3). Every: Hits from one accent to the next (an accent counts as a hit; 1 = every hit)."
						}
					},
					"annotation_name": "Accent Every",
					"annotation": "Accent: Accents every Nth hit of each row, the others become plain hits; ghosts stay (Ableton's Rhythm Accent Frequency and Offset, patterns.md B3). Every: Hits from one accent to the next (an accent counts as a hit; 1 = every hit).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-114",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1126.0,
						100.0,
						22.0
					],
					"text": "prepend param 10 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-115",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2050.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "accent_offset",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						550.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Accent Offset",
							"parameter_shortname": "Offset",
							"parameter_type": 1,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 15.0,
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Accent Offset",
							"parameter_info": "Accent: Accents every Nth hit of each row, the others become plain hits; ghosts stay (Ableton's Rhythm Accent Frequency and Offset, patterns.md B3). Offset: Hits before the first accent."
						}
					},
					"annotation_name": "Accent Offset",
					"annotation": "Accent: Accents every Nth hit of each row, the others become plain hits; ghosts stay (Ableton's Rhythm Accent Frequency and Offset, patterns.md B3). Offset: Hits before the first accent.",
					"hidden": 1
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
					"text": "prepend param 10 1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-117",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 22,
					"patching_rect": [
						1100.0,
						160.0,
						900.0,
						22.0
					],
					"text": "route seed canned_kit canned_from grids_x grids_y grids_density euclid_hits euclid_rotation euclid_steps random_density random_accent random_seed shift_steps reverse_span thin_amount ghosts_amount fill_steps fill_density open_hh_amount accent_every accent_offset",
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
					"id": "obj-118",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1814.0,
						758.0,
						48.0,
						15.0
					],
					"text": "undo",
					"outlettype": [
						"",
						""
					],
					"varname": "undo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						314.0,
						98.0,
						48.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Undo",
							"parameter_shortname": "Undo",
							"parameter_type": 2,
							"parameter_annotation_name": "Undo",
							"parameter_info": "Drops what Seed and the settings show that isn't committed (back to the base, the settings back where they were). Else steps back one commit (a Voice or Function move, or a hand edit). The last 100 patterns are kept; the history isn't saved with the set (the pattern playing is).",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Undo",
					"annotation": "Drops what Seed and the settings show that isn't committed (back to the base, the settings back where they were). Else steps back one commit (a Voice or Function move, or a hand edit). The last 100 patterns are kept; the history isn't saved with the set (the pattern playing is).",
					"texton": "undo",
					"mode": 0
				}
			},
			{
				"box": {
					"id": "obj-119",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						300.0,
						70.0,
						22.0
					],
					"text": "undo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-120",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						2188.0,
						738.0,
						72.0,
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
						688.0,
						98.0,
						72.0,
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
					"text": "prepend swing",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-122",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1512.0,
						698.0,
						324.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "kit_voice",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						12.0,
						98.0,
						324.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Kit Voice",
							"parameter_shortname": "Voice",
							"parameter_type": 2,
							"parameter_enum": [
								"bd",
								"sd",
								"rs",
								"cp",
								"hats",
								"rd"
							],
							"parameter_mmax": 5,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Kit Voice",
							"parameter_info": "Which voice's sound controls show: bd, sd, rs, cp, the hats (ch and oh) or rd."
						}
					},
					"annotation_name": "Kit Voice",
					"annotation": "Which voice's sound controls show: bd, sd, rs, cp, the hats (ch and oh) or rd.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1,
					"hidden": 1
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
					"text": "prepend group kit_voice",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-124",
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
					"id": "obj-125",
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
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_mmin": 30.0,
							"parameter_mmax": 90.0,
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
					"text": "prepend bd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-127",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1152.0,
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
					"id": "obj-128",
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
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
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
					"id": "obj-129",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1156.0,
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
					"id": "obj-130",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1158.0,
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
					"id": "obj-131",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1160.0,
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
					"text": "prepend bd_sweep",
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
							"parameter_initial_enable": 1,
							"parameter_initial": [
								450.0
							],
							"parameter_mmin": 60.0,
							"parameter_mmax": 2000.0,
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
					"id": "obj-134",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1166.0,
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
					"text": "prepend bd_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-136",
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
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
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
					"id": "obj-137",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1172.0,
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
					"id": "obj-138",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1174.0,
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
					"id": "obj-139",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1176.0,
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
					"text": "prepend bd_attack",
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
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
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
					"text": "prepend bd_soft",
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
					"text": "prepend bd_soft",
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
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
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
					"id": "obj-147",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1192.0,
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
					"text": "prepend bd_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-149",
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
						"sd"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						324.0,
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
					"id": "obj-150",
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
					"varname": "sd_tune",
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
							"parameter_longname": "SD Tune",
							"parameter_shortname": "Tune",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								180.0
							],
							"parameter_mmin": 120.0,
							"parameter_mmax": 320.0,
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
					"id": "obj-151",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1200.0,
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
					"text": "prepend sd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-153",
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
					"varname": "sd_tone",
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
							"parameter_longname": "SD Tone",
							"parameter_shortname": "Tone",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								160.0
							],
							"parameter_mmin": 40.0,
							"parameter_mmax": 500.0,
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
					"id": "obj-154",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1206.0,
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
					"id": "obj-155",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1208.0,
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
					"id": "obj-156",
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
					"varname": "sd_snappy",
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
							"parameter_longname": "SD Snappy",
							"parameter_shortname": "Snappy",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								60.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
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
					"id": "obj-157",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1212.0,
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
					"id": "obj-158",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1214.0,
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
					"id": "obj-159",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1216.0,
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
					"text": "prepend sd_snappy",
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
						1680.0,
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
						180.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
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
					"id": "obj-162",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1222.0,
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
					"text": "prepend sd_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-164",
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
						"rs"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						324.0,
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
					"id": "obj-165",
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
					"varname": "rs_bits",
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
							"parameter_longname": "RS Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RS Bits",
							"parameter_info": "Bit reduction on the rim shot, 16 (clean) down to 3. Level only on the 909."
						}
					},
					"annotation_name": "RS Bits",
					"annotation": "Bit reduction on the rim shot, 16 (clean) down to 3. Level only on the 909.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-166",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1230.0,
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
					"text": "prepend rs_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-168",
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
						"cp"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						324.0,
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
					"id": "obj-169",
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
							"parameter_initial_enable": 1,
							"parameter_initial": [
								16.0
							],
							"parameter_mmin": 3.0,
							"parameter_mmax": 16.0,
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "CP Bits",
							"parameter_info": "Bit reduction on the clap, 16 (clean) down to 3. Attack's dub techno clap uses 6. Level only on the 909."
						}
					},
					"annotation_name": "CP Bits",
					"annotation": "Bit reduction on the clap, 16 (clean) down to 3. Attack's dub techno clap uses 6. Level only on the 909.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-170",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1238.0,
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
					"text": "prepend cp_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-172",
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
						"hats"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
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
					"id": "obj-173",
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
					"varname": "hat_tune",
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
							"parameter_longname": "Hat Tune",
							"parameter_shortname": "Tune",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_mmin": 0.43,
							"parameter_mmax": 1.7,
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
					"id": "obj-174",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1246.0,
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
					"text": "prepend hat_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-176",
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
					"varname": "ch_decay",
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
							"parameter_longname": "CH Decay",
							"parameter_shortname": "CH Decay",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								60.0
							],
							"parameter_mmin": 10.0,
							"parameter_mmax": 300.0,
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
					"id": "obj-177",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1252.0,
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
					"id": "obj-178",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1254.0,
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
					"id": "obj-179",
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
					"varname": "oh_decay",
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
							"parameter_longname": "OH Decay",
							"parameter_shortname": "OH Decay",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								500.0
							],
							"parameter_mmin": 80.0,
							"parameter_mmax": 2000.0,
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
					"text": "prepend oh_decay",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-181",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1260.0,
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
					"id": "obj-182",
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
					"varname": "hat_bits",
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
							"parameter_longname": "Hat Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								6.0
							],
							"parameter_mmin": 2.0,
							"parameter_mmax": 12.0,
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
					"text": "prepend hat_bits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-184",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1266.0,
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
					"id": "obj-185",
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
						"rd"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						324.0,
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
					"id": "obj-186",
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
					"varname": "rd_tune",
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
							"parameter_longname": "RD Tune",
							"parameter_shortname": "Tune",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_mmin": 0.6,
							"parameter_mmax": 1.5,
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
					"id": "obj-187",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1272.0,
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
					"text": "prepend rd_tune",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-189",
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
					"varname": "rd_bits",
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
							"parameter_longname": "RD Bits",
							"parameter_shortname": "Bits",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								6.0
							],
							"parameter_mmin": 2.0,
							"parameter_mmax": 12.0,
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
					"id": "obj-190",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1278.0,
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
					"id": "obj-191",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1280.0,
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
					"id": "obj-192",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1860.0,
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
						360.0,
						28.0,
						332.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Mix",
					"annotation": "Each voice's level as a bar, flashing as it plays; dimmed when it doesn't sound (muted, or another voice is soloed).",
					"varname": "view_mix",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-193",
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
					"varname": "bd_level",
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
							"parameter_longname": "BD Level",
							"parameter_shortname": "BD",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								80.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "BD Level",
							"parameter_info": "Level of the bd in the mix. Accents still play louder (Accent)."
						}
					},
					"annotation_name": "BD Level",
					"annotation": "Level of the bd in the mix. Accents still play louder (Accent).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-194",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1286.0,
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
					"text": "prepend bd_level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-196",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1290.0,
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
					"id": "obj-197",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1292.0,
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
					"id": "obj-198",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1860.0,
						758.0,
						20.0,
						15.0
					],
					"text": "m",
					"outlettype": [
						"",
						""
					],
					"varname": "bd_mute",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						360.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Mute",
							"parameter_shortname": "M",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "BD Mute",
							"parameter_info": "Mutes the bd: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "BD Mute",
					"annotation": "Mutes the bd: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
					"texton": "m",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-199",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1296.0,
						100.0,
						22.0
					],
					"text": "prepend bd_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-200",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1298.0,
						100.0,
						22.0
					],
					"text": "prepend bd_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-201",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1884.0,
						758.0,
						20.0,
						15.0
					],
					"text": "s",
					"outlettype": [
						"",
						""
					],
					"varname": "bd_solo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						384.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "BD Solo",
							"parameter_shortname": "S",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "BD Solo",
							"parameter_info": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "BD Solo",
					"annotation": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
					"texton": "s",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-202",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1302.0,
						100.0,
						22.0
					],
					"text": "prepend bd_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-203",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1304.0,
						100.0,
						22.0
					],
					"text": "prepend bd_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-204",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1908.0,
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
						408.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Level",
							"parameter_shortname": "SD",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								70.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "SD Level",
							"parameter_info": "Level of the sd in the mix. Accents still play louder (Accent)."
						}
					},
					"annotation_name": "SD Level",
					"annotation": "Level of the sd in the mix. Accents still play louder (Accent).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-205",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1308.0,
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
					"id": "obj-206",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1310.0,
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
					"id": "obj-207",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1312.0,
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
					"id": "obj-208",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1314.0,
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
					"id": "obj-209",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1908.0,
						758.0,
						20.0,
						15.0
					],
					"text": "m",
					"outlettype": [
						"",
						""
					],
					"varname": "sd_mute",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						408.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Mute",
							"parameter_shortname": "M",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "SD Mute",
							"parameter_info": "Mutes the sd: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "SD Mute",
					"annotation": "Mutes the sd: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
					"texton": "m",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-210",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1318.0,
						100.0,
						22.0
					],
					"text": "prepend sd_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-211",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1320.0,
						100.0,
						22.0
					],
					"text": "prepend sd_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-212",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1932.0,
						758.0,
						20.0,
						15.0
					],
					"text": "s",
					"outlettype": [
						"",
						""
					],
					"varname": "sd_solo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						432.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "SD Solo",
							"parameter_shortname": "S",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "SD Solo",
							"parameter_info": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "SD Solo",
					"annotation": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
					"texton": "s",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-213",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1324.0,
						100.0,
						22.0
					],
					"text": "prepend sd_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-214",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1326.0,
						100.0,
						22.0
					],
					"text": "prepend sd_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-215",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1956.0,
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
						456.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RS Level",
							"parameter_shortname": "RS",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RS Level",
							"parameter_info": "Level of the rs in the mix. Accents still play louder (Accent)."
						}
					},
					"annotation_name": "RS Level",
					"annotation": "Level of the rs in the mix. Accents still play louder (Accent).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-216",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1330.0,
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
					"id": "obj-217",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1332.0,
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
					"id": "obj-218",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1334.0,
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
					"id": "obj-219",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1336.0,
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
					"id": "obj-220",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1956.0,
						758.0,
						20.0,
						15.0
					],
					"text": "m",
					"outlettype": [
						"",
						""
					],
					"varname": "rs_mute",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						456.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RS Mute",
							"parameter_shortname": "M",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "RS Mute",
							"parameter_info": "Mutes the rs: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "RS Mute",
					"annotation": "Mutes the rs: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
					"texton": "m",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-221",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1340.0,
						100.0,
						22.0
					],
					"text": "prepend rs_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-222",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1342.0,
						100.0,
						22.0
					],
					"text": "prepend rs_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-223",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1980.0,
						758.0,
						20.0,
						15.0
					],
					"text": "s",
					"outlettype": [
						"",
						""
					],
					"varname": "rs_solo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						480.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RS Solo",
							"parameter_shortname": "S",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "RS Solo",
							"parameter_info": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "RS Solo",
					"annotation": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
					"texton": "s",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-224",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1346.0,
						100.0,
						22.0
					],
					"text": "prepend rs_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-225",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1348.0,
						100.0,
						22.0
					],
					"text": "prepend rs_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-226",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2004.0,
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
						504.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CP Level",
							"parameter_shortname": "CP",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								60.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "CP Level",
							"parameter_info": "Level of the cp in the mix. Accents still play louder (Accent)."
						}
					},
					"annotation_name": "CP Level",
					"annotation": "Level of the cp in the mix. Accents still play louder (Accent).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-227",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1352.0,
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
					"id": "obj-228",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1354.0,
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
					"id": "obj-229",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1356.0,
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
					"id": "obj-230",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1358.0,
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
					"id": "obj-231",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2004.0,
						758.0,
						20.0,
						15.0
					],
					"text": "m",
					"outlettype": [
						"",
						""
					],
					"varname": "cp_mute",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						504.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CP Mute",
							"parameter_shortname": "M",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "CP Mute",
							"parameter_info": "Mutes the cp: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "CP Mute",
					"annotation": "Mutes the cp: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
					"texton": "m",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-232",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1362.0,
						100.0,
						22.0
					],
					"text": "prepend cp_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-233",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1364.0,
						100.0,
						22.0
					],
					"text": "prepend cp_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-234",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2028.0,
						758.0,
						20.0,
						15.0
					],
					"text": "s",
					"outlettype": [
						"",
						""
					],
					"varname": "cp_solo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						528.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CP Solo",
							"parameter_shortname": "S",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "CP Solo",
							"parameter_info": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "CP Solo",
					"annotation": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
					"texton": "s",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-235",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1368.0,
						100.0,
						22.0
					],
					"text": "prepend cp_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-236",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1370.0,
						100.0,
						22.0
					],
					"text": "prepend cp_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-237",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2052.0,
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
						552.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH Level",
							"parameter_shortname": "CH",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "CH Level",
							"parameter_info": "Level of the ch in the mix. Accents still play louder (Accent)."
						}
					},
					"annotation_name": "CH Level",
					"annotation": "Level of the ch in the mix. Accents still play louder (Accent).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-238",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1374.0,
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
					"id": "obj-239",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1376.0,
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
					"id": "obj-240",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1378.0,
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
					"id": "obj-241",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1380.0,
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
					"id": "obj-242",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2052.0,
						758.0,
						20.0,
						15.0
					],
					"text": "m",
					"outlettype": [
						"",
						""
					],
					"varname": "ch_mute",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						552.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH Mute",
							"parameter_shortname": "M",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "CH Mute",
							"parameter_info": "Mutes the ch: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "CH Mute",
					"annotation": "Mutes the ch: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
					"texton": "m",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-243",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1384.0,
						100.0,
						22.0
					],
					"text": "prepend ch_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-244",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1386.0,
						100.0,
						22.0
					],
					"text": "prepend ch_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-245",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2076.0,
						758.0,
						20.0,
						15.0
					],
					"text": "s",
					"outlettype": [
						"",
						""
					],
					"varname": "ch_solo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						576.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH Solo",
							"parameter_shortname": "S",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "CH Solo",
							"parameter_info": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "CH Solo",
					"annotation": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
					"texton": "s",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-246",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1390.0,
						100.0,
						22.0
					],
					"text": "prepend ch_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-247",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1392.0,
						100.0,
						22.0
					],
					"text": "prepend ch_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-248",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2100.0,
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
						600.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "OH Level",
							"parameter_shortname": "OH",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "OH Level",
							"parameter_info": "Level of the oh in the mix. Accents still play louder (Accent)."
						}
					},
					"annotation_name": "OH Level",
					"annotation": "Level of the oh in the mix. Accents still play louder (Accent).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-249",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1396.0,
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
					"id": "obj-250",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1398.0,
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
					"id": "obj-251",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1400.0,
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
					"id": "obj-252",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1402.0,
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
					"id": "obj-253",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2100.0,
						758.0,
						20.0,
						15.0
					],
					"text": "m",
					"outlettype": [
						"",
						""
					],
					"varname": "oh_mute",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						600.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "OH Mute",
							"parameter_shortname": "M",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "OH Mute",
							"parameter_info": "Mutes the oh: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "OH Mute",
					"annotation": "Mutes the oh: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
					"texton": "m",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-254",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1406.0,
						100.0,
						22.0
					],
					"text": "prepend oh_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-255",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1408.0,
						100.0,
						22.0
					],
					"text": "prepend oh_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-256",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2124.0,
						758.0,
						20.0,
						15.0
					],
					"text": "s",
					"outlettype": [
						"",
						""
					],
					"varname": "oh_solo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						624.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "OH Solo",
							"parameter_shortname": "S",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "OH Solo",
							"parameter_info": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "OH Solo",
					"annotation": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
					"texton": "s",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-257",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1412.0,
						100.0,
						22.0
					],
					"text": "prepend oh_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-258",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1414.0,
						100.0,
						22.0
					],
					"text": "prepend oh_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-259",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2148.0,
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
						648.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RD Level",
							"parameter_shortname": "RD",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								40.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "RD Level",
							"parameter_info": "Level of the rd in the mix. Accents still play louder (Accent)."
						}
					},
					"annotation_name": "RD Level",
					"annotation": "Level of the rd in the mix. Accents still play louder (Accent).",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-260",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1418.0,
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
					"id": "obj-261",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1420.0,
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
					"id": "obj-262",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1422.0,
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
					"id": "obj-263",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1424.0,
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
					"id": "obj-264",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2148.0,
						758.0,
						20.0,
						15.0
					],
					"text": "m",
					"outlettype": [
						"",
						""
					],
					"varname": "rd_mute",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						648.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RD Mute",
							"parameter_shortname": "M",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "RD Mute",
							"parameter_info": "Mutes the rd: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "RD Mute",
					"annotation": "Mutes the rd: its pattern keeps running, it doesn't sound (MIDI notes neither). Saved with the set, not in presets.",
					"texton": "m",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-265",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1428.0,
						100.0,
						22.0
					],
					"text": "prepend rd_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-266",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1430.0,
						100.0,
						22.0
					],
					"text": "prepend rd_mute",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-267",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2172.0,
						758.0,
						20.0,
						15.0
					],
					"text": "s",
					"outlettype": [
						"",
						""
					],
					"varname": "rd_solo",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						672.0,
						98.0,
						20.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RD Solo",
							"parameter_shortname": "S",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "RD Solo",
							"parameter_info": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "RD Solo",
					"annotation": "Solo: while any voice is soloed, only soloed voices sound (a mute still wins). Saved with the set, not in presets.",
					"texton": "s",
					"mode": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-268",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1434.0,
						100.0,
						22.0
					],
					"text": "prepend rd_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-269",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1436.0,
						100.0,
						22.0
					],
					"text": "prepend rd_solo",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-270",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2216.0,
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
						716.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Accent",
							"parameter_shortname": "Accent",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								70.0
							],
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Accent",
							"parameter_info": "How much quieter a normal hit (and a ghost) is than an accent, like the 909's Total Accent. 0 = all the same. Default 70%."
						}
					},
					"annotation_name": "Accent",
					"annotation": "How much quieter a normal hit (and a ghost) is than an accent, like the 909's Total Accent. 0 = all the same. Default 70%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-271",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1440.0,
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
					"id": "obj-272",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1442.0,
						100.0,
						22.0
					],
					"text": "prepend accent",
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
						1
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
						"obj-3",
						4
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-67",
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
						"obj-3",
						1
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
						"obj-3",
						2
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
						"obj-70",
						0
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
						"obj-3",
						1
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
						"obj-73",
						0
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
						"obj-3",
						1
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
						"obj-7",
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
						"obj-76",
						0
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-82",
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
						"obj-3",
						1
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
						"obj-84",
						0
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
						"obj-3",
						1
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
						"obj-86",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-86",
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
						"obj-90",
						0
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
						"obj-3",
						1
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
						"obj-93",
						0
					],
					"destination": [
						"obj-94",
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-104",
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-114",
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
						"obj-3",
						1
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
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						5
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
						"obj-75",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-117",
						1
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
						"obj-117",
						2
					],
					"destination": [
						"obj-79",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-117",
						3
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
						"obj-117",
						4
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
						"obj-117",
						5
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
						"obj-117",
						6
					],
					"destination": [
						"obj-87",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-117",
						7
					],
					"destination": [
						"obj-89",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-117",
						8
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
						"obj-117",
						9
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
						"obj-117",
						10
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
						"obj-117",
						11
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
						"obj-117",
						12
					],
					"destination": [
						"obj-99",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-117",
						13
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
						"obj-117",
						14
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
						"obj-117",
						15
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
						"obj-117",
						16
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
						"obj-117",
						17
					],
					"destination": [
						"obj-109",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-117",
						18
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
						"obj-117",
						19
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
						"obj-117",
						20
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
						"obj-118",
						0
					],
					"destination": [
						"obj-119",
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-7",
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
						"obj-125",
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
						"obj-124",
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
						"obj-129",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-129",
						0
					],
					"destination": [
						"obj-130",
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
						"obj-4",
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
						"obj-124",
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
						"obj-124",
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
						"obj-138",
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
						"obj-4",
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
						"obj-124",
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
						"obj-124",
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
						"obj-124",
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
						"obj-151",
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
						"obj-4",
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
						"obj-149",
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
						"obj-154",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-154",
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
						"obj-153",
						0
					],
					"destination": [
						"obj-155",
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
						"obj-149",
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
						"obj-158",
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
						"obj-4",
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
						"obj-149",
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
						"obj-149",
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
						"obj-166",
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
						"obj-4",
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
						"obj-164",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-169",
						0
					],
					"destination": [
						"obj-170",
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
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-169",
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
						"obj-168",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-173",
						0
					],
					"destination": [
						"obj-174",
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
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-173",
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
						"obj-172",
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
						"obj-177",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-177",
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
						"obj-176",
						0
					],
					"destination": [
						"obj-178",
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
						"obj-172",
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
						"obj-4",
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
						"obj-181",
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
						"obj-172",
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
						"obj-4",
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
						"obj-184",
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
						"obj-172",
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
						"obj-187",
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
						"obj-4",
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
						"obj-185",
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
						"obj-190",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-190",
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
						"obj-189",
						0
					],
					"destination": [
						"obj-191",
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
						"obj-185",
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
						"obj-194",
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
						"obj-193",
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
						"obj-197",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-197",
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
						"obj-198",
						0
					],
					"destination": [
						"obj-199",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-199",
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
						"obj-198",
						0
					],
					"destination": [
						"obj-200",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-200",
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
						"obj-201",
						0
					],
					"destination": [
						"obj-202",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-202",
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
						"obj-201",
						0
					],
					"destination": [
						"obj-203",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-203",
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
						"obj-204",
						0
					],
					"destination": [
						"obj-205",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-205",
						0
					],
					"destination": [
						"obj-206",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-206",
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
						"obj-204",
						0
					],
					"destination": [
						"obj-207",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-207",
						0
					],
					"destination": [
						"obj-208",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-208",
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
						"obj-209",
						0
					],
					"destination": [
						"obj-210",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-210",
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
						"obj-209",
						0
					],
					"destination": [
						"obj-211",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-211",
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
						"obj-212",
						0
					],
					"destination": [
						"obj-213",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-213",
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
						"obj-212",
						0
					],
					"destination": [
						"obj-214",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-214",
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
						"obj-215",
						0
					],
					"destination": [
						"obj-216",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-216",
						0
					],
					"destination": [
						"obj-217",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-217",
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
						"obj-215",
						0
					],
					"destination": [
						"obj-218",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-218",
						0
					],
					"destination": [
						"obj-219",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-219",
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
						"obj-220",
						0
					],
					"destination": [
						"obj-221",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-221",
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
						"obj-220",
						0
					],
					"destination": [
						"obj-222",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-222",
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
						"obj-223",
						0
					],
					"destination": [
						"obj-224",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-224",
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
						"obj-223",
						0
					],
					"destination": [
						"obj-225",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-225",
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
						"obj-226",
						0
					],
					"destination": [
						"obj-227",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-227",
						0
					],
					"destination": [
						"obj-228",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-228",
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
						"obj-226",
						0
					],
					"destination": [
						"obj-229",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-229",
						0
					],
					"destination": [
						"obj-230",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-230",
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
						"obj-231",
						0
					],
					"destination": [
						"obj-232",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-232",
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
						"obj-231",
						0
					],
					"destination": [
						"obj-233",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-233",
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
						"obj-234",
						0
					],
					"destination": [
						"obj-235",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-235",
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
						"obj-234",
						0
					],
					"destination": [
						"obj-236",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-236",
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
						"obj-237",
						0
					],
					"destination": [
						"obj-238",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-238",
						0
					],
					"destination": [
						"obj-239",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-239",
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
						"obj-237",
						0
					],
					"destination": [
						"obj-240",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-240",
						0
					],
					"destination": [
						"obj-241",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-241",
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
						"obj-242",
						0
					],
					"destination": [
						"obj-243",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-243",
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
						"obj-242",
						0
					],
					"destination": [
						"obj-244",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-244",
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
						"obj-245",
						0
					],
					"destination": [
						"obj-246",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-246",
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
						"obj-245",
						0
					],
					"destination": [
						"obj-247",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-247",
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
						"obj-248",
						0
					],
					"destination": [
						"obj-249",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-249",
						0
					],
					"destination": [
						"obj-250",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-250",
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
						"obj-248",
						0
					],
					"destination": [
						"obj-251",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-251",
						0
					],
					"destination": [
						"obj-252",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-252",
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
						"obj-253",
						0
					],
					"destination": [
						"obj-254",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-254",
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
						"obj-253",
						0
					],
					"destination": [
						"obj-255",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-255",
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
						"obj-256",
						0
					],
					"destination": [
						"obj-257",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-257",
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
						"obj-256",
						0
					],
					"destination": [
						"obj-258",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-258",
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
						"obj-259",
						0
					],
					"destination": [
						"obj-260",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-260",
						0
					],
					"destination": [
						"obj-261",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-261",
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
						"obj-259",
						0
					],
					"destination": [
						"obj-262",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-262",
						0
					],
					"destination": [
						"obj-263",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-263",
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
						"obj-264",
						0
					],
					"destination": [
						"obj-265",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-265",
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
						"obj-264",
						0
					],
					"destination": [
						"obj-266",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-266",
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
						"obj-267",
						0
					],
					"destination": [
						"obj-268",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-268",
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
						"obj-267",
						0
					],
					"destination": [
						"obj-269",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-269",
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
						"obj-270",
						0
					],
					"destination": [
						"obj-271",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-271",
						0
					],
					"destination": [
						"obj-272",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-272",
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
						"obj-3",
						3
					],
					"destination": [
						"obj-124",
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
						"obj-149",
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
						"obj-164",
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
						"obj-168",
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
						"obj-172",
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
						"obj-185",
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
						"obj-192",
						0
					]
				}
			}
		]
	}
}