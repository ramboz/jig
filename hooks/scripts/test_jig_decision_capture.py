"""Hook-integration tests for hooks/scripts/jig-decision-capture.sh (slice 083-04).

Unit tests for the scan logic live at hooks/scripts/lib/test_decision_scan.py;
these cover the hook wrapper: stdin payload parsing, owner-gated additionalContext
output, duplicate-flagging against the project's recorded decisions, and
fail-open behavior.

Run from the repo root:
    python3 hooks/scripts/test_jig_decision_capture.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-decision-capture.sh"
sys.path.insert(0, str(REPO_ROOT / "hooks" / "scripts" / "lib"))
import decision_scratch as ds  # noqa: E402


def run_hook(project_dir, payload, raw=None):
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    stdin = raw if raw is not None else json.dumps(payload)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin, capture_output=True, text=True, env=env,
    )


def additional_context(result):
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out).get("additionalContext")


class DecisionCaptureHookTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-decision-capture-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _payload(self, messages):
        return {"session_id": "sess-1", "hook_event_name": "Stop",
                "messages": messages}

    def test_surfaces_user_correction(self):
        result = run_hook(self.project, self._payload(
            [{"role": "user", "content": "English should not be the default language."}]))
        self.assertEqual(result.returncode, 0, msg="stderr: %s" % result.stderr)
        ctx = additional_context(result)
        self.assertIsNotNone(ctx)
        self.assertIn("should not be the default", ctx)
        self.assertIn("triage", ctx.lower())

    def test_ephemera_produce_no_output(self):
        result = run_hook(self.project, self._payload(
            [{"role": "assistant", "content": "Let me run the tests."}]))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_recorded_decision_is_flagged_not_silenced(self):
        # Bug 011 / issue #109: an already-recorded decision used to be silenced.
        # It is now surfaced and flagged, because the containment rule that drove
        # the silencing cannot tell a restatement from a reversal.
        decisions = self.project / "docs" / "decisions"
        decisions.mkdir(parents=True)
        (decisions / "lightweight-decisions.md").write_text(
            "## Entries\n\n"
            "### 2026-06-25 — Default language\n"
            "**Decision:** English is not the default language; users pick on "
            "first run.\n")
        result = run_hook(self.project, self._payload(
            [{"role": "user", "content": "English should not be the default language."}]))
        self.assertEqual(result.returncode, 0)
        ctx = additional_context(result)
        self.assertIsNotNone(ctx, "a recorded decision must still reach the owner")
        self.assertIn("possible duplicate", ctx.lower())
        self.assertRegex(ctx, r"(?i)reversal|changes a recorded decision")

    def test_reversal_of_recorded_decision_reaches_the_owner(self):
        # The bug's headline case, end-to-end through the hook: a Tier-2 override
        # that overturns a recorded decision must never be silenced.
        decisions = self.project / "docs" / "decisions"
        decisions.mkdir(parents=True)
        (decisions / "lightweight-decisions.md").write_text(
            "## Entries\n\n"
            "### 2026-07-15 — Settings button\n"
            "**Decision:** knob circles fill with var(--surface) not the mockup "
            "per-frame hex; the app --border 0.07 alpha light was kept over the "
            "mockup 0.09. Scope: Home settings button.\n")
        result = run_hook(self.project, self._payload(
            [{"role": "user",
              "content": "actually make the settings button border 0.09 alpha"}]))
        self.assertEqual(result.returncode, 0)
        ctx = additional_context(result)
        self.assertIsNotNone(
            ctx, "a reversal of a recorded decision must never be suppressed")
        self.assertIn("0.09", ctx)

    def test_logs_additional_context_event(self):
        run_hook(self.project, self._payload(
            [{"role": "user", "content": "Use a banner instead of a modal."}]))
        # read_attribution writes an events log under .claude/; its presence
        # (not exact path) confirms the surfacing seam fired.
        claude_dir = self.project / ".claude"
        self.assertTrue(claude_dir.exists(),
                        ".claude/ should be created by the attribution seam")

    def test_inflight_stub_surfaces_when_scan_empty(self):
        # A decision captured in-flight (083-07) must surface at session end even
        # when the transcript scan finds nothing.
        ds.append_stub(self.project, "sess-1", "user",
                       "Use a banner instead of a modal", "user-override")
        result = run_hook(self.project, self._payload(
            [{"role": "assistant", "content": "Let me run the tests."}]))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = additional_context(result)
        self.assertIsNotNone(ctx)
        self.assertIn("banner", ctx)

    def test_inflight_stub_dedups_against_scan_no_double_surface(self):
        # The SAME decision captured both in-flight and by the scan surfaces once.
        ds.append_stub(self.project, "sess-1", "user",
                       "English should not be the default language", "user-override")
        result = run_hook(self.project, self._payload(
            [{"role": "user", "content": "English should not be the default language."}]))
        ctx = additional_context(result)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.count("should not be the default"), 1,
                         "decision captured in-flight + by scan must surface once")

    def test_unrecorded_stub_persists_and_resurfaces(self):
        # A stub whose decision isn't recorded yet must survive triage and
        # re-surface on a later Stop — same durability as a scan candidate.
        ds.append_stub(self.project, "sess-1", "user",
                       "Use Postgres instead of MySQL", "user-override")
        first = additional_context(run_hook(self.project, self._payload([])))
        self.assertIsNotNone(first)
        self.assertIn("Postgres", first)
        self.assertTrue(ds.scratch_path(self.project, "sess-1").exists(),
                        "un-recorded stub must persist")
        second = additional_context(run_hook(self.project, self._payload([])))
        self.assertIsNotNone(second)
        self.assertIn("Postgres", second)  # re-surfaces, like the scan does

    def test_recorded_stub_is_flagged_not_pruned(self):
        # Bug 011 / issue #109: this stub used to be pruned to silence. The
        # in-flight surface is the highest-fidelity capture there is, so a stub
        # that looks recorded is flagged for triage and kept, never dropped.
        ds.append_stub(self.project, "sess-1", "user",
                       "Use Postgres instead of MySQL for the primary store",
                       "user-override")
        decisions = self.project / "docs" / "decisions"
        decisions.mkdir(parents=True)
        (decisions / "lightweight-decisions.md").write_text(
            "## Entries\n\n"
            "### 2026-06-26 — Primary store\n"
            "**Decision:** Use Postgres instead of MySQL for the primary store.\n")
        ctx = additional_context(run_hook(self.project, self._payload([])))
        self.assertIsNotNone(ctx, "a stub is never silenced for looking recorded")
        self.assertIn("Postgres", ctx)
        self.assertIn("possible duplicate", ctx.lower())
        self.assertTrue(ds.scratch_path(self.project, "sess-1").exists(),
                        "the stub must persist — the owner has not triaged it yet")

    def test_malformed_json_never_crashes(self):
        result = run_hook(self.project, None, raw="{not valid json")
        self.assertEqual(result.returncode, 0, msg="stderr: %s" % result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_empty_stdin_never_crashes(self):
        result = run_hook(self.project, None, raw="")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
