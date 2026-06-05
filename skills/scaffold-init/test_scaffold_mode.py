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

import tomllib

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
        # `--has-tests` forces tier-1 into installed_tiers so the FULL
        # 14-skill set is copied. Slice 038-02 made the copy tier-gated;
        # these tests verify copy *mechanics* (path rewrite, test-file
        # exclusion, jig- prefixing, quality.py retention) on tier-1
        # skills like `tdd-loop`, so they need the full set present.
        # Tier-gating itself is covered by TierGatedCopyTests.
        r = run_scaffold_with_args(self.target, "--with-machinery", "--has-tests")
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

    # ----- Spec 063-02 AC #5: Step-0 precondition parity --------------------
    def test_spec_workflow_scaffold_copy_carries_step0_precondition(self):
        """Spec 063-02 AC #5 — the SKILL.md copied into a scaffolded target
        carries the Step 0 scaffold-state precondition + both routing
        targets, so the plugin and scaffolded prose can't drift. scaffold
        copies the live SKILL.md body (only path-substituted), so parity is
        structural; this test pins it against silent regression."""
        copied = (
            self.target / ".claude" / "skills"
            / "jig-spec-workflow" / "SKILL.md"
        )
        self.assertTrue(copied.is_file(), f"missing copied SKILL.md: {copied}")
        body = copied.read_text()
        lower = body.lower()
        self.assertIn(
            "step 0", lower,
            "scaffolded spec-workflow SKILL.md must carry the Step 0 "
            "scaffold-state precondition (063-02 AC5)",
        )
        self.assertIn(
            "/jig:scaffold-init", body,
            "scaffolded spec-workflow SKILL.md must route greenfield to "
            "/jig:scaffold-init",
        )
        self.assertIn(
            "/jig:migrate", body,
            "scaffolded spec-workflow SKILL.md must route existing layouts "
            "to /jig:migrate",
        )
        self.assertIn(
            "slices/", body,
            "scaffolded spec-workflow SKILL.md must name the loose-`slices/` "
            "anti-pattern (063-02 AC3 propagates to the scaffold copy)",
        )

    # ----- Spec 066-02 AC #5: ADR Step-0 precondition parity ----------------
    def test_adr_workflow_scaffold_copy_carries_step0_precondition(self):
        """Spec 066-02 AC #5 — the adr-workflow SKILL.md copied into a
        scaffolded target carries the Step 0 scaffold-state precondition +
        both routing targets, so the plugin and scaffolded prose can't
        drift. adr-workflow is a Tier-1 skill (`_TIER_SKILLS["tier-1"]`)
        and scaffold copies the live SKILL.md body (only path-substituted,
        same as spec-workflow), so parity is structural; this test pins it
        against silent regression. Mirrors the 063-02 spec-workflow parity
        test above."""
        copied = (
            self.target / ".claude" / "skills"
            / "jig-adr-workflow" / "SKILL.md"
        )
        self.assertTrue(copied.is_file(), f"missing copied SKILL.md: {copied}")
        body = copied.read_text()
        lower = body.lower()
        self.assertIn(
            "step 0", lower,
            "scaffolded adr-workflow SKILL.md must carry the Step 0 "
            "scaffold-state precondition (066-02 AC5)",
        )
        self.assertIn(
            "/jig:scaffold-init", body,
            "scaffolded adr-workflow SKILL.md must route greenfield to "
            "/jig:scaffold-init",
        )
        self.assertIn(
            "/jig:migrate", body,
            "scaffolded adr-workflow SKILL.md must route existing layouts "
            "to /jig:migrate",
        )
        self.assertIn(
            "docs/decisions/", body,
            "scaffolded adr-workflow SKILL.md must name the "
            "docs/decisions/-skeleton anti-pattern (066-02 AC3 propagates "
            "to the scaffold copy)",
        )

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
        """AC #8 (d) — test_*.py files are NOT in .claude/skills/jig-<name>/,
        with one exception: spec 043-04 retains
        `skills/tdd-loop/test_quality.py` (and `test_quality.py` only) so
        a scaffolded project's review.py can exercise the quality.py
        snapshot helper end-to-end. See `_RETAINED_TEST_FILES` in
        scaffold.py."""
        copied_skills = (self.target / ".claude" / "skills").iterdir()
        for d in copied_skills:
            if not d.is_dir():
                continue
            for entry in d.rglob("test_*.py"):
                # Allowlist: tdd-loop's test_quality.py is the test
                # surface for the quality.py snapshot helper that
                # review.py shells out to. Spec 043-04 AC #7.
                if (
                    d.name == "jig-tdd-loop"
                    and entry.name == "test_quality.py"
                ):
                    continue
                self.fail(f"test file was copied (must be excluded): {entry}")

    # ----- Spec 043-04 AC #7: tdd-loop's quality.py + test_quality.py ------
    def test_tdd_loop_quality_py_copied(self):
        """Spec 043-04 AC #7: a fresh scaffold-init has
        `skills/tdd-loop/quality.py` reachable so review.py's snapshot
        helper can shell out to it."""
        qpath = (
            self.target / ".claude" / "skills"
            / "jig-tdd-loop" / "quality.py"
        )
        self.assertTrue(
            qpath.is_file(),
            f"scaffolded project missing quality.py: {qpath}",
        )
        # And it should be byte-identical to the source (helper .py copied
        # verbatim — no substitution).
        source = (REPO_ROOT / "skills" / "tdd-loop" / "quality.py").read_bytes()
        self.assertEqual(qpath.read_bytes(), source)

    def test_tdd_loop_test_quality_py_copied(self):
        """Spec 043-04 AC #7: scaffolded project also carries
        `test_quality.py` so the snapshot wiring is testable end-to-end
        in adopter projects (an exception to the general
        `test_*.py`-excluded rule — see `_RETAINED_TEST_FILES` in
        scaffold.py)."""
        tqpath = (
            self.target / ".claude" / "skills"
            / "jig-tdd-loop" / "test_quality.py"
        )
        self.assertTrue(
            tqpath.is_file(),
            f"scaffolded project missing test_quality.py: {tqpath}",
        )
        source = (REPO_ROOT / "skills" / "tdd-loop" / "test_quality.py").read_bytes()
        self.assertEqual(tqpath.read_bytes(), source)

    def test_tdd_loop_other_test_files_still_excluded(self):
        """Spec 043-04 AC #7: the allow-list is narrow — `test_tdd.py`
        (the OTHER test file in tdd-loop) must still be excluded."""
        td = self.target / ".claude" / "skills" / "jig-tdd-loop"
        self.assertTrue(td.is_dir())
        self.assertFalse(
            (td / "test_tdd.py").exists(),
            "test_tdd.py must remain excluded — only test_quality.py "
            "is retained per the spec 043-04 allow-list",
        )

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

    # ----- Shared modules: `_common/` is copied unprefixed -----------------
    def test_common_module_copied_unprefixed(self):
        """`_common/` is copied to `.claude/skills/_common/` (no `jig-`
        prefix) so helpers' `from _common.parsing import ...` resolves.
        Helpers `sys.path.insert(0, parent.parent)` lands on
        `.claude/skills/`, making `_common/` a sibling."""
        common = self.target / ".claude" / "skills" / "_common"
        self.assertTrue(common.is_dir(), f"missing `_common/`: {common}")
        self.assertTrue((common / "parsing.py").is_file(),
                        "`_common/parsing.py` must be copied")
        self.assertFalse((common / "test_parsing.py").exists(),
                         "test files must still be excluded from `_common/`")

    def test_scaffolded_helper_imports_common_at_runtime(self):
        """End-to-end: running a scaffolded helper subprocess must not
        ModuleNotFoundError on `_common.parsing`. The import happens at
        module load before argparse, so `--help` is enough to exercise it."""
        helper = (self.target / ".claude" / "skills" / "jig-spec-workflow"
                  / "workflow.py")
        self.assertTrue(helper.is_file(), f"scaffolded helper missing: {helper}")
        r = subprocess.run(
            [sys.executable, str(helper), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(
            r.returncode, 0,
            f"scaffolded helper failed at import-time:\n"
            f"stderr={r.stderr}\nstdout={r.stdout}",
        )
        self.assertNotIn("ModuleNotFoundError", r.stderr)


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
    "jig-boundary-change-warn.sh",
    "jig-context-check.sh",
    "jig-memory-scan.sh",
    "jig-post-edit-verify.sh",
    "jig-secret-scan.sh",  # slice 052-02 — secret-prevention floor (ADR-0013)
    "jig-skill-trace.sh",
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

    def test_hook_lib_directory_copied(self):
        """Slice 026-01 — hooks/scripts/lib/ ships beside the .sh files so
        jig-context-check.sh can import the context_fill helper after a
        scaffold install (not just in the source plugin tree). Test
        modules (test_*.py) are NOT shipped — runtime only."""
        src_lib = REPO_ROOT / "hooks" / "scripts" / "lib"
        if not src_lib.is_dir():
            self.skipTest("source hooks/scripts/lib/ missing")
        dst_lib = self.target / ".claude" / "hooks" / "scripts" / "lib"
        self.assertTrue(dst_lib.is_dir(),
                        f"scaffolded lib/ missing: {dst_lib}")
        # Every runtime .py in the source lib/ is present and byte-
        # identical in the scaffolded copy. test_*.py is excluded.
        runtime_pys = [p for p in sorted(src_lib.glob("*.py"))
                       if not p.name.startswith("test_")]
        self.assertGreater(len(runtime_pys), 0,
                           "source lib/ has no runtime .py files")
        for src_py in runtime_pys:
            dst_py = dst_lib / src_py.name
            self.assertTrue(dst_py.is_file(),
                            f"scaffolded lib/{src_py.name} missing")
            self.assertEqual(src_py.read_bytes(), dst_py.read_bytes(),
                             f"lib/{src_py.name} content drifted")
        # And tests are NOT shipped.
        for src_py in sorted(src_lib.glob("test_*.py")):
            self.assertFalse((dst_lib / src_py.name).exists(),
                             f"test module {src_py.name} should not ship")

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
        # One ${CLAUDE_PROJECT_DIR} ref per source command (a script may be
        # registered on more than one event — e.g. slice 055-02 wires
        # jig-context-check.sh onto both SessionStart and UserPromptSubmit).
        source = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        source_cmd_count = sum(
            1
            for entries in source["hooks"].values()
            for entry in entries
            for _ in entry.get("hooks", [])
        )
        self.assertEqual(
            len(project_dir_refs), source_cmd_count,
            f"expected {source_cmd_count} ${{CLAUDE_PROJECT_DIR}} script refs "
            f"(one per source command), got {len(project_dir_refs)}: "
            f"{project_dir_refs}",
        )
        # Every distinct hook script still appears at least once.
        for name in EXPECTED_HOOK_SCRIPTS:
            self.assertTrue(
                any(name in ref for ref in project_dir_refs),
                f"hook script {name} missing from settings.json refs",
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
            for src_entry, dst_entry in zip(src_event, dst_event, strict=True):
                # matcher (when present) carries over
                self.assertEqual(
                    src_entry.get("matcher"), dst_entry.get("matcher"),
                    f"matcher drifted in {event}",
                )
                # Inner hook list shape
                for src_h, dst_h in zip(src_entry["hooks"], dst_entry["hooks"], strict=True):
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

    def test_pretooluse_registers_read_context_check(self):
        """Slice 055-03 (AC #5) — the read-once / read-lean nudge is wired
        into the generated settings.json: jig-context-check.sh appears under
        PreToolUse with matcher 'Read', so scaffolded projects receive the
        duplicate/large-read nudge, not just the jig repo. The pre-existing
        PreToolUse matchers (e.g. the spec-gate's Edit|Write|MultiEdit) are
        untouched."""
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        pre_tool_use = settings["hooks"]["PreToolUse"]
        read_entries = [
            entry for entry in pre_tool_use
            if entry.get("matcher") == "Read"
            and any("jig-context-check.sh" in h.get("command", "")
                    for h in entry.get("hooks", []))
        ]
        self.assertEqual(
            len(read_entries), 1,
            f"expected exactly one PreToolUse matcher:Read jig-context-check "
            f"entry; got: {pre_tool_use}",
        )
        # Project-relative path, not plugin-root.
        cmd = read_entries[0]["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/", cmd)
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", cmd)
        # The spec-gate's Edit|Write|MultiEdit matcher still present.
        self.assertTrue(
            any(entry.get("matcher") == "Edit|Write|MultiEdit"
                for entry in pre_tool_use),
            "pre-existing PreToolUse spec-gate matcher was disturbed",
        )

    def test_userpromptsubmit_registers_context_check(self):
        """Slice 055-02 (AC #7) — the in-session growth nudge is wired into
        the generated settings.json: jig-context-check.sh appears under
        UserPromptSubmit (the same script that runs on SessionStart), so
        scaffolded projects get the mid-session nudge, not just the jig
        repo."""
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        ups_commands = [
            h.get("command", "")
            for entry in settings["hooks"]["UserPromptSubmit"]
            for h in entry.get("hooks", [])
        ]
        self.assertTrue(
            any("jig-context-check.sh" in c for c in ups_commands),
            f"jig-context-check.sh must be registered on UserPromptSubmit; "
            f"got: {ups_commands}",
        )
        # The command resolves to the project-relative path, not plugin-root.
        ctx_cmds = [c for c in ups_commands if "jig-context-check.sh" in c]
        for c in ctx_cmds:
            self.assertIn("${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/", c)
            self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", c)


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
        top-level field (e.g. 'env') is preserved after the merge.

        Note (slice 052-03): `permissions.deny` is now jig-managed (the
        destructive-command guardrail), so `permissions` is no longer an
        untouched pass-through field — its `deny` array gains jig's defaults
        while `allow` (and any other key) is preserved verbatim. `env` is
        the pure untouched-field assertion here; the full permissions-merge
        contract lives in test_scaffold.py::PermissionsDenyTests."""
        self._seed_settings({
            "permissions": {"allow": ["Bash(ls)"]},
            "env": {"FOO": "bar"},
        })
        r = run_scaffold_with_args(self.target, "--with-machinery")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        merged = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        # A genuine non-hook, non-permissions field survives untouched.
        self.assertEqual(merged.get("env"), {"FOO": "bar"})
        # permissions.allow is preserved verbatim; permissions.deny gains
        # jig's destructive-command defaults (slice 052-03).
        self.assertEqual(merged.get("permissions", {}).get("allow"), ["Bash(ls)"])
        self.assertIn("Bash(git push --force*)",
                      merged.get("permissions", {}).get("deny", []))
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
        runs all scaffold-mode checks PASS against the freshly-scaffolded
        tree. Slice 052-04 grew the set from 4 to 7 (the security-floor
        checks); the count is asserted against `_SCAFFOLD_CHECKS` so it
        tracks the source of truth rather than a hard-coded number."""
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
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import verify_install  # noqa: E402
        expected = len(verify_install._SCAFFOLD_CHECKS)
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        pass_lines = [ln for ln in lines if ln.startswith("PASS")]
        self.assertEqual(
            len(pass_lines), expected,
            f"expected {expected} PASS lines; got {len(pass_lines)}: "
            f"{r.stdout!r}",
        )


# --------------------------------------------------------------------------
# Slice 032-02 — scaffold-completion-marker. `scaffold.json` is written
# last; a crash before that final write leaves a re-runnable partial
# state. Two new tests:
#   AC #2 — crash-before-scaffold.json leaves a re-runnable state.
#   AC #5 — refused scaffold (UnmanagedHooksError) leaves no scaffold.json,
#           so the next run treats it as un-scaffolded and re-attempts.
# These tests import scaffold.py directly so we can monkey-patch
# `atomic_write_text` for the crash-simulation case. The existing
# subprocess-based tests above remain the canonical end-to-end coverage.
# --------------------------------------------------------------------------


sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
import scaffold as scaffold_mod  # noqa: E402


class CodexScaffoldAdapterTests(unittest.TestCase):
    """Slice 033-05/07 — Codex scaffold output is host-native."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-033-codex-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_codex_scaffold(self, *extra_args: str) -> subprocess.CompletedProcess:
        return run_scaffold_with_args(self.target, "--host", "codex", *extra_args)

    def test_codex_scaffold_tree_has_no_claude_only_files(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout={r.stdout}")

        for rel in (
            "AGENTS.md",
            "scaffold.json",
            ".codex/hooks.json",
            ".codex/skills/jig-scaffold-init/SKILL.md",
            ".codex/agents/jig-reviewer.toml",
            ".codex/hooks/scripts/jig-context-check.sh",
        ):
            self.assertTrue(
                (self.target / rel).is_file(),
                f"missing Codex scaffold file: {rel}",
            )

        for rel in ("CLAUDE.md", ".claude", ".agents", ".codex-plugin"):
            self.assertFalse(
                (self.target / rel).exists(),
                f"Codex scaffold should not create Claude-only path: {rel}",
            )

        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("host_renderer"), "codex")
        self.assertEqual(manifest.get("scaffold_mode"), "in-repo")

    def test_codex_skills_are_rewritten_to_project_runtime_paths(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        copied = (
            self.target / ".codex" / "skills" / "jig-scaffold-init"
            / "SKILL.md"
        ).read_text()
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", copied)
        self.assertNotIn("CLAUDE_PROJECT_DIR", copied)
        self.assertNotIn("CLAUDE.md", copied)
        self.assertNotIn(".claude/", copied)
        self.assertIn(
            "${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-scaffold-init/",
            copied,
        )
        self.assertIn(
            "${CODEX_PROJECT_DIR:-$PWD}/.codex/templates/",
            copied,
        )
        self.assertIn("--host codex", copied)

        common = self.target / ".codex" / "skills" / "_common"
        self.assertTrue((common / "parsing.py").is_file())
        self.assertFalse((common / "test_parsing.py").exists())

    def test_codex_review_skills_use_codex_user_skill_locations(self):
        r = self._run_codex_scaffold("--has-tests")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        for skill in ("pr-review", "arch-review", "contracts"):
            copied = (
                self.target / ".codex" / "skills" / f"jig-{skill}"
                / "SKILL.md"
            ).read_text()
            self.assertIn(
                f"$HOME/.agents/skills/{skill}/",
                copied,
                f"Codex-rendered {skill} should name Codex's user skill path",
            )
            self.assertNotIn(
                "~/.claude/skills",
                copied,
                f"Codex-rendered {skill} leaked Claude skill path guidance",
            )
            self.assertNotIn(
                "~/.codex/skills",
                copied,
                f"Codex-rendered {skill} invented an unsupported skill path",
            )
            self.assertNotIn(
                "Codex skill router",
                copied,
                f"Codex-rendered {skill} should use documented skill-selection wording",
            )
            self.assertNotIn(
                "router will prefer",
                copied,
                f"Codex-rendered {skill} should not promise router precedence",
            )

        pr_review = (
            self.target / ".codex" / "skills" / "jig-pr-review" / "SKILL.md"
        ).read_text()
        self.assertIn(
            "Codex-rendered guidance keeps richer-skill deferral to "
            "interactive skill selection or explicit invocation",
            pr_review,
        )

    def test_codex_agents_materialize_as_toml(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        expected_sandbox = {
            "architect": "read-only",
            "implementer": "workspace-write",
            "reviewer": "read-only",
        }
        for role, sandbox in expected_sandbox.items():
            agent = self.target / ".codex" / "agents" / f"jig-{role}.toml"
            self.assertTrue(agent.is_file(), f"missing Codex agent: {agent}")
            data = tomllib.loads(agent.read_text())
            self.assertEqual(data["name"], f"jig-{role}")
            self.assertEqual(data["sandbox_mode"], sandbox)
            self.assertIn("Codex adapter note", data["developer_instructions"])
            self.assertNotIn(".claude", data["developer_instructions"])
            self.assertNotIn("CLAUDE.md", data["developer_instructions"])

    def test_codex_agent_installer_writes_toml_to_requested_dir(self):
        agents_dir = Path(self.tmpdir) / "global-codex-agents"
        r = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD),
                "--install-codex-agents",
                "--codex-agents-dir",
                str(agents_dir),
            ],
            cwd=self.target,
            capture_output=True,
            text=True,
            env={},
        )

        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn("installed 3 Codex agent(s)", r.stdout)
        data = tomllib.loads((agents_dir / "jig-reviewer.toml").read_text())
        self.assertEqual(data["name"], "jig-reviewer")
        self.assertEqual(data["sandbox_mode"], "read-only")

    def test_codex_agent_renderer_requires_explicit_sandbox_mapping(self):
        agent = Path(self.tmpdir) / "triager.md"
        agent.write_text(
            "---\n"
            "description: Triage incoming implementation work.\n"
            "---\n"
            "You triage incoming implementation work.\n"
        )

        with self.assertRaisesRegex(
            scaffold_mod.CodexAgentRoleError,
            "No Codex sandbox mapping configured",
        ):
            scaffold_mod.CodexScaffoldRenderer.render_codex_agent_toml(agent)

    def test_codex_agent_installer_refuses_user_owned_file(self):
        agents_dir = Path(self.tmpdir) / "global-codex-agents"
        agents_dir.mkdir()
        user_owned = agents_dir / "jig-reviewer.toml"
        user_owned.write_text("name = 'my-reviewer'\n")

        r = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD),
                "--install-codex-agents",
                "--codex-agents-dir",
                str(agents_dir),
            ],
            cwd=self.target,
            capture_output=True,
            text=True,
            env={},
        )

        self.assertEqual(r.returncode, 3)
        self.assertIn("--force", r.stderr)
        self.assertEqual(user_owned.read_text(), "name = 'my-reviewer'\n")
        self.assertFalse((agents_dir / "jig-architect.toml").exists())
        self.assertFalse((agents_dir / "jig-implementer.toml").exists())

    def test_codex_hooks_json_registers_all_logical_hooks(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        hooks_path = self.target / ".codex" / "hooks.json"
        payload = json.loads(hooks_path.read_text())
        self.assertTrue(payload.get("metadata", {}).get("managed_by_jig"))
        self.assertEqual(sorted(payload["hooks"].keys()), sorted(EXPECTED_HOOK_EVENTS))

        text = hooks_path.read_text()
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", text)
        self.assertNotIn("CLAUDE_PROJECT_DIR", text)
        for script in EXPECTED_HOOK_SCRIPTS:
            self.assertIn(
                f"${{CODEX_PROJECT_DIR:-$PWD}}/.codex/hooks/scripts/{script}",
                text,
            )
            path = self.target / ".codex" / "hooks" / "scripts" / script
            self.assertTrue(path.is_file(), f"missing hook script: {path}")
            self.assertEqual(path.stat().st_mode & 0o777, 0o755)

    def test_codex_refuses_existing_unmanaged_hooks_before_runtime_copy(self):
        hooks_path = self.target / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True)
        hooks_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Read",
                        "hooks": [{"type": "command", "command": "./user.sh"}],
                    }
                ]
            }
        }, indent=2) + "\n")

        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 3)
        self.assertIn("--force", r.stderr)
        self.assertFalse((self.target / ".codex" / "skills").exists())
        self.assertEqual(
            list((self.target / ".codex").glob("hooks/scripts/jig-*.sh")),
            [],
        )


class ScaffoldCompletionMarkerTests(unittest.TestCase):
    """Slice 032-02 — `scaffold.json` is the completion sentinel: written
    last, after every other filesystem mutation, so a crash mid-scaffold
    leaves a re-runnable partial state without `--force`."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-032-02-marker-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_watermark_constant_is_present_in_claude_md_template(self):
        """Slice 032-02 reconciliation pin — `_is_jig_partial_state` reads
        `CLAUDE.md` for `_JIG_CLAUDE_MD_WATERMARK`. If the watermark string
        ever drifts out of `templates/CLAUDE.md.template`, the recovery
        path for AC #2 silently breaks (the gate returns False and
        `_looks_already_spec_driven` blocks the re-run). Pin the coupling
        with a substring check on the template file."""
        template = REPO_ROOT / "templates" / "CLAUDE.md.template"
        self.assertTrue(template.is_file(), f"template missing: {template}")
        self.assertIn(
            scaffold_mod._JIG_CLAUDE_MD_WATERMARK,
            template.read_text(),
            "CLAUDE.md.template lost the jig watermark — "
            "scaffold partial-state recovery will silently fail.",
        )

    def test_crash_before_scaffold_json_leaves_rerunnable_state(self):
        """AC #2 — a simulated crash on the `scaffold.json` write leaves no
        `scaffold.json` on disk. Re-running scaffold without `--force`
        succeeds and produces a well-formed final scaffold.

        Strategy: monkey-patch `atomic_write_text` inside the scaffold
        module so that the call writing `scaffold.json` raises a synthetic
        IOError. Verify on disk that `scaffold.json` is absent. Then call
        `scaffold()` again on the same target without `--force` and assert
        success + a valid `scaffold.json`."""
        original = scaffold_mod.atomic_write_text

        def patched(path, content, *, encoding="utf-8"):
            if path.name == "scaffold.json":
                raise IOError("simulated crash mid-scaffold")
            return original(path, content, encoding=encoding)

        scaffold_mod.atomic_write_text = patched
        try:
            with self.assertRaises(IOError):
                scaffold_mod.scaffold(
                    self.target, scaffold_mod.plugin_root(),
                )
        finally:
            scaffold_mod.atomic_write_text = original

        # On-disk invariant: no scaffold.json — the completion sentinel
        # never landed, so the partial state is re-runnable.
        self.assertFalse(
            (self.target / "scaffold.json").exists(),
            "scaffold.json must be absent after simulated crash mid-write",
        )

        # Re-run without --force. Must succeed: the "already scaffolded"
        # check gates on scaffold.json presence, which is absent, so the
        # re-run proceeds to a normal greenfield scaffold.
        r = run_scaffold_with_args(self.target)
        self.assertEqual(
            r.returncode, 0,
            f"re-run without --force must succeed after crash: stderr={r.stderr}",
        )
        # The final scaffold.json is well-formed.
        manifest_path = self.target / "scaffold.json"
        self.assertTrue(manifest_path.is_file(),
                        "scaffold.json must exist after the recovery re-run")
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("jig_version", manifest)
        self.assertIn("installed_tiers", manifest)

    def test_unmanaged_hooks_error_leaves_rerunnable_state(self):
        """AC #5 — a refused scaffold (`UnmanagedHooksError`) leaves no
        `scaffold.json` on disk, so the next run treats it as un-scaffolded
        and re-attempts.

        With `scaffold.json` written last, a refused scaffold leaves the
        machinery copy but no `scaffold.json` — the next run treats it as
        un-scaffolded and re-attempts, which is the correct recovery
        behavior. Spec 016-03 deviation log §7 noted this rough edge;
        slice 032-02 closes it by making scaffold.json the completion
        marker."""
        # Seed an unmanaged settings.json to trigger UnmanagedHooksError.
        settings = self.target / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit",
                     "hooks": [{"type": "command",
                                "command": "bash ./user-edit.sh",
                                "timeout": 5}]}
                ]
            }
        }, indent=2) + "\n")

        # First run: scaffold refuses due to unmanaged hooks. We expect
        # non-zero exit (rc=3 per the CLI's UnmanagedHooksError branch).
        r1 = run_scaffold_with_args(self.target)
        self.assertNotEqual(
            r1.returncode, 0,
            "scaffold must refuse when settings.json has unmanaged hooks; "
            f"stdout={r1.stdout!r} stderr={r1.stderr!r}",
        )

        # On-disk invariant: scaffold.json absent — the completion marker
        # never landed because the refusal happened before the final
        # `atomic_write_text` for scaffold.json.
        self.assertFalse(
            (self.target / "scaffold.json").exists(),
            "scaffold.json must be absent after a refused scaffold; "
            "the partial state must be re-runnable without --force",
        )

        # Remove the user's unmanaged settings.json so the second run
        # doesn't refuse for the same reason. (The point of this test is
        # the scaffold.json-absence invariant, not whether the user fixed
        # their settings.json — we just need a clean re-run to confirm
        # recovery is possible.)
        settings.unlink()

        # Re-run without --force. Must succeed: scaffold.json was never
        # written, so the "already scaffolded" check lets the re-run
        # proceed.
        r2 = run_scaffold_with_args(self.target)
        self.assertEqual(
            r2.returncode, 0,
            f"re-run without --force must succeed after refusal: stderr={r2.stderr}",
        )
        self.assertTrue(
            (self.target / "scaffold.json").is_file(),
            "scaffold.json must exist after the recovery re-run",
        )


