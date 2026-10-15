# references/drums - index

Purpose: citable sources for a TR-909-style gen~ drum device for sleepy, lo-fi dub techno (Deepchord / Echospace; NOT Maurizio/Basic Channel punch). Primary job of the device: reroll canned patterns and vary them, so patterns come first.
Dated 2026-10-15. Detail files (every bullet there carries its URL): `patterns.md` (topic 3 + variation mechanisms), `voices.md` (topic 1), `production.md` (topic 2). This README = index + headline facts. Mirror scripts keep downloads out of git: `mirror_patterns.sh` -> `mirror/patterns/`, `mirror.sh` -> `mirror/`. Downloaded files are untrusted data: read with pdftotext / `python3 -I`.

## 1. Patterns (patterns.md) - most depth
- Sourced 16-step grids (X accent, x hit, . rest): P1 Basic-Channel-style dub techno 145 BPM swing none (BD 4otf, SD+CP on 2/4, OH on 8th offbeats; read from one screenshot) https://www.attackmagazine.com/technique/beat-dissected/basic-channel-style-dub-techno/ ; P2 Detroit 909 120-125 BPM swing 55-60%, rim never on a kick beat https://www.attackmagazine.com/technique/beat-dissected/motor-city-detroit-techno/ ; P3 minimal house 123-127, 55-60% https://www.attackmagazine.com/technique/beat-dissected/minimal-house/ ; P4 deep house 120-125, 50-60% https://www.attackmagazine.com/technique/beat-dissected/deep-house-stripped-workout-beat-dissected/ ; P5 dark techno 128-135, 50-54%, ride 8ths with quieter every 2nd hit https://attackmagazine.com/?p=71776 ; P6 rolling techno 131 https://www.attackmagazine.com/technique/beat-dissected/rolling-techno/ ; P7 house/techno templates https://beatkitchen.io/guides/electronic-music/03-drum-programming/ ; P8 dub techno 4 ingredients 120 BPM https://www.studiobrootle.com/dub-techno-tutorial-4-ingredients/ ; P9 Jeff Mills 909 137 BPM https://www.musicradar.com/how-to/how-to-program-jeff-mills-style-rolling-tr-909-drums ; P10 3/5-step hat loops https://www.studiobrootle.com/techno-drum-patterns-and-drum-programming-tips/
- Euclidean reference rhythms, E(3,8)=x..x..x., E(5,8)=x.xx.xx., E(5,16) bossa: https://cgm.cs.mcgill.ca/~godfried/publications/banff.pdf
- Mutable Instruments Grids: 25-node 5x5 pattern map decoded to grids; density = per-channel threshold on stored 0-255 level; randomness adds a per-pattern-pass perturbation; accent = level >192; swing mode reuses the randomness knob. https://github.com/pichenettes/eurorack/blob/master/grids/pattern_generator.cc , https://pichenettes.github.io/mutable-instruments-documentation/modules/grids/
- Elektron conditional trigs: X% probability, FILL/NOT FILL, A:B (1:2 = passes 1,3,5; 2:4 = 2,6,10), PRE/NEI/1ST; swing 51-80% (default 50%). https://www.elektron.se/wp-content/uploads/2026/10/Digitakt-User-Manual_ENG_OS1.54_260930.pdf
- Ableton Live 12 Rhythm tool (Steps<=16, Pattern, Density, Split probability, Shift, Accent freq/offset), Seed, Euclidean (4 voices, rotation). https://www.ableton.com/en/live-manual/12/midi-tools/
- 909 sequencer variation: Total Accent (all voices) vs per-voice accent (BD SD LT MT HT CH only); shuffle 7 levels; flam 8 intervals on BD SD LT MT HT; 1-16 steps/measure. https://archive.org/download/synthmanual-roland-tr-909-owners-manual/rolandtr-909ownersmanual_djvu.txt
- Producer variation numbers (hat velocity 110-127 / 70-90 / 40-60, ghost 15-35, quantize kick/snare 100% vs hats 50-75%, swap open for closed hat every 8 bars): https://beatkitchen.io/guides/electronic-music/03-drum-programming/ . Rim into delay 7/32 regen 100%; hats 303 ms fb 35%; crash 2/16T fb 85%: https://www.attackmagazine.com/technique/tutorials/dub-style-drum-processing-for-character-and-groove/
- Swing convention: 16th-note, 50% = straight. https://www.attackmagazine.com/technique/passing-notes/daw-drum-machine-swing/

