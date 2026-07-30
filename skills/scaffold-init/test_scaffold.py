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
            "docs/bugs/README.md",
            "docs/decisions/README.md",
            "docs/decisions/lightweight-decisions.md",  # spec 083-02
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

    # ADR-0007: per-skill install list lives alongside installed_tiers
    def test_scaffold_json_has_installed_skills(self):
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertIn("installed_skills", manifest,
                      "ADR-0007: scaffold.json must include installed_skills")
        self.assertIsInstance(manifest["installed_skills"], list)
        # Every entry follows the `<tier>/<skill>` shape.
        for entry in manifest["installed_skills"]:
            self.assertRegex(
                entry, r"^tier-[012]/[a-z][a-z0-9-]*$",
                f"installed_skills entry has wrong shape: {entry!r}",
            )

    def test_installed_skills_invariant_with_tiers(self):
        """ADR-0007 invariant — the set of tiers derived from
        installed_skills equals the installed_tiers set."""
        manifest = json.loads((self.target / "scaffold.json").read_text())
        derived = {s.split("/")[0] for s in manifest["installed_skills"]}
        self.assertEqual(
            derived, set(manifest["installed_tiers"]),
            f"derived tiers {derived} != installed_tiers "
            f"{set(manifest['installed_tiers'])}",
        )

    def test_installed_skills_includes_expected_tier0_skills(self):
        """Bare empty dir → only tier-0 skills. The per-skill list must
        name the canonical Tier 0 set."""
        manifest = json.loads((self.target / "scaffold.json").read_text())
        expected = {
            "tier-0/scaffold-init",
            "tier-0/memory-sync",
            "tier-0/spec-workflow",
            "tier-0/independent-review",
            "tier-0/migrate",
        }
        actual = set(manifest["installed_skills"])
        missing = expected - actual
        self.assertFalse(
            missing,
            f"installed_skills missing canonical Tier 0 entries: {missing}",
        )
        # No tier-1 entries (no test signals).
        tier1_entries = [s for s in actual if s.startswith("tier-1/")]
        self.assertEqual(
            tier1_entries, [],
            f"bare empty dir produced tier-1 entries: {tier1_entries}",
        )

    # AC #3: Draft markers — applies to ALL scaffolded .md files
    def test_draft_markers(self):
        marker = "Status: Draft (wizard-generated)"
        # CLAUDE.md + every .md under docs/, EXCEPT the seeded reference
        # spec (slice 048-05). The seed's 001-adopt-jig is real, permanent
        # project history at status: DONE, and its 002-first-spec stub is a
        # status: DRAFT spec — neither carries the "wizard-generated" doc
        # marker by design (the honesty pin in 048-05 AC #2 forbids dressing
        # the DONE worked example up as a draft).
        seed_dirs = {"001-adopt-jig", "002-first-spec"}
        md_files = [self.target / "CLAUDE.md"] + sorted(
            p for p in (self.target / "docs").rglob("*.md")
            if not (seed_dirs & set(p.relative_to(self.target).parts))
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
        self.assertIn("docs/bugs/README.md", claude_md)
        # No raw template placeholders left
        self.assertNotIn("{{PROJECT_NAME}}", claude_md)

    def test_bug_board_links_spec_board(self):
        bug_board = (self.target / "docs/bugs/README.md").read_text()
        self.assertIn("../specs/README.md", bug_board)
        self.assertIn("Spec Status Board", bug_board)

    def test_claude_phase_mode_guidance_is_host_native(self):
        claude_md = (self.target / "CLAUDE.md").read_text()
        workflow = (self.target / "docs/workflow.md").read_text()

        self.assertIn("Claude Code plan mode", claude_md)
        self.assertIn("normal edit mode", claude_md)
        self.assertIn("jig specs, slices, and review artifacts", claude_md)
        self.assertIn("## Phase-Mode Guidance", workflow)
        self.assertIn("Claude Code plan mode", workflow)
        self.assertIn("normal edit mode", workflow)
        self.assertIn("Host-native modes are advisory", workflow)
        self.assertIn("never replace", workflow)
        self.assertNotIn("Codex Plan mode", claude_md)
        self.assertNotIn("Default mode", workflow)

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
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
        env.pop("JIG_CONVENTIONS_APPROVED", None)  # ensure not approved
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 2,
                         f"gate should block; got {result.returncode}, stderr={result.stderr}")
        self.assertIn("conventions.md", result.stderr.lower() + result.stdout.lower())
        # Spec 078-01 AC3: the normal (blocked) path emits no bypass event.
        self.assertEqual(self._read_gate_bypass_events(), [])

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
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
        env["JIG_CONVENTIONS_APPROVED"] = "1"
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, "gate should allow with approval")
        # Spec 078-01 AC2: the bypass emits one content-free event.
        events = self._read_gate_bypass_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["gate"], "conventions")
        self.assertEqual(events[0]["env_var"], "JIG_CONVENTIONS_APPROVED")
        self.assertNotIn("conventions.md", json.dumps(events[0]))

    def test_conventions_gate_bypass_telemetry_fails_open(self):
        """Spec 078-01 AC4: an unwritable telemetry sink must not block the
        edit — make .claude/skill-usage.jsonl a directory so the write raises,
        and confirm the gate still allows."""
        gate = REPO_ROOT / "hooks" / "scripts" / "jig-spec-gate.sh"
        log_dir = self.target / ".claude"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "skill-usage.jsonl").mkdir()
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
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
        env["JIG_CONVENTIONS_APPROVED"] = "1"
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0,
                         f"gate must still allow when telemetry sink is "
                         f"unwritable; stderr={result.stderr}")

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
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
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
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
        env.pop("JIG_CONVENTIONS_APPROVED", None)
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, "gate should ignore non-conventions files")
        # Spec 078-01 AC3: the normal (ungated-file) path emits no bypass event.
        self.assertEqual(self._read_gate_bypass_events(), [])

    def test_conventions_gate_approval_on_other_file_emits_nothing(self):
        """Spec 078-01 AC3 (emit-scoping): an approval token present while
        editing an UNRELATED file must not fire the gate's bypass telemetry
        — emit is scoped to the actual gated file, not to the env var alone."""
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
        env["CLAUDE_PROJECT_DIR"] = str(self.target)
        env["JIG_CONVENTIONS_APPROVED"] = "1"
        result = subprocess.run(
            ["bash", str(gate)],
            input=hook_input,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._read_gate_bypass_events(), [])

    def _read_gate_bypass_events(self):
        log = self.target / ".claude" / "skill-usage.jsonl"
        if not log.is_file():
            return []
        return [
            json.loads(line) for line in log.read_text().splitlines()
            if line.strip()
        ]


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

    def test_workflow_routes_feedback_against_bug_registry(self):
        content = (self.target / "docs/workflow.md").read_text()
        self.assertIn("docs/bugs/README.md", content)
        self.assertIn("feedback/triage", content)
        self.assertIn("bug-fix", content)


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


