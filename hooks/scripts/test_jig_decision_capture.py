"""Hook-integration tests for hooks/scripts/jig-decision-capture.sh (slice 083-04).

Unit tests for the scan logic live at hooks/scripts/lib/test_decision_scan.py;
these cover the hook wrapper: stdin payload parsing, owner-gated additionalContext
output, dedup against the project's recorded decisions, and fail-open behavior.

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

    def test_dedup_against_recorded_lightweight_decision(self):
        # Record the decision first; the scan must then stay quiet.
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
        self.assertEqual(result.stdout.strip(), "",
                         "already-recorded decision must be deduped to silence")

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

    def test_recorded_stub_is_pruned(self):
        ds.append_stub(self.project, "sess-1", "user",
                       "Use Postgres instead of MySQL for the primary store",
                       "user-override")
        decisions = self.project / "docs" / "decisions"
        decisions.mkdir(parents=True)
        (decisions / "lightweight-decisions.md").write_text(
            "## Entries\n\n"
            "### 2026-06-26 — Primary store\n"
            "**Decision:** Use Postgres instead of MySQL for the primary store.\n")
        result = run_hook(self.project, self._payload([]))
        self.assertEqual(result.stdout.strip(), "",
                         "recorded decision must be deduped to silence")
        self.assertFalse(ds.scratch_path(self.project, "sess-1").exists(),
                         "a now-recorded stub must be pruned (file removed)")

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