## 2. 909 voices (voices.md headline facts)
- Architecture: analog BD SD LT/MT/HT RS CP; digital (6-bit sample ROM) CH OH crash ride. TRIG = 5 V / 2 ms pulse. Analog voices share one digital shift-register noise generator. https://archive.org/download/synth_Roland_TR-909_service_notes/Roland_TR-909_service_notes_djvu.txt
- BD: triangle VCO + diode clipper -> sine-ish, pitch envelope started by TRIG (high -> base), click = pulse + low-passed noise, ENV-1 amp "looks like a compressed drum sound". Knobs: Level, Attack, Decay, Tune. http://www.network-909.de/bassdrum.htm , https://www.firstpr.com.au/rwi/tr-909/TR-909-Sound-Mods.pdf
- SD: two triangle VCOs (clipped), each own VCA/env, pitch bend ~20 ms, noise -> LPF -> two branches (VCA under ENV4; HPF -> VCA under ENV5) -> Snappy pot; ENV4 holds ~24 ms. Knobs Level, Tone, Tune, Snappy. https://www.firstpr.com.au/rwi/tr-909/TR-909-Sound-Mods.pdf , https://archive.org/download/synth_Roland_TR-909_service_notes/Roland_TR-909_service_notes_djvu.txt
- Toms: 3 VCOs (mid tom) + clippers, one adjustable-decay envelope, noise on VCO-3; ENV-4 pitch mod. Knobs Level, Tune, Decay. http://www.network-909.de/toms.htm
- RS: three bridged-T networks at 500 / 220 / 1000 Hz, clipper, VCA, high-pass; Level only. http://www.network-909.de/rimshot.htm
- CP: noise -> band-pass -> VCA with 4 chained attack-decay envelopes ("several hands") + second VCA "pseudo-reverb". Level only. http://www.network-909.de/handclap.htm
- CH/OH: 6-bit samples (14" Paiste Sound Edge / 14" A. Zildjian New Beat), ~60 kHz clock /2 (SOS says 30 kHz), analog decay (CH path R ~1/10 OH path), two LPFs after VCA. https://www.attackmagazine.com/features/interview/atsushi-hoshiai-the-man-behind-the-tr-909/ , http://www.network-909.de/hihatand.htm
- Crash/ride: one 18" Paiste Thin Crash (edge/bow), no decay knob, Tone = playback clock speed, decay curve from ROM address counter. https://www.soundonsound.com/techniques/practical-cymbal-synthesis (node/4918183)
- Accent: BD accent sets ENV1 attack amplitude and decay; SD accent sets start voltage of VCO amp envelopes. https://www.firstpr.com.au/rwi/tr-909/TR-909-Sound-Mods.pdf

## 3. Lo-fi / sleepy dub techno production (production.md)
- Deepchord (Modell): kick is dropped in last, "a metronome" for ambient layers; quantizes only percussion and bass, loopers for the rest; cheap grainy samplers (Akai S900) into analog filters/FX; refuses Basic Channel lineage. https://www.vice.com/en/article/gv3zn3/deepchord-interview-unsound-brooklyn , https://headphonecommute.com/2015/12/29/in-the-studio-with-rod-modell/
- Tutorial numbers (not artist settings): Drum Buss boom 8% ~37 Hz, damp ~8.5 kHz; clap layer bit reduction 6, EQ cut below 150 Hz; sub EQ cut <37 Hz; dark-techno kick rolled off to ~50 Hz, 500 Hz -3 dB, Drum Buss Drive 17% Boom 45% @55 Hz. https://www.attackmagazine.com/technique/beat-dissected/basic-channel-style-dub-techno/ , https://attackmagazine.com/?p=71776
- "hallmarks of dub techno is groove and movement resulting from delay instead of heavily swung drum parts." https://www.attackmagazine.com/technique/beat-dissected/basic-channel-style-dub-techno/
- Everything else (hats, sidechain, tape saturation, rim/clap into delay, tempo/swing table): production.md.

