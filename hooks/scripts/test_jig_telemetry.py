"""Hook-integration tests for hooks/scripts/jig-telemetry.sh.

Run from the repo root:
    python3 hooks/scripts/test_jig_telemetry.py
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-telemetry.sh"


def run_hook(project_dir: Path, payload, *, raw: str = None):
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    stdin = raw if raw is not None else json.dumps(payload)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def read_log(project_dir: Path):
    log = project_dir / ".claude" / "skill-usage.jsonl"
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()
            if line.strip()]


class TaskTelemetryHookTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-telemetry-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _task_payload(self, tool_input):
        return {
            "session_id": "sess-1",
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": tool_input,
        }

    def test_records_task_spawn_with_prompt_snippet(self):
        result = run_hook(
            self.project,
            self._task_payload({"prompt": "Review the slice deliverables."}),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        entries = read_log(self.project)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["event"], "task_spawned")
        self.assertEqual(entries[0]["tool_name"], "Task")
        self.assertEqual(entries[0]["session_id"], "sess-1")
        self.assertIn("Review the slice", entries[0]["prompt_snippet"])
        self.assertNotIn("phase", entries[0])

    def test_extracts_phase_spec_slice_from_prompt_tags(self):
        prompt = (
            "[jig:phase=compliance] [jig:spec=56] [jig:slice=56-3]\n"
            "Run the independent review."
        )
        result = run_hook(self.project,
                          self._task_payload({"prompt": prompt}))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        entry = read_log(self.project)[0]
        self.assertEqual(entry["phase"], "compliance")
        self.assertEqual(entry["spec"], "056")
        self.assertEqual(entry["slice"], "056-03")

    def test_structured_tool_input_overrides_prompt_tags(self):
        prompt = "[jig:phase=craft] [jig:spec=055] [jig:slice=055-01]"
        result = run_hook(
            self.project,
            self._task_payload({
                "prompt": prompt,
                "jig_phase": "reconciliation",
                "jig_spec": "57",
                "jig_slice": "57-2",
            }),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        entry = read_log(self.project)[0]
        self.assertEqual(entry["phase"], "reconciliation")
        self.assertEqual(entry["spec"], "057")
        self.assertEqual(entry["slice"], "057-02")

    def test_extracts_line_tags_from_description(self):
        description = "jig_phase: craft\njig_spec: 065\njig_slice: 065-04"
        run_hook(self.project,
                 self._task_payload({"description": description}))
        entry = read_log(self.project)[0]
        self.assertEqual(entry["phase"], "craft")
        self.assertEqual(entry["spec"], "065")
        self.assertEqual(entry["slice"], "065-04")

    def test_malformed_json_never_crashes(self):
        result = run_hook(self.project, None, raw="{not valid json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_log(self.project), [])

    def test_creates_claude_dir_if_absent(self):
        self.assertFalse((self.project / ".claude").exists())
        run_hook(self.project, self._task_payload({"prompt": "hello"}))
        self.assertTrue((self.project / ".claude" / "skill-usage.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
