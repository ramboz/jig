"""
AC verification tests for slice 006-01 (tdd-helper).

Run from the repo root:
    python3 skills/tdd-loop/test_tdd.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