# --------------------------------------------------------------------------
# Slice 035-01 — exclude-fixtures-from-installs. `_copy_skill_dir` must
# treat any directory named `fixtures` (at any depth, matching the
# `__pycache__` semantics) as test-only and skip it. Test data lives at
# `skills/migrate/fixtures/` today; the rule generalizes for any future
# skill that grows a fixtures tree.
# --------------------------------------------------------------------------


class CopySkillDirExcludesFixturesTests(unittest.TestCase):
    """Slice 035-01 AC #1 + AC #3 — `_copy_skill_dir` skips `fixtures/`
    directories at any depth under a skill subtree, no `fixtures` path
    component reaches the destination."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-035-01-scaffold-")
        self.src = Path(self.tmpdir) / "src-skill"
        self.dst = Path(self.tmpdir) / "dst-skill"
        self.src.mkdir()

        # Minimal skill shape — SKILL.md at root + a runtime helper file
        # so the copy actually does work and we can prove fixtures got
        # filtered (vs. nothing being copied at all).
        (self.src / "SKILL.md").write_text(
            "---\nname: dummy\n---\n# dummy skill body\n"
        )
        (self.src / "runtime_helper.py").write_text("# kept\n")

        # AC #1 — root-level fixtures dir under the skill.
        root_fixtures = self.src / "fixtures"
        root_fixtures.mkdir()
        (root_fixtures / "case-a.txt").write_text("test data — must not ship\n")
        (root_fixtures / "case-b.txt").write_text("more test data\n")

        # AC #3 — nested fixtures dir, deeper than the skill root.
        nested_fixtures = self.src / "sub" / "deeper" / "fixtures"
        nested_fixtures.mkdir(parents=True)
        (nested_fixtures / "nested-case.txt").write_text(
            "nested test data — must not ship\n"
        )
        # A non-fixtures sibling under the nested tree, to prove we only
        # skip the named dir, not the entire subtree.
        (self.src / "sub" / "deeper" / "sibling.txt").write_text("kept\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_fixtures_path_component_at_any_depth(self):
        """AC #1 + AC #3 — after `_copy_skill_dir` runs, no path under the
        destination contains a `fixtures` component."""
        scaffold_mod._copy_skill_dir(self.src, self.dst)

        offenders = [
            p for p in self.dst.rglob("*")
            if "fixtures" in p.relative_to(self.dst).parts
        ]
        self.assertEqual(
            offenders, [],
            "scaffold copy must skip every `fixtures/` dir at any depth; "
            f"found {[str(p.relative_to(self.dst)) for p in offenders]!r}",
        )

    def test_non_fixtures_siblings_still_copied(self):
        """Sanity check — the filter targets `fixtures/` specifically and
        does not accidentally drop the rest of the skill tree."""
        scaffold_mod._copy_skill_dir(self.src, self.dst)

        self.assertTrue((self.dst / "SKILL.md").is_file())
        self.assertTrue((self.dst / "runtime_helper.py").is_file())
        self.assertTrue((self.dst / "sub" / "deeper" / "sibling.txt").is_file())


class TierGatedCopyTests(unittest.TestCase):
    """Slice 038-02 — `_copy_skills_and_agents` gates by `installed_tiers`
    so the on-disk skill set matches the `scaffold.json` manifest
    (ADR-0012; ADR-0007's derivation invariant now holds on BOTH sides).

    Floor install (no test signal) = Tier-0 only; `--has-tests` adds
    Tier-1. Infrastructure (`_<name>` private modules, `agents/`) is never
    gated. Both callers (`scaffold()` and the `copy_machinery()` façade)
    thread tiers through; the param's `None` default copies all tiers —
    the interim default for `migrate.py copy-machinery` until slice 038-04
    sources tiers from the target manifest.
    """

    TIER0 = set(scaffold_mod._TIER_SKILLS["tier-0"])
    TIER1 = set(scaffold_mod._TIER_SKILLS["tier-1"])

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-038-02-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ---- helpers ----------------------------------------------------------
    def _scaffold(self, *args):
        target = Path(self.tmpdir) / f"proj-{len(args)}-{'-'.join(a.strip('-') for a in args)}"
        target.mkdir()
        r = run_scaffold_with_args(target, "--with-machinery", *args)
        self.assertEqual(r.returncode, 0, f"scaffold failed: stderr={r.stderr}")
        return target

    def _on_disk_skills(self, target):
        """Set of skill names (jig- prefix stripped) actually copied, i.e.
        directories carrying a SKILL.md — mirrors the copy's own unit."""
        skills_dir = target / ".claude" / "skills"
        return {
            d.name[len("jig-"):]
            for d in skills_dir.iterdir()
            if d.is_dir() and d.name.startswith("jig-") and (d / "SKILL.md").is_file()
        }

    def _manifest_skills(self, target):
        manifest = json.loads((target / "scaffold.json").read_text())
        # installed_skills entries are "<tier>/<skill>" per ADR-0007.
        return {s.split("/", 1)[1] for s in manifest["installed_skills"]}

    # ---- AC #1: floor install is gated ------------------------------------
    def test_floor_install_copies_only_tier0(self):
        target = self._scaffold("--no-tests")
        on_disk = self._on_disk_skills(target)
        self.assertEqual(
            on_disk, self.TIER0,
            f"floor install should copy exactly the Tier-0 skills; got {on_disk}",
        )
        self.assertEqual(
            on_disk & self.TIER1, set(),
            "no Tier-1 skill should be copied under a no-tests floor install",
        )

    # ---- AC #2: tier-1 lands when its tier is installed -------------------
    def test_has_tests_copies_all_tiers(self):
        target = self._scaffold("--has-tests")
        self.assertEqual(self._on_disk_skills(target), self.TIER0 | self.TIER1)

    # ---- AC #3: manifest <-> on-disk consistency (regression) -------------
    def test_manifest_matches_on_disk_floor(self):
        target = self._scaffold("--no-tests")
        self.assertEqual(
            self._on_disk_skills(target), self._manifest_skills(target),
            "scaffold.json installed_skills must equal the on-disk skill set "
            "(the gap slice 038-02 closes)",
        )

    def test_manifest_matches_on_disk_full(self):
        target = self._scaffold("--has-tests")
        self.assertEqual(self._on_disk_skills(target), self._manifest_skills(target))

    # ---- AC #4: infrastructure is never gated -----------------------------
    def test_infra_ungated_in_floor(self):
        target = self._scaffold("--no-tests")
        skills_dir = target / ".claude" / "skills"
        self.assertTrue(
            (skills_dir / "_common").is_dir(),
            "private `_common/` module must be copied regardless of tier",
        )
        agents = list((target / ".claude" / "agents").glob("jig-*.md"))
        self.assertTrue(agents, "agents must be copied regardless of tier")

    # ---- AC #5: param threading + both callers ----------------------------
    def test_copy_helper_none_copies_all_tiers(self):
        """Interim default: `installed_tiers=None` copies every tier —
        preserves behavior for callers that haven't resolved tiers yet
        (migrate's copy-machinery until slice 038-04)."""
        target = Path(self.tmpdir) / "u-none"
        scaffold_mod._copy_skills_and_agents(scaffold_mod.plugin_root(), target, None)
        self.assertEqual(self._on_disk_skills(target), self.TIER0 | self.TIER1)

    def test_copy_helper_gates_to_given_tiers(self):
        target = Path(self.tmpdir) / "u-t0"
        scaffold_mod._copy_skills_and_agents(
            scaffold_mod.plugin_root(), target, ["tier-0"],
        )
        self.assertEqual(self._on_disk_skills(target), self.TIER0)

    def test_copy_machinery_threads_tiers(self):
        """The `copy_machinery()` façade (used by `migrate.py
        copy-machinery`) accepts and applies `installed_tiers`."""
        target = Path(self.tmpdir) / "u-cm"
        target.mkdir()
        scaffold_mod.copy_machinery(
            scaffold_mod.plugin_root(), target, installed_tiers=["tier-0"],
        )
        self.assertEqual(self._on_disk_skills(target), self.TIER0)

    # ---- edge case: unmapped skill is skipped when gating -----------------
    def test_unmapped_skill_skipped_when_gated(self):
        """A skill dir with no entry in `_TIER_SKILLS` has no tier to gate
        on; under gating it is skipped (not silently shipped, which would
        reopen the manifest<->disk gap). Under the copy-all default it is
        still copied."""
        plugin = Path(self.tmpdir) / "fakeplugin"
        mapped = plugin / "skills" / "spec-workflow"   # real Tier-0 name
        unmapped = plugin / "skills" / "totally-unmapped"
        for d in (mapped, unmapped):
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("---\nname: x\n---\n# body\n")

        gated = Path(self.tmpdir) / "u-gated"
        scaffold_mod._copy_skills_and_agents(plugin, gated, ["tier-0"])
        on_disk_gated = self._on_disk_skills(gated)
        self.assertIn("spec-workflow", on_disk_gated)
        self.assertNotIn(
            "totally-unmapped", on_disk_gated,
            "unmapped skill must be skipped under tier gating",
        )

        copy_all = Path(self.tmpdir) / "u-all"
        scaffold_mod._copy_skills_and_agents(plugin, copy_all, None)
        self.assertIn("totally-unmapped", self._on_disk_skills(copy_all))


# --------------------------------------------------------------------------
# Slice 046-01 — scaffold-doc-command-rendering. Generated docs must
# contain commands, links, and skill names that work *inside* the
# scaffolded target, not the source plugin checkout. Four ACs:
#   AC1 — the documented stocktake command runs from the scaffold target.
#   AC2 — generated relative links in core docs resolve in the target tree.
#   AC3 — generated skill names are current (/jig:vision-elicitation, no
#         stale alias, no future-tense for already-landed work).
#   AC4 — ${CLAUDE_PLUGIN_ROOT} appears as a command path only in
#         plugin-mode artifacts, not in a default (in-repo) scaffold.
# --------------------------------------------------------------------------


# Core generated docs an AC2/AC4 walker inspects. Relative to the target
# root. These are the install-shape-facing docs a fresh adopter reads
# first; the seed spec tree links only intra-seed and is covered by its
# own greenfield emission.
_CORE_DOCS = (
    "CLAUDE.md",
    "docs/workflow.md",
    "docs/architecture.md",
    "docs/conventions.md",
    "docs/product-vision.md",
)

# A code-fence-embedded `python3 .../stocktake.py .` invocation. Captures
# the helper path so AC1 can substitute ${CLAUDE_PROJECT_DIR} and run it.
_STOCKTAKE_CMD_RE = re.compile(
    r"^(python3\s+\S*stocktake\.py\s+\.)\s*$", re.MULTILINE
)

# Markdown inline link target: the `(...)` of `[text](target)`. We then
# filter out external / anchor-only targets in the walker itself.
_MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")

# Precise stale-alias probe. `/jig:vision-elicitation` CONTAINS the
# substring `/jig:vision-elicit`, so a naive `in` check false-positives on
# the correct name. The negative-lookahead asserts "the alias NOT followed
# by `ation`" — i.e. the genuinely-stale short form only.
_STALE_VISION_ALIAS_RE = re.compile(r"/jig:vision-elicit(?!ation)")


def _scaffolded_links(doc_path: Path, target: Path):
    """Yield (raw_target, resolved_path) for every *local* Markdown link in
    `doc_path`. Skips http(s)://, mailto:, and pure `#anchor` links, and
    strips any `#fragment` suffix before resolving. Links resolve against
    the containing doc's directory (standard Markdown semantics)."""
    text = doc_path.read_text()
    for raw in _MD_LINK_RE.findall(text):
        raw = raw.strip()
        if (
            raw.startswith("http://")
            or raw.startswith("https://")
            or raw.startswith("mailto:")
            or raw.startswith("#")
        ):
            continue
        # Drop a trailing #fragment (anchor into a file).
        path_part = raw.split("#", 1)[0]
        if not path_part:
            continue
        resolved = (doc_path.parent / path_part).resolve()
        yield raw, resolved


class ScaffoldDocStocktakeCommandTests(unittest.TestCase):
    """AC1 — the stocktake command documented in the generated workflow doc
    points at the copied helper and exits 0 from the scaffold target."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-046-01-stocktake-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        # Default (in-repo) scaffold — machinery copied to .claude/skills.
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_documented_stocktake_command_runs_from_target(self):
        """AC1 — parse the stocktake command out of docs/workflow.md, resolve
        ${CLAUDE_PROJECT_DIR} to the target, run it, and assert exit 0."""
        workflow = (self.target / "docs" / "workflow.md").read_text()
        m = _STOCKTAKE_CMD_RE.search(workflow)
        self.assertIsNotNone(
            m,
            "generated docs/workflow.md has no `python3 .../stocktake.py .` "
            f"command line:\n{workflow}",
        )
        command = m.group(1)
        # The documented command must NOT depend on ${CLAUDE_PLUGIN_ROOT},
        # which is unset in a scaffolded project.
        self.assertNotIn(
            "${CLAUDE_PLUGIN_ROOT}", command,
            "stocktake command still references ${CLAUDE_PLUGIN_ROOT}, which "
            "is unset in a scaffolded project",
        )
        # Resolve the project-dir placeholder the way Claude Code would.
        runnable = command.replace("${CLAUDE_PROJECT_DIR}", str(self.target))
        parts = runnable.split()
        # Swap the leading `python3` for the test interpreter for portability.
        parts[0] = sys.executable
        r = subprocess.run(parts, capture_output=True, text=True,
                            cwd=str(self.target))
        self.assertEqual(
            r.returncode, 0,
            f"documented stocktake command failed: {runnable!r}\n"
            f"stdout={r.stdout}\nstderr={r.stderr}",
        )

    def test_workflow_doc_points_at_local_helper_path(self):
        """AC1 — the generated doc documents the copied
        .claude/skills/jig-scaffold-init/stocktake.py path, not the
        plugin-root path."""
        workflow = (self.target / "docs" / "workflow.md").read_text()
        self.assertIn(
            ".claude/skills/jig-scaffold-init/stocktake.py", workflow,
            "workflow.md should document the copied local helper path",
        )
        self.assertNotIn(
            "${CLAUDE_PLUGIN_ROOT}/skills/scaffold-init/stocktake.py",
            workflow,
            "workflow.md must not document the plugin-root stocktake path "
            "in a scaffolded (in-repo) project",
        )


class ScaffoldDocLinksResolveTests(unittest.TestCase):
    """AC2 — every relative Markdown link in the generated core docs
    resolves to a real path in the scaffolded tree. Catches the old
    `../../skills/contracts/SKILL.md` source-tree-only regression."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-046-01-links-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_relative_links_in_core_docs_resolve(self):
        """AC2 — walk Markdown links across the core docs and report every
        local target that does not exist in the scaffolded tree."""
        missing = []
        for rel in _CORE_DOCS:
            doc = self.target / rel
            self.assertTrue(doc.is_file(), f"core doc not generated: {doc}")
            for raw, resolved in _scaffolded_links(doc, self.target):
                if not resolved.exists():
                    missing.append(f"{rel} -> {raw} (resolved: {resolved})")
        self.assertEqual(
            missing, [],
            "generated core docs contain relative links that do not resolve "
            "in the scaffolded tree:\n  " + "\n  ".join(missing),
        )


class ScaffoldDocSkillNamesCurrentTests(unittest.TestCase):
    """AC3 — generated CLAUDE.md uses the current /jig:vision-elicitation
    name, never the stale /jig:vision-elicit alias, and does not describe
    already-landed work as future."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-046-01-names-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_claude_md_uses_current_vision_skill_name(self):
        """AC3 — CLAUDE.md mentions /jig:vision-elicitation and not the
        stale alias (precise negative-lookahead check — the correct name
        contains the alias as a substring)."""
        claude_md = (self.target / "CLAUDE.md").read_text()
        self.assertIn(
            "/jig:vision-elicitation", claude_md,
            "CLAUDE.md should reference the current /jig:vision-elicitation "
            "skill name",
        )
        stale = _STALE_VISION_ALIAS_RE.findall(claude_md)
        self.assertEqual(
            stale, [],
            "CLAUDE.md still contains the stale /jig:vision-elicit alias "
            f"(matches: {stale})",
        )

    def test_claude_md_has_no_future_tense_for_landed_work(self):
        """AC3 — CLAUDE.md must not describe the (already-shipped)
        vision-elicitation skill with a "once spec 017-02 ships"-style
        future reference."""
        claude_md = (self.target / "CLAUDE.md").read_text()
        self.assertNotIn(
            "once spec 017-02 ships", claude_md,
            "CLAUDE.md describes already-landed work as future "
            "('once spec 017-02 ships')",
        )


class ScaffoldDocPluginRootShapeTests(unittest.TestCase):
    """AC4 — ${CLAUDE_PLUGIN_ROOT} is install-shape-aware: absent as a
    command path in a default (in-repo) scaffold, preserved under
    --plugin-only (where the plugin root IS the correct location)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-046-01-shape-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _scaffold(self, *args):
        target = Path(self.tmpdir) / ("p-" + ("-".join(a.strip("-") for a in args) or "default"))
        target.mkdir()
        r = run_scaffold_with_args(target, *args)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        return target

    def test_in_repo_scaffold_has_no_plugin_root_command_path(self):
        """AC4 — no generated core doc uses ${CLAUDE_PLUGIN_ROOT}/skills/
        as a command path in a default (in-repo) scaffold."""
        target = self._scaffold()
        offenders = []
        for rel in _CORE_DOCS:
            doc = target / rel
            if not doc.is_file():
                continue
            if "${CLAUDE_PLUGIN_ROOT}/skills/" in doc.read_text():
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            "default (in-repo) scaffold leaks ${CLAUDE_PLUGIN_ROOT}/skills/ "
            f"command paths in: {offenders}",
        )

    def test_plugin_only_scaffold_preserves_plugin_root_path(self):
        """AC4 companion — under --plugin-only the rewrite is correctly
        NOT applied: the workflow doc keeps the ${CLAUDE_PLUGIN_ROOT}
        stocktake path, since the helper genuinely lives under the plugin
        root in that install shape. Proves the rewrite is mode-gated, not
        unconditional."""
        target = self._scaffold("--plugin-only")
        workflow = (target / "docs" / "workflow.md").read_text()
        self.assertIn(
            "${CLAUDE_PLUGIN_ROOT}/skills/scaffold-init/stocktake.py",
            workflow,
            "--plugin-only scaffold should preserve the plugin-root "
            "stocktake path (the rewrite must be mode-gated)",
        )


if __name__ == "__main__":
    unittest.main()
