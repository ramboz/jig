"""Hook-injection attribution tests for spec 070-02.

These tests exercise the five hook scripts that can emit `additionalContext`.
The telemetry must be metadata-only: count the injected bytes/tokens and
attribute by hook/spec/session without storing the injected body.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = REPO_ROOT / "hooks" / "scripts"
CONTEXT_CHECK = HOOK_DIR / "jig-context-check.sh"
MEMORY_SCAN = HOOK_DIR / "jig-memory-scan.sh"
POST_EDIT_VERIFY = HOOK_DIR / "jig-post-edit-verify.sh"
TASK_CAPTURE = HOOK_DIR / "jig-task-capture.sh"
BOUNDARY_WARN = HOOK_DIR / "jig-boundary-change-warn.sh"
PROJECT_ORIENT = HOOK_DIR / "jig-project-orient.sh"
LOG_NAME = "context-growth-read-events.jsonl"


def run_hook(hook: Path, payload: dict, project_dir: Path,
             *, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env.pop("JIG_POST_EDIT_VERIFY", None)
    env.pop("JIG_BOUNDARY_CHECK", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def parse_stdout(result: subprocess.CompletedProcess):
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def assert_warning_shape(testcase: unittest.TestCase,
                         result: subprocess.CompletedProcess) -> dict:
    out = parse_stdout(result)
    testcase.assertIsNotNone(out)
    testcase.assertIs(out.get("continue"), True)
    testcase.assertIsInstance(out.get("additionalContext"), str)
    testcase.assertGreater(len(out["additionalContext"]), 0)
    return out


def read_events(project_dir: Path) -> list[dict]:
    log = project_dir / ".claude" / LOG_NAME
    if not log.exists():
        return []
    return [
        json.loads(line)
        for line in log.read_text().splitlines()
        if line.strip()
    ]


def read_injection_events(project_dir: Path) -> list[dict]:
    return [
        event for event in read_events(project_dir)
        if event.get("event") == "additional_context"
    ]


class HookInjectionAttributionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-070-02-hooks-")
        self.project = Path(self.tmpdir) / "project"
        self.project.mkdir()
        marker = self.project / ".jig"
        marker.mkdir()
        (marker / "spec-ref").write_text("spec=070\nslice=070-02\n")
        (self.project / "scaffold.json").write_text("{}\n")
        spec_dir = self.project / "docs" / "specs" / "088-orient"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("---\nstatus: DRAFT\n---\n")
        (spec_dir / "slice-01-work.md").write_text(
            "---\nstatus: DRAFT\ndependencies: []\n---\n\n"
            "## Slice 088-01 — work\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _assert_one_injection(self, source_hook: str, expected_kind: str,
                              expected_event: str) -> dict:
        events = read_injection_events(self.project)
        self.assertEqual(len(events), 1, events)
        event = events[0]
        self.assertEqual(
            set(event),
            {
                "timestamp", "session_id", "event", "kind",
                "source_hook", "hook_event_name", "bytes",
                "estimated_tokens", "spec", "slice",
            },
        )
        self.assertEqual(event["event"], "additional_context")
        self.assertEqual(event["source_hook"], source_hook)
        self.assertEqual(event["kind"], expected_kind)
        self.assertEqual(event["hook_event_name"], expected_event)
        self.assertEqual(event["session_id"], "sess-070")
        self.assertEqual(event["spec"], "070")
        self.assertEqual(event["slice"], "070-02")
        self.assertGreater(event["bytes"], 0)
        self.assertGreaterEqual(event["estimated_tokens"], 0)
        return event

    def test_memory_scan_logs_metadata_only_injection_event(self):
        result = run_hook(MEMORY_SCAN, {
            "session_id": "sess-070",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Please connect the ZQRXController to the parser.",
        }, self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = assert_warning_shape(self, result)

        event = self._assert_one_injection(
            "jig-memory-scan", "memory_terms", "UserPromptSubmit")
        self.assertEqual(
            event["bytes"],
            len(out["additionalContext"].encode("utf-8")),
        )
        self.assertNotIn(out["additionalContext"], json.dumps(event))
        self.assertNotIn("ZQRXController", json.dumps(event))

    def test_context_check_logs_context_growth_injection_event(self):
        transcript = self.project / "session.jsonl"
        transcript.write_text(json.dumps({
            "type": "assistant",
            "message": {"usage": {"cache_read_input_tokens": 500}},
        }) + "\n")
        result = run_hook(CONTEXT_CHECK, {
            "session_id": "sess-070",
            "hook_event_name": "UserPromptSubmit",
            "transcript_path": str(transcript),
        }, self.project, env_overrides={
            "TMPDIR": str(self.project / "tmp"),
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_GROWTH_WARN_PCT": "0.1",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_warning_shape(self, result)
        self._assert_one_injection(
            "jig-context-check", "context_growth", "UserPromptSubmit")

    def test_context_check_logs_read_nudge_injection_event(self):
        big = self.project / "big.py"
        big.write_text("x" * 500)
        result = run_hook(CONTEXT_CHECK, {
            "session_id": "sess-070",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": str(big)},
        }, self.project, env_overrides={
            "TMPDIR": str(self.project / "tmp-read"),
            "JIG_READ_LEAN_BYTES": "100",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_warning_shape(self, result)

        self.assertEqual(
            sorted(event["event"] for event in read_events(self.project)),
            ["additional_context", "read_nudge"],
        )
        self._assert_one_injection(
            "jig-context-check", "read_nudge", "PreToolUse")

    def test_context_check_logs_sessionstart_injection_event(self):
        (self.project / "CLAUDE.md").write_text("x" * 500)
        result = run_hook(CONTEXT_CHECK, {
            "session_id": "sess-070",
            "hook_event_name": "SessionStart",
        }, self.project, env_overrides={
            "JIG_CONTEXT_WINDOW_BYTES": "1000",
            "JIG_CONTEXT_SOFT_WARN_PCT": "0.3",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_warning_shape(self, result)
        self._assert_one_injection(
            "jig-context-check", "context_check", "SessionStart")

    def test_post_edit_verify_logs_injection_event(self):
        f = self.project / "a.txt"
        f.write_text("actual contents")
        result = run_hook(POST_EDIT_VERIFY, {
            "session_id": "sess-070",
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "actual",
                "new_string": "EXPECTED_BUT_MISSING",
            },
        }, self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_warning_shape(self, result)
        self._assert_one_injection(
            "jig-post-edit-verify", "post_edit_verify", "PostToolUse")

    def test_task_capture_logs_injection_event(self):
        result = run_hook(TASK_CAPTURE, {
            "session_id": "sess-070",
            "hook_event_name": "Stop",
            "messages": [
                {"role": "assistant", "content": "TODO: follow up on telemetry."},
            ],
        }, self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_warning_shape(self, result)
        self._assert_one_injection(
            "jig-task-capture", "task_capture", "Stop")

    def test_boundary_change_logs_injection_event(self):
        f = self.project / "openapi.yaml"
        f.write_text("openapi: 3.0.0\n")
        result = run_hook(BOUNDARY_WARN, {
            "session_id": "sess-070",
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "openapi",
                "new_string": "edited",
            },
        }, self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_warning_shape(self, result)
        self._assert_one_injection(
            "jig-boundary-change-warn", "boundary_change", "PostToolUse")

    def test_project_orientation_logs_metadata_only_injection_event(self):
        result = run_hook(PROJECT_ORIENT, {
            "session_id": "sess-070",
            "hook_event_name": "SessionStart",
        }, self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = assert_warning_shape(self, result)
        event = self._assert_one_injection(
            "jig-project-orient", "project_orientation", "SessionStart")
        self.assertEqual(
            event["bytes"], len(out["additionalContext"].encode("utf-8")))
        self.assertNotIn(out["additionalContext"], json.dumps(event))

    def test_silent_hooks_write_no_injection_events(self):
        cases = [
            (MEMORY_SCAN, {
                "session_id": "sess-070",
                "hook_event_name": "UserPromptSubmit",
                "prompt": "all lowercase words only",
            }),
            (CONTEXT_CHECK, {
                "session_id": "sess-070",
                "hook_event_name": "SessionStart",
            }),
            (POST_EDIT_VERIFY, {
                "session_id": "sess-070",
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": str(self.project / "present.txt"),
                    "old_string": "hello",
                    "new_string": "hello",
                },
            }),
            (TASK_CAPTURE, {
                "session_id": "sess-070",
                "hook_event_name": "Stop",
                "messages": [{"role": "assistant", "content": "all done"}],
            }),
            (BOUNDARY_WARN, {
                "session_id": "sess-070",
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": str(self.project / "README.md")},
            }),
        ]
        (self.project / "present.txt").write_text("hello")

        for hook, payload in cases:
            with self.subTest(hook=hook.name):
                log = self.project / ".claude" / LOG_NAME
                if log.exists():
                    log.unlink()
                result = run_hook(hook, payload, self.project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsNone(parse_stdout(result))
                self.assertEqual(read_events(self.project), [])

    def test_logging_failure_preserves_original_output_and_stays_silent(self):
        (self.project / ".claude").write_text("not a directory")
        result = run_hook(MEMORY_SCAN, {
            "session_id": "sess-070",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Please investigate the ZQRXController.",
        }, self.project)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "")
        assert_warning_shape(self, result)


if __name__ == "__main__":
    unittest.main()
