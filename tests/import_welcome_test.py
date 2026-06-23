import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ImportWelcomeTest(unittest.TestCase):
    def _run_python(self, code, cwd=None, extra_pythonpath=()):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir="/tmp") as mpl_config_dir:
            pythonpath = [str(repo_root), *extra_pythonpath]
            if os.environ.get("PYTHONPATH"):
                pythonpath.append(os.environ["PYTHONPATH"])

            env = os.environ.copy()
            env["MPLCONFIGDIR"] = mpl_config_dir
            env["PYTHONPATH"] = os.pathsep.join(pythonpath)

            return subprocess.run(
                [sys.executable, "-c", code],
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
            )

    def test_direct_import_shows_welcome_once(self):
        result = self._run_python("import pm4py; import pm4py")

        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertEqual(1, result.stderr.count("Welcome to"))
        self.assertIn("PM4Py", result.stderr)
        self.assertIn("AGPL v3", result.stderr)

    def test_direct_from_import_shows_welcome(self):
        result = self._run_python("from pm4py import read_xes")

        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertEqual(1, result.stderr.count("Welcome to"))

    def test_direct_importlib_import_shows_welcome(self):
        result = self._run_python("import importlib; importlib.import_module('pm4py')")

        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertEqual(1, result.stderr.count("Welcome to"))

    def test_indirect_import_does_not_show_welcome(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as module_dir:
            Path(module_dir, "helper.py").write_text("import pm4py\n")
            result = self._run_python(
                "import helper",
                cwd=module_dir,
                extra_pythonpath=(module_dir,),
            )

        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertNotIn("Welcome to", result.stderr)


if __name__ == "__main__":
    unittest.main()
