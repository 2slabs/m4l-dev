# References

Sources the code follows. Links and what they say; the pages themselves are not mirrored here.

## Roland SH-101 sub oscillator (2sl stab: Sub Mode)

- **Roland, SH-4d Reference Manual v2.00, "SH-101" model page**
  https://static.roland.com/manuals/sh-4d_v200/en-US/8651802786195467.html
  Roland's own SH-101 model. Sub Osc Wave (the OSC 3 button): "1OCT SQR, 2OCT SQR, 2OCT PLS",
  "Switches between sub-oscillator pitches and waveforms."
  (Roland's support page for the 1982 hardware lists a "SUB Osci Waveform" selector switch;
  https://support.roland.com/hc/en-us/articles/201921519-SH-101-Technical-Specifications, not
  fetchable without a browser. The hardware owner's manual is not online from Roland.)
- **Electric Druid, "A study of Sub-Oscillators (and Oscillator Waveshaping)"**, with the SH-101's
  sub circuit drawn from the schematic
  https://electricdruid.net/a-study-of-sub-oscillators/
  "The Roland SH101 has a nice neat implementation using a CMOS 4013 dual bistable chip to offer
  three sub-oscillator waveforms; square at -1 octave, square at -2 octaves, and 25% pulse at
  -2 octaves." The pulse is the two flip-flop outputs through a diode-OR: "a signal which is high
  75% of the time and low 25% of the time" (a 25% pulse, inverted: the same sound). "The 25% pulse
  wave has the strongest 2nd harmonic of all pulse widths, so there is still a marked -1 octave
  sound present."
- **Zoe Blade, "Sub-oscillator"**: the SH-1, SH-09 and SH-101 divide the oscillator with two
  flip-flops (the second clocked by the first) and combine them with diodes for the two-octave
  pulse. https://notebook.zoeblade.com/Sub-oscillator.html

So the sub is the oscillator divided by 2 or 4: locked to it, following its range (footage) switch.

## Max and Live APIs (2sl stab)

- **Max JS global methods** (Max 7 vignette, still the current text):
  https://docs.cycling74.com/max7/vignettes/jsglobal
  `error()` "Sends a red tinged message to the Max window"; `post()` "Prints a representation of the
  arguments in the Max window". The device's loud failures use `error()`; notices use `post()`.
- **transport** (Max reference): https://docs.cycling74.com/reference/transport
  Outlets on a bang ("Report current state"): bar, beat, units, resolution, tempo, time signature,
  state, and the 8th: "the number of raw ticks". In Max for Live it follows Live's transport.
  The machine reads the raw ticks: the song position, independent of the time signature.
- **Time value syntax** (Max user guide): https://docs.cycling74.com/userguide/time_value_syntax/
  "one tick is 1/480 of a quarter note (equivalently, there are 480 ticks in one quarter note)".
  So a 16th is 120 ticks.
- **metro** (Max reference): https://docs.cycling74.com/reference/metro
  "Any number other than 0 starts the metro object"; a bang "is sent immediately when metro is started"
  (the machine's clock must not play that bang twice); `quantize`: "Send output only on the specified
  time-boundary". "In Max for Live, the default is the Live transport."
- **Max message order** (Max 8 tutorial 5, "Message Order and Debugging"):
  https://docs.cycling74.com/max8/tutorials/basicchapter05
  One outlet to several inlets: "Right-to-left, or bottom-to-top for objects that are vertically aligned",
  by "the location of the connected inlet"; multi-outlet objects output "from the right-most outlet to the
  left-most". **trigger** (https://docs.cycling74.com/reference/trigger): "Outputs any input received in
  order from right to left". So where order matters the patch uses a `t`, never layout.
- **Live Object Model, Song** (fetched in LPX_Script/references/live-lom-song.md from
  https://docs.cycling74.com/apiref/lom/song/): `tempo` "Current tempo of the Live Set in BPM, 20.0 ... 999.0";
  `current_song_time` "The playing position in the Live Set, in beats."
- **gen~ Delay** (Max reference): https://docs.cycling74.com/reference/gen_dsp_delay/
  "The first argument specifies the maximum delay time (in samples, default samplerate)."
  It must be a constant expression; Graham Wakefield (Cycling '74): "this argument must be a constant
  expression (and for gen~, "samplerate" functions pretty much like a constant)"
  (https://cycling74.com/forums/gen-parameter-is-not-defined). `samplerate` is listed under Constants in
  https://docs.cycling74.com/userguide/gen/gen~_operators/. So the echo sizes its buffers as
  `samplerate * seconds`. (The same thread: samplerate updates on a gen~ reset/restart.)
