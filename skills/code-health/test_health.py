"""
AC verification tests for the code-health helper (spec 060) — spanning
slice 060-01 (Python lint), 060-03 (table-driven ecosystems + complexity),
and 060-04 (duplication: native-first / `npx jscpd` fallback).

Run from the repo root:
    python3 scripts/run_tests.py
or
    python3 -m unittest discover -s skills/code-health -p 'test_*.py'

Tests are hermetic — they do NOT depend on ruff actually being installed.
The subprocess + tool-resolution boundary is mocked (mirrors the mocking
style in skills/tdd-loop/test_tdd.py).
"""

import glob
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def _seed_python(target: Path) -> Path:
    """Seed a Python ecosystem marker so detection fires (slice 060-03 —
    ecosystem detection is now a real gate per AC4; a bare empty dir is
    legitimately 'unknown', so the 060-01 Python tests now plant a marker)."""
    return _write(target / "pyproject.toml", "[project]\nname = \"x\"\n")


def _seed_node(target: Path) -> Path:
    """Seed a Node ecosystem marker (package.json) so Node detection fires."""
    return _write(target / "package.json", '{"name": "x"}\n')


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
        _seed_python(self.target)  # ecosystem marker so detection fires
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
        _seed_python(self.target)  # single Python ecosystem, no resolvable linter

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
        _seed_python(self.target)  # ecosystem marker so detection fires

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


# A representative `eslint --format json` payload: two files, three messages
# total across two distinct ruleIds.
ESLINT_JSON_THREE_MSGS = json.dumps([
    {
        "filePath": "/x/a.js",
        "messages": [
            {"ruleId": "no-unused-vars", "severity": 2, "message": "x"},
            {"ruleId": "semi", "severity": 1, "message": "y"},
        ],
        "errorCount": 1,
        "warningCount": 1,
    },
    {
        "filePath": "/x/b.js",
        "messages": [
            {"ruleId": "no-unused-vars", "severity": 2, "message": "z"},
        ],
        "errorCount": 1,
        "warningCount": 0,
    },
])

ESLINT_JSON_CLEAN = json.dumps([
    {"filePath": "/x/a.js", "messages": [], "errorCount": 0, "warningCount": 0},
])

# A ruff complexity-probe payload (one function over the C901 threshold).
RUFF_COMPLEXITY_JSON = (
    '[{"code": "C901", "filename": "a.py", "location": {"row": 5, "column": 1}}]'
)


# -------------------- TableExtensibilityTests --------------------


class TableExtensibilityTests(unittest.TestCase):
    """AC #1 — ecosystems live in a data structure, iterated; adding one is a
    table entry, not a control-flow fork."""

    def setUp(self):
        self._h = _load_health()

    def test_ecosystems_are_a_table(self):
        names = {eco.name for eco in self._h.ECOSYSTEMS}
        self.assertIn("python", names)
        self.assertIn("node", names)

    def test_each_ecosystem_has_required_fields(self):
        for eco in self._h.ECOSYSTEMS:
            self.assertTrue(callable(eco.detect))
            self.assertTrue(callable(eco.resolve_primary))
            self.assertTrue(callable(eco.summarize_primary))
            self.assertTrue(eco.no_linter_msg)
            self.assertIsInstance(eco.advisory_probes, list)


# -------------------- NodeDetectionTests --------------------


