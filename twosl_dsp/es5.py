"""Duktape, an ES5.1 engine, through ctypes: compile a script to catch syntax newer than ES5 before Max's [js] does,
or run ES5 code and read its last value.

Max's classic [js] / [jsui] run an old JavaScript engine (ES5), so `let`, `const`, arrow functions, template strings
and the like are errors there while node accepts them. `syntax_problem(source)` only compiles (it runs nothing).
`evaluate(source)` runs ES5 code and returns its last value as a string: a device build uses it to read data that
lives in a device's ES5 script, so that script stays its one source.

libduktape comes from the system: Homebrew's `brew install duktape` (it ships only libduktape.so, no .dylib, so
ctypes.util.find_library misses it on macOS) or Debian/Ubuntu's libduktape207. The loader tries the candidates in
LIBDUKTAPE_CANDIDATES (and `brew --prefix`) by full path, so no DYLD_* variable is needed (macOS's SIP strips those
from /usr/bin/python3), and fails listing every path it tried.
"""
import ctypes
import ctypes.util
import os
import shutil
import subprocess

from twosl_dsp.build_error import BuildError

DUK_COMPILE_EVAL = 1 << 3
DUK_COMPILE_SAFE = 1 << 7
DUK_COMPILE_NOSOURCE = 1 << 9
DUK_COMPILE_NOFILENAME = 1 << 11

LIBDUKTAPE_CANDIDATES = (
    "/opt/homebrew/lib/libduktape.so",      # Homebrew on Apple silicon
    "/usr/local/lib/libduktape.so",         # Homebrew on Intel, or a source install
    "libduktape.so.207",                    # Debian / Ubuntu libduktape207 (found by the dynamic loader)
)

_loaded_duktape = None


def _candidate_library_paths():
    """The places libduktape may be, the cheap ones first (`brew --prefix` runs brew, so it is asked last)."""
    found_by_ctypes = ctypes.util.find_library("duktape")
    if found_by_ctypes:
        yield found_by_ctypes
    yield from LIBDUKTAPE_CANDIDATES
    brew = shutil.which("brew")
    if brew:
        brew_prefix = subprocess.run([brew, "--prefix"], capture_output=True, text=True).stdout.strip()
        if brew_prefix:
            yield os.path.join(brew_prefix, "lib", "libduktape.so")


def load_duktape():
    """libduktape, with the return types this module uses declared (pointers are 64-bit: without restype ctypes
    takes them as 32-bit ints and the heap pointer is cut, a segfault on macOS)."""
    global _loaded_duktape
    if _loaded_duktape is not None:
        return _loaded_duktape
    tried = []
    for candidate in _candidate_library_paths():
        try:
            duktape = ctypes.CDLL(candidate)
        except OSError as problem:
            tried.append(f"{candidate}: {problem}")
            continue
        duktape.duk_create_heap.restype = ctypes.c_void_p
        duktape.duk_safe_to_lstring.restype = ctypes.c_char_p
        _loaded_duktape = duktape
        return duktape
    raise BuildError("es5: libduktape isn't installed (macOS: brew install duktape; Debian/Ubuntu: apt install "
                     "libduktape207), so the ES5 check can't run. Tried:\n  " + "\n  ".join(tried))


def _run_in_fresh_heap(source_bytes, run):
    duktape = load_duktape()
    heap = duktape.duk_create_heap(None, None, None, None, None)
    if not heap:
        raise BuildError("es5: duk_create_heap failed (out of memory?)")
    try:
        return run(duktape, ctypes.c_void_p(heap), source_bytes)
    finally:
        duktape.duk_destroy_heap(ctypes.c_void_p(heap))


def _top_of_stack_as_text(duktape, heap):
    return duktape.duk_safe_to_lstring(heap, ctypes.c_int(-1), None).decode("utf-8", "replace")


def syntax_problem(source):
    """None when `source` compiles as ES5, else Duktape's message (with the line)."""
    def compile_only(duktape, heap, source_bytes):
        result = duktape.duk_compile_raw(heap, ctypes.c_char_p(source_bytes), ctypes.c_size_t(len(source_bytes)),
                                         ctypes.c_uint(DUK_COMPILE_SAFE | DUK_COMPILE_NOSOURCE | DUK_COMPILE_NOFILENAME))
        return None if result == 0 else _top_of_stack_as_text(duktape, heap)
    return _run_in_fresh_heap(source.encode("utf-8"), compile_only)


def evaluate(source):
    """Run ES5 `source` in a fresh heap; its last expression's value, as a string. Raises BuildError with
    Duktape's message when the code throws or isn't ES5."""
    def evaluate_in_heap(duktape, heap, source_bytes):
        result = duktape.duk_eval_raw(heap, ctypes.c_char_p(source_bytes), ctypes.c_size_t(len(source_bytes)),
                                      ctypes.c_uint(DUK_COMPILE_EVAL | DUK_COMPILE_SAFE | DUK_COMPILE_NOSOURCE
                                                    | DUK_COMPILE_NOFILENAME))
        value = _top_of_stack_as_text(duktape, heap)
        if result != 0:
            raise BuildError(f"ES5 code threw or did not compile: {value}")
        return value
    return _run_in_fresh_heap(source.encode("utf-8"), evaluate_in_heap)
