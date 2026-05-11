"""
AC verification tests for slice 001-01 (greenfield-scaffold) and 001-02 (doc-content).

Run from the repo root:
    python3 -m unittest skills.scaffold-init.test_scaffold
or directly:
    python3 skills/scaffold-init/test_scaffold.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def run_scaffold(target: Path) -> subprocess.CompletedProcess:
    """Invoke scaffold.py against a target directory."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target)],
        capture_output=True,
        text=True,
        env=env,
    )


class GreenfieldScaffoldTests(unittest.TestCase):
    """Each test maps to one acceptance criterion."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-test-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        result = run_scaffold(self.target)
        self.assertEqual(
            result.returncode, 0,
            f"scaffold.py failed: stderr={result.stderr}\nstdout={result.stdout}"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #1: Full tree produced
    def test_creates_full_tree(self):
        expected = [
            "CLAUDE.md",
            "scaffold.json",
            ".claude/hooks",  # directory
            "docs/architecture.md",
            "docs/workflow.md",
            "docs/conventions.md",
            "docs/refinement-todo.md",
            "docs/inbox.md",
            "docs/memory/glossary.md",
            "docs/memory/learnings.md",
            "docs/memory/tooling.md",
            "docs/specs/README.md",
            "docs/adrs/README.md",
        ]
        for rel in expected:
            path = self.target / rel
            self.assertTrue(path.exists(), f"missing: {rel}")

    # AC #2: scaffold.json schema
    def test_scaffold_json_schema(self):
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertIn("jig_version", manifest)
        self.assertIn("timestamp", manifest)
        self.assertIn("installed_tiers", manifest)
        self.assertIsInstance(manifest["installed_tiers"], list)
        self.assertIn("tier-0", manifest["installed_tiers"])
        self.assertIn("tier-1", manifest["installed_tiers"])
        # Timestamp is ISO-8601 UTC
        self.assertRegex(manifest["timestamp"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    # AC #3: Draft markers — applies to ALL scaffolded .md files
    def test_draft_markers(self):
        marker = "Status: Draft (wizard-generated)"
        # CLAUDE.md + every .md under docs/
        md_files = [self.target / "CLAUDE.md"] + sorted(
            (self.target / "docs").rglob("*.md")
        )
        self.assertGreaterEqual(len(md_files), 9, "expected at least 9 scaffolded .md files")
        for path in md_files:
            content = path.read_text()
            rel = path.relative_to(self.target)
            self.assertIn(marker, content, f"missing draft marker in {rel}")

    # AC #4: Memory stubs seeded with meaningful starter content (per 001-02 AC #5)
    def test_memory_stubs(self):
        for name in ("glossary", "learnings", "tooling"):
            path = self.target / f"docs/memory/{name}.md"
            content = path.read_text()
            self.assertGreater(len(content), 200, f"{name}.md too thin to be meaningful")
            # Must include title heading
            self.assertRegex(content, rf"(?im)^#\s+{name}", f"missing # {name} heading")
            # Must explain how to use it (a usage block or format hint)
            self.assertRegex(
                content,
                r"(?i)(format|update via|how to use|<!--)",
                f"{name}.md lacks usage/format guidance",
            )
            # Must include the Status marker (from AC #3, but reinforced here)
            self.assertIn("Status: Draft", content)

    # AC #5: inbox.md header
    def test_inbox_header(self):
        inbox = (self.target / "docs/inbox.md").read_text()
        self.assertIn("Inbox", inbox)
        # Should explain its purpose
        self.assertTrue(
            "capture" in inbox.lower() or "parked" in inbox.lower(),
            "inbox.md should explain it's a capture/parking layer"
        )

    # AC #6: CLAUDE.md from template + Hot Cache + project name substituted
    def test_claude_md_hot_cache(self):
        claude_md = (self.target / "CLAUDE.md").read_text()
        self.assertIn("Hot Cache", claude_md)
        self.assertIn("demo-project", claude_md, "project name not substituted")
        # No raw template placeholders left
        self.assertNotIn("{{PROJECT_NAME}}", claude_md)

    # AC #7: No people.md (solo project default)
    def test_no_people_md(self):
        self.assertFalse(
            (self.target / "docs/memory/people.md").exists(),
            "people.md should not be created for solo projects in greenfield slice"
        )

    # AC #8: Spec-gate hook blocks edits to conventions.md without approval
    def test_conventions_gate_blocks(self):
        gate = REPO_ROOT / "hooks" / "scripts" / "jig-spec-gate.sh"
        self.assertTrue(gate.exists(), "spec-gate hook script missing")
        # Simulate a PreToolUse Edit on conventions.md without approval
        hook_input = json.dumps({
            "session_id": "test",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(self.target / "docs/conventions.md"),
            },
            "cwd": str(self.target),
        })
        env = os.environ.copy()
        env.pop("JIG_CONVENTIONS_APPROVED", None)  # ensure not approved
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 2, f"gate should block; got {result.returncode}, stderr={result.stderr}")
        self.assertIn("conventions.md", result.stderr.lower() + result.stdout.lower())

    def test_conventions_gate_allows_with_approval(self):
        gate = REPO_ROOT / "hooks" / "scripts" / "jig-spec-gate.sh"
        hook_input = json.dumps({
            "session_id": "test",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(self.target / "docs/conventions.md"),
            },
            "cwd": str(self.target),
        })
        env = os.environ.copy()
        env["JIG_CONVENTIONS_APPROVED"] = "1"
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, "gate should allow with approval")

    def test_conventions_gate_resists_path_traversal(self):
        """Regression: foo/docs/conventions.md/../conventions.md must still be gated."""
        gate = REPO_ROOT / "hooks" / "scripts" / "jig-spec-gate.sh"
        sneaky = str(self.target / "docs/conventions.md") + "/../conventions.md"
        hook_input = json.dumps({
            "session_id": "test",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": sneaky},
            "cwd": str(self.target),
        })
        env = os.environ.copy()
        env.pop("JIG_CONVENTIONS_APPROVED", None)
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 2, "gate should block path-traversal bypass")

    def test_conventions_gate_ignores_other_files(self):
        gate = REPO_ROOT / "hooks" / "scripts" / "jig-spec-gate.sh"
        hook_input = json.dumps({
            "session_id": "test",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(self.target / "docs/architecture.md"),
            },
            "cwd": str(self.target),
        })
        env = os.environ.copy()
        env.pop("JIG_CONVENTIONS_APPROVED", None)
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, "gate should ignore non-conventions files")


class DocContentTests(unittest.TestCase):
    """Slice 001-02 — content-shape requirements for scaffolded docs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-content-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #2 (001-02): workflow.md documents spec lifecycle AND hook strictness (deferred)
    def test_workflow_has_strictness_section(self):
        content = (self.target / "docs/workflow.md").read_text()
        self.assertIn("DRAFT", content)
        self.assertIn("DONE", content)
        # Locate the strictness section
        idx = re.search(r"(?im)^##\s+hook\s+strictness", content)
        self.assertIsNotNone(idx, "missing Hook Strictness section heading")
        section_start = idx.start()
        # Next H2 (or EOF) bounds the section
        next_h2 = re.search(r"(?m)^##\s+", content[section_start + 1:])
        section_end = (section_start + 1 + next_h2.start()) if next_h2 else len(content)
        section = content[section_start:section_end]
        # The Deferred marker must appear inside this section, not just anywhere
        self.assertIn("Deferred", section,
                      "Deferred marker missing from Hook Strictness section specifically")

    # AC #3 (001-02): conventions.md uses Rule → Why → How to apply format throughout
    def test_conventions_uses_format(self):
        content = (self.target / "docs/conventions.md").read_text()
        # Format markers appear in pairs — each rule has one Why and one How to apply
        why_count = content.count("**Why:**")
        how_count = content.count("**How to apply:**")
        self.assertGreaterEqual(why_count, 2, "expected ≥2 Why: markers")
        self.assertEqual(why_count, how_count,
                         f"Why/How mismatch: {why_count} Why vs {how_count} How")

    # AC #7 (001-02): CLAUDE.md Hot Cache codenames includes project name
    def test_claude_md_codename_includes_project_name(self):
        content = (self.target / "CLAUDE.md").read_text()
        # Locate the codenames section
        idx = content.find("### Project codenames")
        self.assertGreater(idx, 0, "missing codenames section")
        # The project name must appear within the next 300 chars (inside that section)
        codenames_block = content[idx:idx + 300]
        self.assertIn("demo-project", codenames_block,
                      "project name not present in codenames section")


