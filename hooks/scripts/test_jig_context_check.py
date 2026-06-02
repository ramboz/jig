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


def run_hook_prompt(
    project_dir: Path,
    transcript_path,
    *,
    session_id: str = "sess-1",
    env_overrides: dict = None,
    tmpdir: Path = None,
) -> subprocess.CompletedProcess:
    """Invoke jig-context-check.sh with a UserPromptSubmit payload pointing at
    a synthetic transcript (slice 055-02). The per-session state file lives
    under TMPDIR; tests pass an isolated tmpdir so bands don't leak between
    cases."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    for var in ("JIG_CONTEXT_WINDOW_BYTES", "JIG_CONTEXT_SOFT_WARN_PCT",
                "JIG_CONTEXT_GROWTH_WARN_PCT"):
        env.pop(var, None)
    if tmpdir is not None:
        env["TMPDIR"] = str(tmpdir)
    if env_overrides:
        env.update(env_overrides)
    payload = {
        "session_id": session_id,
        "hook_event_name": "UserPromptSubmit",
        "transcript_path": str(transcript_path) if transcript_path else "",
    }
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    )


def write_transcript(path: Path, cache_read_values) -> Path:
    """Write a synthetic transcript JSONL: one assistant record per value,
    each with the given cache_read_input_tokens. The last value is the tail
    the hook reads."""
    records = []
    for v in cache_read_values:
        records.append({"type": "user", "message": {"role": "user"}})
        records.append({
            "type": "assistant",
            "message": {"usage": {"cache_read_input_tokens": v}},
        })
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return path


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


# --------------------------------------------------------------------------
# Slice 055-02 — in-session context-growth nudge on UserPromptSubmit. The
# SAME script handles both events (Clarification Q2); these feed crafted
# transcript JSONL to the hook and assert nudge text vs. silence, exit 0,
# never continue:false, and per-band rate-limit with re-arm-on-drop.
# --------------------------------------------------------------------------


class GrowthNudgeUserPromptTests(unittest.TestCase):
    """AC #1–#6 — the UserPromptSubmit branch."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="jig-055-02-"))
        self.project = self.base / "project"
        self.project.mkdir()
        self.transcripts = self.base / "transcripts"
        self.transcripts.mkdir()
        # Isolated state dir per test so warned-bands don't leak.
        self.state = self.base / "state"
        self.state.mkdir()
        # Tidy 100-token window: 40 tok = 40%, 60 = 60%, 80 = 80%.
        self.window_env = {"JIG_CONTEXT_WINDOW_BYTES": "400"}  # 400 / 4 = 100

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)

    def _run(self, values, *, session_id="s", extra_env=None):
        path = write_transcript(
            self.transcripts / f"{session_id}.jsonl", values
        )
        env = dict(self.window_env)
        if extra_env:
            env.update(extra_env)
        return run_hook_prompt(
            self.project, path, session_id=session_id,
            env_overrides=env, tmpdir=self.state,
        )

    # ----- AC #1 / AC #3: below threshold → silent ------------------------
    def test_below_threshold_silent(self):
        r = self._run([30])  # 30% < 40% default
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(parse_or_none(r))

    # ----- AC #1: first crossing → exactly one nudge ----------------------
    def test_first_crossing_emits_nudge(self):
        r = self._run([45])  # 45% ≥ 40%
        self.assertEqual(r.returncode, 0, r.stderr)
        out = parse_or_none(r)
        self.assertIsNotNone(out, f"expected nudge; stdout={r.stdout}")
        ctx = out["additionalContext"]
        # AC #1: recommends /compact or delegating a read-heavy step.
        self.assertIn("/compact", ctx)
        self.assertIn("delegat", ctx.lower())
        # AC #6: references the workflow.md Context-cost discipline section.
        self.assertIn("Context-cost discipline", ctx)

    # ----- AC #4: re-crossing the same band → silent ----------------------
    def test_recrossing_same_band_silent(self):
        first = self._run([45], session_id="same")
        self.assertIsNotNone(parse_or_none(first))
        # Second user turn, still in the 40–60 band → silent.
        second = self._run([50], session_id="same")
        self.assertEqual(second.returncode, 0)
        self.assertIsNone(parse_or_none(second),
                          f"same band must stay silent; got {second.stdout}")

    # ----- AC #4: a higher band → nudge again -----------------------------
    def test_higher_band_nudges_again(self):
        first = self._run([45], session_id="climb")
        self.assertIsNotNone(parse_or_none(first))
        second = self._run([65], session_id="climb")  # crosses 60%
        out = parse_or_none(second)
        self.assertIsNotNone(out, "crossing a higher band must nudge")
        self.assertIn("/compact", out["additionalContext"])

    # ----- AC #4: drop then re-climb → re-armed nudge ---------------------
    def test_drop_then_reclimb_rearmed_nudge(self):
        first = self._run([45], session_id="rearm")
        self.assertIsNotNone(parse_or_none(first))
        # /compact drops context below the band → silent + re-arm.
        drop = self._run([20], session_id="rearm")
        self.assertIsNone(parse_or_none(drop))
        # Re-climb past 40% → nudges AGAIN.
        reclimb = self._run([45], session_id="rearm")
        out = parse_or_none(reclimb)
        self.assertIsNotNone(out, "re-armed band must nudge on re-climb")

    # ----- AC #5: no assistant turn yet → silent --------------------------
    def test_no_assistant_turn_silent(self):
        path = self.transcripts / "noturn.jsonl"
        path.write_text(json.dumps({"type": "user", "message": {}}) + "\n")
        r = run_hook_prompt(self.project, path, session_id="noturn",
                            env_overrides=self.window_env, tmpdir=self.state)
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(parse_or_none(r))

    # ----- AC #5: missing transcript → silent -----------------------------
    def test_missing_transcript_silent(self):
        r = run_hook_prompt(self.project, self.transcripts / "nope.jsonl",
                            env_overrides=self.window_env, tmpdir=self.state)
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(parse_or_none(r))

    # ----- AC #5: empty transcript_path → silent --------------------------
    def test_empty_transcript_path_silent(self):
        r = run_hook_prompt(self.project, None,
                            env_overrides=self.window_env, tmpdir=self.state)
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(parse_or_none(r))

    # ----- AC #5: malformed transcript → silent, never throws -------------
    def test_malformed_transcript_silent(self):
        path = self.transcripts / "bad.jsonl"
        path.write_text("{not valid json at all\n!!!\n")
        r = run_hook_prompt(self.project, path, session_id="bad",
                            env_overrides=self.window_env, tmpdir=self.state)
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(parse_or_none(r))

    # ----- AC #1: never blocks --------------------------------------------
    def test_never_emits_continue_false(self):
        r = self._run([85])  # crosses everything
        self.assertEqual(r.returncode, 0)
        out = parse_or_none(r)
        if out is not None:
            self.assertTrue(out.get("continue", True) is True,
                            f"continue must be True or absent; got {out!r}")

    # ----- AC #3: env-var override of the threshold -----------------------
    def test_growth_threshold_env_override(self):
        # Raise the bar to 0.50: 45% now silent.
        r = self._run([45], session_id="ovr",
                       extra_env={"JIG_CONTEXT_GROWTH_WARN_PCT": "0.50"})
        self.assertIsNone(parse_or_none(r))
        # 55% crosses the overridden 0.50 band.
        r2 = self._run([55], session_id="ovr2",
                        extra_env={"JIG_CONTEXT_GROWTH_WARN_PCT": "0.50"})
        self.assertIsNotNone(parse_or_none(r2))

    # ----- AC #2: only the tail is read (not the whole file) --------------
    def test_uses_last_assistant_record(self):
        # Early big read, then a small tail: the LAST record (10%) governs →
        # silent. If the hook scanned the whole file it'd see the 90% and
        # nudge.
        r = self._run([90, 10], session_id="tail")
        self.assertIsNone(parse_or_none(r),
                          "hook must read the tail record, not the max")


