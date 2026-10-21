#pragma once

// A device's Max [js] script (its brain) running unchanged in a plugin, in JUCE's JavascriptEngine (QuickJS), with
// the few Max globals a 2sl brain uses: outlet, inlet, messagename, inlets / outlets, arrayfromargs, post, error and
// Task. Messages reach it as Max delivers them (a function named like the message, else anything()), as the kit's
// node sandbox does for the device's own tests (tools/max_sandbox.js). Task runs on a clock the plugin moves
// (advanceTo), so a plugin can fire a script's timers at the exact sample.

#include <juce_javascript/juce_javascript.h>

#include <vector>

namespace twosl::plugin
{
class MaxScript
{
public:
    // one message out of the script: its outlet and its values (numbers or text)
    struct Output
    {
        int outlet;
        juce::Array<juce::var> values;
    };

    // `name` is the script's file name, for messages in the log
    MaxScript (const juce::String& source, const juce::String& name);

    // a message into an inlet ("list" with a note's pitch and velocity, "tick" with a song position ...): what the
    // script sent back is in outputs() until clearOutputs()
    void deliver (int inlet, const juce::String& message, const juce::Array<juce::var>& values);

    // the script's clock in milliseconds: every Task due by `milliseconds` fires, in order, at its own time
    void advanceTo (double milliseconds);
    // when the next Task is due (ms on the same clock), or a negative number when none is running
    double nextTaskDue();

    std::vector<Output>& outputs() { return sent; }
    void clearOutputs() { sent.clear(); }

    // what the script posted and its errors (Max's window): read and cleared by the plugin, never on the audio thread
    juce::StringArray takeLog();

private:
    juce::var call (const char* function, const juce::Array<juce::var>& arguments);

    juce::String scriptName;
    juce::JavascriptEngine engine;
    std::vector<Output> sent;
    juce::CriticalSection logLock;
    juce::StringArray logLines;
};
} // namespace twosl::plugin
