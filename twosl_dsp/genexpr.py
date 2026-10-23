#!/usr/bin/env python3
"""Offline GenExpr (Max gen~ codebox) syntax checker and sample renderer.

IMPORTANT: this is a SUBSET checker written by us. It is NOT Cycling '74's
compiler. Code accepted here is not guaranteed to compile in Max, and code
rejected here may be valid gen~. Anything outside the subset below is rejected
with a GenExprError carrying a line:col, never silently ignored.

Subset
------
* Comments: // ... and /* ... */
* Function definitions first: name(a, b) { ... }  (only arguments, own locals,
  builtins and constants; `return expr;` allowed; falling off the end returns 0).
* Then declarations: Param name(default[, min=X][, max=Y]); History a(0), b(1);
  A Param may leave its default out (`Param name(min=X, max=Y);`, `Param name;`): its default is then the value the
  device's Init values send it, which the patch builder writes into the code it builds
  (code_with_param_defaults; twosl_dsp/patch_builder.py). GenProgram makes such a Param be set before it runs.
  Delay d(size[, taps]);  (d.read(t[, interp="none"|"linear"|"cubic"|"spline"]), d.write(x);)
  A Delay is read at most `taps` times in the code (default 1): Max's delay operator has one read tap per
  "tap inlet/outlet pair" (its second argument), and code that reads one Delay at two places declares 2
  (references/dsp.md, "gen~ delay taps").
  Data name(size);  one channel of `size` doubles, zeroed at the start and kept between samples: peek(name, index)
  reads sample `index` (floored; out of range or NaN reads 0), poke(name, value, index); writes it (out of range or
  NaN: nothing written), as gen~'s data, peek and poke with their default boundmode "ignore" (references/dsp.md, "gen~
  data, peek and poke"). Not inside a function, as a Delay.
* Then statements: x = expr; if (...) {...} else if (...) {...} else {...};
  d.write(expr); poke(name, value, index); outN = expr; (braces required, plain `=` only).
* Bounded loops only: for (i = START; i < LIMIT; i += STEP) { ... } (or i <= LIMIT), START, LIMIT and STEP number
  literals, STEP > 0, the counter a new name that the body reads but never assigns, so the loop runs at most
  `bounded_loop_iterations` times whatever its body does; break; and continue; inside it. That is gen~'s own `for`
  (Cycling '74's GenExpr guide: "Branching and looping is supported in GenExpr with if/else, for and while
  constructs"; references/dsp.md, "gen~ (what Max accepts)"), narrowed to a count known when the code is checked: a
  `while`, or a `for` whose count is not, is refused (gen~ only guards against an infinite loop at run time).
  `+=` is accepted in a for's step only (the guide's own form; gen~ has no `++`). The counter is a float, as in gen~.
* Expressions: numbers, identifiers, calls, parentheses, unary - and !,
  * / %   + -   < > <= >=   == !=   &&   ||   and right-associative a ? b : c.
* Inputs in1..inN (read only), outputs out1..outN (write only).
* Constants samplerate pi twopi halfpi e; builtins listed in BUILTIN_ARITY.
* Scoping: a local belongs to the block where it is first assigned; reading it
  outside that block is an error. Locals do not persist between samples;
  History values do.

Design decisions where the task text left room
----------------------------------------------
* A Param default outside its own [min, max] is an error (not clamped).
* interp="spline" is Catmull-Rom (Max's delay reference: "spline" performs four-point Catmull-Rom spline
  interpolation). interp="cubic" is rendered as the same Catmull-Rom here, but Max documents it only as
  "four-point cubic interpolation" without its formula: the kit's blocks use "spline".
* Delay size must be a positive integer literal; interp="none" truncates the
  delay time (floor); out-of-range delay time is clamped to [0, size-1];
  a NaN delay time yields NaN.
* Reading an outN, assigning to a function name or builtin name, unary plus,
  string literals outside interp="...", and expression statements other than
  d.write(x); are errors.
* Function arguments may be reassigned (they are locals of the function).

Rendering
---------
GenProgram translates the program to C once, builds it with the system C compiler ($CC, default `cc`) into a cache
directory ($TWOSL_DSP_GENEXPR_CACHE, default ~/.cache/2sl-dsp/genexpr; one shared library per program text, compiler and
flags) and runs it through ctypes: about 25x the speed of rendering in Python (2sl gate's core: 3.5 s -> 0.14 s per
second of audio at 44.1 kHz). No compiler: CLibraryBuildError, saying so. Checking (check, analyze) needs no compiler.
The C reproduces CPython's arithmetic: every non-NaN value is the bits Python's float and math module give for the
same expressions (and noise() is random.Random(seed).random()'s sequence); a NaN comes out where Python's would, with
its sign and payload left open, as IEEE 754 leaves them.

Usage
-----
    python3 -m twosl_dsp.genexpr check FILE [FILE...]
"""

import array
import ctypes
import functools
import math
import os
import random
import re
import sys
from dataclasses import dataclass, field

from twosl_dsp.build_error import BuildError
from twosl_dsp.c_library_cache import load_c_library


class GenExprError(BuildError):
    """A syntax or semantic error with a 1-based line and column. A subclass of BuildError because its callers need
    the position (`line`, `col`, `message`): gen_box wraps it with the box, the command-line checker prints it as
    path:line:col."""

    def __init__(self, message, line, col):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def __str__(self):
        return f"line {self.line}:{self.col}: {self.message}"


# ----------------------------------------------------------------------------
# Language tables
# ----------------------------------------------------------------------------

CONSTANT_NAMES = frozenset({"samplerate", "pi", "twopi", "halfpi", "e"})

BUILTIN_ARITY = {
    "abs": 1, "sign": 1, "floor": 1, "ceil": 1, "trunc": 1, "fract": 1,
    "min": 2, "max": 2, "clamp": 3, "wrap": 3, "mix": 3,
    "exp": 1, "log": 1, "log2": 1, "log10": 1, "pow": 2, "sqrt": 1,
    "sin": 1, "cos": 1, "tan": 1, "tanh": 1, "atan": 1, "atan2": 2,
    "noise": 0, "mstosamps": 1, "sampstoms": 1, "dbtoa": 1, "atodb": 1,
}

DECLARATION_KEYWORDS = frozenset({"Param", "History", "Delay", "Data"})
STATEMENT_KEYWORDS = frozenset({"if", "else", "return", "for", "while", "break", "continue"})
RESERVED_WORDS = DECLARATION_KEYWORDS | STATEMENT_KEYWORDS

INPUT_NAME_PATTERN = re.compile(r"^in(\d+)$")
OUTPUT_NAME_PATTERN = re.compile(r"^out(\d+)$")

DELAY_INTERPOLATION_MODES = ("none", "linear", "cubic", "spline")

# gen~'s operators on a Data, which take its name as their first argument (their argument counts): peek(name, index)
# reads, poke(name, value, index); writes. Not in BUILTIN_ARITY: their first argument is a Data, not a value.
DATA_OPERATORS = {"peek": 2, "poke": 3}

# The most iterations a for loop's header may allow: ours (gen~ states no limit, only a run-time guard against
# infinite loops), far above any loop a block runs a sample (the LTC1060 section's ticks: 138), so a header that
# allows more is a mistake, refused when the code is checked.
MAXIMUM_LOOP_ITERATIONS = 65536

# Operators we recognise only to refuse them with a helpful message.
UNSUPPORTED_OPERATORS = ("+=", "-=", "*=", "/=", "%=", "<<", ">>", "**", "&", "|", "^", "~")
SUPPORTED_MULTI_OPERATORS = ("&&", "||", "==", "!=", "<=", ">=")
SINGLE_CHARACTER_OPERATORS = "+-*/%<>=!?:;,(){}."

BINARY_PRECEDENCE_LEVELS = (
    ("||",),
    ("&&",),
    ("==", "!="),
    ("<", ">", "<=", ">="),
    ("+", "-"),
    ("*", "/", "%"),
)
BINARY_OPERATOR_LEVELS = {operator: level for level, operators in enumerate(BINARY_PRECEDENCE_LEVELS)
                          for operator in operators}
COMPARISON_OPERATORS = frozenset({"<", ">", "<=", ">=", "==", "!="})


# ----------------------------------------------------------------------------
# Tokenizer
# ----------------------------------------------------------------------------

@dataclass
class Token:
    kind: str   # "number" | "ident" | "string" | "op" | "eof"
    text: str
    line: int
    col: int

    @property
    def end_col(self):
        return self.col + len(self.text)


# One pattern for every token and everything between tokens, tried in the order the alternatives are written; the
# group that matched (`lastgroup`) says which. A number is digits (any Unicode decimal digits, as Python's \d) with an
# optional fraction and exponent, or a leading-dot fraction (before the operators: ".5" is a number, "." alone an
# operator). The operators: the supported two-character ones, the refused two-character ones (compound assignment and
# friends, tokens so that the parser can name them), then the single characters; a refused single character fails here.
TWO_CHARACTER_OPERATORS = SUPPORTED_MULTI_OPERATORS + tuple(o for o in UNSUPPORTED_OPERATORS if len(o) == 2)
UNSUPPORTED_SINGLE_CHARACTERS = "".join(o for o in UNSUPPORTED_OPERATORS if len(o) == 1)
TOKEN_PATTERN = re.compile(r"""
    (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<space>[ \t\r\n]+)
  | (?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
  | (?P<line_comment>//[^\n]*)
  | (?P<block_comment>/\*.*?\*/)
  | (?P<unterminated_block_comment>/\*)
  | (?P<op>%s|[%s])
  | (?P<string>"[^"\n]*")
  | (?P<unterminated_string>")
  | (?P<unsupported_operator>[%s])
""" % ("|".join(re.escape(operator) for operator in TWO_CHARACTER_OPERATORS), re.escape(SINGLE_CHARACTER_OPERATORS),
       re.escape(UNSUPPORTED_SINGLE_CHARACTERS)), re.DOTALL | re.VERBOSE)


NEWLINE_PATTERN = re.compile(r"\n")

# Numbers Max's GenExpr lexer refuses though they are numbers here (references/dsp.md, "gen~ numbers"):
# - an exponent with a sign of '+' (its grammar's exponent is e or E, then an optional '-', then digits: genpatcher's
#   GenExpr.Language, read 2026-10-21);
# - a whole-number mantissa with a two-digit positive exponent: Max's parser stopped at the bbd's History initial -1e18
#   ("function call missing '('", found by a probe device of every prefix of the code, 2026-10-21), while 1e9 and
#   -1.4528355093231122e-05 compile in every 2sl device. Why its lexer splits it isn't read; the measured line is.
MAX_REFUSED_PLUS_EXPONENT = re.compile(r"[eE]\+")
MAX_REFUSED_WHOLE_MANTISSA_LONG_EXPONENT = re.compile(r"^\d+[eE]\d{2,}$")


