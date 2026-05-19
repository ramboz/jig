"""
AC verification tests for slice 016-01 (copy-skills-and-agents).

These cases map 1:1 to spec 016's AC #8 (a)..(g) plus a couple of
companions for the new flag, scaffold.json field, and frontmatter
preservation. Each test is named after the AC sub-letter it verifies.

Run as part of the full suite via:
    python3 scripts/run_tests.py
or in isolation:
    python3 skills/scaffold-init/test_scaffold_mode.py
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


def run_scaffold_with_args(target: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke scaffold.py with extra CLI flags before the target path."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), *args, str(target)],
        capture_output=True, text=True, env=env,
    )


# --------------------------------------------------------------------------
# Plugin-only opt-out behavior (slice 016-01 AC #8 (g) PRE-016-03; slice
# 016-03 AC #1 flipped the default ON, so these tests now drive the
# behavior via --plugin-only explicitly. Same invariants — slice 016-01
# `--with-machinery` flag is still default-on; the dormant path is now
# the explicit opt-out.)
# --------------------------------------------------------------------------


class DefaultOffMachineryTests(unittest.TestCase):
    """Slice 016-01 AC #8 (g) — the dormant copy path now reached via
    `--plugin-only` (slice 016-03 flipped the default)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-default-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_g_no_skills_or_agents_dir_without_flag(self):
        """AC #8 (g) — with `--plugin-only`, .claude/skills and
        .claude/agents are NOT created. Pure existing-behavior preservation
        for users who explicitly opted out of scaffold-mode."""
        r = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (self.target / ".claude" / "skills").exists(),
            ".claude/skills must not exist with --plugin-only",
        )
        self.assertFalse(
            (self.target / ".claude" / "agents").exists(),
            ".claude/agents must not exist with --plugin-only",
        )

    def test_scaffold_mode_defaults_to_plugin_only(self):
        """AC #7 — with --plugin-only, scaffold.json.scaffold_mode
        is 'plugin-only'."""
        r = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "plugin-only")


# --------------------------------------------------------------------------
# With --with-machinery: skills/, agents/, path-substitution, etc.
# --------------------------------------------------------------------------


