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
					"text": "js 2sl-stab.js",
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
					"numinlets": 7,
					"numoutlets": 2,
					"patching_rect": [
						30.0,
						150.0,
						90.0,
						22.0
					],
					"text": "midiformat",
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-5",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 6,
					"patching_rect": [
						30.0,
						190.0,
						190.0,
						22.0
					],
					"text": "mc.noteallocator~ @voices 16 @steal 1",
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
					"id": "obj-6",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						30.0,
						215.0,
						60.0,
						22.0
					],
					"text": "t b l l",
					"outlettype": [
						"bang",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-7",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						30.0,
						240.0,
						80.0,
						22.0
					],
					"text": "unpack 0 0",
					"outlettype": [
						"int",
						"int"
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
						120.0,
						240.0,
						80.0,
						22.0
					],
					"text": "unpack 0 0",
					"outlettype": [
						"int",
						"int"
					]
				}
			},
			{
				"box": {
					"id": "obj-9",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						30.0,
						270.0,
						40.0,
						22.0
					],
					"text": "mtof",
					"outlettype": [
						"float"
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
						120.0,
						270.0,
						50.0,
						22.0
					],
					"text": "/ 127.",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-11",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						200.0,
						270.0,
						30.0,
						22.0
					],
					"text": "t 0",
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "obj-12",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						30.0,
						300.0,
						70.0,
						22.0
					],
					"text": "mc.target",
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-13",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						120.0,
						300.0,
						70.0,
						22.0
					],
					"text": "mc.target",
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-14",
					"maxclass": "newobj",
					"numinlets": 3,
					"numoutlets": 4,
					"patching_rect": [
						260.0,
						240.0,
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
					"id": "obj-15",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						260.0,
						270.0,
						70.0,
						22.0
					],
					"text": "mc.target",
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-16",
					"maxclass": "newobj",
					"numinlets": 4,
					"numoutlets": 1,
					"patching_rect": [
						30.0,
						350.0,
						160.0,
						22.0
					],
					"text": "mc.gen~ @chans 16",
					"outlettype": [
						"multichannelsignal"
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
									"code": "// one-pole smoothing coefficient for a time constant in ms (63% of the way there in that time)\nsmoothing_coefficient(time_constant_ms, sample_rate) {\n\treturn 1 - exp(-1000 / (max(time_constant_ms, 0.001) * sample_rate));\n}\n\n// One voice. in1: frequency (Hz). in2: gate = velocity 0..1, 0 = release. in3: the LFO (-1..1, shared).\n// in4: the note-on count: a new number on every note-on (the patch counts them), so a note-on always starts the\n// envelope, even when it changes no other value (a voice stolen for its own pitch at the same velocity).\n// Two oscillators, a sub and noise into a mixer, like the Juno / Jupiter / Prophet voices of the time.\n// (gen requires functions before everything else, declarations included.)\n// polyBLEP: removes the aliasing from a saw's jump\nblep(t, dt) {\n\tif (t < dt) {\n\t\tx = t / dt;\n\t\treturn x + x - x * x - 1;\n\t} else if (t > 1 - dt) {\n\t\tx = (t - 1) / dt;\n\t\treturn x * x + x + x + 1;\n\t}\n\treturn 0;\n}\n\nParam wave1(2, min=0, max=2);           // DCO 1: 0 saw, 1 pulse, 2 saw + pulse\nParam oct1(0, min=-1, max=1);           // 16' 8' 4'\nParam pw(0.7, min=0.5, max=0.95);       // pulse width (both DCOs)\nParam wave2(0, min=0, max=2);           // DCO 2: 0 saw, 1 pulse, 2 triangle\nParam oct2(0, min=-1, max=1);\nParam semi(0, min=-12, max=12);         // DCO 2 interval: 7 = a fifth up\nParam fine(10, min=0, max=50);          // DCO 2 detune, cents\nParam lvl1(0.8, min=0, max=1);          // mixer\nParam lvl2(0.8, min=0, max=1);\nParam sublvl(0, min=0, max=1);          // the sub: DCO 1 divided down, as on the SH-101\nParam submode(0, min=0, max=2);         // 0 square -1 oct, 1 square -2 oct, 2 25% pulse -2 oct\nParam noiseamt(0.08, min=0, max=1);\nParam pwmamt(0, min=0, max=1);          // LFO -> pulse width\nParam lfofilt(0, min=0, max=1);         // LFO -> cutoff, up to +-3 octaves\nParam vibamt(0, min=0, max=1);          // LFO -> pitch, up to +-50 cents\nParam cutoff(700, min=40, max=12000);   // Hz\nParam reso(0.3, min=0, max=1);\nParam envamt(0.5, min=0, max=1);        // envelope -> cutoff, up to +6 octaves\nParam keytrack(0.5, min=0, max=1);\nParam velfilt(0.5, min=0, max=1);       // velocity -> envelope amount\nParam atk(2, min=0.5, max=4000);        // ms\nParam dec(260, min=5, max=6000);        // ms to -40 dB\nParam sus(0, min=0, max=1);\nParam rel(240, min=5, max=6000);        // ms to -40 dB\nParam level(0.22, min=0, max=1);\nParam tonemac(0, min=-1, max=1);        // Play page Tone: cutoff and envelope up or down\nParam lenmac(0, min=-1, max=1);         // Play page Length: decay and release x0.25..x4\nParam panic(0);                         // Stop: every new number ramps the voice to silence\n\nHistory env(0), stage(0), lastgate(0), velo(0), last_note_on_count(0), lastpanic(0), fadeleft(0), fadestep(0);\nHistory velo_smoothed(0);   // velo, glided: a stolen voice's new velocity mustn't jump the gain (a click)\nHistory ph1(0), ph2(0), dco1_cycle_count(0), s1(0), s2(0), s3(0), s4(0);\n\nlfo = in3;\nnote = max(in1, 1);                    // the played pitch (vibrato is applied on top)\nfreq = note * pow(2, vibamt * lfo * 0.5 / 12);\ngatein = in2;\nnote_on_count = in4;\nsr = samplerate;\n\n// A note-on is a new count with the gate up: start the envelope. The gate falling is the note-off. Values alone\n// can't be the note-on: messages within one vector reach gen~ as their last value, so a voice stolen for the same\n// pitch and velocity (note-off, note-on: gate v, 0, v) would see nothing change.\nif (note_on_count != last_note_on_count && gatein > 0) {\n\tstage = 1;\n\tvelo = gatein;\n} else if (gatein <= 0 && lastgate > 0) {\n\tstage = 3;\n}\nlastgate = gatein;\nlast_note_on_count = note_on_count;\n\n// Stop: ramp to exactly 0 over 20 ms, whatever the release. A key pressed during the ramp starts when it ends.\nif (panic != lastpanic) {\n\tlastpanic = panic;\n\tfadeleft = max(mstosamps(20), 1);\n\tfadestep = env / fadeleft;\n}\nif (fadeleft > 0) {\n\tfadeleft = fadeleft - 1;\n\tstage = 0;\n\tenv = fadeleft > 0 ? max(env - fadestep, 0) : 0;\n\tlastgate = 0;\n\tlast_note_on_count = -1;           // the counts start at 1: a key held through the ramp starts when it ends\n}\n\n// the velocity glides to a new value over ~2 ms (time constant 0.5 ms: 98% there in 2 ms)\nvelo_smoothed = velo_smoothed + (velo - velo_smoothed) * smoothing_coefficient(0.5, sr);\n\n// analog-style ADSR: the attack aims past 1, decay and release are exponential\nstretch = pow(4, lenmac);\nka = 1 - exp(-1.47 / max(atk * 0.001 * sr, 1));\nkd = 1 - exp(-4.6 / max(dec * stretch * 0.001 * sr, 1));\nkr = 1 - exp(-4.6 / max(rel * stretch * 0.001 * sr, 1));\nif (stage == 1) {\n\tenv = env + (1.3 - env) * ka;\n\tif (env >= 1) {\n\t\tenv = 1;\n\t\tstage = 2;\n\t}\n} else if (stage == 2) {\n\tenv = env + (sus - env) * kd;\n} else if (stage == 3) {\n\tenv = env + (0 - env) * kr;\n\tif (env < 0.0005) {\n\t\tenv = 0;\n\t\tstage = 0;\n\t}\n}\n\nwidth = clamp(pw + pwmamt * 0.35 * lfo, 0.05, 0.95);\n\n// DCO 1\nf1 = freq * pow(2, oct1);\ndt1 = f1 / sr;\ndco1_phase_unwrapped = ph1 + dt1;\nif (dco1_phase_unwrapped >= 1) {       // DCO 1 completed a cycle: clock the sub's divider (0..3)\n\tdco1_cycle_count = wrap(dco1_cycle_count + 1, 0, 4);\n}\nph1 = wrap(dco1_phase_unwrapped, 0, 1);\nsaw1 = 2 * ph1 - 1 - blep(ph1, dt1);\np1b = wrap(ph1 + width, 0, 1);\npulse1 = saw1 - (2 * p1b - 1 - blep(p1b, dt1));\no1 = wave1 < 0.5 ? saw1 : (wave1 < 1.5 ? pulse1 : (saw1 + pulse1) * 0.6);\n\n// DCO 2\nf2 = freq * pow(2, oct2 + semi / 12 + fine / 1200);\ndt2 = f2 / sr;\nph2 = wrap(ph2 + dt2, 0, 1);\nsaw2 = 2 * ph2 - 1 - blep(ph2, dt2);\np2b = wrap(ph2 + width, 0, 1);\npulse2 = saw2 - (2 * p2b - 1 - blep(p2b, dt2));\ntri2 = 2 * abs(2 * ph2 - 1) - 1;\no2 = wave2 < 0.5 ? saw2 : (wave2 < 1.5 ? pulse2 : tri2);\n\n// sub: DCO 1 divided by 2 or 4 (the SH-101's flip-flops), so it stays locked to DCO 1 and follows its\n// footage. Its phase is DCO 1's phase plus the cycles counted so far. Square -1 oct, square -2 oct, or a\n// 25% pulse -2 oct (DC removed, so switching doesn't shift the level). Edges band-limited with blep.\nsub_phase_1oct = (wrap(dco1_cycle_count, 0, 2) + ph1) * 0.5;\nsub_dt_1oct = dt1 * 0.5;\nsub_phase_2oct = (dco1_cycle_count + ph1) * 0.25;\nsub_dt_2oct = dt1 * 0.25;\nsub_square_1oct = (sub_phase_1oct < 0.5 ? 1 : -1) + blep(sub_phase_1oct, sub_dt_1oct)\n\t- blep(wrap(sub_phase_1oct + 0.5, 0, 1), sub_dt_1oct);\nsub_square_2oct = (sub_phase_2oct < 0.5 ? 1 : -1) + blep(sub_phase_2oct, sub_dt_2oct)\n\t- blep(wrap(sub_phase_2oct + 0.5, 0, 1), sub_dt_2oct);\nsub_pulse_2oct = (sub_phase_2oct < 0.25 ? 1 : -1) + 0.5 + blep(sub_phase_2oct, sub_dt_2oct)\n\t- blep(wrap(sub_phase_2oct + 0.75, 0, 1), sub_dt_2oct);\nsubosc = submode < 0.5 ? sub_square_1oct : (submode < 1.5 ? sub_square_2oct : sub_pulse_2oct);\n\nosc = (o1 * lvl1 + o2 * lvl2 + subosc * sublvl) * 0.5 + noise() * noiseamt * 0.4;\n\n// 4-pole ladder low-pass with saturated feedback\nvel_env = clamp(envamt + 0.25 * tonemac, 0, 1) * (1 - velfilt + velfilt * velo_smoothed);\nfc = cutoff * pow(2, 2.5 * tonemac) * pow(2, keytrack * log2(note / 261.63)) * pow(2, 6 * vel_env * env)\n\t* pow(2, 3 * lfofilt * lfo);\nfc = clamp(fc, 20, sr * 0.45);\ng = 1 - exp(-twopi * fc / sr);\nk = reso * 3.8;\nx0 = tanh(osc - k * s4);\ns1 = s1 + g * (x0 - s1);\ns2 = s2 + g * (s1 - s2);\ns3 = s3 + g * (s2 - s3);\ns4 = s4 + g * (s3 - s4);\ny = s4 * (1 + k * 0.4);\n\nout1 = y * env * (0.35 + 0.65 * velo_smoothed) * level;\n",
									"fontname": "<Monospaced>",
									"fontsize": 12.0,
									"numinlets": 4,
									"numoutlets": 1,
									"outlettype": [
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
									"id": "in1",
									"maxclass": "newobj",
									"text": "in 1",
									"numinlets": 0,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										20.0,
										20.0,
										40.0,
										22.0
									]
								}
							},
							{
								"box": {
									"id": "in2",
									"maxclass": "newobj",
									"text": "in 2",
									"numinlets": 0,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										100.0,
										20.0,
										40.0,
										22.0
									]
								}
							},
							{
								"box": {
									"id": "in3",
									"maxclass": "newobj",
									"text": "in 3",
									"numinlets": 0,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										180.0,
										20.0,
										40.0,
										22.0
									]
								}
							},
							{
								"box": {
									"id": "in4",
									"maxclass": "newobj",
									"text": "in 4",
									"numinlets": 0,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										260.0,
										20.0,
										40.0,
										22.0
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
							}
						],
						"lines": [
							{
								"patchline": {
									"source": [
										"in1",
										0
									],
									"destination": [
										"cb",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"in2",
										0
									],
									"destination": [
										"cb",
										1
									]
								}
							},
							{
								"patchline": {
									"source": [
										"in3",
										0
									],
									"destination": [
										"cb",
										2
									]
								}
							},
							{
								"patchline": {
									"source": [
										"in4",
										0
									],
									"destination": [
										"cb",
										3
									]
								}
							},
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
							}
						]
					}
				}
			},
			{
				"box": {
					"id": "obj-17",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						220.0,
						300.0,
						80.0,
						22.0
					],
					"text": "phasor~ 0.5",
					"outlettype": [
						"signal"
					]
				}
			},
			{
				"box": {
					"id": "obj-18",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						220.0,
						325.0,
						40.0,
						22.0
					],
					"text": "cos~",
					"outlettype": [
						"signal"
					]
				}
			},
			{
				"box": {
					"id": "obj-19",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						30.0,
						390.0,
						170.0,
						22.0
					],
					"text": "mc.mixdown~ 1 @autogain 0",
					"outlettype": [
						"multichannelsignal"
					]
				}
			},
			{
				"box": {
					"id": "obj-20",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 3,
					"patching_rect": [
						30.0,
						430.0,
						120.0,
						22.0
					],
					"text": "gen~",
					"outlettype": [
						"signal",
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
									"code": "// one-pole smoothing coefficient for a time constant in ms (63% of the way there in that time)\nsmoothing_coefficient(time_constant_ms, sample_rate) {\n\treturn 1 - exp(-1000 / (max(time_constant_ms, 0.001) * sample_rate));\n}\n\n// in1: the voices, mono. in2: Live's beat ramp (plugphasor~). out1/out2: left/right.\n// soft clip: clean below 0.8, rounding off above (gen needs functions first)\nsclip(v) {\n\ta = abs(v);\n\ty = v;\n\tif (a > 0.8) {\n\t\ty = (v < 0 ? -1 : 1) * (0.8 + 0.2 * tanh((a - 0.8) / 0.2));\n\t}\n\treturn y;\n}\n\n// the pump's duck (0..1) at phase ph of a division: a sine ramp in over atkf, then a recovery shaped by curve\npump_duck(ph, atkf, release_end, curve) {\n\tduck = 0;\n\tif (ph < atkf) {\n\t\tduck = sin(1.5707963 * ph / atkf);\n\t} else {\n\t\tduck = pow(1 - clamp((ph - atkf) / (release_end - atkf), 0, 1), 1 + curve * 3);\n\t}\n\treturn duck;\n}\n\n// The echo is only for throws: silent until Dub, Throw or Freeze feeds it.\nParam drive(0.25, min=0, max=1);        // tape saturation\nParam dtime(363, min=20, max=6000.0);  // ms (Live's tempo x the Time menu): 1/2 at 20 BPM is the longest\nParam dub(0, min=0, max=1);             // the dub macro: send, feedback, darker, smeared\nParam throwgate(0, min=0, max=1);       // 1 while a throw is open\nParam freeze(0, min=0, max=1);          // hold the loop\nParam pumpdepth(0, min=0, max=1);\nParam pumprate(1, min=0.25, max=4);     // ducks per beat\nParam pumpatk(6, min=1, max=40);        // ms to full duck\nParam pumprel(0.55, min=0.1, max=0.95); // fraction of the division to recover\nParam pumpcurve(0.5, min=0, max=1);     // recovery: 0 linear .. 1 snappy\nParam bpm(120, min=20, max=999);        // Live's tempo, for the pump's own clock when stopped\nParam transport(0, min=0, max=1);       // 1 while Live plays: lock to its beat\nParam volume(0, min=-60, max=12);       // output, dB\nParam panic(0);                         // Stop: every new number empties the echo\n\nDelay dl(samplerate * 6.25);   // samplerate is a constant to gen~, so the size follows it\nDelay dr(samplerate * 6.25);\nDelay al1(samplerate * 0.02);           // the diffusion allpasses: up to 14 ms\nDelay al2(samplerate * 0.02);\nDelay ar1(samplerate * 0.02);\nDelay ar2(samplerate * 0.02);\nHistory ts(363), wph(0), wph2(0), sendsm(0), fbsm(0.4), frz(0);\nHistory lpl1(0), lpl2(0), hpl(0), lpr1(0), lpr2(0), hpr(0), lvl(0), ownph(0), gsm(1);\nHistory lastpanic(0), elapsed(1e9), pressfade(0);\nHistory live_clock_weight(0);           // 0 = the pump runs on its own clock, 1 = on Live's beat\n\nsr = samplerate;\n// Smoothing time constants in ms (each was a per-sample coefficient; the times are what it gave at 44.1 kHz).\nfreeze_glide = smoothing_coefficient(11.3, sr);\nsend_rise = smoothing_coefficient(1.12, sr);\nsend_fall = smoothing_coefficient(15.1, sr);\nfeedback_rise = smoothing_coefficient(2.26, sr);\nfeedback_fall = smoothing_coefficient(567, sr);\necho_time_glide = smoothing_coefficient(56.7, sr);\nlevel_meter_fall = smoothing_coefficient(75.6, sr);\npump_gain_glide = smoothing_coefficient(0.442, sr);\ngain = 1 + drive * 5;\nx = tanh(in1 * gain) / (1 + drive * 2.2);\n\n// what goes into the echo, and how long it rings\nfrz = frz + (freeze - frz) * freeze_glide;\ntarget_send = max(dub * dub * 0.9, throwgate) * (1 - freeze);\nsendsm = sendsm + (target_send - sendsm) * (target_send > sendsm ? send_rise : send_fall);\ntarget_fb = max(0.3 + dub * 0.62, throwgate * 0.9);\nfbsm = fbsm + (target_fb - fbsm) * (target_fb > fbsm ? feedback_rise : feedback_fall);\nfb = fbsm * (1 - frz) + 1.05 * frz;\nlooplp = (4500 - dub * 3100) * (1 - frz) + 9000 * frz;\nloophp = (90 + dub * 160) * (1 - frz) + 50 * frz;\ndiffuse = 0.2 + dub * 0.45;\n\n// tape echo: time glides when it changes, wow and flutter, L/R slightly apart\nts = ts + (dtime - ts) * echo_time_glide;\nwph = wrap(wph + 0.53 / sr, 0, 1);\nwph2 = wrap(wph2 + 0.137 / sr, 0, 1);\nwow = (sin(twopi * wph) * 0.6 + sin(twopi * wph2) * 0.4) * 0.0012;\necho_buffer_samples = samplerate * 6.25;\ntl = clamp(mstosamps(ts * 1.031 * (1 + wow)), 2, echo_buffer_samples - 4);   // -4: room for the cubic read\ntr = clamp(mstosamps(ts * 0.979 * (1 - 0.8 * wow)), 2, echo_buffer_samples - 4);\n\n// Stop: everything in the buffers is from before it. `clean` is a gain by where the longest read lands:\n// 0 on audio from before Stop, rising to 1 over the 2 ms of audio written after it. It is a position, not\n// a time, so a read gliding back past the Stop point (Time changed) is silent however fast it moves.\n// The old echo fades out over 2 ms at the press, so no click. New sound goes in straight away.\nif (panic != lastpanic) {\n\tlastpanic = panic;\n\telapsed = 0;\n\tpressfade = 1;\n}\nelapsed = min(elapsed + 1, 1e9);       // capped far past any read, so `clean` stays 1 long after Stop\nclean = clamp((elapsed - max(tl, tr) - 3) / mstosamps(2), 0, 1);   // -3: the cubic read's reach\npressfade = max(pressfade - 1 / mstosamps(2), 0);\nkeep = max(clean, pressfade);\nrl = dl.read(tl, interp=\"cubic\") * keep;\nrr = dr.read(tr, interp=\"cubic\") * keep;\nif (clean <= 0) {                      // empty the loop filters too\n\tlpl1 = 0;\n\tlpl2 = 0;\n\thpl = 0;\n\tlpr1 = 0;\n\tlpr2 = 0;\n\thpr = 0;\n}\n\n// in the loop: low-pass (12 dB) and high-pass, compounding on every repeat\nlpk = 1 - exp(-twopi * looplp / sr);\nhpk = 1 - exp(-twopi * loophp / sr);\nlpl1 = lpl1 + lpk * (rl - lpl1);\nlpl2 = lpl2 + lpk * (lpl1 - lpl2);\nhpl = hpl + hpk * (lpl2 - hpl);\nfl = lpl2 - hpl;\nlpr1 = lpr1 + lpk * (rr - lpr1);\nlpr2 = lpr2 + lpk * (lpr1 - lpr2);\nhpr = hpr + hpk * (lpr2 - hpr);\nfr = lpr2 - hpr;\n\n// diffusion: two allpasses per side\nd1 = al1.read(mstosamps(8.458));          // 373, 587, 401 and 613 samples at 44.1 kHz\nv1 = fl + diffuse * d1;\nal1.write(v1 * clean);\nfl = d1 - diffuse * v1;\nd2 = al2.read(mstosamps(13.311));\nv2 = fl + diffuse * d2;\nal2.write(v2 * clean);\nfl = d2 - diffuse * v2;\nd3 = ar1.read(mstosamps(9.093));\nv3 = fr + diffuse * d3;\nar1.write(v3 * clean);\nfr = d3 - diffuse * v3;\nd4 = ar2.read(mstosamps(13.900));\nv4 = fr + diffuse * d4;\nar2.write(v4 * clean);\nfr = d4 - diffuse * v4;\n\ndl.write(x * sendsm + clean * tanh(fl * fb * 1.1) / 1.1);\ndr.write(x * sendsm + clean * tanh(fr * fb * 1.1) / 1.1);\n\n// pump: a sidechain-style duck on every beat division. Live's beat while it plays, our own clock when\n// stopped. The duck ramps in over Attack (never a jump, so no click), recovers over Release with Curve.\n// The two clocks are at different places in the beat, so Live starting or stopping hands over from one to\n// the other with a 20 ms crossfade of their ducks, not a switch (which jumped the gain).\nownph = wrap(ownph + bpm / 60 / sr, 0, 1);\ndivms = 60000 / max(bpm, 20) / pumprate;\natkf = clamp(pumpatk / divms, 0.001, 0.3);\nrl_end = max(pumprel, atkf + 0.05);\nlive_clock_weight = live_clock_weight + ((transport > 0.5 ? 1 : 0) - live_clock_weight) * smoothing_coefficient(20, sr);\nduck_on_live_beat = pump_duck(wrap(in2 * pumprate, 0, 1), atkf, rl_end, pumpcurve);\nduck_on_own_clock = pump_duck(wrap(ownph * pumprate, 0, 1), atkf, rl_end, pumpcurve);\nduck = duck_on_own_clock + (duck_on_live_beat - duck_on_own_clock) * live_clock_weight;\ntarget_g = 1 - pumpdepth * duck;\ngsm = gsm + (target_g - gsm) * pump_gain_glide;   // ~1 ms to 90%: no steps, ever\n\nlvl = max(abs(rl) + abs(rr), lvl * (1 - level_meter_fall));\nout3 = lvl;\ngain = dbtoa(volume) * 2;              // +6 dB over the old level; the soft clip catches overs\nout1 = sclip((x + rl * 1.2) * gsm * gain);\nout2 = sclip((x + rr * 1.2) * gsm * gain);\n",
									"fontname": "<Monospaced>",
									"fontsize": 12.0,
									"numinlets": 2,
									"numoutlets": 3,
									"outlettype": [
										"",
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
									"id": "in1",
									"maxclass": "newobj",
									"text": "in 1",
									"numinlets": 0,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										20.0,
										20.0,
										40.0,
										22.0
									]
								}
							},
							{
								"box": {
									"id": "in2",
									"maxclass": "newobj",
									"text": "in 2",
									"numinlets": 0,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										100.0,
										20.0,
										40.0,
										22.0
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
							},
							{
								"box": {
									"id": "out3",
									"maxclass": "newobj",
									"text": "out 3",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										180.0,
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
										"in1",
										0
									],
									"destination": [
										"cb",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"in2",
										0
									],
									"destination": [
										"cb",
										1
									]
								}
							},
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
							},
							{
								"patchline": {
									"source": [
										"cb",
										2
									],
									"destination": [
										"out3",
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
					"id": "obj-21",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						160.0,
						400.0,
						80.0,
						22.0
					],
					"text": "plugphasor~",
					"outlettype": [
						"signal",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-22",
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
					"id": "obj-23",
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
					"id": "obj-24",
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
					"id": "obj-25",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						620.0,
						90.0,
						140.0,
						22.0
					],
					"text": "property root_note",
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
						620.0,
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
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						620.0,
						180.0,
						110.0,
						22.0
					],
					"text": "prepend root",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-28",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						780.0,
						90.0,
						140.0,
						22.0
					],
					"text": "property scale_intervals",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-29",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						780.0,
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
					"id": "obj-30",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						780.0,
						180.0,
						110.0,
						22.0
					],
					"text": "prepend intervals",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-31",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						940.0,
						90.0,
						140.0,
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
					"id": "obj-32",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						940.0,
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
					"id": "obj-33",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						940.0,
						180.0,
						110.0,
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
					"id": "obj-34",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						470.0,
						90.0,
						100.0,
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
					"id": "obj-35",
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
					"id": "obj-36",
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
					"id": "obj-37",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						420.0,
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
					"id": "obj-38",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						420.0,
						220.0,
						90.0,
						22.0
					],
					"text": "pak 120. 0.75",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-39",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						420.0,
						250.0,
						150.0,
						22.0
					],
					"text": "expr 60000. / $f1 * $f2",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-40",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						420.0,
						280.0,
						80.0,
						22.0
					],
					"text": "prepend dtime",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-41",
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
					"id": "obj-42",
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
					"id": "obj-43",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						720.0,
						250.0,
						110.0,
						22.0
					],
					"text": "prepend transport",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-44",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						620.0,
						250.0,
						80.0,
						22.0
					],
					"text": "prepend bpm",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-45",
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
					"id": "obj-46",
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
					"id": "obj-47",
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
					"id": "obj-48",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						250.0,
						520.0,
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
					"id": "obj-49",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						250.0,
						550.0,
						55.0,
						22.0
					],
					"text": "throwgate 1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-50",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						320.0,
						550.0,
						60.0,
						22.0
					],
					"text": "delay 8n",
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "obj-51",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						320.0,
						580.0,
						55.0,
						22.0
					],
					"text": "throwgate 0",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-52",
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
					"filename": "2sl-stab-view.js",
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
					"id": "obj-53",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						30.0,
						120.0,
						22.0
					],
					"text": "js 2sl-stab-ui.js",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-54",
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
					"id": "obj-55",
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
					"id": "obj-56",
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
					"id": "obj-57",
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
					"id": "obj-58",
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
					"id": "obj-59",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1003.0,
						56.0,
						15.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"link"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						3.0,
						56.0,
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
					"id": "obj-60",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1500.0,
						560.0,
						144.0,
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
						80.0,
						3.0,
						144.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Page",
							"parameter_shortname": "Page",
							"parameter_type": 2,
							"parameter_enum": [
								"play",
								"osc",
								"shape"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Page",
							"parameter_info": "Shows the play, osc or shape page. Controls on hidden pages keep working."
						}
					},
					"annotation_name": "Page",
					"annotation": "Shows the play, osc or shape page. Controls on hidden pages keep working.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1
				}
			},
			{
				"box": {
					"id": "obj-61",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1020.0,
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
					"id": "obj-62",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1784.0,
						643.0,
						200.0,
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
						284.0,
						3.0,
						200.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Preset",
							"parameter_shortname": "Preset",
							"parameter_type": 2,
							"parameter_enum": [
								"init",
								"chain stab",
								"m-stab",
								"deep haze",
								"fog",
								"wash",
								"skank",
								"roots chop",
								"sub stab",
								"tape chord",
								"ambient dub",
								"throw dub",
								"hypnotic loop",
								"dark machine",
								"chord memory",
								"warehouse",
								"pulse",
								"rolling",
								"dark fifths",
								"throw machine",
								"detroit strings",
								"deep house keys",
								"pump pad"
							],
							"parameter_mmax": 22,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Preset",
							"parameter_info": "Sets every control (and the machine's pattern) to a preset; tweak from there. When Live reopens a set, your saved tweaks win."
						}
					},
					"annotation_name": "Preset",
					"annotation": "Sets every control (and the machine's pattern) to a preset; tweak from there. When Live reopens a set, your saved tweaks win."
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
							"parameter_info": "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs. Presets set it to match their loudness."
						}
					},
					"annotation_name": "Volume",
					"annotation": "Output level, -36 to +12 dB (default 0). A soft clip above about -2 dBFS rounds off overs. Presets set it to match their loudness."
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
					"text": "prepend volume",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-65",
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
							"parameter_info": "Panic: releases every note, clears a latched chord, ramps the voices to silence in 20 ms, empties the echo and turns Freeze off. Stopping Live doesn't run it: tails ring out.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Stop",
					"annotation": "Panic: releases every note, clears a latched chord, ramps the voices to silence in 20 ms, empties the echo and turns Freeze off. Stopping Live doesn't run it: tails ring out.",
					"texton": "stop",
					"mode": 0
				}
			},
			{
				"box": {
					"id": "obj-66",
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
					"id": "obj-67",
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
					"id": "obj-68",
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
					"id": "obj-69",
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
					"id": "obj-70",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1028.0,
						184.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"chord"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						184.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Chord",
					"annotation": "The chord sounding now: its name, its notes (top right), and two octaves of keys with those notes lit mint. With Machine on, the last stab the machine played. In orange on top: In Key is on but Live's scale has under 5 notes, so chords use the fixed shapes.",
					"varname": "view_chord"
				}
			},
			{
				"box": {
					"id": "obj-71",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1512.0,
						738.0,
						112.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "chord",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						12.0,
						98.0,
						112.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Chord",
							"parameter_shortname": "Chord",
							"parameter_type": 2,
							"parameter_enum": [
								"poly",
								"minor",
								"m7",
								"m9",
								"m11",
								"sus4",
								"fifths",
								"dark"
							],
							"parameter_mmax": 7,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1
							],
							"parameter_annotation_name": "Chord",
							"parameter_info": "What each key plays: poly plays your notes as they are; the others stack a chord on each key (minor, m7, m9, m11, sus4, fifths, dark = 0-5-8). Default minor."
						}
					},
					"annotation_name": "Chord",
					"annotation": "What each key plays: poly plays your notes as they are; the others stack a chord on each key (minor, m7, m9, m11, sus4, fifths, dark = 0-5-8). Default minor."
				}
			},
			{
				"box": {
					"id": "obj-72",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1042.0,
						100.0,
						22.0
					],
					"text": "prepend shape",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-73",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1628.0,
						758.0,
						68.0,
						15.0
					],
					"text": "in key",
					"outlettype": [
						"",
						""
					],
					"varname": "in_key",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						128.0,
						98.0,
						68.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "In Key",
							"parameter_shortname": "In Key",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "In Key",
							"parameter_info": "Builds chords from the scale set in Live (its root and scale): each key snaps down into the scale and the chord stacks scale tones on it. Scales under 5 notes fall back to the fixed shapes, and the chord display says so.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "In Key",
					"annotation": "Builds chords from the scale set in Live (its root and scale): each key snaps down into the scale and the chord stacks scale tones on it. Scales under 5 notes fall back to the fixed shapes, and the chord display says so.",
					"texton": "in key",
					"mode": 1
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
					"text": "prepend inkey",
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
						1512.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "tone",
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
							"parameter_longname": "Tone",
							"parameter_shortname": "Tone",
							"parameter_type": 0,
							"parameter_mmin": -100.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Tone",
							"parameter_info": "Brighter or darker: moves the cutoff up to 2.5 octaves either way, and the filter envelope with it. -100 to +100, default 0."
						}
					},
					"annotation_name": "Tone",
					"annotation": "Brighter or darker: moves the cutoff up to 2.5 octaves either way, and the filter envelope with it. -100 to +100, default 0."
				}
			},
			{
				"box": {
					"id": "obj-76",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1050.0,
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
					"id": "obj-77",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1052.0,
						100.0,
						22.0
					],
					"text": "prepend tonemac",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-78",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1582.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "length",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						82.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Length",
							"parameter_shortname": "Length",
							"parameter_type": 0,
							"parameter_mmin": -100.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Length",
							"parameter_info": "Shorter or longer tails: scales Decay and Release from x0.25 (-100) to x4 (+100). Default 0."
						}
					},
					"annotation_name": "Length",
					"annotation": "Shorter or longer tails: scales Decay and Release from x0.25 (-100) to x4 (+100). Default 0."
				}
			},
			{
				"box": {
					"id": "obj-79",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1056.0,
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
					"text": "prepend lenmac",
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
						1652.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "drift",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						152.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Drift",
							"parameter_shortname": "Drift",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Drift",
							"parameter_info": "Chance each chord gets another voicing of the same chord (inverted, top note dropped, middle spread, or octave added). 0 = always the same."
						}
					},
					"annotation_name": "Drift",
					"annotation": "Chance each chord gets another voicing of the same chord (inverted, top note dropped, middle spread, or octave added). 0 = always the same."
				}
			},
			{
				"box": {
					"id": "obj-82",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1062.0,
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
					"text": "prepend drift",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-84",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1720.0,
						1028.0,
						280.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"steps"
					],
					"presentation": 1,
					"presentation_rect": [
						220.0,
						28.0,
						280.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Pattern",
					"annotation": "The machine's 16 steps, as Shift places them. Click a step to cycle rest, hit, accent. Bright with a bar on top: accent (full velocity, fires at Density x1.4). Dim: hit (softer, fires at Density). Empty steps: the lighter ones start each beat. Blue outline: the step playing now. Orange outline: that stab was thrown into the echo.",
					"varname": "view_steps"
				}
			},
			{
				"box": {
					"id": "obj-85",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1720.0,
						758.0,
						72.0,
						15.0
					],
					"text": "machine",
					"outlettype": [
						"",
						""
					],
					"varname": "machine",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						220.0,
						98.0,
						72.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Machine",
							"parameter_shortname": "Machine",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Machine",
							"parameter_info": "With Machine on, keys don't play directly: they pick the chord the pattern plays, on 16th steps. Follows Live's transport. With Live stopped it plays only keys you hold, at Live's tempo.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Machine",
					"annotation": "With Machine on, keys don't play directly: they pick the chord the pattern plays, on 16th steps. Follows Live's transport. With Live stopped it plays only keys you hold, at Live's tempo.",
					"texton": "machine",
					"mode": 1
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
					"text": "prepend machine",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-87",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1796.0,
						758.0,
						56.0,
						15.0
					],
					"text": "latch",
					"outlettype": [
						"",
						""
					],
					"varname": "latch",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						296.0,
						98.0,
						56.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Latch",
							"parameter_shortname": "Latch",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Latch",
							"parameter_info": "With Machine on, the chord keeps playing after you let go, while Live plays. A new chord replaces it; Stop clears it.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Latch",
					"annotation": "With Machine on, the chord keeps playing after you let go, while Live plays. A new chord replaces it; Stop clears it.",
					"texton": "latch",
					"mode": 1
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
					"text": "prepend latch",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-89",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1856.0,
						738.0,
						144.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "pattern",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						356.0,
						98.0,
						144.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Pattern",
							"parameter_shortname": "Pattern",
							"parameter_type": 2,
							"parameter_enum": [
								"dub dotted",
								"one & three+",
								"offbeat chops",
								"skank",
								"deep stab",
								"3-3-2"
							],
							"parameter_mmax": 5,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Pattern",
							"parameter_info": "Loads a 16-step stab pattern as a starting point. Click steps in the display to cycle rest, hit, accent; edited steps are saved with the set."
						}
					},
					"annotation_name": "Pattern",
					"annotation": "Loads a 16-step stab pattern as a starting point. Click steps in the display to cycle rest, hit, accent; edited steps are saved with the set."
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
					"text": "prepend pattern",
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
						1720.0,
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
						220.0,
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
								80.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Density",
							"parameter_info": "Each step fires by chance: hits at Density, accents at Density x1.4. Above 70%, empty offbeat 16ths also fire now and then (up to 15% at 100). Default 80%."
						}
					},
					"annotation_name": "Density",
					"annotation": "Each step fires by chance: hits at Density, accents at Density x1.4. Above 70%, empty offbeat 16ths also fire now and then (up to 15% at 100). Default 80%."
				}
			},
			{
				"box": {
					"id": "obj-92",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1082.0,
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
					"id": "obj-93",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1084.0,
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
					"id": "obj-94",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1776.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "throws",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						276.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Throws",
							"parameter_shortname": "Throws",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Throws",
							"parameter_info": "Chance each machine stab is also thrown into the echo (opens the echo for an 8th at 90% feedback)."
						}
					},
					"annotation_name": "Throws",
					"annotation": "Chance each machine stab is also thrown into the echo (opens the echo for an 8th at 90% feedback)."
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
					"text": "prepend throws",
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
						1832.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "gate",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						332.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Gate",
							"parameter_shortname": "Gate",
							"parameter_type": 0,
							"parameter_mmin": 1.0,
							"parameter_mmax": 4.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Gate",
							"parameter_info": "How long each machine stab is held, in 16th notes (1-4). Default 1."
						}
					},
					"annotation_name": "Gate",
					"annotation": "How long each machine stab is held, in 16th notes (1-4). Default 1."
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
					"text": "prepend length",
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
						1888.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "shift",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						388.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Shift",
							"parameter_shortname": "Shift",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 15.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Shift",
							"parameter_info": "Rotates the pattern later by 0-15 16ths without changing it; the display shows the shifted pattern. Default 0."
						}
					},
					"annotation_name": "Shift",
					"annotation": "Rotates the pattern later by 0-15 16ths without changing it; the display shows the shifted pattern. Default 0."
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
					"text": "prepend shift",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-101",
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
					"varname": "steps",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Steps",
							"parameter_shortname": "Steps",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								73.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-102",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1500.0,
						1430.0,
						60.0,
						15.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "accents",
					"parameter_enable": 1,
					"presentation": 0,
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Accents",
							"parameter_shortname": "Accents",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 65535.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1.0
							],
							"parameter_unitstyle": 0,
							"parameter_invisible": 1
						}
					}
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
					"text": "prepend stepbits",
					"outlettype": [
						""
					]
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
					"text": "prepend accbits",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-105",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1100.0,
						120.0,
						140.0,
						22.0
					],
					"text": "route stepbits accbits",
					"outlettype": [
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-106",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						2024.0,
						1028.0,
						184.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"echo"
					],
					"presentation": 1,
					"presentation_rect": [
						524.0,
						28.0,
						184.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Echo",
					"annotation": "The stab (left) and its repeats, each lower by the feedback, mint fading as they go round (slower with more Dub). Outlines only while the echo is silent. Frozen: the loop swelling, each repeat a little louder (105% feedback, less what the loop's filters take) from its level now up to full height, where tape saturation holds it. A throw flashes an orange frame. The line along the bottom is the echo's level now.",
					"varname": "view_echo"
				}
			},
			{
				"box": {
					"id": "obj-107",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						160.0,
						470.0,
						80.0,
						22.0
					],
					"text": "snapshot~ 33",
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
					"text": "prepend level",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-109",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2024.0,
						758.0,
						88.0,
						15.0
					],
					"text": "throw",
					"outlettype": [
						"",
						""
					],
					"varname": "throw",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						524.0,
						98.0,
						88.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Throw",
							"parameter_shortname": "Throw",
							"parameter_type": 2,
							"parameter_annotation_name": "Throw",
							"parameter_info": "Throws the sound into the echo now: opens the echo for an 8th at 90% feedback.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Throw",
					"annotation": "Throws the sound into the echo now: opens the echo for an 8th at 90% feedback.",
					"texton": "throw",
					"mode": 0
				}
			},
			{
				"box": {
					"id": "obj-110",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						300.0,
						520.0,
						45.0,
						22.0
					],
					"text": "throw",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-111",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2120.0,
						758.0,
						88.0,
						15.0
					],
					"text": "freeze",
					"outlettype": [
						"",
						""
					],
					"varname": "freeze",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						620.0,
						98.0,
						88.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Freeze",
							"parameter_shortname": "Freeze",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Freeze",
							"parameter_info": "Holds the echo loop: nothing new goes in, and each time round it gets a little louder, so it swells over tens of seconds until tape saturation holds it just under full level. Stop turns it off.",
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					},
					"annotation_name": "Freeze",
					"annotation": "Holds the echo loop: nothing new goes in, and each time round it gets a little louder, so it swells over tens of seconds until tape saturation holds it just under full level. Stop turns it off.",
					"texton": "freeze",
					"mode": 1
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
					"text": "prepend freeze",
					"outlettype": [
						""
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
					"text": "prepend freeze",
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
						2024.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "dub",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						524.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Dub",
							"parameter_shortname": "Dub",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Dub",
							"parameter_info": "The echo amount: more sound sent in, longer feedback (30% to 92%), each repeat darker and more smeared. 0 = no echo except throws."
						}
					},
					"annotation_name": "Dub",
					"annotation": "The echo amount: more sound sent in, longer feedback (30% to 92%), each repeat darker and more smeared. 0 = no echo except throws."
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
					"text": "prepend dub",
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
					"text": "prepend dub",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-119",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						2088.0,
						776.0,
						64.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "echo_time",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						588.0,
						136.0,
						64.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Echo Time",
							"parameter_shortname": "Time",
							"parameter_type": 2,
							"parameter_enum": [
								"1/16",
								"1/8",
								"1/8d",
								"1/4",
								"1/4d",
								"1/2"
							],
							"parameter_mmax": 5,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								2
							],
							"parameter_annotation_name": "Echo Time",
							"parameter_info": "Echo time, synced to Live's tempo: 1/16 to 1/2 (default 1/8 dotted). Left and right run slightly apart; a change glides like tape."
						}
					},
					"annotation_name": "Echo Time",
					"annotation": "Echo time, synced to Live's tempo: 1/16 to 1/2 (default 1/8 dotted). Left and right run slightly apart; a change glides like tape."
				}
			},
			{
				"box": {
					"id": "obj-120",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						700.0,
						400.0,
						22.0
					],
					"text": "expr ($i1==0)*0.25 + ($i1==1)*0.5 + ($i1==2)*0.75 + ($i1==3)*1. + ($i1==4)*1.5 + ($i1==5)*2.",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-121",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						2232.0,
						1028.0,
						216.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"pump"
					],
					"presentation": 1,
					"presentation_rect": [
						732.0,
						28.0,
						216.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Pump",
					"annotation": "The output level over two beats at Live's tempo: each dip is a duck, mint while Depth is above 0. The blue line is Live's position in the beat. Top right: Depth.",
					"varname": "view_pump"
				}
			},
			{
				"box": {
					"id": "obj-122",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						250.0,
						430.0,
						80.0,
						22.0
					],
					"text": "snapshot~ 33",
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
					"text": "prepend phase",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-124",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1146.0,
						100.0,
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
					"id": "obj-125",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						2232.0,
						738.0,
						96.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "pump_rate",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						732.0,
						98.0,
						96.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Pump Rate",
							"parameter_shortname": "Rate",
							"parameter_type": 2,
							"parameter_enum": [
								"1/4",
								"1/8",
								"1/16"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Pump Rate",
							"parameter_info": "How often the pump ducks: every quarter, 8th or 16th note."
						}
					},
					"annotation_name": "Pump Rate",
					"annotation": "How often the pump ducks: every quarter, 8th or 16th note."
				}
			},
			{
				"box": {
					"id": "obj-126",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						760.0,
						260.0,
						22.0
					],
					"text": "expr ($i1==0)*1. + ($i1==1)*2. + ($i1==2)*4.",
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
					"text": "prepend pumprate",
					"outlettype": [
						""
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
					"text": "prepend rate",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-129",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2232.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "pump",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						732.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Pump",
							"parameter_shortname": "Depth",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Pump Depth",
							"parameter_info": "How deep the output ducks on every Pump Rate step; 100% ducks to silence. Locks to Live's beat while it plays. Default 0."
						}
					},
					"annotation_name": "Pump Depth",
					"annotation": "How deep the output ducks on every Pump Rate step; 100% ducks to silence. Locks to Live's beat while it plays. Default 0."
				}
			},
			{
				"box": {
					"id": "obj-130",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1158.0,
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
					"text": "prepend pumpdepth",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-132",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1162.0,
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
					"id": "obj-133",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1164.0,
						100.0,
						22.0
					],
					"text": "prepend depth",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-134",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2288.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "pump_attack",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						788.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Pump Attack",
							"parameter_shortname": "Attack",
							"parameter_type": 0,
							"parameter_mmin": 1.0,
							"parameter_mmax": 40.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								6.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 2.0,
							"parameter_annotation_name": "Pump Attack",
							"parameter_info": "Time to full duck, in ms (1-40, default 6). A ramp, never a jump, so no click."
						}
					},
					"annotation_name": "Pump Attack",
					"annotation": "Time to full duck, in ms (1-40, default 6). A ramp, never a jump, so no click."
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
					"text": "prepend pumpatk",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-136",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1170.0,
						100.0,
						22.0
					],
					"text": "prepend atk",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-137",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2344.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "pump_release",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						844.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Pump Release",
							"parameter_shortname": "Release",
							"parameter_type": 0,
							"parameter_mmin": 10.0,
							"parameter_mmax": 95.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								55.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Pump Release",
							"parameter_info": "How much of each step the pump takes to come back up (10% to 95%, default 55%)."
						}
					},
					"annotation_name": "Pump Release",
					"annotation": "How much of each step the pump takes to come back up (10% to 95%, default 55%)."
				}
			},
			{
				"box": {
					"id": "obj-138",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1174.0,
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
					"text": "prepend pumprel",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-140",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1178.0,
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
					"id": "obj-141",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1180.0,
						100.0,
						22.0
					],
					"text": "prepend rel",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-142",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2400.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "pump_curve",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						900.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Pump Curve",
							"parameter_shortname": "Curve",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Pump Curve",
							"parameter_info": "Shape of the recovery: 0 = linear, 100 = snappy (comes back fast, then eases in). Default 50."
						}
					},
					"annotation_name": "Pump Curve",
					"annotation": "Shape of the recovery: 0 = linear, 100 = snappy (comes back fast, then eases in). Default 50."
				}
			},
			{
				"box": {
					"id": "obj-143",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1184.0,
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
					"id": "obj-144",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1186.0,
						100.0,
						22.0
					],
					"text": "prepend pumpcurve",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-145",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1188.0,
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
					"id": "obj-146",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1190.0,
						100.0,
						22.0
					],
					"text": "prepend curve",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-147",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1028.0,
						140.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"sub"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						140.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Sub",
					"annotation": "The sub as the voice makes it for Sub Mode, in mint: DCO 1 divided by 2 or 4, drawn over the same time as DCO 1's two cycles, so -1 oct is one cycle and -2 oct half of one (shown across an edge). The 25% pulse sits off centre (+1.5 / -0.5) as in the voice. Top right: the mode. Its level is Sub in the mixer.",
					"varname": "view_sub",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-148",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1512.0,
						698.0,
						140.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "sub_mode",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						12.0,
						98.0,
						140.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Sub Mode",
							"parameter_shortname": "Sub",
							"parameter_type": 2,
							"parameter_enum": [
								"-1 sq",
								"-2 sq",
								"-2 pls"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "Sub Mode",
							"parameter_info": "The sub's wave, as on the SH-101: a square 1 octave below DCO 1, a square 2 octaves below, or a 25% pulse 2 octaves below (keeps a strong -1 octave). Default -1 oct square."
						}
					},
					"annotation_name": "Sub Mode",
					"annotation": "The sub's wave, as on the SH-101: a square 1 octave below DCO 1, a square 2 octaves below, or a 25% pulse 2 octaves below (keeps a strong -1 octave). Default -1 oct square.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-149",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1196.0,
						100.0,
						22.0
					],
					"text": "prepend submode",
					"outlettype": [
						""
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
					"text": "prepend submode",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-151",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1676.0,
						1028.0,
						196.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"osc1"
					],
					"presentation": 1,
					"presentation_rect": [
						176.0,
						28.0,
						196.0,
						64.0
					],
					"border": 0,
					"annotation_name": "DCO 1",
					"annotation": "Two cycles of DCO 1's waveform as the voice makes it (saw, pulse or both), in mint. Top right: the wave and pulse width. With PWM up, the pulse width moves with the LFO, in step with it.",
					"varname": "view_osc1",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-152",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1676.0,
						698.0,
						120.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "dco1_wave",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						176.0,
						98.0,
						120.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "DCO1 Wave",
							"parameter_shortname": "Wave 1",
							"parameter_type": 2,
							"parameter_enum": [
								"saw",
								"pulse",
								"both"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								2
							],
							"parameter_annotation_name": "DCO 1 Wave",
							"parameter_info": "DCO 1 waveform: saw, pulse (width from PW), or both mixed."
						}
					},
					"annotation_name": "DCO 1 Wave",
					"annotation": "DCO 1 waveform: saw, pulse (width from PW), or both mixed.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1,
					"hidden": 1
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
					"text": "prepend wave1",
					"outlettype": [
						""
					]
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
					"text": "prepend wave1",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-155",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1800.0,
						698.0,
						72.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "dco1_octave",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						300.0,
						98.0,
						72.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "DCO1 Octave",
							"parameter_shortname": "Oct 1",
							"parameter_type": 2,
							"parameter_enum": [
								"16'",
								"8'",
								"4'"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1
							],
							"parameter_annotation_name": "DCO 1 Octave",
							"parameter_info": "DCO 1 footage: 16' an octave down, 8' as played, 4' an octave up. The sub follows it."
						}
					},
					"annotation_name": "DCO 1 Octave",
					"annotation": "DCO 1 footage: 16' an octave down, 8' as played, 4' an octave up. The sub follows it.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-156",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1100.0,
						820.0,
						40.0,
						22.0
					],
					"text": "- 1",
					"outlettype": [
						"int"
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
					"text": "prepend oct1",
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
						1676.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "pw",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						176.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "PW",
							"parameter_shortname": "PW",
							"parameter_type": 0,
							"parameter_mmin": 50.0,
							"parameter_mmax": 95.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								70.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Pulse Width",
							"parameter_info": "Pulse width of both DCOs' pulse waves, 50% (square) to 95% (thin). Default 70%."
						}
					},
					"annotation_name": "Pulse Width",
					"annotation": "Pulse width of both DCOs' pulse waves, 50% (square) to 95% (thin). Default 70%.",
					"hidden": 1
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
					"text": "prepend pw",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-161",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1220.0,
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
					"text": "prepend pw",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-163",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1732.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "pwm",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						232.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "PWM",
							"parameter_shortname": "PWM",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "PWM",
							"parameter_info": "How much the LFO moves the pulse width (up to +-35%): the Juno shimmer. Only heard on pulse waves."
						}
					},
					"annotation_name": "PWM",
					"annotation": "How much the LFO moves the pulse width (up to +-35%): the Juno shimmer. Only heard on pulse waves.",
					"hidden": 1
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
					"text": "prepend pwmamt",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-166",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1230.0,
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
					"text": "prepend pwm",
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
						1896.0,
						1028.0,
						196.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"osc2"
					],
					"presentation": 1,
					"presentation_rect": [
						396.0,
						28.0,
						196.0,
						64.0
					],
					"border": 0,
					"annotation_name": "DCO 2",
					"annotation": "DCO 2's waveform (saw, pulse or triangle) over the same time as DCO 1's two cycles, so Semi shows as more or fewer cycles. Its pulse has PW's width and moves with PWM, as DCO 1's. Top right: the wave, pulse width (on pulse), Semi and Fine.",
					"varname": "view_osc2",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-169",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						1896.0,
						698.0,
						120.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "dco2_wave",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						396.0,
						98.0,
						120.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "DCO2 Wave",
							"parameter_shortname": "Wave 2",
							"parameter_type": 2,
							"parameter_enum": [
								"saw",
								"pulse",
								"tri"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_annotation_name": "DCO 2 Wave",
							"parameter_info": "DCO 2 waveform: saw, pulse (width from PW), or triangle."
						}
					},
					"annotation_name": "DCO 2 Wave",
					"annotation": "DCO 2 waveform: saw, pulse (width from PW), or triangle.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1,
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
					"text": "prepend wave2",
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
					"text": "prepend wave2",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-172",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						2020.0,
						698.0,
						72.0,
						15.0
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"varname": "dco2_octave",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						520.0,
						98.0,
						72.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "DCO2 Octave",
							"parameter_shortname": "Oct 2",
							"parameter_type": 2,
							"parameter_enum": [
								"16'",
								"8'",
								"4'"
							],
							"parameter_mmax": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1
							],
							"parameter_annotation_name": "DCO 2 Octave",
							"parameter_info": "DCO 2 footage: 16' an octave down, 8' as played, 4' an octave up."
						}
					},
					"annotation_name": "DCO 2 Octave",
					"annotation": "DCO 2 footage: 16' an octave down, 8' as played, 4' an octave up.",
					"num_lines_patching": 1,
					"num_lines_presentation": 1,
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-173",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1150.0,
						820.0,
						40.0,
						22.0
					],
					"text": "- 1",
					"outlettype": [
						"int"
					]
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
					"text": "prepend oct2",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-175",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1896.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "semi",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						396.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Semi",
							"parameter_shortname": "Semi",
							"parameter_type": 0,
							"parameter_mmin": -12.0,
							"parameter_mmax": 12.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 7,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "DCO 2 Semi",
							"parameter_info": "DCO 2 interval in semitones, -12 to +12 (default 0). 7 = a fifth up."
						}
					},
					"annotation_name": "DCO 2 Semi",
					"annotation": "DCO 2 interval in semitones, -12 to +12 (default 0). 7 = a fifth up.",
					"hidden": 1
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
					"text": "prepend semi",
					"outlettype": [
						""
					]
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
					"text": "prepend semi",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-178",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1952.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "fine",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						452.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Fine",
							"parameter_shortname": "Fine",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 50.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								10.0
							],
							"parameter_unitstyle": 1,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "DCO 2 Fine",
							"parameter_info": "Detunes DCO 2 upward, in cents (0-50, default 10)."
						}
					},
					"annotation_name": "DCO 2 Fine",
					"annotation": "Detunes DCO 2 upward, in cents (0-50, default 10).",
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
					"text": "prepend fine",
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
					"text": "prepend fine",
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
						2116.0,
						764.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "osc_1",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						616.0,
						64.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "OSC 1",
							"parameter_shortname": "OSC 1",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								80.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "OSC 1 Level",
							"parameter_info": "DCO 1 level in the mixer. Default 80%."
						}
					},
					"annotation_name": "OSC 1 Level",
					"annotation": "DCO 1 level in the mixer. Default 80%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-182",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1262.0,
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
					"text": "prepend lvl1",
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
						2168.0,
						764.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "osc_2",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						668.0,
						64.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "OSC 2",
							"parameter_shortname": "OSC 2",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								80.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "OSC 2 Level",
							"parameter_info": "DCO 2 level in the mixer. Default 80%."
						}
					},
					"annotation_name": "OSC 2 Level",
					"annotation": "DCO 2 level in the mixer. Default 80%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-185",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1268.0,
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
					"text": "prepend lvl2",
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
						2116.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "sub",
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
							"parameter_longname": "Sub",
							"parameter_shortname": "Sub",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Sub Level",
							"parameter_info": "Level of the sub: DCO 1 divided down, an octave or two below it (Sub Mode). Default 0."
						}
					},
					"annotation_name": "Sub Level",
					"annotation": "Level of the sub: DCO 1 divided down, an octave or two below it (Sub Mode). Default 0.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-188",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1274.0,
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
					"text": "prepend sublvl",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-190",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2168.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "noise",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						668.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Noise",
							"parameter_shortname": "Noise",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								8.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Noise Level",
							"parameter_info": "Level of white noise in the mix (the 'chuff'). Default 8%."
						}
					},
					"annotation_name": "Noise Level",
					"annotation": "Level of white noise in the mix (the 'chuff'). Default 8%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-191",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1280.0,
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
					"text": "prepend noiseamt",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-193",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						2236.0,
						1028.0,
						212.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"lfo"
					],
					"presentation": 1,
					"presentation_rect": [
						736.0,
						28.0,
						212.0,
						64.0
					],
					"border": 0,
					"annotation_name": "LFO",
					"annotation": "The LFO's last two seconds, scrolling, in mint, in step with the sound (read from the LFO itself) and drawn at its current rate; its rate top right. Along the bottom, where it goes: pwm, vibrato, filter, bright with the amount when on, dim when off.",
					"varname": "view_lfo",
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
					"text": "prepend pwm",
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
					"text": "prepend pw",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-198",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1294.0,
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
					"text": "prepend pwm",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-200",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						310.0,
						300.0,
						80.0,
						22.0
					],
					"text": "snapshot~ 33",
					"outlettype": [
						"float"
					]
				}
			},
			{
				"box": {
					"id": "obj-201",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1300.0,
						100.0,
						22.0
					],
					"text": "prepend lfophase",
					"outlettype": [
						""
					]
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
					"text": "prepend lfophase",
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
					"text": "prepend lfophase",
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
						2236.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "lfo_rate",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						736.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "LFO Rate",
							"parameter_shortname": "Rate",
							"parameter_type": 0,
							"parameter_mmin": 0.05,
							"parameter_mmax": 12.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.5
							],
							"parameter_unitstyle": 3,
							"parameter_exponent": 3.0,
							"parameter_annotation_name": "LFO Rate",
							"parameter_info": "Speed of the sine LFO, 0.05 to 12 Hz (default 0.5). One LFO for all voices."
						}
					},
					"annotation_name": "LFO Rate",
					"annotation": "Speed of the sine LFO, 0.05 to 12 Hz (default 0.5). One LFO for all voices.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-205",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1308.0,
						100.0,
						22.0
					],
					"text": "prepend lforate",
					"outlettype": [
						""
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
					"text": "prepend lforate",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-207",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1312.0,
						100.0,
						22.0
					],
					"text": "prepend lforate",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-208",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2300.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "vibrato",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						800.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Vibrato",
							"parameter_shortname": "Vibrato",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Vibrato",
							"parameter_info": "LFO to pitch, up to +-50 cents."
						}
					},
					"annotation_name": "Vibrato",
					"annotation": "LFO to pitch, up to +-50 cents.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-209",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1316.0,
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
					"text": "prepend vibamt",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-211",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1320.0,
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
					"id": "obj-212",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1322.0,
						100.0,
						22.0
					],
					"text": "prepend vib",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-213",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2364.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "lfo_filter",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						864.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "LFO Filter",
							"parameter_shortname": "Filter",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "LFO Filter",
							"parameter_info": "LFO to cutoff, up to +-3 octaves."
						}
					},
					"annotation_name": "LFO Filter",
					"annotation": "LFO to cutoff, up to +-3 octaves.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-214",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1326.0,
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
					"id": "obj-215",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1328.0,
						100.0,
						22.0
					],
					"text": "prepend lfofilt",
					"outlettype": [
						""
					]
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
					"text": "prepend lfofilt",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-218",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1512.0,
						1028.0,
						340.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"filter"
					],
					"presentation": 1,
					"presentation_rect": [
						12.0,
						28.0,
						340.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Filter",
					"annotation": "The low-pass response from 20 Hz to 20 kHz in mint, with the resonance peak, at the cutoff (top right, Tone included). Grey: how far the envelope opens it at full velocity.",
					"varname": "view_filter",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-219",
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
					"varname": "cutoff",
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
							"parameter_longname": "Cutoff",
							"parameter_shortname": "Cutoff",
							"parameter_type": 0,
							"parameter_mmin": 40.0,
							"parameter_mmax": 12000.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								700.0
							],
							"parameter_unitstyle": 3,
							"parameter_exponent": 3.0,
							"parameter_annotation_name": "Cutoff",
							"parameter_info": "Low-pass cutoff (24 dB ladder), 40 Hz to 12 kHz, default 700 Hz. The envelope, key, Tone and LFO move it from here."
						}
					},
					"annotation_name": "Cutoff",
					"annotation": "Low-pass cutoff (24 dB ladder), 40 Hz to 12 kHz, default 700 Hz. The envelope, key, Tone and LFO move it from here.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-220",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1338.0,
						100.0,
						22.0
					],
					"text": "prepend cutoff",
					"outlettype": [
						""
					]
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
					"text": "prepend cutoff",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-222",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1580.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "resonance",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						80.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Resonance",
							"parameter_shortname": "Reso",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								30.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Resonance",
							"parameter_info": "Filter resonance: a peak at the cutoff. Default 30%."
						}
					},
					"annotation_name": "Resonance",
					"annotation": "Filter resonance: a peak at the cutoff. Default 30%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-223",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1344.0,
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
					"text": "prepend reso",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-225",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1348.0,
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
					"id": "obj-226",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1350.0,
						100.0,
						22.0
					],
					"text": "prepend reso",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-227",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1648.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "env_amount",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						148.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Env Amount",
							"parameter_shortname": "Env",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Env Amount",
							"parameter_info": "How far the envelope opens the cutoff: up to +6 octaves at 100%. Default 50%."
						}
					},
					"annotation_name": "Env Amount",
					"annotation": "How far the envelope opens the cutoff: up to +6 octaves at 100%. Default 50%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-228",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1354.0,
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
					"id": "obj-229",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1356.0,
						100.0,
						22.0
					],
					"text": "prepend envamt",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-230",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1358.0,
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
					"id": "obj-231",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1360.0,
						100.0,
						22.0
					],
					"text": "prepend envamt",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-232",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1716.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "key_track",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						216.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Key Track",
							"parameter_shortname": "Key",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Key Track",
							"parameter_info": "How much the cutoff follows the note played, around middle C; 100% = fully. Default 50%."
						}
					},
					"annotation_name": "Key Track",
					"annotation": "How much the cutoff follows the note played, around middle C; 100% = fully. Default 50%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-233",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1364.0,
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
					"id": "obj-234",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1366.0,
						100.0,
						22.0
					],
					"text": "prepend keytrack",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-235",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1784.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "velocity_filter",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						284.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Velocity Filter",
							"parameter_shortname": "Vel",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								50.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Velocity Filter",
							"parameter_info": "How much velocity scales Env Amount: 0 = not at all, 100% = fully. Velocity always sets the loudness. Default 50%."
						}
					},
					"annotation_name": "Velocity Filter",
					"annotation": "How much velocity scales Env Amount: 0 = not at all, 100% = fully. Velocity always sets the loudness. Default 50%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-236",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1370.0,
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
					"id": "obj-237",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1372.0,
						100.0,
						22.0
					],
					"text": "prepend velfilt",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-238",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1876.0,
						1028.0,
						280.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"env"
					],
					"presentation": 1,
					"presentation_rect": [
						376.0,
						28.0,
						280.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Envelope",
					"annotation": "The envelope in mint: attack, decay to Sustain, a held stretch, then release. Times are on a squashed scale and include the Length macro.",
					"varname": "view_env",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-239",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1876.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "attack",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						376.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Attack",
							"parameter_shortname": "Attack",
							"parameter_type": 0,
							"parameter_mmin": 0.5,
							"parameter_mmax": 4000.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								2.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 3.0,
							"parameter_annotation_name": "Attack",
							"parameter_info": "Envelope attack, 0.5 ms to 4 s (default 2 ms). One envelope for amp and filter."
						}
					},
					"annotation_name": "Attack",
					"annotation": "Envelope attack, 0.5 ms to 4 s (default 2 ms). One envelope for amp and filter.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-240",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1378.0,
						100.0,
						22.0
					],
					"text": "prepend atk",
					"outlettype": [
						""
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
					"text": "prepend atk",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-242",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						1946.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "decay",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						446.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Decay",
							"parameter_shortname": "Decay",
							"parameter_type": 0,
							"parameter_mmin": 5.0,
							"parameter_mmax": 6000.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								260.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 3.0,
							"parameter_annotation_name": "Decay",
							"parameter_info": "Envelope decay to Sustain, 5 ms to 6 s (default 260 ms). Length scales it."
						}
					},
					"annotation_name": "Decay",
					"annotation": "Envelope decay to Sustain, 5 ms to 6 s (default 260 ms). Length scales it.",
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
					"text": "prepend dec",
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
					"text": "prepend dec",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-245",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2016.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "sustain",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						516.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Sustain",
							"parameter_shortname": "Sustain",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Sustain",
							"parameter_info": "Envelope level while the note is held. Default 0: a stab."
						}
					},
					"annotation_name": "Sustain",
					"annotation": "Envelope level while the note is held. Default 0: a stab.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-246",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1390.0,
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
					"text": "prepend sus",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-248",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1394.0,
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
					"id": "obj-249",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1396.0,
						100.0,
						22.0
					],
					"text": "prepend sus",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-250",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2086.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "release",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						586.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Release",
							"parameter_shortname": "Release",
							"parameter_type": 0,
							"parameter_mmin": 5.0,
							"parameter_mmax": 6000.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								240.0
							],
							"parameter_unitstyle": 2,
							"parameter_exponent": 3.0,
							"parameter_annotation_name": "Release",
							"parameter_info": "Envelope fade after the note ends, 5 ms to 6 s (default 240 ms). Length scales it."
						}
					},
					"annotation_name": "Release",
					"annotation": "Envelope fade after the note ends, 5 ms to 6 s (default 240 ms). Length scales it.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-251",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1400.0,
						100.0,
						22.0
					],
					"text": "prepend rel",
					"outlettype": [
						""
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
					"text": "prepend rel",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-253",
					"maxclass": "jsui",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						2180.0,
						1028.0,
						268.0,
						64.0
					],
					"outlettype": [
						""
					],
					"filename": "2sl-stab-view.js",
					"jsarguments": [
						"drive"
					],
					"presentation": 1,
					"presentation_rect": [
						680.0,
						28.0,
						268.0,
						64.0
					],
					"border": 0,
					"annotation_name": "Drive",
					"annotation": "The saturation curve in mint: input level across (-1 to +1, full scale), output up on the same scale. More Drive bends it into a steeper middle and flatter ends, and turns the output down to keep the level about even.",
					"varname": "view_drive",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-254",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						2180.0,
						819.0,
						44.0,
						48.0
					],
					"outlettype": [
						"",
						"float"
					],
					"varname": "drive",
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						680.0,
						119.0,
						44.0,
						48.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Drive",
							"parameter_shortname": "Drive",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 100.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								25.0
							],
							"parameter_unitstyle": 5,
							"parameter_exponent": 1.0,
							"parameter_annotation_name": "Drive",
							"parameter_info": "Tape saturation on the voices, before the echo. Default 25%."
						}
					},
					"annotation_name": "Drive",
					"annotation": "Tape saturation on the voices, before the echo. Default 25%.",
					"hidden": 1
				}
			},
			{
				"box": {
					"id": "obj-255",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1408.0,
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
					"id": "obj-256",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1410.0,
						100.0,
						22.0
					],
					"text": "prepend drive",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-257",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1412.0,
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
					"text": "prepend drive",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-259",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1416.0,
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
					"id": "obj-260",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1418.0,
						100.0,
						22.0
					],
					"text": "prepend tone",
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "obj-261",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						1300.0,
						1420.0,
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
					"id": "obj-262",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						1360.0,
						1422.0,
						100.0,
						22.0
					],
					"text": "prepend len",
					"outlettype": [
						""
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
					"text": "prepend page",
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
						1
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
						"obj-6",
						0
					],
					"destination": [
						"obj-14",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-14",
						0
					],
					"destination": [
						"obj-15",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-5",
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
						"obj-6",
						2
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
						"obj-6",
						1
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
						"obj-7",
						0
					],
					"destination": [
						"obj-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-8",
						1
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
						"obj-9",
						0
					],
					"destination": [
						"obj-12",
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
						"obj-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-5",
						1
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
						"obj-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-5",
						5
					],
					"destination": [
						"obj-12",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-5",
						5
					],
					"destination": [
						"obj-13",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-5",
						5
					],
					"destination": [
						"obj-15",
						1
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
						"obj-18",
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
						"obj-16",
						2
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-12",
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
						"obj-13",
						0
					],
					"destination": [
						"obj-16",
						1
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
						3
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
						"obj-5",
						0
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
						"obj-20",
						1
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
						"obj-19",
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
						"obj-22",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-20",
						1
					],
					"destination": [
						"obj-22",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-24",
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
						"obj-26",
						0
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
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-24",
						1
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
						"obj-28",
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
						"obj-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-24",
						1
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
						0
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
						"obj-33",
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
						"obj-24",
						1
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
						"obj-24",
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
						"obj-34",
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
						"obj-35",
						0
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
						"obj-37",
						1
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
						"obj-26",
						1
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
						"obj-29",
						1
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
						"obj-32",
						1
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
						"obj-42",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-42",
						2
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
						"obj-42",
						1
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
						"obj-43",
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
						"obj-42",
						0
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
						"obj-37",
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
						"obj-20",
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
						"obj-45",
						0
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
						"obj-46",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-46",
						7
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
						"obj-47",
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
						1
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
						"obj-50",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-48",
						1
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
						"obj-49",
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
						"obj-50",
						0
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
						"obj-51",
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
						"obj-39",
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
						"obj-20",
						0
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
						"obj-23",
						0
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
						"obj-53",
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
						1
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
						"obj-53",
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
						"obj-61",
						0
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
						"obj-53",
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
						"obj-53",
						0
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
						"obj-20",
						0
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
						1
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
						"obj-53",
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
						"obj-69",
						0
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
						"obj-16",
						0
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
						"obj-20",
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
						"obj-3",
						1
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
						"obj-16",
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
						"obj-79",
						0
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
						"obj-16",
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
						"obj-3",
						2
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
						"obj-3",
						3
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
						"obj-93",
						0
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
						"obj-3",
						1
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
						"obj-3",
						1
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
						"obj-3",
						4
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
						"obj-101",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-105",
						1
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
						"obj-20",
						2
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
						"obj-106",
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
						"obj-106",
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
						"obj-20",
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
						"obj-106",
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
						"obj-20",
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
						"obj-106",
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
						"obj-38",
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
						"obj-121",
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
						"obj-124",
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
						"obj-121",
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
						"obj-20",
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
						"obj-121",
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
						"obj-20",
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
						"obj-133",
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
						"obj-121",
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
						"obj-20",
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
						"obj-121",
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
						"obj-20",
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
						"obj-141",
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
						"obj-121",
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
						"obj-20",
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
						"obj-146",
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
						"obj-121",
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
						"obj-16",
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
						"obj-147",
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
						"obj-16",
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
						"obj-151",
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
						"obj-16",
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
						"obj-16",
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
						"obj-161",
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
						"obj-151",
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
						"obj-16",
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
						"obj-151",
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
						"obj-16",
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
						"obj-172",
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
						"obj-16",
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
						"obj-16",
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
						"obj-168",
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
						"obj-16",
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
						"obj-168",
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
						"obj-16",
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
						"obj-16",
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
						"obj-16",
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
						"obj-16",
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
						"obj-193",
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
						"obj-168",
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
						"obj-198",
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
						"obj-168",
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
						"obj-201",
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
						"obj-193",
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
						"obj-151",
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
						"obj-168",
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
						"obj-17",
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
						"obj-193",
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
						"obj-151",
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
						"obj-168",
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
						"obj-209",
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
						"obj-16",
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
						"obj-212",
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
						"obj-193",
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
						"obj-215",
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
						"obj-16",
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
						"obj-193",
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
						"obj-220",
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
						"obj-16",
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
						"obj-218",
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
						"obj-223",
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
						"obj-16",
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
						"obj-226",
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
						"obj-218",
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
						"obj-16",
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
						"obj-231",
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
						"obj-218",
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
						"obj-234",
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
						"obj-16",
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
						"obj-237",
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
						"obj-16",
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
						"obj-16",
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
						"obj-238",
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
						"obj-16",
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
						"obj-238",
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
						"obj-16",
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
						"obj-248",
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
						"obj-238",
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
						"obj-16",
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
						"obj-238",
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
						"obj-256",
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
						"obj-20",
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
						"obj-253",
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
						"obj-259",
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
						"obj-218",
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
						"obj-238",
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
						"obj-52",
						0
					]
				}
			}
		]
	}
}