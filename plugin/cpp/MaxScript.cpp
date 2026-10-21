#include "MaxScript.h"

namespace twosl::plugin
{
namespace
{
    // Max's [js] globals, in the script's own language. Task: `interval` (ms), `repeat (n, initialdelay)` (n < 0 or
    // left out: until cancelled; the first run after initialdelay, 0 when left out), `cancel()`, `schedule (delay)`
    // (once), `execute()`, `running`. A task due several times by one advanceTo runs once a time, at its own time.
    const char* prelude = R"js(
var __global = this;
var inlet = 0, messagename = "", inlets = 1, outlets = 1, jsarguments = [];
function outlet() { __host.outlet(Array.prototype.slice.call(arguments)); }
function post() { __host.post(Array.prototype.slice.call(arguments).join(" ")); }
function error() { __host.error(Array.prototype.slice.call(arguments).join(" ")); }
function arrayfromargs(a) { return Array.prototype.slice.call(a); }
var __now = 0, __tasks = [];
function Task(fn, owner) {
  this.fn = fn; this.owner = owner; this.interval = 500; this.running = false; this.due = 0; this.left = -1;
  __tasks.push(this);
}
Task.prototype.repeat = function (n, initialdelay) {
  this.running = true; this.left = (n === undefined || n < 0) ? -1 : n;
  this.due = __now + (initialdelay === undefined ? 0 : initialdelay);
};
Task.prototype.schedule = function (delay) { this.running = true; this.left = 1; this.due = __now + (delay || 0); };
Task.prototype.cancel = function () { this.running = false; };
Task.prototype.execute = function () { this.fn.call(this.owner); };
function __nextDue() {
  var next = -1;
  for (var i = 0; i < __tasks.length; i++)
    if (__tasks[i].running && (next < 0 || __tasks[i].due < next)) next = __tasks[i].due;
  return next;
}
function __advanceTo(now) {
  for (;;) {
    var task = null;
    for (var i = 0; i < __tasks.length; i++)
      if (__tasks[i].running && __tasks[i].due <= now && (task === null || __tasks[i].due < task.due)) task = __tasks[i];
    if (task === null) break;
    __now = task.due;
    task.due += Math.max(task.interval, 1);
    if (task.left > 0 && --task.left === 0) task.running = false;
    task.fn.call(task.owner);
  }
  __now = now;
}
function __deliver(i, name, values) {
  inlet = i; messagename = name;
  var f = __global[name];
  if (typeof f === "function" && name !== "anything") return f.apply(null, values);
  if (typeof __global.anything === "function") return __global.anything.apply(null, values);
  error("the script has no " + name + "() and no anything()");
}
)js";
} // namespace

MaxScript::MaxScript (const juce::String& source, const juce::String& name)
    : scriptName (name)
{
    auto* host = new juce::DynamicObject();
    host->setMethod ("outlet", [this] (const juce::var::NativeFunctionArgs& args) {
        if (args.numArguments > 0 && args.arguments[0].isArray())
        {
            const auto& values = *args.arguments[0].getArray();
            if (! values.isEmpty())
            {
                Output output { (int) values[0], {} };
                for (int i = 1; i < values.size(); ++i)
                    output.values.add (values[i]);
                sent.push_back (std::move (output));
            }
        }
        return juce::var();
    });
    host->setMethod ("post", [this] (const juce::var::NativeFunctionArgs& args) {
        const juce::ScopedLock lock (logLock);
        logLines.add (scriptName + ": " + (args.numArguments > 0 ? args.arguments[0].toString() : juce::String()));
        return juce::var();
    });
    host->setMethod ("error", [this] (const juce::var::NativeFunctionArgs& args) {
        const juce::ScopedLock lock (logLock);
        logLines.add (scriptName + " error: " + (args.numArguments > 0 ? args.arguments[0].toString() : juce::String()));
        return juce::var();
    });
    engine.registerNativeObject ("__host", host);
    engine.maximumExecutionTime = juce::RelativeTime::seconds (2.0);
    for (const auto* code : { prelude, source.toRawUTF8() })
    {
        const auto result = engine.execute (code);
        if (result.failed())
            throw std::runtime_error ((scriptName + ": " + result.getErrorMessage()).toStdString());
    }
}

juce::var MaxScript::call (const char* function, const juce::Array<juce::var>& arguments)
{
    juce::Result result = juce::Result::ok();
    const juce::var::NativeFunctionArgs args ({}, arguments.begin(), arguments.size());
    auto value = engine.callFunction (function, args, &result);
    if (result.failed())
    {
        const juce::ScopedLock lock (logLock);
        logLines.add (scriptName + " error: " + result.getErrorMessage());
    }
    return value;
}

void MaxScript::deliver (int inlet, const juce::String& message, const juce::Array<juce::var>& values)
{
    call ("__deliver", { inlet, message, juce::var (values) });
}

void MaxScript::advanceTo (double milliseconds)
{
    call ("__advanceTo", { milliseconds });
}

double MaxScript::nextTaskDue()
{
    return (double) call ("__nextDue", {});
}

juce::StringArray MaxScript::takeLog()
{
    const juce::ScopedLock lock (logLock);
    auto lines = logLines;
    logLines.clear();
    return lines;
}
} // namespace twosl::plugin
