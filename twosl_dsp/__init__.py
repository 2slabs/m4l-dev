"""2sl-dsp: the 2sl kit for building Max for Live devices from Python.

A device lives in its own repository with this repository as a git submodule at `<device repo>/2sl-dsp`
(architecture/device-repository.md). Its `build.py` puts the submodule on sys.path and imports from here:

    from twosl_dsp.device_repository import DeviceRepository
    from twosl_dsp.patch_builder import DevicePatchBuilder
    from twosl_dsp.device_build import build_device

Python 3.9 or later, standard library only (plus the system's libduktape for the ES5 check: twosl_dsp/es5.py).
"""
