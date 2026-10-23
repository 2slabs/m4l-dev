"""Build C source into a shared library once, cache it, load it: the one place the kit runs a C compiler.

Used by the GenExpr renderer (twosl_dsp/genexpr.py: the translated program) and the patch matcher's analysis
(twosl_dsp/patch_match_score.py: patch_match_features.c). The library is cached per source text, compiler (path and
--version) and flags, in $TWOSL_DSP_GENEXPR_CACHE (default ~/.cache/2sl-dsp/genexpr), shared between processes and runs;
parallel processes wanting the same library wait for one build. No C compiler, or a compiler that refuses the source,
is a CLibraryBuildError saying so.
"""
import ctypes
import hashlib
import os
import shutil
import subprocess

from twosl_dsp.build_error import BuildError

C_COMPILER_ENVIRONMENT_VARIABLE = "CC"
CACHE_DIRECTORY_ENVIRONMENT_VARIABLE = "TWOSL_DSP_GENEXPR_CACHE"


class CLibraryBuildError(BuildError):
    """No C compiler, or the compiler refused the source."""


_compiler_identity_by_command = {}
_loaded_library_by_path = {}


def c_compiler_command():
    command = os.environ.get(C_COMPILER_ENVIRONMENT_VARIABLE, "cc")
    if shutil.which(command) is None:
        raise CLibraryBuildError(
            f"the kit builds C (the GenExpr renderer, the patch matcher's analysis) with a C compiler and '{command}' "
            f"is not on PATH: install one (gcc or clang) or set {C_COMPILER_ENVIRONMENT_VARIABLE}=/path/to/compiler")
    return command


def c_compiler_identity(command):
    if command not in _compiler_identity_by_command:
        try:
            completed = subprocess.run([command, "--version"], capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError) as problem:
            raise CLibraryBuildError(f"the C compiler '{command}' does not answer --version: {problem}") from problem
        _compiler_identity_by_command[command] = shutil.which(command) + "\n" + completed.stdout
    return _compiler_identity_by_command[command]


def build_cache_directory():
    directory = os.environ.get(CACHE_DIRECTORY_ENVIRONMENT_VARIABLE)
    if not directory:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
        directory = os.path.join(base, "2sl-dsp", "genexpr")
    os.makedirs(directory, exist_ok=True)
    return directory


def build_library(command, compiler_flags, c_source, library_path):
    source_path = f"{library_path}.{os.getpid()}.c"
    building_path = f"{library_path}.{os.getpid()}.building"
    with open(source_path, "w", encoding="utf-8") as handle:
        handle.write(c_source)
    try:
        completed = subprocess.run([command, *compiler_flags, "-o", building_path, source_path, "-lm"],
                                   capture_output=True, text=True)
        if completed.returncode != 0:
            raise CLibraryBuildError(f"the C compiler refused the C source ({source_path} kept):\n{completed.stderr}")
        os.replace(building_path, library_path)   # atomic: a reader never sees half a library
        os.remove(source_path)
    finally:
        if os.path.exists(building_path):
            os.remove(building_path)


def load_c_library(c_source, compiler_flags, file_name_prefix=""):
    """The ctypes library of `c_source`: built once per source, compiler and flags into the cache directory (shared
    between processes and runs), loaded once per process. `file_name_prefix` only names the cached file."""
    command = c_compiler_command()
    digest = hashlib.sha256("\n".join((c_compiler_identity(command), " ".join(compiler_flags), c_source))
                            .encode("utf-8")).hexdigest()
    library_path = os.path.join(build_cache_directory(), f"{file_name_prefix}{digest}.so")
    if library_path in _loaded_library_by_path:
        return _loaded_library_by_path[library_path]
    if not os.path.exists(library_path):
        import fcntl   # POSIX only: parallel processes that want the same library wait for one build of it
        with open(f"{library_path}.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not os.path.exists(library_path):
                build_library(command, compiler_flags, c_source, library_path)
    library = ctypes.CDLL(library_path)
    _loaded_library_by_path[library_path] = library
    return library