class SessionStartNoRegressionTests(unittest.TestCase):
    """AC #1 — extending the script to UserPromptSubmit must not change the
    SessionStart baseline behavior. A SessionStart payload still runs the
    primer-fill estimate and never touches the growth path."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-055-02-ss-")
        self.target = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_sessionstart_still_warns_on_baseline_fill(self):
        """SessionStart + an over-threshold primer → the existing
        context-fill warning, unchanged."""
        (self.target / "CLAUDE.md").write_text("x" * 400)
        result = run_hook(self.target, env_overrides={
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_SOFT_WARN_PCT": "0.3",
        })
        self.assertEqual(result.returncode, 0)
        out = parse_or_none(result)
        self.assertIsNotNone(out)
        ctx = out["additionalContext"]
        self.assertIn("/jig:memory-sync", ctx)
        self.assertIn("/compact", ctx)
        # The growth-nudge text must NOT appear on a SessionStart event.
        self.assertNotIn("Context-cost discipline", ctx)

    def test_sessionstart_silent_below_baseline_threshold(self):
        """SessionStart with a tiny primer → no warning (unchanged)."""
        (self.target / "CLAUDE.md").write_text("x" * 10)
        result = run_hook(self.target)
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(parse_or_none(result))


if __name__ == "__main__":
    unittest.main()
