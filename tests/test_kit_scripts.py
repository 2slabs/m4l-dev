"""The kit's generated scripts in node (tests/kit-scripts.test.js), on the fixture device built into a temporary
repository. Needs node on PATH (or NODE=/path/to/node): fails, saying so, without it."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_device  # noqa: E402

NODE = os.environ.get("NODE") or shutil.which("node")


class KitScriptTests(unittest.TestCase):
    def test_the_generated_scripts_in_node(self):
        if NODE is None:
            self.fail("node isn't on PATH (set NODE=/path/to/node): the kit's script tests need it")
        root = tempfile.mkdtemp(prefix="kit-scripts-")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                fixture_device.build_fixture_device(root)
            device_folder = os.path.join(root, "devices", fixture_device.FIXTURE_SCRIPT_NAME)
            run = subprocess.run([NODE, os.path.join(HERE, "kit-scripts.test.js"), device_folder],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
