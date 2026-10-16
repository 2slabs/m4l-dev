"""m4l-dev: the 2sl kit for building Max for Live devices from Python.

A device lives in its own repository with this repository as a git submodule at `<device repo>/m4l-dev`
(architecture/device-repository.md). Its `build.py` puts the submodule on sys.path and imports from here:

    from m4l_dev.device_repository import DeviceRepository
    from m4l_dev.patch_builder import DevicePatchBuilder
    from m4l_dev.device_build import build_device

Python 3.9 or later, standard library only (plus the system's libduktape for the ES5 check: m4l_dev/es5.py).
"""
