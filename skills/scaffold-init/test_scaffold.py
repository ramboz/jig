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
            "docs/decisions/README.md",
        ]
        for rel in expected:
            path = self.target / rel
            self.assertTrue(path.exists(), f"missing: {rel}")

    # AC #2 (001-01): scaffold.json schema.
    # Note: slice 001-03 made Tier 1 signal-gated. Bare empty dir → only tier-0.
    def test_scaffold_json_schema(self):
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertIn("jig_version", manifest)
        self.assertIn("timestamp", manifest)
        self.assertIn("installed_tiers", manifest)
        self.assertIsInstance(manifest["installed_tiers"], list)
        self.assertIn("tier-0", manifest["installed_tiers"])
        # Bare empty target — no test signals — so tier-1 should NOT be auto-installed
        self.assertNotIn("tier-1", manifest["installed_tiers"],
                         "bare empty dir has no test signals; tier-1 should not auto-install")
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


class SignalDetectionTests(unittest.TestCase):
    """Slice 001-03 — detector + tier selection + brief.md."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-signal-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _scaffold(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")

    def _manifest(self):
        return json.loads((self.target / "scaffold.json").read_text())

    # AC #5: bare repo produces no false positives
    def test_bare_repo_no_false_positives(self):
        self._scaffold()
        signals = self._manifest()["scaffold_signals"]
        self.assertFalse(signals["has_llm_agent_files"])
        self.assertFalse(signals["has_ci"])
        self.assertFalse(signals["has_tests"])
        self.assertEqual(self._manifest()["installed_tiers"], ["tier-0"])
        self.assertEqual(self._manifest()["hook_profile"], "standard")

    # AC #1: LLM/agent files → Tier 2 offered (recorded in scaffold_signals; brief.md mentions)
    def test_llm_agent_signals_record_offer(self):
        (self.target / "AGENTS.md").write_text("# Agents\n")
        self._scaffold()
        signals = self._manifest()["scaffold_signals"]
        self.assertTrue(signals["has_llm_agent_files"])
        # Tier 2 is offered, not auto-installed
        self.assertNotIn("tier-2", self._manifest()["installed_tiers"])
        brief = (self.target / "brief.md").read_text().lower()
        self.assertIn("tier 2", brief, "brief.md should mention Tier 2 offer")

    def test_llm_signal_via_cursor_dir(self):
        (self.target / ".cursor").mkdir()
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_llm_agent_files"])

    def test_llm_signal_via_prompt_md(self):
        (self.target / "user.prompt.md").write_text("test")
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_llm_agent_files"])

    def test_llm_signal_via_package_json_dep(self):
        (self.target / "package.json").write_text(json.dumps({
            "name": "x", "dependencies": {"anthropic": "^0.1"}
        }))
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_llm_agent_files"])

    def test_llm_signal_via_requirements_txt(self):
        (self.target / "requirements.txt").write_text("openai==1.0\nrequests\n")
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_llm_agent_files"])

    def test_llm_signal_not_triggered_by_pyproject_description_alone(self):
        """Regression: pyproject.toml that merely mentions openai in metadata
        (no actual dep) must not trigger LLM detection."""
        (self.target / "pyproject.toml").write_text(
            '[project]\n'
            'name = "my-pkg"\n'
            'description = "openai integration helper"\n'
            'dependencies = ["requests", "pyyaml"]\n'
        )
        self._scaffold()
        self.assertFalse(self._manifest()["scaffold_signals"]["has_llm_agent_files"],
                         "description-only mention must not count as LLM dependency")

    def test_llm_signal_via_pyproject_dep(self):
        """Companion: an actual pyproject dep DOES trigger."""
        (self.target / "pyproject.toml").write_text(
            '[project]\n'
            'name = "x"\n'
            'dependencies = ["anthropic>=0.5", "requests"]\n'
        )
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_llm_agent_files"])

    def test_llm_signal_excludes_claude_dir(self):
        """The spike deliberately excludes .claude/ as a signal — too ambiguous."""
        (self.target / ".claude").mkdir()
        self._scaffold()
        self.assertFalse(self._manifest()["scaffold_signals"]["has_llm_agent_files"])

    # AC #2: CI present → strict hook profile
    def test_ci_signals_set_strict_profile(self):
        (self.target / ".github" / "workflows").mkdir(parents=True)
        (self.target / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")
        self._scaffold()
        manifest = self._manifest()
        self.assertTrue(manifest["scaffold_signals"]["has_ci"])
        self.assertEqual(manifest["hook_profile"], "strict")

    def test_ci_signal_via_jenkinsfile(self):
        (self.target / "Jenkinsfile").write_text("pipeline {}\n")
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_ci"])

    def test_ci_signal_excludes_makefile(self):
        """The spike excludes Makefile targets — too noisy."""
        (self.target / "Makefile").write_text("test:\n\techo test\n")
        self._scaffold()
        self.assertFalse(self._manifest()["scaffold_signals"]["has_ci"])

    # AC #3: tests present → tier-1 auto-installed
    def test_test_signals_install_tier_1(self):
        (self.target / "pytest.ini").write_text("[pytest]\n")
        self._scaffold()
        manifest = self._manifest()
        self.assertTrue(manifest["scaffold_signals"]["has_tests"])
        self.assertIn("tier-1", manifest["installed_tiers"])

    def test_test_signal_via_vitest_in_package_json(self):
        (self.target / "package.json").write_text(json.dumps({
            "name": "x", "devDependencies": {"vitest": "^1.0"}
        }))
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_tests"])

    def test_test_signal_via_go_test_files(self):
        (self.target / "foo_test.go").write_text("package x\n")
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_tests"])

    def test_test_signal_via_conftest_py(self):
        (self.target / "conftest.py").write_text("# pytest config\n")
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_tests"])

    # AC #4: brief.md exists and summarizes
    def test_brief_md_exists_and_summarizes(self):
        # Multi-signal scaffold
        (self.target / "pytest.ini").write_text("[pytest]\n")
        (self.target / ".github" / "workflows").mkdir(parents=True)
        (self.target / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")
        (self.target / "AGENTS.md").write_text("# Agents\n")
        self._scaffold()
        brief = (self.target / "brief.md")
        self.assertTrue(brief.exists(), "brief.md must exist at project root")
        content = brief.read_text()
        # Brief should mention each detected signal category
        lowered = content.lower()
        self.assertIn("ci", lowered)
        self.assertIn("test", lowered)
        self.assertIn("agent", lowered)
        # And the project name
        self.assertIn("demo-project", content)
        # And carry the Status marker
        self.assertIn("Status: Draft", content)


def run_scaffold_with_args(target: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke scaffold.py with extra CLI flags before the target path."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), *args, str(target)],
        capture_output=True, text=True, env=env,
    )


class WizardQATests(unittest.TestCase):
    """Slice 001-05 — CLI flag overrides for Q&A wizard answers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-qa-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _manifest(self):
        return json.loads((self.target / "scaffold.json").read_text())

    # 1. Runtime flag is recorded in scaffold.json
    def test_runtime_flag_recorded(self):
        result = run_scaffold_with_args(self.target, "--runtime", "python")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertEqual(self._manifest().get("project_runtime"), "python")

    def test_runtime_absent_when_unset(self):
        result = run_scaffold_with_args(self.target)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("project_runtime", self._manifest(),
                         "project_runtime should be absent when --runtime unset")

    # 2. Team / solo flag overrides detect_team
    def test_team_flag_forces_people_md_on_solo_dir(self):
        result = run_scaffold_with_args(self.target, "--team")
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.target / "docs/memory/people.md").exists(),
                        "--team should force people.md even without ≥2 git authors")
        self.assertTrue(self._manifest()["scaffold_signals"]["is_team"])

    @unittest.skipUnless(_git_available(), "git not available")
    def test_solo_flag_suppresses_people_md_on_team_repo(self):
        # Build a team git repo, then scaffold with --solo
        env = os.environ.copy()
        subprocess.run(["git", "-C", str(self.target), "init", "-q"],
                       capture_output=True, env=env, check=True)
        for name, email, fn in [("Alice", "alice@x.com", "a.txt"),
                                 ("Bob", "bob@x.com", "b.txt")]:
            (self.target / fn).write_text("x")
            subprocess.run(["git", "-C", str(self.target), "add", fn],
                           capture_output=True, env=env, check=True)
            env_extra = {
                **env,
                "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
                "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
            }
            subprocess.run(["git", "-C", str(self.target), "commit", "-q", "-m", fn],
                           capture_output=True, env=env_extra, check=True)
        result = run_scaffold_with_args(self.target, "--solo")
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.target / "docs/memory/people.md").exists(),
                         "--solo should suppress people.md even on multi-author git repo")
        self.assertFalse(self._manifest()["scaffold_signals"]["is_team"])

    # 3. CI flag overrides _detect_ci
    def test_has_ci_flag_sets_strict_profile(self):
        result = run_scaffold_with_args(self.target, "--has-ci")
        self.assertEqual(result.returncode, 0)
        manifest = self._manifest()
        self.assertTrue(manifest["scaffold_signals"]["has_ci"])
        self.assertEqual(manifest["hook_profile"], "strict")

    def test_no_ci_flag_overrides_filesystem(self):
        # Real CI files present
        (self.target / ".github" / "workflows").mkdir(parents=True)
        (self.target / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")
        result = run_scaffold_with_args(self.target, "--no-ci")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self._manifest()["scaffold_signals"]["has_ci"])
        self.assertEqual(self._manifest()["hook_profile"], "standard")

    # 4. Tests flag overrides _detect_tests + tier-1 install
    def test_has_tests_flag_forces_tier_1(self):
        result = run_scaffold_with_args(self.target, "--has-tests")
        self.assertEqual(result.returncode, 0)
        manifest = self._manifest()
        self.assertTrue(manifest["scaffold_signals"]["has_tests"])
        self.assertIn("tier-1", manifest["installed_tiers"])

    def test_no_tests_flag_overrides_filesystem(self):
        # Real pytest.ini present
        (self.target / "pytest.ini").write_text("[pytest]\n")
        result = run_scaffold_with_args(self.target, "--no-tests")
        self.assertEqual(result.returncode, 0)
        manifest = self._manifest()
        self.assertFalse(manifest["scaffold_signals"]["has_tests"])
        self.assertNotIn("tier-1", manifest["installed_tiers"])

    # 5. AI flag overrides _detect_llm_agent + tier-2 offer
    def test_plans_ai_flag_offers_tier_2(self):
        result = run_scaffold_with_args(self.target, "--plans-ai")
        self.assertEqual(result.returncode, 0)
        manifest = self._manifest()
        self.assertTrue(manifest["scaffold_signals"]["has_llm_agent_files"])
        self.assertIn("tier-2", manifest.get("offered_tiers", []))

    def test_no_ai_flag_overrides_filesystem(self):
        # Real LLM signal present
        (self.target / "AGENTS.md").write_text("# Agents\n")
        result = run_scaffold_with_args(self.target, "--no-ai")
        self.assertEqual(result.returncode, 0)
        manifest = self._manifest()
        self.assertFalse(manifest["scaffold_signals"]["has_llm_agent_files"])
        self.assertNotIn("tier-2", manifest.get("offered_tiers", []))

    # Skip semantics: no flags = pure inference (slice 001-03 behavior)
    def test_no_flags_matches_inference_baseline(self):
        # Multi-signal scaffold
        (self.target / "pytest.ini").write_text("[pytest]\n")
        (self.target / "AGENTS.md").write_text("# Agents\n")
        result = run_scaffold_with_args(self.target)
        self.assertEqual(result.returncode, 0)
        signals = self._manifest()["scaffold_signals"]
        # All signals match what filesystem inference produces (verified by 001-03 tests)
        self.assertTrue(signals["has_tests"])
        self.assertTrue(signals["has_llm_agent_files"])
        self.assertFalse(signals["has_ci"])
        self.assertFalse(signals["is_team"])

    # Mutually exclusive flag pairs
    def test_team_and_solo_are_mutually_exclusive(self):
        result = run_scaffold_with_args(self.target, "--team", "--solo")
        self.assertNotEqual(result.returncode, 0,
                            "should reject --team and --solo together")

    def test_has_ci_and_no_ci_are_mutually_exclusive(self):
        result = run_scaffold_with_args(self.target, "--has-ci", "--no-ci")
        self.assertNotEqual(result.returncode, 0)

    def test_has_tests_and_no_tests_are_mutually_exclusive(self):
        result = run_scaffold_with_args(self.target, "--has-tests", "--no-tests")
        self.assertNotEqual(result.returncode, 0)

    def test_plans_ai_and_no_ai_are_mutually_exclusive(self):
        result = run_scaffold_with_args(self.target, "--plans-ai", "--no-ai")
        self.assertNotEqual(result.returncode, 0)