class NodeDetectionTests(unittest.TestCase):
    """AC #1 / AC #2 — package.json selects the Node ecosystem; eslint
    resolves on PATH and via npx."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        _seed_node(self.target)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_node_marker_selects_node_ecosystem(self):
        matches = self._h._detect_ecosystems(self.target)
        names = [eco.name for eco in matches]
        self.assertEqual(names, ["node"])

    def test_eslint_resolves_on_path(self):
        def fake_which(name):
            return "/usr/bin/eslint" if name == "eslint" else None
        with patch.object(self._h.shutil, "which", side_effect=fake_which):
            argv = self._h.resolve_lint_command(self.target)
        self.assertIsNotNone(argv)
        self.assertEqual(argv[0], "eslint")
        self.assertIn("--format", argv)
        self.assertIn("json", argv)

    def test_eslint_resolves_via_npx(self):
        def fake_which(name):
            return "/usr/bin/npx" if name == "npx" else None
        with patch.object(self._h.shutil, "which", side_effect=fake_which):
            argv = self._h.resolve_lint_command(self.target)
        self.assertIsNotNone(argv)
        self.assertEqual(argv[:2], ["npx", "eslint"])

    def test_node_no_linter_degrades_exit_2(self):
        with patch.object(self._h.shutil, "which", return_value=None):
            code = self._h.cmd_check(self.target)
        self.assertEqual(code, 2)


# -------------------- EslintSummaryTests --------------------


class EslintSummaryTests(unittest.TestCase):
    """AC #2 — eslint JSON parsed into count (total messages) + top ruleIds;
    exit 1 on findings, 0 on clean."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        _seed_node(self.target)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_summarize_eslint_counts_messages_and_top_rules(self):
        count, top = self._h._summarize_eslint(ESLINT_JSON_THREE_MSGS)
        self.assertEqual(count, 3)
        self.assertEqual(top[0], "no-unused-vars")  # most common ruleId
        self.assertIn("semi", top)

    def test_eslint_findings_exit_1_with_summary(self):
        stdout_buf = []
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["eslint", "--format", "json", "."]):
            with patch.object(self._h, "_run_advisory_probes", return_value=[]):
                with patch.object(self._h.subprocess, "run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=1, stdout=ESLINT_JSON_THREE_MSGS, stderr="")
                    with patch("sys.stdout") as mock_out:
                        mock_out.write = lambda s: stdout_buf.append(s)
                        code = self._h.cmd_check(self.target)
        self.assertEqual(code, 1)
        out = "".join(stdout_buf)
        self.assertIn("3", out)
        self.assertIn("no-unused-vars", out)

    def test_eslint_clean_exit_0(self):
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["eslint", "--format", "json", "."]):
            with patch.object(self._h, "_run_advisory_probes", return_value=[]):
                with patch.object(self._h.subprocess, "run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout=ESLINT_JSON_CLEAN, stderr="")
                    code = self._h.cmd_check(self.target)
        self.assertEqual(code, 0)


# -------------------- PrettierAdvisoryTests --------------------


class PrettierAdvisoryTests(unittest.TestCase):
    """AC #2 / AC #3 — prettier is an advisory probe: its signal appears in
    the summary but does NOT flip a clean eslint run's exit code."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        _seed_node(self.target)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_prettier_signal_does_not_flip_clean_exit(self):
        # eslint clean (rc 0) but prettier reports files needing formatting
        # (rc 1). Exit code must stay 0; prettier line appears in the summary.
        stdout_buf = []

        def fake_run(argv, *a, **k):
            if argv[0] == "eslint" or "eslint" in argv:
                return MagicMock(returncode=0, stdout=ESLINT_JSON_CLEAN, stderr="")
            # prettier --check: non-zero + a file path on stdout
            return MagicMock(returncode=1, stdout="src/a.js\n", stderr="")

        with patch.object(self._h, "resolve_lint_command",
                          return_value=["eslint", "--format", "json", "."]):
            with patch.object(self._h.subprocess, "run", side_effect=fake_run):
                with patch("sys.stdout") as mock_out:
                    mock_out.write = lambda s: stdout_buf.append(s)
                    code = self._h.cmd_check(self.target)
        self.assertEqual(code, 0, "prettier (advisory) must not flip the exit code")
        out = "".join(stdout_buf).lower()
        self.assertIn("prettier", out, "prettier signal must appear in the summary")

    def test_prettier_clean_reports_nothing(self):
        line = self._h._summarize_prettier_probe(0, "", "")
        self.assertIsNone(line)


# -------------------- ComplexityAdvisoryTests --------------------


class ComplexityAdvisoryTests(unittest.TestCase):
    """AC #3 — Python complexity is an advisory probe: signal appears in the
    summary, doesn't change the exit code, best-effort failure swallowed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        _seed_python(self.target)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_complexity_signal_in_summary_clean_primary(self):
        # ruff primary clean (rc 0); complexity probe reports one function.
        stdout_buf = []

        def fake_run(argv, *a, **k):
            if "--select" in argv:  # the complexity probe
                return MagicMock(returncode=1, stdout=RUFF_COMPLEXITY_JSON, stderr="")
            return MagicMock(returncode=0, stdout="[]", stderr="")

        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check", "--output-format=json", "."]):
            with patch.object(self._h.shutil, "which", return_value="/usr/bin/ruff"):
                with patch.object(self._h.subprocess, "run", side_effect=fake_run):
                    with patch("sys.stdout") as mock_out:
                        mock_out.write = lambda s: stdout_buf.append(s)
                        code = self._h.cmd_check(self.target)
        self.assertEqual(code, 0, "complexity (advisory) must not flip the exit code")
        out = "".join(stdout_buf).lower()
        self.assertIn("complexity", out)
        self.assertIn("c901", out)

    def test_complexity_probe_best_effort_swallows_failure(self):
        # The complexity probe raises on start; the run must not crash and
        # must report nothing for complexity.
        stdout_buf = []

        def fake_run(argv, *a, **k):
            if "--select" in argv:
                raise FileNotFoundError("ruff vanished mid-run")
            return MagicMock(returncode=0, stdout="[]", stderr="")

        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check", "--output-format=json", "."]):
            with patch.object(self._h.shutil, "which", return_value="/usr/bin/ruff"):
                with patch.object(self._h.subprocess, "run", side_effect=fake_run):
                    with patch("sys.stdout") as mock_out:
                        mock_out.write = lambda s: stdout_buf.append(s)
                        code = self._h.cmd_check(self.target)
        self.assertEqual(code, 0)
        out = "".join(stdout_buf).lower()
        self.assertNotIn("complexity", out)

    def test_complexity_probe_unparseable_reports_nothing(self):
        line = self._h._summarize_complexity_probe(1, "not json at all", "")
        self.assertIsNone(line)


# -------------------- MixedAndUnknownTests --------------------


class MixedAndUnknownTests(unittest.TestCase):
    """AC #4 — mixed (both markers) and unknown (no markers, no override)
    degrade to exit 2 + a recommendation; never a traceback."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_mixed_ecosystems_exit_2(self):
        _seed_python(self.target)
        _seed_node(self.target)
        with patch.object(self._h.shutil, "which", return_value="/usr/bin/x"):
            code = self._h.cmd_check(self.target)
        self.assertEqual(code, 2)

    def test_mixed_recommendation_names_both_and_override(self):
        _seed_python(self.target)
        _seed_node(self.target)
        msg = self._h._degradation_message(self.target).lower()
        self.assertIn("python", msg)
        self.assertIn("node", msg)
        self.assertIn(".jig/lint-command", msg)

    def test_unknown_ecosystem_exit_2(self):
        # No markers, no override → exit 2 + a recommendation.
        with patch.object(self._h.shutil, "which", return_value="/usr/bin/x"):
            code = self._h.cmd_check(self.target)
        self.assertEqual(code, 2)

    def test_unknown_recommendation_mentions_ecosystem_and_override(self):
        msg = self._h._degradation_message(self.target).lower()
        self.assertIn("ecosystem", msg)
        self.assertIn(".jig/lint-command", msg)

    def test_mixed_no_traceback_via_cli(self):
        _seed_python(self.target)
        _seed_node(self.target)
        result = run_health("check", str(self.target))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("traceback", (result.stdout + result.stderr).lower())

    def test_override_wins_over_mixed(self):
        # Even with both markers, a .jig/lint-command override bypasses
        # detection entirely (preserves 060-01 semantics).
        _seed_python(self.target)
        _seed_node(self.target)
        _write(self.target / ".jig" / "lint-command", "my-linter src\n")
        argv = self._h.resolve_lint_command(self.target)
        self.assertEqual(argv, shlex.split("my-linter src"))


# A representative `jscpd --reporters json` report (one clone, 50%
# duplicated across two files). Mirrors the real jscpd-report.json shape
# verified against `npx jscpd`: statistics.total.{percentage,clones} +
# duplicates[].{firstFile,secondFile}.{name,startLoc.line}.
JSCPD_REPORT_ONE_CLONE = json.dumps({
    "statistics": {
        "total": {
            "lines": 26,
            "clones": 1,
            "duplicatedLines": 13,
            "percentage": 50,
        },
    },
    "duplicates": [
        {
            "format": "javascript",
            "lines": 14,
            "firstFile": {"name": "src/a.js", "startLoc": {"line": 1}},
            "secondFile": {"name": "src/b.js", "startLoc": {"line": 1}},
        },
    ],
})

# A jscpd report with no clones (clean) — percentage 0, empty duplicates.
JSCPD_REPORT_CLEAN = json.dumps({
    "statistics": {"total": {"clones": 0, "percentage": 0}},
    "duplicates": [],
})


# -------------------- DuplicationResolverTests --------------------


class DuplicationResolverTests(unittest.TestCase):
    """AC1/AC2 — the duplication resolver's documented order: native (none
    wired yet — empty structural branch), then `npx jscpd` when npx is on
    PATH, else None (→ the skip line)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolves_npx_jscpd_when_npx_present(self):
        # AC2 — npx on PATH (+ a runner-provided workdir) → `npx jscpd ...`
        # writing its report into that workdir via --output.
        workdir = self.target / "wd"
        workdir.mkdir()

        def fake_which(name):
            return "/usr/bin/npx" if name == "npx" else None
        with patch.object(self._h.shutil, "which", side_effect=fake_which):
            argv = self._h._resolve_duplication(self.target, workdir)
        self.assertIsNotNone(argv)
        self.assertEqual(argv[:2], ["npx", "jscpd"])
        self.assertIn("--output", argv)
        self.assertIn(str(workdir), argv)

    def test_resolves_none_when_no_npx(self):
        # AC3 — no native tool, no npx → None (triggers the skip line).
        # NOTE: there is intentionally NO native-duplication tool wired yet
        # (see _resolve_duplication's native extension point); we do NOT fake
        # one here — the native branch is currently empty by design.
        with patch.object(self._h.shutil, "which", return_value=None):
            argv = self._h._resolve_duplication(self.target, self.target)
        self.assertIsNone(argv)

    def test_resolves_none_when_no_workdir(self):
        # Defensive: even with npx present, no workdir → None (the runner
        # always supplies one for this probe, but the resolver guards).
        with patch.object(self._h.shutil, "which", return_value="/usr/bin/npx"):
            argv = self._h._resolve_duplication(self.target, None)
        self.assertIsNone(argv)