def refused_by_max_number_lexer(text):
    """Why Max's GenExpr would refuse the number `text`, or None (see MAX_REFUSED_*)."""
    if MAX_REFUSED_PLUS_EXPONENT.search(text):
        return "Max's GenExpr has no '+' in an exponent (write 1e9, not 1e+9)"
    if MAX_REFUSED_WHOLE_MANTISSA_LONG_EXPONENT.match(text):
        return ("Max's GenExpr parser refused a whole-number mantissa with a two-digit positive exponent (-1e18, 2026-10-21): "
                "write it as a number Max has compiled (1e9, or digits)")
    return None


def tokenize(code):
    tokens = []
    position = 0
    line = 1
    line_start = 0
    length = len(code)
    match_token_at = TOKEN_PATTERN.match
    while position < length:
        match = match_token_at(code, position)
        col = position - line_start + 1
        if match is None:
            raise GenExprError(f"unexpected character {code[position]!r}", line, col)
        kind = match.lastgroup
        text = match.group()
        end = match.end()
        if kind == "ident" or kind == "op":
            tokens.append(Token(kind, text, line, col))
        elif kind == "space" or kind == "block_comment":
            newlines_inside = text.count("\n")
            if newlines_inside:
                line += newlines_inside
                line_start = position + text.rindex("\n") + 1
        elif kind == "line_comment":
            pass
        elif kind == "number":
            following = code[end:end + 1]
            if following and (following.isalpha() or following == "_"):
                raise GenExprError(f"malformed number '{text}{following}'", line, col)
            refused = refused_by_max_number_lexer(text)
            if refused:
                raise GenExprError(f"number '{text}': {refused}", line, col)
            tokens.append(Token("number", text, line, col))
        elif kind == "string":
            tokens.append(Token("string", text[1:-1], line, col))
        elif kind == "unterminated_block_comment":
            raise GenExprError("unterminated /* comment", line, col)
        elif kind == "unterminated_string":
            raise GenExprError("unterminated string literal", line, col)
        elif kind == "unsupported_operator":
            raise GenExprError(f"operator '{text}' is not supported in this GenExpr subset", line, col)
        else:
            raise GenExprError(f"internal error: the token pattern matched an unknown group {kind!r}", line, col)
        position = end
    tokens.append(Token("eof", "", line, position - line_start + 1))
    return tokens


# ----------------------------------------------------------------------------
# AST
# ----------------------------------------------------------------------------

@dataclass
class Node:
    line: int
    col: int


@dataclass
class Number(Node):
    value: float


@dataclass
class Name(Node):
    name: str


@dataclass
class Unary(Node):
    operator: str
    operand: "Node"


@dataclass
class Binary(Node):
    operator: str
    left: "Node"
    right: "Node"


@dataclass
class Ternary(Node):
    condition: "Node"
    when_true: "Node"
    when_false: "Node"


@dataclass
class Call(Node):
    name: str
    arguments: list


@dataclass
class MethodCall(Node):
    object_name: str
    method: str
    arguments: list
    keywords: dict   # keyword -> Token (string token)


@dataclass
class Block(Node):
    statements: list


@dataclass
class Assign(Node):
    name: str
    expression: "Node"


@dataclass
class If(Node):
    branches: list   # [(condition, Block)]
    else_block: "Block | None"


@dataclass
class Return(Node):
    expression: "Node"


@dataclass
class For(Node):
    """for (counter = start; counter < limit (<= when `inclusive`); counter += step) body: bounded by its literals."""
    counter: str
    start: float
    limit: float
    inclusive: bool
    step: float
    body: Block

    @property
    def bounded_loop_iterations(self):
        """How many times the body runs at most (break leaves sooner), counted the way the C runs it (float steps);
        None when that is more than MAXIMUM_LOOP_ITERATIONS or the step is lost in the counter's rounding."""
        if (self.limit - self.start) / self.step > MAXIMUM_LOOP_ITERATIONS:
            return None
        iterations = 0
        counter = self.start
        while counter < self.limit or (self.inclusive and counter == self.limit):
            iterations += 1
            if counter + self.step == counter or iterations > MAXIMUM_LOOP_ITERATIONS:
                return None
            counter = counter + self.step
        return iterations


@dataclass
class Break(Node):
    pass


@dataclass
class Continue(Node):
    pass


@dataclass
class MethodStatement(Node):
    call: MethodCall


@dataclass
class FunctionDef(Node):
    name: str
    parameters: list   # [(name, line, col)]
    body: Block


@dataclass
class ParamDecl(Node):
    name: str
    default: "float | None"     # None: left out of the code, the Init values give it (code_with_param_defaults)
    minimum: "float | None"
    maximum: "float | None"


@dataclass
class HistoryDecl(Node):
    name: str
    initial: float


@dataclass
class DelayDecl(Node):
    name: str
    size: int
    taps: int = 1


@dataclass
class DataDecl(Node):
    name: str
    size: int


@dataclass
class PokeStatement(Node):
    data_name: str
    value: "Node"
    index: "Node"


@dataclass
class Program:
    functions: list = field(default_factory=list)
    declarations: list = field(default_factory=list)
    statements: list = field(default_factory=list)


# ----------------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------------

