import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

RUN_TESTS = Path(__file__).resolve().parent / "run_tests.py"
SPEC = importlib.util.spec_from_file_location("jig_run_tests", RUN_TESTS)
run_tests = importlib.util.module_from_spec(SPEC)
assert SPEC is not None
assert SPEC.loader is not None
SPEC.loader.exec_module(run_tests)


class PyrightGateTests(unittest.TestCase):
    def test_resolver_prefers_path_pyright(self):
        with patch.object(
            run_tests.shutil, "which",
            side_effect=lambda name: f"/bin/{name}" if name == "pyright" else None,
        ):
            self.assertEqual(
                run_tests._resolve_pyright_gate(),
                ["pyright", "--outputjson"],
            )

    def test_resolver_falls_back_to_uvx_then_pipx(self):
        with patch.object(
            run_tests.shutil, "which",
            side_effect=lambda name: f"/bin/{name}" if name == "uvx" else None,
        ):
            self.assertEqual(
                run_tests._resolve_pyright_gate(),
                ["uvx", "pyright", "--outputjson"],
            )
        with patch.object(
            run_tests.shutil, "which",
            side_effect=lambda name: f"/bin/{name}" if name == "pipx" else None,
        ):
            self.assertEqual(
                run_tests._resolve_pyright_gate(),
                ["pipx", "run", "pyright", "--outputjson"],
            )

    def test_pyright_diagnostic_fails_gate(self):
        report = {
            "generalDiagnostics": [{
                "file": "/repo/skills/example.py",
                "range": {"start": {"line": 4}},
                "rule": "reportOptionalMemberAccess",
                "message": "\"name\" is not a known attribute of \"None\"",
            }],
            "summary": {
                "errorCount": 1,
                "warningCount": 0,
                "informationCount": 0,
            },
        }
        completed = subprocess.CompletedProcess(
            ["pyright"], 1, stdout=json.dumps(report), stderr="",
        )

        with patch.object(run_tests, "_resolve_pyright_gate",
                          return_value=["pyright", "--outputjson"]):
            with patch.object(run_tests.subprocess, "run",
                              return_value=completed) as mock_run:
                with patch("sys.stderr", new_callable=io.StringIO) as err:
                    self.assertFalse(run_tests.run_pyright_gate(Path("/repo")))

        mock_run.assert_called_once_with(
            ["pyright", "--outputjson"],
            cwd="/repo",
            capture_output=True,
            text=True,
        )
        self.assertIn("pyright: 1 error(s)", err.getvalue())
        self.assertIn("skills/example.py:5", err.getvalue())
        self.assertIn("reportOptionalMemberAccess", err.getvalue())

    def test_pyright_clean_passes_gate(self):
        completed = subprocess.CompletedProcess(["pyright"], 0, stdout="{}", stderr="")

        with patch.object(run_tests, "_resolve_pyright_gate",
                          return_value=["pyright", "--outputjson"]):
            with patch.object(run_tests.subprocess, "run", return_value=completed):
                with patch("sys.stderr", new_callable=io.StringIO) as err:
                    self.assertTrue(run_tests.run_pyright_gate(Path("/repo")))

        self.assertIn("pyright: clean", err.getvalue())

    def test_missing_pyright_fails_gate(self):
        with patch.object(run_tests, "_resolve_pyright_gate", return_value=None):
            with patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertFalse(run_tests.run_pyright_gate(Path("/repo")))
        self.assertIn("no type checker found", err.getvalue())


if __name__ == "__main__":
    unittest.main()
