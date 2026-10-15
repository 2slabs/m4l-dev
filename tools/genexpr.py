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
  Delay d(size);  (d.read(t[, interp="none"|"linear"|"cubic"]), d.write(x);)
* Then statements: x = expr; if (...) {...} else if (...) {...} else {...};
  d.write(expr); outN = expr; (braces required, plain `=` only).
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
* Delay size must be a positive integer literal; interp="none" truncates the
  delay time (floor); out-of-range delay time is clamped to [0, size-1];
  a NaN delay time yields NaN.
* Reading an outN, assigning to a function name or builtin name, unary plus,
  string literals outside interp="...", and expression statements other than
  d.write(x); are errors.
* Function arguments may be reassigned (they are locals of the function).

Usage
-----
    python3 tools/genexpr.py check FILE [FILE...]
"""

import math
import random
import re
import sys
from dataclasses import dataclass, field


class GenExprError(Exception):
    """A syntax or semantic error with a 1-based line and column."""

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

DECLARATION_KEYWORDS = frozenset({"Param", "History", "Delay"})
STATEMENT_KEYWORDS = frozenset({"if", "else", "return"})
RESERVED_WORDS = DECLARATION_KEYWORDS | STATEMENT_KEYWORDS

INPUT_NAME_PATTERN = re.compile(r"^in(\d+)$")
OUTPUT_NAME_PATTERN = re.compile(r"^out(\d+)$")

DELAY_INTERPOLATION_MODES = ("none", "linear", "cubic")

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


NUMBER_PATTERN = re.compile(r"(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def tokenize(code):
    tokens = []
    position = 0
    line = 1
    line_start = 0
    length = len(code)
    while position < length:
        char = code[position]
        col = position - line_start + 1
        if char == "\n":
            line += 1
            position += 1
            line_start = position
            continue
        if char in " \t\r":
            position += 1
            continue
        if code.startswith("//", position):
            newline_at = code.find("\n", position)
            position = length if newline_at < 0 else newline_at
            continue
        if code.startswith("/*", position):
            close_at = code.find("*/", position + 2)
            if close_at < 0:
                raise GenExprError("unterminated /* comment", line, col)
            for offset in range(position, close_at + 2):
                if code[offset] == "\n":
                    line += 1
                    line_start = offset + 1
            position = close_at + 2
            continue
        if char.isdigit() or (char == "." and position + 1 < length and code[position + 1].isdigit()):
            match = NUMBER_PATTERN.match(code, position)
            text = match.group(0)
            following = code[match.end():match.end() + 1]
            if following and (following.isalpha() or following == "_"):
                raise GenExprError(f"malformed number '{text}{following}'", line, col)
            tokens.append(Token("number", text, line, col))
            position = match.end()
            continue
        if char.isalpha() or char == "_":
            match = IDENTIFIER_PATTERN.match(code, position)
            tokens.append(Token("ident", match.group(0), line, col))
            position = match.end()
            continue
        if char == '"':
            close_at = code.find('"', position + 1)
            newline_at = code.find("\n", position + 1)
            if close_at < 0 or (0 <= newline_at < close_at):
                raise GenExprError("unterminated string literal", line, col)
            tokens.append(Token("string", code[position + 1:close_at], line, col))
            position = close_at + 1
            continue
        two_characters = code[position:position + 2]
        if two_characters in SUPPORTED_MULTI_OPERATORS:
            tokens.append(Token("op", two_characters, line, col))
            position += 2
            continue
        # Compound assignment and friends are tokenised so that the parser can name them.
        if two_characters in UNSUPPORTED_OPERATORS:
            tokens.append(Token("op", two_characters, line, col))
            position += 2
            continue
        if char in SINGLE_CHARACTER_OPERATORS:
            tokens.append(Token("op", char, line, col))
            position += 1
            continue
        if char in UNSUPPORTED_OPERATORS:
            raise GenExprError(f"operator '{char}' is not supported in this GenExpr subset", line, col)
        raise GenExprError(f"unexpected character {char!r}", line, col)
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
    default: float
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
        return self.tokens[min(self.index + offset, len(self.tokens) - 1)]

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
        return [self.parse_delay_declaration(keyword)]

    def parse_param_declaration(self, keyword):
        name = self.expect_identifier("after Param")
        self.expect_op("(", "after the Param name")
        default = self.parse_signed_number("as the Param default")
        limits = {}
        while self.at_op(","):
            self.advance()
            key = self.peek()
            if key.kind != "ident" or key.text not in ("min", "max"):
                self.fail_at(key, f"expected min=... or max=... in Param, found {self.describe(key)}")
            self.advance()
            if key.text in limits:
                self.fail_at(key, f"duplicate '{key.text}' in Param {name.text}")
            self.expect_op("=", f"after '{key.text}'")
            limits[key.text] = self.parse_signed_number(f"for '{key.text}'")
        self.expect_op(")", "to close the Param")
        self.expect_semicolon("after the Param declaration")
        minimum, maximum = limits.get("min"), limits.get("max")
        if minimum is not None and maximum is not None and minimum > maximum:
            self.fail_at(name, f"Param {name.text}: min {minimum} is greater than max {maximum}")
        if (minimum is not None and default < minimum) or (maximum is not None and default > maximum):
            self.fail_at(name, f"Param {name.text}: default {default} is outside its min/max range")
        return ParamDecl(name.line, name.col, name.text, default, minimum, maximum)

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
        self.expect_op(")", "to close the Delay")
        if self.at_op(","):
            self.fail_at(self.peek(), "declare one Delay per statement")
        self.expect_semicolon("after the Delay declaration")
        return DelayDecl(name.line, name.col, name.text, int(size))

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
                if following.text == "(":
                    self.fail_at(token, f"a call to '{token.text}' cannot be used as a statement; assign its result to a variable")
            self.fail_at(following if following.kind != "eof" else token,
                         f"expected '=' after '{token.text}', found {self.describe(following)}")
        if token.kind == "op" and token.text == "{":
            self.fail_at(token, "free-standing blocks are not supported")
        self.fail_at(token, f"unexpected {self.describe(token)} at the start of a statement")

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

    def parse_binary(self, level):
        if level == len(BINARY_PRECEDENCE_LEVELS):
            return self.parse_unary()
        left = self.parse_binary(level + 1)
        while self.peek().kind == "op" and self.peek().text in BINARY_PRECEDENCE_LEVELS[level]:
            operator = self.advance()
            right = self.parse_binary(level + 1)
            left = Binary(operator.line, operator.col, operator.text, left, right)
        return left

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


class Analyzer:
    def __init__(self, program, num_inputs, num_outputs):
        self.program = program
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.params = {}
        self.histories = {}
        self.delays = {}
        self.functions = {}
        self.used_inputs = set()
        self.used_outputs = set()
        self.closed_block_locals = {}   # name -> line of the block that held it
        self.function_being_checked = None

    def error(self, node_or_position, message):
        if isinstance(node_or_position, tuple):
            raise GenExprError(message, node_or_position[0], node_or_position[1])
        raise GenExprError(message, node_or_position.line, node_or_position.col)

    def classify_reserved(self, name):
        if name in CONSTANT_NAMES:
            return "a constant"
        if name in BUILTIN_ARITY:
            return "a builtin function"
        if name in self.functions:
            return "a function"
        if name in self.params:
            return "a Param"
        if name in self.histories:
            return "a History"
        if name in self.delays:
            return "a Delay"
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
            else:
                self.declare_global_name(declaration, declaration.name, "Delay")
                self.delays[declaration.name] = declaration
        for function in self.program.functions:
            self.analyze_function(function)
        scope = Scope(None, 0)
        self.check_statements(self.program.statements, scope)
        return ProgramInfo(self.params, self.histories, self.delays, self.functions,
                           self.used_inputs, self.used_outputs)

    def analyze_function(self, function):
        existing = self.classify_reserved(function.name)
        if existing:
            self.error(function, f"cannot define function '{function.name}': the name is already {existing}")
        if function.name in self.params or function.name in self.histories or function.name in self.delays:
            self.error(function, f"function name '{function.name}' clashes with a declaration")
        scope = Scope(None, function.body.line)
        for parameter_name, line, col in function.parameters:
            if parameter_name in CONSTANT_NAMES or parameter_name in BUILTIN_ARITY or parameter_name in self.functions \
                    or INPUT_NAME_PATTERN.match(parameter_name) or OUTPUT_NAME_PATTERN.match(parameter_name):
                self.error((line, col), f"function argument '{parameter_name}' clashes with {self.classify_reserved(parameter_name)}")
            if parameter_name in scope.variables:
                self.error((line, col), f"duplicate function argument '{parameter_name}'")
            scope.variables[parameter_name] = line
        self.function_being_checked = function
        self.check_statements(function.body.statements, scope)
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
        else:
            self.error(statement, "internal error: unknown statement type")

    def check_assignment_target(self, statement, scope):
        name = statement.name
        inside_function = self.function_being_checked is not None
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
        if name in BUILTIN_ARITY or name in self.functions:
            self.error(node, f"'{name}' is a function; call it as {name}(...)")
        if name in self.closed_block_locals:
            self.error(node, f"{name} is assigned only inside the block at line {self.closed_block_locals[name]}; assign it before the if")
        self.error(node, f"'{name}' is read before it is assigned (and is not a Param, History, Delay, input or constant)")

    def check_call(self, node, scope):
        name = node.name
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
# Transpiler: AST -> Python source
# ----------------------------------------------------------------------------

SIMPLE_PYTHON_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# builtin name -> format string over already-translated argument expressions
BUILTIN_TEMPLATES = {
    "abs": "abs({0})", "sign": "_sign({0})", "floor": "_floor({0})", "ceil": "_ceil({0})",
    "trunc": "_trunc({0})", "fract": "_fract({0})", "min": "min({0}, {1})", "max": "max({0}, {1})",
    "clamp": "_clamp({0}, {1}, {2})", "wrap": "_wrap({0}, {1}, {2})", "mix": "_mix({0}, {1}, {2})",
    "exp": "_exp({0})", "log": "_log({0})", "log2": "_log2({0})", "log10": "_log10({0})",
    "pow": "_pow({0}, {1})", "sqrt": "_sqrt({0})", "sin": "_sin({0})", "cos": "_cos({0})",
    "tan": "_tan({0})", "tanh": "_tanh({0})", "atan": "_atan({0})", "atan2": "_atan2({0}, {1})",
    "noise": "(_random_uniform() * 2.0 - 1.0)",
    "dbtoa": "_dbtoa({0})", "atodb": "_atodb({0})",
}


class Transpiler:
    def __init__(self, program, info, samplerate):
        self.program = program
        self.info = info
        self.samplerate = float(samplerate)
        self.lines = []
        self.indent = 0
        self.temporary_counter = 0
        self.constants = {
            "samplerate": repr(self.samplerate),
            "pi": repr(math.pi), "twopi": repr(2 * math.pi),
            "halfpi": repr(math.pi / 2), "e": repr(math.e),
        }

    def emit(self, text):
        self.lines.append("    " * self.indent + text)

    def new_temporary(self):
        self.temporary_counter += 1
        return f"_t{self.temporary_counter}"

    # -- program --
    def transpile(self):
        for function in self.program.functions:
            self.emit_function(function)
        self.emit_render()
        return "\n".join(self.lines) + "\n"

    def emit_function(self, function):
        arguments = ", ".join(f"v_{name}" for name, _, _ in function.parameters)
        self.emit(f"def f_{function.name}({arguments}):")
        self.indent += 1
        self.emit_statements(function.body.statements)
        self.emit("return 0.0")
        self.indent -= 1
        self.emit("")

    def emit_render(self):
        info = self.info
        self.emit("def _render(_n, _params, _hist, _dbuf, _dpos, _inputs, _outputs):")
        self.indent += 1
        for name in info.params:
            self.emit(f"v_{name} = _params[{name!r}]")
        for name in info.histories:
            self.emit(f"v_{name} = _hist[{name!r}]")
        for name in info.delays:
            self.emit(f"d_{name} = _dbuf[{name!r}]")
            self.emit(f"p_{name} = _dpos[{name!r}]")
        for number in sorted(info.used_inputs):
            self.emit(f"_in_{number} = _inputs[{number - 1}]")
        for number in sorted(info.used_outputs):
            self.emit(f"_out_{number} = _outputs[{number - 1}]")
        self.emit("for _i in range(_n):")
        self.indent += 1
        for number in sorted(info.used_inputs):
            self.emit(f"v_in{number} = _in_{number}[_i]")
        for number in sorted(info.used_outputs):
            self.emit(f"v_out{number} = 0.0")
        self.emit_statements(self.program.statements)
        for number in sorted(info.used_outputs):
            self.emit(f"_out_{number}[_i] = v_out{number}")
        for name, delay in info.delays.items():
            self.emit(f"p_{name} += 1")
            self.emit(f"if p_{name} == {delay.size}: p_{name} = 0")
        self.indent -= 1
        for name in info.histories:
            self.emit(f"_hist[{name!r}] = v_{name}")
        for name in info.delays:
            self.emit(f"_dpos[{name!r}] = p_{name}")
        self.indent -= 1

    # -- statements --
    def emit_statements(self, statements):
        start_length = len(self.lines)
        for statement in statements:
            self.emit_statement(statement)
        if len(self.lines) == start_length:
            self.emit("pass")

    def emit_statement(self, statement):
        if isinstance(statement, Assign):
            self.emit(f"v_{statement.name} = {self.value(statement.expression)}")
        elif isinstance(statement, Return):
            self.emit(f"return {self.value(statement.expression)}")
        elif isinstance(statement, MethodStatement):
            call = statement.call
            self.emit(f"d_{call.object_name}[p_{call.object_name}] = {self.value(call.arguments[0])}")
        elif isinstance(statement, If):
            for branch_index, (condition, block) in enumerate(statement.branches):
                keyword = "if" if branch_index == 0 else "elif"
                self.emit(f"{keyword} {self.condition(condition)}:")
                self.indent += 1
                self.emit_statements(block.statements)
                self.indent -= 1
            if statement.else_block is not None:
                self.emit("else:")
                self.indent += 1
                self.emit_statements(statement.else_block.statements)
                self.indent -= 1
        else:
            raise GenExprError("internal error: cannot translate statement", statement.line, statement.col)

    # -- expressions --
    def condition(self, node):
        """Python boolean expression for the truth of `node` (nonzero = true)."""
        if isinstance(node, Binary):
            if node.operator in COMPARISON_OPERATORS:
                return f"({self.value(node.left)} {node.operator} {self.value(node.right)})"
            if node.operator == "&&":
                return f"({self.condition(node.left)} and {self.condition(node.right)})"
            if node.operator == "||":
                return f"({self.condition(node.left)} or {self.condition(node.right)})"
        if isinstance(node, Unary) and node.operator == "!":
            return f"(not {self.condition(node.operand)})"
        return f"({self.value(node)} != 0.0)"

    def value(self, node):
        """Python float expression for `node`."""
        if isinstance(node, Number):
            return repr(float(node.value))
        if isinstance(node, Name):
            return self.constants.get(node.name, f"v_{node.name}")
        if isinstance(node, Unary):
            if node.operator == "-":
                return f"(-{self.value(node.operand)})"
            return f"(1.0 if {self.condition(node)} else 0.0)"
        if isinstance(node, Ternary):
            return f"({self.value(node.when_true)} if {self.condition(node.condition)} else {self.value(node.when_false)})"
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
            return f"(1.0 if {self.condition(node)} else 0.0)"
        left = self.value(node.left)
        right = self.value(node.right)
        if operator in ("+", "-", "*"):
            return f"({left} {operator} {right})"
        if operator == "/":
            if isinstance(node.right, Number):
                return "0.0" if node.right.value == 0 else f"({left} / {right})"
            if SIMPLE_PYTHON_NAME.match(right):
                return f"({left} / {right} if {right} else 0.0)"
            temporary = self.new_temporary()
            return f"({left} / {temporary} if ({temporary} := {right}) else 0.0)"
        return f"_modulo({left}, {right})"

    def call_value(self, node):
        arguments = [self.value(argument) for argument in node.arguments]
        name = node.name
        if name in BUILTIN_TEMPLATES:
            return BUILTIN_TEMPLATES[name].format(*arguments)
        if name == "mstosamps":
            return f"({arguments[0]} * {self.samplerate!r} / 1000.0)"
        if name == "sampstoms":
            return f"({arguments[0]} * 1000.0 / {self.samplerate!r})"
        return f"f_{name}({', '.join(arguments)})"

    def delay_read_value(self, node):
        mode_token = node.keywords.get("interp")
        mode = mode_token.text if mode_token else "linear"
        delay = self.info.delays[node.object_name]
        return (f"_delay_read_{mode}(d_{node.object_name}, p_{node.object_name}, "
                f"{delay.size}, {self.value(node.arguments[0])})")


# ----------------------------------------------------------------------------
# Runtime helpers (the namespace the generated code runs in)
# ----------------------------------------------------------------------------

NOT_A_NUMBER = float("nan")
INFINITY = float("inf")


def _sign(x):
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)


def _rounding(function):
    def rounded(x):
        try:
            return float(function(x))
        except (OverflowError, ValueError):
            return x   # inf and nan pass through
    return rounded


_floor = _rounding(math.floor)
_ceil = _rounding(math.ceil)
_trunc = _rounding(math.trunc)


def _fract(x):
    return x - _floor(x)


def _clamp(x, low, high):
    if low > high:
        low, high = high, low
    return low if x < low else (high if x > high else x)


def _wrap(x, low, high):
    if high < low:
        low, high = high, low
    if low <= x < high:
        return x
    span = high - low
    if span == 0:
        return low
    wrapped = low + (x - low) % span
    return low if wrapped >= high else wrapped


def _mix(a, b, t):
    return a + (b - a) * t


def _exp(x):
    try:
        return math.exp(x)
    except OverflowError:
        return INFINITY


def _logarithm(function):
    def logarithm(x):
        return function(x) if x > 0 or x != x else 0.0
    return logarithm


_log = _logarithm(math.log)
_log2 = _logarithm(math.log2)
_log10 = _logarithm(math.log10)


def _pow(base, exponent):
    try:
        return math.pow(base, exponent)
    except OverflowError:
        return INFINITY
    except ValueError:
        return NOT_A_NUMBER


def _sqrt(x):
    return math.sqrt(x) if x >= 0 or x != x else 0.0


def _trigonometric(function):
    def trigonometric(x):
        try:
            return function(x)
        except (ValueError, OverflowError):
            return NOT_A_NUMBER
    return trigonometric


_sin = _trigonometric(math.sin)
_cos = _trigonometric(math.cos)
_tan = _trigonometric(math.tan)


def _modulo(a, b):
    if b == 0:
        return 0.0
    try:
        return math.fmod(a, b)
    except ValueError:
        return NOT_A_NUMBER


def _dbtoa(db):
    try:
        return 10.0 ** (db / 20.0)
    except OverflowError:
        return INFINITY


def _atodb(x):
    return 20.0 * math.log10(x) if x > 0 else (-999.0 if x == x else NOT_A_NUMBER)


def _clamp_delay_time(time_in_samples, size):
    if time_in_samples < 0.0:
        return 0.0
    if time_in_samples > size - 1:
        return float(size - 1)
    return time_in_samples


def _delay_read_none(buffer, position, size, time_in_samples):
    if time_in_samples != time_in_samples:
        return NOT_A_NUMBER
    whole = int(_clamp_delay_time(time_in_samples, size))
    return buffer[(position - whole) % size]


def _delay_read_linear(buffer, position, size, time_in_samples):
    if time_in_samples != time_in_samples:
        return NOT_A_NUMBER
    time_in_samples = _clamp_delay_time(time_in_samples, size)
    whole = int(time_in_samples)
    fraction = time_in_samples - whole
    newer = buffer[(position - whole) % size]
    if fraction == 0.0:
        return newer
    older = buffer[(position - whole - 1) % size]
    return newer + (older - newer) * fraction


def _delay_read_cubic(buffer, position, size, time_in_samples):
    if time_in_samples != time_in_samples:
        return NOT_A_NUMBER
    time_in_samples = _clamp_delay_time(time_in_samples, size)
    whole = int(time_in_samples)
    fraction = time_in_samples - whole
    # Catmull-Rom through the samples at delays whole-1, whole, whole+1, whole+2.
    y_before = buffer[(position - whole + 1) % size]
    y_start = buffer[(position - whole) % size]
    y_end = buffer[(position - whole - 1) % size]
    y_after = buffer[(position - whole - 2) % size]
    c1 = 0.5 * (y_end - y_before)
    c2 = y_before - 2.5 * y_start + 2.0 * y_end - 0.5 * y_after
    c3 = 0.5 * (y_after - y_before) + 1.5 * (y_start - y_end)
    return ((c3 * fraction + c2) * fraction + c1) * fraction + y_start


def _make_namespace():
    return {
        "_sign": _sign, "_floor": _floor, "_ceil": _ceil, "_trunc": _trunc, "_fract": _fract,
        "_clamp": _clamp, "_wrap": _wrap, "_mix": _mix, "_exp": _exp, "_log": _log,
        "_log2": _log2, "_log10": _log10, "_pow": _pow, "_sqrt": _sqrt, "_sin": _sin,
        "_cos": _cos, "_tan": _tan, "_tanh": math.tanh, "_atan": math.atan, "_atan2": math.atan2,
        "_modulo": _modulo, "_dbtoa": _dbtoa, "_atodb": _atodb,
        "_delay_read_none": _delay_read_none, "_delay_read_linear": _delay_read_linear,
        "_delay_read_cubic": _delay_read_cubic,
    }


# ----------------------------------------------------------------------------
# GenProgram
# ----------------------------------------------------------------------------

class GenProgram:
    def __init__(self, code, num_inputs, num_outputs, samplerate=44100.0, seed=1):
        self.samplerate = float(samplerate)
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        program, info = analyze(code, num_inputs, num_outputs)
        self.params = {
            name: {"default": decl.default, "min": decl.minimum, "max": decl.maximum}
            for name, decl in info.params.items()
        }
        self.histories = list(info.histories)
        self._param_values = {name: decl.default for name, decl in info.params.items()}
        self._history_values = {name: decl.initial for name, decl in info.histories.items()}
        self._delay_buffers = {name: [0.0] * decl.size for name, decl in info.delays.items()}
        self._delay_positions = {name: 0 for name in info.delays}
        self.python_source = Transpiler(program, info, self.samplerate).transpile()
        self._namespace = _make_namespace()
        self.set_seed(seed)
        try:
            exec(compile(self.python_source, "<genexpr>", "exec"), self._namespace)
        except SyntaxError as problem:
            raise RuntimeError(f"genexpr internal error: generated Python is invalid ({problem}); "
                               "most likely the expression nesting is too deep") from problem
        self._render = self._namespace["_render"]

    def set_seed(self, seed):
        self._noise_generator = random.Random(seed)
        self._namespace["_random_uniform"] = self._noise_generator.random

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
        self._param_values[name] = value

    def get_param(self, name):
        if name not in self.params:
            raise KeyError(f"unknown Param '{name}'; this program declares: {', '.join(self.params) or '(none)'}")
        return self._param_values[name]

    def get_history(self, name):
        if name not in self._history_values:
            raise KeyError(f"unknown History '{name}'; this program declares: {', '.join(self.histories) or '(none)'}")
        return self._history_values[name]

    def run(self, num_samples, inputs=None):
        if num_samples < 0:
            raise ValueError("num_samples must be >= 0")
        if inputs is None:
            inputs = [0.0] * self.num_inputs
        if len(inputs) != self.num_inputs:
            raise ValueError(f"expected {self.num_inputs} input sequence(s), got {len(inputs)}")
        input_sequences = []
        for input_index, source in enumerate(inputs):
            if isinstance(source, (int, float)):
                input_sequences.append([float(source)] * num_samples)
                continue
            if len(source) < num_samples:
                raise ValueError(f"input {input_index + 1} has {len(source)} samples, need {num_samples}")
            input_sequences.append([float(sample) for sample in source[:num_samples]])
        outputs = [[0.0] * num_samples for _ in range(self.num_outputs)]
        self._render(num_samples, self._param_values, self._history_values,
                     self._delay_buffers, self._delay_positions, input_sequences, outputs)
        return outputs


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main(argv):
    if len(argv) < 3 or argv[1] != "check":
        print("usage: python3 tools/genexpr.py check FILE [FILE...]", file=sys.stderr)
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
