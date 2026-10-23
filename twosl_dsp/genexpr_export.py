"""A device's gen~ code as C for a plugin: the renderer's C (twosl_dsp/genexpr.py's CTranslator), made fit to run outside
Python. A plugin (2sl filter's, JUCE) compiles the .c and drives it through the .h; the gen~ code stays the one copy
of the DSP.

What changes from the renderer's C, and why:
* The sample rate is an argument of the render function: a host chooses it, and can change it.
* The noise source and the sample rate are thread-local: a host renders several instances on several threads at once.
* Every name starts with the program's prefix, so several programs can link into one plugin.
* The header describes the program (Params with their defaults and ranges, Histories with their initial values, the
  delay memory) and seeds the noise as random.Random(seed) does, so a plugin starts where GenProgram starts.

Built with the renderer's flags (genexpr.COMPILER_FLAGS: no contraction, no fast math, libm for every function) the
render is the renderer's bits; at -O2 with the same floating-point flags it should be too (the plugin's parity test
checks that).

    python3 -m twosl_dsp.genexpr_export PREFIX INPUTS OUTPUTS < code.genexpr   # writes PREFIX.c and PREFIX.h
"""
import re
import sys

from twosl_dsp.build_error import BuildError
from twosl_dsp.genexpr import COMPILER_FLAGS, CTranslator, GenExprError, analyze, c_double_literal

PREFIX_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# the renderer's flags that matter to the bits (the rest are how it builds a shared library)
FLOATING_POINT_FLAGS = tuple(flag for flag in COMPILER_FLAGS if flag.startswith(("-ffp-", "-fno-")))

NOISE_STATE_TYPEDEF = "typedef struct { uint32_t words[624]; int32_t index; } genexpr_noise_state;"
NOISE_SOURCE_DECLARATION = "static genexpr_noise_state *genexpr_noise_source;"
RENDER_SIGNATURE = ("void genexpr_render(long sample_count, const double *params, double *histories, "
                    "double *delay_memory, long *delay_positions, const double *const *inputs, "
                    "double *const *outputs, genexpr_noise_state *noise) {")

# Python's random.seed(n) for 0 <= n < 2**32 (Modules/_randommodule.c: init_genrand, init_by_array with one key word)
NOISE_SEED_C = r"""
void PREFIX_noise_seed(genexpr_noise_state *noise, uint32_t seed) {
    uint32_t *mt = noise->words;
    uint32_t i = 1, j = 0, k;
    mt[0] = 19650218U;
    for (k = 1; k < 624; k++) mt[k] = 1812433253U * (mt[k - 1] ^ (mt[k - 1] >> 30)) + k;
    for (k = 624; k; k--) {
        mt[i] = (mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525U)) + seed + j;
        i++; j = 0;
        if (i >= 624) { mt[0] = mt[623]; i = 1; }
    }
    for (k = 623; k; k--) {
        mt[i] = (mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941U)) - i;
        i++;
        if (i >= 624) { mt[0] = mt[623]; i = 1; }
    }
    mt[0] = 0x80000000U;
    noise->index = 624;
}
"""


class RuntimeSampleRateTranslator(CTranslator):
    """CTranslator with the sample rate read from a thread-local the render function sets."""

    def __init__(self, program, info):
        super().__init__(program, info, 44100.0)
        self.constants["samplerate"] = "genexpr_samplerate"

    def call_value(self, node):
        if node.name in ("mstosamps", "sampstoms"):
            prefix, arguments = self.operands_in_python_order(node.arguments, self.value)
            if node.name == "mstosamps":
                return f"({prefix}{arguments[0]} * genexpr_samplerate / 1000.0)"
            return f"({prefix}{arguments[0]} * 1000.0 / genexpr_samplerate)"
        return super().call_value(node)


def replace_once(text, old, new, what):
    if text.count(old) != 1:
        raise GenExprError(f"internal error: the renderer's C changed ({what}); twosl_dsp/genexpr_export.py needs "
                           "updating to match", 0, 0)
    return text.replace(old, new)


