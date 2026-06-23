"""
AC verification tests for slices 006-01, 006-04, 006-05.

Run from the repo root:
    python3 -m unittest discover -s skills/tdd-loop -p 'test_*.py'
"""

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
TDD_PY = REPO_ROOT / "skills" / "tdd-loop" / "tdd.py"
SKILL_MD = REPO_ROOT / "skills" / "tdd-loop" / "SKILL.md"


def run_tdd(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    """Invoke tdd.py as a subprocess. `cwd` lets tests run against a tmp dir."""
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, str(TDD_PY), *args],
        capture_output=True, text=True, env=env,
        cwd=str(cwd) if cwd else None,
    )


def _load_tdd():
    """Load tdd.py as a module for direct-call tests with mocking."""
    spec = importlib.util.spec_from_file_location("tdd", TDD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path: Path, content: str = "") -> Path:
    """Helper: create parent dirs and write `content` to `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# -------------------- DetectTests --------------------


class DetectTests(unittest.TestCase):
    """AC #1 — `tdd.py detect [target]` returns runner name + priority rules."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    # ---- pytest signals ----

    def test_pytest_via_pytest_ini(self):
        write(self.target / "pytest.ini", "[pytest]\n")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_pytest_via_conftest(self):
        write(self.target / "conftest.py", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_pytest_via_pyproject(self):
        write(self.target / "pyproject.toml", "[tool.pytest.ini_options]\n")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_pytest_via_test_file(self):
        write(self.target / "test_foo.py", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_pytest_via_test_suffix_file(self):
        write(self.target / "foo_test.py", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_pytest_via_test_file_in_subdir(self):
        # Direct subdir counts (per spec AC #1 — "any direct subdirectory").
        write(self.target / "tests" / "test_foo.py", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    # ---- vitest signals ----

    def test_vitest_via_config(self):
        write(self.target / "vitest.config.ts", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "vitest")

    def test_vitest_via_package_json(self):
        write(self.target / "package.json",
              json.dumps({"devDependencies": {"vitest": "^1.0.0"}}))
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "vitest")

    # ---- jest signals ----

    def test_jest_via_config(self):
        write(self.target / "jest.config.js", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "jest")

    def test_jest_via_package_json(self):
        write(self.target / "package.json",
              json.dumps({"devDependencies": {"jest": "^29.0.0"}}))
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "jest")

    # ---- priority rules ----

    def test_priority_pytest_over_jest(self):
        write(self.target / "pytest.ini", "[pytest]\n")
        write(self.target / "jest.config.js", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_priority_pytest_over_vitest(self):
        write(self.target / "pytest.ini", "[pytest]\n")
        write(self.target / "vitest.config.ts", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_priority_vitest_over_jest(self):
        write(self.target / "vitest.config.ts", "")
        write(self.target / "jest.config.js", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "vitest")

    # ---- no-signal cases ----

    def test_cli_no_runner_exits_2(self):
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no test runner detected", r.stderr)
        self.assertIn(str(self.target), r.stderr)

    def test_cli_default_target_dot(self):
        # No `target` arg → defaults to `.`. We `cwd` into an empty tmp dir so
        # the default `.` resolves to a directory with no runner signals.
        r = run_tdd("detect", cwd=self.target)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no test runner detected", r.stderr)


# -------------------- RunTests --------------------


class RunTests(unittest.TestCase):
    """AC #2 — `tdd.py run [target]` invokes runner + normalizes exit code."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pytest_real_run_all_green(self):
        # Real pytest run, but only if pytest is installed locally. The DoR
        # claims pytest is available; if it's not, skip rather than failing
        # noisily.
        try:
            import pytest  # noqa: F401
        except ImportError:
            self.skipTest("pytest not installed in this environment")
        write(self.target / "pytest.ini", "[pytest]\n")
        write(self.target / "test_pass.py",
              "def test_truthy():\n    assert True\n")
        r = run_tdd("run", str(self.target))
        self.assertEqual(r.returncode, 0,
                         f"expected exit 0; stderr={r.stderr}; stdout={r.stdout}")

    def test_pytest_real_run_one_red(self):
        try:
            import pytest  # noqa: F401
        except ImportError:
            self.skipTest("pytest not installed in this environment")
        write(self.target / "pytest.ini", "[pytest]\n")
        write(self.target / "test_pass.py",
              "def test_truthy():\n    assert True\n")
        write(self.target / "test_fail.py",
              "def test_falsy():\n    assert False\n")
        r = run_tdd("run", str(self.target))
        # Normalized: any non-zero runner exit collapses to 1 (red), not 2.
        self.assertEqual(r.returncode, 1,
                         f"expected exit 1; stderr={r.stderr}; stdout={r.stdout}")

    def test_no_runner_exits_2(self):
        r = run_tdd("run", str(self.target))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no test runner detected", r.stderr)

    def test_missing_binary_exits_2(self):
        # Construct a tdd.py invocation where the *detected runner's binary* is
        # missing from PATH. Easiest reliable approach: set a vitest signal
        # (config file) and strip PATH so `npx` cannot resolve.
        write(self.target / "vitest.config.ts", "")
        env = os.environ.copy()
        env["PATH"] = "/nonexistent"
        result = subprocess.run(
            [sys.executable, str(TDD_PY), "run", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 2,
                         f"expected exit 2; stderr={result.stderr}")
        self.assertIn("not found", result.stderr.lower())


# -------------------- TargetedRunTests (058-01) --------------------


class TargetedRunTests(unittest.TestCase):
    """ACs for slice 058-01 — `tdd.py run --test <selector>`."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._tdd = _load_tdd()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pytest_targeted_passing_test_ignores_other_red_tests(self):
        try:
            import pytest  # noqa: F401
        except ImportError:
            self.skipTest("pytest not installed in this environment")
        write(self.target / "pytest.ini", "[pytest]\n")
        write(self.target / "test_sample.py",
              "def test_passes():\n    assert True\n\n"
              "def test_fails():\n    assert False\n")

        r = run_tdd("run", str(self.target), "--test", "test_sample.py::test_passes")

        self.assertEqual(r.returncode, 0,
                         f"expected targeted green; stderr={r.stderr}; stdout={r.stdout}")

    def test_pytest_targeted_failing_test_exits_1(self):
        try:
            import pytest  # noqa: F401
        except ImportError:
            self.skipTest("pytest not installed in this environment")
        write(self.target / "pytest.ini", "[pytest]\n")
        write(self.target / "test_sample.py",
              "def test_fails():\n    assert False\n")

        r = run_tdd("run", str(self.target), "--test", "test_sample.py::test_fails")

        self.assertEqual(r.returncode, 1,
                         f"expected targeted red; stderr={r.stderr}; stdout={r.stdout}")

    def test_pytest_missing_selector_exits_2_and_names_selector(self):
        try:
            import pytest  # noqa: F401
        except ImportError:
            self.skipTest("pytest not installed in this environment")
        write(self.target / "pytest.ini", "[pytest]\n")
        write(self.target / "test_sample.py",
              "def test_passes():\n    assert True\n")

        selector = "test_sample.py::test_missing"
        r = run_tdd("run", str(self.target), "--test", selector)

        self.assertEqual(r.returncode, 2,
                         f"missing selector must be env error; stderr={r.stderr}")
        self.assertIn(selector, r.stderr)
        self.assertIn("unresolved selector", r.stderr)

    def test_pytest_selector_builds_node_id_command(self):
        write(self.target / "pytest.ini", "[pytest]\n")
        with patch.object(self._tdd, "_is_module_importable", return_value=True):
            with patch.object(self._tdd, "_run_streaming") as mock_run:
                mock_run.return_value = (0, "")
                code = self._tdd.cmd_run(
                    self.target, None, test_selector="test_sample.py::test_passes")

        self.assertEqual(code, 0)
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv[-1], "test_sample.py::test_passes")

    def test_pytest_targeted_failure_text_does_not_look_unresolved(self):
        write(self.target / "pytest.ini", "[pytest]\n")
        with patch.object(self._tdd, "_is_module_importable", return_value=True):
            with patch.object(self._tdd, "_run_streaming") as mock_run:
                mock_run.return_value = (
                    1,
                    "AssertionError: no tests found for this input",
                )
                code = self._tdd.cmd_run(
                    self.target, None, test_selector="test_sample.py::test_fails")

        self.assertEqual(code, 1)

    def test_vitest_selector_maps_file_and_test_name(self):
        write(self.target / "vitest.config.ts", "")
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (0, "")
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.ts::does the thing")

        self.assertEqual(code, 0)
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv, [
            "npx", "vitest", "run", "tests/foo.test.ts", "-t", "does the thing",
        ])

    def test_jest_selector_maps_file_and_test_name(self):
        write(self.target / "jest.config.js", "")
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (0, "")
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.js::does the thing")

        self.assertEqual(code, 0)
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv, [
            "npx", "jest", "tests/foo.test.js", "-t", "does the thing",
        ])

    def test_js_no_matching_test_output_exits_2(self):
        write(self.target / "vitest.config.ts", "")
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (1, "No test found")
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.ts::missing")

        self.assertEqual(code, 2)

    def test_js_suite_load_failure_text_does_not_look_unresolved(self):
        write(self.target / "jest.config.js", "")
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (
                1,
                "Test suite failed to run\nReferenceError: broken is not defined",
            )
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.js::loads")

        self.assertEqual(code, 1)

    def test_js_targeted_failure_text_does_not_look_unresolved(self):
        write(self.target / "vitest.config.ts", "")
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (
                1,
                "AssertionError: no tests found for this input",
            )
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.ts::fails")

        self.assertEqual(code, 1)

    def test_indented_js_targeted_failure_text_does_not_look_unresolved(self):
        write(self.target / "vitest.config.ts", "")
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (
                1,
                "    No tests found for this input",
            )
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.ts::fails")

        self.assertEqual(code, 1)

    def test_without_test_selector_uses_existing_path_behavior(self):
        write(self.target / "vitest.config.ts", "")
        test_path = self.target / "tests"
        with patch.object(self._tdd.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            code = self._tdd.cmd_run(self.target, test_path)

        self.assertEqual(code, 0)
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv, ["npx", "vitest", "run", str(test_path)])


# -------------------- SkillSurfaceTests --------------------


class SkillSurfaceTests(unittest.TestCase):
    """AC #3 — SKILL.md has active frontmatter + trigger phrases + body refs."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def _frontmatter(self):
        m = re.match(r"^---\n(.*?)\n---\n", self.text, re.DOTALL)
        return m.group(1) if m else ""

    def test_frontmatter_active(self):
        # Active means: frontmatter exists AND does NOT contain
        # `disable-model-invocation: true`.
        fm = self._frontmatter()
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")
        self.assertNotIn("disable-model-invocation: true", fm)
        # Also has a name field.
        self.assertRegex(fm, r"(?m)^name:\s*tdd-loop\s*$")

    def test_description_has_trigger_phrases(self):
        # AC #3 enumerates these auto-trigger phrases. We normalize whitespace
        # before matching because the description is a YAML folded scalar
        # (`description: >`) — line wraps insert literal newlines into the raw
        # bytes, but the parsed value collapses them to single spaces. Match
        # against the parsed shape.
        phrases = [
            "write a test",
            "TDD this",
            "let me test-drive",
            "is my coverage complete",
            "run my tests",
            "are tests green",
            "implement",
        ]
        fm = self._frontmatter()
        normalized = " ".join(fm.lower().split())
        for phrase in phrases:
            self.assertIn(phrase.lower(), normalized,
                          f"description missing trigger phrase: {phrase!r}")

    def test_body_references_subcommands(self):
        # Body must mention `tdd.py detect` and `tdd.py run` so the agent knows
        # how to invoke the helper.
        self.assertIn("tdd.py detect", self.text)
        self.assertIn("tdd.py run", self.text)

    def test_body_references_implementer_agent(self):
        # AC #3 — "Relationship to the implementer subagent" section must
        # cite agents/implementer.md.
        self.assertIn("agents/implementer.md", self.text)

    def test_body_has_red_green_refactor_section(self):
        # AC #3 body sections: "The red-green-refactor loop".
        self.assertRegex(self.text, r"(?i)red[- ]green[- ]refactor")

    def test_body_has_when_not_to_use_section(self):
        # AC #3 — "When NOT to use" section.
        self.assertRegex(self.text, r"(?i)when not to use")


# -------------------- MissingModuleTests (006-04) --------------------


class MissingModuleTests(unittest.TestCase):
    """AC #1–5 for slice 006-04 — missing module normalizes to exit 2."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        # Write a pytest.ini so pytest is detected via filesystem signals.
        (self.target / "pytest.ini").write_text("[pytest]\n")
        self._tdd = _load_tdd()

    def tearDown(self):
        self.tmp.cleanup()

    def _run_cmd_run(self, importable: bool):
        """Helper: call cmd_run with _is_module_importable patched."""
        buf = []
        with patch.object(self._tdd, "_is_module_importable",
                          return_value=importable):
            with patch("sys.stderr") as mock_stderr:
                mock_stderr.write = lambda s: buf.append(s)
                # Also patch subprocess.run so we don't actually run pytest.
                with patch.object(self._tdd.subprocess, "run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    code = self._tdd.cmd_run(self.target, None)
        return code, "".join(buf)

    def test_missing_pytest_module_exits_2(self):
        # AC #1: pytest detected but module not importable → exit 2.
        code, _ = self._run_cmd_run(importable=False)
        self.assertEqual(code, 2)

    def test_missing_pytest_module_stderr_contains_not_installed(self):
        # AC #1: stderr must contain "not installed".
        _, stderr = self._run_cmd_run(importable=False)
        self.assertIn("not installed", stderr.lower())

    def test_existing_pytest_module_proceeds(self):
        # AC #2: when module IS importable, subprocess is called (not short-circuited).
        code, _ = self._run_cmd_run(importable=True)
        self.assertEqual(code, 0)

    def test_detect_unaffected_by_missing_module(self):
        # AC #4: detect still returns "pytest" regardless of module availability.
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "pytest")

    def test_vitest_no_preflight(self):
        # AC #3: vitest path unchanged — _is_module_importable NOT called for vitest.
        vitest_target = Path(self.tmp.name) / "js"
        vitest_target.mkdir()
        (vitest_target / "vitest.config.ts").write_text("")
        tdd = _load_tdd()
        calls = []

        def tracking_check(name):
            calls.append(name)
            return True

        with patch.object(tdd, "_is_module_importable", side_effect=tracking_check):
            with patch.object(tdd.subprocess, "run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                tdd.cmd_run(vitest_target, None)

        self.assertNotIn("vitest", calls, "vitest must not trigger a module pre-flight")


# -------------------- CustomCommandTests (006-05) --------------------


def _write(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class CustomCommandDetectTests(unittest.TestCase):
    """AC #1, #4 for slice 006-05 — detect returns 'custom' when override present."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_detect_custom_when_file_present(self):
        # AC #1: .jig/test-command present → detect prints "custom".
        _write(self.target / ".jig" / "test-command",
               "python3 -m unittest discover\n")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "custom")

    def test_detect_custom_takes_priority_over_pytest_signal(self):
        # AC #1: custom beats all other detection signals.
        _write(self.target / "pytest.ini", "[pytest]\n")
        _write(self.target / ".jig" / "test-command",
               "python3 -m unittest discover\n")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.stdout.strip(), "custom")

    def test_detect_falls_through_without_file(self):
        # AC #4: no .jig/test-command → normal detection (empty dir → exit 2).
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no test runner detected", r.stderr)

    def test_detect_falls_through_with_empty_file(self):
        # AC #3: empty file → falls through to normal detection (not treated as custom).
        _write(self.target / ".jig" / "test-command", "")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 2)

    def test_detect_falls_through_with_comment_only_file(self):
        # AC #3: comment-only file → falls through.
        _write(self.target / ".jig" / "test-command", "# just a comment\n")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 2)


class CustomCommandRunTests(unittest.TestCase):
    """AC #2, #3, #5 for slice 006-05 — run executes custom command."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._tdd = _load_tdd()

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_uses_custom_command_argv(self):
        # AC #2/#5: run calls subprocess with the custom command's argv.
        _write(self.target / ".jig" / "test-command",
               "python3 -m unittest discover\n")
        captured = []
        with patch.object(self._tdd.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            self._tdd.cmd_run(self.target, None)
            captured = mock_run.call_args[0][0]
        self.assertEqual(captured,
                         shlex.split("python3 -m unittest discover"))

    def test_run_custom_command_green_exits_0(self):
        # AC #2: custom command returns 0 → tdd.py exits 0.
        _write(self.target / ".jig" / "test-command",
               "python3 -m unittest discover\n")
        with patch.object(self._tdd.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            code = self._tdd.cmd_run(self.target, None)
        self.assertEqual(code, 0)

    def test_run_custom_command_red_exits_1(self):
        # AC #2: custom command returns non-zero → tdd.py exits 1.
        _write(self.target / ".jig" / "test-command",
               "python3 -m unittest discover\n")
        with patch.object(self._tdd.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            code = self._tdd.cmd_run(self.target, None)
        self.assertEqual(code, 1)

    def test_run_custom_command_missing_binary_exits_2(self):
        # AC #2: FileNotFoundError from subprocess → exit 2.
        _write(self.target / ".jig" / "test-command",
               "nonexistent-binary --run\n")
        with patch.object(self._tdd.subprocess, "run",
                          side_effect=FileNotFoundError):
            code = self._tdd.cmd_run(self.target, None)
        self.assertEqual(code, 2)

    def test_run_custom_command_oserror_exits_2(self):
        # AC #2: OSError (e.g. permission denied) from subprocess → exit 2.
        _write(self.target / ".jig" / "test-command",
               "some-command --run\n")
        with patch.object(self._tdd.subprocess, "run",
                          side_effect=OSError("Permission denied")):
            code = self._tdd.cmd_run(self.target, None)
        self.assertEqual(code, 2)

    def test_run_empty_command_file_exits_2(self):
        # AC #3: empty file → exit 2 with message.
        _write(self.target / ".jig" / "test-command", "")
        stderr_buf = []
        with patch("sys.stderr") as mock_err:
            mock_err.write = lambda s: stderr_buf.append(s)
            code = self._tdd.cmd_run(self.target, None)
        self.assertEqual(code, 2)
        self.assertIn(".jig/test-command", "".join(stderr_buf))

    def test_run_comment_only_file_exits_2(self):
        # AC #3: comment-only file → exit 2.
        _write(self.target / ".jig" / "test-command",
               "# run all tests\n# python3 -m pytest\n")
        stderr_buf = []
        with patch("sys.stderr") as mock_err:
            mock_err.write = lambda s: stderr_buf.append(s)
            code = self._tdd.cmd_run(self.target, None)
        self.assertEqual(code, 2)

    def test_run_ignores_comment_lines_in_file(self):
        # AC #3: comment lines are skipped; first non-comment line is the command.
        _write(self.target / ".jig" / "test-command",
               "# this is a comment\npython3 -m unittest discover\n")
        captured = []
        with patch.object(self._tdd.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            self._tdd.cmd_run(self.target, None)
            captured = mock_run.call_args[0][0]
        self.assertEqual(captured,
                         shlex.split("python3 -m unittest discover"))

    def test_run_normal_detection_when_no_file(self):
        # AC #4: no .jig/test-command → existing runner detection used.
        r = run_tdd("run", str(self.target))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no test runner detected", r.stderr)


if __name__ == "__main__":
    unittest.main()
