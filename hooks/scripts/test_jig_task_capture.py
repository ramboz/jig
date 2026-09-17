import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks" / "scripts" / "jig-task-capture.sh"


class TaskCaptureTranscriptTests(unittest.TestCase):
    def test_transcript_input_surfaces_task(self):
        with tempfile.TemporaryDirectory(prefix="jig-task-") as tmp:
            project = Path(tmp)
            transcript = project / "session.jsonl"
            transcript.write_text(json.dumps({
                "type": "assistant",
                "message": {"role": "assistant",
                            "content": "TODO: document the follow-up"},
            }) + "\n")
            env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
            result = subprocess.run(
                ["bash", str(HOOK)],
                input=json.dumps({
                    "session_id": "s", "hook_event_name": "Stop",
                    "transcript_path": str(transcript),
                }),
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Task-capture patterns detected", result.stdout)

    def test_malformed_transcript_fails_open(self):
        with tempfile.TemporaryDirectory(prefix="jig-task-") as tmp:
            project = Path(tmp)
            transcript = project / "session.jsonl"
            transcript.write_text("not json\n")
            env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
            result = subprocess.run(
                ["bash", str(HOOK)],
                input=json.dumps({"transcript_path": str(transcript)}),
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
