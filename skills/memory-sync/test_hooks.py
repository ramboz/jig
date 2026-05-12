"""
Hook script tests for slice 002-03 (auto-detect-hooks).

Tests both `jig-memory-scan.sh` (UserPromptSubmit) and `jig-task-capture.sh` (Stop)
by piping mock hook payloads in via stdin and asserting on stdout JSON, stderr,
and exit code.

Run from the repo root:
    python3 skills/memory-sync/test_hooks.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-memory-scan.sh"
CAPTURE_HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-task-capture.sh"
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
MEMORY = REPO_ROOT / "skills" / "memory-sync" / "memory.py"


def run_hook(hook_path: Path, payload: dict, project_dir: Path) -> subprocess.CompletedProcess:
    """Invoke a hook script with the given JSON payload piped via stdin.
    CLAUDE_PROJECT_DIR is set so the hook can locate CLAUDE.md / glossary.md."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        ["bash", str(hook_path)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    )


def scaffold_project(target: Path) -> None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target)],
        capture_output=True, text=True, env=env, check=True,
    )


class MemoryScanHookTests(unittest.TestCase):
    """jig-memory-scan.sh fires on UserPromptSubmit and surfaces unknown
    capitalized references that aren't in the hot cache or glossary."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-scan-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold_project(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _scan(self, prompt: str) -> subprocess.CompletedProcess:
        return run_hook(SCAN_HOOK, {
            "session_id": "test", "hook_event_name": "UserPromptSubmit",
            "prompt": prompt, "cwd": str(self.target),
        }, self.target)

    def _scan_output(self, prompt: str):
        """Run scan; return (returncode, parsed_json_or_None)."""
        result = self._scan(prompt)
        self.assertEqual(result.returncode, 0, f"hook should never block; stderr: {result.stderr}")
        if not result.stdout.strip():
            return result.returncode, None
        return result.returncode, json.loads(result.stdout)

    def test_exits_0_always(self):
        """AC #3: non-blocking, regardless of input."""
        result = self._scan("")
        self.assertEqual(result.returncode, 0)
        result = self._scan("just plain text")
        self.assertEqual(result.returncode, 0)
        # Even garbage doesn't fail
        result = run_hook(SCAN_HOOK, {"unexpected": "shape"}, self.target)
        self.assertEqual(result.returncode, 0)

    def test_silent_on_no_capitalized(self):
        _, out = self._scan_output("how do i implement the lookup pattern")
        self.assertIsNone(out, "no capitalized refs → no output expected")

    def test_silent_on_known_terms_in_hot_cache(self):
        # Promote a term to hot cache
        subprocess.run(
            [sys.executable, str(MEMORY), "promote", "MyWidget", "the widget", str(self.target)],
            capture_output=True, env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
            check=True,
        )
        _, out = self._scan_output("can you update the MyWidget config?")
        self.assertIsNone(out, "term in hot cache should be treated as known")

    def test_silent_on_known_terms_in_glossary(self):
        subprocess.run(
            [sys.executable, str(MEMORY), "add-term", "Quartzite", "a metamorphic rock", str(self.target)],
            capture_output=True, env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
            check=True,
        )
        _, out = self._scan_output("tell me more about Quartzite")
        self.assertIsNone(out, "term in glossary should be treated as known")

    def test_flags_unknown_acronym(self):
        _, out = self._scan_output("can we add support for ZQRX in the parser?")
        self.assertIsNotNone(out, "unknown acronym should be flagged")
        self.assertTrue(out.get("continue"))
        self.assertIn("ZQRX", out["additionalContext"])

    def test_flags_unknown_camelcase(self):
        _, out = self._scan_output("please review the QuackPipeline class")
        self.assertIsNotNone(out)
        self.assertIn("QuackPipeline", out["additionalContext"])

    def test_skips_common_acronyms(self):
        _, out = self._scan_output("call the API and parse the JSON via the CLI")
        self.assertIsNone(out, "common acronyms (API/JSON/CLI) should be skipped")

    def test_strips_inline_code_before_scanning(self):
        _, out = self._scan_output("fix the bug in `MyNewClass` method")
        self.assertIsNone(out, "inline code blocks should be stripped before scan")

    def test_strips_fenced_code_blocks(self):
        prompt = "look at this:\n```python\nclass NovelClass:\n    pass\n```\nfix it"
        _, out = self._scan_output(prompt)
        self.assertIsNone(out, "fenced code blocks should be stripped before scan")

    def test_strips_urls(self):
        _, out = self._scan_output("see https://AnthropicCorp.com/docs for details")
        self.assertIsNone(out, "URLs should be stripped before scan")

    def test_skips_absolute_paths(self):
        _, out = self._scan_output("the file at /Users/RandomGuy/Projects/widget.py needs work")
        # /Users, /Projects, RandomGuy, Projects are all in path
        self.assertIsNone(out, "absolute paths should be stripped before scan")

    def test_output_is_well_formed_json(self):
        _, out = self._scan_output("the system uses BarBazQuux internally")
        self.assertIsNotNone(out)
        self.assertIsInstance(out, dict)
        self.assertIn("continue", out)
        self.assertIn("additionalContext", out)
        self.assertIsInstance(out["additionalContext"], str)


class TaskCaptureHookTests(unittest.TestCase):
    """jig-task-capture.sh fires on Stop and surfaces task-capture language."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-cap-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold_project(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _capture(self, messages_text: str) -> subprocess.CompletedProcess:
        return run_hook(CAPTURE_HOOK, {
            "session_id": "test", "hook_event_name": "Stop",
            "messages": [{"role": "assistant", "content": messages_text}],
        }, self.target)

    def _capture_output(self, messages_text: str):
        result = self._capture(messages_text)
        self.assertEqual(result.returncode, 0, f"hook should never block; stderr: {result.stderr}")
        if not result.stdout.strip():
            return result.returncode, None
        return result.returncode, json.loads(result.stdout)

    def test_exits_0_always(self):
        result = self._capture("")
        self.assertEqual(result.returncode, 0)
        result = self._capture("plain summary, nothing actionable")
        self.assertEqual(result.returncode, 0)
        # Garbage payload still doesn't block
        result = run_hook(CAPTURE_HOOK, {"unexpected": "shape"}, self.target)
        self.assertEqual(result.returncode, 0)

    def test_silent_on_no_capture_patterns(self):
        _, out = self._capture_output("I fixed the bug and added a test. Done.")
        self.assertIsNone(out)

    def test_flags_we_should_also(self):
        _, out = self._capture_output("the change works. we should also update the docs at some point.")
        self.assertIsNotNone(out)
        self.assertIn("triage", out["additionalContext"].lower())

    def test_flags_todo_marker(self):
        _, out = self._capture_output("the rest is left as TODO: cover the error path")
        self.assertIsNotNone(out)

    def test_flags_remind_me_to(self):
        _, out = self._capture_output("done with the main fix. remind me to file an issue later.")
        self.assertIsNotNone(out)

    def test_flags_dont_forget(self):
        _, out = self._capture_output("merged. don't forget to bump the version next release.")
        self.assertIsNotNone(out)

    def test_output_is_well_formed_json(self):
        _, out = self._capture_output("we should also revisit the timeout logic")
        self.assertIsNotNone(out)
        self.assertIsInstance(out, dict)
        self.assertIn("continue", out)
        self.assertIn("additionalContext", out)


if __name__ == "__main__":
    unittest.main()
