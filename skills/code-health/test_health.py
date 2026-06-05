"""
AC verification tests for slice 060-01 — Python lint, detect-and-drive.

Run from the repo root:
    python3 scripts/run_tests.py
or
    python3 -m unittest discover -s skills/code-health -p 'test_*.py'

Tests are hermetic — they do NOT depend on ruff actually being installed.
The subprocess + tool-resolution boundary is mocked (mirrors the mocking
style in skills/tdd-loop/test_tdd.py).
"""

import importlib.util
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTH_PY = REPO_ROOT / "skills" / "code-health" / "health.py"


def run_health(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    """Invoke health.py as a subprocess. `cwd` lets tests run against a tmp dir."""
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, str(HEALTH_PY), *args],
        capture_output=True, text=True, env=env,
        cwd=str(cwd) if cwd else None,
    )


def _load_health():
    """Load health.py as a module for direct-call tests with mocking."""
    spec = importlib.util.spec_from_file_location("health", HEALTH_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# A representative `ruff check --output-format=json` payload (two findings,
# two distinct rule codes). Used by the findings tests so the summary parsing
# is exercised against ruff's real JSON shape.
RUFF_JSON_TWO_FINDINGS = (
    '[{"code": "F401", "filename": "a.py", "location": {"row": 1, "column": 1}},'
    ' {"code": "E501", "filename": "b.py", "location": {"row": 2, "column": 1}}]'
)


# -------------------- ResolverTests --------------------


class ResolverTests(unittest.TestCase):
    """AC #1 — ruff resolves on PATH or via an ephemeral runner; the argv is
    built accordingly. AC #4 — a .jig/lint-command override wins."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolve_ruff_on_path(self):
        # ruff on PATH → use the `ruff` binary directly.
        def fake_which(name):
            return "/usr/bin/ruff" if name == "ruff" else None
        with patch.object(self._h.shutil, "which", side_effect=fake_which):
            argv = self._h.resolve_lint_command(self.target)
        self.assertIsNotNone(argv)
        self.assertEqual(argv[0], "ruff")

    def test_resolve_ruff_via_uvx(self):
        # ruff NOT on PATH but uvx is → `uvx ruff ...`.
        def fake_which(name):
            return "/usr/bin/uvx" if name == "uvx" else None
        with patch.object(self._h.shutil, "which", side_effect=fake_which):
            argv = self._h.resolve_lint_command(self.target)
        self.assertIsNotNone(argv)
        self.assertEqual(argv[:2], ["uvx", "ruff"])

    def test_resolve_ruff_via_pipx(self):
        # neither ruff nor uvx, but pipx is → `pipx run ruff ...`.
        def fake_which(name):
            return "/usr/bin/pipx" if name == "pipx" else None
        with patch.object(self._h.shutil, "which", side_effect=fake_which):
            argv = self._h.resolve_lint_command(self.target)
        self.assertIsNotNone(argv)
        self.assertEqual(argv[:3], ["pipx", "run", "ruff"])

    def test_resolve_prefers_path_over_ephemeral(self):
        # ruff AND uvx both present → prefer the PATH binary.
        with patch.object(self._h.shutil, "which", return_value="/usr/bin/x"):
            argv = self._h.resolve_lint_command(self.target)
        self.assertEqual(argv[0], "ruff")

    def test_resolve_none_when_nothing_available(self):
        # AC #3 — nothing on PATH → resolver returns None.
        with patch.object(self._h.shutil, "which", return_value=None):
            argv = self._h.resolve_lint_command(self.target)
        self.assertIsNone(argv)

    def test_resolve_override_wins(self):
        # AC #4 — .jig/lint-command overrides auto-detection, honored verbatim.
        _write(self.target / ".jig" / "lint-command", "my-linter --check src\n")
        # Even with ruff on PATH, the override must win.
        with patch.object(self._h.shutil, "which", return_value="/usr/bin/ruff"):
            argv = self._h.resolve_lint_command(self.target)
        self.assertEqual(argv, shlex.split("my-linter --check src"))


# -------------------- CheckExitCodeTests --------------------


class CheckExitCodeTests(unittest.TestCase):
    """AC #1 / AC #2 — `check` exits 0 clean / 1 findings / 2 no-runner."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_exits_0(self):
        # AC #1/#2 — ruff runs, returncode 0, empty JSON → exit 0.
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check"]):
            with patch.object(self._h.subprocess, "run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]",
                                                  stderr="")
                code = self._h.cmd_check(self.target)
        self.assertEqual(code, 0)

    def test_findings_exits_1(self):
        # AC #1/#2 — ruff returncode 1 with findings JSON → exit 1.
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check"]):
            with patch.object(self._h.subprocess, "run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stdout=RUFF_JSON_TWO_FINDINGS, stderr="")
                code = self._h.cmd_check(self.target)
        self.assertEqual(code, 1)

    def test_no_runner_exits_2(self):
        # AC #2/#3 — resolver returns None → exit 2.
        with patch.object(self._h, "resolve_lint_command", return_value=None):
            code = self._h.cmd_check(self.target)
        self.assertEqual(code, 2)

    def test_binary_missing_exits_2(self):
        # AC #2 — FileNotFoundError from subprocess (resolved tool vanished)
        # → exit 2, distinct from "ran and found issues" (1).
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check"]):
            with patch.object(self._h.subprocess, "run",
                              side_effect=FileNotFoundError):
                code = self._h.cmd_check(self.target)
        self.assertEqual(code, 2)

    def test_oserror_exits_2(self):
        # AC #2 — OSError from subprocess → exit 2 (env error), not a finding.
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check"]):
            with patch.object(self._h.subprocess, "run",
                              side_effect=OSError("boom")):
                code = self._h.cmd_check(self.target)
        self.assertEqual(code, 2)


# -------------------- SummaryTests --------------------


class SummaryTests(unittest.TestCase):
    """AC #1 — findings count + top rule codes appear on stdout (tight
    summary, not the raw ruff dump per spec 057)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_findings_summary_on_stdout(self):
        stdout_buf = []
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check"]):
            with patch.object(self._h.subprocess, "run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stdout=RUFF_JSON_TWO_FINDINGS, stderr="")
                with patch("sys.stdout") as mock_out:
                    mock_out.write = lambda s: stdout_buf.append(s)
                    self._h.cmd_check(self.target)
        out = "".join(stdout_buf)
        self.assertIn("2", out, "findings count must appear on stdout")
        self.assertIn("F401", out, "top rule codes must appear on stdout")
        self.assertIn("E501", out)

    def test_clean_summary_on_stdout(self):
        stdout_buf = []
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check"]):
            with patch.object(self._h.subprocess, "run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]",
                                                  stderr="")
                with patch("sys.stdout") as mock_out:
                    mock_out.write = lambda s: stdout_buf.append(s)
                    self._h.cmd_check(self.target)
        out = "".join(stdout_buf).lower()
        self.assertIn("clean", out, "a clean run must say so on stdout")

    def test_summary_is_tight_not_raw_dump(self):
        # spec 057 — the raw ruff JSON dump must NOT be echoed wholesale.
        stdout_buf = []
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check"]):
            with patch.object(self._h.subprocess, "run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stdout=RUFF_JSON_TWO_FINDINGS, stderr="")
                with patch("sys.stdout") as mock_out:
                    mock_out.write = lambda s: stdout_buf.append(s)
                    self._h.cmd_check(self.target)
        out = "".join(stdout_buf)
        self.assertNotIn('"location"', out,
                         "summary must not echo the raw ruff JSON dump")


# -------------------- DegradationTests --------------------


class DegradationTests(unittest.TestCase):
    """AC #3 — no linter + no ephemeral runner → exit 2 + one-line
    recommendation, never a stack trace."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_cli_no_runner_recommendation(self):
        env = os.environ.copy()
        env["PATH"] = "/nonexistent"  # nothing resolvable
        result = subprocess.run(
            [sys.executable, str(HEALTH_PY), "check", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        combined = (result.stdout + result.stderr).lower()
        self.assertIn("no python linter found", combined)
        # Never a stack trace.
        self.assertNotIn("traceback", combined)

    def test_recommendation_mentions_ruff_or_pipx(self):
        env = os.environ.copy()
        env["PATH"] = "/nonexistent"
        result = subprocess.run(
            [sys.executable, str(HEALTH_PY), "check", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        combined = (result.stdout + result.stderr).lower()
        self.assertTrue("ruff" in combined or "pipx" in combined,
                        "recommendation should name ruff / pipx")


# -------------------- OverrideRunTests --------------------


class OverrideRunTests(unittest.TestCase):
    """AC #4 — `.jig/lint-command` override is honored verbatim through to
    the subprocess, mirroring tdd.py's .jig/test-command semantics."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_override_argv_used_verbatim(self):
        _write(self.target / ".jig" / "lint-command",
               "my-linter --check src\n")
        captured = []
        with patch.object(self._h.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            self._h.cmd_check(self.target)
            captured = mock_run.call_args[0][0]
        self.assertEqual(captured, shlex.split("my-linter --check src"))

    def test_override_skips_comment_lines(self):
        _write(self.target / ".jig" / "lint-command",
               "# the linter\nmy-linter --check\n")
        captured = []
        with patch.object(self._h.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            self._h.cmd_check(self.target)
            captured = mock_run.call_args[0][0]
        self.assertEqual(captured, shlex.split("my-linter --check"))

    def test_override_nonzero_exits_1(self):
        # An override that reports findings (non-zero) → exit 1.
        _write(self.target / ".jig" / "lint-command", "my-linter\n")
        with patch.object(self._h.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            code = self._h.cmd_check(self.target)
        self.assertEqual(code, 1)

    def test_empty_override_falls_through(self):
        # AC #4 — an empty / comment-only override does NOT win; resolution
        # falls through to ruff detection (here: nothing → None → exit 2).
        _write(self.target / ".jig" / "lint-command", "# only a comment\n")
        with patch.object(self._h.shutil, "which", return_value=None):
            argv = self._h.resolve_lint_command(self.target)
        self.assertIsNone(argv)


# -------------------- DetectTests --------------------


class DetectTests(unittest.TestCase):
    """`detect` subcommand mirrors tdd.py detect — prints the linter name,
    exit 2 on miss."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_detect_prints_ruff_when_on_path(self):
        h = _load_health()
        with patch.object(h.shutil, "which",
                          side_effect=lambda n: "/x" if n == "ruff" else None):
            stdout_buf = []
            with patch("sys.stdout") as mock_out:
                mock_out.write = lambda s: stdout_buf.append(s)
                code = h.cmd_detect(self.target)
        self.assertEqual(code, 0)
        self.assertIn("ruff", "".join(stdout_buf))

    def test_detect_exit_2_when_nothing(self):
        env = os.environ.copy()
        env["PATH"] = "/nonexistent"
        result = subprocess.run(
            [sys.executable, str(HEALTH_PY), "detect", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 2)


# -------------------- CliBasicsTests --------------------


class CliBasicsTests(unittest.TestCase):
    """Argparse + bad-target handling mirror tdd.py."""

    def test_nonexistent_target_exits_2(self):
        result = run_health("check", "/no/such/dir/xyz")
        self.assertEqual(result.returncode, 2)

    def test_no_subcommand_exits_2(self):
        result = run_health()
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
