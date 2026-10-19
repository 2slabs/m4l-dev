// ---- the m4l-dev kit's seeded sequence (templates/seeded-sequence.template.js) ----------------------------------
// mulberry32 (Tommy Ettinger, public domain; references/README.md "Randomness"): a 32-bit state stepped by a Weyl
// constant and mixed with Math.imul and shifts, which JavaScript does exactly on 32-bit integers, so Max's [js] and
// node give the same numbers. seededSequence(seed) -> a function giving the next number in [0, 1) each call; the
// same seed gives the same numbers, in the same order.
function seededSequence(seed) {
  if (!(seed >= 0 && seed <= 4294967295 && seed === Math.floor(seed))) {
    throw new Error(DEVICE_NAME + ": a seeded sequence's seed must be a whole number 0..4294967295, not " + seed);
  }
  var state = seed >>> 0;
  return function () {
    state = (state + 0x6D2B79F5) >>> 0;
    var mixed = state;
    mixed = Math.imul(mixed ^ (mixed >>> 15), mixed | 1);
    mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), mixed | 61);
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
  };
}
// ---- end of the kit's seeded sequence ----------------------------------------------------------------------------