def _git_available() -> bool:
    try:
        return subprocess.run(["git", "--version"], capture_output=True, timeout=3).returncode == 0
    except Exception:
        return False


@unittest.skipUnless(_git_available(), "git not available")
class TeamDetectionTests(unittest.TestCase):
    """Slice 001-02 — AC #8: people.md is only created on team projects."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-team-")
        self.target = Path(self.tmpdir) / "team-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _git(self, *args, env_extra=None):
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["git", "-C", str(self.target), *args],
            capture_output=True, text=True, env=env, check=True,
        )

    def _commit_as(self, name: str, email: str, filename: str):
        (self.target / filename).write_text("seed")
        self._git("add", filename)
        env = {
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        }
        self._git("commit", "-m", f"add {filename}", env_extra=env)

    def test_people_md_present_on_team_repo(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Bob", "bob@example.com", "b.txt")
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")
        people = self.target / "docs/memory/people.md"
        self.assertTrue(people.exists(), "people.md should exist when ≥2 git contributors")
        self.assertIn("Status: Draft (wizard-generated)", people.read_text())

    def test_people_md_absent_on_solo_repo(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Alice", "alice@example.com", "b.txt")
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")
        self.assertFalse(
            (self.target / "docs/memory/people.md").exists(),
            "people.md should be absent with only one contributor",
        )

    def test_people_md_absent_inside_parent_monorepo(self):
        """Regression: scaffolding a fresh subdir of a multi-author parent repo
        must not inherit the parent's contributor count."""
        # Initialize git at tmpdir root with two authors
        parent = Path(self.tmpdir)
        env = os.environ.copy()
        subprocess.run(["git", "-C", str(parent), "init", "-q"],
                       capture_output=True, env=env, check=True)
        for name, email, fn in [("Alice", "alice@x.com", "a.txt"),
                                 ("Bob", "bob@x.com", "b.txt")]:
            (parent / fn).write_text("x")
            subprocess.run(["git", "-C", str(parent), "add", fn],
                           capture_output=True, env=env, check=True)
            env_extra = {
                **env,
                "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
                "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
            }
            subprocess.run(["git", "-C", str(parent), "commit", "-q", "-m", fn],
                           capture_output=True, env=env_extra, check=True)
        # Now scaffold a SUBDIR of that repo — should be treated as solo
        sub = parent / "new-sub-project"
        sub.mkdir()
        result = run_scaffold(sub)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")
        self.assertFalse(
            (sub / "docs/memory/people.md").exists(),
            "people.md must not be created when target is a subdir of a parent repo",
        )

    def test_people_md_solo_with_mailmap_aliases(self):
        """Same person with two emails should still count as solo when mailmap maps them."""
        self._git("init", "-q")
        # Two commits, different emails, same person
        self._commit_as("Alice", "alice@work.com", "a.txt")
        self._commit_as("Alice", "alice@personal.com", "b.txt")
        # mailmap unifies them
        (self.target / ".mailmap").write_text(
            "Alice <alice@work.com> <alice@personal.com>\n"
        )
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")
        self.assertFalse(
            (self.target / "docs/memory/people.md").exists(),
            "people.md should be absent when mailmap unifies all authors to one",
        )

    def test_people_md_absent_when_no_git(self):
        # Don't run git init — target is a plain directory
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")
        self.assertFalse(
            (self.target / "docs/memory/people.md").exists(),
            "people.md should be absent when target is not a git repo",
        )


