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
import shutil
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

    # ---- node built-in test runner signals ----

    def test_node_via_package_json_test_script(self):
        write(self.target / "package.json",
              json.dumps({"scripts": {"test": "node --test"}}))
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "node")

    def test_node_via_shallow_node_test_import(self):
        write(self.target / "test" / "sample.test.mjs",
              "import { test } from 'node:test';\n"
              "test('works', () => {});\n")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "node")

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

    def test_priority_vitest_over_node(self):
        write(self.target / "vitest.config.ts", "")
        write(self.target / "package.json",
              json.dumps({"scripts": {"test": "node --test"}}))
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "vitest")

    def test_priority_jest_over_node(self):
        write(self.target / "jest.config.js", "")
        write(self.target / "package.json",
              json.dumps({"scripts": {"test": "node --test"}}))
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "jest")

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

    def test_node_selector_maps_file_and_test_name(self):
        write(self.target / "package.json",
              json.dumps({"scripts": {"test": "node --test"}}))
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (0, "")
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.mjs::does the thing")

        self.assertEqual(code, 0)
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv, [
            "node", "--test", "--test-name-pattern", "does the thing",
            "tests/foo.test.mjs",
        ])

    def test_node_default_run_uses_builtin_discovery(self):
        write(self.target / "package.json",
              json.dumps({"scripts": {"test": "node --test"}}))
        with patch.object(self._tdd.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            code = self._tdd.cmd_run(self.target, None)

        self.assertEqual(code, 0)
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv, ["node", "--test"])

    def test_node_explicit_test_path_is_passed_to_runner(self):
        write(self.target / "package.json",
              json.dumps({"scripts": {"test": "node --test"}}))
        test_path = self.target / "test" / "sample.test.mjs"
        with patch.object(self._tdd.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            code = self._tdd.cmd_run(self.target, test_path)

        self.assertEqual(code, 0)
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv, ["node", "--test", str(test_path)])

    def test_js_no_matching_test_output_exits_2(self):
        write(self.target / "vitest.config.ts", "")
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (1, "No test found")
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.ts::missing")

        self.assertEqual(code, 2)

    def test_node_no_matching_test_output_exits_2(self):
        write(self.target / "package.json",
              json.dumps({"scripts": {"test": "node --test"}}))
        with patch.object(self._tdd, "_run_streaming") as mock_run:
            mock_run.return_value = (0, "TAP version 13\n1..0\n")
            code = self._tdd.cmd_run(
                self.target, None, test_selector="tests/foo.test.mjs::missing")

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


# ------------- Bug 021 — custom-command selector contract -------------


