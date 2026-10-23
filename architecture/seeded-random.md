# The seeded random

Every random thing a device does (a stab firing on a step, a voicing, a throw, a random modulator's next value) is
`randomNext()` in its brain: the next number in [0, 1) of one sequence per device, which **Seed** starts.
**Loop** makes the randomness repeat. User, 2026-10-18: "if it wants a random number (do I play a different chord
and if so what chord) is a random.next() call and then it has the new number"; "some way to set the length to
random reset (how many bars until we go back to the seed restart) and a way to set the seed".

- **The generator**: mulberry32 (references/README.md, "Randomness"), in `templates/seeded-sequence.template.js`:
  32-bit integer steps (Math.imul, shifts) that JavaScript does exactly, so Max and node draw the same numbers.
  It is the kit's only generator: a device that needs numbers from a value of its own (2sl drums' random function,
  seeded by its settings) uses `seededSequence(seed)` directly.
- **At audio rate** (gen~, where the brain cannot draw a number a sample): the `SeededWhiteNoise` technique
  (Park-Miller's minimal standard, twosl_dsp/techniques/seeded_white_noise.py) makes the samples, its seed drawn from
  the brain's sequence (`floor(randomNext() * 2147483646)`) and sent to gen~, so its noise starts over with Seed and
  Loop like every other draw. gen~'s own noise() cannot be seeded and is not used for anything a seed must repeat.
- **When it starts over** (`templates/seeded-random.template.js`): when Seed changes; when Live starts playing (so
  play always sounds the same from where it starts); and while Live plays, whenever the song position enters another
  Loop: every Loop bars, counted from the song's start, a bar being 16 16ths (4 beats) whatever Live's time
  signature (the brain's position is Live's ticks, 480 a beat). A locate into another Loop starts it over there too.
  Tempo doesn't matter (the position is in beats). Loop off: never, once Live has started. With Live stopped it
  keeps stepping: what plays then (keys held, a machine on its own clock) draws on.
- **Draws compare against the control** where a control sets a chance (fire if the draw is under Density): turning
  the control thins or thickens what plays. Drawing more or fewer numbers (another chord size, another Density)
  moves every later draw; that is accepted (user).
- **Controls** (`twosl_dsp/seeded_random.py`): Seed, 0-999 (a float with Live's Int unit style, the brain taking the
  nearest whole number: the Live preset writer knows only float and enum parameters), a live.numbox in the row band
  (`seed_control`) or a live.dial in the dial band (`seed_dial`); the two are one parameter to Live (its long name,
  range and unit), so a device moving between them keeps its sets' Seed and automation, and only the lock's maxclass
  changes; and Loop, a
  live.menu (off, 1 bar ... 64 bars). The kit names them and writes their Info text; each device places them where
  its randomness is. Both are saved in presets (Init: Seed 0, Loop 16 bars, unless a device's preset book says
  otherwise).
- **The device's part**: include `/*SEEDED_RANDOM*/` in the brain; pass control messages to
  `seededRandomMessage`; call `seededRandomTransport(playing)` on Live starting or stopping and
  `seededRandomAtSongSixteenth(n)` on each 16th of the song it plays, before anything draws there.
- **Drawing ahead**: a brain that draws numbers before they are used (2sl gate holds its next hits' draws in its gen~
  core, so a sequencer pulse there has its own draw at its sample) reads `seededRandomStarts()`, the count of times
  the sequence started over, and draws its held numbers again when it changes, so they come from the new start.
