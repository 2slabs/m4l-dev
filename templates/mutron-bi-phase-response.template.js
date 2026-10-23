// The kit's Mu-Tron Bi-Phase (twosl_dsp/circuit_modules/mutron_bi_phase.py), one instance of it, as a display draws it:
// one phasor's small-signal response (the module's phasor_response, magnitude, the foot switch on) and its notches
// (phasor_notches_hz, the same steps), from what the running module puts out: the stage corner, the feedback pot's
// wiper position and the stages' spread (`<name>_corner_<side>_hz`, `<name>_pot_<side>`, `<name>_stage_corner_spread`).
// The constants are the module's and the instance's, filled in by the build.

/** One bilinear one-pole's s = j t / g at frequencyHz, cut and prewarped as the kit's one-pole and all-pass cascade
 * clamp them (zero_delay_one_pole_filter.small_signal_response): returns t / g. */
function /*NAME*/_bilinear_ratio(frequencyHz, cutoffHz, prewarpHz, sampleRate) {
  var cutoff = Math.max(cutoffHz, /*LOWEST_CUTOFF_HZ*/);
  var point = Math.min(Math.max(prewarpHz, /*LOWEST_CUTOFF_HZ*/), /*HIGHEST_PREWARP_OF_SAMPLE_RATE*/ * sampleRate);
  var g = Math.tan(Math.PI * point / sampleRate) * cutoff / point;
  return Math.tan(Math.PI * Math.min(frequencyHz, 0.4999 * sampleRate) / sampleRate) / g;
}