PHASE_FUNCTIONS, PHASE_DECLARATIONS, PHASE_STATEMENTS = 0, 1, 2


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        self.previous_token = None

    # -- token helpers --
    def peek(self, offset=0):
        index = self.index + offset
        return self.tokens[index] if index < len(self.tokens) else self.tokens[-1]

    def advance(self):
        token = self.tokens[self.index]
        if token.kind != "eof":
            self.index += 1
        self.previous_token = token
        return token

    def at_op(self, text, offset=0):
        token = self.peek(offset)
        return token.kind == "op" and token.text == text

    def at_word(self, text, offset=0):
        token = self.peek(offset)
        return token.kind == "ident" and token.text == text

    @staticmethod
    def describe(token):
        if token.kind == "eof":
            return "end of file"
        if token.kind == "string":
            return f'string "{token.text}"'
        return f"'{token.text}'"

    def fail_at(self, token, message):
        raise GenExprError(message, token.line, token.col)

    def expect_op(self, text, context):
        token = self.peek()
        if token.kind == "op" and token.text == text:
            return self.advance()
        self.fail_at(token, f"expected '{text}' {context}, found {self.describe(token)}")

    def expect_identifier(self, context):
        token = self.peek()
        if token.kind != "ident" or token.text in RESERVED_WORDS:
            self.fail_at(token, f"expected a name {context}, found {self.describe(token)}")
        return self.advance()

    def expect_semicolon(self, context):
        if self.at_op(";"):
            return self.advance()
        anchor = self.previous_token
        raise GenExprError(f"missing ';' {context}", anchor.line, anchor.end_col)

    # -- program --
    def parse_program(self):
        program = Program()
        phase = PHASE_FUNCTIONS
        while self.peek().kind != "eof":
            token = self.peek()
            if self.looks_like_function_definition():
                if phase == PHASE_DECLARATIONS:
                    self.fail_at(token, "function definitions must come before all declarations (found after a declaration)")
                if phase == PHASE_STATEMENTS:
                    self.fail_at(token, "function definitions must come before all statements (found after a statement)")
                program.functions.append(self.parse_function_definition())
            elif token.kind == "ident" and token.text in DECLARATION_KEYWORDS:
                if phase == PHASE_STATEMENTS:
                    self.fail_at(token, f"{token.text} declarations must come before the first statement")
                phase = PHASE_DECLARATIONS
                program.declarations.extend(self.parse_declaration())
            else:
                phase = PHASE_STATEMENTS
                program.statements.append(self.parse_statement())
        return program

    def looks_like_function_definition(self):
        if self.peek().kind != "ident" or self.peek().text in RESERVED_WORDS:
            return False
        if not self.at_op("(", 1):
            return False
        offset = 2
        if self.at_op(")", offset):
            return self.at_op("{", offset + 1)
        while True:
            if self.peek(offset).kind != "ident":
                return False
            offset += 1
            if self.at_op(",", offset):
                offset += 1
                continue
            return self.at_op(")", offset) and self.at_op("{", offset + 1)

    def parse_function_definition(self):
        name_token = self.expect_identifier("for the function")
        self.expect_op("(", "after the function name")
        parameters = []
        if not self.at_op(")"):
            while True:
                parameter = self.expect_identifier("as a function argument")
                parameters.append((parameter.text, parameter.line, parameter.col))
                if self.at_op(","):
                    self.advance()
                    continue
                break
        self.expect_op(")", "after the function arguments")
        body = self.parse_block()
        return FunctionDef(name_token.line, name_token.col, name_token.text, parameters, body)

    # -- declarations --
    def parse_signed_number(self, context):
        sign = 1.0
        if self.at_op("-"):
            self.advance()
            sign = -1.0
        token = self.peek()
        if token.kind != "number":
            self.fail_at(token, f"expected a number {context}, found {self.describe(token)}")
        self.advance()
        return sign * self.number_value(token)

    @staticmethod
    def number_value(token):
        value = float(token.text)
        if math.isinf(value):
            raise GenExprError(f"number literal '{token.text}' is out of range", token.line, token.col)
        return value

    def parse_declaration(self):
        keyword = self.advance()
        if keyword.text == "Param":
            return [self.parse_param_declaration(keyword)]
        if keyword.text == "History":
            return self.parse_history_declaration()
        if keyword.text == "Data":
            return [self.parse_data_declaration()]
        return [self.parse_delay_declaration(keyword)]

    def parse_param_declaration(self, keyword):
        """Param name(default[, min=X][, max=Y]); the default may be left out: Param name(min=X, max=Y); Param name;"""
        name = self.expect_identifier("after Param")
        default = None
        limits = {}
        if self.at_op("("):
            self.advance()
            if self.at_limit_keyword():
                self.parse_param_limit(name, limits)
            elif not self.at_op(")"):
                default = self.parse_signed_number("as the Param default")
            while (default is not None or limits) and self.at_op(","):
                self.advance()
                self.parse_param_limit(name, limits)
            self.expect_op(")", "to close the Param")
        self.expect_semicolon("after the Param declaration")
        minimum, maximum = limits.get("min"), limits.get("max")
        if minimum is not None and maximum is not None and minimum > maximum:
            self.fail_at(name, f"Param {name.text}: min {minimum} is greater than max {maximum}")
        if default is not None and ((minimum is not None and default < minimum)
                                    or (maximum is not None and default > maximum)):
            self.fail_at(name, f"Param {name.text}: default {default} is outside its min/max range")
        return ParamDecl(name.line, name.col, name.text, default, minimum, maximum)

    def parse_param_limit(self, name, limits):
        key = self.peek()
        if not self.at_limit_keyword():
            self.fail_at(key, f"expected min=... or max=... in Param, found {self.describe(key)}")
        self.advance()
        if key.text in limits:
            self.fail_at(key, f"duplicate '{key.text}' in Param {name.text}")
        self.expect_op("=", f"after '{key.text}'")
        limits[key.text] = self.parse_signed_number(f"for '{key.text}'")

    def at_limit_keyword(self):
        token = self.peek()
        return token.kind == "ident" and token.text in ("min", "max") and self.at_op("=", 1)

    def parse_history_declaration(self):
        declarations = []
        while True:
            name = self.expect_identifier("after History")
            self.expect_op("(", "after the History name")
            initial = self.parse_signed_number("as the History initial value")
            self.expect_op(")", "to close the History")
            declarations.append(HistoryDecl(name.line, name.col, name.text, initial))
            if self.at_op(","):
                self.advance()
                continue
            break
        self.expect_semicolon("after the History declaration")
        return declarations

    def parse_delay_declaration(self, keyword):
        name = self.expect_identifier("after Delay")
        self.expect_op("(", "after the Delay name")
        size_token = self.peek()
        size = self.parse_signed_number("as the Delay size")
        if size < 1 or size != int(size):
            self.fail_at(size_token, f"Delay {name.text}: size must be a positive integer literal, got {size}")
        taps = 1
        if self.at_op(","):
            self.advance()
            taps_token = self.peek()
            taps = self.parse_signed_number("as the Delay's number of taps")
            if taps < 1 or taps != int(taps):
                self.fail_at(taps_token, f"Delay {name.text}: taps must be a positive integer literal, got {taps}")
        self.expect_op(")", "to close the Delay")
        if self.at_op(","):
            self.fail_at(self.peek(), "declare one Delay per statement")
        self.expect_semicolon("after the Delay declaration")
        return DelayDecl(name.line, name.col, name.text, int(size), int(taps))

    def parse_data_declaration(self):
        """Data name(size); one channel (gen~'s data takes a channel count third; the kit's subset has one)."""
        name = self.expect_identifier("after Data")
        self.expect_op("(", "after the Data name")
        size_token = self.peek()
        size = self.parse_signed_number("as the Data size")
        if size < 1 or size != int(size):
            self.fail_at(size_token, f"Data {name.text}: size must be a positive integer literal, got {size}")
        if self.at_op(","):
            self.fail_at(self.peek(), f"Data {name.text}: one channel only in this subset (Data name(size);)")
        self.expect_op(")", "to close the Data")
        if self.at_op(","):
            self.fail_at(self.peek(), "declare one Data per statement")
        self.expect_semicolon("after the Data declaration")
        return DataDecl(name.line, name.col, name.text, int(size))

    # -- statements --
    def parse_block(self):
        opening = self.expect_op("{", "to open a block (braces are required)")
        statements = []
        while not self.at_op("}"):
            if self.peek().kind == "eof":
                self.fail_at(opening, "unterminated block: missing '}'")
            statements.append(self.parse_statement())
        self.advance()
        return Block(opening.line, opening.col, statements)

    def parse_statement(self):
        token = self.peek()
        if token.kind == "ident":
            if token.text == "if":
                return self.parse_if()
            if token.text == "else":
                self.fail_at(token, "'else' without a matching 'if'")
            if token.text == "for":
                return self.parse_for()
            if token.text == "while":
                self.fail_at(token, "'while' loops are refused: the kit runs only loops it can bound when it checks the "
                                    "code; write for (i = 0; i < MAXIMUM; i += 1) { ... if (done) { break; } }")
            if token.text in ("break", "continue"):
                self.advance()
                self.expect_semicolon(f"after {token.text}")
                return (Break if token.text == "break" else Continue)(token.line, token.col)
            if token.text == "return":
                self.advance()
                expression = self.parse_expression()
                self.expect_semicolon("after return")
                return Return(token.line, token.col, expression)
            if token.text in DECLARATION_KEYWORDS:
                self.fail_at(token, f"{token.text} declarations are only allowed at the top level, before the first statement")
            following = self.peek(1)
            if following.kind == "op":
                if following.text == "=":
                    self.advance()
                    self.advance()
                    expression = self.parse_expression()
                    self.expect_semicolon("after the assignment")
                    return Assign(token.line, token.col, token.text, expression)
                if following.text in ("+=", "-=", "*=", "/=", "%="):
                    self.fail_at(following, f"compound assignment '{following.text}' is not supported; write x = x {following.text[0]} ...;")
                if following.text == ".":
                    call = self.parse_postfix()
                    self.expect_semicolon("after the method call")
                    return MethodStatement(token.line, token.col, call)
                if following.text == "(" and token.text == "poke":
                    return self.parse_poke_statement()
                if following.text == "(":
                    self.fail_at(token, f"a call to '{token.text}' cannot be used as a statement; assign its result to a variable")
            self.fail_at(following if following.kind != "eof" else token,
                         f"expected '=' after '{token.text}', found {self.describe(following)}")
        if token.kind == "op" and token.text == "{":
            self.fail_at(token, "free-standing blocks are not supported")
        self.fail_at(token, f"unexpected {self.describe(token)} at the start of a statement")

    def parse_poke_statement(self):
        """poke(name, value, index);"""
        keyword = self.advance()
        arguments, keywords = self.parse_call_arguments()
        if keywords:
            self.fail_at(next(iter(keywords.values())), "poke takes no keyword arguments in this subset")
        if len(arguments) != DATA_OPERATORS["poke"]:
            self.fail_at(keyword, f"poke takes 3 arguments (the Data, the value, the index), got {len(arguments)}")
        if not isinstance(arguments[0], Name):
            self.fail_at(keyword, "poke's first argument must be a Data's name")
        self.expect_semicolon("after poke(...)")
        return PokeStatement(keyword.line, keyword.col, arguments[0].name, arguments[1], arguments[2])

    def parse_if(self):
        keyword = self.advance()
        branches = []
        else_block = None
        while True:
            self.expect_op("(", "after 'if'")
            condition = self.parse_expression()
            self.expect_op(")", "to close the if condition")
            branches.append((condition, self.parse_block()))
            if not self.at_word("else"):
                break
            self.advance()
            if self.at_word("if"):
                self.advance()
                continue
            else_block = self.parse_block()
            break
        return If(keyword.line, keyword.col, branches, else_block)

    def parse_for(self):
        """for (i = START; i < LIMIT; i += STEP) { ... }: the only loop, its count fixed by its three literals."""
        keyword = self.advance()
        unbounded = ("a for loop must be bounded when it is checked: for (i = START; i < LIMIT; i += STEP) with "
                     "number literals and STEP > 0")
        self.expect_op("(", "after 'for'")
        counter = self.expect_identifier("as the loop counter")
        self.expect_op("=", f"after the loop counter '{counter.text}'")
        start = self.parse_for_literal(unbounded)
        self.expect_semicolon("after the loop's start")
        if not (self.peek().kind == "ident" and self.peek().text == counter.text):
            self.fail_at(self.peek(), f"{unbounded}: the condition must test the counter '{counter.text}'")
        self.advance()
        comparison = self.peek()
        if not (comparison.kind == "op" and comparison.text in ("<", "<=")):
            self.fail_at(comparison, f"{unbounded}: the condition must be {counter.text} < LIMIT or {counter.text} <= LIMIT")
        self.advance()
        limit = self.parse_for_literal(unbounded)
        if not self.at_op(";"):
            self.fail_at(self.peek(), f"{unbounded}: the condition is the counter against one number literal, "
                                      f"found {self.describe(self.peek())}")
        self.advance()
        step_counter = self.peek()
        if not (step_counter.kind == "ident" and step_counter.text == counter.text and self.at_op("+=", 1)):
            self.fail_at(step_counter, f"{unbounded}: the step must be {counter.text} += STEP")
        self.advance()
        self.advance()
        step_token = self.peek()
        step = self.parse_for_literal(unbounded)
        if not step > 0:
            self.fail_at(step_token, f"{unbounded}: the step must be more than 0, got {step!r}")
        self.expect_op(")", "to close the for loop's header")
        body = self.parse_block()
        return For(keyword.line, keyword.col, counter.text, start, limit, comparison.text == "<=", step, body)

    def parse_for_literal(self, unbounded):
        sign = 1.0
        if self.at_op("-"):
            self.advance()
            sign = -1.0
        token = self.peek()
        if token.kind != "number":
            self.fail_at(token, f"{unbounded}: expected a number literal, found {self.describe(token)}")
        self.advance()
        return sign * self.number_value(token)

    # -- expressions --
    def parse_expression(self):
        return self.parse_ternary()

    def parse_ternary(self):
        condition = self.parse_binary(0)
        if self.at_op("?"):
            question = self.advance()
            when_true = self.parse_ternary()
            self.expect_op(":", "in the ternary expression")
            when_false = self.parse_ternary()
            return Ternary(question.line, question.col, condition, when_true, when_false)
        return condition

    def parse_binary(self, lowest_level):
        """Precedence climbing: an operand, then while the next token is an operator of `lowest_level` or tighter,
        that operator and its right operand (bound at the next tighter level: left associative)."""
        left = self.parse_unary()
        while True:
            token = self.peek()
            level = BINARY_OPERATOR_LEVELS.get(token.text) if token.kind == "op" else None
            if level is None or level < lowest_level:
                return left
            self.advance()
            right = self.parse_binary(level + 1)
            left = Binary(token.line, token.col, token.text, left, right)

    def parse_unary(self):
        token = self.peek()
        if token.kind == "op" and token.text in ("-", "!"):
            self.advance()
            return Unary(token.line, token.col, token.text, self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self):
        token = self.peek()
        if token.kind == "number":
            self.advance()
            return Number(token.line, token.col, self.number_value(token))
        if token.kind == "string":
            self.fail_at(token, 'string literals are only allowed as interp="..." in Delay.read')
        if token.kind == "op" and token.text == "(":
            self.advance()
            inner = self.parse_expression()
            self.expect_op(")", "to close the parenthesis")
            return inner
        if token.kind == "ident" and token.text not in RESERVED_WORDS:
            self.advance()
            if self.at_op("("):
                arguments, keywords = self.parse_call_arguments()
                if keywords:
                    keyword_token = next(iter(keywords.values()))
                    self.fail_at(keyword_token, f"keyword arguments are only supported on Delay.read, not on '{token.text}'")
                return Call(token.line, token.col, token.text, arguments)
            if self.at_op("."):
                self.advance()
                method = self.expect_identifier("after '.'")
                if not self.at_op("("):
                    self.fail_at(self.peek(), f"expected '(' after '{token.text}.{method.text}'")
                arguments, keywords = self.parse_call_arguments()
                return MethodCall(token.line, token.col, token.text, method.text, arguments, keywords)
            return Name(token.line, token.col, token.text)
        self.fail_at(token, f"unexpected {self.describe(token)} in an expression")

    def parse_call_arguments(self):
        self.expect_op("(", "to open the argument list")
        arguments = []
        keywords = {}
        if not self.at_op(")"):
            while True:
                token = self.peek()
                if token.kind == "ident" and self.at_op("=", 1):
                    self.advance()
                    self.advance()
                    value = self.peek()
                    if value.kind != "string":
                        self.fail_at(value, f"keyword '{token.text}' needs a string value, found {self.describe(value)}")
                    self.advance()
                    if token.text in keywords:
                        self.fail_at(token, f"duplicate keyword '{token.text}'")
                    keywords[token.text] = value
                else:
                    if keywords:
                        self.fail_at(token, "positional argument after a keyword argument")
                    arguments.append(self.parse_expression())
                if self.at_op(","):
                    self.advance()
                    continue
                break
        self.expect_op(")", "to close the argument list")
        return arguments, keywords


