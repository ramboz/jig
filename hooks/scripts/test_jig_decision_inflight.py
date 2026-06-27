"""Hook-integration tests for hooks/scripts/jig-decision-inflight.sh (slice 083-07).

Unit tests for the scratch logic live at
hooks/scripts/lib/test_decision_scratch.py; these cover the hook wrapper:
PostToolUse(AskUserQuestion) and UserPromptSubmit payload parsing, the in-flight
stub write, ephemera producing no stub, and fail-open behavior.

Run from the repo root:
    python3 hooks/scripts/test_jig_decision_inflight.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-decision-inflight.sh"
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


class InflightHookTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-decision-inflight-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_askuserquestion_answer_writes_stub(self):
        payload = {
            "session_id": "s1", "hook_event_name": "PostToolUse",
            "tool_name": "AskUserQuestion",
            "tool_input": {"question": "Which cache?"},
            "tool_response": {"answers": [{"value": "Redis over Memcached"}]},
        }
        result = run_hook(self.project, payload)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        stubs = ds.read_stubs(self.project, "s1")
        self.assertEqual(len(stubs), 1)
        self.assertEqual(stubs[0]["source"], "askuserquestion")
        self.assertEqual(stubs[0]["who"], "user")
        self.assertIn("Redis", stubs[0]["quote"])

    def test_blank_askuserquestion_answer_writes_nothing(self):
        payload = {
            "session_id": "s1", "hook_event_name": "PostToolUse",
            "tool_name": "AskUserQuestion",
            "tool_response": {"answers": [{"value": "   "}]},
        }
        result = run_hook(self.project, payload)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(ds.read_stubs(self.project, "s1"), [])

    def test_non_askuserquestion_posttooluse_ignored(self):
        payload = {
            "session_id": "s1", "hook_event_name": "PostToolUse",
            "tool_name": "Edit", "tool_response": {"ok": "edited a file"},
        }
        run_hook(self.project, payload)
        self.assertEqual(ds.read_stubs(self.project, "s1"), [])

    def test_user_override_prompt_writes_stub(self):
        payload = {
            "session_id": "s2", "hook_event_name": "UserPromptSubmit",
            "prompt": "Actually, use a banner instead of a modal.",
        }
        result = run_hook(self.project, payload)
        self.assertEqual(result.returncode, 0)
        stubs = ds.read_stubs(self.project, "s2")
        self.assertEqual(len(stubs), 1)
        self.assertEqual(stubs[0]["source"], "user-override")
        self.assertIn("banner", stubs[0]["quote"])

    def test_plain_prompt_writes_nothing(self):
        payload = {
            "session_id": "s2", "hook_event_name": "UserPromptSubmit",
            "prompt": "Can you run the tests and show me the output?",
        }
        run_hook(self.project, payload)
        self.assertEqual(ds.read_stubs(self.project, "s2"), [])

    def test_malformed_json_never_crashes(self):
        result = run_hook(self.project, None, raw="{not valid json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_empty_stdin_never_crashes(self):
        result = run_hook(self.project, None, raw="")
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
