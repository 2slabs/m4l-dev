#pragma once

// One running copy of an exported gen~ program: its Params, its state (Histories, delay memory, noise) and render.
// What gen~ does in Max, with the state kept here so a plugin can run several copies (a synth's voices). No JUCE.

#include "PluginTable.h"

#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

namespace twosl::plugin
{
class GenProgram
{
public:
    // the memory (the delays' above all) is allocated here, never while audio runs
    GenProgram (const ProgramSpec& specIn, uint32_t noiseSeedIn)
        : spec (specIn), noiseSeed (noiseSeedIn),
          params ((size_t) std::max (1, spec.paramCount)), histories ((size_t) std::max (1, spec.historyCount)),
          delayMemory ((size_t) std::max (1, spec.delayMemory)), delayPositions ((size_t) std::max (1, spec.delayCount))
    {
        reset();
    }

    // back to the start: Params at their defaults, Histories at their initial values, delays empty, noise reseeded
    void reset()
    {
        std::copy (spec.paramDefaults, spec.paramDefaults + spec.paramCount, params.begin());
        std::copy (spec.historyInitials, spec.historyInitials + spec.historyCount, histories.begin());
        std::fill (delayMemory.begin(), delayMemory.end(), 0.0);
        std::fill (delayPositions.begin(), delayPositions.end(), 0L);
        spec.seed (&noise, noiseSeed);
    }

    // a Param, held in its range as gen~ holds it
    void setParam (int index, double value)
    {
        params[(size_t) index] = std::clamp (value, spec.paramLowest[index], spec.paramHighest[index]);
    }
    double param (int index) const { return params[(size_t) index]; }

    int paramIndex (const char* name) const { return indexOf (spec.paramNames, spec.paramCount, name, "Param"); }
    int historyIndex (const char* name) const { return indexOf (spec.historyNames, spec.historyCount, name, "History"); }

    // a History's value, as if the program had run to it (a voice's oscillator phases at the start)
    void setHistory (int index, double value) { histories[(size_t) index] = value; }
    double history (int index) const { return histories[(size_t) index]; }

    // `count` samples: inputs and outputs are one array of `count` per inlet / outlet
    void render (int count, double sampleRate, const double* const* inputs, double* const* outputs)
    {
        spec.render (count, sampleRate, params.data(), histories.data(), delayMemory.data(), delayPositions.data(),
                     inputs, outputs, &noise);
    }

    const ProgramSpec& programSpec() const { return spec; }

private:
    static int indexOf (const char* const* names, int count, const char* name, const char* what)
    {
        for (int i = 0; i < count; ++i)
            if (std::strcmp (names[i], name) == 0)
                return i;
        throw std::invalid_argument (std::string ("the gen~ program has no ") + what + " '" + name + "'");
    }

    ProgramSpec spec;
    uint32_t noiseSeed;
    std::vector<double> params, histories, delayMemory;
    std::vector<long> delayPositions;
    genexpr_noise_state noise {};
};
} // namespace twosl::plugin
