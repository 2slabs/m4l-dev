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