def parse(code):
    return Parser(tokenize(code)).parse_program()


def param_default_text(value):
    """A Param default as the code shows it: an integer without a decimal point (700), any other value as Python's
    shortest repr that reads back to the same double (0.22)."""
    value = float(value)
    if not math.isfinite(value):
        raise BuildError(f"a Param default must be a finite number, not {value}")
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return repr(value)


def code_with_param_defaults(code, defaults_by_name):
    """`code` with each Param of `defaults_by_name` given that default where its declaration leaves it out
    (`Param cutoff(min=40, max=12000);` -> `Param cutoff(700, min=40, max=12000);`, `Param x;` -> `Param x(0.5);`).
    Fails on a name that is no Param, on a Param whose code already holds a default (one number, one source), and if
    the result does not read back with exactly these defaults. A device's build asks for the same code as built more
    than once (the patch's codebox, a renderer's or exporter's copy): the last few answers are kept, by code and
    defaults (a refusal is not kept: asked again, it fails again)."""
    return code_with_param_defaults_by_items(code, tuple(sorted(defaults_by_name.items())))


@functools.lru_cache(maxsize=8)
def code_with_param_defaults_by_items(code, default_items):
    """code_with_param_defaults with its defaults as sorted (name, value) pairs: hashable, for the cache."""
    defaults_by_name = dict(default_items)
    tokens = tokenize(code)
    declarations = {declaration.name: declaration for declaration in Parser(tokens).parse_program().declarations
                    if isinstance(declaration, ParamDecl)}
    unknown = sorted(set(defaults_by_name) - set(declarations))
    if unknown:
        raise BuildError(f"defaults for {unknown}, which the code does not declare as Params "
                         f"(it declares: {', '.join(declarations) or 'none'})")
    written_twice = sorted(name for name in defaults_by_name if declarations[name].default is not None)
    if written_twice:
        raise BuildError(f"Params {written_twice} hold a default in the code and are given one: leave the default "
                         f"out of the code (Param name(min=..., max=...);), the one given is the default")
    line_starts = [0] + [newline.end() for newline in NEWLINE_PATTERN.finditer(code)]

    def offset_of(token):
        return line_starts[token.line - 1] + token.col - 1

    insertions = []                                   # (offset, text), applied from the end
    for index, token in enumerate(tokens):
        if not (token.kind == "ident" and token.text == "Param" and tokens[index + 1].text in defaults_by_name):
            continue
        name_token, following = tokens[index + 1], tokens[index + 2]
        default_text = param_default_text(defaults_by_name[name_token.text])
        if following.kind == "op" and following.text == "(":
            closing = tokens[index + 3].kind == "op" and tokens[index + 3].text == ")"
            insertions.append((offset_of(following) + 1, default_text if closing else default_text + ", "))
        else:
            insertions.append((offset_of(name_token) + len(name_token.text), f"({default_text})"))
    for offset, inserted in sorted(insertions, reverse=True):
        code = code[:offset] + inserted + code[offset:]
    read_back = {declaration.name: declaration.default for declaration in parse(code).declarations
                 if isinstance(declaration, ParamDecl) and declaration.name in defaults_by_name}
    if read_back != {name: float(value) for name, value in defaults_by_name.items()}:
        raise BuildError(f"internal error: the Param defaults written read back as {read_back}, "
                         f"not {dict(defaults_by_name)}")
    return code


# ----------------------------------------------------------------------------
# Semantic analysis
# ----------------------------------------------------------------------------

class Scope:
    def __init__(self, parent, block_line):
        self.parent = parent
        self.block_line = block_line
        self.variables = {}

    def find(self, name):
        scope = self
        while scope is not None:
            if name in scope.variables:
                return scope
            scope = scope.parent
        return None


@dataclass
class ProgramInfo:
    params: dict          # name -> ParamDecl
    histories: dict       # name -> HistoryDecl
    delays: dict          # name -> DelayDecl
    functions: dict       # name -> FunctionDef
    used_inputs: set
    used_outputs: set
    data: dict = field(default_factory=dict)   # name -> DataDecl

    @property
    def memory_size(self):
        """The doubles the program's Delays and Datas hold, in that order: one block of memory (`delay_memory`)."""
        return sum(delay.size for delay in self.delays.values()) + sum(data.size for data in self.data.values())