class ScaffoldSafetyTests(unittest.TestCase):
    """Reviewer-flagged safety behaviors that aren't tied to a single AC."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-safety-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_refuses_to_overwrite_existing_scaffold(self):
        first = run_scaffold(self.target)
        self.assertEqual(first.returncode, 0)
        second = run_scaffold(self.target)
        self.assertNotEqual(second.returncode, 0, "should refuse to overwrite")
        self.assertIn("already scaffolded", second.stderr.lower())

    def test_force_flag_allows_overwrite(self):
        first = run_scaffold(self.target)
        self.assertEqual(first.returncode, 0)
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        second = subprocess.run(
            [sys.executable, str(SCAFFOLD), "--force", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(second.returncode, 0, f"force should succeed: {second.stderr}")

    def test_unrendered_placeholder_fails_loud(self):
        """If a template introduces an unknown placeholder, scaffold must fail non-zero."""
        # Temporarily inject a bad template into a copy
        import shutil
        plugin_copy = Path(self.tmpdir) / "plugin"
        shutil.copytree(REPO_ROOT, plugin_copy, ignore=shutil.ignore_patterns(".git"))
        # Inject an unrendered placeholder
        bad = plugin_copy / "templates" / "docs" / "architecture.md.template"
        bad.write_text(bad.read_text() + "\n{{NEVER_SUBSTITUTED}}\n")
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(plugin_copy)
        result = subprocess.run(
            [sys.executable, str(plugin_copy / "skills" / "scaffold-init" / "scaffold.py"),
             str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertNotEqual(result.returncode, 0, "should fail on unrendered placeholders")
        self.assertIn("unrendered", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
