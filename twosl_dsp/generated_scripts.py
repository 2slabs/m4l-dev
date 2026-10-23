"""Generated scripts: templates filled in by marker, and the ES5 check every generated script passes.

A template marks each place the build fills with `/*MARKER*/` (capitals, digits and _). `fill_template` fills them
all in one pass over the template (text filled in is never searched for markers again) and fails when the template
lacks a marker it was given or keeps one it wasn't: a renamed marker can't silently leave a hole.
"""
import os
import re

from twosl_dsp import es5
from twosl_dsp.build_error import BuildError

KIT_TEMPLATES_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
TEMPLATE_MARKER = re.compile(r"/\*([A-Z][A-Z0-9_]*)\*/")


def kit_template_text(file_name):
    """One of the kit's templates (2sl-dsp/templates/), as text."""
    path = os.path.join(KIT_TEMPLATES_DIRECTORY, file_name)
    if not os.path.isfile(path):
        raise BuildError(f"the kit has no template {file_name} in {KIT_TEMPLATES_DIRECTORY}")
    with open(path, encoding="utf-8") as template_file:
        return template_file.read()


def fill_template(template_text, replacements, template_name):
    """`template_text` with every `/*MARKER*/` replaced by replacements["MARKER"] (marker names without the comment
    delimiters). Fails on a marker the template doesn't have and on one it has but wasn't given."""
    markers_in_template = set(TEMPLATE_MARKER.findall(template_text))
    missing = sorted(set(replacements) - markers_in_template)
    if missing:
        raise BuildError(f"{template_name} has no marker for {', '.join('/*' + m + '*/' for m in missing)}")
    unfilled = sorted(markers_in_template - set(replacements))
    if unfilled:
        raise BuildError(f"{template_name} has markers nothing fills: {', '.join('/*' + m + '*/' for m in unfilled)}")
    return TEMPLATE_MARKER.sub(lambda found: replacements[found.group(1)], template_text)


def check_es5(scripts):
    """Fails unless every script ({file name: text}) compiles as ES5, naming each one that doesn't."""
    problems = []
    for file_name, text in sorted(scripts.items()):
        problem = es5.syntax_problem(text)
        if problem is not None:
            problems.append(f"{file_name}: {problem}")
    if problems:
        raise BuildError("generated scripts that aren't ES5 (Max's [js] would refuse them):\n  " + "\n  ".join(problems))
