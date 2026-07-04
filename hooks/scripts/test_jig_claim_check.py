"""Hook-integration tests for hooks/scripts/jig-claim-check.sh (the
refinement-todo "Memory-recall verification" cheapest-first-cut mitigation).

Unit tests for the scan logic live at hooks/scripts/lib/test_claim_check.py;
these cover the hook wrapper: stdin payload parsing, additionalContext
output shape, and fail-open behavior.

Run from the repo root:
    python3 hooks/scripts/test_jig_claim_check.py
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-claim-check.sh"


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


class ClaimCheckHookTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-claim-check-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _payload(self, messages):
        return {"session_id": "sess-1", "hook_event_name": "Stop",
                "messages": messages}

    def _agent(self, text):
        return {"role": "assistant", "content": text}

    def _make_spec(self, num, slug="demo"):
        spec_dir = self.project / "docs" / "specs" / f"{num:03d}-{slug}"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            "---\nstatus: DONE\n---\n\n# Spec\n\n## Overview\n\nx.\n"
        )

    def test_flags_unresolved_spec_claim(self):
        result = run_hook(self.project, self._payload(
            [self._agent("I checked spec 999 and it covers this.")]))
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        ctx = additional_context(result)
        self.assertIsNotNone(ctx)
        self.assertIn("spec 999", ctx)

    def test_resolved_spec_claim_emits_nothing(self):
        self._make_spec(42)
        result = run_hook(self.project, self._payload(
            [self._agent("I checked spec 42 and it covers this.")]))
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertIsNone(additional_context(result))

    def test_no_claims_emits_nothing(self):
        result = run_hook(self.project, self._payload(
            [self._agent("Just finished the refactor, all tests pass.")]))
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(additional_context(result))

    def test_only_scans_last_assistant_message(self):
        # An unresolved claim from an EARLIER turn must not resurface once a
        # later turn has been scanned — same-turn framing, not whole-session.
        result = run_hook(self.project, self._payload([
            self._agent("spec 999 does not exist yet"),
            {"role": "user", "content": "ok, thanks"},
            self._agent("all good, no further references here"),
        ]))
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(additional_context(result))

    def test_user_message_claims_are_not_scanned(self):
        result = run_hook(self.project, self._payload(
            [{"role": "user", "content": "does spec 999 exist?"}]))
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(additional_context(result))

    def test_missing_messages_key_is_graceful(self):
        result = run_hook(self.project, {"session_id": "s", "hook_event_name": "Stop"})
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertIsNone(additional_context(result))

    def test_malformed_json_never_crashes(self):
        result = run_hook(self.project, None, raw="{not valid json")
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")

    def test_empty_stdin_never_crashes(self):
        result = run_hook(self.project, None, raw="")
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
