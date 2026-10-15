// ---- 2sl drums' functions (src/2sl-drums-functions.js, inserted into the brain by src/2sl-drums.py) ------------
// A pattern is one row per voice (VOICES order), 16 steps, each step a grade: REST, GHOST, HIT or ACCENT.
// Every function is pure (references/drums PLANS/2026-10-15-2sl-drums-functions.md):
//   generator: run(values) -> a pattern (a row may be null: "nothing for this voice", the row is kept)
//   modifier:  run(pattern, values) -> a new pattern (the input is never changed)
// `values` holds the function's settings by name, in their own units (int, or 0-100 for %). The brain applies
// the result only to the selected rows; the rest pass through.
//
// FUNCTIONS is the one source of a function: the build reads its entries (through Duktape, tools/es5check.py)
// and makes one Live parameter per setting from them; the brain runs them. Adding a function is one entry:
//   { name, kind: "generator" | "modifier", info: Info View text, needs: [voice ids it needs selected] (optional),
//     params: [{ name, min, max, initial, unit: "int" | "%", info, roll (optional: 0 = a new seed every Run) }],
//     summary: function (values) -> what it will do, in a few words (the status display),
//     run: as above }
// Sources: references/drums/patterns.md (B1 Grids, B2 Elektron, B3 Ableton's Rhythm / Seed / Euclidean, B5,
// P1-P12). The choices no source makes are marked (unsourced) and listed in devices/2sl-drums/README.md.

var STEPS = 16;
var REST = 0, GHOST = 1, HIT = 2, ACCENT = 3;
var GRADE_CHARACTERS = ".oxX";
var REST_ROW_TEXT = "................";
var GRIDS_ACCENT_ABOVE = 192;     // Grids: a firing step above this level is an accent (B1)

// ---- helpers the functions share -----------------------------------------------------------------------

function copyPattern(pattern) { var out = []; for (var v = 0; v < pattern.length; v++) out.push(pattern[v].slice()); return out; }
function mapRows(pattern, rowFunction) {
  var out = [];
  for (var v = 0; v < pattern.length; v++) out.push(rowFunction(pattern[v].slice(), v));
  return out;
}

/** A row from its text (16 of . o x X). Bad text is a broken build or message: it throws, with the text. */
function parseRow(text, where) {
  if (typeof text !== "string" || text.length !== STEPS) {
    throw new Error(DEVICE_NAME + ": " + where + ": row '" + text + "' is not " + STEPS + " steps");
  }
  var row = [];
  for (var s = 0; s < STEPS; s++) {
    var grade = GRADE_CHARACTERS.indexOf(text.charAt(s));
    if (grade < 0) throw new Error(DEVICE_NAME + ": " + where + ": row '" + text + "' has '" + text.charAt(s) + "' (use . o x X)");
    row.push(grade);
  }
  return row;
}
function rowText(row) { var t = ""; for (var s = 0; s < STEPS; s++) t += GRADE_CHARACTERS.charAt(row[s]); return t; }

/** How strong a step is in the bar: the downbeat 4, beat 3 3, beats 2 and 4 2, 8ths 1, 16ths 0 (unsourced:
 *  the usual metric hierarchy). Thin, ghosts and open hh use it to pick steps without randomness. */
function metricWeight(step) { return step % 16 === 0 ? 4 : step % 8 === 0 ? 3 : step % 4 === 0 ? 2 : step % 2 === 0 ? 1 : 0; }

/** The first `count` of `steps` after sorting by `order` (a comparator), so the pick is the same every time. */
function firstSteps(steps, order, count) { return steps.slice().sort(order).slice(0, count); }
function countOf(percent, total) { return Math.round(percent / 100 * total); }

/** A seeded random number generator (Park and Miller's minimal standard, a Lehmer generator; unsourced in
 *  references/): the same seed gives the same numbers, in Max and in the tests. Returns a function -> [0, 1). */
function seededRandom(seed) {
  var state = (Math.abs(Math.floor(seed)) * 48271 + 12345) % 2147483646 + 1;
  var next = function () { state = (state * 16807) % 2147483647; return (state - 1) / 2147483646; };
  next(); next(); next();          // the first numbers after a small seed are small: skip them
  return next;
}

