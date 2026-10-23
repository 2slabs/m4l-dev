// The kit's sidechain-style pump (twosl_dsp/techniques/sidechain_style_pump.py) as a display draws it: the duck (0..1)
// at a phase of a division, a quarter sine in over the attack, then the curved recovery. The constants are the
// technique's, filled in by the build.
var SIDECHAIN_PUMP_LOWEST_ATTACK_FRACTION = /*SIDECHAIN_PUMP_LOWEST_ATTACK_FRACTION*/;
var SIDECHAIN_PUMP_HIGHEST_ATTACK_FRACTION = /*SIDECHAIN_PUMP_HIGHEST_ATTACK_FRACTION*/;
var SIDECHAIN_PUMP_RELEASE_END_MARGIN = /*SIDECHAIN_PUMP_RELEASE_END_MARGIN*/;
var SIDECHAIN_PUMP_CURVE_EXPONENT_PER_CURVE = /*SIDECHAIN_PUMP_CURVE_EXPONENT_PER_CURVE*/;

/** The duck at `phase` (0..1) of a division divisionMs long, with the attack in ms, the release as a fraction of the
 *  division and the curve 0..1, exactly as the technique computes it. */
function sidechainPumpDuck(phase, attackMs, divisionMs, releaseFraction, curve) {
  var attackFraction = Math.min(Math.max(attackMs / divisionMs, SIDECHAIN_PUMP_LOWEST_ATTACK_FRACTION),
    SIDECHAIN_PUMP_HIGHEST_ATTACK_FRACTION);
  var releaseEnd = Math.max(releaseFraction, attackFraction + SIDECHAIN_PUMP_RELEASE_END_MARGIN);
  if (phase < attackFraction) return Math.sin(Math.PI / 2 * phase / attackFraction);
  var recoveryLeft = 1 - Math.min(Math.max((phase - attackFraction) / (releaseEnd - attackFraction), 0), 1);
  return Math.pow(recoveryLeft, 1 + curve * SIDECHAIN_PUMP_CURVE_EXPONENT_PER_CURVE);
}