class Analyzer:
    def __init__(self, program, num_inputs, num_outputs):
        self.program = program
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.params = {}
        self.histories = {}
        self.delays = {}
        self.data = {}
        self.delay_read_sites = {}      # Delay name -> how many places the code reads it (each needs a tap)
        self.functions = {}
        self.used_inputs = set()
        self.used_outputs = set()
        self.closed_block_locals = {}   # name -> line of the block that held it
        self.function_being_checked = None
        self.loop_counters_in_force = []   # the counters of the for loops being checked, outermost first

    def error(self, node_or_position, message):
        if isinstance(node_or_position, tuple):
            raise GenExprError(message, node_or_position[0], node_or_position[1])
        raise GenExprError(message, node_or_position.line, node_or_position.col)

    def classify_reserved(self, name):
        if name in CONSTANT_NAMES:
            return "a constant"
        if name in BUILTIN_ARITY or name in DATA_OPERATORS:
            return "a builtin function"
        if name in self.functions:
            return "a function"
        if name in self.params:
            return "a Param"
        if name in self.histories:
            return "a History"
        if name in self.delays:
            return "a Delay"
        if name in self.data:
            return "a Data"
        if INPUT_NAME_PATTERN.match(name):
            return "an input"
        if OUTPUT_NAME_PATTERN.match(name):
            return "an output"
        return None

    def declare_global_name(self, node, name, what):
        existing = self.classify_reserved(name)
        if existing:
            self.error(node, f"cannot declare {what} '{name}': the name is already {existing}")

    # -- driver --
    def analyze(self):
        for declaration in self.program.declarations:
            if isinstance(declaration, ParamDecl):
                self.declare_global_name(declaration, declaration.name, "Param")
                self.params[declaration.name] = declaration
            elif isinstance(declaration, HistoryDecl):
                self.declare_global_name(declaration, declaration.name, "History")
                self.histories[declaration.name] = declaration
            elif isinstance(declaration, DataDecl):
                self.declare_global_name(declaration, declaration.name, "Data")
                self.data[declaration.name] = declaration
            else:
                self.declare_global_name(declaration, declaration.name, "Delay")
                self.delays[declaration.name] = declaration
        for function in self.program.functions:
            self.analyze_function(function)
        scope = Scope(None, 0)
        self.check_statements(self.program.statements, scope)
        return ProgramInfo(self.params, self.histories, self.delays, self.functions,
                           self.used_inputs, self.used_outputs, self.data)

    def analyze_function(self, function):
        existing = self.classify_reserved(function.name)
        if existing:
            self.error(function, f"cannot define function '{function.name}': the name is already {existing}")
        if function.name in self.params or function.name in self.histories or function.name in self.delays:
            self.error(function, f"function name '{function.name}' clashes with a declaration")
        scope = Scope(None, function.body.line)
        for parameter_name, line, col in function.parameters:
            if parameter_name in CONSTANT_NAMES or parameter_name in BUILTIN_ARITY or parameter_name in DATA_OPERATORS \
                    or parameter_name in self.functions \
                    or INPUT_NAME_PATTERN.match(parameter_name) or OUTPUT_NAME_PATTERN.match(parameter_name):
                self.error((line, col), f"function argument '{parameter_name}' clashes with {self.classify_reserved(parameter_name)}")
            if parameter_name in scope.variables:
                self.error((line, col), f"duplicate function argument '{parameter_name}'")
            scope.variables[parameter_name] = line
        self.function_being_checked = function
        loop_counters_outside = self.loop_counters_in_force
        self.loop_counters_in_force = []
        self.check_statements(function.body.statements, scope)
        self.loop_counters_in_force = loop_counters_outside
        self.function_being_checked = None
        self.functions[function.name] = function

    # -- statements --
    def check_statements(self, statements, scope):
        for statement in statements:
            self.check_statement(statement, scope)

    def check_block(self, block, parent_scope):
        scope = Scope(parent_scope, block.line)
        self.check_statements(block.statements, scope)
        for name in scope.variables:
            self.closed_block_locals[name] = block.line

    def check_statement(self, statement, scope):
        inside_function = self.function_being_checked is not None
        if isinstance(statement, Assign):
            self.check_expression(statement.expression, scope)
            self.check_assignment_target(statement, scope)
        elif isinstance(statement, If):
            for condition, block in statement.branches:
                self.check_expression(condition, scope)
                self.check_block(block, scope)
            if statement.else_block is not None:
                self.check_block(statement.else_block, scope)
        elif isinstance(statement, Return):
            if not inside_function:
                self.error(statement, "'return' is only allowed inside a function")
            self.check_expression(statement.expression, scope)
        elif isinstance(statement, MethodStatement):
            self.check_method_statement(statement.call, scope)
        elif isinstance(statement, PokeStatement):
            self.require_data(statement, statement.data_name, "poke")
            self.check_expression(statement.value, scope)
            self.check_expression(statement.index, scope)
        elif isinstance(statement, For):
            self.check_for(statement, scope)
        elif isinstance(statement, (Break, Continue)):
            if not self.loop_counters_in_force:
                self.error(statement, f"'{'break' if isinstance(statement, Break) else 'continue'}' is only allowed "
                                      "inside a for loop")
        else:
            self.error(statement, "internal error: unknown statement type")

    def check_for(self, loop, scope):
        counter = loop.counter
        if scope.find(counter) is not None:
            self.error(loop, f"the loop counter '{counter}' must be a new name: it is already a local here")
        existing = self.classify_reserved(counter)
        if existing:
            self.error(loop, f"the loop counter '{counter}' must be a new name: it is already {existing}")
        if counter in self.closed_block_locals:
            self.error(loop, f"the loop counter '{counter}' must be a new name: it is a local of the block at line "
                             f"{self.closed_block_locals[counter]}")
        if loop.bounded_loop_iterations is None:
            self.error(loop, f"the for loop over '{counter}' would run more than {MAXIMUM_LOOP_ITERATIONS} times, or "
                             "its step is lost in the counter's rounding: the kit runs only loops it can bound")
        body_scope = Scope(scope, loop.body.line)
        body_scope.variables[counter] = loop.line
        self.loop_counters_in_force.append(counter)
        self.check_statements(loop.body.statements, body_scope)
        self.loop_counters_in_force.pop()
        for name in body_scope.variables:
            self.closed_block_locals[name] = loop.body.line

    def check_assignment_target(self, statement, scope):
        name = statement.name
        inside_function = self.function_being_checked is not None
        if name in self.loop_counters_in_force:
            self.error(statement, f"cannot assign to the loop counter '{name}' inside its loop: the loop would no "
                                  "longer be bounded by its header")
        existing_scope = scope.find(name)
        if existing_scope is not None:
            return
        if name in CONSTANT_NAMES:
            self.error(statement, f"cannot assign to the constant '{name}'")
        if name in BUILTIN_ARITY:
            self.error(statement, f"cannot assign to '{name}': it is a builtin function")
        if name in self.functions:
            self.error(statement, f"cannot assign to '{name}': it is a function")
        if INPUT_NAME_PATTERN.match(name):
            self.error(statement, f"cannot assign to the input '{name}' (inputs are read only)")
        output_match = OUTPUT_NAME_PATTERN.match(name)
        if output_match:
            if inside_function:
                self.error(statement, f"cannot write the output '{name}' inside a function")
            output_number = int(output_match.group(1))
            if output_number < 1 or output_number > self.num_outputs_limit():
                self.error(statement, f"output '{name}' is out of range: this program has {self.num_outputs} output(s)")
            self.used_outputs.add(output_number)
            return
        if name in self.params:
            self.error(statement, f"cannot assign to the Param '{name}' (set Params from outside)")
        if name in self.delays:
            self.error(statement, f"cannot assign to the Delay '{name}'; use {name}.write(x);")
        if name in self.data:
            self.error(statement, f"cannot assign to the Data '{name}'; use poke({name}, value, index);")
        if name in DATA_OPERATORS:
            self.error(statement, f"cannot assign to '{name}': it is a builtin function")
        if name in self.histories:
            if inside_function:
                self.error(statement, f"History '{name}' cannot be used inside a function")
            return
        scope.variables[name] = statement.line

    def num_outputs_limit(self):
        return float("inf") if self.num_outputs is None else self.num_outputs

    def num_inputs_limit(self):
        return float("inf") if self.num_inputs is None else self.num_inputs

    def check_method_statement(self, call, scope):
        if self.function_being_checked is not None:
            self.error(call, "Delay methods cannot be used inside a function")
        self.require_delay(call)
        if call.method != "write":
            self.error(call, f"'{call.object_name}.{call.method}(...)' has no effect as a statement; only {call.object_name}.write(x); is a statement")
        if len(call.arguments) != 1 or call.keywords:
            self.error(call, f"{call.object_name}.write takes exactly 1 argument")
        self.check_expression(call.arguments[0], scope)

    def require_delay(self, call):
        if call.object_name not in self.delays:
            self.error(call, f"'{call.object_name}' is not a Delay, so '.{call.method}' is not available")

    def require_data(self, node, data_name, operator):
        if self.function_being_checked is not None:
            self.error(node, f"{operator} cannot be used inside a function (a Data is not passed to one)")
        if data_name not in self.data:
            self.error(node, f"{operator}'s first argument '{data_name}' is not a Data (declare Data {data_name}(size);)")

    # -- expressions --
    def check_expression(self, node, scope):
        if isinstance(node, Number):
            return
        if isinstance(node, Name):
            self.check_name_read(node, scope)
        elif isinstance(node, Unary):
            self.check_expression(node.operand, scope)
        elif isinstance(node, Binary):
            self.check_expression(node.left, scope)
            self.check_expression(node.right, scope)
        elif isinstance(node, Ternary):
            self.check_expression(node.condition, scope)
            self.check_expression(node.when_true, scope)
            self.check_expression(node.when_false, scope)
        elif isinstance(node, Call):
            self.check_call(node, scope)
        elif isinstance(node, MethodCall):
            self.check_method_expression(node, scope)
        else:
            self.error(node, "internal error: unknown expression type")

    def check_name_read(self, node, scope):
        name = node.name
        if name in CONSTANT_NAMES or scope.find(name) is not None:
            return
        inside_function = self.function_being_checked is not None
        kind = None
        if name in self.params:
            kind = "Param"
        elif name in self.histories:
            kind = "History"
        elif name in self.delays:
            kind = "Delay"
        elif name in self.data:
            self.error(node, f"Data '{name}' is not a value; use peek({name}, index)")
        input_match = INPUT_NAME_PATTERN.match(name)
        if input_match:
            kind = "input"
        if OUTPUT_NAME_PATTERN.match(name):
            self.error(node, f"outputs are write only: cannot read '{name}'")
        if kind and inside_function:
            self.error(node, f"{kind} '{name}' cannot be used inside function '{self.function_being_checked.name}' (pass it as an argument)")
        if kind == "Delay":
            self.error(node, f"Delay '{name}' is not a value; use {name}.read(t)")
        if input_match:
            input_number = int(input_match.group(1))
            if input_number < 1 or input_number > self.num_inputs_limit():
                self.error(node, f"input '{name}' is out of range: this program has {self.num_inputs} input(s)")
            self.used_inputs.add(input_number)
            return
        if kind:
            return
        if name in BUILTIN_ARITY or name in DATA_OPERATORS or name in self.functions:
            self.error(node, f"'{name}' is a function; call it as {name}(...)")
        if name in self.closed_block_locals:
            self.error(node, f"{name} is assigned only inside the block at line {self.closed_block_locals[name]}; assign it before the if")
        self.error(node, f"'{name}' is read before it is assigned (and is not a Param, History, Delay, input or constant)")

    def check_call(self, node, scope):
        name = node.name
        if name == "poke":
            self.error(node, "poke(name, value, index); is a statement, not an expression")
        if name == "peek":
            if len(node.arguments) != DATA_OPERATORS["peek"] or not isinstance(node.arguments[0], Name):
                self.error(node, "peek takes 2 arguments: a Data's name and the index (peek(name, index))")
            self.require_data(node, node.arguments[0].name, "peek")
            self.check_expression(node.arguments[1], scope)
            return
        if name in BUILTIN_ARITY:
            expected = BUILTIN_ARITY[name]
        elif name in self.functions:
            expected = len(self.functions[name].parameters)
        else:
            if self.function_being_checked is not None and name == self.function_being_checked.name:
                self.error(node, f"function '{name}' cannot call itself (recursion is not supported)")
            hint = ""
            if name in self.params or name in self.histories or name in self.delays:
                hint = " (it is a variable, not a function)"
            self.error(node, f"unknown function '{name}'{hint}; functions must be builtins or defined earlier")
        if len(node.arguments) != expected:
            plural = "" if expected == 1 else "s"
            self.error(node, f"'{name}' takes {expected} argument{plural}, got {len(node.arguments)}")
        for argument in node.arguments:
            self.check_expression(argument, scope)

    def check_method_expression(self, node, scope):
        if self.function_being_checked is not None:
            self.error(node, "Delay methods cannot be used inside a function")
        self.require_delay(node)
        if node.method == "read":
            self.delay_read_sites[node.object_name] = self.delay_read_sites.get(node.object_name, 0) + 1
            declared = self.delays[node.object_name]
            if self.delay_read_sites[node.object_name] > declared.taps:
                self.error(node, f"Delay {node.object_name} is read at {self.delay_read_sites[node.object_name]} places "
                                 f"but has {declared.taps} tap(s): declare Delay {node.object_name}(size, "
                                 f"{self.delay_read_sites[node.object_name]})")
        if node.method == "write":
            self.error(node, f"'{node.object_name}.write(x)' is a statement, not an expression")
        if node.method != "read":
            self.error(node, f"unknown Delay method '{node.method}' (supported: read, write)")
        if len(node.arguments) != 1:
            self.error(node, f"'{node.object_name}.read' takes 1 positional argument (the delay time), got {len(node.arguments)}")
        for keyword, token in node.keywords.items():
            if keyword != "interp":
                self.error(token, f"unknown keyword '{keyword}' for read (supported: interp)")
            if token.text not in DELAY_INTERPOLATION_MODES:
                self.error(token, f'interp must be one of {", ".join(DELAY_INTERPOLATION_MODES)}, got "{token.text}"')
        self.check_expression(node.arguments[0], scope)


def analyze(code, num_inputs=None, num_outputs=None):
    program = parse(code)
    info = Analyzer(program, num_inputs, num_outputs).analyze()
    return program, info


def check(code, num_inputs=None, num_outputs=None):
    """Raise GenExprError if `code` is outside the checked subset or has scoping errors."""
    analyze(code, num_inputs, num_outputs)


# ----------------------------------------------------------------------------
# Renderer: AST -> C source, built once by the system C compiler, run through ctypes
# ----------------------------------------------------------------------------
#
# Every value is an IEEE double, as in Python. Each builtin below reproduces what CPython's float and math module give
# for the same call, including the special cases (inf, nan, -0.0, domain and overflow errors), so a render is the bits
# CPython computes evaluating the same expressions (NaN sign and payload aside: which NaN an operation on two NaNs
# returns depends on operand order, which neither C nor CPython's own build fixes).
# Evaluation order is fixed where it can be seen (only noise() has a side effect): left to right, as Python. C leaves
# the order of operands open, so wherever two operands could draw noise they are sequenced into temporaries; a
# division evaluates its divisor first and skips its dividend when the divisor is 0 (x / 0 reads 0).
# The compiler must not contract or reassociate floating point, and must call libm for every math function as CPython
# does rather than inline its own (-fno-builtin: an inlined fmod returns other NaNs). -O0: a test suite runs as fast as
# at -O1 or -O2 (its time is no longer the rendering), and a large program (2sl gate's core) builds in 0.4 s against
# 1.2 s and 3.4 s.

COMPILER_FLAGS = ("-O0", "-std=c99", "-fPIC", "-shared", "-ffp-contract=off", "-fno-fast-math", "-fno-builtin")
# A program rendered thousands of times (the patch matcher's voice) is built at -O2 instead: the build's extra seconds
# pay off within a match, and with the same floating-point flags the samples are the same bits (measured 2026-10-20 on
# the 2sl drums synth voice: -O0, -O2 and -O3 renders identical; 34.5 -> 19.1 ms a 0.55 s hit; tests/test_patch_matcher.py
# holds the fixture voice to it; twosl_dsp/genexpr_export.py relies on the same for plugins).
OPTIMISED_COMPILER_FLAGS = ("-O2",) + COMPILER_FLAGS[1:]