# -------------------- JscpdParsingTests --------------------


class JscpdParsingTests(unittest.TestCase):
    """AC4 — parse the jscpd JSON report into a tight percentage + top
    file:line clones; malformed input degrades gracefully (no crash)."""

    def setUp(self):
        self._h = _load_health()

    def test_parses_percentage_and_top_clones(self):
        line = self._h._summarize_jscpd_report(JSCPD_REPORT_ONE_CLONE)
        self.assertIsNotNone(line)
        self.assertIn("duplication", line.lower())
        self.assertIn("50", line)  # percentage
        self.assertIn("src/a.js:1", line)  # top clone file:line

    def test_clean_report_reports_zero(self):
        line = self._h._summarize_jscpd_report(JSCPD_REPORT_CLEAN)
        self.assertIsNotNone(line)
        self.assertIn("0", line)

    def test_malformed_report_no_crash_no_junk(self):
        # Unparseable / missing report → None (report nothing), never raise.
        self.assertIsNone(self._h._summarize_jscpd_report("not json at all"))
        self.assertIsNone(self._h._summarize_jscpd_report(""))
        self.assertIsNone(self._h._summarize_jscpd_report("{}"))


# -------------------- DuplicationAdvisoryTests --------------------


class DuplicationAdvisoryTests(unittest.TestCase):
    """AC2/AC3/AC4 — duplication is an advisory probe: it appears in the
    summary, never flips a clean primary exit, and emits a `skipped (no
    detector)` line when nothing resolves (the skip_summary extension)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_jscpd_signal_does_not_flip_clean_exit(self):
        # AC2/AC3 — ruff primary clean (rc 0); duplication probe (jscpd) runs
        # and reports a percentage. Exit stays 0; the line appears.
        _seed_python(self.target)
        stdout_buf = []

        def fake_run(argv, *a, **k):
            if "jscpd" in argv:
                # jscpd ran; the summarizer reads the report file, so the
                # subprocess result itself can be anything benign.
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="[]", stderr="")

        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check", "--output-format=json", "."]):
            with patch.object(self._h.shutil, "which",
                              side_effect=lambda n: "/x" if n in ("ruff", "npx") else None):
                with patch.object(self._h, "_summarize_jscpd_report",
                                  return_value="duplication: 50.0% (1 clones); top: src/a.js:1"):
                    with patch.object(self._h.subprocess, "run", side_effect=fake_run):
                        with patch("sys.stdout") as mock_out:
                            mock_out.write = lambda s: stdout_buf.append(s)
                            code = self._h.cmd_check(self.target)
        self.assertEqual(code, 0, "duplication (advisory) must not flip the exit code")
        out = "".join(stdout_buf).lower()
        self.assertIn("duplication", out)
        self.assertIn("50", out)

    def test_skip_line_when_no_detector_and_exit_unaffected(self):
        # AC3 — no native tool, no npx → the duplication probe emits a
        # `skipped (no detector)` line AND the overall exit is unaffected.
        _seed_python(self.target)
        stdout_buf = []

        def fake_run(argv, *a, **k):
            return MagicMock(returncode=0, stdout="[]", stderr="")

        # ruff resolves (so the primary runs clean) but npx does not.
        with patch.object(self._h, "resolve_lint_command",
                          return_value=["ruff", "check", "--output-format=json", "."]):
            with patch.object(self._h.shutil, "which",
                              side_effect=lambda n: "/x" if n == "ruff" else None):
                with patch.object(self._h.subprocess, "run", side_effect=fake_run):
                    with patch("sys.stdout") as mock_out:
                        mock_out.write = lambda s: stdout_buf.append(s)
                        code = self._h.cmd_check(self.target)
        self.assertEqual(code, 0, "advisory skip must not flip the exit code")
        out = "".join(stdout_buf).lower()
        self.assertIn("duplication", out)
        self.assertIn("skipped", out)
        self.assertIn("no detector", out)


# -------------------- AdvisoryProbeSkipSummaryTests --------------------


class AdvisoryProbeSkipSummaryTests(unittest.TestCase):
    """The AdvisoryProbe.skip_summary extension: a probe WITHOUT skip_summary
    (complexity / prettier) stays SILENT when its resolver returns None, while
    a probe WITH skip_summary (duplication) emits its skip line. Proves the
    060-04 extension did not regress 060-03 behavior."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def test_probe_without_skip_summary_silent_when_unresolved(self):
        probe = self._h.AdvisoryProbe(
            name="x",
            resolve=lambda t, w: None,
            summarize=lambda rc, o, e, w: "should never appear",
        )
        lines = self._h._run_advisory_probes([probe], self.target)
        self.assertEqual(lines, [])

    def test_probe_with_skip_summary_emits_when_unresolved(self):
        probe = self._h.AdvisoryProbe(
            name="dup",
            resolve=lambda t, w: None,
            summarize=lambda rc, o, e, w: None,
            skip_summary="duplication: skipped (no detector)",
        )
        lines = self._h._run_advisory_probes([probe], self.target)
        self.assertEqual(lines, ["duplication: skipped (no detector)"])

    def test_duplication_probe_wired_into_both_ecosystems(self):
        # AC1/AC2 — the shared duplication probe is referenced by BOTH
        # ecosystems' advisory_probes lists.
        for eco in self._h.ECOSYSTEMS:
            names = [p.name for p in eco.advisory_probes]
            self.assertIn("duplication", names,
                          f"{eco.name} should run the duplication probe")


