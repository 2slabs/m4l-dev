// ---- the 2sl-dsp kit's transport clock (templates/transport-clock.template.js) -------------------
// The patch sends `tick <ticks>` on every 16th while Live plays: a [metro 16n @quantize 16n] bang asks
// [transport] for Live's song position in ticks (480 per quarter note, whatever the time signature). Every 16th
// of the song is played exactly once: a second bang on the same 16th is ignored, and a bang between 16ths (the
// metro's immediate bang when Live starts mid-16th) plays nothing, since that 16th began before we heard it.
// The script that includes this defines DEVICE_NAME, `playing` (Live's transport, 0/1) and
// playSixteenth(songSixteenth); it calls clockTick(ticks) on `tick` and resetClock() when Live starts or stops.
var TICKS_PER_SIXTEENTH = 120;        // Max: 480 ticks per quarter note
var ON_SIXTEENTH_TOLERANCE = 0.25;    // a bang within a quarter of a 16th of one is on it (clock jitter)
var lastPlayedSixteenth = null;       // song position (in 16ths) of the last 16th played while Live plays

function clockTick(ticks) {
  if (!playing) return;
  if (!isFinite(ticks)) {
    error(DEVICE_NAME + ": the clock got a song position of " + ticks + " ticks: 16th skipped\n");
    return;
  }
  var position = ticks / TICKS_PER_SIXTEENTH;
  var nearest = Math.round(position);
  if (Math.abs(position - nearest) > ON_SIXTEENTH_TOLERANCE) {
    lastPlayedSixteenth = Math.floor(position);
    return;
  }
  if (nearest === lastPlayedSixteenth) return;
  if (lastPlayedSixteenth !== null && nearest > lastPlayedSixteenth + 1) {
    post(DEVICE_NAME + ": the song position jumped from 16th " + lastPlayedSixteenth + " to " + nearest +
         " (a locate, or a late clock): the 16ths between were not played\n");
  }
  lastPlayedSixteenth = nearest;
  playSixteenth(nearest);
}

/** Live started or stopped: the next tick starts afresh. */
function resetClock() { lastPlayedSixteenth = null; }
// ---- end of the kit's transport clock ------------------------------------------------------------