class WithMachineryTests(unittest.TestCase):
    """AC #1..#8 (a..f) — opt-in copy of skills and agents."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-machinery-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        r = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertEqual(
            r.returncode, 0,
            f"scaffold --with-machinery failed: stderr={r.stderr}\nstdout={r.stdout}",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ----- AC #8 (a) --------------------------------------------------------
    def test_a_skill_md_exists_under_jig_prefix(self):
        """AC #8 (a) — .claude/skills/jig-scaffold-init/SKILL.md exists
        and matches the source up to path substitutions."""
        copied = self.target / ".claude" / "skills" / "jig-scaffold-init" / "SKILL.md"
        self.assertTrue(copied.is_file(), f"missing copied SKILL.md: {copied}")
        source = (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").read_text()
        # The "matches source up to path substitutions" claim: rewriting
        # the source the same way and comparing should give exact equality.
        expected = source.replace(
            "${CLAUDE_PLUGIN_ROOT}/skills/scaffold-init/",
            "${CLAUDE_PROJECT_DIR}/.claude/skills/jig-scaffold-init/",
        )
        # All other plugin-root path strings in this SKILL.md (none expected
        # outside the scaffold-init namespace, but be defensive) — verify by
        # generic rewrite.
        expected = re.sub(
            r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/([A-Za-z0-9_-]+)/",
            r"${CLAUDE_PROJECT_DIR}/.claude/skills/jig-\1/",
            expected,
        )
        self.assertEqual(copied.read_text(), expected)

    # ----- AC #8 (b) --------------------------------------------------------
    def test_b_every_plugin_root_skills_path_rewritten(self):
        """AC #8 (b) — every ${CLAUDE_PLUGIN_ROOT}/skills/ in any copied
        SKILL.md has been rewritten."""
        copied_skills = (self.target / ".claude" / "skills").iterdir()
        skill_dirs = [d for d in copied_skills if d.is_dir()]
        self.assertGreater(len(skill_dirs), 0, "no skills copied")
        for d in skill_dirs:
            skill_md = d / "SKILL.md"
            if not skill_md.is_file():
                continue
            body = skill_md.read_text()
            self.assertNotIn(
                "${CLAUDE_PLUGIN_ROOT}/skills/", body,
                f"un-rewritten plugin-root path in {skill_md}",
            )

    # ----- AC #8 (c) --------------------------------------------------------
    def test_c_no_plugin_root_skills_path_remains_in_copied_skill_md(self):
        """AC #8 (c) — no `${CLAUDE_PLUGIN_ROOT}/skills/` occurrences remain
        in any copied SKILL.md (the substitution covers all of them, not a
        subset).

        Scope note: AC #3 mandates rewriting *only* the
        `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` pattern; "no other strings in
        SKILL.md are modified". A subset of source SKILL.md files (notably
        scaffold-init's own) carry incidental
        `${CLAUDE_PLUGIN_ROOT}/templates/` and prose-level
        `${CLAUDE_PLUGIN_ROOT}` mentions that survive the copy unchanged.
        That is intentional per AC #3 and recorded in the deviation log.
        AC #8 (c) is read as "the SKILL.md skills-path substitution covers
        all `.../skills/...` occurrences, not a subset" — which is the
        runtime-relevant invariant; non-skills mentions are documentation
        about plugin mode and don't break scaffolded execution."""
        copied_skills = (self.target / ".claude" / "skills").iterdir()
        skill_dirs = [d for d in copied_skills if d.is_dir()]
        for d in skill_dirs:
            skill_md = d / "SKILL.md"
            if not skill_md.is_file():
                continue
            body = skill_md.read_text()
            self.assertNotIn(
                "${CLAUDE_PLUGIN_ROOT}/skills/", body,
                f"un-rewritten plugin-root skills-path in {skill_md}",
            )

    # ----- AC #8 (d) --------------------------------------------------------
    def test_d_test_files_excluded_from_copy(self):
        """AC #8 (d) — test_*.py files are NOT in .claude/skills/jig-<name>/."""
        copied_skills = (self.target / ".claude" / "skills").iterdir()
        for d in copied_skills:
            if not d.is_dir():
                continue
            for entry in d.rglob("test_*.py"):
                self.fail(f"test file was copied (must be excluded): {entry}")

    # ----- AC #8 (e) --------------------------------------------------------
    def test_e_agent_file_copied_with_jig_prefix(self):
        """AC #8 (e) — .claude/agents/jig-reviewer.md exists with unchanged
        content."""
        copied = self.target / ".claude" / "agents" / "jig-reviewer.md"
        self.assertTrue(copied.is_file(), f"missing copied agent: {copied}")
        source = (REPO_ROOT / "agents" / "reviewer.md").read_text()
        self.assertEqual(
            copied.read_text(), source,
            "agent file content must be byte-identical to source",
        )

    def test_e_all_agents_copied_with_jig_prefix(self):
        """AC #4 — every agents/*.md is copied to .claude/agents/jig-<name>.md."""
        for agent in (REPO_ROOT / "agents").glob("*.md"):
            copied = self.target / ".claude" / "agents" / f"jig-{agent.name}"
            self.assertTrue(copied.is_file(), f"missing copied agent: {copied}")
            self.assertEqual(copied.read_text(), agent.read_text())

    # ----- AC #8 (f) --------------------------------------------------------
    def test_f_scaffold_json_scaffold_mode_in_repo(self):
        """AC #8 (f) — scaffold.json.scaffold_mode == 'in-repo' when the
        flag was passed."""
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "in-repo")

    # ----- AC #2: every skill dir copied with jig- prefix on dir name ------
    def test_every_skill_dir_copied_with_jig_prefix(self):
        """AC #2 — every directory under skills/ becomes
        .claude/skills/jig-<name>/ (excluding _common-style private dirs
        and dirs without a SKILL.md, mirroring run_tests.py's convention)."""
        for source in (REPO_ROOT / "skills").iterdir():
            if not source.is_dir() or source.name.startswith("_"):
                continue
            # Only skill dirs with a SKILL.md are user-facing; the copy
            # treats them as the unit.
            if not (source / "SKILL.md").is_file():
                continue
            copied = self.target / ".claude" / "skills" / f"jig-{source.name}"
            self.assertTrue(
                copied.is_dir(),
                f"missing copied skill dir: {copied} (source: {source})",
            )
            self.assertTrue(
                (copied / "SKILL.md").is_file(),
                f"copied skill dir has no SKILL.md: {copied}",
            )

    # ----- AC #5: frontmatter preserved verbatim ---------------------------
    def test_frontmatter_preserved_byte_for_byte(self):
        """AC #5 — copied SKILL.md keeps its YAML frontmatter intact;
        no re-rendering. Only the body's path strings are touched."""
        source_md = (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").read_text()
        copied_md = (self.target / ".claude" / "skills" / "jig-scaffold-init"
                     / "SKILL.md").read_text()
        # Frontmatter = the content between the first two lines that are
        # exactly '---'.
        source_fm = self._extract_frontmatter(source_md)
        copied_fm = self._extract_frontmatter(copied_md)
        self.assertTrue(source_fm, "source SKILL.md has no frontmatter — "
                                   "test assumption violated")
        self.assertEqual(copied_fm, source_fm,
                         "frontmatter must be byte-identical to source")

    @staticmethod
    def _extract_frontmatter(text: str) -> str:
        """Return the YAML frontmatter block (between leading `---` fences),
        or '' if there is none. Includes the fences."""
        lines = text.splitlines(keepends=True)
        if not lines or lines[0].rstrip("\n") != "---":
            return ""
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].rstrip("\n") == "---":
                end_idx = i
                break
        if end_idx is None:
            return ""
        return "".join(lines[: end_idx + 1])

    # ----- AC #6: helper .py files copied verbatim, test_*.py excluded -----
    def test_helper_py_files_copied_verbatim(self):
        """AC #6 — skill helpers (*.py, excluding test_*.py) are copied
        with no substitution. plugin_root() fallback handles self-location."""
        source = (REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py").read_text()
        copied = (self.target / ".claude" / "skills" / "jig-scaffold-init"
                  / "scaffold.py").read_text()
        self.assertEqual(copied, source,
                         "helper .py must be byte-identical to source")

    # ----- AC #2: jig- prefix is on the directory only, not frontmatter ----
    def test_frontmatter_name_field_unchanged(self):
        """AC #2 — the jig- prefix is on the directory; the frontmatter
        `name` field stays untouched (Claude Code's discovery uses the
        frontmatter, not the directory name)."""
        copied = (self.target / ".claude" / "skills" / "jig-scaffold-init"
                  / "SKILL.md").read_text()
        # Look for the literal frontmatter name line.
        m = re.search(r"(?m)^name:\s*(\S+)\s*$", copied)
        self.assertIsNotNone(m, "frontmatter has no `name:` field")
        self.assertEqual(m.group(1), "scaffold-init",
                         "frontmatter name must stay 'scaffold-init', "
                         "not 'jig-scaffold-init' — the prefix is on the "
                         "directory only.")


# --------------------------------------------------------------------------
# AC #9: regression guard — calling scaffold --with-machinery must NOT
# break any existing scaffold behavior. The existing test_scaffold.py
# suite already covers the without-flag path; here we just sanity-check
# that the with-flag path still produces the canonical docs tree.
# --------------------------------------------------------------------------


class WithMachineryDocsRegressionTests(unittest.TestCase):
    """AC #9 — the canonical scaffold output is unchanged when the flag is
    passed: docs/, CLAUDE.md, scaffold.json, etc. still appear."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-regress-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        r = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_canonical_files_still_created(self):
        for rel in ("CLAUDE.md", "scaffold.json",
                    "docs/architecture.md", "docs/workflow.md",
                    "docs/conventions.md", "docs/memory/glossary.md"):
            self.assertTrue(
                (self.target / rel).exists(),
                f"--with-machinery must not break canonical scaffold: missing {rel}",
            )


# --------------------------------------------------------------------------
# Slice 016-02 — copy hooks + write .claude/settings.json. Cases (h)..(k)
# from AC #6 of slice 016-02. Plus extra tests covering AC #1, #2, #5 and
# the merge-strategy (append-with-marker) behavior for AC #3.
# --------------------------------------------------------------------------


EXPECTED_HOOK_SCRIPTS = (
    "jig-context-check.sh",
    "jig-memory-scan.sh",
    "jig-post-edit-verify.sh",
    "jig-spec-gate.sh",
    "jig-task-capture.sh",
    "jig-telemetry.sh",
)

EXPECTED_HOOK_EVENTS = (
    "PreToolUse", "PostToolUse", "SessionStart", "UserPromptSubmit", "Stop",
)


class CopyHooksAndRegisterTests(unittest.TestCase):
    """Slice 016-02 — clean-create path: no pre-existing settings.json."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-02-hooks-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        r = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertEqual(
            r.returncode, 0,
            f"scaffold --with-machinery failed: stderr={r.stderr}\nstdout={r.stdout}",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ----- AC #6 (h) --------------------------------------------------------
    def test_h_all_hook_scripts_exist_and_are_executable(self):
        """AC #6 (h) — every hook script in EXPECTED_HOOK_SCRIPTS exists
        under .claude/hooks/scripts/ and is executable (0o755)."""
        scripts_dir = self.target / ".claude" / "hooks" / "scripts"
        self.assertTrue(scripts_dir.is_dir(),
                        f".claude/hooks/scripts missing: {scripts_dir}")
        for name in EXPECTED_HOOK_SCRIPTS:
            script = scripts_dir / name
            self.assertTrue(script.is_file(),
                            f"hook script missing: {script}")
            # AC #5 — executable bit set. Check all three exec bits (owner/
            # group/other) — that's what 0o755 implies.
            mode = script.stat().st_mode & 0o777
            self.assertEqual(
                mode, 0o755,
                f"hook script {script} has mode {oct(mode)}, expected 0o755",
            )

    def test_hook_scripts_copied_verbatim(self):
        """AC #1 — hook scripts copy verbatim, no substitution. They
        already use $CLAUDE_PROJECT_DIR exclusively (audit-confirmed)."""
        for name in EXPECTED_HOOK_SCRIPTS:
            source = (REPO_ROOT / "hooks" / "scripts" / name).read_bytes()
            copied = (self.target / ".claude" / "hooks" / "scripts" / name).read_bytes()
            self.assertEqual(source, copied,
                             f"hook script {name} content drifted from source")

    # ----- AC #6 (i) --------------------------------------------------------
    def test_i_settings_json_registers_all_hook_events(self):
        """AC #6 (i) — .claude/settings.json parses as JSON and contains
        entries for all expected hook events referencing
        ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/jig-*.sh."""
        settings_path = self.target / ".claude" / "settings.json"
        self.assertTrue(settings_path.is_file(),
                        f"settings.json missing: {settings_path}")
        settings = json.loads(settings_path.read_text())
        self.assertIn("hooks", settings, "settings.json missing top-level 'hooks'")
        hooks = settings["hooks"]
        for event in EXPECTED_HOOK_EVENTS:
            self.assertIn(event, hooks, f"hook event {event} missing")
            self.assertGreater(len(hooks[event]), 0,
                               f"hook event {event} has no entries")

        # All jig hook commands resolve to project-relative paths.
        plugin_root_refs = re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}",
                                      settings_path.read_text())
        self.assertEqual(plugin_root_refs, [],
                         "settings.json must not contain ${CLAUDE_PLUGIN_ROOT}")
        project_dir_refs = re.findall(
            r"\$\{CLAUDE_PROJECT_DIR\}/\.claude/hooks/scripts/jig-[a-z-]+\.sh",
            settings_path.read_text(),
        )
        # One command reference per hook script.
        self.assertEqual(
            len(project_dir_refs), len(EXPECTED_HOOK_SCRIPTS),
            f"expected {len(EXPECTED_HOOK_SCRIPTS)} ${{CLAUDE_PROJECT_DIR}} "
            f"script refs, got {len(project_dir_refs)}: {project_dir_refs}",
        )

    def test_settings_json_shape_mirrors_source_hooks_json(self):
        """AC #2 — settings.json hook entries mirror hooks/hooks.json:
        matchers and timeouts carry over unchanged."""
        source = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        for event in EXPECTED_HOOK_EVENTS:
            src_event = source["hooks"][event]
            dst_event = settings["hooks"][event]
            self.assertEqual(
                len(src_event), len(dst_event),
                f"hook event {event} entry count drifted",
            )
            for src_entry, dst_entry in zip(src_event, dst_event):
                # matcher (when present) carries over
                self.assertEqual(
                    src_entry.get("matcher"), dst_entry.get("matcher"),
                    f"matcher drifted in {event}",
                )
                # Inner hook list shape
                for src_h, dst_h in zip(src_entry["hooks"], dst_entry["hooks"]):
                    self.assertEqual(src_h.get("type"), dst_h.get("type"))
                    self.assertEqual(src_h.get("timeout"), dst_h.get("timeout"))
                    self.assertEqual(src_h.get("async"), dst_h.get("async"))

    def test_each_jig_hook_entry_carries_managed_by_marker(self):
        """AC #3/AC #4 prep — every jig-managed hook entry carries a
        metadata.managed_by_jig:true marker, so re-runs and the AC #4
        unmanaged-hooks safety check can find it."""
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        for event in EXPECTED_HOOK_EVENTS:
            for entry in settings["hooks"][event]:
                meta = entry.get("metadata") or {}
                self.assertTrue(
                    meta.get("managed_by_jig"),
                    f"hook entry missing managed_by_jig marker: {entry}",
                )