class FormatComplianceTests(unittest.TestCase):
    """Slice 001-04 ACs #1 + #2 — refinement-todo.md format and categories."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-fmt-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")
        self.todo = (self.target / "docs/refinement-todo.md").read_text()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #2: 3 categories
    def test_refinement_todo_has_three_categories(self):
        for category in ("Architecture", "Conventions", "Operations"):
            self.assertRegex(
                self.todo, rf"(?m)^##\s+{category}\b",
                f"missing top-level category: {category}",
            )

    # AC #1: each entry has consistent format
    def test_refinement_todo_format_compliance(self):
        """Each '### Decision: ...' heading must be followed (within its section)
        by a '**Deferred:**' line and a '**Resolution trigger:**' line."""
        # Find decision headings and their bodies (up to next ### or ##)
        chunks = re.split(r"(?m)^### Decision: ", self.todo)
        # chunks[0] is preamble before the first decision; ignore
        decisions = chunks[1:]
        self.assertGreaterEqual(len(decisions), 3, "expected ≥3 deferred decisions")
        for chunk in decisions:
            # name appears on first line
            name = chunk.splitlines()[0].strip()
            self.assertTrue(name, "decision name empty")
            # body extends until next heading or end of file
            body = re.split(r"(?m)^(?:##|###)\s", chunk, maxsplit=1)[0]
            self.assertIn("**Deferred:**", body,
                          f"decision '{name}' missing **Deferred:**")
            self.assertIn("**Resolution trigger:**", body,
                          f"decision '{name}' missing **Resolution trigger:**")

    def test_each_category_has_at_least_one_decision(self):
        for category in ("Architecture", "Conventions", "Operations"):
            # Find the category section and look for at least one ### Decision: inside it
            m = re.search(rf"(?ms)^##\s+{category}\b(.*?)(?=^##\s|\Z)", self.todo)
            self.assertIsNotNone(m, f"category {category} not found")
            self.assertRegex(
                m.group(1), r"(?m)^### Decision:",
                f"category {category} has no decisions",
            )


REPO_ROOT_STR = str(REPO_ROOT)
STOCKTAKE = REPO_ROOT / "skills" / "scaffold-init" / "stocktake.py"


def run_stocktake(target: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = REPO_ROOT_STR
    return subprocess.run(
        [sys.executable, str(STOCKTAKE), str(target)],
        capture_output=True, text=True, env=env,
    )


class StocktakeTests(unittest.TestCase):
    """Slice 001-04 AC #3 — stocktake counts reconciled slices and suggests promotion at ≥3."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-stock-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"scaffold failed: {result.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_slice(self, spec_dir_name: str, slice_name: str, status: str):
        """Append a slice with the given status into an existing or new spec.md."""
        spec_dir = self.target / "docs" / "specs" / spec_dir_name
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        existing = spec_md.read_text() if spec_md.exists() else f"# Spec {spec_dir_name}\n\n"
        existing += f"\n## Slice {slice_name}\n\n**STATUS: {status}**\n\n"
        spec_md.write_text(existing)

    def test_stocktake_runs_on_fresh_scaffold(self):
        result = run_stocktake(self.target)
        self.assertEqual(result.returncode, 0, f"stderr={result.stderr}")
        out = result.stdout
        self.assertIn("Stocktake", out)
        # Fresh scaffold has 0 reconciled slices and ≥3 deferred items (from template)
        self.assertIn("0", out, "expected slice count of 0 shown in report")
        # Should NOT contain the promotion suggestion
        self.assertNotIn("promote", out.lower(),
                         "should not suggest promotion below threshold")

    def test_stocktake_silent_below_threshold(self):
        # Two reconciled slices — below the 3-threshold
        self._make_slice("001-x", "001-01 alpha", "DONE")
        self._make_slice("001-x", "001-02 beta", "RECONCILED")
        result = run_stocktake(self.target)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("promote", result.stdout.lower())

    def test_stocktake_suggests_at_threshold(self):
        # Three reconciled slices — should surface the suggestion
        self._make_slice("001-x", "001-01 alpha", "DONE")
        self._make_slice("001-x", "001-02 beta", "RECONCILED")
        self._make_slice("002-y", "002-01 gamma", "DONE")
        result = run_stocktake(self.target)
        self.assertEqual(result.returncode, 0)
        self.assertIn("promote", result.stdout.lower())
        # Should mention specific deferred items by name
        self.assertRegex(result.stdout, r"(?i)tech\s+stack|module\s+boundaries")

    def test_stocktake_reports_deferred_items(self):
        result = run_stocktake(self.target)
        self.assertEqual(result.returncode, 0)
        # Should enumerate at least the seeded deferred items
        out = result.stdout
        # The template has at least Architecture / Conventions / Operations sections
        # and several decisions in each
        self.assertGreaterEqual(out.lower().count("decision"), 3,
                                "expected ≥3 deferred decisions enumerated")

    def test_stocktake_handles_missing_refinement_todo(self):
        # Delete the file and verify graceful behavior
        (self.target / "docs/refinement-todo.md").unlink()
        result = run_stocktake(self.target)
        self.assertEqual(result.returncode, 0, f"stderr={result.stderr}")
        self.assertIn("0 deferred", result.stdout.lower())


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


