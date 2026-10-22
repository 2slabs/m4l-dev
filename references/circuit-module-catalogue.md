# Circuit-module catalogue: which characteristic circuits we actually have the information on

Written 2026-10-20 for the kit's layer 2 (architecture/dsp-blocks.md: techniques -> circuit modules -> instruments).
The user's rule: "filter it down to things we actually have the information on - what do we actually have the schematic
of - and those are the starting building blocks." So this note is a ranking by source quality, not by fame.

Nothing here is mirrored. No file was downloaded into the repo by this note; every link below is a pointer. If a row is
picked as a module, its PDFs go in through a `fetch-<module>-sources.sh` with sha256 checks (like fetch-dsp-sources.sh),
into a gitignored mirror, and that module's own note replaces the row's labels with page-level quotes.

## Labels, and how much was read

- **[VERIFIED]** read in the source text this session.
- **[SECONDARY]** stated by a page or search result I saw this session but not the primary source (e.g. a wiki page, a
  search-result abstract). The link was status-checked or surfaced by search, the claim not checked against the primary.
- **[UNVERIFIED]** from my memory of the field (weights, "statistical"). Needs a source before the module is built.
- **[INFERENCE]** my reading, not a source's statement.

What was actually read this session: the whole table of contents and the passages of Zavalishin, *The Art of VA Filter
Design* 2.1.2 (the local copy in `dsp-sources/` has the same sha256) that name the structures below; the sdiy.info wiki
pages for CEM3340, SSM2040, SSM2044, IR3109, CA3080, SSM2164; the Stinchcombe diode-ladder page header; search-result
abstracts for the DAFx / AES / MDPI papers (titles, authors, venues, one-line scope; the papers themselves not read
except where marked). HTTP reachability was checked with curl for the PDFs marked (200). Many electrosmash.com pages did
not answer from this machine, so none are cited as checked.

**Source score** (0-3): 0 = no circuit info; 1 = a description or a block diagram only; 2 = circuit documentation (a
schematic or a chip datasheet with internal/application circuit) OR a published model, not both; 3 = circuit documentation
AND a published model of that circuit. For discrete circuits there is no datasheet; a service manual or patent schematic
stands in for it. A 3 means "we can build it from sources", not "it is easy".

**"Measurable"**: I do not know what hardware or plugins the user owns beyond what memory records (ER-1, Microtonic,
Jomox, ADX1, Drumazon are drum-matcher targets). So the column says what kind of reference is plausible; plugin
emulations are other people's models, useful as a listening reference only, never as ground truth. Ask the user which
hardware exists before using any of it. [INFERENCE]

**Already in the 2slabs repos** is marked **[MODELLED]**.

## 1. Oscillators / VCO cores

