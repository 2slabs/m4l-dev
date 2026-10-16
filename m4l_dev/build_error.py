"""The one way a build fails: BuildError, with a message that says what is wrong and where to fix it."""


class BuildError(Exception):
    """A broken build. Raised before anything half-checked is written; never caught inside the kit, so the
    build stops with the traceback and the message."""
