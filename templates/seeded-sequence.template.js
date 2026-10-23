// ---- the 2sl-dsp kit's seeded sequence (templates/seeded-sequence.template.js) ----------------------------------
// mulberry32 (Tommy Ettinger, public domain; references/README.md "Randomness"): a 32-bit state stepped by a Weyl
// constant and mixed with 32-bit multiplies and shifts, which JavaScript does exactly on 32-bit integers, so Max's
// [js] and node give the same numbers. seededSequence(seed) -> a function giving the next number in [0, 1) each
// call; the same seed gives the same numbers, in the same order.
// Max's [js] / [jsui] engine is ES5 and has no Math.imul (ES2015; the 2sl devices' jsui has no Math.tanh either), so
// the multiply is multiplyLow32Bits: the low 32 bits of a * b, from 16-bit halves (each partial product stays under
// 2^53, so a double holds it exactly), the same result as Math.imul.
function multiplyLow32Bits(a, b) {
  var aHigh = (a >>> 16) & 0xffff, aLow = a & 0xffff, bHigh = (b >>> 16) & 0xffff, bLow = b & 0xffff;
  return ((aLow * bLow) + (((aHigh * bLow + aLow * bHigh) << 16) >>> 0)) | 0;
}
function seededSequence(seed) {
  if (!(seed >= 0 && seed <= 4294967295 && seed === Math.floor(seed))) {
    throw new Error(DEVICE_NAME + ": a seeded sequence's seed must be a whole number 0..4294967295, not " + seed);
  }
  var state = seed >>> 0;
  return function () {
    state = (state + 0x6D2B79F5) >>> 0;
    var mixed = state;
    mixed = multiplyLow32Bits(mixed ^ (mixed >>> 15), mixed | 1);
    mixed ^= mixed + multiplyLow32Bits(mixed ^ (mixed >>> 7), mixed | 61);
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
  };
}
// ---- end of the kit's seeded sequence ----------------------------------------------------------------------------
