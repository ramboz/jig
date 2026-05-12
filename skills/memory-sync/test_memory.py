"""
AC verification tests for slice 002-01 (memory-sync explicit-sync).

Run from the repo root:
    python3 skills/memory-sync/test_memory.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY = REPO_ROOT / "skills" / "memory-sync" / "memory.py"
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def run_memory(target: Path, *args: str, stdin: str = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(MEMORY), *args, str(target)],
        capture_output=True, text=True, env=env,
        input=stdin,
    )


def scaffold(target: Path) -> None:
    """Run scaffold-init to set up the target."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target)],
        capture_output=True, text=True, env=env, check=True,
    )


class MemoryHelperTests(unittest.TestCase):
    """Slice 002-01 — CLI helpers operate on a scaffolded target."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-mem-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _glossary(self) -> str:
        return (self.target / "docs/memory/glossary.md").read_text()

    def _learnings(self) -> str:
        return (self.target / "docs/memory/learnings.md").read_text()

    def _inbox(self) -> str:
        return (self.target / "docs/inbox.md").read_text()

    def _claude(self) -> str:
        return (self.target / "CLAUDE.md").read_text()

    # AC #2: new glossary terms
    def test_add_term_appends_to_glossary(self):
        result = run_memory(self.target, "add-term", "SPIDR",
                            "Five story-splitting techniques: Spike, Path, Interface, Data, Rules")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._glossary()
        self.assertRegex(content, r"(?m)^## SPIDR\b")
        self.assertIn("Five story-splitting techniques", content)

    def test_add_term_idempotent(self):
        run_memory(self.target, "add-term", "FOO", "the foo system")
        run_memory(self.target, "add-term", "FOO", "the foo system")
        # Only one ## FOO heading
        self.assertEqual(self._glossary().count("\n## FOO\n"), 1,
                         "duplicate term should not write twice")

    # AC #3: new learnings
    def test_add_learning_with_body_flag(self):
        result = run_memory(self.target, "add-learning", "Heredoc stdin bug",
                            "--body", "python3 - <<EOF consumes stdin; use python3 -c instead")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._learnings()
        self.assertIn("Heredoc stdin bug", content)
        self.assertIn("python3 -c instead", content)

    def test_add_learning_via_stdin(self):
        result = run_memory(self.target, "add-learning", "Title via stdin",
                            stdin="Body comes from stdin when --body omitted.\n")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("Title via stdin", self._learnings())
        self.assertIn("Body comes from stdin", self._learnings())

    def test_add_learning_idempotent_on_same_title(self):
        run_memory(self.target, "add-learning", "X", "--body", "y")
        run_memory(self.target, "add-learning", "X", "--body", "y")
        self.assertEqual(self._learnings().count("\n## X\n"), 1)

    # AC #5: unresolved → inbox.md
    def test_add_inbox_dates_entry(self):
        result = run_memory(self.target, "add-inbox", "explore jq alternative for hooks")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._inbox()
        self.assertRegex(content, r"- \[\d{4}-\d{2}-\d{2}\] explore jq alternative")

    def test_add_inbox_appends(self):
        run_memory(self.target, "add-inbox", "first")
        run_memory(self.target, "add-inbox", "second")
        # Both items present, in order
        c = self._inbox()
        self.assertLess(c.index("first"), c.index("second"))

    # AC #4: high-frequency terms promoted to hot cache
    def test_promote_writes_to_hot_cache(self):
        result = run_memory(self.target, "promote", "jig",
                            "the AI-native dev scaffold plugin")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._claude()
        # Locate the Key terms section under Hot Cache
        idx = content.find("### Key terms")
        self.assertGreater(idx, 0, "missing Key terms section")
        section = content[idx:idx + 600]
        self.assertIn("jig", section)
        self.assertIn("the AI-native dev scaffold plugin", section)

    def test_promote_idempotent(self):
        run_memory(self.target, "promote", "ABC", "alpha bravo charlie")
        run_memory(self.target, "promote", "ABC", "alpha bravo charlie")
        # Only one entry
        c = self._claude()
        self.assertEqual(c.count("alpha bravo charlie"), 1)

    def test_promote_not_fooled_by_prose_mention(self):
        """Regression (reviewer-flagged): if an existing entry's prose mentions
        `- **FOO**`, promoting FOO must still write a real entry — the
        idempotency check is line-anchored."""
        # Promote a term whose definition references another marker-shaped phrase
        run_memory(self.target, "promote", "BAZ",
                   "see also - **FOO** for related context")
        # Now promote FOO — should succeed, not be falsely treated as already-present
        result = run_memory(self.target, "promote", "FOO", "the foo system")
        self.assertEqual(result.returncode, 0)
        self.assertIn("promoted", result.stdout.lower())
        # And the actual FOO entry should be in the file
        self.assertIn("the foo system", self._claude())

    # AC #1: summary command lists what's in memory
    def test_summary_lists_counts(self):
        run_memory(self.target, "add-term", "AAA", "first")
        run_memory(self.target, "add-learning", "BBB", "--body", "second")
        run_memory(self.target, "add-inbox", "CCC")
        result = run_memory(self.target, "summary")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        out = result.stdout
        self.assertIn("glossary", out.lower())
        self.assertIn("learnings", out.lower())
        self.assertIn("inbox", out.lower())
        # The counts should reflect at least the items just added
        self.assertRegex(out, r"glossary.*?\b1\b|\b1\b.*?glossary")


class SelfHealingTests(unittest.TestCase):
    """AC #6: memory.py creates docs/memory/ and docs/inbox.md if absent."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-heal-")
        self.target = Path(self.tmpdir) / "bare-project"
        self.target.mkdir()
        # Do NOT scaffold — we want a bare directory

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_memory_dir_if_missing(self):
        result = run_memory(self.target, "add-term", "X", "y")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue((self.target / "docs/memory/glossary.md").exists())

    def test_creates_inbox_md_if_missing(self):
        result = run_memory(self.target, "add-inbox", "first thing")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue((self.target / "docs/inbox.md").exists())

    def test_promote_warns_when_no_claude_md(self):
        result = run_memory(self.target, "promote", "X", "y")
        # Should still succeed (writing X to glossary as fallback)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # Stderr should mention the fallback
        combined = result.stderr.lower() + result.stdout.lower()
        self.assertTrue(
            "claude.md" in combined or "fallback" in combined,
            "expected a warning about missing CLAUDE.md",
        )


if __name__ == "__main__":
    unittest.main()
