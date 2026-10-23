"""The `outlet(index, message, ...)` calls of an ES5 script ([js] / [jsui]), read from its text.

What the build needs from a device's script: which outlet each call sends from, and what message name it sends, so a
message sent straight into a gen~ can be held to the Params that gen~ declares (DevicePatchBuilder.
check_script_messages_into_gen). The script is tokenized (string literals in either quote with escapes, comments,
regular expression literals, nested brackets), not run.

An OutletCall says:
  outlet_index: the outlet as an int (a number literal, or a name the script binds once with `var NAME = <int>`), or
                None when the text can't say (`spec.outlet`); `outlet_expression` is that argument's text
  message: a MessageName: the first argument after the index as a regular expression of the names it can send
           ("hit_count" exactly; "random_" + n + "_draw" as random_.+_draw), or None when it can't be read (a bare
           variable, a call, a ternary, no argument), with `message_text` that argument's text
"""
import json
import re
from dataclasses import dataclass
from typing import Optional

from twosl_dsp.build_error import BuildError

PUNCTUATORS = sorted(["{", "}", "(", ")", "[", "]", ";", ",", "<", ">", "<=", ">=", "==", "!=", "===", "!==", "+", "-",
                      "*", "%", "++", "--", "<<", ">>", ">>>", "&", "|", "^", "!", "~", "&&", "||", "?", ":", "=", "+=",
                      "-=", "*=", "%=", "<<=", ">>=", ">>>=", "&=", "|=", "^=", ".", "/", "/="], key=len, reverse=True)
# after one of these a `/` starts a regular expression literal, not a division
REGEX_MAY_FOLLOW = {"(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "+", "-", "*", "%", "<", ">", "~", "^",
                    "&&", "||", "==", "!=", "===", "!==", "<=", ">=", "+=", "-=", "*=", "/=", "%=", "return",
                    "typeof", "case", "in", "delete", "void", "throw", "new"}
IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
NUMBER = re.compile(r"(0[xX][0-9a-fA-F]+|(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?)")
STRING_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


@dataclass(frozen=True)
class Token:
    kind: str           # "identifier", "number", "string", "regex", "punctuator"
    text: str           # as written (a string's value for "string")
    line: int


@dataclass(frozen=True)
class MessageName:
    pattern: str        # a regular expression the whole message name must match
    is_literal: bool    # one string literal: the name exactly


@dataclass(frozen=True)
class OutletCall:
    line: int
    outlet_index: Optional[int]
    outlet_expression: str
    message: Optional[MessageName]
    message_text: str


def tokens_of(script_text, script_name):
    """The script's tokens, comments left out. Fails on an unterminated string, comment or regular expression."""
    tokens, position, line, length = [], 0, 1, len(script_text)
    while position < length:
        character = script_text[position]
        if character == "\n":
            line += 1
            position += 1
        elif character.isspace():
            position += 1
        elif script_text.startswith("//", position):
            end = script_text.find("\n", position)
            position = length if end < 0 else end
        elif script_text.startswith("/*", position):
            end = script_text.find("*/", position + 2)
            if end < 0:
                raise BuildError(f"{script_name}: line {line}: a /* comment that never ends")
            line += script_text.count("\n", position, end)
            position = end + 2
        elif character in "\"'":
            value, position = read_string(script_text, position, line, script_name)
            tokens.append(Token("string", value, line))
        elif character == "/" and regex_may_start_after(tokens[-1] if tokens else None):
            start = position
            position = read_regex_end(script_text, position, line, script_name)
            tokens.append(Token("regex", script_text[start:position], line))
        elif IDENTIFIER.match(script_text, position):
            match = IDENTIFIER.match(script_text, position)
            tokens.append(Token("identifier", match.group(), line))
            position = match.end()
        elif character.isdigit() or (character == "." and position + 1 < length and script_text[position + 1].isdigit()):
            match = NUMBER.match(script_text, position)
            tokens.append(Token("number", match.group(), line))
            position = match.end()
        else:
            for punctuator in PUNCTUATORS:
                if script_text.startswith(punctuator, position):
                    tokens.append(Token("punctuator", punctuator, line))
                    position += len(punctuator)
                    break
            else:
                raise BuildError(f"{script_name}: line {line}: {character!r} is no ES5 token")
    return tokens


def regex_may_start_after(previous_token):
    """True when a `/` after `previous_token` (None: the script's start) starts a regular expression literal."""
    if previous_token is None:
        return True
    return previous_token.kind in ("punctuator", "identifier") and previous_token.text in REGEX_MAY_FOLLOW


def read_string(script_text, position, line, script_name):
    quote, position, characters = script_text[position], position + 1, []
    while position < len(script_text):
        character = script_text[position]
        if character == quote:
            return "".join(characters), position + 1
        if character == "\n":
            break
        if character == "\\":
            escaped = script_text[position + 1:position + 2]
            if escaped == "\n":                         # a line continuation
                position += 2
                continue
            characters.append(STRING_ESCAPES.get(escaped, escaped))
            position += 2
            continue
        characters.append(character)
        position += 1
    raise BuildError(f"{script_name}: line {line}: a string literal that never ends")