# -------------------- WorkdirLifecycleTests --------------------


class WorkdirLifecycleTests(unittest.TestCase):
    """060-04 craft-review fix: a `needs_workdir` probe's temp dir is owned by
    the runner (a `TemporaryDirectory`), so it is torn down on EVERY exit path —
    a normal run AND a subprocess failure (the leak the original
    summarizer-owned `finally` missed). Proven by globbing the `jig-jscpd-*`
    temp dirs before/after."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        self._h = _load_health()

    def tearDown(self):
        self.tmp.cleanup()

    def _jscpd_temp_dirs(self):
        return set(glob.glob(os.path.join(tempfile.gettempdir(), "jig-jscpd-*")))

    def test_workdir_threaded_into_resolve_and_summarize(self):
        # The runner creates a real temp dir and passes the SAME path to both
        # resolve and summarize.
        seen = {}
        probe = self._h.AdvisoryProbe(
            name="dup",
            resolve=lambda t, w: (seen.__setitem__("resolve", w), ["echo"])[1],
            summarize=lambda rc, o, e, w: (seen.__setitem__("summarize", w), "ok")[1],
            needs_workdir=True,
        )
        with patch.object(self._h.subprocess, "run",
                          return_value=MagicMock(returncode=0, stdout="", stderr="")):
            lines = self._h._run_advisory_probes([probe], self.target)
        self.assertEqual(lines, ["ok"])
        self.assertIsNotNone(seen.get("resolve"))
        self.assertEqual(seen["resolve"], seen["summarize"])

    def test_workdir_cleaned_after_normal_run(self):
        before = self._jscpd_temp_dirs()
        probe = self._h.AdvisoryProbe(
            name="dup",
            resolve=lambda t, w: ["echo", "x"],
            summarize=lambda rc, o, e, w: "line",
            needs_workdir=True,
        )
        with patch.object(self._h.subprocess, "run",
                          return_value=MagicMock(returncode=0, stdout="", stderr="")):
            lines = self._h._run_advisory_probes([probe], self.target)
        self.assertEqual(lines, ["line"])
        self.assertEqual(before, self._jscpd_temp_dirs(),
                         "needs_workdir temp dir must be cleaned after a normal run")

    def test_workdir_cleaned_when_subprocess_raises(self):
        # The leak path: subprocess.run raises AFTER the temp dir is created.
        # The runner's TemporaryDirectory context must still tear it down, and
        # the run must not crash (advisory best-effort).
        before = self._jscpd_temp_dirs()
        probe = self._h.AdvisoryProbe(
            name="dup",
            resolve=lambda t, w: ["jscpd"],
            summarize=lambda rc, o, e, w: "should not appear",
            skip_summary="dup: skipped",
            needs_workdir=True,
        )
        with patch.object(self._h.subprocess, "run", side_effect=OSError("boom")):
            lines = self._h._run_advisory_probes([probe], self.target)
        self.assertEqual(lines, [], "a raising subprocess contributes nothing")
        self.assertEqual(before, self._jscpd_temp_dirs(),
                         "needs_workdir temp dir must be cleaned even when subprocess raises")


if __name__ == "__main__":
    unittest.main()