C_PRELUDE = r"""
#include <math.h>
#include <stdint.h>
#include <string.h>

typedef struct { uint32_t words[624]; int32_t index; } genexpr_noise_state;
static genexpr_noise_state *genexpr_noise_source;

/* CPython's float("nan"): the positive quiet NaN */
static double genexpr_python_nan(void) { uint64_t bits = 0x7ff8000000000000ULL; double value; memcpy(&value, &bits, 8); return value; }
static const double genexpr_infinity = HUGE_VAL;

/* CPython Modules/_randommodule.c: genrand_uint32 and random_random (MT19937, 53-bit result) */
static uint32_t genexpr_mersenne_next(void) {
    static const uint32_t matrix_by_low_bit[2] = {0x0U, 0x9908b0dfU};
    uint32_t *words = genexpr_noise_source->words;
    uint32_t y;
    if (genexpr_noise_source->index >= 624) {
        int k;
        for (k = 0; k < 624 - 397; k++) {
            y = (words[k] & 0x80000000U) | (words[k + 1] & 0x7fffffffU);
            words[k] = words[k + 397] ^ (y >> 1) ^ matrix_by_low_bit[y & 0x1U];
        }
        for (; k < 624 - 1; k++) {
            y = (words[k] & 0x80000000U) | (words[k + 1] & 0x7fffffffU);
            words[k] = words[k + (397 - 624)] ^ (y >> 1) ^ matrix_by_low_bit[y & 0x1U];
        }
        y = (words[623] & 0x80000000U) | (words[0] & 0x7fffffffU);
        words[623] = words[396] ^ (y >> 1) ^ matrix_by_low_bit[y & 0x1U];
        genexpr_noise_source->index = 0;
    }
    y = words[genexpr_noise_source->index++];
    y ^= (y >> 11);
    y ^= (y << 7) & 0x9d2c5680U;
    y ^= (y << 15) & 0xefc60000U;
    y ^= (y >> 18);
    return y;
}
static double genexpr_noise(void) {
    uint32_t high = genexpr_mersenne_next() >> 5, low = genexpr_mersenne_next() >> 6;
    return ((high * 67108864.0 + low) * (1.0 / 0x1p53)) * 2.0 - 1.0;
}

/* Python's min(a, b) / max(a, b): the second replaces the first only if strictly less / greater */
static double genexpr_min(double a, double b) { return b < a ? b : a; }
static double genexpr_max(double a, double b) { return b > a ? b : a; }
static double genexpr_sign(double x) { return x > 0 ? 1.0 : (x < 0 ? -1.0 : 0.0); }
/* float(math.floor(x)) goes through a Python int: -0.0 comes back as 0.0; inf and nan pass through */
static double genexpr_through_int(double rounded) { return rounded == 0.0 ? 0.0 : rounded; }
static double genexpr_floor(double x) { return isfinite(x) ? genexpr_through_int(floor(x)) : x; }
static double genexpr_ceil(double x) { return isfinite(x) ? genexpr_through_int(ceil(x)) : x; }
static double genexpr_trunc(double x) { return isfinite(x) ? genexpr_through_int(trunc(x)) : x; }
static double genexpr_fract(double x) { return x - genexpr_floor(x); }
static double genexpr_clamp(double x, double low, double high) {
    if (low > high) { double swap = low; low = high; high = swap; }
    return x < low ? low : (x > high ? high : x);
}
/* CPython float_rem: the remainder takes the divisor's sign */
static double genexpr_python_float_remainder(double dividend, double divisor) {
    double remainder = fmod(dividend, divisor);
    if (remainder != 0.0) {
        if ((divisor < 0) != (remainder < 0)) remainder += divisor;
    } else {
        remainder = copysign(0.0, divisor);
    }
    return remainder;
}
static double genexpr_wrap(double x, double low, double high) {
    if (high < low) { double swap = low; low = high; high = swap; }
    if (low <= x && x < high) return x;
    double span = high - low;
    if (span == 0) return low;
    double wrapped = low + genexpr_python_float_remainder(x - low, span);
    return wrapped >= high ? low : wrapped;
}
static double genexpr_mix(double a, double b, double t) { return a + (b - a) * t; }
/* math.exp: overflow raises, read as inf */
static double genexpr_exp(double x) { return exp(x); }
/* math.log / log2 / log10 (CPython m_log*): nan and inf come back as themselves; x <= 0 reads 0 (our rule) */
static double genexpr_log(double x) { if (isnan(x)) return x; if (x <= 0) return 0.0; if (isinf(x)) return x; return log(x); }
static double genexpr_log2(double x) { if (isnan(x)) return x; if (x <= 0) return 0.0; if (isinf(x)) return x; return log2(x); }
static double genexpr_log10(double x) { if (isnan(x)) return x; if (x <= 0) return 0.0; if (isinf(x)) return x; return log10(x); }
/* math.pow (CPython math_pow): its own non-finite cases, then libm; a domain error reads nan, an overflow +inf */
static double genexpr_pow(double base, double exponent) {
    if (!isfinite(base) || !isfinite(exponent)) {
        if (isnan(base)) return exponent == 0.0 ? 1.0 : base;
        if (isnan(exponent)) return base == 1.0 ? 1.0 : exponent;
        if (isinf(base)) {
            int odd_exponent = isfinite(exponent) && fmod(fabs(exponent), 2.0) == 1.0;
            if (exponent > 0.) return odd_exponent ? base : fabs(base);
            if (exponent == 0.) return 1.;
            return odd_exponent ? copysign(0., base) : 0.;
        }
        if (fabs(base) == 1.0) return 1.;
        if (exponent > 0. && fabs(base) > 1.0) return exponent;
        if (exponent < 0. && fabs(base) < 1.0) return -exponent;
        return 0.;
    }
    double result = pow(base, exponent);
    if (!isfinite(result)) {
        if (isnan(result)) return genexpr_python_nan();
        if (base == 0.) return genexpr_python_nan();
        return genexpr_infinity;
    }
    return result;
}
/* math.sqrt; x < 0 reads 0 (our rule) */
static double genexpr_sqrt(double x) { return (x >= 0 || x != x) ? sqrt(x) : 0.0; }
/* math.sin / cos / tan: a nan from a non-nan argument (inf) raises, read as nan */
static double genexpr_sin(double x) { return isinf(x) ? genexpr_python_nan() : sin(x); }
static double genexpr_cos(double x) { return isinf(x) ? genexpr_python_nan() : cos(x); }
static double genexpr_tan(double x) { return isinf(x) ? genexpr_python_nan() : tan(x); }
/* math.atan2 (CPython m_atan2); 0x1.921fb54442d18p+1 is math.pi to the bit */
static double genexpr_atan2(double y, double x) {
    if (isnan(x) || isnan(y)) return genexpr_python_nan();
    if (isinf(y)) {
        if (isinf(x)) return copysign(copysign(1., x) == 1. ? 0.25 * 0x1.921fb54442d18p+1 : 0.75 * 0x1.921fb54442d18p+1, y);
        return copysign(0.5 * 0x1.921fb54442d18p+1, y);
    }
    if (isinf(x) || y == 0.) return copysign(1., x) == 1. ? copysign(0., y) : copysign(0x1.921fb54442d18p+1, y);
    return atan2(y, x);
}
/* math.fmod (CPython math_fmod); a zero divisor reads 0 (our rule) */
static double genexpr_modulo(double dividend, double divisor) {
    if (divisor == 0) return 0.0;
    if (isinf(divisor) && isfinite(dividend)) return dividend;
    double remainder = fmod(dividend, divisor);
    if (isnan(remainder) && !isnan(dividend) && !isnan(divisor)) return genexpr_python_nan();
    return remainder;
}
/* 10.0 ** (db / 20.0): overflow raises, read as inf */
static double genexpr_dbtoa(double db) { return pow(10.0, db / 20.0); }
static double genexpr_atodb(double x) {
    if (x > 0) return 20.0 * (isinf(x) ? x : log10(x));
    return x == x ? -999.0 : genexpr_python_nan();
}

static long genexpr_wrap_index(long index, long size) { index %= size; return index < 0 ? index + size : index; }
static double genexpr_clamp_delay_time(double time_in_samples, long size) {
    if (time_in_samples < 0.0) return 0.0;
    if (time_in_samples > (double)(size - 1)) return (double)(size - 1);
    return time_in_samples;
}
static double genexpr_delay_read_none(const double *buffer, long position, long size, double time_in_samples) {
    if (time_in_samples != time_in_samples) return genexpr_python_nan();
    long whole = (long)genexpr_clamp_delay_time(time_in_samples, size);
    return buffer[genexpr_wrap_index(position - whole, size)];
}
static double genexpr_delay_read_linear(const double *buffer, long position, long size, double time_in_samples) {
    if (time_in_samples != time_in_samples) return genexpr_python_nan();
    time_in_samples = genexpr_clamp_delay_time(time_in_samples, size);
    long whole = (long)time_in_samples;
    double fraction = time_in_samples - (double)whole;
    double newer = buffer[genexpr_wrap_index(position - whole, size)];
    if (fraction == 0.0) return newer;
    double older = buffer[genexpr_wrap_index(position - whole - 1, size)];
    return newer + (older - newer) * fraction;
}
/* Catmull-Rom through the samples at delays whole-1, whole, whole+1, whole+2 */
static double genexpr_delay_read_spline(const double *buffer, long position, long size, double time_in_samples) {
    if (time_in_samples != time_in_samples) return genexpr_python_nan();
    time_in_samples = genexpr_clamp_delay_time(time_in_samples, size);
    long whole = (long)time_in_samples;
    double fraction = time_in_samples - (double)whole;
    double y_before = buffer[genexpr_wrap_index(position - whole + 1, size)];
    double y_start = buffer[genexpr_wrap_index(position - whole, size)];
    double y_end = buffer[genexpr_wrap_index(position - whole - 1, size)];
    double y_after = buffer[genexpr_wrap_index(position - whole - 2, size)];
    double c1 = 0.5 * (y_end - y_before);
    double c2 = y_before - 2.5 * y_start + 2.0 * y_end - 0.5 * y_after;
    double c3 = 0.5 * (y_after - y_before) + 1.5 * (y_start - y_end);
    return ((c3 * fraction + c2) * fraction + c1) * fraction + y_start;
}
"""

# gen~ data's peek and poke: written only into a program that has a Data, so every other program's C (a plugin's
# exported core) is as it was before Data
C_DATA_HELPERS = r"""/* a Data's sample at the floored index; out of range or NaN reads 0 (gen~'s boundmode "ignore") */
static double genexpr_peek(const double *data, long size, double index) {
    if (!(index >= 0.0 && index < (double)size)) return 0.0;
    return data[(long)floor(index)];
}
/* writes a Data's sample at the floored index; out of range or NaN writes nothing */
static void genexpr_poke(double *data, long size, double value, double index) {
    if (!(index >= 0.0 && index < (double)size)) return;
    data[(long)floor(index)] = value;
}
"""

