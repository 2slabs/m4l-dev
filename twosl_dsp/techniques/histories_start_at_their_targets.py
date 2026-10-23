"""Histories that start at their targets (a technique): on the code's first sample, each named History is set to its
target, so a smoother (a one-pole glide, a tape's time) or a delay ring starts where its control already is, and
nothing glides when the device loads (references/dsp.md, "Histories start at their targets").

Why a technique: a gen~ History starts at a constant written in the code, and a control's starting value is the
device's Init (2sl-dsp architecture/presets.md: the build writes each control-set Param's default from Init, one
source). A History started at a hand-written constant is a second copy of Init that drifts from it (2sl stab's echo
started at 363 ms while its Time Param started at 375 ms, and glided there on load). Starting at the target on the
first sample needs no copy: the target is the Param (or what the code makes of it) as it is on that sample.

The block owns one History, `<name>_started` (0, then 1 from the first sample on). It sets Histories the caller
declares (each History's own initial value is then never read before the first sample overwrites it: write 0). Its
statements go where every target is computed and before any of the Histories is read or updated, so on the first
sample each smoother's step is from its target to its target: the same value, bit for bit, as a History whose constant
already equalled the target.

Inputs: `targets`, {History name: GenExpr expression} (evaluated on the first sample only).
"""
from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import GEN_IDENTIFIER, Technique


class HistoriesStartAtTheirTargets(Technique):
    """See the module docstring."""

    def __init__(self, instance_name, *, targets):
        if not targets:
            raise BuildError(f"HistoriesStartAtTheirTargets {instance_name}: no Histories to start")
        for history_name in targets:
            if not GEN_IDENTIFIER.match(history_name):
                raise BuildError(f"HistoriesStartAtTheirTargets {instance_name}: {history_name!r} is not a lower-case "
                                 "GenExpr identifier (a History's name)")
        super().__init__(instance_name, **targets)
        self.latency_samples = 0       # no signal passes through it: it sets Histories on the first sample
        self.history_names = list(targets)

    def declarations(self):
        return self.substituted("History ${p}_started(0);")

    def statements(self):
        assignments = "".join(f"\n\t{history_name} = ${{{history_name}}};" for history_name in self.history_names)
        return self.substituted(f"""// ${{p}}: the Histories start at their targets on the first sample (kit technique)
if (${{p}}_started == 0) {{
	${{p}}_started = 1;{assignments}
}}""")