/** Bjorklund's algorithm as Toussaint gives it (patterns.md P11): k onsets spread as evenly as possible over n. */
function euclidean(k, n) {
  if (!(k >= 0 && k <= n && n >= 1)) throw new Error(DEVICE_NAME + ": E(" + k + "," + n + ") doesn't exist");
  var groups = [], remainders = [], i;
  if (k === 0 || k === n) { for (i = 0; i < n; i++) groups.push(k ? 1 : 0); return groups; }
  for (i = 0; i < k; i++) groups.push([1]);
  for (i = 0; i < n - k; i++) remainders.push([0]);
  // pair a remainder onto each group, then the leftovers become the remainders; at least once, until one is left
  do {
    var pairs = Math.min(groups.length, remainders.length), merged = [];
    for (i = 0; i < pairs; i++) merged.push(groups[i].concat(remainders[i]));
    var leftover = groups.length > pairs ? groups.slice(pairs) : remainders.slice(pairs);
    groups = merged;
    remainders = leftover;
  } while (remainders.length > 1);
  var out = [];
  for (i = 0; i < groups.length; i++) out = out.concat(groups[i]);
  for (i = 0; i < remainders.length; i++) out = out.concat(remainders[i]);
  return out;
}

/** avrlib U8Mix: a crossfade of two bytes by `balance` 0-255 (written from memory, README). */
function u8Mix(a, b, balance) { return (a * (255 - balance) + b * balance) >> 8; }

/** Grids' ReadDrumMap (patterns.md P12): the level of `step` (0-31, 32nds) for `instrument` (0 BD, 1 SD, 2 HH)
 *  at map point x, y (0-255), bilinear between the four nearest nodes. */
function gridsLevel(step, instrument, x, y) {
  var i = x >> 6, j = y >> 6;
  var offset = instrument * 32 + step;
  var a = GRIDS_NODES[GRIDS_DRUM_MAP[i][j]][offset];
  var b = GRIDS_NODES[GRIDS_DRUM_MAP[i + 1][j]][offset];
  var c = GRIDS_NODES[GRIDS_DRUM_MAP[i][j + 1]][offset];
  var d = GRIDS_NODES[GRIDS_DRUM_MAP[i + 1][j + 1]][offset];
  var xBalance = (x << 2) & 255, yBalance = (y << 2) & 255;
  return u8Mix(u8Mix(a, b, xBalance), u8Mix(c, d, xBalance), yBalance);
}

function voiceIndexOf(id) {
  for (var v = 0; v < VOICES.length; v++) if (VOICES[v].id === id) return v;
  throw new Error(DEVICE_NAME + ": no voice '" + id + "'");
}
function cannedKitList() {
  var names = [];
  for (var k = 0; k < CANNED_KITS.length; k++) names.push((k + 1) + " " + CANNED_KITS[k].name);
  return names.join(", ");
}
function voiceList() {
  var names = [];
  for (var v = 0; v < VOICES.length; v++) names.push((v + 1) + " " + VOICES[v].name);
  return names.join(", ");
}

// ---- the registry ------------------------------------------------------------------------------------------