class MergeExistingSettingsTests(unittest.TestCase):
    """Slice 016-02 AC #3 + #6 (j) — merging into a pre-existing
    .claude/settings.json. Strategy: append-with-marker. Non-hook fields
    pass through. Existing user hooks survive untouched. jig hooks land
    with metadata.managed_by_jig:true."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-02-merge-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seed_settings(self, payload: dict) -> None:
        settings = self.target / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(payload, indent=2) + "\n")

    # ----- AC #6 (j) --------------------------------------------------------
    def test_j_existing_non_hook_field_preserved(self):
        """AC #6 (j) — merge into existing settings.json: a non-hook
        top-level field (e.g. 'permissions') is preserved after the merge."""
        self._seed_settings({
            "permissions": {"allow": ["Bash(ls)"]},
            "env": {"FOO": "bar"},
        })
        r = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        merged = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        # Non-hook fields survive.
        self.assertEqual(merged.get("permissions"), {"allow": ["Bash(ls)"]})
        self.assertEqual(merged.get("env"), {"FOO": "bar"})
        # jig hooks were appended.
        self.assertIn("hooks", merged)
        for event in EXPECTED_HOOK_EVENTS:
            self.assertIn(event, merged["hooks"])

    def test_existing_user_hooks_under_other_matcher_preserved(self):
        """AC #3 — pre-existing hook entries that are NOT jig-managed
        survive the merge. We seed a hook entry under PreToolUse with a
        different matcher; after scaffolding (with --force, per AC #4's
        safety stance) it should still be there."""
        user_hook_entry = {
            "matcher": "Read",
            "hooks": [
                {"type": "command",
                 "command": "bash ./scripts/user-pre-read.sh",
                 "timeout": 5}
            ],
        }
        self._seed_settings({"hooks": {"PreToolUse": [user_hook_entry]}})
        # --force is the documented escape hatch for unmanaged hooks
        # (AC #4). Without it scaffold refuses; with it, the merge appends.
        r = run_scaffold_with_args(self.target, "--with-machinery", "--force")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        merged = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        pre_tool_use = merged["hooks"]["PreToolUse"]
        # The user's Read-matcher entry survives.
        user_present = any(
            entry.get("matcher") == "Read"
            and entry.get("hooks", [{}])[0].get("command", "").endswith(
                "user-pre-read.sh"
            )
            for entry in pre_tool_use
        )
        self.assertTrue(
            user_present,
            f"user's Read-matcher hook was clobbered: {pre_tool_use}",
        )
        # And jig's marker-bearing entries are present too.
        jig_present = any(
            (entry.get("metadata") or {}).get("managed_by_jig")
            for entry in pre_tool_use
        )
        self.assertTrue(jig_present, "jig hooks not present after merge")

    def test_idempotent_rerun_does_not_duplicate_jig_entries(self):
        """AC #3 — re-running scaffold over a settings.json that ALREADY
        has jig-marked entries replaces them in place, doesn't duplicate."""
        # First run — clean create.
        r1 = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertEqual(r1.returncode, 0, f"stderr: {r1.stderr}")
        # Second run with --force (since scaffold.json now exists).
        r2 = run_scaffold_with_args(self.target, "--with-machinery", "--force")
        self.assertEqual(r2.returncode, 0, f"stderr: {r2.stderr}")
        merged = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        for event in EXPECTED_HOOK_EVENTS:
            jig_entries = [
                entry for entry in merged["hooks"][event]
                if (entry.get("metadata") or {}).get("managed_by_jig")
            ]
            # Source hooks.json has exactly one entry per event for jig
            # (matchers under PreToolUse differ but each is a separate
            # event-array element).
            source = json.loads(
                (REPO_ROOT / "hooks" / "hooks.json").read_text()
            )
            expected = len(source["hooks"][event])
            self.assertEqual(
                len(jig_entries), expected,
                f"event {event}: expected {expected} jig entries after "
                f"idempotent re-run, got {len(jig_entries)}",
            )

    # ----- AC #6 (k) --------------------------------------------------------
    def test_k_refuse_on_unmanaged_hooks(self):
        """AC #6 (k) / AC #4 — an existing settings.json with hooks but
        no jig marker raises and exits non-zero. Same safety stance as
        AlreadyScaffoldedError."""
        self._seed_settings({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit",
                     "hooks": [{"type": "command",
                                "command": "bash ./user-edit.sh",
                                "timeout": 5}]}
                ]
            }
        })
        r = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertNotEqual(
            r.returncode, 0,
            "scaffold must refuse when settings.json has unmanaged hooks; "
            f"stdout={r.stdout!r} stderr={r.stderr!r}",
        )
        # Error message hints at --force as the escape hatch.
        self.assertIn("--force", r.stderr,
                      f"refuse-message should mention --force: {r.stderr}")

    def test_refused_scaffold_leaves_no_partial_hook_scripts(self):
        """Regression for slice 016-03 deviation log §7 — when
        UnmanagedHooksError fires, the scaffold MUST NOT have written any
        `.claude/hooks/scripts/jig-*.sh` files. Before the §7 follow-up,
        the safety check ran AFTER the copy loop, leaving partial state
        behind on refuse. The fix moves the check to the top of
        `_copy_hooks_and_register`; this test pins that ordering."""
        self._seed_settings({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit",
                     "hooks": [{"type": "command",
                                "command": "bash ./user-edit.sh",
                                "timeout": 5}]}
                ]
            }
        })
        r = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertNotEqual(r.returncode, 0,
                            "scaffold should refuse on unmanaged hooks")
        scripts_dir = self.target / ".claude" / "hooks" / "scripts"
        if scripts_dir.exists():
            jig_scripts = list(scripts_dir.glob("jig-*.sh"))
            self.assertEqual(
                jig_scripts, [],
                f"refused scaffold left partial state: {jig_scripts}. "
                "The safety check must run BEFORE the hook-script copy "
                "loop so a refused scaffold leaves no trace.",
            )

    def test_force_overrides_unmanaged_hooks_refusal(self):
        """AC #4 — --force is the documented escape hatch. With it, the
        merge proceeds even when no jig marker is present."""
        existing = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit",
                     "hooks": [{"type": "command",
                                "command": "bash ./user-edit.sh",
                                "timeout": 5}]}
                ]
            }
        }
        self._seed_settings(existing)
        r = run_scaffold_with_args(self.target, "--with-machinery", "--force")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        merged = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        # User's entry survived.
        pre_tool_use = merged["hooks"]["PreToolUse"]
        user_present = any(
            entry.get("matcher") == "Edit"
            and entry.get("hooks", [{}])[0].get("command", "").endswith(
                "user-edit.sh"
            )
            for entry in pre_tool_use
        )
        self.assertTrue(
            user_present,
            "user's Edit-matcher hook was clobbered under --force",
        )

    def test_default_off_does_not_write_settings_or_hooks(self):
        """AC #1 — with --plugin-only, no hook scripts, no settings.json.
        Pure existing-behavior preservation for users who opt out.
        (Slice 016-03 flipped the default, so this case is now reached
        via the explicit opt-out flag rather than absent-by-default.)"""
        r = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (self.target / ".claude" / "hooks" / "scripts").exists(),
            ".claude/hooks/scripts must not exist with --plugin-only",
        )
        self.assertFalse(
            (self.target / ".claude" / "settings.json").exists(),
            ".claude/settings.json must not exist with --plugin-only",
        )