# ==========================================================================
# Slice 008-05 — scaffold-init --migrate suggestion tests
# ==========================================================================


def _make_spec_driven_tree(root: Path, triggers: list) -> None:
    """Build a synthetic spec-driven project tree under `root`.

    Each entry in `triggers` is one of the four trigger names: 'specs',
    'slices', 'decisions', 'adrs', 'workflow', 'architecture'. Note: 'specs'
    and 'slices' both satisfy the spec-or-slice trigger; 'decisions' and
    'adrs' both satisfy the decisions-or-adr trigger. The caller controls
    exactly which the fixture exercises."""
    (root / "docs").mkdir(parents=True, exist_ok=True)
    for t in triggers:
        if t == "specs":
            (root / "docs" / "specs" / "001-sample").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "specs" / "001-sample" / "spec.md").write_text("# Sample\n")
        elif t == "slices":
            (root / "docs" / "slices").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "slices" / "slice-01-sample.md").write_text("# Slice\n")
        elif t == "decisions":
            (root / "docs" / "decisions").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "decisions" / "adr-0001-sample.md").write_text("# adr\n")
        elif t == "adrs":
            (root / "docs" / "adrs").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "adrs" / "0001-sample.md").write_text("# adr\n")
        elif t == "workflow":
            (root / "docs" / "workflow.md").write_text("# Workflow\n")
        elif t == "architecture":
            (root / "docs" / "architecture.md").write_text("# Architecture\n")
        else:
            raise ValueError(f"unknown trigger: {t}")