var FUNCTIONS = [
  // ======== generators ========
  { name: "canned", kind: "generator",
    info: "Rows from a sourced kit (patterns.md P1-P11, as their sources give them).",
    params: [
      { name: "kit", min: 1, max: CANNED_KITS.length, initial: 1, unit: "int",
        info: "Which kit: " + cannedKitList() + "." },
      { name: "from", min: 0, max: VOICES.length, initial: 0, unit: "int",
        info: "0: each row gets its own voice's row from the kit. Else every selected row gets this voice's row: " +
              voiceList() + "." }],
    summary: function (values) {
      return CANNED_KITS[values.kit - 1].name + (values.from ? ", " + VOICES[values.from - 1].name + "'s row" : "");
    },
    run: function (values) {
      var kit = CANNED_KITS[values.kit - 1], rows = [];
      for (var v = 0; v < VOICES.length; v++) {
        var id = values.from ? VOICES[values.from - 1].id : VOICES[v].id;
        rows.push(parseRow(kit.rows[id] || REST_ROW_TEXT, "canned kit " + kit.name + " / " + id));
      }
      return rows;
    } },

  { name: "grids", kind: "generator",
    info: "Rows from Mutable Instruments Grids' pattern map (patterns.md P12, B1): BD, SD and HH from its three " +
          "channels; CP takes the SD channel's accents, OH the HH channel's offbeat 8ths; RS and RD have no channel.",
    params: [
      { name: "x", min: 0, max: 255, initial: 128, unit: "int", info: "The map's X, 0-255, as on Grids." },
      { name: "y", min: 0, max: 255, initial: 128, unit: "int", info: "The map's Y, 0-255, as on Grids." },
      { name: "density", min: 0, max: 100, initial: 50, unit: "%",
        info: "Grids' density: a step plays when its level is above 255 - density. Above 192 it is an accent." }],
    summary: function (values) { return "map " + values.x + "," + values.y + "  density " + values.density + "%"; },
    run: function (values) {
      var threshold = 255 - Math.round(values.density / 100 * 255), rows = [];
      for (var v = 0; v < VOICES.length; v++) {
        var channel = VOICES[v].grids;
        if (!channel) { rows.push(null); continue; }
        var row = [];
        for (var s = 0; s < STEPS; s++) {
          var level = gridsLevel(2 * s, channel.instrument, values.x, values.y);   // 16ths: the even 32nds
          var grade = level > threshold ? (level > GRIDS_ACCENT_ABOVE ? ACCENT : HIT) : REST;
          if (channel.keep === "accents" && grade !== ACCENT) grade = REST;
          if (channel.keep === "offbeat eighths" && s % 4 !== 2) grade = REST;
          row.push(grade);
        }
        rows.push(row);
      }
      return rows;
    } },

  { name: "euclid", kind: "generator",
    info: "A Euclidean rhythm (Toussaint, patterns.md P11): hits spread as evenly as possible over a cycle of " +
          "steps, rotated, repeated across the bar (P10's 3- and 5-step loops are E(1,3) and E(1,5)).",
    params: [
      { name: "hits", min: 0, max: 16, initial: 4, unit: "int", info: "Onsets in the cycle (no more than Steps)." },
      { name: "rotation", min: 0, max: 15, initial: 0, unit: "int",
        info: "Steps later the cycle starts, like Ableton's Euclidean rotation (B3)." },
      { name: "steps", min: 1, max: 16, initial: 16, unit: "int", info: "The cycle's length; it repeats across the 16 steps." }],
    summary: function (values) {
      var hits = Math.min(values.hits, values.steps);
      return "E(" + hits + "," + values.steps + ")" + (values.rotation ? " +" + values.rotation : "") +
             (hits < values.hits ? "  (only " + values.steps + " hits fit)" : "");
    },
    run: function (values) {
      var cycle = euclidean(Math.min(values.hits, values.steps), values.steps), row = [], rows = [];
      for (var s = 0; s < STEPS; s++) row.push(cycle[(((s - values.rotation) % values.steps) + values.steps) % values.steps] ? HIT : REST);
      for (var v = 0; v < VOICES.length; v++) rows.push(row.slice());
      return rows;
    } },

  { name: "random", kind: "generator",
    info: "Random hits: each step plays with Density's chance, and a hit is an accent with Accent's chance " +
          "(Ableton's Seed density, Elektron's trig probability: patterns.md B2, B3).",
    params: [
      { name: "density", min: 0, max: 100, initial: 30, unit: "%", info: "The chance that a step is a hit." },
      { name: "accent", min: 0, max: 100, initial: 10, unit: "%", info: "The chance that a hit is an accent." },
      { name: "seed", min: 0, max: 999, initial: 0, unit: "int", roll: true,
        info: "The same seed makes the same rows. 0: a new seed every Run (the status line shows which)." }],
    summary: function (values) {
      return "density " + values.density + "%  accent " + values.accent + "%  " + (values.seed ? "seed " + values.seed : "new seed");
    },
    run: function (values) {
      var rows = [];
      for (var v = 0; v < VOICES.length; v++) {
        var random = seededRandom(values.seed * 131 + v), row = [];
        for (var s = 0; s < STEPS; s++) {
          var hit = random() < values.density / 100, accented = random() < values.accent / 100;
          row.push(hit ? (accented ? ACCENT : HIT) : REST);
        }
        rows.push(row);
      }
      return rows;
    } },

  // ======== modifiers ========
  { name: "shift", kind: "modifier",
    info: "Moves the rows by steps, later for positive, earlier for negative, wrapping around the bar " +
          "(Ableton's Rhythm Shift, patterns.md B3).",
    params: [{ name: "steps", min: -15, max: 15, initial: 1, unit: "int", info: "Steps to move: + later, - earlier." }],
    summary: function (values) { return (values.steps > 0 ? "+" : "") + values.steps + " steps"; },
    run: function (pattern, values) {
      return mapRows(pattern, function (row) {
        var out = [];
        for (var s = 0; s < STEPS; s++) out.push(row[(((s - values.steps) % STEPS) + STEPS) % STEPS]);
        return out;
      });
    } },

  { name: "reverse", kind: "modifier",
    info: "Plays the rows backwards from the downbeat: step 1 stays, step 2 swaps with 16, 3 with 15, ... " +
          "(unsourced), so four on the floor and offbeats stay where they are.",
    params: [],
    summary: function () { return "backwards from the downbeat"; },
    run: function (pattern) {
      return mapRows(pattern, function (row) {
        var out = [];
        for (var s = 0; s < STEPS; s++) out.push(row[(STEPS - s) % STEPS]);
        return out;
      });
    } },

  { name: "thin", kind: "modifier",
    info: "Removes the weakest hits, as Grids' density keeps the strongest steps (patterns.md B1): ghosts first, " +
          "then hits, then accents; within a grade the weakest place in the bar first.",
    params: [{ name: "amount", min: 0, max: 100, initial: 25, unit: "%", info: "The share of each row's hits removed." }],
    summary: function (values) { return "remove " + values.amount + "% of the hits"; },
    run: function (pattern, values) {
      return mapRows(pattern, function (row) {
        var hits = [];
        for (var s = 0; s < STEPS; s++) if (row[s] > REST) hits.push(s);
        var removed = firstSteps(hits, function (a, b) {
          return (row[a] - row[b]) || (metricWeight(a) - metricWeight(b)) || (b - a);
        }, countOf(values.amount, hits.length));
        for (var i = 0; i < removed.length; i++) row[removed[i]] = REST;
        return row;
      });
    } },

  { name: "ghosts", kind: "modifier",
    info: "Adds ghost notes (quiet hits, patterns.md B5) on rests: first just before a hit (as P6's ghost kicks " +
          "before beats 2 and 4), then on the weakest places in the bar.",
    params: [{ name: "amount", min: 0, max: 100, initial: 25, unit: "%", info: "The share of each row's rests that become ghosts." }],
    summary: function (values) { return values.amount + "% of the rests"; },
    run: function (pattern, values) {
      return mapRows(pattern, function (row) {
        var rests = [];
        for (var s = 0; s < STEPS; s++) if (row[s] === REST) rests.push(s);
        var beforeHit = function (s) { return row[(s + 1) % STEPS] >= HIT ? 0 : 1; };
        var chosen = firstSteps(rests, function (a, b) {
          return (beforeHit(a) - beforeHit(b)) || (metricWeight(a) - metricWeight(b)) || (a - b);
        }, countOf(values.amount, rests.length));
        for (var i = 0; i < chosen.length; i++) row[chosen[i]] = GHOST;
        return row;
      });
    } },

  { name: "fill", kind: "modifier",
    info: "A fill at the end of the bar (Elektron's FILL, patterns.md B2): hits on the rests of the last steps, " +
          "spread evenly (Toussaint, P11). Run it, hear it, Undo it.",
    params: [
      { name: "steps", min: 1, max: 16, initial: 4, unit: "int", info: "How many of the bar's last steps: 4 = the last beat, 8 = the last half bar." },
      { name: "density", min: 0, max: 100, initial: 50, unit: "%", info: "The share of those steps that get a hit." }],
    summary: function (values) { return "last " + values.steps + " steps, " + values.density + "%"; },
    run: function (pattern, values) {
      var onsets = euclidean(countOf(values.density, values.steps), values.steps), first = STEPS - values.steps;
      return mapRows(pattern, function (row) {
        for (var i = 0; i < values.steps; i++) if (onsets[i] && row[first + i] === REST) row[first + i] = HIT;
        return row;
      });
    } },

  { name: "open hh", kind: "modifier", needs: ["ch", "oh"],
    info: "Turns closed hats into open hats (the CH row's hits move to the OH row; patterns.md B5 swaps them for " +
          "variation): offbeat 8ths first, where the sourced kits put the open hat (P1, P2), then the weakest places.",
    params: [{ name: "amount", min: 0, max: 100, initial: 50, unit: "%", info: "The share of the closed hat's hits that open." }],
    summary: function (values) { return values.amount + "% of the closed hats"; },
    run: function (pattern, values) {
      var out = copyPattern(pattern), ch = voiceIndexOf("ch"), oh = voiceIndexOf("oh"), hits = [];
      for (var s = 0; s < STEPS; s++) if (out[ch][s] > REST) hits.push(s);
      var offbeat = function (s) { return s % 4 === 2 ? 0 : 1; };
      var opened = firstSteps(hits, function (a, b) {
        return (offbeat(a) - offbeat(b)) || (metricWeight(a) - metricWeight(b)) || (b - a);
      }, countOf(values.amount, hits.length));
      for (var i = 0; i < opened.length; i++) {
        out[oh][opened[i]] = Math.max(out[oh][opened[i]], out[ch][opened[i]]);
        out[ch][opened[i]] = REST;
      }
      return out;
    } },

  { name: "accent", kind: "modifier",
    info: "Accents every Nth hit of each row, the others become plain hits; ghosts stay (Ableton's Rhythm Accent " +
          "Frequency and Offset, patterns.md B3).",
    params: [
      { name: "every", min: 1, max: 16, initial: 4, unit: "int", info: "Hits from one accent to the next (an accent counts as a hit; 1 = every hit)." },
      { name: "offset", min: 0, max: 15, initial: 0, unit: "int", info: "Hits before the first accent." }],
    summary: function (values) { return "every " + values.every + (values.offset ? ", from hit " + (values.offset + 1) : ""); },
    run: function (pattern, values) {
      return mapRows(pattern, function (row) {
        var count = 0;
        for (var s = 0; s < STEPS; s++) {
          if (row[s] < HIT) continue;
          row[s] = ((((count - values.offset) % values.every) + values.every) % values.every) === 0 ? ACCENT : HIT;
          count++;
        }
        return row;
      });
    } }
];