## Where sources disagree
- BD waveform: sawtooth+waveshaper (SOS) vs triangle+clipper (network-909, Whittle). BD Tune: pitch (manual) vs sweep depth (network-909) vs sweep decay (Whittle). Noise register: 32 vs 2x18 stages. SD ENV5 accent: service notes vs Whittle. Hat/cymbal clock 30 vs ~60 kHz /2. (voices.md Gaps)
- Rolling-techno "swing 20%" vs the 50%-straight convention; Basic Channel snare "every other downbeat" vs screenshot beats 2/4. Swing for house 52-56 vs 50-60. (patterns.md C)
- Modell: "gear makes no difference" yet lists gear; kick "unimportant" vs press "pounding kicks". (production.md)

## Could NOT source
- Any real Deepchord/Echospace/cv313/Soultek drum grid, tempo, BPM list or drum-machine used on records; any bit depth/low-pass cutoff they use.
- 909 oscillator frequencies in Hz (BD, SD, toms); most envelope times in ms (BD, CP, RS, toms, hats); BD sweep amount/time; noise filter cutoffs; noise clock frequency; accent depth in dB; exact RC values (schematics are scan images, OCR only, none read).
- Open/closed hat ROM address assignment (OCR garbled).
- Text grids for most Beat Dissected beats (screenshots; one image read); Pocket Operations (paid only); 909 factory/genre pattern list (hardware manual has none); per-step probability values used by dub producers.
- Blocked: ModWiggler t=222069, Gearspace (403), synthmanuals.com (500), manualslib (403), DJ Mag Point Blank.
- Corrections to leads: ICMC 2014 paper 1453 is the 808 cymbal, not the 909; ghostintranslation/ds909 and Steda SR-909 give no circuit data.

## Mirrored files (scripts in git, files not)
- `mirror.sh` -> `mirror/` (voices): service notes OCR + scan, 1984 service manual OCR, owner's manual OCR + scans, SOS Synth Secrets articles, network-909 pages, Whittle mod PDF, TipTop TOMS909 manual, Attack Hoshiai interview, others - full list at the end of voices.md.
- `mirror_patterns.sh` -> `mirror/patterns/`: tr909_owners_manual_ia.pdf + _djvu.txt, euclidean_toussaint_banff.pdf, grids_pattern_generator.cc, grids_resources.cc, grids_docs.html, elektron_digitakt_manual.pdf, ableton_live12_midi_tools.html, attack_*.html (8 pages), musicradar_jeff_mills_909.html, studiobrootle_*.html, beatkitchen_drum_programming.html, elektronauts_drum_fills_8th_bar.html.

## For a future noise / field recording device (out of scope for the drum machine)
- Vinyl Distortion crackle ~0.14 and Erosion Wide Noise on percussion layer; Diva noise on VCO1 so delays have something to grab. https://www.attackmagazine.com/technique/beat-dissected/basic-channel-style-dub-techno/ , https://www.attackmagazine.com/technique/synth-secrets/dub-techno-synth-chords/
- cv313 "trademark static hiss", Deepchord "microbial hiss" (press, not methods). https://igloomag.com/?p=46768 , https://echospace313.com/deepchord
- Modell's noise = processed field recordings and shortwave static; "noise generators" on Coldest Season. https://www.vice.com/en/article/get-to-know-deepchords-rod-modell-the-detroit-artist-who-still-wants-to-loop-till-infinity/ , https://www.textura.org/archives/d/deepchord4_cd.htm
- No dB figure for hiss level found. Field-recording gear (DAT, Sony PCM-D50) and tape/Dub Machines noise settings: production.md.