class LooksAlreadySpecDrivenTests(unittest.TestCase):
    """Slice 008-05 — scaffold-init refuses on spec-driven layout and
    routes to /jig:migrate."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-008-05-")
        self.target = Path(self.tmpdir) / "preexisting-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_three_triggers_refuses_and_suggests_migrate(self):
        _make_spec_driven_tree(self.target,
                               ["specs", "decisions", "workflow"])
        r = run_scaffold(self.target)
        self.assertNotEqual(r.returncode, 0,
                            "should refuse on spec-driven layout")
        self.assertIn("migrate", r.stderr.lower())
        # Suggestion text must name the report command and the skill.
        self.assertIn("migrate.py report", r.stderr)
        self.assertIn("/jig:migrate", r.stderr)
        # Triggers found must be named in the message.
        for name in ("docs/specs", "docs/decisions", "docs/workflow.md"):
            self.assertIn(name, r.stderr,
                          f"trigger path missing from message: {name}")

    def test_four_triggers_refuses_with_full_list(self):
        _make_spec_driven_tree(self.target,
                               ["slices", "adrs", "workflow", "architecture"])
        r = run_scaffold(self.target)
        self.assertNotEqual(r.returncode, 0)
        for name in ("docs/slices", "docs/adrs", "docs/workflow.md",
                     "docs/architecture.md"):
            self.assertIn(name, r.stderr)

    def test_two_triggers_does_not_refuse(self):
        _make_spec_driven_tree(self.target, ["workflow", "architecture"])
        r = run_scaffold(self.target)
        # Two triggers is NOT enough — scaffold should proceed.
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        # And scaffold.json should now exist.
        self.assertTrue((self.target / "scaffold.json").is_file())

    def test_scaffold_json_takes_precedence_over_spec_driven_check(self):
        """If both scaffold.json AND 3+ triggers are present, the existing
        AlreadyScaffoldedError fires (not the new error). Tests the ordering
        invariant from AC #3."""
        # First, do a normal scaffold (which creates scaffold.json + the
        # canonical structure that has 3+ triggers naturally).
        r1 = run_scaffold(self.target)
        self.assertEqual(r1.returncode, 0)
        self.assertTrue((self.target / "scaffold.json").is_file())
        # Second invocation should refuse with the OLD message (scaffold.json
        # case), not the new spec-driven-shape message.
        r2 = run_scaffold(self.target)
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("already scaffolded", r2.stderr.lower())
        # And must NOT use the new error's specific routing text.
        self.assertNotIn("/jig:migrate", r2.stderr)

    def test_force_bypasses_spec_driven_check(self):
        _make_spec_driven_tree(self.target,
                               ["specs", "decisions", "workflow", "architecture"])
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        r = subprocess.run(
            [sys.executable, str(SCAFFOLD), "--force", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0,
                         f"--force should bypass the new check: {r.stderr}")
        # Greenfield output is present.
        self.assertTrue((self.target / "scaffold.json").is_file())
        self.assertTrue((self.target / "CLAUDE.md").is_file())

    @classmethod
    def _load_scaffold_module(cls):
        """Load scaffold.py as a module for direct symbol access. Cached
        on the class so the two unit tests below share one import."""
        if getattr(cls, "_scaffold_mod", None) is None:
            import importlib.util
            spec = importlib.util.spec_from_file_location("scaffold", SCAFFOLD)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls._scaffold_mod = mod
        return cls._scaffold_mod

    def test_detection_function_unit_each_single_trigger_insufficient(self):
        """Unit-level: any single trigger alone does NOT trip the heuristic."""
        mod = self._load_scaffold_module()
        for t in ("specs", "slices", "decisions", "adrs",
                  "workflow", "architecture"):
            d = Path(tempfile.mkdtemp(prefix=f"jig-08-05-unit-{t}-"))
            try:
                _make_spec_driven_tree(d, [t])
                triggered, triggers = mod._looks_already_spec_driven(d)
                self.assertFalse(triggered,
                                 f"single trigger '{t}' should not trip: got {triggers}")
                self.assertEqual(len(triggers), 1,
                                 f"trigger '{t}' should produce one entry: {triggers}")
            finally:
                import shutil
                shutil.rmtree(d, ignore_errors=True)

    def test_detection_function_unit_three_triggers_trips(self):
        mod = self._load_scaffold_module()
        d = Path(tempfile.mkdtemp(prefix="jig-08-05-unit-3-"))
        try:
            _make_spec_driven_tree(d, ["specs", "decisions", "workflow"])
            triggered, triggers = mod._looks_already_spec_driven(d)
            self.assertTrue(triggered)
            self.assertEqual(len(triggers), 3)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
