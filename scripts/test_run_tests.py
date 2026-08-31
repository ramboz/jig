import importlib.util
import io
import json
import subprocess
import tempfile
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


class Bug021TargetedSelectorTests(unittest.TestCase):
    """Bug 021: run_tests.py accepts optional `path::Class[::method]` selector
    args and runs just the named tests (no pyright), so jig's own
    `.jig/test-command` can honor tdd.py's `{test}` placeholder instead of
    silently running the whole suite. An unresolved selector reports
    "no matching tests" (exit 1) — which tdd.py maps to exit 2, never red."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        skill = self.root / "skills" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "test_demo.py").write_text(
            "import unittest\n"
            "\n"
            "\n"
            "class PassingCase(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertTrue(True)\n"
            "\n"
            "    def test_ok_too(self):\n"
            "        self.assertTrue(True)\n"
            "\n"
            "\n"
            "class FailingCase(unittest.TestCase):\n"
            "    def test_no(self):\n"
            "        self.fail('deliberately red')\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, suite: unittest.TestSuite) -> unittest.TestResult:
        return unittest.TextTestRunner(
            stream=io.StringIO(), verbosity=0,
        ).run(suite)

    def test_class_selector_runs_only_named_class(self):
        suite, missing = run_tests.build_suite_from_selectors(
            ["skills/demo-skill/test_demo.py::PassingCase"], root=self.root,
        )
        self.assertEqual(missing, [])
        self.assertEqual(suite.countTestCases(), 2)
        self.assertTrue(self._run(suite).wasSuccessful())

    def test_method_selector_runs_single_test(self):
        suite, missing = run_tests.build_suite_from_selectors(
            ["skills/demo-skill/test_demo.py::FailingCase::test_no"],
            root=self.root,
        )
        self.assertEqual(missing, [])
        self.assertEqual(suite.countTestCases(), 1)
        self.assertFalse(self._run(suite).wasSuccessful())

    def test_unresolved_selector_is_reported_not_run(self):
        suite, missing = run_tests.build_suite_from_selectors(
            ["skills/demo-skill/test_demo.py::GhostCase"], root=self.root,
        )
        self.assertEqual(missing, ["skills/demo-skill/test_demo.py::GhostCase"])
        _, missing_path = run_tests.build_suite_from_selectors(
            ["skills/ghost/test_ghost.py::Nope"], root=self.root,
        )
        self.assertEqual(missing_path, ["skills/ghost/test_ghost.py::Nope"])

    def test_main_with_selector_skips_pyright_and_reports_no_match(self):
        with patch.object(run_tests, "ROOT", self.root):
            with patch.object(run_tests, "run_pyright_gate") as gate:
                with patch("sys.stderr", new_callable=io.StringIO):
                    code = run_tests.main(
                        ["skills/demo-skill/test_demo.py::PassingCase"],
                    )
        self.assertEqual(code, 0)
        gate.assert_not_called()

        with patch.object(run_tests, "ROOT", self.root):
            with patch("sys.stderr", new_callable=io.StringIO) as err:
                code = run_tests.main(["skills/ghost/test_ghost.py::Nope"])
        self.assertEqual(code, 1)
        self.assertIn(
            "no matching tests: skills/ghost/test_ghost.py::Nope",
            err.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