def export_c(code, num_inputs, num_outputs, prefix):
    """(C source, header source) of a GenExpr program, its names prefixed with `prefix`."""
    if not PREFIX_PATTERN.match(prefix):
        raise ValueError(f"genexpr_export: the prefix '{prefix}' must be a lower-case C identifier")
    program, info = analyze(code, num_inputs, num_outputs)
    without_default = [name for name, param in info.params.items() if param.default is None]
    if without_default:
        raise BuildError(f"genexpr_export: Params {without_default} have no default in this code (the build writes "
                         "each from the Init values): export the code as the device's patch built it "
                         "(DevicePatchBuilder.gen_code_as_built)")
    source = RuntimeSampleRateTranslator(program, info).translate()
    source = replace_once(source, NOISE_STATE_TYPEDEF, f'#include "{prefix}.h"', "the noise state's typedef")
    source = replace_once(source, NOISE_SOURCE_DECLARATION,
                          "static __thread genexpr_noise_state *genexpr_noise_source;\n"
                          "static __thread double genexpr_samplerate;", "the noise source")
    source = replace_once(source, RENDER_SIGNATURE,
                          f"void {prefix}_render(long sample_count, double samplerate, const double *params, "
                          "double *histories, double *delay_memory, long *delay_positions, "
                          "const double *const *inputs, double *const *outputs, genexpr_noise_state *noise) {\n"
                          "    genexpr_samplerate = samplerate;", "the render function's signature")
    source = NOTICE + source + NOISE_SEED_C.replace("PREFIX", prefix)
    return source, header(info, num_inputs, num_outputs, prefix)


NOTICE = "/* Generated by 2sl-dsp's genexpr_export.py from a device's gen~ code. Don't edit: edit the gen~ code. */\n"


def c_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def c_doubles(values):
    return "{" + ", ".join(c_double_literal(value) for value in values) + "}" if values else "{0}"


def header(info, num_inputs, num_outputs, prefix):
    upper = prefix.upper()
    # a program with a Data says where its memory is in delay_memory; every other program's header is as before Data
    memory_note = (f"({upper}_DELAY_MEMORY doubles: the Delays', then the Datas'; zeroed at the start) " if info.data
                   else "(zeroed at the start) ")
    params = list(info.params.values())
    histories = list(info.histories.values())
    lowest = [param.minimum if param.minimum is not None else -1e308 for param in params]
    highest = [param.maximum if param.maximum is not None else 1e308 for param in params]
    names = ", ".join(c_string(param.name) for param in params) or "0"
    history_names = ", ".join(c_string(history.name) for history in histories) or "0"
    return NOTICE + f"""#ifndef {upper}_H
#define {upper}_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {{
#endif

#ifndef GENEXPR_NOISE_STATE_DEFINED
#define GENEXPR_NOISE_STATE_DEFINED
{NOISE_STATE_TYPEDEF}
#endif

enum {{
    {upper}_INPUTS = {num_inputs},
    {upper}_OUTPUTS = {num_outputs},
    {upper}_PARAMS = {len(params)},
    {upper}_HISTORIES = {len(histories)},
    {upper}_DELAYS = {len(info.delays)},
    {upper}_DELAY_MEMORY = {info.memory_size}
}};

/* the Params in the order params[] holds them: name, default, lowest, highest (unbounded: +-1e308) */
static const char *const {prefix}_param_names[] = {{{names}}};
static const double {prefix}_param_defaults[] = {c_doubles([param.default for param in params])};
static const double {prefix}_param_lowest[] = {c_doubles(lowest)};
static const double {prefix}_param_highest[] = {c_doubles(highest)};
/* the Histories by name and their values at the start (and after a reset) */
static const char *const {prefix}_history_names[] = {{{history_names}}};
static const double {prefix}_history_initials[] = {c_doubles([history.initial for history in histories])};

/* Renders sample_count samples. params: {upper}_PARAMS values (clamp them to their range, as gen~ does).
   histories, delay_memory {memory_note}and delay_positions (zeroed): the program's state, kept by the
   caller between calls. inputs / outputs: one array of sample_count per inlet / outlet. noise: seeded once. */
void {prefix}_render(long sample_count, double samplerate, const double *params, double *histories,
                     double *delay_memory, long *delay_positions, const double *const *inputs,
                     double *const *outputs, genexpr_noise_state *noise);

/* Seeds the noise as Python's random.Random(seed): the renderer's noise for the same seed. */
void {prefix}_noise_seed(genexpr_noise_state *noise, uint32_t seed);

#ifdef __cplusplus
}}
#endif

#endif
"""


def main(argv):
    if len(argv) != 4:
        print("usage: python3 -m twosl_dsp.genexpr_export PREFIX INPUTS OUTPUTS < code", file=sys.stderr)
        return 2
    prefix, num_inputs, num_outputs = argv[1], int(argv[2]), int(argv[3])
    source, header_source = export_c(sys.stdin.read(), num_inputs, num_outputs, prefix)
    with open(f"{prefix}.c", "w", encoding="utf-8") as handle:
        handle.write(source)
    with open(f"{prefix}.h", "w", encoding="utf-8") as handle:
        handle.write(header_source)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