# builtin name -> C function (every builtin but noise, mstosamps and sampstoms, which CTranslator writes inline)
BUILTIN_C_FUNCTIONS = {
    "abs": "fabs", "sign": "genexpr_sign", "floor": "genexpr_floor", "ceil": "genexpr_ceil", "trunc": "genexpr_trunc",
    "fract": "genexpr_fract", "min": "genexpr_min", "max": "genexpr_max", "clamp": "genexpr_clamp",
    "wrap": "genexpr_wrap", "mix": "genexpr_mix", "exp": "genexpr_exp", "log": "genexpr_log", "log2": "genexpr_log2",
    "log10": "genexpr_log10", "pow": "genexpr_pow", "sqrt": "genexpr_sqrt", "sin": "genexpr_sin",
    "cos": "genexpr_cos", "tan": "genexpr_tan", "tanh": "tanh", "atan": "atan", "atan2": "genexpr_atan2",
    "dbtoa": "genexpr_dbtoa", "atodb": "genexpr_atodb",
}
INLINE_BUILTINS = frozenset({"noise", "mstosamps", "sampstoms"})
assert set(BUILTIN_C_FUNCTIONS) | INLINE_BUILTINS == set(BUILTIN_ARITY), "every builtin needs a C translation"

# interp="cubic" is rendered as the same Catmull-Rom as "spline" (module docstring)
DELAY_READ_C_FUNCTIONS = {"none": "genexpr_delay_read_none", "linear": "genexpr_delay_read_linear",
                          "cubic": "genexpr_delay_read_spline", "spline": "genexpr_delay_read_spline"}