/** The hand edit (a click on a step) is a modifier too, outside the panel: values {voice, step, grade}. */
var HAND_EDIT = {
  name: "edit", kind: "modifier",
  run: function (pattern, values) {
    var out = copyPattern(pattern);
    out[values.voice][values.step] = values.grade;
    return out;
  }
};

/** A broken registry is a broken device: say what is wrong, at build time (the build evaluates this) and load. */
function checkFunctionRegistry() {
  var seen = {};
  for (var f = 0; f < FUNCTIONS.length; f++) {
    var entry = FUNCTIONS[f], where = DEVICE_NAME + ": function " + f + " (" + entry.name + ")";
    if (!entry.name || seen[entry.name]) throw new Error(where + ": needs a name of its own");
    seen[entry.name] = 1;
    if (entry.kind !== "generator" && entry.kind !== "modifier") throw new Error(where + ": kind is '" + entry.kind + "'");
    if (!entry.info) throw new Error(where + ": has no Info text");
    if (typeof entry.run !== "function" || typeof entry.summary !== "function") throw new Error(where + ": needs run and summary");
    var needs = entry.needs || [];
    for (var n = 0; n < needs.length; n++) voiceIndexOf(needs[n]);
    var names = {};
    for (var p = 0; p < entry.params.length; p++) {
      var param = entry.params[p];
      if (!param.name || names[param.name]) throw new Error(where + ": setting " + p + " needs a name of its own");
      names[param.name] = 1;
      if (param.unit !== "int" && param.unit !== "%") throw new Error(where + " / " + param.name + ": unit '" + param.unit + "' (int or %)");
      if (!(param.min <= param.initial && param.initial <= param.max)) throw new Error(where + " / " + param.name + ": initial outside min..max");
      if (Math.round(param.min) !== param.min || Math.round(param.max) !== param.max || Math.round(param.initial) !== param.initial) {
        throw new Error(where + " / " + param.name + ": min, max and initial must be whole numbers");
      }
      if (!param.info) throw new Error(where + " / " + param.name + ": has no Info text");
      if (param.roll && param.min !== 0) throw new Error(where + " / " + param.name + ": a roll setting starts at 0 (= roll)");
    }
  }
}
checkFunctionRegistry();
