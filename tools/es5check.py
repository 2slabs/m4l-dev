#!/usr/bin/env python3
"""Compile scripts with Duktape, an ES5.1 engine, to catch syntax newer than ES5 before Max's `js` object does.

  python3 tools/es5check.py devices/2sl-drums/*.js

Max's classic [js] / [jsui] run an old JavaScript engine (ES5), so `let`, `const`, arrow functions, template
strings and the like are errors there, while node accepts them. The command line only compiles (syntax); it runs
nothing. `evaluate(source)` runs ES5 code and returns its last value as a string: device generators use it to read
data that lives in a device's ES5 script (2sl drums' function registry), so that script stays its one source.
Uses the system's libduktape (Ubuntu: libduktape207) through ctypes; fails loudly if it isn't there.
"""
import ctypes
import ctypes.util
import sys

DUK_COMPILE_EVAL = 1 << 3
DUK_COMPILE_SAFE = 1 << 7
DUK_COMPILE_NOSOURCE = 1 << 9
DUK_COMPILE_NOFILENAME = 1 << 11


def load_duktape():
    for name in ("libduktape.so.207", ctypes.util.find_library("duktape")):
        if not name:
            continue
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue
    sys.exit("es5check.py: libduktape isn't installed (apt install libduktape207): can't check ES5 syntax")


def check(duktape, path):
    source = open(path, "rb").read()
    heap = duktape.duk_create_heap(None, None, None, None, None)
    if not heap:
        sys.exit("es5check.py: duk_create_heap failed")
    try:
        result = duktape.duk_compile_raw(ctypes.c_void_p(heap), ctypes.c_char_p(source), ctypes.c_size_t(len(source)),
                                         ctypes.c_uint(DUK_COMPILE_SAFE | DUK_COMPILE_NOSOURCE | DUK_COMPILE_NOFILENAME))
        if result == 0:
            return None
        duktape.duk_safe_to_lstring.restype = ctypes.c_char_p
        message = duktape.duk_safe_to_lstring(ctypes.c_void_p(heap), ctypes.c_int(-1), None)
        return message.decode("utf-8", "replace")
    finally:
        duktape.duk_destroy_heap(ctypes.c_void_p(heap))


class EvaluationError(Exception):
    """The ES5 code threw (or didn't compile): the message is Duktape's."""


def evaluate(source):
    """Run ES5 `source` in a fresh Duktape heap; its last expression's value, as a string. Throws EvaluationError
    with Duktape's message when the code throws or isn't ES5."""
    duktape = load_duktape()
    duktape.duk_create_heap.restype = ctypes.c_void_p
    duktape.duk_safe_to_lstring.restype = ctypes.c_char_p
    heap = duktape.duk_create_heap(None, None, None, None, None)
    if not heap:
        sys.exit("es5check.py: duk_create_heap failed")
    try:
        encoded = source.encode("utf-8")
        result = duktape.duk_eval_raw(ctypes.c_void_p(heap), ctypes.c_char_p(encoded), ctypes.c_size_t(len(encoded)),
                                      ctypes.c_uint(DUK_COMPILE_EVAL | DUK_COMPILE_SAFE | DUK_COMPILE_NOSOURCE
                                                    | DUK_COMPILE_NOFILENAME))
        value = duktape.duk_safe_to_lstring(ctypes.c_void_p(heap), ctypes.c_int(-1), None).decode("utf-8", "replace")
        if result != 0:
            raise EvaluationError(value)
        return value
    finally:
        duktape.duk_destroy_heap(ctypes.c_void_p(heap))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    duktape = load_duktape()
    failures = 0
    for path in sys.argv[1:]:
        problem = check(duktape, path)
        print(f"{path}: {'ok (ES5)' if problem is None else problem}")
        failures += problem is not None
    sys.exit(1 if failures else 0)
