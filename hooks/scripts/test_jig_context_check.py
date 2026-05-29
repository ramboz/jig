"""Hook-integration tests for hooks/scripts/jig-context-check.sh
(spec 026, slice 026-01).

Run from the repo root:
    python3 hooks/scripts/test_jig_context_check.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-context-check.sh"


def run_hook(project_dir: Path, *, env_overrides: dict = None) -> subprocess.CompletedProcess:
    """Invoke jig-context-check.sh with a stub SessionStart payload."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    # Strip any inherited estimator env so each test sets its own.
    for var in ("JIG_CONTEXT_WINDOW_BYTES", "JIG_CONTEXT_SOFT_WARN_PCT"):
        env.pop(var, None)
    if env_overrides:
        env.update(env_overrides)
    payload = {"session_id": "test", "hook_event_name": "SessionStart"}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    )


def parse_or_none(result: subprocess.CompletedProcess):
    """The hook may exit 0 with empty stdout (no warning) or stdout JSON
    (a warning)."""
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


class HookContextFillWarningTests(unittest.TestCase):
    """The context-fill branch of the hook (new in slice 026-01)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-hook-ctx-")
        self.target = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_repo_no_warning(self):
        """AC #3: ratio < threshold → no context-fill warning. No MCP
        config either, so the hook emits nothing."""
        result = run_hook(self.target)
        self.assertEqual(result.returncode, 0,
                         f"hook should never block; stderr: {result.stderr}")
        self.assertIsNone(parse_or_none(result))

    def test_threshold_not_crossed_no_warning(self):
        """AC #3: ratio below threshold → no context-fill warning."""
        # Tiny CLAUDE.md (10 bytes) against the 800_000-byte default window:
        # ratio ≈ 0.0000125, well below 0.30.
        (self.target / "CLAUDE.md").write_text("x" * 10)
        result = run_hook(self.target)
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(parse_or_none(result))

    def test_threshold_crossed_emits_warning(self):
        """AC #3: ratio >= threshold → additionalContext warning with the
        byte count, threshold, ratio, and the /jig:memory-sync + /compact
        hint."""
        # Force a crossing via env override: tiny window, tiny threshold.
        (self.target / "CLAUDE.md").write_text("x" * 400)
        result = run_hook(self.target, env_overrides={
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_SOFT_WARN_PCT": "0.3",
        })
        self.assertEqual(result.returncode, 0)
        out = parse_or_none(result)
        self.assertIsNotNone(out, f"expected warning; stdout: {result.stdout}")
        self.assertTrue(out.get("continue"), "continue must be True")
        ctx = out["additionalContext"]
        self.assertIn("400", ctx, "byte count must appear in warning")
        self.assertIn("/jig:memory-sync", ctx)
        self.assertIn("/compact", ctx)

    def test_threshold_warning_includes_ratio_for_calibration(self):
        """Goal #3 (spec 026): the warning surfaces the bytes→tokens
        conversion ratio so the user can calibrate (= the RATIO=4 constant
        showing up either explicitly or as the est_tokens count)."""
        (self.target / "CLAUDE.md").write_text("x" * 400)
        result = run_hook(self.target, env_overrides={
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_SOFT_WARN_PCT": "0.3",
        })
        out = parse_or_none(result)
        self.assertIsNotNone(out)
        ctx = out["additionalContext"]
        # est_tokens = 400 // 4 = 100. Either "100" tokens or "4 bytes/token"
        # would be evidence the conversion is surfaced.
        self.assertTrue("100" in ctx or "bytes/token" in ctx,
                        f"expected calibration signal in warning; got: {ctx}")

    def test_threshold_boundary_treated_as_crossed(self):
        """DoD edge case: ratio == threshold → crossed (>=, not >)."""
        # 300 bytes, 1000-byte window → ratio = 0.3 exactly. Threshold = 0.3.
        (self.target / "CLAUDE.md").write_text("x" * 300)
        result = run_hook(self.target, env_overrides={
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_SOFT_WARN_PCT": "0.3",
        })
        self.assertEqual(result.returncode, 0)
        out = parse_or_none(result)
        self.assertIsNotNone(out, "ratio == threshold must emit warning")
        self.assertIn("300", out["additionalContext"])

    def test_never_emits_continue_false(self):
        """AC #5: the hook must never set continue: false. Pinned even
        when the threshold is crossed."""
        (self.target / "CLAUDE.md").write_text("x" * 999)
        result = run_hook(self.target, env_overrides={
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_SOFT_WARN_PCT": "0.1",
        })
        self.assertEqual(result.returncode, 0, "exit 0 always")
        out = parse_or_none(result)
        if out is not None:
            # The contract is: either continue is True or the key is absent
            # (Claude defaults to true when omitted).
            self.assertTrue(
                out.get("continue", True) is True,
                f"continue must be True or absent; got: {out!r}",
            )


class HookMCPBranchTests(unittest.TestCase):
    """AC #4 + #7: existing MCP-server-count branch is preserved."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-hook-mcp-")
        self.target = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_mcp(self, n: int) -> None:
        """Write a .mcp.json with `n` server entries."""
        cfg = {"mcpServers": {f"srv{i}": {"command": "echo"} for i in range(n)}}
        (self.target / ".mcp.json").write_text(json.dumps(cfg))

    def test_few_servers_no_warning(self):
        """AC #7 no-regression: <=8 servers → no MCP warning."""
        self._write_mcp(3)
        result = run_hook(self.target)
        self.assertEqual(result.returncode, 0)
        out = parse_or_none(result)
        # No CLAUDE.md, no context-fill warning. <=8 servers, no MCP warning.
        self.assertIsNone(out)

    def test_many_servers_emits_mcp_warning(self):
        """AC #7 no-regression: >8 servers → MCP warning."""
        self._write_mcp(10)
        result = run_hook(self.target)
        self.assertEqual(result.returncode, 0)
        out = parse_or_none(result)
        self.assertIsNotNone(out)
        self.assertTrue(out.get("continue"))
        self.assertIn("MCP servers", out["additionalContext"])
        self.assertIn("10", out["additionalContext"])

    def test_both_warnings_coexist(self):
        """AC #4: MCP warning + context-fill warning fire together. Both
        present in a single additionalContext string."""
        self._write_mcp(10)
        (self.target / "CLAUDE.md").write_text("x" * 500)
        result = run_hook(self.target, env_overrides={
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_SOFT_WARN_PCT": "0.3",
        })
        self.assertEqual(result.returncode, 0)
        out = parse_or_none(result)
        self.assertIsNotNone(out)
        ctx = out["additionalContext"]
        # MCP-side evidence:
        self.assertIn("MCP servers", ctx)
        self.assertIn("10", ctx)
        # Context-fill-side evidence:
        self.assertIn("500", ctx)
        self.assertIn("/jig:memory-sync", ctx)


class HookRobustnessTests(unittest.TestCase):
    """The hook must be tolerant of malformed input + missing files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-hook-rob-")
        self.target = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_garbage_payload_still_exits_zero(self):
        """AC #5: hook is non-blocking — garbage stdin → exit 0."""
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="not-json-at-all",
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 0)

    def test_missing_project_dir_still_exits_zero(self):
        """Hook tolerates a missing CLAUDE_PROJECT_DIR."""
        env = {k: v for k, v in os.environ.items()
               if k != "CLAUDE_PROJECT_DIR"}
        result = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"session_id": "t", "hook_event_name": "SessionStart"}),
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
