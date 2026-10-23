"""The device repository contract: where a device's sources are, where its build writes, and where the kit is.

    <device repo>/
      build.py                     the build's entry point (puts 2sl-dsp on sys.path, calls the device's build)
      2sl-dsp/                     this kit, as an initialised git submodule (never written by a build)
      src/                         hand-written sources only (Python, script templates, the preset book) and
        live-parameters.lock.json  the Live parameter lock (twosl_dsp/live_parameter_identity.py)
      devices/<script name>/       the development build: written by the build, committed
      dist/                        the release: written by the build, not committed

architecture/device-repository.md has the reasoning.
"""
import os

import twosl_dsp
from twosl_dsp.build_error import BuildError

KIT_SUBMODULE_DIRECTORY_NAME = "2sl-dsp"
KIT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(twosl_dsp.__file__)))


class DeviceRepository:
    def __init__(self, root_directory):
        """A repository rooted at `root_directory`, which must have src/. The kit checks below are of_build_script's;
        a test can make one in a temporary folder with this constructor."""
        self.root_directory = os.path.abspath(root_directory)
        self.source_directory = os.path.join(self.root_directory, "src")
        self.devices_directory = os.path.join(self.root_directory, "devices")
        self.dist_directory = os.path.join(self.root_directory, "dist")
        # the kit first: it is refused whatever it holds (it has no src/, and must not get one by accident)
        if os.path.realpath(self.root_directory) == os.path.realpath(KIT_DIRECTORY):
            raise BuildError(f"{self.root_directory} is the kit itself: a device is built from its own repository, "
                             "with the kit as its 2sl-dsp submodule")
        if not os.path.isdir(self.source_directory):
            raise BuildError(f"{self.root_directory} is no device repository: it has no src/ (see 2sl-dsp "
                             "architecture/device-repository.md)")

    @classmethod
    def of_build_script(cls, build_script_path):
        """The repository whose root holds `build_script_path` (the build's __file__). Fails unless the root has src/
        and an initialised 2sl-dsp submodule, and the kit running is that submodule (not another checkout)."""
        root_directory = os.path.dirname(os.path.abspath(build_script_path))
        repository = cls(root_directory)
        submodule_directory = os.path.join(root_directory, KIT_SUBMODULE_DIRECTORY_NAME)
        if not os.path.isdir(os.path.join(submodule_directory, "twosl_dsp")):
            raise BuildError(f"{submodule_directory} has no kit: run `git submodule update --init` in {root_directory}")
        if not os.path.exists(os.path.join(submodule_directory, ".git")):
            raise BuildError(f"{submodule_directory} isn't a git submodule checkout (no .git): add the kit with "
                             "`git submodule add https://github.com/2slabs/2sl-dsp.git 2sl-dsp`")
        if os.path.realpath(KIT_DIRECTORY) != os.path.realpath(submodule_directory):
            raise BuildError(f"the kit running is {KIT_DIRECTORY}, not this repository's submodule "
                             f"{submodule_directory}: build.py must put {KIT_SUBMODULE_DIRECTORY_NAME}/ first on sys.path")
        return repository

    def source_path(self, file_name):
        return os.path.join(self.source_directory, file_name)

    def device_directory(self, script_name):
        return os.path.join(self.devices_directory, script_name)

    def relative(self, path):
        """`path` relative to the repository root, for the build's log."""
        return os.path.relpath(path, self.root_directory)

    def check_writable(self, path):
        """Fails if a build would write `path` outside the repository, or inside the kit."""
        real_path = os.path.realpath(path)
        if os.path.commonpath([real_path, os.path.realpath(KIT_DIRECTORY)]) == os.path.realpath(KIT_DIRECTORY):
            raise BuildError(f"the build tried to write {path}, inside the kit ({KIT_DIRECTORY}); the kit is never "
                             "written by a build")
        if os.path.commonpath([real_path, os.path.realpath(self.root_directory)]) != os.path.realpath(self.root_directory):
            raise BuildError(f"the build tried to write {path}, outside the repository {self.root_directory}")
        return path
