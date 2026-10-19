// A sandbox with Max's [js] globals stubbed, for running 2sl device scripts in plain node (no packages).
// Used by tests/2sl-drums.test.js and tools/drums_hits.js. Math.random is seeded (mulberry32) so runs repeat.
//   const { sandbox, deliverMessage } = require("./max_sandbox");
//   const { context, record } = sandbox(seed, { extra globals });  vm.runInContext(source, context);
// record.outlets: [[outlet, ...args]]   record.errors / record.posts: what error() / post() printed.
"use strict";
const vm = require("vm");

// The Math functions ES2015 added (ECMA-262 6th edition, 20.2.2), which Max's ES5 [js] engine lacks.
const ES2015_MATH_FUNCTIONS = ["imul", "clz32", "fround", "log10", "log2", "log1p", "expm1", "cosh", "sinh", "tanh",
                               "acosh", "asinh", "atanh", "hypot", "trunc", "sign", "cbrt"];

function seededRandom(seed) {
  let state = seed >>> 0;
  return function () {
    state = (state + 0x6D2B79F5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function sandbox(seed, extraGlobals) {
  const record = { outlets: [], errors: [], posts: [] };
  const seededMath = Object.create(Math);
  seededMath.random = seededRandom(seed);
  // Max's [js] / [jsui] engine is ES5: the Math functions ES2015 added aren't there. Hide them, so a script that
  // calls one fails here ("... is not a function") the way it would in Live, not only in Live.
  for (const es2015MathFunction of ES2015_MATH_FUNCTIONS) seededMath[es2015MathFunction] = undefined;
  const context = Object.assign({
    Math: seededMath, JSON, isFinite, Error, Object, Array, String, Number, RegExp, Date,
    inlets: 0, outlets: 0, inlet: 0, messagename: "",
    post: (s) => record.posts.push(String(s)),
    error: (s) => record.errors.push(String(s)),
    outlet: function (n) {
      const args = Array.prototype.slice.call(arguments, 1);
      record.outlets.push([n].concat(args.length === 1 && Array.isArray(args[0]) ? args[0] : args));
    },
    arrayfromargs: (a) => Array.prototype.slice.call(a),
  }, extraGlobals || {});
  vm.createContext(context);
  return { context, record };
}

/** Deliver message `name` the way Max's [js] does: a global function of that name takes it (bypassing
 *  anything()); only names without one reach anything(). So a test sees what Live will do when a handler
 *  name collides with a function the script defines. */
function deliverMessage(context, inletIndex, name, args) {
  context.inlet = inletIndex;
  context.messagename = name;
  const sameNamedFunction = context[name];
  if (typeof sameNamedFunction === "function" && name !== "anything") return sameNamedFunction.apply(null, args);
  if (typeof context.anything !== "function") throw new Error("the script has no anything() for '" + name + "'");
  return context.anything.apply(null, args);
}

module.exports = { sandbox, seededRandom, deliverMessage, ES2015_MATH_FUNCTIONS };