| circuit | classic instruments | what makes its sound | schematic | datasheet | published models / analyses | measurable | score |
|---|---|---|---|---|---|---|---|
| CEM3340 / CEM3345 (and Alfa AS3340) | Prophet-5 rev3, OB-Xa and Oberheim line, many Sequential / Moog Memorymoog-era synths [UNVERIFIED list] | Self-contained VCO; exponential + linear control, tri / saw / square / PWM, hard and soft sync, full temperature compensation, hi-frequency track trim [SECONDARY: https://sdiy.info/wiki/CEM3340]. Sound: saw from a ramp-core with a reset time and slight curvature; [UNVERIFIED] | datasheet application circuits; synth schematics (Prophet-5 service manual) [UNVERIFIED which archives] | yes: Electric Druid mirrors it, CEM3340 + 3345 (200) https://electricdruid.net/wp-content/uploads/2020/02/CEM33403345-VCO.pdf; product page https://electricdruid.net/product/cem3340-vco-rev-g/; Alfa AS3340 on alfarzpp.lv [UNVERIFIED URL] | no chip-specific paper found. Generic: Valimaki & Huovilainen CMJ 2006; polyBLEP Valimaki et al. JASA 2012 (local: dsp-sources/valimaki-polyblep-jasa2012.pdf, kit already follows) | plugin emulations of Prophet / OB (reference only) | 2 |
| SSM2030 | not established [UNVERIFIED] | Dual-VCO chip family from SSM; character = the saw with its ramp core quirks [UNVERIFIED]. | synth schematics only [UNVERIFIED] | the sdiy.info page for SSM2030 returned 404; datasheet existence [UNVERIFIED] | none found | no | 1 |
| Moog 921 / 921A oscillator | Moog modular, Minimoog (discrete core) [UNVERIFIED] | Discrete exponential converter + ramp core, waveshaped from saw; the "fat" is the tracking/instability and the shaped waveforms [UNVERIFIED] | Moog modular schematics circulate; archive location [UNVERIFIED] | n/a (discrete) | none found | Minimoog / modular hardware if owned | 1 |
| Roland discrete saw cores (Juno-6/60, Jupiter-4 era) | Juno-6/60, Jupiter-4, SH-101 [SECONDARY via https://sdiy.info/wiki/IR3109 for filter only; oscillator part UNVERIFIED] | Juno-6/60 / Jupiter-4: analog saw+pulse+sub from a ramp core. | service manuals on community archives (Juno-106 manual listed at https://emusic-diy.org/rolandmanuals, https://el34world.com/charts/Schematics/Files/Roland/Roland_Schematics.htm) [SECONDARY, results listed, files not opened] | n/a | none specific found | TAL-U-No-LX type plugin (UNVERIFIED) | 1 |
| Buchla 259 sine core + modulation oscillator | Buchla 259, Easel / 200e family | Triangle -> sine shaper (Buchla-style sine), FM through the modulation oscillator, then the folder | **[MODELLED]** the kit modules buchla_259_principal_oscillator.py, buchla_259_modulation_oscillator.py, buchla_259_timbre_section.py; circuits/buchla-259.md | see that note | Esqueda, Pontynen, Parker, Bilbao, DAFx-17, "Virtual Analog Buchla 259 Wavefolder" https://dafx.de/paper-archive/details/zmNQ8s5sZVhM_ObMB_D8tg ; Theelen 259 timbre note (in circuits/sources) | Buchla / Easel hardware if owned | 3 |
| Serge VCO (dual) | Serge modular [UNVERIFIED] | Triangle core with waveshaping to sine / saw; the Serge sound is mostly the system (DUSG, wave multipliers) | Stinchcombe's site has a "Serge VCS" page, https://www.timstinchcombe.co.uk/ (menu entry listed, content not read) [SECONDARY] | n/a | wavefolder part: Esqueda et al. 2017 (section 3 below) | no | 1 |

Instrument columns for rows without a source are my recollection; do not build from them.

## 2. Filters

Zavalishin 2.1.2 TOC [VERIFIED, local copy]: ch.4 SVF (analog model 4.1, resonance 4.2, digital model 4.4, further types
4.7); ch.5 ladder (5.1-5.7 incl. multimode, HP, BP), 5.8 Sallen-Key filters (SKF and transposed SKF), 5.9 8-pole ladder,
5.10 diode ladder; ch.6 nonlinearities incl. 6.3 feedback loop saturation, 6.9 saturation in 1-pole filters, "OTA ladder
1-poles" (around p.201, Fig. 6.35), nonlinear Sallen-Key (Fig. 6.10) vs transposed Sallen-Key (Fig. 6.11) with the remark
that they "significantly differ" in sound. The text does not name the MS-20, Korg 35, SEM, TB-303 or Roland products
(grep for those names, no hits except Moog); mapping the structures to those instruments is **[INFERENCE]** (and
well established in the field, but not in this book).

Tim Stinchcombe's site (https://www.timstinchcombe.co.uk/) has: Moog ladder transfer function PDF (200)
https://www.timstinchcombe.co.uk/synth/Moog_ladder_tf.pdf ; a Korg MS10/20 filter study (200)
https://www.timstinchcombe.co.uk/synth/MS20_study.pdf ; a Diode Ladder Filters page (200)
https://www.timstinchcombe.co.uk/index.php?pge=diode ("Diode Ladder Filters (including the pretension to 18dB)");
"Moog paper refs"; "Serge VCS". Contents not read beyond headers this session. [SECONDARY]

| circuit | classic instruments | what makes its sound | schematic | datasheet | published models / analyses | measurable | score |
|---|---|---|---|---|---|---|---|
| Moog transistor ladder | Minimoog, Moog modular 904A, Moog One lineage; copied everywhere | 4 cascaded transistor-pair 1-poles with global feedback; resonance up to k=4 self-oscillation, passband drops at high resonance, tanh-like stage saturation [VERIFIED Zavalishin 5.1-5.4, also in dsp.md] | patent US3475623 https://patents.google.com/patent/US3475623A (200) ; Minimoog schematics widely circulated [UNVERIFIED] | n/a (discrete) | Huovilainen DAFx-04 (200) https://dafx.de/paper-archive/2004/P_061.PDF ; Stinchcombe PDF above; Zavalishin ch.5-6; Valimaki & Huovilainen 2006; D'Angelo & Valimaki ICASSP 2013 and IEEE TASLP 2014 "generalized Moog ladder" [UNVERIFIED venues]; Fontana ICMC 2007 [UNVERIFIED] | any Minimoog-ladder plugin as listening reference | **3**; MODELLED 2026-10-20: m4l_dev/circuit_modules/moog_transistor_ladder.py, references/circuits/moog-transistor-ladder.md (patent, Minimoog and 904A sheets, Stinchcombe, Huovilainen, Stilson & Smith, D'Angelo & Valimaki Part I read; the ICASSP 2013 paper and Part II not obtained) |
| TB-303 / Roland diode ladder (also EMS VCS3 / Synthi-type) | TB-303, TD-3 etc.; EMS Synthi / VCS3 variant (Stinchcombe + Fontana & Civolani 2010) | 4-pole diode ladder; poles not identical (gain compensation weak), 18 dB feel, coupling-cap high-pass adds poles and a high-pass in the resonance loop, flattish bumpy passband [SECONDARY: search abstracts quoting Stinchcombe; a1k0n/303 repo measured on x0xb0x] | 303 service manual (community archives) [UNVERIFIED location]; Stinchcombe page has analysis from the schematic [SECONDARY] | n/a | Stinchcombe diode ladder page; Zavalishin 5.10 [VERIFIED present]; a1k0n/303 https://github.com/a1k0n/303 (surfaced by search, not read) | TB-303 clone hardware if owned | **3** |
| Roland IR3109 (and BA662 cousins, IR3R05) | Juno-6/60, Jupiter-4 (early: matched BA662 + FET buffers), Jupiter-6/8, JX-3P, MKS-30, MKS-80, SH-101, MC-202, Boss PH-2 [SECONDARY, https://sdiy.info/wiki/IR3109] | "Four independent buffered OTAs ... single input exponential frequency control": an OTA-ladder 4-pole; soft saturation per stage [SECONDARY / VERIFIED structure: Zavalishin OTA ladder 1-poles, p.201] | service manuals (Juno-60 / Jupiter-8 on community archives, https://emusic-diy.org/rolandmanuals; files not opened); AMSynths AM8109 and Shruthi-1 board are open designs (DIY projects listed on sdiy page) | IR3109 datasheet not found by search; Alfa AS3109 clone exists, datasheet via alfarzpp.lv or Electric Druid page on AS3109 filter designs [UNVERIFIED URL] | Zavalishin OTA ladder (structure only); Werner et al. DAFx-17 OTA circuits in WDF [UNVERIFIED venue]; nothing IR3109-specific found | Juno-60-type plugins (reference only) | 2 |
| SSM2040 | Prophet-5 rev1/2, others | 4-pole filter, exponentially controlled 10 000:1; "resonance and small amounts of soft distortion when overdriven" [SECONDARY, https://sdiy.info/wiki/SSM2040] | clones and schematics section on the wiki; chip datasheet [UNVERIFIED location] | datasheet not found by search (Analog Devices URL unreachable from this machine) | none found | no | 1 |
| SSM2044 | Korg Poly-6, Monopoly, Trident; PPG Wave 2.2/2.3, E-mu Emulator, SP-12, SP-1200, Drumulator, Ensoniq SDP-1, Simmons SDS5, Crumar Bit 01/99, Doepfer A-105, Shruthi-1 [SECONDARY, https://sdiy.info/wiki/SSM2044] | 4-pole LP optimised OTA-style filter; samplers' "dirty" filter [INFERENCE from the instruments list] | wiki lists remakes (SSI2144); datasheet location [UNVERIFIED] | not located | none found | Emulator / SP-1200 / PPG plugin emulations (reference only) | 1 |
| CEM3320 | Prophet-5 rev3, OB-Xa (2 per voice per one forum post: unverified), SCI Pro-One, Six-Trak [SECONDARY: https://presetpatch.com/articles/synths-using-cem-3320-vcf-filter] | 4-pole OTA filter (Curtis gain cell, internal temperature compensation); LP / HP / BP configurations [SECONDARY] | datasheet circuits redrawn at https://electricdruid.net/cem3320-filter-designs (200), compared with Pro-One and OB-Xa implementations [SECONDARY] | datasheet exists (as redrawn above); direct PDF not found | no chip-specific paper; structurally the OTA ladder in Zavalishin | Prophet / OB plugins | 2 |
| Korg MS-20 filter (and Korg35 / MS-10) | MS-10, MS-20, Korg 35 [UNVERIFIED] | Sallen-Key topology; sharp resonance, harsh overload, the "screaming" HP/LP pair; MS-20 revisions differ (OTA vs diode-limited, see Stinchcombe) [UNVERIFIED sound claims; INFERENCE linking MS-20 to Zavalishin 5.8 and the 6.10 nonlinear SK] | MS-20 service manual widely circulated [UNVERIFIED]; Stinchcombe MS10/20 study from schematic | n/a | Stinchcombe MS20_study.pdf (200); Zavalishin 5.8 + 6.10-6.11 [VERIFIED]; Pirkle app notes [UNVERIFIED] | Korg MS-20 mini / plugin reference | **3** [INFERENCE for the score: study + service manual + SK nonlinear model] |
| Oberheim SEM SVF | SEM, OB-X lineage [UNVERIFIED] | 2-pole state-variable, simultaneous LP/BP/HP, notch by summing; the 12 dB open feeling; OTA-based integrators (in the SEM; per a course page, GaTech EMS homework) [SECONDARY: https://lanterman.ece.gatech.edu/?p=149 surfaced by search] | SEM schematics (GaTech page links them) [SECONDARY] | n/a | Zavalishin ch.4 SVF [VERIFIED structure] (kit has gen_state_variable.py already); no SEM-specific nonlinear paper found | Arturia SEM Filter plugin (reference) | 2 |
| ARP 4072 / 4075 / 4012 ladder | ARP 2600, Odyssey, Pro Soloist, Quadra [UNVERIFIED] | Moog-like ladder variants (4012 / 4072 / 4075 differ in RC and resonance, 4072 = 2600 filter) [UNVERIFIED] | ARP 2600 schematics well circulated [UNVERIFIED] | n/a (discrete) | no filter-specific paper found; shares the Moog ladder math | ARP 2600 hardware / reissue | 1 |
| Steiner-Parker (Synthacon) | Steiner-Parker Synthacon, Minicon | 2-pole Sallen-Key multimode; "more controllable resonance" in Vult's modelling (vendor claims) [SECONDARY: https://en.wikipedia.org/wiki/Steiner-Parker_Synthacon via search] | schematic availability [UNVERIFIED] | n/a | no paper found; Vult Tangents is vendor marketing only | Vult plugin | 1 |
| Polivoks filter | Polivoks | Programmable op-amp filter, "distinctive and gritty" [SECONDARY, Cherry Audio vendor text] | schematic circulated [UNVERIFIED] | n/a | no paper found (vendor only) | Cherry Audio Atomika / Filtomika plugin (reference) | 1 |
| EDP Wasp VCF | EDP Wasp | Odd state-variable with highly nonlinear / dynamic behaviour [SECONDARY] | Stinchcombe's site lists "EDP Gnat schematics" [SECONDARY] | n/a | Koper, Holters, Esqueda, Parker, DAFx-22 "A Virtual Analog Model of the EDP Wasp VCF" https://dafx.de/paper-archive/details/MX0iFIRDuNA243d0W4x7Lg | Wasp hardware or clone if owned | 2 (schematic of Gnat is the Wasp's sibling, so close to 3 after reading the paper) |
| Buchla 292 low pass gate (vactrol) | Buchla 292, 200e, Easel | Vactrol photo-resistor memory (non-linear, level-dependent decay), VCA + filter in one | **[MODELLED]** the kit module buchla_292_low_pass_gate_channel.py; circuits/buchla-292-low-pass-gate.md | VTL5C3 datasheet (in circuits/sources) | Parker & D'Angelo DAFx-13; Najnudel et al. DAFx-23 (in sources) | Buchla / Make Noise hardware if owned | 3 |
| MF10 / LTC1060 switched-capacitor | Sherman filterbank, other boards [UNVERIFIED] | Clocked SC filter: clock feedthrough, aliasing of the clock, stepped response | **[MODELLED]** ~/2slabs/2sl-filter/references/sherman-filterbank.md | LTC1060, MF10 in dsp.md (fetched) | see the Sherman note | Sherman hardware if owned | 3 |

## 3. VCAs, shapers, folders, clippers

| circuit | classic instruments | what makes its sound | schematic | datasheet | published models / analyses | measurable | score |
|---|---|---|---|---|---|---|---|
| Roland BA662 (OTA VCA) | Jupiter-4 (matched BA662 with FET buffers), Juno-6/60 VCA [SECONDARY on IR3109 page; BA662 detail UNVERIFIED] | OTA: soft tanh-like non-linearity, control-feedthrough thump [INFERENCE] | service manuals | not found (sdiy page 404) | OTA in WDF: Werner et al. DAFx-17 [UNVERIFIED venue]; Zavalishin ch.6 tanh stage | no | 1 |
| CA3080 / LM13700 OTA | everywhere (Doepfer A135, SEM, countless) [SECONDARY] | tanh differential pair; linearising diodes for the LM13700 | n/a | LM13700 TI (200) https://www.ti.com/lit/ds/symlink/lm13700.pdf ; CA3080 sdiy page https://sdiy.info/wiki/CA3080 (CA3080 discontinued 2005) | tanh: Zavalishin 6.x; WDF OTA [UNVERIFIED] | any OTA module | 2 |
| CEM3360 / Alfa AS3360 dual VCA | Prophet-5 rev3, OB-Xa [UNVERIFIED] | clean exponential VCA with some control feedthrough [UNVERIFIED] | datasheet application circuit [UNVERIFIED] | Alfa AS3330 (similar dual VCA) datasheet seen via ericasynths.lv, link 404 now | none | no | 1 |
| SSM2164 / THAT 2180 VCA | 1980s-90s synths and mixers; Eurorack VCAs [SECONDARY, https://sdiy.info/wiki/SSM2164] | Clean: "100 dB dynamic range and 0.02% THD", -33 mV/dB control [SECONDARY]; the "sound" is no sound | n/a | THAT 2180 series (200) https://www.thatcorp.com/datashts/THAT_2180-Series_Datasheet.pdf ; SSM2164 data sheets via sdiy | none needed | no | 2 (but not characteristic: the clinical VCA, which has value as the control) |
| Vactrol cell | Buchla 292, many LPGs | see 292 above | **[MODELLED]** | **[MODELLED]** | **[MODELLED]** | | 3 |
| Buchla 259 wavefolder | 259, 200e | five parallel op-amp folding stages [SECONDARY] | **[MODELLED]** | **[MODELLED]** | Esqueda et al. DAFx-17 | | 3 |
| Serge wavefolder / Lockhart wavefolder | Serge Wave Multipliers, Lockhart fold | Serge and Lockhart give "a very similar effect"; modelled with Lambert-W + first-order antiderivative antialiasing [SECONDARY, from the MDPI abstract] | published in the paper | n/a | Esqueda, Pontynen, Parker, Bilbao, Applied Sciences 7(12):1328 (2017); PDF (200) https://acris.aalto.fi/ws/portalfiles/portal/16820117/esqueda_et_al_applsci_07_01328_v2_1.pdf | Serge / Make Noise hardware if owned | **3** (kit: Bilbao ADAA already in dsp.md) |
| Diode clippers | Tube Screamer, RAT, Fuzz Face lineage, many consoles | symmetric / asymmetric soft clipping; Shockley diode equation | any pedal schematic (public) | diode datasheets (1N4148, 1N34A) [UNVERIFIED] | Yeh, Abel, Smith (DAFx-07, DAFx-08) and Yeh's thesis (200) https://ccrma.stanford.edu/~dtyeh/papers/DavidYehThesissinglesided.pdf ; Werner et al. AES 2015 "improved and generalized diode clipper model" [UNVERIFIED] | any overdrive pedal | **3** (clipper maths; no "famous" single instrument) |
| Diode ring modulator | Moog / Korg / Wasp ring mods, Dalek voice | multiplication artefacts through diode bridge; sound is the bridge's non-ideal | Parker "A simple digital model of the diode-based ring modulator" DAFx-11 [UNVERIFIED venue: the search I ran did not find it; the DAFx-11 PDF number 53_e is a different paper] | n/a | Parker 2011 | Ring-mod hardware | 2 |

## 4. Noise

Noise is a technique-layer item (layer 1), not a circuit module; the 808 noise sources live inside the 808 voices. [INFERENCE]

| circuit | classic instruments | what makes its sound | schematic | datasheet | published models | measurable | score |
|---|---|---|---|---|---|---|---|
| Transistor avalanche (reverse-biased B-E junction) noise source | Moog, Korg, ARP noise, 808 hat/snare noise (808 uses transistor noise) [UNVERIFIED] | near-white, a little pink-tilted by the coupling caps; not Gaussian-perfect | public in every modular's schematic [UNVERIFIED] | n/a | 808 Cymbal paper (below) includes the noise source block | | 2 |
| LFSR digital noise (Atari-style) | [UNVERIFIED] | pitched periodic noise at short registers | n/a | n/a | n/a | | 1 |

## 5. Drum circuits

| circuit | classic instruments | what makes its sound | schematic | datasheet | published models / analyses | measurable | score |
|---|---|---|---|---|---|---|---|
| TR-808 bass drum (bridged-T resonator + pulse trigger shaping) | TR-808 | bridged-T network rings when kicked by a shaped trigger; "physically-informed, circuit-bendable" [SECONDARY, DAFx archive abstract]; the pitch sags because the decay amplitude changes the resonator's effective frequency [UNVERIFIED claim] | 808 service manual [UNVERIFIED]; the paper shows the sub-circuit schematics [SECONDARY] | n/a (discrete) | Werner, Abel, Smith, DAFx-14 (200) https://dafx14.fau.de/papers/dafx14_kurt_james_werner_a_physically_informed,_ci.pdf ; model built in Gen~ (the kit's own environment) [SECONDARY]; Werner's Stanford dissertation uses it as the running example https://purl.stanford.edu/jy057cz8322 | 808 clones/plugins; the kit's drum matcher targets (ER-1/Microtonic/Jomox/ADX1 per memory) | **3** |
| TR-808 cymbal (six square-wave metallic oscillators + bandpass/hp, VCA) | TR-808 cymbal / hat | metallic inharmonic square cluster through a band shaping + envelope [SECONDARY] | in paper | n/a | Werner, Abel, Smith, ICMC/SMC 2014 "The TR-808 Cymbal: a physically-informed, circuit-bendable, digital model" (200) https://speech.di.uoa.gr/ICMC-SMC-2014/images/VOL_2/1453.pdf ; Gen~ model [SECONDARY] | | **3** |
| TR-808 cowbell, clap, snare, toms | 808 | "More Cowbell" (AES 2014) [SECONDARY: CCRMA keyword listing https://ccrma.stanford.edu/papers/keyword/398] | in paper | n/a | cowbell paper; no snare / clap paper found | | 2 |
| TR-909 | TR-909 | sample-based hats/cymbals, analog kick/snare/toms with a different pitch envelope than 808 [UNVERIFIED] | service manual [UNVERIFIED] | n/a | no circuit paper found | Drumazon (909 clone; memory says it covers it) | 1 |

## 6. Modulation, time, and ambience

Local sources already in dsp.md: Downing & Terjesen (RE-201 model, 2016 class paper), Chowdhury DAFx-19 (tape). The
tape echo / RE-201 module's sources are in dsp.md, not repeated here.

| circuit | classic instruments | what makes its sound | schematic | datasheet | published models / analyses | measurable | score |
|---|---|---|---|---|---|---|---|
| BBD (MN3005 / MN3007 / MN3009 etc.) with companding and filters | Boss CE-1/CE-2, Roland Juno-6/60 chorus (MN3009 delay + MN3101 clock driver) [SECONDARY via search of clone vendors], Dimension D (Roland SDD-320; chip assignment UNVERIFIED) | clocked delay line that aliases; input / output low-pass filters mask its artefacts: "Filters sit before and after the BBDs to mask artifacts from the chip" [SECONDARY], noise and companding | Juno-60 service manual; Boss CE-2 schematic (public) [UNVERIFIED] | Panasonic MN3005/3007/3009 datasheets exist [UNVERIFIED location]; sdiy pages for MN3005 / MN3007 were 404 | Raffel & Smith DAFx-10 "Practical modeling of BBD circuits" (200) https://dafx10.iem.at/proceedings/papers/RaffelSmith_DAFx10_P42.pdf ; Holters & Parker DAFx-18 "A combined model for a BBD and its input and output filters" https://dafx.de/paper-archive/details/KbFTgvcTMmHQ2bHZvOUekw (implemented in chowdsp_utils, listed in search) | Juno-60-type plugins; CE-2 pedals | **3** |
| Mu-Tron Bi-Phase | Mu-Tron | LED + photocell phaser, two six-stage op-amp all-pass phasors (ARP drawing 77204); MODELLED 2026-10-20: m4l_dev/circuit_modules/mutron_bi_phase.py, references/circuits/mutron-bi-phase.md | | | | | modelled |
| Uni-Vibe (opto phaser) | Univibe, Shin-ei | 4 allpass stages with LDR + lamp, asymmetric LFO; the lamp-driven photocell = the vactrol story (circuits/buchla-292-low-pass-gate.md) [INFERENCE] | public (electrosmash analysis, not reachable from this machine) [UNVERIFIED] | n/a | no paper checked | | 1 |
| Spring reverb tank | Fender, Hammond, Rhodes amps | dispersive chirp: "chirps" and dripping; dispersion from the helical spring [SECONDARY] | n/a (mechanical, Accutronics datasheets [UNVERIFIED]) | | Bilbao & Parker, IEEE TASLP 2010 "A virtual model of spring reverberation" https://era.ed.ac.uk/handle/1842/3718?show=full ; Parker & Bilbao DAFx-09 "Spring reverberation: a physical perspective" https://dafx.de/paper-archive/details/MBjqiMDVjnAseoN9C-fzBw ; Valimaki, Parker, Abel, "Parametric spring reverberation effect" JAES 2010 (https://aes2.org/publications/elibrary-page/?id=15511); Gamper, Parker, Valimaki DAFx-11 calibration | spring tank hardware if owned | 2; MODELLED 2026-10-21: the techniques dispersive_loop_spring_tank.py (2sl gate's) and parametric_spring_reverb.py (VPA10's chirps, references/dsp.md), the modules buchla_208_spring_reverb.py, accutronics_type_9_spring_tank.py, grampian_636_spring_reverb.py (references/circuits/) |
| Tape echo / RE-201 | Roland RE-201 Space Echo | in dsp.md (Downing & Terjesen; Chowdhury DAFx-19) | | | already in the kit's DSP sources | | see dsp.md |

## 7. What the kit already has (not to rebuild)

- Buchla 259 (one module per schematic sheet): principal oscillator, timbre section (the CA3160 folder), modulation
  oscillator, m4l_dev/circuit_modules/buchla_259_*.py; circuits/buchla-259.md (Esqueda DAFx-17, Theelen, the sheets).
- Buchla 292 LPG + vactrol: m4l_dev/circuit_modules/buchla_292_low_pass_gate_channel.py; circuits/buchla-292-low-pass-gate.md
  (Parker & D'Angelo DAFx-13, Najnudel DAFx-23, VTL5C3).
- LTC1060 / MF10 switched-capacitor (Sherman): the kit module m4l_dev/circuit_modules/ltc1060_mf10_section.py, its
  datasheets in circuits/ltc1060-mf10.md; the instrument's side in ~/2slabs/2sl-filter/references/sherman-filterbank.md.
- The zero-delay ladder (m4l_dev/techniques/zero_delay_ladder_filter.py): a technique, not a chip model.
- The Moog transistor ladder (904A / Minimoog VCF): m4l_dev/circuit_modules/moog_transistor_ladder.py;
  circuits/moog-transistor-ladder.md (US 3,475,623, the Minimoog and 904A sheets, Stinchcombe 2008, Huovilainen
  DAFx-04, Stilson & Smith 1996, D'Angelo & Valimaki 2014 Part I, Zavalishin ch. 5-6).
- The zero-delay state-variable filter (m4l_dev/techniques/zero_delay_state_variable_filter.py): a technique, same
  status; the SEM row would be a module built on it.

## 8. Ranked shortlist: starting base modules

Order: score 3 first, then by number of classic instruments covered, then by how different it sounds from the ones above.
Rank is by source quality and distinctiveness; I have not weighed how hard each is to model or what the user's
instruments need. [INFERENCE throughout.]

1. **Moog transistor ladder** (3) - Minimoog, modular, the entire "ladder" lineage. MODELLED 2026-10-20
   (`MoogTransistorLadder`); the kit's generic ladder technique stays (2sl stab runs on it).
2. **TB-303 diode ladder** (3) - TB-303 plus EMS Synthi / VCS3 variant; clearly different from #1 (weaker resonance
   compensation, coupling-cap high-pass in the loop).
3. **Korg MS-20 / Sallen-Key filter** (3 by inference) - MS-10 / MS-20; the only high-resonance 2-pole, distinct again.
4. **BBD chorus/delay (MN3009-class + filters + clock)** (3) - Juno-6/60 chorus, CE-2, Dimension D lineage, flangers;
   the only modulation module with a full paper trail (two DAFx papers + circuits).
5. **TR-808 voice set (bass drum, cymbal; cowbell)** (3 for bass drum and cymbal, 2 for cowbell) - papers built in
   Gen~; hits the drum matcher directly.
6. **Serge / Lockhart wavefolder** (3) - complements the already-built 259 folder (different characters per the
   paper's finding: Serge and Lockhart are very similar, so one module).
7. **Diode clipper** (3) - small, source-complete, shared by many pedals; useful as the shaper layer for filters.
8. **EDP Wasp VCF** (2, 3 after reading the DAFx-22 paper) - distinctive, one paper, a sibling schematic.
9. **Roland IR3109 OTA ladder** (2) - covers Juno-6/60, Jupiter-4/6/8, SH-101, JX-3P (largest instrument count of any
   row); held back to 2 only because no datasheet and no IR3109-specific model were found, so the project's
   "Roland (IR3109, BA662)" plan step (kit-layers step 5) starts with sources to find, not to read.
10. **Oberheim SEM SVF** (2) - SEM, OB-X lineage; the kit already has the SVF technique, so it is a small step.
11. **Spring reverb tank** (2) - physical-model papers exist (Bilbao/Parker); no electrical circuit needed. MODELLED
    2026-10-21: the Easel's (as 2sl gate had it), the Accutronics type 9 and the Grampian 636, on the parametric spring
    reverb technique (VPA10's chirps); no tank's own dispersion is measured, the Leem Pro's stands in.
12. **CEM3340 VCO core** (2) - the most-used oscillator chip, datasheet in hand; no chip paper, so the oscillator model
    would be generic ramp-core + polyBLEP.

Already built (the base the above extends): 259 sine core + folder, 292 LPG, LTC1060, the spring tanks.

## 9. Biggest gaps

- **Roland family**: no datasheet for IR3109 / BA662 found, no Juno/Jupiter DCO or VCA model paper; the step-5 target
  is a source-hunt.
- **Oscillator chips**: CEM3340 / SSM2030 / Moog 921 / Roland discrete cores have schematics but no chip-level model
  paper; sound character is not documented as numbers.
- **SSM2040 / SSM2044 / CEM3320 / ARP 4072**: wiki pages and redrawn datasheets only; no analysis paper, so no model
  validated against a measured circuit.
- **Polivoks, Steiner-Parker, Univibe**: vendor claims only.
- **909 and 808 snare / clap / toms**: no circuit papers found.
- **VCA character**: BA662 / CEM3360 (what makes the Roland and Curtis VCAs sound like themselves) undocumented.
- **Not checked**: Yeh thesis page numbers; Electrosmash analyses (host unreachable); Huovilainen, Stinchcombe,
  Raffel & Smith, DAFx-14 / ICMC papers were not read, only their existence confirmed; sdiy pages for SSM2030, BA662,
  CEM3360, MN3005, MN3007 returned 404 (so no wiki entry at that address). All instrument lists marked [UNVERIFIED]
  must be sourced before use.
- **Hardware inventory**: the "measurable" column needs the user to say which hardware exists.