def read_regex_end(script_text, position, line, script_name):
    position, in_class = position + 1, False
    while position < len(script_text):
        character = script_text[position]
        if character == "\n":
            break
        if character == "\\":
            position += 2
            continue
        if character == "[":
            in_class = True
        elif character == "]":
            in_class = False
        elif character == "/" and not in_class:
            position += 1
            while position < len(script_text) and (script_text[position].isalnum() or script_text[position] == "_"):
                position += 1                           # its flags
            return position
        position += 1
    raise BuildError(f"{script_name}: line {line}: a regular expression literal that never ends")


def text_of(tokens):
    """The tokens as text: spaced, except around a `.` (`spec.outlet`); a string as a quoted literal."""
    text, previous_written = "", None
    for token in tokens:
        written = json.dumps(token.text) if token.kind == "string" else token.text
        spaced = previous_written is not None and "." not in (written, previous_written)
        text += (" " if spaced else "") + written
        previous_written = written
    return text


def split_arguments(tokens, open_index, script_name):
    """The argument token lists of the call whose `(` is tokens[open_index], and the index after its `)`."""
    arguments, current, depth, index = [], [], 0, open_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "punctuator" and token.text in "([{":
            depth += 1
        elif token.kind == "punctuator" and token.text in ")]}":
            if depth == 0:
                if token.text != ")":
                    break
                if current or arguments:
                    arguments.append(current)
                return arguments, index + 1
            depth -= 1
        elif token.kind == "punctuator" and token.text == "," and depth == 0:
            arguments.append(current)
            current = []
            index += 1
            continue
        current.append(token)
        index += 1
    raise BuildError(f"{script_name}: line {tokens[open_index].line}: an outlet( call whose brackets don't close")


def split_on_plus(tokens):
    """The parts of a `+` chain at the top level (unary + and +=-style operators aren't the punctuator "+")."""
    parts, current, depth = [], [], 0
    for token in tokens:
        if token.kind == "punctuator" and token.text in "([{":
            depth += 1
        elif token.kind == "punctuator" and token.text in ")]}":
            depth -= 1
        if token.kind == "punctuator" and token.text == "+" and depth == 0:
            parts.append(current)
            current = []
            continue
        current.append(token)
    parts.append(current)
    return parts


def message_name_of(tokens):
    """The MessageName of a message argument, or None when it can't be read: it must be a string literal, or a `+`
    chain with at least one string literal part (every other part stands for any text: `.+`)."""
    if len(tokens) == 1 and tokens[0].kind == "string":
        return MessageName(re.escape(tokens[0].text), True)
    parts = split_on_plus(tokens)
    if len(parts) < 2 or any(not part for part in parts):
        return None
    if not any(len(part) == 1 and part[0].kind == "string" for part in parts):
        return None
    return MessageName("".join(re.escape(part[0].text) if len(part) == 1 and part[0].kind == "string" else ".+"
                               for part in parts), False)


def integer_constants(tokens):
    """{name: int} for each name the script binds exactly once, as `var NAME = <int>` (a name bound twice, or
    assigned elsewhere, is left out: its value isn't one number)."""
    bound, assigned_elsewhere = {}, set()
    for index, token in enumerate(tokens):
        if token.kind != "identifier":
            continue
        following = tokens[index + 1:index + 4]
        is_var_binding = index > 0 and tokens[index - 1].text in ("var", ",") and tokens[index - 1].kind != "string"
        if (is_var_binding and len(following) >= 2 and following[0].text == "=" and following[1].kind == "number"
                and (len(following) < 3 or following[2].text in (";", ","))
                and re.fullmatch(r"\d+", following[1].text)):
            bound.setdefault(token.text, []).append(int(following[1].text))
        elif following and following[0].kind == "punctuator" and following[0].text in (
                "=", "+=", "-=", "*=", "/=", "%=", "++", "--") and not is_var_binding:
            assigned_elsewhere.add(token.text)
        elif index > 0 and tokens[index - 1].text in ("++", "--"):
            assigned_elsewhere.add(token.text)
    return {name: values[0] for name, values in bound.items() if len(values) == 1 and name not in assigned_elsewhere}


def outlet_calls(script_text, script_name):
    """Every `outlet(...)` call of the script (not `x.outlet(...)`, not `function outlet(...)`), as OutletCalls.
    Fails on a call with no arguments."""
    tokens = tokens_of(script_text, script_name)
    constants = integer_constants(tokens)
    calls = []
    for index, token in enumerate(tokens):
        if not (token.kind == "identifier" and token.text == "outlet" and index + 1 < len(tokens)
                and tokens[index + 1].text == "(" and tokens[index + 1].kind == "punctuator"):
            continue
        if index > 0 and tokens[index - 1].text in (".", "function") and tokens[index - 1].kind != "string":
            continue
        arguments, _ = split_arguments(tokens, index + 1, script_name)
        if not arguments or not arguments[0]:
            raise BuildError(f"{script_name}: line {token.line}: outlet() with no outlet index")
        index_tokens = arguments[0]
        outlet_index = None
        if len(index_tokens) == 1 and index_tokens[0].kind == "number" and re.fullmatch(r"\d+", index_tokens[0].text):
            outlet_index = int(index_tokens[0].text)
        elif len(index_tokens) == 1 and index_tokens[0].kind == "identifier":
            outlet_index = constants.get(index_tokens[0].text)
        message_tokens = arguments[1] if len(arguments) > 1 else []
        calls.append(OutletCall(token.line, outlet_index, text_of(index_tokens),
                                message_name_of(message_tokens) if message_tokens else None,
                                text_of(message_tokens) if message_tokens else "(nothing)"))
    return calls
