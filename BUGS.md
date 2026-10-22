# Bugs and notes

## Every device soft clips its output, always (Graham, 2026-10-21)
Every 2sl device ends in the kit's knee soft clip (`m4l_dev/techniques/knee_soft_clip.py`), with no way to turn it off,
and none of them says so on its face. Graham didn't know it was there and doesn't want it as a default.

| device | where | knee |
|---|---|---|
| 2sl stab | `src/stab_dsp.py` `OUTPUT_SOFT_CLIP_KNEE` | 0.8 (about -1.9 dBFS) |
| 2sl drums | `src/drums_dsp.py` (copied as "2sl stab's output stage") | 0.8 |
| 2sl gate | `src/gate_dsp.py`, after Output with the spring and echo in it | 0.8 |
| 2sl filter | `src/filter_dsp.py`, after its limiter | 0.95 (about -0.4 dBFS) |
| 2sl phaser | `src/phaser_dsp.py` | 0.95 |

The stab and filter VST3s are generated from the same cores, so they very likely clip too (not checked in the plugin
source). Not to confuse with the saturation that is the sound and has its own control (stab's Drive, filter's tube
drive, the echoes' tape loops, gate's spring loop).

Decided (Graham, 2026-10-21): no output soft clip, in any device or plugin. "It should 100 not be on everything; if
people want to add a saturate they're welcome to after the plugin." The output is clean; saturation stays only where it
is the sound and has its own control. Every preset's render changes, so the lock and the preset renders move with it.

Done (2026-10-22): no output soft clip in 2sl gate 0.5.3, stab 2.8.0, drums 0.4.0, filter 0.3.0, phaser 0.2.0, and the
stab and filter VST3s (generated from the same cores; neither plugin's own source clipped). Filter keeps its limiter
(its SPEC §1.4, §3.5: a screaming resonance can't blow up a mix; ceiling -0.3 dBFS). The presets' peak checks are now
against full scale (filter: its limiter's ceiling; architecture/presets.md). `knee_soft_clip.py` stays: it is the
Mu-Tron Bi-Phase's op-amp rails inside its feedback loop (zero_delay_allpass_cascade.py's `loop_limit`), the
phaser's sound, not an output stage.