class Bug021CustomCommandSelectorContractTests(unittest.TestCase):
    """Bug 021: a custom .jig/test-command must never silently swallow a
    requested selector. Targeting is opt-in via a `{test}` placeholder token;
    without one, a targeted run is refused (exit 2, "could not target"), never
    silently widened to the whole suite. A targeted run whose command reports
    no matching tests is an unresolved selector (exit 2), not a red suite."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_recorder(self) -> None:
        """A stand-in test command that records its argv and exits 0."""
        (self.target / "recorder.py").write_text(
            "import json, sys\n"
            "from pathlib import Path\n"
            "Path('recorder.argv.json').write_text(json.dumps(sys.argv[1:]))\n"
        )

    def _recorded_argv(self) -> list:
        return json.loads((self.target / "recorder.argv.json").read_text())

    def test_selector_without_placeholder_is_refused_exit_2(self):
        # The load-bearing half of the bug: an untargetable command must not
        # run at all when a selector was requested — a whole-suite exit code
        # is not evidence about the named test.
        self._write_recorder()
        _write(self.target / ".jig" / "test-command", "python3 recorder.py\n")
        r = run_tdd("run", str(self.target), "--test", "pkg/test_x.py::Case")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("{test}", r.stderr)
        self.assertIn(".jig/test-command", r.stderr)
        self.assertFalse(
            (self.target / "recorder.argv.json").exists(),
            "the untargetable custom command must not be run at all",
        )

    def test_selector_substituted_at_placeholder(self):
        self._write_recorder()
        _write(self.target / ".jig" / "test-command",
               "python3 recorder.py {test}\n")
        r = run_tdd("run", str(self.target), "--test", "pkg/test_x.py::Case")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._recorded_argv(), ["pkg/test_x.py::Case"])

    def test_placeholder_dropped_when_no_selector(self):
        self._write_recorder()
        _write(self.target / ".jig" / "test-command",
               "python3 recorder.py {test}\n")
        r = run_tdd("run", str(self.target))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._recorded_argv(), [])

    def test_unresolved_selector_report_maps_to_exit_2(self):
        # Parity with the auto-detect runners' _selector_missed protection:
        # "no matching tests" from a targeted custom run is exit 2, not red.
        (self.target / "nomatch.py").write_text(
            "import sys\n"
            "print('no matching tests: ' + sys.argv[1])\n"
            "raise SystemExit(1)\n"
        )
        _write(self.target / ".jig" / "test-command",
               "python3 nomatch.py {test}\n")
        r = run_tdd("run", str(self.target), "--test", "ghost/test_g.py::Nope")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("unresolved selector", r.stderr)

    def test_red_targeted_run_still_exits_1(self):
        # A command that honors the selector and fails stays a plain red.
        (self.target / "red.py").write_text(
            "import sys\n"
            "print('ran ' + sys.argv[1])\n"
            "raise SystemExit(1)\n"
        )
        _write(self.target / ".jig" / "test-command", "python3 red.py {test}\n")
        r = run_tdd("run", str(self.target), "--test", "pkg/test_x.py::Case")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


# ------------- Spec 123-01 — custom-command exit contract (ADR-0068) -------------


class Spec123CustomCommandExitContractTests(unittest.TestCase):
    """ADR-0068 §2: a custom .jig/test-command follows tdd.py's own contract —
    0 green, 1 red (a test ran and failed), and every other status (2, a
    shell's 126/127, a runner code, a signal) "could not run": exit 2,
    never red."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        (self.target / "exiter.py").write_text(
            "import sys\n"
            "print('ran', sys.argv[2:])\n"
            "if len(sys.argv) > 3 and sys.argv[3] == 'nomatch':\n"
            "    print('no matching tests')\n"
            "raise SystemExit(int(sys.argv[1]))\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, code: int, *, selector: bool, extra: str = ""):
        _write(self.target / ".jig" / "test-command",
               f"{shlex.quote(sys.executable)} exiter.py {code} {{test}} {extra}\n")
        args = ["run", str(self.target)]
        if selector:
            args += ["--test", "pkg/test_x.py::Case"]
        return run_tdd(*args)

    def _last_stderr_line(self, r) -> str:
        return [ln for ln in r.stderr.splitlines() if ln.strip()][-1]

    def test_any_status_but_0_and_1_is_environment_error_in_both_branches(self):
        # AC1 (selector branch) + AC2 (whole-suite branch).
        for selector in (True, False):
            for code in (2, 3, 101, 127):
                with self.subTest(selector=selector, code=code):
                    r = self._run(code, selector=selector)
                    self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_message_names_the_contract_on_the_last_line(self):
        # AC3: one last stderr line — bug.py quotes exactly that line.
        for selector in (True, False):
            for code in (2, 127):
                with self.subTest(selector=selector, code=code):
                    line = self._last_stderr_line(
                        self._run(code, selector=selector))
                    self.assertIn(f"exited {code}", line)
                    self.assertIn(".jig/test-command", line)
                    self.assertIn("environment error", line)
                    self.assertIn("not a failing test", line)
                    self.assertIn("exit 1 only when a test ran and failed",
                                  line)
                    self.assertNotIn("||", line)  # no blanket `|| exit 1`
                    self.assertLessEqual(len(line), 300)

    def test_zero_and_one_are_unchanged(self):
        # AC4.
        for selector in (True, False):
            for code in (0, 1):
                with self.subTest(selector=selector, code=code):
                    r = self._run(code, selector=selector)
                    self.assertEqual(r.returncode, code, r.stdout + r.stderr)
                    self.assertNotIn("environment error", r.stderr)

    def test_death_by_signal_is_environment_error(self):
        # Edge case: a killed command (negative return code) is not red.
        (self.target / "killed.py").write_text(
            "import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n")
        for selector in (True, False):
            with self.subTest(selector=selector):
                _write(self.target / ".jig" / "test-command",
                       f"{shlex.quote(sys.executable)} killed.py {{test}}\n")
                args = ["run", str(self.target)]
                if selector:
                    args += ["--test", "pkg/test_x.py::Case"]
                r = run_tdd(*args)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_no_match_line_with_exit_1_is_still_unresolved_selector(self):
        # AC5: the bug 021 no-match mapping is unchanged.
        r = self._run(1, selector=True, extra="nomatch")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("unresolved selector", r.stderr)

    def test_exit_2_with_no_match_line_reports_the_contract_line(self):
        # Edge case: the exit code is checked first.
        r = self._run(2, selector=True, extra="nomatch")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("exited 2", self._last_stderr_line(r))

    def test_unparsable_command_is_environment_error(self):
        # An unbalanced quote must not surface as exit 1 (red).
        _write(self.target / ".jig" / "test-command", "sh -c 'oops {test}\n")
        for args in (["run", str(self.target)],
                     ["run", str(self.target), "--test", "a::b"]):
            r = run_tdd(*args)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn(".jig/test-command cannot be parsed", r.stderr)

    def test_undecodable_output_does_not_crash_a_targeted_run(self):
        (self.target / "bytes.py").write_text(
            "import sys\nsys.stdout.buffer.write(b'\\xff\\xfe bad\\n')\n"
            "raise SystemExit(1)\n")
        _write(self.target / ".jig" / "test-command",
               f"{shlex.quote(sys.executable)} bytes.py {{test}}\n")
        r = run_tdd("run", str(self.target), "--test", "a::b")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("tdd.py failed", r.stderr)

    def test_helper_crash_is_exit_2_not_red(self):
        tdd = _load_tdd()
        with patch.object(tdd, "cmd_run", side_effect=RuntimeError("boom")):
            self.assertEqual(tdd.main(["tdd.py", "run", str(self.target)]), 2)

    def test_skill_md_documents_the_contract(self):
        # AC9.
        text = SKILL_MD.read_text()
        self.assertIn("ADR-0068", text)
        self.assertIn("a test ran and failed", text)
        self.assertIn("could not run", text)


# ------------- Spec 123-02 — the no-runner dead end names the way out -------------


class Spec123NoRunnerHintTests(unittest.TestCase):
    """ADR-0068 §3: with no runner detected, detect/run say what to do. The
    guidance is the LAST stderr line and fits the 300 characters bug.py
    quotes untruncated."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _check(self, r):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        lines = [ln for ln in r.stderr.splitlines() if ln.strip()]
        self.assertTrue(lines[0].startswith("no test runner detected at "))
        last = lines[-1]
        self.assertLessEqual(len(last), 300, last)
        for needle in (".jig/test-command", "{test}", "0 = tests passed",
                       "1 = a test ran and failed", "could not run",
                       "build failure", "wrapper",
                       "test-command-recipes.md"):
            self.assertIn(needle, last)
        # An earlier line carries the resolved path of the recipes document.
        recipes = TDD_PY.parent / "test-command-recipes.md"
        self.assertTrue(any(str(recipes) in ln for ln in lines[:-1]), lines)
        self.assertTrue(recipes.is_file())

    def test_detect_names_the_way_out(self):
        self._check(run_tdd("detect", str(self.target)))

    def test_run_names_the_way_out_with_and_without_selector(self):
        self._check(run_tdd("run", str(self.target)))
        self._check(run_tdd("run", str(self.target), "--test", "a/b.kt::c"))

    def test_hint_is_not_printed_when_a_runner_is_detected(self):
        _write(self.target / ".jig" / "test-command", "true\n")
        r = run_tdd("detect", str(self.target))
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("test-command-recipes.md", r.stderr)


# ------------- Spec 123-02 — the Gradle recipe's wrapper, against a stub -------------

RECIPES_MD = REPO_ROOT / "skills" / "tdd-loop" / "test-command-recipes.md"

_STUB_GRADLEW = r"""#!/bin/sh
# Stub gradlew: records its argv, optionally writes a JUnit XML report.
printf '%s\n' "$@" > gradlew.args
dir="${JIG_GRADLE_RESULTS:-build/test-results/test}"
counts='tests="1" skipped="0" failures="0" errors="0"'
body='<testcase name="a" classname="p.C"/>'
case "${STUB_REPORT:-none}" in
  pass)  ;;
  noisy) out='<failure message="x"> <testsuite tests="9" failures="3">'
         body="$body<system-out><![CDATA[$out]]></system-out>" ;;
  fail)  counts='tests="1" skipped="0" failures="1" errors="0"'
         body='<testcase name="a" classname="p.C"><failure message="x">boom</failure></testcase>' ;;
  error) counts='tests="1" skipped="0" failures="0" errors="1"'
         body='<testcase name="a" classname="p.C"><error message="x">boom</error></testcase>' ;;
  empty) counts='tests="0" skipped="0" failures="0" errors="0"'; body='' ;;
  none)  exit "${STUB_EXIT:-0}" ;;