def _load_scaffold_module():
    """Load scaffold.py as a module for in-process helper tests (the dir
    name has a hyphen, so a plain `import` won't work)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("jig_scaffold_for_test", SCAFFOLD)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(_git_available(), "git not available")
class CountTeamContributorsParityTests(unittest.TestCase):
    """Slice 050-01 AC6 — `count_team_contributors` (int) and `detect_team`
    (bool) must agree on the ≥2 threshold across the fixture matrix. The
    threshold lives in exactly one place.

    Slice 050-02 (ADR-0002 rule-of-three) moved the count + threshold into
    `_common.team_signal`. scaffold's `count_team_contributors` is now a
    re-export of that single source of truth (asserted by
    `test_count_is_common_reexport`), and `detect_team` delegates to it; this
    matrix pins that the re-exported behavior is unchanged."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-count-")
        self.target = Path(self.tmpdir) / "proj"
        self.target.mkdir()
        self.mod = _load_scaffold_module()
        sys.path.insert(0, str(REPO_ROOT / "skills"))
        from _common import team_signal
        self.team_signal = team_signal

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

    def _commit_as(self, name, email, filename):
        (self.target / filename).write_text("seed")
        self._git("add", filename)
        env = {
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        }
        self._git("commit", "-m", f"add {filename}", env_extra=env)

    def _assert_parity(self, expected_count):
        # Target the _common helper directly — it is the single source of
        # truth post-extraction (slice 050-02).
        count = self.team_signal.count_team_contributors(self.target)
        verdict = self.mod.detect_team(self.target)
        self.assertEqual(count, expected_count,
                         f"count_team_contributors should be {expected_count}")
        self.assertEqual(verdict, count >= self.team_signal.TEAM_THRESHOLD,
                         "detect_team must equal (count >= TEAM_THRESHOLD)")

    def test_count_is_common_reexport(self):
        """scaffold.count_team_contributors must BE the _common function —
        a single source of truth, not a divergent copy (ADR-0002)."""
        self.assertIs(self.mod.count_team_contributors,
                      self.team_signal.count_team_contributors)

    def test_parity_solo(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Alice", "alice@example.com", "b.txt")
        self._assert_parity(1)

    def test_parity_team_2(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Bob", "bob@example.com", "b.txt")
        self._assert_parity(2)

    def test_parity_team_3(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Bob", "bob@example.com", "b.txt")
        self._commit_as("Carol", "carol@example.com", "c.txt")
        self._assert_parity(3)

    def test_parity_mailmap_coalesced(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@work.com", "a.txt")
        self._commit_as("Alice", "alice@personal.com", "b.txt")
        (self.target / ".mailmap").write_text(
            "Alice <alice@work.com> <alice@personal.com>\n"
        )
        self._assert_parity(1)

    def test_parity_monorepo_parent(self):
        """Target is a SUBDIR of a multi-author parent repo → guarded to 0
        (solo), so count and detect_team must both reflect the guard."""
        parent = Path(self.tmpdir)
        env = os.environ.copy()
        subprocess.run(["git", "-C", str(parent), "init", "-q"],
                       capture_output=True, env=env, check=True)
        for name, email, fn in [("Alice", "alice@x.com", "pa.txt"),
                                 ("Bob", "bob@x.com", "pb.txt")]:
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
        # self.target is a subdir of parent (not its own repo root)
        self._assert_parity(0)

    def test_parity_non_git(self):
        # No git init at all — both helpers fail-soft.
        self._assert_parity(0)


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
        # ADR-0007 — per-skill list should ALSO carry tier-1 entries
        tier1_skills = [s for s in manifest["installed_skills"]
                        if s.startswith("tier-1/")]
        self.assertTrue(
            tier1_skills,
            "tier-1 in installed_tiers but no tier-1/* in installed_skills",
        )
        # And one named tier-1 skill should be present
        self.assertIn("tier-1/tdd-loop", manifest["installed_skills"])

    def test_test_signal_via_vitest_in_package_json(self):
        (self.target / "package.json").write_text(json.dumps({
            "name": "x", "devDependencies": {"vitest": "^1.0"}
        }))
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_tests"])

    def test_test_signal_via_node_test_script(self):
        (self.target / "package.json").write_text(json.dumps({
            "name": "x", "scripts": {"test": "node --test"}
        }))
        self._scaffold()
        self.assertTrue(self._manifest()["scaffold_signals"]["has_tests"])

    def test_test_signal_via_node_test_import(self):
        (self.target / "test" / "sample.test.mjs").parent.mkdir()
        (self.target / "test" / "sample.test.mjs").write_text(
            "import { test } from 'node:test';\n"
            "test('works', () => {});\n"
        )
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

    # Slice 050-01 — explicit --solo writes a tracked opt-out marker so
    # memory-sync's team-recheck never re-nudges a deliberate solo project.
    def test_solo_flag_writes_no_people_md_marker(self):
        result = run_scaffold_with_args(self.target, "--solo")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        marker = self.target / ".jig" / "no-people-md"
        self.assertTrue(marker.exists(),
                        "--solo must write the .jig/no-people-md opt-out marker")

    # Slice 050-01 — auto-detected solo (no --solo flag) must NOT write the
    # marker, or a solo-scaffolded project that later grows is permanently
    # suppressed (defeating spec 050).
    def test_auto_solo_does_not_write_marker(self):
        # bare dir → inferred solo, no explicit override
        result = run_scaffold_with_args(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        marker = self.target / ".jig" / "no-people-md"
        self.assertFalse(marker.exists(),
                         "auto-detected solo must NOT write the opt-out marker")
        # marker must not be gitignored — it is a tracked project-level opt-out
        gitignore = self.target / ".gitignore"
        if gitignore.exists():
            self.assertNotIn("no-people-md", gitignore.read_text(),
                             "the marker is tracked; must not be in .gitignore")

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
            sys.modules[spec.name] = mod
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


class VisionTemplateSlotsTests(unittest.TestCase):
    """AC verification tests for slice 017-01 (vision-template-and-architecture-slots).

    These tests pin the *template* shape — the named-but-empty slots that
    `scaffold-init` produces, before the elicitation skill (017-02) exists.
    The skill that fills the slots is out of scope for 017-01.
    """

    # Slice 068-01 added "## Use cases" (after Scope) — the breadth-layer
    # capture section (ADR-0025). Count is now 10.
    EXPECTED_VISION_SECTIONS = [
        "Identity",
        "Target users",
        "Core problem",
        "Competitive landscape",
        "Scope",
        "Use cases",
        "Stack",
        "Design principles & constraints",
        "How new work enters",
        "Open questions",
    ]

    UNFILLED_MARKER = "<!-- elicited: PENDING / status: unfilled -->"

    # Slice 017-01 reshape: architecture.md.template now has 4 elicitation
    # slots (was 3 Deferred stanzas). "What this project does" was removed —
    # product-vision.md owns that question, and the template has a top-of-doc
    # pointer to it instead. Two new slots — Repository structure and Data
    # model — were added based on the proven structure of jig's own
    # docs/architecture.md.
    EXPECTED_ARCH_STANZAS = [
        "Repository structure",
        "Tech stack",
        "Module boundaries",
        "Data model",
        # Added by spec 022-02: Contract surfaces feeds the
        # `/jig:contracts` reviewer-prompt and `/jig:migrate report`
        # integrations. Marker shape identical to the original four.
        "Contract surfaces",
    ]
    # Two sections exist but are NOT elicitation slots — they carry no marker.
    # "Core architecture decisions" is populated incrementally by ADRs over
    # time, not a single-shot elicitation. "Open questions" is a footer that
    # points to refinement-todo.md.
    EXPECTED_ARCH_NON_MARKER_SECTIONS = [
        "Core architecture decisions",
        "Open questions",
    ]

    def _read(self, rel: str) -> str:
        return (REPO_ROOT / rel).read_text(encoding="utf-8")

    # AC #1
    def test_product_vision_template_exists(self):
        path = REPO_ROOT / "templates" / "docs" / "product-vision.md.template"
        self.assertTrue(
            path.exists(),
            "templates/docs/product-vision.md.template must exist (slice 017-01 AC #1)",
        )

    # AC #2: 10 H2 sections in exact order (9 from slice 017-01 +
    # "Use cases" added by slice 068-01).
    def test_product_vision_template_has_9_sections_in_order(self):
        body = self._read("templates/docs/product-vision.md.template")
        # match `## <heading>` but not deeper headings
        headings = re.findall(r"^## (.+)$", body, flags=re.MULTILINE)
        self.assertEqual(
            headings,
            self.EXPECTED_VISION_SECTIONS,
            f"product-vision.md.template H2 sections must be exactly "
            f"{self.EXPECTED_VISION_SECTIONS}, got {headings}",
        )

    # AC #3: each H2 section starts with the unfilled marker
    def test_product_vision_template_each_section_has_unfilled_marker(self):
        body = self._read("templates/docs/product-vision.md.template")
        # split by `## ` heading; first chunk is preamble, rest are sections
        chunks = re.split(r"^## ", body, flags=re.MULTILINE)[1:]
        self.assertEqual(
            len(chunks), 10,
            f"expected 10 sections, got {len(chunks)}",
        )
        for chunk in chunks:
            heading_line, _, rest = chunk.partition("\n")
            # first non-blank line after the heading must be the unfilled marker
            stripped = rest.lstrip("\n")
            first_line = stripped.split("\n", 1)[0]
            self.assertEqual(
                first_line.strip(),
                self.UNFILLED_MARKER,
                f"section '## {heading_line}' must start with "
                f"'{self.UNFILLED_MARKER}', got '{first_line}'",
            )

    # AC #4: architecture.md.template's four elicitation slots have markers
    def test_architecture_template_four_slots_have_unfilled_markers(self):
        body = self._read("templates/docs/architecture.md.template")
        for stanza in self.EXPECTED_ARCH_STANZAS:
            # Each elicitation slot heading is followed by the unfilled marker
            # on the line immediately after (blank lines tolerated).
            pattern = re.compile(
                rf"^## {re.escape(stanza)}\s*\n+{re.escape(self.UNFILLED_MARKER)}",
                flags=re.MULTILINE,
            )
            self.assertRegex(
                body, pattern,
                f"slot '## {stanza}' must have '{self.UNFILLED_MARKER}' "
                f"on the line(s) immediately after the heading (slice 017-01 AC #4)",
            )

    # AC #4 sub: exactly 5 markers total — no duplicates, no extra slot.
    # Originally 4 (slice 017-01 AC #4); slice 022-02 added the Contract
    # surfaces slot, raising the count to 5.
    def test_architecture_template_has_exactly_five_markers(self):
        body = self._read("templates/docs/architecture.md.template")
        count = body.count(self.UNFILLED_MARKER)
        self.assertEqual(
            count, 5,
            f"architecture.md.template must contain exactly 5 unfilled "
            f"markers (one per elicitation slot — Repository structure / "
            f"Tech stack / Module boundaries / Data model / Contract "
            f"surfaces); got {count}. A duplicate marker or a marker on "
            f"the Core architecture decisions / Open questions sections "
            f"would break this assertion (slice 017-01 AC #4 + slice "
            f"022-02 AC #1).",
        )

    # AC #4 sub: non-elicitation sections (decisions, open questions) carry NO marker
    def test_architecture_template_non_marker_sections_have_no_marker(self):
        body = self._read("templates/docs/architecture.md.template")
        for section in self.EXPECTED_ARCH_NON_MARKER_SECTIONS:
            # Capture the body between this H2 and the next H2 (or EOF).
            match = re.search(
                rf"^## {re.escape(section)}\n+(.*?)(?=^## |\Z)",
                body, flags=re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(
                match,
                f"section '## {section}' must exist in architecture.md.template",
            )
            section_body = match.group(1)
            self.assertNotIn(
                self.UNFILLED_MARKER, section_body,
                f"section '## {section}' must NOT carry an elicitation marker — "
                f"it's a hand-curated section, not an elicitation slot",
            )

    # AC #4 sub: architecture.md.template keeps Deferred fallback prose on
    # the slots that previously had it (Tech stack and Module boundaries).
    # Repository structure and Data model are new slots that get a positive
    # placeholder rather than a Deferred fallback (the answer is rarely
    # "no signal" for those — every project has a layout).
    def test_architecture_template_keeps_deferred_fallback(self):
        body = self._read("templates/docs/architecture.md.template")
        for stanza in ("Tech stack", "Module boundaries"):
            pattern = re.compile(
                rf"^## {re.escape(stanza)}\b.*?\*\*Deferred",
                flags=re.MULTILINE | re.DOTALL,
            )
            self.assertRegex(
                body, pattern,
                f"slot '## {stanza}' must keep its Deferred fallback prose "
                f"(slice 017-01 AC #4)",
            )

    # AC #4 sub: template no longer carries the old "What this project does"
    # stub — that's vision.md's job. The pointer to vision.md is in the
    # top-of-doc preamble instead.
    def test_architecture_template_no_what_project_does_stub(self):
        body = self._read("templates/docs/architecture.md.template")
        self.assertNotIn(
            "## What this project does", body,
            "architecture.md.template must not carry its own 'What this project "
            "does' stub — that question is owned by product-vision.md (slice 017-01 AC #4)",
        )
        self.assertIn(
            "product-vision.md", body,
            "architecture.md.template must reference product-vision.md "
            "(top-of-doc pointer; slice 017-01 AC #4)",
        )

    # AC #5: CLAUDE.md.template's "What this project does" line points to vision doc
    def test_claude_md_template_references_product_vision(self):
        body = self._read("templates/CLAUDE.md.template")
        # The "What this project does" section must reference docs/product-vision.md
        # and must not contain the old "Deferred — no signal from initial pitch" stub.
        what_section = re.search(
            r"^## What this project does\n+(.+?)(?=^##|\Z)",
            body, flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(
            what_section,
            "CLAUDE.md.template must have a '## What this project does' section",
        )
        section_body = what_section.group(1)
        self.assertIn(
            "docs/product-vision.md", section_body,
            "the 'What this project does' section must reference "
            "docs/product-vision.md (slice 017-01 AC #5)",
        )
        self.assertNotIn(
            "Deferred — no signal from initial pitch", section_body,
            "the 'What this project does' section must no longer carry the "
            "'Deferred — no signal' stub (slice 017-01 AC #5)",
        )

    # AC #6: docs/conventions.md documents the marker convention
    def test_conventions_md_documents_marker_convention(self):
        body = self._read("docs/conventions.md")
        # Tightened per implementation-reviewer feedback (deviation §3): the
        # earlier substring-only check could pass on a convention body where
        # the words "unfilled" / "filled" / "skipped" appeared in unrelated
        # rules. Anchor instead on the "Elicitation slots" rule's heading
        # text + content adjacency.
        rule_match = re.search(
            r"\*\*Rule:\*\* Elicitation slots.*?(?=\*\*Rule:\*\*|\Z)",
            body, flags=re.DOTALL,
        )
        self.assertIsNotNone(
            rule_match,
            "docs/conventions.md must contain a '**Rule:** Elicitation slots' "
            "block documenting the marker convention (slice 017-01 AC #6)",
        )
        rule_body = rule_match.group(0)
        # The rule body must mention all three lifecycle states.
        for state in ("unfilled", "filled", "skipped"):
            self.assertIn(
                state, rule_body,
                f"the 'Elicitation slots' rule must name the '{state}' "
                f"marker state (slice 017-01 AC #6)",
            )
        # The rule body must mention the marker format (so a future edit
        # that removes the format example is caught).
        self.assertIn(
            "elicited:", rule_body,
            "the 'Elicitation slots' rule must document the marker prefix "
            "'<!-- elicited: ... -->' (slice 017-01 AC #6)",
        )
        # The rule body must name 017-03 as the slice that introduces the
        # hash field — so the convention notes its own intentional deferral
        # rather than silently shipping incomplete machinery.
        self.assertIn(
            "017-03", rule_body,
            "the 'Elicitation slots' rule must reference slice 017-03 as the "
            "introducer of the `hash` field (slice 017-01 AC #6)",
        )

    # AC #7: scaffold-init dogfood produces docs/product-vision.md AND
    # docs/architecture.md, both with their slot structure intact.
    def test_scaffold_produces_product_vision_md(self):
        with tempfile.TemporaryDirectory(prefix="jig-017-01-dogfood-") as tmp:
            target = Path(tmp) / "demo-project"
            result = run_scaffold(target)
            self.assertEqual(
                result.returncode, 0,
                f"scaffold.py exit nonzero: stderr={result.stderr}",
            )

            # Vision side: 10 H2 sections in order (9 from slice 017-01 +
            # "Use cases" added by slice 068-01).
            vision = target / "docs" / "product-vision.md"
            self.assertTrue(
                vision.exists(),
                "scaffold-init must produce docs/product-vision.md "
                "(slice 017-01 AC #7)",
            )
            vision_body = vision.read_text(encoding="utf-8")
            headings = re.findall(r"^## (.+)$", vision_body, flags=re.MULTILINE)
            self.assertEqual(
                headings, self.EXPECTED_VISION_SECTIONS,
                f"scaffolded docs/product-vision.md must have 10 sections "
                f"in order; got {headings}",
            )

            # Architecture side: 4 elicitation markers present
            # (deviation §3 close-out — reviewer noted AC #7 originally
            # only verified the vision side).
            arch = target / "docs" / "architecture.md"
            self.assertTrue(
                arch.exists(),
                "scaffold-init must produce docs/architecture.md "
                "(slice 017-01 AC #7)",
            )
            arch_body = arch.read_text(encoding="utf-8")
            marker_count = arch_body.count(self.UNFILLED_MARKER)
            self.assertEqual(
                marker_count, 5,
                f"scaffolded docs/architecture.md must contain exactly 5 "
                f"unfilled-marker comments (Repository structure / Tech "
                f"stack / Module boundaries / Data model / Contract "
                f"surfaces); got {marker_count} (slice 017-01 AC #7 + "
                f"slice 022-02 AC #1)",
            )
            # And each of the 4 named slots is present as an H2 in the
            # scaffolded file (catches reordering / renaming bugs in the
            # template at scaffold time).
            arch_headings = re.findall(r"^## (.+)$", arch_body, flags=re.MULTILINE)
            for slot in self.EXPECTED_ARCH_STANZAS:
                self.assertIn(
                    slot, arch_headings,
                    f"scaffolded docs/architecture.md must contain "
                    f"'## {slot}' (slice 017-01 AC #7)",
                )


class TierSkillSetTests(unittest.TestCase):
    """Pin the full per-tier skill inventory emitted to scaffold.json.

    Catches one-line typos in `scaffold.py`'s `_TIER_SKILLS` table in CI
    rather than in downstream scaffold dogfooding. Filed as the inbox
    item `scaffold/test/install-list-tier-1-full-set` (2026-05-18)."""

    EXPECTED_TIER_0 = [
        "scaffold-init",
        "memory-sync",
        "spec-workflow",
        "independent-review",
        "migrate",
        "vision-elicitation",
        "contracts",
    ]

    EXPECTED_TIER_1 = [
        "adr-workflow",
        "tdd-loop",
        "slice-land",
        "pr-review",
        "arch-review",
        "clarify",
        "analyze",
        "security-review",
        "code-health",
        "explain",
        "bug-fix",
        "reframe",
        "orient",
    ]

    # tier-2 is empty in scaffold.py today; this assertion turns a future
    # tier-2 addition into a deliberate test update.
    EXPECTED_TIER_2: list[str] = []

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-tier-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _manifest(self):
        return json.loads((self.target / "scaffold.json").read_text())

    def _skills_in_tier(self, manifest: dict, tier: str) -> list[str]:
        prefix = f"{tier}/"
        return [
            s[len(prefix):]
            for s in manifest.get("installed_skills", [])
            if s.startswith(prefix)
        ]

    def test_tier_0_is_pinned(self):
        result = run_scaffold_with_args(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        actual = self._skills_in_tier(self._manifest(), "tier-0")
        self.assertEqual(
            actual, self.EXPECTED_TIER_0,
            f"tier-0 set drift: expected {self.EXPECTED_TIER_0}, got {actual}",
        )

    def test_tier_1_is_pinned(self):
        result = run_scaffold_with_args(self.target, "--has-tests")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        actual = self._skills_in_tier(self._manifest(), "tier-1")
        self.assertEqual(
            actual, self.EXPECTED_TIER_1,
            f"tier-1 set drift: expected {self.EXPECTED_TIER_1}, got {actual}",
        )

    def test_tier_2_is_empty(self):
        # Even with the tier-2 trigger present, no tier-2 skills exist yet —
        # tier-2 stays in `offered_tiers` but never lands as `tier-2/<name>`
        # in `installed_skills` because the table is empty.
        result = run_scaffold_with_args(
            self.target, "--has-tests", "--plans-ai",
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        manifest = self._manifest()
        actual = self._skills_in_tier(manifest, "tier-2")
        self.assertEqual(
            actual, self.EXPECTED_TIER_2,
            f"tier-2 set drift: expected {self.EXPECTED_TIER_2}, got {actual}",
        )

    # ----- Slice 038-03: doc <-> _TIER_SKILLS consistency -----------------
    # These pin the positioning docs to the pinned tier inventory. The gap
    # they close is the one spec 038 was filed for: `vision-elicitation`
    # was in `_TIER_SKILLS["tier-0"]` but absent from product-vision.md's
    # numbered list, and README claimed "5 Tier 0 skills" — both survived
    # for months because nothing asserted doc↔code tier consistency.
    def test_product_vision_names_every_tier_skill(self):
        vision = (REPO_ROOT / "docs" / "product-vision.md").read_text()
        missing = [
            s for s in (self.EXPECTED_TIER_0 + self.EXPECTED_TIER_1)
            if f"`{s}`" not in vision
        ]
        self.assertEqual(
            missing, [],
            f"docs/product-vision.md does not name every tier skill; "
            f"missing: {missing}. Add them to the tier inventory or fix "
            f"the _TIER_SKILLS table.",
        )

    def test_readme_states_correct_tier0_count(self):
        readme = (REPO_ROOT / "README.md").read_text()
        self.assertIn(
            f"{len(self.EXPECTED_TIER_0)} Tier 0 skills", readme,
            f"README must state the Tier-0 floor count "
            f"({len(self.EXPECTED_TIER_0)} skills) to match _TIER_SKILLS",
        )

    def test_vision_elicitation_worked_example_tier_line_in_sync(self):
        """The vision-elicitation worked example is hand-seeded to mirror
        product-vision.md's "Where jig fits" line; its tier counts must
        track `_TIER_SKILLS`. (Slice 038-03 compliance review caught this
        shipped Tier-0 resource carrying the stale "5 Tier 0 + ~5 Tier 1"
        line — a `skills/` path the original `docs/`-scoped grep missed.)"""
        example = (
            REPO_ROOT / "skills" / "vision-elicitation" / "worked-example-jig.md"
        ).read_text()
        n0, n1 = len(self.EXPECTED_TIER_0), len(self.EXPECTED_TIER_1)
        self.assertIn(
            f"{n0} Tier 0 + {n1} Tier 1", example,
            f"worked-example-jig.md tier-count line must match _TIER_SKILLS "
            f"({n0} Tier 0 + {n1} Tier 1)",
        )


class SeedReferenceSpecTests(unittest.TestCase):
    """Slice 048-05 — scaffold-init seeds a complete DONE worked-example
    spec (001-adopt-jig) plus a DRAFT hand-off stub (002-first-spec) and a
    populated status board, honest-by-construction."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-seed-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        result = run_scaffold(self.target)
        self.assertEqual(
            result.returncode, 0,
            f"scaffold.py failed: stderr={result.stderr}\nstdout={result.stdout}",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _read(self, rel: str) -> str:
        return (self.target / rel).read_text()

    # AC #1 — the worked-example spec is emitted, slice at status: DONE.
    def test_seed_001_files_exist_with_done_slice(self):
        spec = self.target / "docs/specs/001-adopt-jig/spec.md"
        slice_file = self.target / "docs/specs/001-adopt-jig/slice-01-bootstrap.md"
        self.assertTrue(spec.is_file(), "001-adopt-jig/spec.md missing")
        self.assertTrue(slice_file.is_file(), "slice-01-bootstrap.md missing")
        # Slice frontmatter is status: DONE.
        self.assertRegex(
            slice_file.read_text(), r"(?m)^status:\s*DONE\s*$",
            "bootstrap slice must be status: DONE",
        )
        self.assertIn("## Slice 001-01 — bootstrap", slice_file.read_text())

    # AC #2 — honesty pin: review line references the deterministic check,
    # and there is NO fabricated subagent verdict string.
    def test_seed_review_line_is_honest(self):
        body = self._read("docs/specs/001-adopt-jig/slice-01-bootstrap.md")
        self.assertIn("scaffold-completion check", body,
                      "review boxes must be annotated as verified by the "
                      "deterministic scaffold-completion check")
        lowered = body.lower()
        for forbidden in (
            "reviewer subagent verdict: pass",
            "reviewer subagent: pass",
            "subagent verdict: pass",
            "verdict: pass",
        ):
            self.assertNotIn(
                forbidden, lowered,
                f"seed must not fabricate a subagent verdict ({forbidden!r})",
            )

    # AC #5 — the 002 hand-off stub exists at status: DRAFT (not READY).
    def test_seed_002_stub_is_draft(self):
        stub = self.target / "docs/specs/002-first-spec/spec.md"
        self.assertTrue(stub.is_file(), "002-first-spec/spec.md missing")
        text = stub.read_text()
        self.assertRegex(text, r"(?m)^status:\s*DRAFT\s*$",
                         "002 stub must be status: DRAFT")
        self.assertNotRegex(
            text, r"(?m)^status:\s*READY_FOR_IMPLEMENTATION\s*$",
            "002 stub status must NOT be READY_FOR_IMPLEMENTATION",
        )

    # AC #4 — the status board has a real, populated 001-01 DONE row.
    def test_status_board_has_done_row(self):
        board = self._read("docs/specs/README.md")
        self.assertIn("001-01 — bootstrap", board)
        self.assertIn("001-adopt-jig", board)
        # The bootstrap row is DONE.
        self.assertRegex(
            board, r"001-01 — bootstrap.*\*\*DONE\*\*",
            "status board must mark 001-01 — bootstrap DONE",
        )

    # AC #6 — no plugin-root / source-checkout leakage in the seed.
    def test_seed_has_no_path_leakage(self):
        for rel in (
            "docs/specs/001-adopt-jig/spec.md",
            "docs/specs/001-adopt-jig/slice-01-bootstrap.md",
            "docs/specs/002-first-spec/spec.md",
            "docs/specs/README.md",
        ):
            text = self._read(rel)
            self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text, f"{rel} leaks plugin root")
            self.assertNotIn(str(REPO_ROOT), text, f"{rel} leaks source-checkout path")
            self.assertNotIn("{{", text, f"{rel} has an unrendered placeholder")

    # AC #3 — the freshly scaffolded tree passes spec_lint.py --all.
    def test_seed_lints_clean(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "spec_lint.py"), "--all"],
            capture_output=True, text=True, cwd=str(self.target),
        )
        self.assertEqual(
            result.returncode, 0,
            f"spec_lint --all failed on seed:\n{result.stdout}\n{result.stderr}",
        )


class SeedGreenfieldGuardTests(unittest.TestCase):
    """Slice 048-05 / Clarification Q1 — the seed is greenfield-only: it is
    emitted only when docs/specs/ is otherwise empty, and is skipped
    silently (never overwriting) when any spec already exists."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-seed-guard-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_seed_skipped_when_specs_already_present(self):
        # Pre-create a user spec under docs/specs/.
        existing = self.target / "docs/specs/007-my-spec"
        existing.mkdir(parents=True)
        marker = "# my own spec — do not touch\n"
        (existing / "spec.md").write_text(marker)
        result = run_scaffold_with_args(self.target, "--force")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # The seed must NOT have been emitted.
        self.assertFalse(
            (self.target / "docs/specs/001-adopt-jig").exists(),
            "seed must be skipped when docs/specs/ already has content",
        )
        # The user's spec is untouched.
        self.assertEqual((existing / "spec.md").read_text(), marker)

    def test_seed_emitted_into_empty_specs_dir(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue(
            (self.target / "docs/specs/001-adopt-jig/spec.md").is_file(),
            "seed must be emitted into a greenfield docs/specs/",
        )


class CompletionVerificationTests(unittest.TestCase):
    """Slice 048-06 — the wizard runs verification and reports a verdict.

    These exercise the wired-in run end-to-end (AC #1/#3/#4/#6):
    a good scaffold prints the completion summary and exits 0; a scaffold
    with a required artifact removed reports failure loudly (non-zero exit);
    a plugin-only scaffold does not false-fail on absent .claude machinery.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-complete-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #1 — verification runs at scaffold end with a summary + verdict.
    def test_in_repo_scaffold_emits_completion_summary(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("Scaffold verification", result.stdout)
        self.assertIn("in-repo", result.stdout)
        # AC #3 — the seed is in the verified set.
        self.assertIn("seed", result.stdout)
        self.assertIn("verified", result.stdout.lower())

    # AC #3 — a good plugin-only scaffold verifies the seed without
    # false-failing on the .claude machinery that lives in the plugin.
    def test_plugin_only_scaffold_verifies_seed_without_false_fail(self):
        result = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("plugin-only", result.stdout)
        self.assertIn("seed", result.stdout)
        self.assertIn("verified", result.stdout.lower())
        self.assertNotIn("FAILED", result.stdout)

    # AC #4 — removing a required artifact makes the verdict loud + non-zero.
    def test_missing_seed_file_makes_verification_fail_loudly(self):
        first = run_scaffold(self.target)
        self.assertEqual(first.returncode, 0, f"stderr: {first.stderr}")
        # Drop a seed file, then re-run verification via the headless surface
        # of the wizard helper (scaffold itself refuses re-scaffold). We assert
        # on the completion summary directly through verify_install.
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import io

        import verify_install  # noqa: E402

        (self.target / "docs/specs/001-adopt-jig/spec.md").unlink()
        buf = io.StringIO()
        rc = verify_install.run_completion_summary(
            self.target, with_machinery=True, seed_expected=True, out=buf,
        )
        self.assertEqual(rc, 1, msg=buf.getvalue())
        self.assertIn("FAILED", buf.getvalue())
        self.assertIn("seed", buf.getvalue())

    # AC #4 — a missing machinery artifact in an in-repo scaffold fails too.
    def test_missing_machinery_artifact_makes_verification_fail(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import io

        import verify_install  # noqa: E402

        first = run_scaffold(self.target)
        self.assertEqual(first.returncode, 0, f"stderr: {first.stderr}")
        # Remove a scaffolded agent file.
        agent = self.target / ".claude/agents/jig-reviewer.md"
        if agent.exists():
            agent.unlink()
        buf = io.StringIO()
        rc = verify_install.run_completion_summary(
            self.target, with_machinery=True, seed_expected=True, out=buf,
        )
        self.assertEqual(rc, 1, msg=buf.getvalue())
        self.assertIn("FAILED", buf.getvalue())


class AdoptionHandoffTests(unittest.TestCase):
    """Slice 048-03 — a freshly scaffolded project exposes the adoption /
    readiness guidance: docs/adoption-readiness.md is copied into the
    target so links resolve locally, CLAUDE.md carries a short pointer to
    it (not the body), and nothing leaks a plugin-root or source path."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adopt-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        result = run_scaffold(self.target)
        self.assertEqual(
            result.returncode, 0,
            f"scaffold.py failed: stderr={result.stderr}\nstdout={result.stdout}",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _read(self, rel: str) -> str:
        return (self.target / rel).read_text()

    # AC #3 — the guide is copied into the scaffolded tree.
    def test_guide_copied_into_target(self):
        self.assertTrue(
            (self.target / "docs/adoption-readiness.md").is_file(),
            "docs/adoption-readiness.md must be copied into the scaffolded "
            "project so its links resolve locally (AC #3)",
        )

    # AC #1 / AC #2 — CLAUDE.md carries a short pointer, not the guide body.
    def test_claude_md_points_but_does_not_inline(self):
        claude = self._read("CLAUDE.md")
        self.assertIn(
            "docs/adoption-readiness.md", claude,
            "CLAUDE.md must point at the adoption guide (AC #1)",
        )
        # The guide's distinctive section content must NOT be inlined into
        # the always-loaded CLAUDE.md (AC #2 — a pointer, not the body).
        self.assertNotIn(
            "Your first 30 minutes", claude,
            "CLAUDE.md must carry a short pointer, not the guide body (AC #2)",
        )

    # {{PROJECT_NAME}} substituted; no unrendered placeholder.
    def test_project_name_substituted(self):
        guide = self._read("docs/adoption-readiness.md")
        self.assertIn("demo-project", guide,
                      "the guide must substitute {{PROJECT_NAME}}")
        self.assertNotIn("{{", guide, "the guide has an unrendered placeholder")

    # AC #5 — no plugin-root / source-checkout leakage in the handoff.
    def test_handoff_has_no_path_leakage(self):
        for rel in ("docs/adoption-readiness.md", "CLAUDE.md"):
            text = self._read(rel)
            self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text,
                             f"{rel} leaks plugin root (AC #5)")
            self.assertNotIn(str(REPO_ROOT), text,
                             f"{rel} leaks source-checkout path (AC #5)")

    # AC #3 — every relative link in the guide resolves inside the target.
    def test_guide_links_resolve_in_target(self):
        guide_path = self.target / "docs/adoption-readiness.md"
        link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        unresolved = []
        for href in link_re.findall(guide_path.read_text()):
            href = href.split("#", 1)[0].strip()
            if not href or href.startswith(("http://", "https://", "mailto:")):
                continue
            if not (guide_path.parent / href).resolve().exists():
                unresolved.append(href)
        self.assertEqual(
            unresolved, [],
            f"adoption guide has links that don't resolve in the scaffolded "
            f"tree (AC #3): {unresolved}",
        )


class SecurityFloorTests(unittest.TestCase):
    """Slice 052-02 — secret-prevention-floor.

    A fresh scaffold ships (AC #1) secret-ignore `.gitignore` patterns,
    (AC #2) the agent-time secret-scan hook registered in the scaffolded
    settings.json + copied to .claude/hooks/scripts/, and (AC #4) a lean
    `## Security (MUST)` block in CLAUDE.md. Plus the `.gitignore` merge is
    idempotent and never clobbers pre-existing lines.
    """

    SECRET_BLOCK_PATTERNS = (".env", ".env.*", "*.pem", "*.key",
                             "secrets/", "credentials/")

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-052-02-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ---- AC #1: secret-ignore .gitignore patterns ----
    def test_gitignore_written_with_secret_patterns(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        gi = self.target / ".gitignore"
        self.assertTrue(gi.is_file(), ".gitignore must be scaffolded")
        text = gi.read_text()
        for pat in self.SECRET_BLOCK_PATTERNS:
            self.assertIn(pat, text, f".gitignore missing secret pattern: {pat}")

    def test_gitignore_ignores_semantic_index_local_runtime_files(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = (self.target / ".gitignore").read_text()
        self.assertIn(".jig/semantic-index-claude-hook.json", text)
        self.assertIn(".jig/semantic-index-codex-hook.json", text)
        self.assertIn(".jig/semantic-index-events.jsonl", text)
        self.assertNotIn(".jig/semantic-index.json", text)

    def test_gitignore_block_is_marker_delimited(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = (self.target / ".gitignore").read_text()
        self.assertIn(">>> jig secret-ignore >>>", text)
        self.assertIn("<<< jig secret-ignore <<<", text)

    def test_gitignore_written_in_plugin_only_mode(self):
        """Slice 052-04 — the `.gitignore` floor must still land in
        `--plugin-only` mode (the floor write must not be gated behind
        `--with-machinery`)."""
        result = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = (self.target / ".gitignore").read_text()
        self.assertIn(">>> jig secret-ignore >>>", text)
        self.assertIn(".env", text)

    def test_gitignore_reincludes_env_placeholder_templates(self):
        """`.env.*` would otherwise ignore `.env.example` — but the
        secret-scan hook tells users to "commit a placeholder in a *.example
        file" and skips those suffixes when scanning, so the floor must
        re-include them via git negations that follow the `.env.*` line.
        (Reconciliation fix, 052-02 — keeps the floor internally consistent.)
        """
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        lines = (self.target / ".gitignore").read_text().splitlines()
        self.assertIn(".env.*", lines)
        for neg in ("!.env.example", "!.env.sample",
                    "!.env.template", "!.env.dist"):
            self.assertIn(neg, lines, f".gitignore missing re-include: {neg}")
        # A git negation only takes effect AFTER the matching ignore line.
        self.assertLess(
            lines.index(".env.*"), lines.index("!.env.example"),
            "!.env.example must follow .env.* to re-include it",
        )

    # ---- AC #1: append-not-clobber + idempotent ----
    def test_gitignore_preserves_preexisting_lines(self):
        gi = self.target / ".gitignore"
        gi.write_text("# my project\nnode_modules/\ndist/\n")
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = gi.read_text()
        # Pre-existing lines survive.
        self.assertIn("node_modules/", text)
        self.assertIn("dist/", text)
        self.assertIn("# my project", text)
        # And the jig block was appended.
        self.assertIn(".env", text)
        self.assertIn(">>> jig secret-ignore >>>", text)

    def test_gitignore_block_is_idempotent_across_reruns(self):
        first = run_scaffold(self.target)
        self.assertEqual(first.returncode, 0, f"stderr: {first.stderr}")
        # --force re-scaffold (scaffold refuses a bare re-run).
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        second = subprocess.run(
            [sys.executable, str(SCAFFOLD), "--force", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(second.returncode, 0, f"stderr: {second.stderr}")
        text = (self.target / ".gitignore").read_text()
        # Exactly one jig block — no duplicate markers.
        self.assertEqual(text.count(">>> jig secret-ignore >>>"), 1,
                         "re-scaffold duplicated the jig secret-ignore block")
        self.assertEqual(text.count("<<< jig secret-ignore <<<"), 1)

    def test_gitignore_merge_function_is_idempotent_unit(self):
        """Unit-level: calling the merge twice on the same file is a no-op
        after the first, and a third distinct content does not stack."""
        mod = _load_scaffold_module()
        gi = self.target / ".gitignore"
        gi.write_text("existing-line\n")
        mod._write_gitignore_secret_block(self.target)
        once = gi.read_text()
        mod._write_gitignore_secret_block(self.target)
        twice = gi.read_text()
        self.assertEqual(once, twice, "second merge must be a no-op")
        self.assertIn("existing-line", twice)
        self.assertEqual(twice.count(">>> jig secret-ignore >>>"), 1)

    # ---- AC #2: secret-scan hook copied + registered ----
    def test_secret_scan_hook_copied_to_project(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        hook = self.target / ".claude/hooks/scripts/jig-secret-scan.sh"
        self.assertTrue(hook.is_file(),
                        "jig-secret-scan.sh must be copied to the scaffolded tree")
        # Executable bit pinned (mirrors other scaffolded hooks).
        self.assertTrue(os.access(hook, os.X_OK), "hook must be executable")

    def test_secret_scan_hook_registered_in_settings(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        settings = json.loads(
            (self.target / ".claude/settings.json").read_text()
        )
        pre = settings.get("hooks", {}).get("PreToolUse", [])
        # Find a jig-managed Edit|Write|MultiEdit group that references the
        # secret-scan hook (project-relative path).
        found = False
        for entry in pre:
            if entry.get("matcher") != "Edit|Write|MultiEdit":
                continue
            if not (entry.get("metadata") or {}).get("managed_by_jig"):
                continue
            for h in entry.get("hooks", []):
                if "jig-secret-scan.sh" in (h.get("command") or ""):
                    self.assertIn(
                        "${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/",
                        h["command"],
                        "scaffolded hook command must use the project path",
                    )
                    found = True
        self.assertTrue(
            found,
            "secret-scan hook not registered in the scaffolded "
            "PreToolUse Edit|Write|MultiEdit group with the jig marker",
        )

    def test_secret_scan_hook_works_after_scaffold(self):
        """End-to-end: the copied hook blocks a real secret in the scaffolded
        project tree (AC #2 'observable end-to-end')."""
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        hook = self.target / ".claude/hooks/scripts/jig-secret-scan.sh"
        # Assemble the secret at runtime so this source file never holds one.
        secret = "AKIA" + "JKL4MNOP5QRS6TUV"
        payload = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.target / "config.py"),
                "content": "key = '" + secret + "'\n",
            },
        })
        env = os.environ.copy()
        env.pop("JIG_SECRET_SCAN_APPROVED", None)
        r = subprocess.run(["bash", str(hook)], input=payload,
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2,
                         f"scaffolded hook should block a real secret; "
                         f"stderr={r.stderr!r}")

    # ---- AC #4: lean `## Security (MUST)` block in CLAUDE.md ----
    def test_security_block_present_in_claude_md(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        claude_md = (self.target / "CLAUDE.md").read_text()
        idx = claude_md.find("## Security (MUST)")
        self.assertGreater(idx, 0, "CLAUDE.md missing `## Security (MUST)` block")
        # Section bounds: from heading to the next H2 (or EOF).
        next_h2 = re.search(r"(?m)^##\s+", claude_md[idx + 1:])
        section = claude_md[idx:(idx + 1 + next_h2.start()) if next_h2 else len(claude_md)]
        low = section.lower()
        # No-secrets MUST rule + env-var / secret-manager guidance.
        self.assertIn("secret", low)
        self.assertTrue("env" in low or "secret manager" in low,
                        "Security block should point to env vars / secret managers")
        # Honesty note: defense-in-depth, not a guarantee.
        self.assertIn("defense-in-depth", low)
        # Pointer to richer security depth.
        self.assertTrue(
            "security-review" in low or "adobe-security" in low,
            "Security block should point to a richer security skill for depth",
        )

    def test_security_block_is_lean(self):
        """AC #4 — the block stays within the ≈≤ 12-line lean budget
        (design principle #2)."""
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        claude_md = (self.target / "CLAUDE.md").read_text()
        idx = claude_md.find("## Security (MUST)")
        self.assertGreater(idx, 0)
        next_h2 = re.search(r"(?m)^##\s+", claude_md[idx + 1:])
        section = claude_md[idx:(idx + 1 + next_h2.start()) if next_h2 else len(claude_md)]
        # Count non-blank lines including the heading.
        lines = [ln for ln in section.strip().splitlines() if ln.strip()]
        self.assertLessEqual(
            len(lines), 12,
            f"Security block must be ≤ 12 non-blank lines; got {len(lines)}",
        )

    def test_semantic_index_guidance_rendered_to_claude_and_workflow(self):
        """Slice 080-02 — generated Claude surfaces prefer public
        semantic-index exploration when available, with targeted search/read
        fallback and no Scout-specific public prose."""
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

        claude_md = (self.target / "CLAUDE.md").read_text()
        self.assertIn("Semantic-index exploration", claude_md)
        self.assertIn("configured public semantic-index provider first", claude_md)
        self.assertIn("fall back to targeted search/read", claude_md)

        workflow = (self.target / "docs" / "workflow.md").read_text()
        self.assertIn("## Semantic-Index Exploration", workflow)
        self.assertIn("jig-semantic-index", workflow)
        self.assertIn(".jig/semantic-index.json", workflow)
        self.assertIn("auto_attach: true", workflow)
        self.assertIn("discovers the first installed supported", workflow)
        self.assertNotIn('"provider": "tokensave"', workflow)
        self.assertIn("none is installed", workflow)
        self.assertIn("never installs providers", workflow)
        self.assertIn("downloads", workflow)
        self.assertIn("models", workflow)
        self.assertIn("blocks a workflow", workflow)
        self.assertNotIn("Scout", claude_md)
        self.assertNotIn("Scout", workflow)


class PermissionsDenyTests(unittest.TestCase):
    """Slice 052-03 — destructive-command-guardrail.

    A fresh scaffold's `.claude/settings.json` carries conservative
    `permissions.deny` defaults (force-push / hard-reset / `rm -rf`, AC #1).
    The merge is non-destructive + idempotent (AC #2): jig-ownership of a
    deny entry is identified by membership in `_PERMISSIONS_DENY_DEFAULTS`
    (set-membership marker — a string array can't carry a per-entry
    `metadata` marker), so user-added `allow` / `ask` / custom `deny`
    entries survive and jig's globs are never duplicated.
    """

    # The three guardrails AC #1 names explicitly, in canonical
    # `Bash(<pattern>)` rule shape.
    FORCE_PUSH_GLOB = "Bash(git push --force*)"
    HARD_RESET_GLOB = "Bash(git reset --hard*)"
    RM_RF_GLOB = "Bash(rm -rf*)"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-052-03-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _read_settings(self) -> dict:
        return json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )

    def _seed_settings(self, payload: dict) -> None:
        settings = self.target / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(payload, indent=2) + "\n")

    def _rescaffold_force(self) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, str(SCAFFOLD), "--force", str(self.target)],
            capture_output=True, text=True, env=env,
        )

    # ---- AC #1: conservative deny defaults are scaffolded ----
    def test_fresh_scaffold_has_destructive_deny_globs(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        deny = self._read_settings().get("permissions", {}).get("deny", [])
        for glob in (self.FORCE_PUSH_GLOB, self.HARD_RESET_GLOB, self.RM_RF_GLOB):
            self.assertIn(
                glob, deny,
                f"scaffolded permissions.deny missing guardrail: {glob}",
            )

    def test_fresh_scaffold_deny_matches_constant(self):
        """The scaffolded deny array is exactly jig's source-of-truth set
        (no manual count drift)."""
        mod = _load_scaffold_module()
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        deny = self._read_settings().get("permissions", {}).get("deny", [])
        self.assertEqual(
            set(deny), set(mod._PERMISSIONS_DENY_DEFAULTS),
            "fresh scaffold deny array must equal _PERMISSIONS_DENY_DEFAULTS",
        )

    # ---- AC #2: non-destructive merge into a pre-existing settings.json ----
    def test_merge_preserves_user_permissions_entries(self):
        """A pre-existing settings.json with user allow + ask + a custom
        deny entry: all survive AND jig's deny globs are added, with no
        duplicates."""
        custom_deny = "Bash(curl*evil.example.com*)"
        self._seed_settings({
            "permissions": {
                "allow": ["Bash(ls*)", "Bash(git status*)"],
                "ask": ["Bash(git commit*)"],
                "deny": [custom_deny],
            },
        })
        # --force is the documented escape hatch; the seed has no hooks so
        # the unmanaged-hooks refusal does not apply, but a re-run over an
        # existing tree still needs --force (scaffold.json sentinel).
        r = self._rescaffold_force()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        perms = self._read_settings().get("permissions", {})
        # User allow + ask survive untouched.
        self.assertEqual(perms.get("allow"), ["Bash(ls*)", "Bash(git status*)"])
        self.assertEqual(perms.get("ask"), ["Bash(git commit*)"])
        # User's custom deny survives.
        deny = perms.get("deny", [])
        self.assertIn(custom_deny, deny)
        # jig's guardrails were added.
        for glob in (self.FORCE_PUSH_GLOB, self.HARD_RESET_GLOB, self.RM_RF_GLOB):
            self.assertIn(glob, deny)
        # No duplicates anywhere in the deny array.
        self.assertEqual(
            len(deny), len(set(deny)),
            f"permissions.deny has duplicate entries: {deny}",
        )
        # The custom deny appears exactly once.
        self.assertEqual(deny.count(custom_deny), 1)

    def test_merge_into_settings_without_permissions_key(self):
        """If a pre-existing settings.json has no `permissions` key at all,
        the merge creates `{"deny": [...]}` with jig's globs."""
        self._seed_settings({"env": {"FOO": "bar"}})
        r = self._rescaffold_force()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        settings = self._read_settings()
        self.assertEqual(settings.get("env"), {"FOO": "bar"})
        deny = settings.get("permissions", {}).get("deny", [])
        for glob in (self.FORCE_PUSH_GLOB, self.HARD_RESET_GLOB, self.RM_RF_GLOB):
            self.assertIn(glob, deny)

    # ---- AC #2: idempotent re-run ----
    def test_deny_globs_idempotent_across_reruns(self):
        first = run_scaffold(self.target)
        self.assertEqual(first.returncode, 0, f"stderr: {first.stderr}")
        second = self._rescaffold_force()
        self.assertEqual(second.returncode, 0, f"stderr: {second.stderr}")
        deny = self._read_settings().get("permissions", {}).get("deny", [])
        # Each jig glob appears exactly once after a re-scaffold.
        for glob in (self.FORCE_PUSH_GLOB, self.HARD_RESET_GLOB, self.RM_RF_GLOB):
            self.assertEqual(
                deny.count(glob), 1,
                f"re-scaffold duplicated deny glob {glob}: {deny}",
            )
        self.assertEqual(
            len(deny), len(set(deny)),
            f"permissions.deny has duplicates after re-run: {deny}",
        )

    # ---- AC #2: unit-level merge logic (preserve + idempotent + no-clobber) ----
    def test_merge_settings_permissions_unit(self):
        """Unit: `_merge_settings` preserves user allow/ask/custom-deny,
        appends jig's deny set exactly once, leaves non-`deny` permission
        keys untouched, and is idempotent when called twice."""
        mod = _load_scaffold_module()
        existing = {
            "permissions": {
                "allow": ["Bash(ls*)"],
                "ask": ["Bash(git commit*)"],
                "deny": ["Bash(curl*evil*)"],
            },
        }
        merged = mod._merge_settings(existing, {})
        perms = merged["permissions"]
        # Non-deny keys untouched.
        self.assertEqual(perms["allow"], ["Bash(ls*)"])
        self.assertEqual(perms["ask"], ["Bash(git commit*)"])
        # User deny preserved + jig set appended, no duplicates.
        self.assertIn("Bash(curl*evil*)", perms["deny"])
        for glob in mod._PERMISSIONS_DENY_DEFAULTS:
            self.assertIn(glob, perms["deny"])
        self.assertEqual(len(perms["deny"]), len(set(perms["deny"])))
        # Idempotent: a second merge over the result yields the same deny set.
        merged2 = mod._merge_settings(merged, {})
        self.assertEqual(merged2["permissions"]["deny"], perms["deny"])
        # Does not mutate the input.
        self.assertEqual(existing["permissions"]["deny"], ["Bash(curl*evil*)"])

    def test_merge_dedups_user_supplied_jig_exact_glob_unit(self):
        """Unit: if a user's deny array already contains one of jig's exact
        globs, the merge must not duplicate it. Set-membership identifies the
        entry as jig-owned, so it is filtered out of the user set then
        re-appended exactly once (the dedup-and-relocate the docstring
        promises). Pins the behavior directly rather than only via the
        re-scaffold idempotency path."""
        mod = _load_scaffold_module()
        jig_glob = mod._PERMISSIONS_DENY_DEFAULTS[0]
        existing = {
            "permissions": {"deny": [jig_glob, "Bash(curl*evil*)"]},
        }
        merged = mod._merge_settings(existing, {})
        deny = merged["permissions"]["deny"]
        self.assertEqual(
            deny.count(jig_glob), 1,
            f"user-supplied jig-exact glob {jig_glob} was duplicated: {deny}",
        )
        # The genuinely-custom (non-jig) deny still survives exactly once.
        self.assertEqual(deny.count("Bash(curl*evil*)"), 1)
        self.assertEqual(len(deny), len(set(deny)))

    def test_merge_settings_creates_permissions_when_absent_unit(self):
        """Unit: `_merge_settings` on a dict with no `permissions` key
        creates `permissions.deny` = jig's set."""
        mod = _load_scaffold_module()
        merged = mod._merge_settings({}, {})
        self.assertEqual(
            set(merged["permissions"]["deny"]),
            set(mod._PERMISSIONS_DENY_DEFAULTS),
        )


def _load_scaffold_module():
    """Import scaffold.py as a module for direct symbol access (used by the
    unit-level idempotency test)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("scaffold_for_052", SCAFFOLD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class VersionProvenanceTests(unittest.TestCase):
    """Slice 046-02 — scaffold.json.jig_version is derived from the host
    plugin manifest, not a hard-coded constant.

    AC1: version read from the manifest; no production code hard-codes the
         release version.
    AC2: generated metadata matches source.
    AC3: missing / malformed / version-less manifest fails clearly.
    AC4: a regression test fails if the manifest version drifts from the
         recorded scaffold metadata.
    """

    @classmethod
    def _load_scaffold_module(cls):
        """Load scaffold.py as a module for direct symbol access."""
        if getattr(cls, "_scaffold_mod", None) is None:
            import importlib.util
            spec = importlib.util.spec_from_file_location("scaffold", SCAFFOLD)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            cls._scaffold_mod = mod
        return cls._scaffold_mod

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-46-02-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _live_manifest_version(self) -> str:
        manifest = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
        )
        return manifest["version"]

    # AC1 — no production code hard-codes the release version. The old
    # `JIG_VERSION = "0.1.0"` constant must be gone, and the helper that
    # derives the version from the manifest must exist.
    def test_no_hardcoded_release_version_constant(self):
        mod = self._load_scaffold_module()
        self.assertFalse(
            hasattr(mod, "JIG_VERSION"),
            "scaffold.py must not keep a hard-coded JIG_VERSION constant "
            "(AC1) — the version is derived from the plugin manifest.",
        )
        self.assertTrue(
            hasattr(mod, "_read_plugin_version"),
            "scaffold.py must expose _read_plugin_version() (AC1).",
        )

    def test_read_plugin_version_returns_manifest_version(self):
        mod = self._load_scaffold_module()
        self.assertEqual(
            mod._read_plugin_version(REPO_ROOT),
            self._live_manifest_version(),
        )

    def test_read_plugin_version_accepts_codex_manifest(self):
        mod = self._load_scaffold_module()
        fake_plugin = Path(self.tmpdir) / "codex-plugin"
        (fake_plugin / ".codex-plugin").mkdir(parents=True)
        (fake_plugin / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "jig", "version": "9.8.7"})
        )

        self.assertEqual(mod._read_plugin_version(fake_plugin), "9.8.7")

    # AC2 — a temp scaffold records the source manifest version.
    def test_scaffold_json_jig_version_matches_source(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(
            manifest["jig_version"],
            self._live_manifest_version(),
            "scaffold.json.jig_version must equal the source manifest version (AC2).",
        )

    # AC2 — brief.md shares the {{JIG_VERSION}} placeholder, so it must
    # mention the same version.
    def test_brief_mentions_source_version(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        brief = (self.target / "brief.md").read_text()
        version = self._live_manifest_version()
        self.assertIn(
            f"Generated by jig {version} ", brief,
            "brief.md must report the source manifest version (AC2).",
        )

    # AC3 — missing plugin.json fails with the custom exception, naming the
    # manifest path.
    def test_missing_manifest_raises_clear_error(self):
        mod = self._load_scaffold_module()
        fake_plugin = Path(self.tmpdir) / "no-manifest"
        fake_plugin.mkdir()
        with self.assertRaises(mod.PluginManifestError) as ctx:
            mod._read_plugin_version(fake_plugin)
        msg = str(ctx.exception)
        self.assertIn("plugin.json", msg)

    # AC3 — malformed JSON fails with the custom exception.
    def test_malformed_manifest_raises_clear_error(self):
        mod = self._load_scaffold_module()
        fake_plugin = Path(self.tmpdir) / "bad-json"
        (fake_plugin / ".claude-plugin").mkdir(parents=True)
        (fake_plugin / ".claude-plugin" / "plugin.json").write_text("{ not json")
        with self.assertRaises(mod.PluginManifestError) as ctx:
            mod._read_plugin_version(fake_plugin)
        msg = str(ctx.exception)
        self.assertIn("plugin.json", msg)

    # AC3 — a manifest lacking `version` (and an empty version) fails clearly.
    def test_versionless_manifest_raises_clear_error(self):
        mod = self._load_scaffold_module()
        for payload in ('{"name": "jig"}', '{"name": "jig", "version": ""}'):
            with self.subTest(payload=payload):
                fake_plugin = Path(self.tmpdir) / f"noversion-{hash(payload)}"
                (fake_plugin / ".claude-plugin").mkdir(parents=True)
                (fake_plugin / ".claude-plugin" / "plugin.json").write_text(payload)
                with self.assertRaises(mod.PluginManifestError) as ctx:
                    mod._read_plugin_version(fake_plugin)
                msg = str(ctx.exception)
                self.assertIn("version", msg)

    # AC3 (integration) — scaffold() propagates the error, and it raises
    # BEFORE any file is written (fail-fast, no partial scaffold).
    def test_scaffold_propagates_and_writes_nothing_on_bad_manifest(self):
        mod = self._load_scaffold_module()
        # A plugin root with a valid template tree but a malformed manifest.
        fake_plugin = Path(self.tmpdir) / "plugin-bad-manifest"
        fake_plugin.mkdir()
        # Symlink the real templates so scaffold() gets past the template
        # check and reaches the manifest read.
        (fake_plugin / "templates").symlink_to(REPO_ROOT / "templates")
        (fake_plugin / ".claude-plugin").mkdir()
        (fake_plugin / ".claude-plugin" / "plugin.json").write_text("{ broken")
        with self.assertRaises(mod.PluginManifestError):
            mod.scaffold(self.target, fake_plugin, with_machinery=False)
        # Fail-fast: no scaffold artifacts on disk (CLAUDE.md is the first
        # file written, after the version is read).
        self.assertFalse(
            (self.target / "CLAUDE.md").exists(),
            "a bad manifest must fail before the first file write (AC3).",
        )
        self.assertFalse((self.target / "scaffold.json").exists())

    # AC4 — release-drift regression. A fresh scaffold's recorded version
    # tracks the live manifest; this fails if a constant is reintroduced
    # that drifts from .claude-plugin/plugin.json.
    def test_release_drift_regression(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        manifest = json.loads((self.target / "scaffold.json").read_text())
        live = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
        )["version"]
        self.assertEqual(
            manifest["jig_version"], live,
            "scaffold.json.jig_version drifted from the plugin manifest "
            "version — derive it from .claude-plugin/plugin.json (AC4).",
        )


class SelfDefiningConventionBlockTests(unittest.TestCase):
    """Spec 065-04 AC3 — a fresh scaffold's docs/workflow.md carries the
    marker-delimited self-defining-vocabulary convention block, written by the
    shared `_ensure_self_defining_convention_block` helper (mirroring the
    .gitignore secret floor)."""

    BLOCK_BEGIN = "<!-- >>> jig self-defining-vocabulary >>> -->"
    BLOCK_END = "<!-- <<< jig self-defining-vocabulary <<< -->"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-065-04-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_fresh_scaffold_has_convention_block(self):
        result = run_scaffold(self.target)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        wf = self.target / "docs" / "workflow.md"
        self.assertTrue(wf.is_file(), "docs/workflow.md must be scaffolded")
        text = wf.read_text()
        self.assertIn(self.BLOCK_BEGIN, text)
        self.assertIn(self.BLOCK_END, text)
        self.assertIn("Self-defining vocabulary", text)

    def test_block_is_single_and_idempotent_on_reforce(self):
        run_scaffold(self.target)
        wf = self.target / "docs" / "workflow.md"
        first = wf.read_text()
        # exactly one block, no duplication
        self.assertEqual(first.count(self.BLOCK_BEGIN), 1)
        # a --force re-scaffold keeps it single (replace-in-place, no dupes)
        result = run_scaffold_with_args(self.target, "--force")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertEqual(wf.read_text().count(self.BLOCK_BEGIN), 1)


class DecisionsConventionTemplateTests(unittest.TestCase):
    """Spec 097-01 / issue #124 instance 1 — the scaffolded conventions
    template ships a rule that accepted decision records are append-only
    (strike-and-date, never erase), while proposed/draft ones stay editable.

    Two downstream sessions independently erased superseded reasoning from a
    decision record because nothing in the scaffold said not to. jig holds the
    rule for itself (docs/conventions.md); this guards that it reaches every
    scaffolded project too. Scoped to *accepted* records so it does not
    contradict the maintainer's ruling that a Proposed ADR's body is a draft.
    """

    def _template(self) -> str:
        return (REPO_ROOT / "templates" / "docs"
                / "conventions.md.template").read_text(encoding="utf-8")

    def _decisions_section(self, body: str) -> str:
        # Body of the `## Decisions` section: from its heading to the next H2.
        m = re.search(r"^## Decisions\b.*?(?=^## |\Z)", body,
                      flags=re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(
            m, "conventions template must carry a `## Decisions` section "
               "stating the append-only rule (spec 097-01 AC #1)")
        return m.group(0)

    def test_template_states_accepted_decisions_are_append_only(self):
        """AC #1 — the rule exists and names the immutable-after-acceptance
        discipline: strike-and-date or supersede, never delete/overwrite."""
        section = self._decisions_section(self._template()).lower()
        self.assertIn("append-only", section,
                      "the Decisions rule must state records are append-only")
        self.assertIn("accepted", section,
                      "the rule must scope immutability to *accepted* records")
        # The honest correction mechanism, not deletion.
        self.assertTrue(
            "strike" in section or "supersede" in section,
            "the rule must name strike-and-date / supersede as the way to "
            "correct an accepted record (not deletion)")

    def test_template_keeps_proposed_records_editable(self):
        """AC #2 — the rule explicitly leaves Proposed/draft records editable,
        so it does not contradict question 2's ruling (a draft ADR is not
        frozen)."""
        section = self._decisions_section(self._template()).lower()
        self.assertIn("proposed", section,
                      "the rule must carve out Proposed/draft records as still "
                      "editable, per the maintainer's question-2 ruling")
        # Assert the editable *sense*, not the bare token "edit": an inverted
        # carve-out like "a Proposed record must never be edited" contains
        # "edit" too, and would satisfy a bare-token check while contradicting
        # AC #2. Dogfooding this spec's own vacuous-test discipline.
        self.assertTrue(
            "edit freely" in section or "edit its body inline" in section,
            "the carve-out must affirmatively permit editing a draft record "
            "(e.g. 'edit freely' / 'edit its body inline'), not merely mention "
            "the word 'edit' — otherwise an inverted 'never edit' phrasing "
            "would pass this test")

    def test_fresh_scaffold_conventions_carry_the_rule(self):
        """AC #1 end-to-end — a freshly scaffolded project's docs/conventions.md
        (rendered from the template) carries the append-only rule."""
        tmpdir = tempfile.mkdtemp(prefix="jig-097-01-")
        try:
            target = Path(tmpdir) / "demo-project"
            target.mkdir()
            result = run_scaffold(target)
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            conv = target / "docs" / "conventions.md"
            self.assertTrue(conv.is_file(), "docs/conventions.md must scaffold")
            section = self._decisions_section(conv.read_text()).lower()
            self.assertIn("append-only", section)
            self.assertIn("accepted", section)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
