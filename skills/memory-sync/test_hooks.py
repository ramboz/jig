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
            [sys.executable, str(MEMORY), "add-term", "Quartzite",
             "a metamorphic rock", str(self.target)],
            capture_output=True, env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
            check=True,
        )
        _, out = self._scan_output("tell me more about Quartzite")
        # As of slice 065-02 the lexicon overlay (AC #4) surfaces a glossary
        # term's plain-language definition — so the hook is no longer silent
        # here. Assert the def DID surface (guards against a vacuous pass if a
        # future regression silenced both paths) AND that the unknown-reference
        # surfacing still stays quiet for a known glossary term.
        self.assertIsNotNone(out, "glossary term should now surface a lexicon def")
        self.assertIn("a metamorphic rock", out["additionalContext"],
                      "the glossary overlay def should be surfaced")
        self.assertNotIn("Unrecognized references", out["additionalContext"],
                         "glossary term must not be flagged as unknown")

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


class MemoryScanLexiconTests(unittest.TestCase):
    """Slice 065-02: jig-memory-scan.sh surfaces plain-language definitions
    of jig lexicon terms appearing in the prompt, via _common/lexicon.py."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-lex-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold_project(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _scan(self, prompt: str, env_overrides=None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            ["bash", str(SCAN_HOOK)],
            input=json.dumps({
                "session_id": "test", "hook_event_name": "UserPromptSubmit",
                "prompt": prompt, "cwd": str(self.target),
            }),
            capture_output=True, text=True, env=env,
        )

    def _scan_output(self, prompt: str, env_overrides=None):
        result = self._scan(prompt, env_overrides)
        self.assertEqual(result.returncode, 0, f"hook should never block; stderr: {result.stderr}")
        if not result.stdout.strip():
            return result.returncode, None
        return result.returncode, json.loads(result.stdout)

    def test_known_term_definition_surfaced(self):
        """AC #1: a lexicon term in the prompt yields its short def."""
        _, out = self._scan_output("how does reconciliation work in this project?")
        self.assertIsNotNone(out, "lexicon term should surface a definition")
        ctx = out["additionalContext"]
        self.assertIn("reconciliation", ctx.lower())
        # The short def text should appear.
        self.assertIn("deviation log", ctx.lower())

    def test_multiword_term_surfaced(self):
        """AC #1: a multi-word key (vertical slice) matches as a phrase."""
        _, out = self._scan_output("explain what a vertical slice is")
        self.assertIsNotNone(out)
        self.assertIn("vertical slice", out["additionalContext"].lower())

    def test_acronym_term_case_insensitive(self):
        """AC #1: SPIDR matches case-insensitively."""
        _, out = self._scan_output("can you summarize the spidr techniques?")
        self.assertIsNotNone(out)
        self.assertIn("spidr", out["additionalContext"].lower())

    def test_no_substring_match(self):
        """AC #1: keys match on word/phrase boundaries, not substrings."""
        # 'adr' must not match inside 'quadrant'; 'ac' must not match 'space'.
        _, out = self._scan_output("draw a quadrant diagram in the space provided")
        # No lexicon defs should be injected for substring-only hits.
        if out is not None:
            ctx = out["additionalContext"]
            self.assertNotIn("Architecture Decision Record", ctx)
            self.assertNotIn("Acceptance Criteria", ctx)

    def test_composes_with_unknown_surfacing(self):
        """AC #2: lexicon def and unknown-ref message coexist."""
        _, out = self._scan_output(
            "how does reconciliation interact with the ZQRX subsystem?")
        self.assertIsNotNone(out)
        ctx = out["additionalContext"]
        self.assertIn("ZQRX", ctx, "unknown reference must still surface")
        self.assertIn("reconciliation", ctx.lower(), "lexicon def must still surface")
        self.assertTrue(out.get("continue"))

    def test_unknown_behavior_unchanged_no_lexicon_match(self):
        """AC #2: a prompt with only an unknown ref still surfaces it."""
        _, out = self._scan_output("can we add support for ZQRX in the parser?")
        self.assertIsNotNone(out)
        self.assertIn("ZQRX", out["additionalContext"])

    def test_capped_at_five(self):
        """AC #3: at most 5 lexicon defs are emitted, in order of appearance."""
        # Seven distinct lexicon terms in the prompt.
        prompt = ("the reconciliation step, the deviation log, the dod, "
                  "the dor, the hot cache, the dumb zone, and the spidr method")
        _, out = self._scan_output(prompt)
        self.assertIsNotNone(out)
        ctx = out["additionalContext"]
        # Count def lines: each def line begins with the term in our format.
        def_lines = [ln for ln in ctx.splitlines() if ln.strip().startswith("- ")]
        self.assertEqual(len(def_lines), 5,
                         f"expected exactly 5 lexicon defs, got {len(def_lines)}:\n{ctx}")
        # Order-of-appearance: reconciliation comes before spidr; spidr is 7th
        # so it must be dropped.
        self.assertIn("reconciliation", ctx.lower())
        self.assertNotIn("story-splitting", ctx.lower(),
                         "spidr (7th) should be dropped by the 5-cap")

    def test_fail_open_broken_lexicon(self):
        """AC #5: a broken lexicon import leaves exit 0 + unknowns intact."""
        # Force the lexicon import to fail by pointing the resolver at a path
        # whose lexicon module is broken. We simulate via a sabotaged copy.
        broken = Path(self.tmpdir) / "broken_common"
        broken.mkdir()
        (broken / "lexicon.py").write_text("raise RuntimeError('boom')\n")
        result = self._scan(
            "how does reconciliation interact with the ZQRX subsystem?",
            env_overrides={"JIG_LEXICON_COMMON_DIR": str(broken)},
        )
        self.assertEqual(result.returncode, 0, "broken lexicon must fail open (exit 0)")
        # The prompt proceeds; unknown surfacing still works.
        if result.stdout.strip():
            out = json.loads(result.stdout)
            self.assertIn("ZQRX", out["additionalContext"],
                          "unknown surfacing must survive a broken lexicon")

    def test_silent_when_no_terms(self):
        """No lexicon term and no unknown ref → no output."""
        _, out = self._scan_output("how do i write a simple loop")
        self.assertIsNone(out)


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
        _, out = self._capture_output(
            "the change works. we should also update the docs at some point.")
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
