"""Every number a build computes and writes goes through `generated_number`, so every machine writes the same bytes
(architecture/overview.md, "Generated numbers").

Why: Python's +, -, *, / and sqrt are IEEE 754 and the same everywhere, but math.sin / cos / tan / exp / log / pow,
cmath and `**` with a float call the platform's maths library, which may round the last bit differently (glibc vs
macOS's libm). A design computed through them (the half-band's coefficients, a fitted curve) then differs in the last
digits between machines: 2sl filter's oversampler coefficients came out 0.9497427837050028 on one Mac and
0.9497427837050002 here, 2.6e-15 apart.

The rule, by what the value is:
- a float (or int): it may carry a maths library's last bits, so it is rounded to SIGNIFICANT_DIGITS significant
  digits (both of the above are 0.9497427837);
- a fractions.Fraction: exact rational arithmetic, the same on every machine, so it is written as the double nearest
  it, every digit kept (a polyBLEP's 1/24, an antiderivative's constants from rounded pieces, where rounding again
  would open a gap that an antiderivative's difference quotient divides by a tiny step).
Where the number is computed, so the Python model and the written code hold the same number.

The digit count, 10:
- The noise it has to swallow: measured 2026-10-21 by building every device with every libm result moved 1 to 4
  units in the last place (tests/test_generated_numbers.py does the same to the fixture device): the computed
  constants moved by at most 3.2e-15 of their value; the Mac-vs-Linux filter build differed by at most 2.6e-15.
- A constant still differs between machines when it lies within that noise of a rounding midpoint. At 10 digits a
  step is 1e-10 to 1e-9 of the value, so that chance is under 2 x 3.2e-15 / 1e-10 = 6.4e-5 per constant (about 1e-5
  on average over leading digits): over the few hundred computed constants the five devices write, all of them land
  the same in well over 99 % of machine pairs. At 12 digits it would be about 0.6 % a constant, so roughly every
  other pair of machines would build some device differently: too often.
- What it costs: a constant moves by at most 5e-10 of itself (-186 dB), 240 times finer than float32's precision;
  gen~ and the plugins compute in double, and no filter, curve or table the kit has is that sensitive (the half-band
  pairs' 99.3 / 100 dB stop bands need about 1e-5).

The check: `check_generated_text` fails the build on a decimal literal with more than SIGNIFICANT_DIGITS significant
digits that generated_number didn't write from a Fraction (a computed float that skipped the rule, or one typed by
hand: the same rule holds for both). device_build checks every file it writes, the plugin layer every generated file.
The one exception: a number the Live parameter lock holds (a parameter's range or initial value,
src/live-parameters.lock.json), which can't change without changing what Live knows the parameter by, and which the
lock already holds to the byte on every machine (a machine whose maths library made it differently fails the lock
check).
"""
import math
import re
from fractions import Fraction

from twosl_dsp.build_error import BuildError

SIGNIFICANT_DIGITS = 10

# a decimal literal (a point or an exponent; integers can't carry libm noise), not part of a name, a hex literal or a
# longer number
_DECIMAL_LITERAL = re.compile(r"(?<![\w.])(?:\d+\.\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+)(?![\w.])")

# the longer literals generated_number wrote from Fractions (their repr, unsigned): what the check lets through
_WRITTEN_FROM_FRACTIONS = set()


def generated_number(value):
    """`value` as a build writes it, a float: a float or int rounded to SIGNIFICANT_DIGITS significant digits (its repr,
    str and json.dumps have at most that many), a Fraction the double nearest it (see the module docstring)."""
    if isinstance(value, Fraction):
        number = float(value)                    # correctly rounded: the same double on every machine
        if significant_digits(repr(abs(number))) > SIGNIFICANT_DIGITS:
            _WRITTEN_FROM_FRACTIONS.add(repr(abs(number)))
        return number
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BuildError(f"generated_number: a generated number is a finite int, float or Fraction, got {value!r}")
    return float(f"{value:.{SIGNIFICANT_DIGITS}g}")


def significant_digits(literal):
    """How many significant digits a decimal literal has ("0.00120" has 2, "52.0" 2, "1e-05" 1)."""
    mantissa = re.split(r"[eE]", literal)[0].replace(".", "")
    return len(mantissa.strip("0")) or 1


def unrounded_literals(text):
    """[(offset, literal)]: each decimal literal in `text` with more than SIGNIFICANT_DIGITS significant digits."""
    return [(found.start(), found.group(0)) for found in _DECIMAL_LITERAL.finditer(text)
            if significant_digits(found.group(0)) > SIGNIFICANT_DIGITS]


def literals_held_by_the_lock(lock_text):
    """The longer literals the Live parameter lock's text holds (the exception in the module docstring)."""
    return frozenset(literal for _, literal in unrounded_literals(lock_text))


def check_generated_text(text, where, held_by_the_lock=frozenset()):
    """Fails the build when `text` (a file the build writes) holds a longer number that generated_number didn't
    write from a Fraction and the Live parameter lock doesn't hold (`literals_held_by_the_lock`)."""
    found = [(offset, literal) for offset, literal in unrounded_literals(text)
             if literal not in held_by_the_lock and literal not in _WRITTEN_FROM_FRACTIONS]
    if found:
        shown = "; ".join(f"{literal} after {' '.join(text[max(0, offset - 40):offset].split())!r}"
                          for offset, literal in found[:5])
        raise BuildError(f"{where}: {len(found)} number(s) with more than {SIGNIFICANT_DIGITS} significant digits "
                         f"({shown}{' ...' if len(found) > 5 else ''}) that didn't go through "
                         "twosl_dsp.generated_numbers.generated_number: a float computed through a maths library differs "
                         "in its last digits between machines; pass it through generated_number where it is computed "
                         "(a Fraction keeps every digit, a float is rounded)")