# --------------------------------------------------------------------------
# Slice 016-03 — default flip + --plugin-only opt-out + dogfood regression
# --------------------------------------------------------------------------


class DefaultOnMachineryTests(unittest.TestCase):
    """Slice 016-03 AC #1 — `--with-machinery` is now default-on. Running
    scaffold without flags produces a fully-scaffolded `.claude/` tree."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-03-default-on-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_includes_machinery(self):
        """AC #1 — no flag → machinery copied. scaffold_mode is 'in-repo'."""
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertTrue(
            (self.target / ".claude" / "skills" / "jig-scaffold-init"
             / "SKILL.md").is_file(),
            "default scaffold should include skills/",
        )
        self.assertTrue(
            (self.target / ".claude" / "agents" / "jig-reviewer.md").is_file(),
            "default scaffold should include agents/",
        )
        self.assertTrue(
            (self.target / ".claude" / "hooks" / "scripts").is_dir(),
            "default scaffold should include hooks/scripts/",
        )
        self.assertTrue(
            (self.target / ".claude" / "settings.json").is_file(),
            "default scaffold should write settings.json",
        )
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "in-repo")


class PluginOnlyOptOutTests(unittest.TestCase):
    """Slice 016-03 AC #1 — `--plugin-only` opts out, preserving the old
    docs-only behavior (scaffold_mode: plugin-only, no .claude/skills/
    or .claude/agents/)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-03-plugin-only-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_plugin_only_skips_machinery(self):
        r = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (self.target / ".claude" / "skills").exists(),
            "--plugin-only must not create .claude/skills/",
        )
        self.assertFalse(
            (self.target / ".claude" / "agents").exists(),
            "--plugin-only must not create .claude/agents/",
        )
        self.assertFalse(
            (self.target / ".claude" / "hooks" / "scripts").exists(),
            "--plugin-only must not create .claude/hooks/scripts/",
        )
        self.assertFalse(
            (self.target / ".claude" / "settings.json").exists(),
            "--plugin-only must not write .claude/settings.json",
        )
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "plugin-only")

    def test_plugin_only_and_with_machinery_are_exclusive(self):
        """Passing both --plugin-only and --with-machinery is a usage
        error (argparse mutually-exclusive group, exit 2)."""
        r = run_scaffold_with_args(
            self.target, "--plugin-only", "--with-machinery",
        )
        self.assertNotEqual(
            r.returncode, 0,
            "passing both flags must be rejected by argparse",
        )


class DogfoodVerifyInstallScaffoldTests(unittest.TestCase):
    """Slice 016-03 AC #6 — regression-pin the dogfood shape by scaffolding
    into a tmpdir and asserting all four `verify_install.py --mode scaffold`
    checks pass on the resulting tree.

    The automation backstop for AC #5. If this test fails, the end-to-end
    dogfood is broken too — the structural rewrite has regressed."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-03-dogfood-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        # Default-on scaffold (no flags); 016-03 made this fully wire up
        # the .claude/ tree.
        r = run_scaffold_with_args(self.target)
        self.assertEqual(
            r.returncode, 0,
            f"scaffold failed: stderr={r.stderr}\nstdout={r.stdout}",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_verify_install_scaffold_mode_all_checks_pass(self):
        """AC #6 — `verify_install.py --mode scaffold --project-root <target>`
        runs four PASS checks against the freshly-scaffolded tree."""
        verify = REPO_ROOT / "scripts" / "verify_install.py"
        r = subprocess.run(
            [
                sys.executable, str(verify),
                "--mode", "scaffold",
                "--project-root", str(self.target),
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(
            r.returncode, 0,
            f"verify_install --mode scaffold failed: rc={r.returncode}\n"
            f"stdout={r.stdout}\nstderr={r.stderr}",
        )
        # Four PASS lines + 1 summary line.
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        pass_lines = [ln for ln in lines if ln.startswith("PASS")]
        self.assertEqual(
            len(pass_lines), 4,
            f"expected 4 PASS lines; got {len(pass_lines)}: {r.stdout!r}",
        )


if __name__ == "__main__":
    unittest.main()