/** [re, im] of a * b for complex a, b as [re, im]. */
function /*NAME*/_times(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
function /*NAME*/_over(a, b) {
  var d = b[0] * b[0] + b[1] * b[1];
  return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
}

/** |H|^2 of one phasor (phasor "a" or "b") at frequencyHz: the six stages (each the corner x (1 + spread x its
 * pattern ratio), prewarped at the corner), C12's high-pass and C5's low-pass at the wiper's position, k, the loop,
 * Z9B's inversion and the passive mix through C14 (the bypass cell lit). */
function /*NAME*/_phasor_level(frequencyHz, cornerHz, potPosition, spread, sampleRate, phasor) {
  var pattern = /*STAGE_SPREAD_PATTERN*/[phasor];
  if (!pattern) throw new Error("/*NAME*/_phasor_level: no phasor '" + phasor + "' (a or b)");
  var stages = [1, 0];
  for (var i = 0; i < pattern.length; i++) {
    var x = /*NAME*/_bilinear_ratio(frequencyHz, cornerHz * (1 + spread * pattern[i]), cornerHz, sampleRate);
    stages = /*NAME*/_times(stages, /*NAME*/_over([1, -x], [1, x]));        // (1 - s) / (1 + s)
  }
  var position = potPosition, load = /*FEEDBACK_DIVIDER_TOP_OHMS*/ + /*FEEDBACK_DIVIDER_BOTTOM_OHMS*/;
  var lower = position * /*FEEDBACK_POT_OHMS*/;
  var potOhms = (1 - position) * /*FEEDBACK_POT_OHMS*/ + (lower > 0 ? lower * load / (lower + load) : 0);
  var couplingHz = 1 / (2 * Math.PI * (1 / (1 / /*WET_INVERTER_INPUT_OHMS*/ + 1 / potOhms)) * /*OUTPUT_COUPLING_FARADS*/);
  var source = /*FEEDBACK_DIVIDER_TOP_OHMS*/ + position * (1 - position) * /*FEEDBACK_POT_OHMS*/;
  var lowpassHz = 1 / (2 * Math.PI * (1 / (1 / /*FEEDBACK_DIVIDER_BOTTOM_OHMS*/ + 1 / source)) *
    /*FEEDBACK_NODE_CAPACITOR_FARADS*/);
  var wiper = position * load / (load + position * (1 - position) * /*FEEDBACK_POT_OHMS*/);
  var k = /*INPUT_STAGE_GAIN_ON_PLUS*/ * /*FEEDBACK_DIVIDER_BOTTOM_OHMS*/ / load * wiper;
  var c = /*NAME*/_bilinear_ratio(frequencyHz, couplingHz, couplingHz, sampleRate);
  var coupling = /*NAME*/_over([0, c], [1, c]);                                 // s / (1 + s)
  var l = /*NAME*/_bilinear_ratio(frequencyHz, lowpassHz, lowpassHz, sampleRate);
  var fedBack = /*NAME*/_over([1, 0], [1, l]);                                  // 1 / (1 + s)
  var path = /*NAME*/_times(coupling, stages);
  var loop = /*NAME*/_times(fedBack, path);
  var loopInput = /*NAME*/_over([-1, 0], [1 - k * loop[0], -k * loop[1]]);
  var wet = /*NAME*/_times([-path[0], -path[1]], loopInput);
  var m = /*NAME*/_bilinear_ratio(frequencyHz, /*MIX_CORNER_HZ*/, /*MIX_CORNER_HZ*/, sampleRate);
  var mix = /*NAME*/_times(/*NAME*/_over([0, m], [1, m]), [wet[0] - 1, wet[1]]);
  var re = 1 + /*MIX_WEIGHT*/ * mix[0], im = /*MIX_WEIGHT*/ * mix[1];
  return re * re + im * im;
}

/** |H| of one phasor at frequencyHz (phasor_response's magnitude). */
function /*NAME*/_phasor_response(frequencyHz, cornerHz, potPosition, spread, sampleRate, phasor) {
  return Math.sqrt(/*NAME*/_phasor_level(frequencyHz, cornerHz, potPosition, spread, sampleRate, phasor));
}

/** The phasor's notches now (Hz, low to high), phasor_notches_hz's steps: each between two of the equal-stage peaks
 * (tan(m pi / N) x the corner, the outer two reaching NOTCH_SEARCH_REACH past the outer notches' nominal places, held
 * inside 1 Hz .. 0.49 x the sample rate), a log grid, then golden sections around the grid's least point. */
function /*NAME*/_phasor_notches_hz(cornerHz, potPosition, spread, sampleRate, phasor) {
  var stages = /*STAGES_PER_PHASOR*/, half = stages / 2, grid = /*NOTCH_SEARCH_GRID*/;
  var edges = [cornerHz * Math.tan(Math.PI / (2 * stages)) / /*NOTCH_SEARCH_REACH*/];
  for (var m = 1; m < half; m++) edges.push(cornerHz * Math.tan(m * Math.PI / stages));
  edges.push(cornerHz * Math.tan((stages - 1) * Math.PI / (2 * stages)) * /*NOTCH_SEARCH_REACH*/);
  var highest = /*NOTCH_SEARCH_HIGHEST_OF_SAMPLE_RATE*/ * sampleRate;
  for (var e = 0; e < edges.length; e++) edges[e] = Math.min(Math.max(edges[e], 1), highest);
  var level = function (logHz) {
    return /*NAME*/_phasor_level(Math.exp(logHz), cornerHz, potPosition, spread, sampleRate, phasor);
  };
  var golden = (Math.sqrt(5) - 1) / 2, notches = [];
  for (var n = 0; n < half; n++) {
    var low = Math.log(edges[n]), high = Math.log(edges[n + 1]), step = (high - low) / (grid - 1);
    var least = 0, leastLevel = Infinity;
    for (var i = 0; i < grid; i++) {
      var here = level(low + i * step);
      if (here < leastLevel) { leastLevel = here; least = i; }
    }
    var a = low + Math.max(least - 1, 0) * step, b = low + Math.min(least + 1, grid - 1) * step;
    for (var s = 0; s < /*NOTCH_SEARCH_SECTIONS*/; s++) {
      var c = b - golden * (b - a), d = a + golden * (b - a);
      if (level(c) < level(d)) b = d; else a = c;
    }
    notches.push(Math.exp((a + b) / 2));
  }
  return notches;
}