def c_double_literal(value):
    """An exact C literal for a finite double (hexadecimal floating point)."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"internal error: no C literal for the non-finite constant {value}")
    return f"({value.hex()})" if value >= 0 else f"(-{(-value).hex()})"


class CTranslator:
    """One GenExpr program as one C translation unit with
    void genexpr_render(long sample_count, const double *params, double *histories, double *delay_memory,
                        long *delay_positions, const double *const *inputs, double *const *outputs,
                        genexpr_noise_state *noise)."""

    def __init__(self, program, info, samplerate):
        self.program = program
        self.info = info
        self.samplerate = float(samplerate)
        self.lines = []
        self.indent = 0
        self.constants = {
            "samplerate": c_double_literal(self.samplerate),
            "pi": c_double_literal(math.pi), "twopi": c_double_literal(2 * math.pi),
            "halfpi": c_double_literal(math.pi / 2), "e": c_double_literal(math.e),
        }
        self.functions_that_draw_noise = set()
        self.temporary_count = 0

    def emit(self, text):
        self.lines.append("    " * self.indent + text)

    def new_temporary(self):
        self.temporary_count += 1
        return f"t_{self.temporary_count}"

    def declare_temporaries_at(self, line_index):
        if self.temporary_count:
            names = ", ".join(f"t_{number}" for number in range(1, self.temporary_count + 1))
            self.lines.insert(line_index, "    " * self.indent + f"double {names};")

    # -- program --
    def translate(self):
        self.lines.append(C_PRELUDE)
        if self.info.data:
            self.lines.append(C_DATA_HELPERS)
        for function in self.program.functions:
            self.emit_function(function)
        self.emit_render()
        return "\n".join(self.lines) + "\n"

    def emit_function(self, function):
        if self.statements_draw_noise(function.body.statements):
            self.functions_that_draw_noise.add(function.name)
        arguments = ", ".join(f"double v_{name}" for name, _, _ in function.parameters) or "void"
        self.emit(f"static double f_{function.name}({arguments}) {{")
        self.indent += 1
        parameter_names = {name for name, _, _ in function.parameters}
        locals_assigned = sorted(self.assigned_names(function.body.statements) - parameter_names)
        if locals_assigned:
            self.emit("double " + ", ".join(f"v_{name}" for name in locals_assigned) + ";")
        self.temporary_count = 0
        temporaries_line = len(self.lines)
        self.emit_statements(function.body.statements)
        self.emit("return 0.0;")
        self.declare_temporaries_at(temporaries_line)
        self.indent -= 1
        self.emit("}")
        self.emit("")

    def emit_render(self):
        info = self.info
        self.emit("void genexpr_render(long sample_count, const double *params, double *histories, double *delay_memory, "
                  "long *delay_positions, const double *const *inputs, double *const *outputs, "
                  "genexpr_noise_state *noise) {")
        self.indent += 1
        self.emit("genexpr_noise_source = noise;")
        for index, name in enumerate(info.params):
            self.emit(f"const double v_{name} = params[{index}];")
        for index, name in enumerate(info.histories):
            self.emit(f"double v_{name} = histories[{index}];")
        delay_offset = 0
        for index, (name, delay) in enumerate(info.delays.items()):
            self.emit(f"double *const d_{name} = delay_memory + {delay_offset};")
            self.emit(f"long p_{name} = delay_positions[{index}];")
            delay_offset += delay.size
        for name, data in info.data.items():
            self.emit(f"double *const data_{name} = delay_memory + {delay_offset};")
            delay_offset += data.size
        for number in sorted(info.used_inputs):
            self.emit(f"const double *const in_{number} = inputs[{number - 1}];")
        for number in sorted(info.used_outputs):
            self.emit(f"double *const out_{number} = outputs[{number - 1}];")
        global_names = set(info.params) | set(info.histories) | {f"in{n}" for n in info.used_inputs} \
            | {f"out{n}" for n in info.used_outputs}
        locals_assigned = sorted(self.assigned_names(self.program.statements) - global_names)
        if locals_assigned:
            self.emit("double " + ", ".join(f"v_{name}" for name in locals_assigned) + ";")
        self.temporary_count = 0
        temporaries_line = len(self.lines)
        self.emit("for (long sample_index = 0; sample_index < sample_count; sample_index++) {")
        self.indent += 1
        for number in sorted(info.used_inputs):
            self.emit(f"const double v_in{number} = in_{number}[sample_index];")
        for number in sorted(info.used_outputs):
            self.emit(f"double v_out{number} = 0.0;")
        self.emit_statements(self.program.statements)
        for number in sorted(info.used_outputs):
            self.emit(f"out_{number}[sample_index] = v_out{number};")
        for name, delay in info.delays.items():
            self.emit(f"p_{name} += 1;")
            self.emit(f"if (p_{name} == {delay.size}) p_{name} = 0;")
        self.indent -= 1
        self.emit("}")
        self.declare_temporaries_at(temporaries_line)
        for index, name in enumerate(info.histories):
            self.emit(f"histories[{index}] = v_{name};")
        for index, name in enumerate(info.delays):
            self.emit(f"delay_positions[{index}] = p_{name};")
        self.indent -= 1
        self.emit("}")

    @staticmethod
    def assigned_names(statements):
        names = set()
        for statement in statements:
            if isinstance(statement, Assign):
                names.add(statement.name)
            elif isinstance(statement, If):
                for _, block in statement.branches:
                    names |= CTranslator.assigned_names(block.statements)
                if statement.else_block is not None:
                    names |= CTranslator.assigned_names(statement.else_block.statements)
            elif isinstance(statement, For):
                names.add(statement.counter)
                names |= CTranslator.assigned_names(statement.body.statements)
        return names

    # -- noise: the one side effect, whose order Python fixes and C does not --
    def statements_draw_noise(self, statements):
        for statement in statements:
            if isinstance(statement, (Assign, Return)) and self.draws_noise(statement.expression):
                return True
            if isinstance(statement, MethodStatement) and self.draws_noise(statement.call.arguments[0]):
                return True
            if isinstance(statement, PokeStatement) and (self.draws_noise(statement.value)
                                                         or self.draws_noise(statement.index)):
                return True
            if isinstance(statement, If):
                for condition, block in statement.branches:
                    if self.draws_noise(condition) or self.statements_draw_noise(block.statements):
                        return True
                if statement.else_block is not None and self.statements_draw_noise(statement.else_block.statements):
                    return True
            if isinstance(statement, For) and self.statements_draw_noise(statement.body.statements):
                return True
        return False

    def draws_noise(self, node):
        if isinstance(node, (Number, Name)):
            return False
        if isinstance(node, Unary):
            return self.draws_noise(node.operand)
        if isinstance(node, Binary):
            return self.draws_noise(node.left) or self.draws_noise(node.right)
        if isinstance(node, Ternary):
            return any(self.draws_noise(part) for part in (node.condition, node.when_true, node.when_false))
        if isinstance(node, Call):
            if node.name == "noise" or node.name in self.functions_that_draw_noise:
                return True
            return any(self.draws_noise(argument) for argument in node.arguments)
        if isinstance(node, MethodCall):
            return any(self.draws_noise(argument) for argument in node.arguments)
        raise GenExprError("internal error: unknown expression type", node.line, node.col)

    def operands_in_python_order(self, operand_nodes, translate):
        """C translations of operands that Python evaluates left to right. When two or more of them draw noise, those
        are evaluated into temporaries first, in order: returns (sequencing prefix, [operand C expressions])."""
        translations = [translate(node) for node in operand_nodes]
        if sum(1 for node in operand_nodes if self.draws_noise(node)) < 2:
            return "", translations
        prefix_parts = []
        for index, node in enumerate(operand_nodes):
            if self.draws_noise(node):
                temporary = self.new_temporary()
                prefix_parts.append(f"{temporary} = {translations[index]}")
                translations[index] = temporary
        return "".join(part + ", " for part in prefix_parts), translations

    # -- statements --
    def emit_statements(self, statements):
        for statement in statements:
            self.emit_statement(statement)

    def emit_statement(self, statement):
        if isinstance(statement, Assign):
            self.emit(f"v_{statement.name} = {self.value(statement.expression)};")
        elif isinstance(statement, Return):
            self.emit(f"return {self.value(statement.expression)};")
        elif isinstance(statement, MethodStatement):
            call = statement.call
            self.emit(f"d_{call.object_name}[p_{call.object_name}] = {self.value(call.arguments[0])};")
        elif isinstance(statement, PokeStatement):
            # the value, then the index: Python's order
            prefix, (value, index) = self.operands_in_python_order([statement.value, statement.index], self.value)
            size = self.info.data[statement.data_name].size
            if prefix:
                self.emit(f"{prefix.rstrip(', ')};")
            self.emit(f"genexpr_poke(data_{statement.data_name}, {size}, {value}, {index});")
        elif isinstance(statement, If):
            for branch_index, (condition, block) in enumerate(statement.branches):
                keyword = "if" if branch_index == 0 else "} else if"
                self.emit(f"{keyword} ({self.condition(condition)}) {{")
                self.indent += 1
                self.emit_statements(block.statements)
                self.indent -= 1
            if statement.else_block is not None:
                self.emit("} else {")
                self.indent += 1
                self.emit_statements(statement.else_block.statements)
                self.indent -= 1
            self.emit("}")
        elif isinstance(statement, For):
            counter = f"v_{statement.counter}"
            comparison = "<=" if statement.inclusive else "<"
            self.emit(f"for ({counter} = {c_double_literal(statement.start)}; {counter} {comparison} "
                      f"{c_double_literal(statement.limit)}; {counter} = {counter} + {c_double_literal(statement.step)}) {{")
            self.indent += 1
            self.emit_statements(statement.body.statements)
            self.indent -= 1
            self.emit("}")
        elif isinstance(statement, Break):
            self.emit("break;")
        elif isinstance(statement, Continue):
            self.emit("continue;")
        else:
            raise GenExprError("internal error: cannot translate statement", statement.line, statement.col)

    # -- expressions --
    def condition(self, node):
        """C truth expression for `node` (nonzero = true)."""
        if isinstance(node, Binary):
            if node.operator in COMPARISON_OPERATORS:
                prefix, (left, right) = self.operands_in_python_order([node.left, node.right], self.value)
                return f"({prefix}{left} {node.operator} {right})"
            if node.operator == "&&":
                return f"({self.condition(node.left)} && {self.condition(node.right)})"
            if node.operator == "||":
                return f"({self.condition(node.left)} || {self.condition(node.right)})"
        if isinstance(node, Unary) and node.operator == "!":
            return f"(!{self.condition(node.operand)})"
        return f"({self.value(node)} != 0.0)"

    def value(self, node):
        """C double expression for `node`."""
        if isinstance(node, Number):
            return c_double_literal(node.value)
        if isinstance(node, Name):
            return self.constants.get(node.name, f"v_{node.name}")
        if isinstance(node, Unary):
            if node.operator == "-":
                return f"(-{self.value(node.operand)})"
            return f"({self.condition(node)} ? 1.0 : 0.0)"
        if isinstance(node, Ternary):
            return f"({self.condition(node.condition)} ? {self.value(node.when_true)} : {self.value(node.when_false)})"
        if isinstance(node, Binary):
            return self.binary_value(node)
        if isinstance(node, Call):
            return self.call_value(node)
        if isinstance(node, MethodCall):
            return self.delay_read_value(node)
        raise GenExprError("internal error: cannot translate expression", node.line, node.col)

    def binary_value(self, node):
        operator = node.operator
        if operator in COMPARISON_OPERATORS or operator in ("&&", "||"):
            return f"({self.condition(node)} ? 1.0 : 0.0)"
        if operator == "/":
            # x / 0 reads 0. Python evaluated `left / right if right else 0.0`: the divisor first, the dividend only
            # when the divisor is not 0.
            if isinstance(node.right, Number):
                return "0.0" if node.right.value == 0 else f"({self.value(node.left)} / {self.value(node.right)})"
            divisor = self.new_temporary()
            return f"({divisor} = {self.value(node.right)}, {divisor} != 0.0 ? {self.value(node.left)} / {divisor} : 0.0)"
        prefix, (left, right) = self.operands_in_python_order([node.left, node.right], self.value)
        if operator in ("+", "-", "*"):
            return f"({prefix}{left} {operator} {right})"
        if operator == "%":
            return f"({prefix}genexpr_modulo({left}, {right}))"
        raise GenExprError(f"internal error: cannot translate operator '{operator}'", node.line, node.col)

    def call_value(self, node):
        name = node.name
        if name == "noise":
            return "genexpr_noise()"
        if name == "peek":
            data_name = node.arguments[0].name
            return (f"genexpr_peek(data_{data_name}, {self.info.data[data_name].size}, "
                    f"{self.value(node.arguments[1])})")
        prefix, arguments = self.operands_in_python_order(node.arguments, self.value)
        if name == "mstosamps":
            return f"({prefix}{arguments[0]} * {c_double_literal(self.samplerate)} / 1000.0)"
        if name == "sampstoms":
            return f"({prefix}{arguments[0]} * 1000.0 / {c_double_literal(self.samplerate)})"
        function = BUILTIN_C_FUNCTIONS.get(name, f"f_{name}")
        return f"({prefix}{function}({', '.join(arguments)}))"

    def delay_read_value(self, node):
        mode_token = node.keywords.get("interp")
        mode = mode_token.text if mode_token else "linear"
        delay = self.info.delays[node.object_name]
        return (f"{DELAY_READ_C_FUNCTIONS[mode]}(d_{node.object_name}, p_{node.object_name}, {delay.size}, "
                f"{self.value(node.arguments[0])})")


class NoiseState(ctypes.Structure):
    _fields_ = [("words", ctypes.c_uint32 * 624), ("index", ctypes.c_int32)]


def load_render_function(c_source, optimised=False):
    """The compiled genexpr_render of `c_source` (twosl_dsp/c_library_cache.py builds, caches and loads it), at
    OPTIMISED_COMPILER_FLAGS when `optimised` (the same samples, built slower, rendered faster)."""
    library = load_c_library(c_source, OPTIMISED_COMPILER_FLAGS if optimised else COMPILER_FLAGS)
    render = library.genexpr_render
    render.restype = None
    render.argtypes = [ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(NoiseState)]
    return render


_translations_by_program_text = {}


def translated_program(code, num_inputs, num_outputs, samplerate):
    """(program, info, C source) of `code`, analysed and translated once per process (the AST and info are only read
    from here on: a GenProgram keeps its own state)."""
    key = (code, num_inputs, num_outputs, samplerate)
    if key not in _translations_by_program_text:
        program, info = analyze(code, num_inputs, num_outputs)
        _translations_by_program_text[key] = (program, info, CTranslator(program, info, samplerate).translate())
    return _translations_by_program_text[key]


def buffer_address(double_array):
    return double_array.buffer_info()[0]


# ----------------------------------------------------------------------------
# GenProgram
# ----------------------------------------------------------------------------

class GenProgram:
    def __init__(self, code, num_inputs, num_outputs, samplerate=44100.0, seed=1, optimised=False):
        self.samplerate = float(samplerate)
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        program, info, c_source = translated_program(code, num_inputs, num_outputs, self.samplerate)
        self.params = {
            name: {"default": decl.default, "min": decl.minimum, "max": decl.maximum}
            for name, decl in info.params.items()
        }
        self.histories = list(info.histories)
        self._param_index = {name: index for index, name in enumerate(info.params)}
        self._history_index = {name: index for index, name in enumerate(info.histories)}
        # a Param whose code leaves its default out (the build writes it from the Init values) holds nothing until
        # set_param: run() refuses to start while one is unset
        self._params_never_set = {name for name, decl in info.params.items() if decl.default is None}
        self._param_values = array.array("d", (math.nan if decl.default is None else decl.default
                                               for decl in info.params.values()))
        self._history_values = array.array("d", (decl.initial for decl in info.histories.values()))
        self._delay_memory = array.array("d", bytes(8 * info.memory_size))   # the Delays', then the Datas'
        self._delay_positions = (ctypes.c_long * max(1, len(info.delays)))()
        self._noise_state = NoiseState()
        self.c_source = c_source
        self._render = load_render_function(c_source, optimised)
        self.set_seed(seed)

    def set_seed(self, seed):
        """Noise draws Python's random.Random(seed).random() sequence (Mersenne Twister), as 2 * draw - 1."""
        version, internal_state, _ = random.Random(seed).getstate()
        if version != 3 or len(internal_state) != 625:
            raise RuntimeError(f"genexpr: random.Random's state format changed (version {version}, "
                               f"{len(internal_state)} words): the C noise source copies version 3's 624 words + index")
        self._noise_state.words[:] = internal_state[:624]
        self._noise_state.index = internal_state[624]

    def set_param(self, name, value):
        if name not in self.params:
            raise KeyError(f"unknown Param '{name}'; this program declares: {', '.join(self.params) or '(none)'}")
        value = float(value)
        if value != value:
            raise ValueError(f"Param '{name}' cannot be set to NaN")
        limits = self.params[name]
        if limits["min"] is not None and value < limits["min"]:
            value = limits["min"]
        if limits["max"] is not None and value > limits["max"]:
            value = limits["max"]
        self._param_values[self._param_index[name]] = value
        self._params_never_set.discard(name)

    def get_param(self, name):
        if name not in self.params:
            raise KeyError(f"unknown Param '{name}'; this program declares: {', '.join(self.params) or '(none)'}")
        if name in self._params_never_set:
            raise ValueError(f"Param '{name}' has no default in the code (the build writes it from the Init values) "
                             "and was never set")
        return self._param_values[self._param_index[name]]

    def get_history(self, name):
        if name not in self._history_index:
            raise KeyError(f"unknown History '{name}'; this program declares: {', '.join(self.histories) or '(none)'}")
        return self._history_values[self._history_index[name]]

    def set_history(self, name, value):
        """Sets a History's state, as if the program had run to it: a measurement's starting point (an oscillator's
        phase where Live's would be, twosl_dsp/preset_loudness.py's oscillator_start_phases)."""
        if name not in self._history_index:
            raise KeyError(f"unknown History '{name}'; this program declares: {', '.join(self.histories) or '(none)'}")
        value = float(value)
        if value != value:
            raise ValueError(f"History '{name}' cannot be set to NaN")
        self._history_values[self._history_index[name]] = value

    def run(self, num_samples, inputs=None):
        if num_samples < 0:
            raise ValueError("num_samples must be >= 0")
        if self._params_never_set:
            raise ValueError(f"Params {sorted(self._params_never_set)} have no default in the code (the build writes "
                             "each from the Init values it sends) and were never set: set_param them before running "
                             "(a device's render sets them through its patch, messages_for its Init values)")
        if inputs is None:
            inputs = [0.0] * self.num_inputs
        if len(inputs) != self.num_inputs:
            raise ValueError(f"expected {self.num_inputs} input sequence(s), got {len(inputs)}")
        input_arrays = []
        for input_index, source in enumerate(inputs):
            if isinstance(source, (int, float)):
                input_arrays.append(array.array("d", [float(source)]) * num_samples)
                continue
            if len(source) < num_samples:
                raise ValueError(f"input {input_index + 1} has {len(source)} samples, need {num_samples}")
            input_arrays.append(array.array("d", source[:num_samples]))   # a non-number raises TypeError
        output_arrays = [array.array("d", bytes(8 * num_samples)) for _ in range(self.num_outputs)]
        if num_samples == 0:
            return [[] for _ in output_arrays]
        input_pointers = (ctypes.c_void_p * max(1, len(input_arrays)))(*map(buffer_address, input_arrays))
        output_pointers = (ctypes.c_void_p * max(1, len(output_arrays)))(*map(buffer_address, output_arrays))
        self._render(num_samples, buffer_address(self._param_values) if self._param_values else None,
                     buffer_address(self._history_values) if self._history_values else None,
                     buffer_address(self._delay_memory) if self._delay_memory else None,
                     ctypes.addressof(self._delay_positions), input_pointers, output_pointers,
                     ctypes.byref(self._noise_state))
        return [output.tolist() for output in output_arrays]


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main(argv):
    if len(argv) < 3 or argv[1] != "check":
        print("usage: python3 -m twosl_dsp.genexpr check FILE [FILE...]", file=sys.stderr)
        return 2
    any_error = False
    for path in argv[2:]:
        try:
            with open(path, encoding="utf-8") as handle:
                code = handle.read()
        except OSError as problem:
            print(f"{path}: cannot read file: {problem}")
            any_error = True
            continue
        try:
            check(code)
        except GenExprError as problem:
            print(f"{path}:{problem.line}:{problem.col}: {problem.message}")
            any_error = True
        else:
            print(f"{path}: ok")
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
