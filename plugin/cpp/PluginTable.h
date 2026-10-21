#pragma once

// The types a plugin's generated header (m4l_dev/plugin/header.py) fills in: its host parameters and how each reaches
// the device's parts, its Stored Only values, presets and gen~ programs. No JUCE, so tests can build without it.

#include <algorithm>
#include <cmath>
#include <cstdint>

#ifndef GENEXPR_NOISE_STATE_DEFINED
#define GENEXPR_NOISE_STATE_DEFINED
typedef struct { uint32_t words[624]; int32_t index; } genexpr_noise_state;
#endif

namespace twosl::plugin
{
enum class Kind { Float, Int, Choice, Button };
enum class RouteKind { Gen, Message, Raw };

// One way a parameter reaches the device: a gen~ program's Param (`target`), a script's message, or a bare number
// into a box. Its value: a number x scale + offset; a choice's choices[index]; a tempo route's beats[index] x 60000 /
// the tempo (milliseconds of the host's tempo).
struct Route
{
    int destination;
    RouteKind kind;
    int target;
    const char* message;
    double scale, offset;
    const double* choices;
    const double* beats;

    bool followsTempo() const { return beats != nullptr; }

    double value (double held, int itemCount, double tempo) const
    {
        const auto index = std::clamp ((int) std::lround (held), 0, std::max (0, itemCount - 1));
        if (beats != nullptr)
            return beats[index] * 60000.0 / std::max (tempo, 1.0);
        if (choices != nullptr)
            return choices[index];
        return held * scale + offset;
    }
};

// One host parameter: Live's range, exponent (value = minimum + (maximum - minimum) * normalised ^ exponent), its
// neutral value (Live's initial value, the double-click target: the host's default), its start value (a fresh
// instance's, the Init sound; a host restoring a state sets every value after) and unit style (Live's: 0 int, 1 float, 2 ms, 3 Hz, 4 dB, 5 %, -1 none), its menu items, its routes. A Button
// (no routes) is the plugin's to handle: every change is a press.
struct Parameter
{
    const char* id;
    const char* name;
    Kind kind;
    double minimum, maximum, exponent, neutral, start;
    int unitStyle;
    int itemCount;
    const char* const* items;
    int routeCount;
    const Route* routes;
};

// One of Live's Stored Only values: the plugin's state, never a host parameter (a machine's stored steps).
struct Stored
{
    const char* id;
    const char* name;
    double initial;
    int routeCount;
    const Route* routes;
};

struct Preset
{
    const char* name;
    const double* values; // one a parameter, as Live holds it
    const double* stored; // one a Stored value (or nullptr)
};

// One exported gen~ program (m4l_dev/genexpr_export.py): its render and noise seeding, and what it holds.
struct ProgramSpec
{
    void (*render) (long, double, const double*, double*, double*, long*, const double* const*, double* const*,
                    genexpr_noise_state*);
    void (*seed) (genexpr_noise_state*, uint32_t);
    int inputs, outputs;
    int paramCount;
    const char* const* paramNames;
    const double* paramDefaults;
    const double* paramLowest;
    const double* paramHighest;
    int historyCount;
    const char* const* historyNames;
    const double* historyInitials;
    int delayMemory, delayCount;
};
} // namespace twosl::plugin
