// A sandbox with Max's [js] globals stubbed, for running 2sl device scripts in plain node (no packages).
// Used by tests/2sl-drums.test.js and tools/drums_hits.js. Math.random is seeded (mulberry32) so runs repeat.
//   const { sandbox } = require("./max_sandbox");
//   const { context, record } = sandbox(seed, { extra globals });  vm.runInContext(source, context);
// record.outlets: [[outlet, ...args]]   record.errors / record.posts: what error() / post() printed.
"use strict";
const vm = require("vm");

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

module.exports = { sandbox, seededRandom };
