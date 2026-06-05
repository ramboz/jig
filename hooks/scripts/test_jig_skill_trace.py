"""Hook-integration tests for hooks/scripts/jig-skill-trace.sh
(skill-routing observability — spec 041).

Run from the repo root:
    python3 hooks/scripts/test_jig_skill_trace.py
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-skill-trace.sh"


def run_hook(project_dir: Path, payload, *, raw: str = None) -> subprocess.CompletedProcess:
    """Invoke jig-skill-trace.sh with a PreToolUse/Skill payload.

    `payload` is a dict serialized to JSON; pass `raw` to send arbitrary
    (possibly malformed) stdin instead.
    """
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    stdin = raw if raw is not None else json.dumps(payload)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        capture_output=True, text=True, env=env,
    )


def read_log(project_dir: Path):
    log = Path(project_dir) / ".claude" / "skill-usage.jsonl"
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]


class SkillTraceHookTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-skill-trace-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _skill_payload(self, skill_name):
        return {
            "session_id": "sess-1",
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill_name": skill_name},
        }

    def test_records_invoked_skill_name(self):
        result = run_hook(self.project, self._skill_payload("pr-review"))
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        entries = read_log(self.project)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["skill_name"], "pr-review")
        self.assertEqual(entries[0]["event"], "skill_invoked")
        self.assertEqual(entries[0]["tool_name"], "Skill")
        self.assertEqual(entries[0]["session_id"], "sess-1")
        self.assertIn("timestamp", entries[0])

    def test_records_plugin_scoped_name_verbatim(self):
        # The whole point: distinguish the jig baseline from a richer skill.
        run_hook(self.project, self._skill_payload("jig:pr-review"))
        entries = read_log(self.project)
        self.assertEqual(entries[0]["skill_name"], "jig:pr-review")

    def test_appends_rather_than_overwrites(self):
        run_hook(self.project, self._skill_payload("pr-review"))
        run_hook(self.project, self._skill_payload("jig:arch-review"))
        names = [e["skill_name"] for e in read_log(self.project)]
        self.assertEqual(names, ["pr-review", "jig:arch-review"])

    def test_missing_tool_input_is_graceful(self):
        payload = {"session_id": "s", "tool_name": "Skill"}  # no tool_input
        result = run_hook(self.project, payload)
        self.assertEqual(result.returncode, 0)
        entries = read_log(self.project)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["skill_name"], "")

    def test_malformed_json_never_crashes(self):
        result = run_hook(self.project, None, raw="{not valid json")
        # Hook must swallow the error and exit 0 — it must never block a tool.
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertEqual(read_log(self.project), [])

    def test_empty_stdin_never_crashes(self):
        result = run_hook(self.project, None, raw="")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(read_log(self.project), [])

    def test_creates_claude_dir_if_absent(self):
        # No .claude/ pre-created — the hook must mkdir it.
        self.assertFalse((self.project / ".claude").exists())
        run_hook(self.project, self._skill_payload("pr-review"))
        self.assertTrue((self.project / ".claude" / "skill-usage.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
