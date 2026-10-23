// ---- the 2sl-dsp kit's seeded random (templates/seeded-random.template.js; architecture/seeded-random.md) ---------
// One generator per device: everything random the device does (a stab firing, a voicing, a throw, a random
// modulator's next value) is randomNext(), the next number of the sequence Seed starts. Loop starts it over:
//   - while Live plays, whenever the song position enters another Loop (every Loop bars of 16 16ths, counted from
//     the song's start: a boundary, or a locate into another Loop); Loop off: never, once Live has started;
//   - when Live starts playing, so pressing play always sounds the same from where it starts;
//   - when Seed changes. With Live stopped it just keeps stepping.
// The script that includes this defines DEVICE_NAME, passes every control message to seededRandomMessage(name,
// args) (true when it took it: random_seed, random_loop), calls seededRandomTransport(playing) when Live starts or
// stops, and seededRandomAtSongSixteenth(sixteenth) on each 16th of the song it plays, before anything draws at it.
// A script that draws ahead of the numbers' use (2sl gate: the next hits' draws, held in its gen~ core) reads
// seededRandomStarts(), a count of the times the sequence started over, and draws again when it changes.
/*SEEDED_SEQUENCE*/

var RANDOM_LOOP_BARS = /*LOOP_BARS*/;            // the Loop menu's items, in bars (0: off)
var RANDOM_SIXTEENTHS_PER_BAR = 16;
var RANDOM_SEED_HIGHEST = /*SEED_HIGHEST*/;
var randomSeed = /*INITIAL_SEED*/;
var randomLoopBars = RANDOM_LOOP_BARS[/*INITIAL_LOOP*/];
var randomSequence = seededSequence(randomSeed);
var randomLoopNumber = null;                      // the Loop the song position was last in (null: not yet heard)
var randomLivePlaying = 0;                        // the 16ths of the song count only while Live plays
var randomStartCount = 0;                         // how often the sequence has started over (seededRandomStarts)

function randomNext() { return randomSequence(); }
function randomRestart() { randomSequence = seededSequence(randomSeed); randomStartCount++; }
function seededRandomStarts() { return randomStartCount; }

function seededRandomMessage(name, args) {
  var value = args[0];
  if (name === "random_seed") {
    if (!(value >= 0 && value <= RANDOM_SEED_HIGHEST)) {
      error(DEVICE_NAME + ": Seed got " + value + ", outside 0.." + RANDOM_SEED_HIGHEST + " (a wiring error): using " +
            (Math.max(0, Math.min(RANDOM_SEED_HIGHEST, Math.round(value))) || 0) + "\n");
    }
    randomSeed = Math.max(0, Math.min(RANDOM_SEED_HIGHEST, Math.round(value))) || 0;
    randomRestart();
    return true;
  }
  if (name === "random_loop") {
    var index = Math.round(value);
    if (!(index >= 0 && index < RANDOM_LOOP_BARS.length)) {
      error(DEVICE_NAME + ": Loop got " + value + ", not one of its " + RANDOM_LOOP_BARS.length +
            " items (a wiring error): ignored\n");
      return true;
    }
    randomLoopBars = RANDOM_LOOP_BARS[index];
    randomLoopNumber = null;                      // the next 16th counts from the new length without a restart
    return true;
  }
  return false;
}

function seededRandomTransport(playing) {
  randomLoopNumber = null;
  randomLivePlaying = playing ? 1 : 0;
  if (playing) randomRestart();
}

function seededRandomAtSongSixteenth(sixteenth) {
  if (!isFinite(sixteenth)) {
    error(DEVICE_NAME + ": the seeded random got a song position of " + sixteenth + " 16ths: Loop skipped\n");
    return;
  }
  if (!randomLivePlaying || !randomLoopBars) return;
  var loopNumber = Math.floor(sixteenth / (randomLoopBars * RANDOM_SIXTEENTHS_PER_BAR));
  if (randomLoopNumber !== null && loopNumber !== randomLoopNumber) randomRestart();
  randomLoopNumber = loopNumber;
}
// ---- end of the kit's seeded random ------------------------------------------------------------------------------