esac
mkdir -p "$dir"
printf '<?xml version="1.0"?>\n<testsuite name="p.C" %s time="0.1">\n%s\n</testsuite>\n' \
  "$counts" "$body" > "$dir/TEST-p.C.xml"
exit "${STUB_EXIT:-0}"
"""


def _recipe_script() -> str:
    text = RECIPES_MD.read_text()
    m = re.search(r"<!-- recipe:gradle-wrapper -->\n```sh\n(.*?)\n```", text,
                  re.DOTALL)
    assert m, "gradle wrapper block not found in the recipes document"
    return m.group(1) + "\n"


@unittest.skipUnless(shutil.which("sh"), "needs sh")
class Spec123GradleRecipeTests(unittest.TestCase):
    """Slice 123-02 AC6: the wrapper printed in test-command-recipes.md is
    extracted and run against a stub `gradlew`. This checks the script's own
    logic (exit mapping, report reading, selector mapping) — not Gradle."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self.tmp.name)
        (self.proj / "wrapper.sh").write_text(_recipe_script())
        gradlew = self.proj / "gradlew"
        gradlew.write_text(_STUB_GRADLEW)
        gradlew.chmod(0o755)
        self.results = self.proj / "build" / "test-results" / "test"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args, report="none", stub_exit=0):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("JIG_GRADLE", "JIG_GRADLEW", "STUB_"))}
        env.update(STUB_REPORT=report, STUB_EXIT=str(stub_exit))
        return subprocess.run(["sh", "wrapper.sh", *args], cwd=self.proj,
                              env=env, capture_output=True, text=True)

    def _args(self):
        return (self.proj / "gradlew.args").read_text().split()

    def test_tests_pass_is_0(self):
        self.assertEqual(self._run(report="pass").returncode, 0)

    def test_failure_text_in_captured_output_is_not_red(self):
        # A passing test that PRINTS `<failure ...>` must stay green: the
        # verdict comes from the <testsuite> header counts, not the body.
        r = self._run(report="noisy")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_failure_and_error_reports_are_1(self):
        for report in ("fail", "error"):
            with self.subTest(report=report):
                r = self._run(report=report, stub_exit=1)
                self.assertEqual(r.returncode, 1, r.stderr)

    def test_build_failure_with_no_report_is_2(self):
        r = self._run(report="none", stub_exit=1)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no JUnit report", r.stderr)

    def test_gradle_failure_with_clean_reports_is_2(self):
        r = self._run(report="pass", stub_exit=1)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no test failed", r.stderr)

    def test_exit_0_with_no_report_is_2(self):
        # The task was skipped (up to date) or filtered to nothing.
        self.assertEqual(self._run(report="none", stub_exit=0).returncode, 2)

    def test_exit_0_with_no_test_case_is_2(self):
        r = self._run(report="empty", stub_exit=0)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no test ran", r.stderr)

    def test_selector_is_mapped_to_tests_filter(self):
        self._run("pkg.Class::method", report="pass")
        self.assertEqual(self._args(), ["test", "--tests", "pkg.Class.method"])
        self._run(report="pass")
        self.assertEqual(self._args(), ["test"])

    def test_stale_failing_report_is_deleted_before_the_run(self):
        self.results.mkdir(parents=True)
        (self.results / "TEST-old.xml").write_text(
            '<testsuite name="o" tests="1" failures="1" errors="0">'
            '<testcase name="o"><failure/></testcase></testsuite>')
        # A passing run must not be turned red by the earlier report...
        self.assertEqual(self._run(report="pass").returncode, 0)
        self.assertFalse((self.results / "TEST-old.xml").exists())
        # ...and a run that writes nothing must not be vouched for by it.
        (self.results / "TEST-old.xml").write_text(
            '<testsuite name="o" tests="1" failures="0" errors="0">'
            '<testcase name="o"/></testsuite>')
        self.assertEqual(self._run(report="none").returncode, 2)

    def test_missing_gradlew_is_2(self):
        (self.proj / "gradlew").unlink()
        r = self._run()
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found", r.stderr)

    def test_wrapper_under_tdd_py_end_to_end(self):
        # The recipe wired through .jig/test-command and the real tdd.py.
        _write(self.proj / ".jig" / "test-command", "sh wrapper.sh {test}\n")
        for report, stub_exit, want in (("pass", 0, 0), ("fail", 1, 1),
                                        ("none", 1, 2)):
            with self.subTest(report=report):
                env = {k: v for k, v in os.environ.items()
                       if not k.startswith(("JIG_GRADLE", "STUB_"))}
                env.update(STUB_REPORT=report, STUB_EXIT=str(stub_exit))
                r = subprocess.run(
                    [sys.executable, str(TDD_PY), "run", str(self.proj),
                     "--test", "pkg.Class::method"],
                    capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, want, r.stdout + r.stderr)

    def test_skill_md_states_the_closed_list_policy(self):
        # AC4.
        text = SKILL_MD.read_text()
        self.assertIn("The built-in list is closed", text)
        self.assertIn("does not add an adapter per test framework", text)
        self.assertIn("(test-command-recipes.md)", text)
        # The old wording listed these runners as deferred detection work.
        self.assertNotRegex(text, r"(?s)Out of scope[^\n]*\n?[^\n]*rspec")
        self.assertIn("is not deferred work", text)

    def test_document_states_the_limits(self):
        text = RECIPES_MD.read_text()
        for needle in ("ADR-0068", "not a catalogue",
                       "has not run this against real Gradle",
                       "instrumented tests", "out of scope for jig",
                       "does not ship or run it", ":app:testDebugUnitTest",
                       "|| exit 1"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
