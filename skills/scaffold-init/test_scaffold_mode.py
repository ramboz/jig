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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 (e.g. default macOS 3.9)
    tomllib = None  # no tomli fallback (jig is zero-dependency); see _load_agent_toml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def _load_agent_toml(text: str) -> dict:
    """Parse a jig-rendered Codex agent TOML into a dict.

    Uses `tomllib` when available (Python 3.11+). Below that — jig's documented
    floor is 3.9, the default macOS `python3` — there is no `tomli` fallback
    because jig ships zero dependencies, so this parses the exact shape
    `CodexScaffoldRenderer.render_codex_agent_toml` emits: a `#`-comment managed
    marker, scalar keys rendered as JSON strings (`json.dumps`), and a trailing
    `developer_instructions` as a `'''…'''` multiline literal (or a JSON string
    when the body itself contains `'''`). Writer and reader are both jig's and
    kept in step — this is not a general TOML parser. It exists so these tests
    RUN and PASS on 3.9 rather than being skipped there (the whole file used to
    skip below 3.11 for these two assertions, silently dropping ~90 tests that
    have nothing to do with TOML)."""
    if tomllib is not None:
        return tomllib.loads(text)
    data: dict = {}
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        key, sep, rest = lines[i].partition(" = ")
        if not sep:
            i += 1
            continue
        key = key.strip()
        value = rest.lstrip()
        if value.startswith("'''"):
            # Multiline literal: everything from the opening `'''` to the next
            # `'''` is opaque (may contain `=`, `#`, blank lines).
            after = value[3:]
            if "'''" in after:
                data[key] = after[: after.index("'''")]
            else:
                buf = after
                i += 1
                while i < len(lines) and "'''" not in lines[i]:
                    buf += lines[i]
                    i += 1
                if i < len(lines):
                    buf += lines[i][: lines[i].index("'''")]
                data[key] = buf
        else:
            data[key] = json.loads(rest.strip())
        i += 1
    return data


def run_scaffold_with_args(target: Path, *args: str,
                           env: "dict | None" = None) -> subprocess.CompletedProcess:
    """Invoke scaffold.py with extra CLI flags before the target path.

    Defaults to a plugin-driven environment (`CLAUDE_PLUGIN_ROOT` set), which
    is what most tests want and keeps slice 099-01's unconfirmed-plugin note
    out of their stdout. Pass `env=` explicitly to drive the other side of
    that branch."""
    if env is None:
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), *args, str(target)],
        capture_output=True, text=True, env=env,
    )


# --------------------------------------------------------------------------
# Plugin-only behavior. History: slice 016-01 AC #8 (g) had plugin mode as the
# default; 016-03 flipped it to in-repo, so these tests drove it via an explicit
# `--plugin-only`; slice 099-01 flipped it back, so `--plugin-only` is now
# redundant with the default and kept for back-compat. The tests still pass it
# explicitly — that is deliberate, it pins the FLAG's behavior rather than the
# default's, which `DefaultPluginModeTests` covers separately.
# --------------------------------------------------------------------------


class DefaultOffMachineryTests(unittest.TestCase):
    """Slice 016-01 AC #8 (g) — plugin mode copies no machinery.

    Framing corrected by slice 099-01. This path was 016-01's default, became
    the "dormant" one under 016-03's in-repo default, and is the default again
    now — so it is not dormant and `--plugin-only` reaches nothing special.
    The tests pass the flag explicitly on purpose: that pins the FLAG, while
    `DefaultPluginModeTests` pins the no-flag default. Same assertions
    throughout — what plugin mode produces never moved, only what it was
    relative to."""

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
# Spec 095-01 — Claude scaffold mode copies `templates/` into `.claude/`,
# mirroring the Codex side's `_copy_codex_templates`, so the copied helpers'
# existing `parents[2]/templates/` fallback resolves with no change to any
# helper's template resolution. Before this slice, `copy_machinery` copied
# `skills/` and `hooks/` only, so no helper could reach a template in the one
# install mode that has no plugin root to fall back on.
# --------------------------------------------------------------------------


class ClaudeScaffoldTemplatesTests(unittest.TestCase):
    """Spec 095-01 — the record-helper family can seed records in Claude
    scaffold mode.

    `--has-tests` forces tier-1 into `installed_tiers` so `adr-workflow` is
    copied too (AC2). Both helpers run as subprocesses out of the project's
    OWN copied machinery with `CLAUDE_PLUGIN_ROOT` unset — the exact runtime
    a scaffolded project has, and the one where `parents[2]` lands on
    `<project>/.claude`.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-095-templates-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        r = run_scaffold_with_args(self.target, "--with-machinery", "--has-tests")
        self.assertEqual(
            r.returncode, 0,
            f"scaffold --with-machinery failed: stderr={r.stderr}\n"
            f"stdout={r.stdout}",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ----- fixtures ---------------------------------------------------------
    def _scaffold_mode_env(self) -> dict:
        """The env a scaffolded project's helper actually runs in: no
        CLAUDE_PLUGIN_ROOT. Git identity is supplied because `adr.py new`
        commits its reservation stub (AC2); it is inert for AC1."""
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
        env.update({
            "GIT_AUTHOR_NAME": "jig test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "jig test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        })
        return env

    def _copied_helper(self, skill: str, helper: str) -> Path:
        path = self.target / ".claude" / "skills" / skill / helper
        self.assertTrue(path.is_file(), f"copied helper missing: {path}")
        return path

    def _templates_snapshot(self) -> dict:
        root = self.target / ".claude" / "templates"
        return {
            str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()
        }

    # ----- AC1: decisions.py seeds its record home --------------------------
    def test_ac1_scaffold_mode_seeds_lightweight_decisions_without_plugin_root(self):
        """AC1 — with the record home absent (bug 012 mode 1: the shape of a
        project scaffolded before the lightweight-decisions template shipped),
        the copied helper seeds it from the copied template and appends."""
        record = self.target / "docs" / "decisions" / "lightweight-decisions.md"
        record.unlink()  # scaffold-init seeds it; the pre-feature shape has none

        helper = self._copied_helper("jig-memory-sync", "decisions.py")
        r = subprocess.run(
            [sys.executable, str(helper), "add-lightweight",
             "--title", "Probe entry",
             "--decision", "recorded from copied machinery",
             "--context", "scaffold mode has no CLAUDE_PLUGIN_ROOT",
             "--scope", "test fixture",
             "--project-dir", str(self.target)],
            capture_output=True, text=True, env=self._scaffold_mode_env(),
        )
        self.assertEqual(
            r.returncode, 0,
            f"copied decisions.py could not seed its record home:\n"
            f"stderr={r.stderr}\nstdout={r.stdout}",
        )
        self.assertTrue(record.is_file(), f"record home not seeded: {record}")
        self.assertIn("Probe entry", record.read_text(),
                      "seeded file must carry the appended entry")

    # ----- AC2: adr.py seeds a new ADR --------------------------------------
    def test_ac2_scaffold_mode_opens_an_adr_without_plugin_root(self):
        """AC2 — the family's second member. `adr.py` had the identical gap
        and no mitigation; unlike the record home, its template is never
        rendered into the project at install time, so this fails on a
        *fresh* scaffold today."""
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        env = self._scaffold_mode_env()
        # `checkout -b` is load-bearing, not cosmetic: off `main`, `adr.py new
        # --no-push` routes to `_reserve_local_on_current_branch`, which skips
        # the clean-tree gate. On `main` that gate refuses outright — a freshly
        # scaffolded tree is entirely untracked. `commit.gpgsign=false` isolates
        # the fixture from a maintainer's global signing config, which would
        # otherwise fail this test with "copied adr.py could not scaffold an
        # ADR" and blame the feature for the environment.
        for args in (["init", "-q"],
                     ["config", "commit.gpgsign", "false"],
                     ["checkout", "-q", "-b", "probe-branch"]):
            g = subprocess.run(["git", *args], cwd=str(self.target),
                               capture_output=True, text=True, env=env)
            self.assertEqual(g.returncode, 0, f"git {args}: {g.stderr}")

        helper = self._copied_helper("jig-adr-workflow", "adr.py")
        r = subprocess.run(
            [sys.executable, str(helper), "new", "probe-decision",
             "--no-push", "--project-dir", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(
            r.returncode, 0,
            f"copied adr.py could not scaffold an ADR:\n"
            f"stderr={r.stderr}\nstdout={r.stdout}",
        )
        written = sorted(
            (self.target / "docs" / "decisions").glob("adr-*-probe-decision.md")
        )
        self.assertEqual(len(written), 1,
                         f"expected one new ADR, found {written}")
        self.assertIn("Proposed", written[0].read_text(),
                      "ADR must be rendered from the copied template")

    # ----- AC3: the copy mirrors Codex --------------------------------------
    def test_ac3_every_plugin_template_is_copied(self):
        """AC3 — every file under the plugin's `templates/` lands under
        `.claude/templates/` at the same relative path."""
        src_root = REPO_ROOT / "templates"
        expected = {
            str(p.relative_to(src_root))
            for p in src_root.rglob("*") if p.is_file()
        }
        self.assertTrue(expected, "fixture check: plugin has no templates/")
        self.assertEqual(
            set(self._templates_snapshot()), expected,
            "copied .claude/templates/ must mirror the plugin's templates/ "
            "tree file-for-file (parity with _copy_codex_templates)",
        )

    # ----- AC4: copied templates name the copied machinery ------------------
    def test_ac4_copied_md_templates_name_the_copied_helpers(self):
        """AC4 — a record seeded from a copied template must not name
        `${CLAUDE_PLUGIN_ROOT}`, which is unset in the project that seeded
        it. Same transform SKILL.md bodies and rendered docs already get."""
        template = (self.target / ".claude" / "templates" / "docs"
                    / "decisions" / "lightweight-decisions.md.template")
        body = template.read_text()
        self.assertNotIn(
            "${CLAUDE_PLUGIN_ROOT}/skills/", body,
            "copied template still names the plugin root — the command it "
            "teaches would not run in the project that carries it",
        )
        self.assertIn(
            "${CLAUDE_PROJECT_DIR}/.claude/skills/jig-memory-sync/", body,
            "copied template must name the copied helper",
        )

    def test_ac4_rewritten_templates_without_a_literal_are_byte_identical(self):
        """AC4 edge case — the rewrite is a substitution, not a re-render.
        These go through `_rewrite_skill_md_paths` (they end `.md.template`)
        but carry no plugin-root literal, so the round trip
        read_text→sub→atomic_write_text must return the source bytes.

        An earlier version of this test asserted the edge case against
        `adr-0000-template.md` / `scaffold.json.template` — neither of which
        ends in `.md.template`, so both took the byte-copy branch and the
        rewrite path was never exercised at all. Caught in review.
        """
        for rel in ("docs/conventions.md.template",
                    "docs/memory/glossary.md.template"):
            src = (REPO_ROOT / "templates" / rel).read_bytes()
            self.assertTrue(rel.endswith(".md.template"),
                            f"fixture check: {rel} must take the rewrite branch")
            self.assertNotIn(b"${CLAUDE_PLUGIN_ROOT}/skills/", src,
                             f"fixture check: {rel} has a plugin-root literal")
            copied = (self.target / ".claude" / "templates" / rel).read_bytes()
            self.assertEqual(
                copied, src,
                f"{rel} has nothing to rewrite — it must survive byte-for-byte")

    def test_ac4_non_md_templates_are_byte_copied(self):
        """AC4 edge case — files that are not `.md.template` skip the rewrite
        entirely and are byte-copied. Iterated rather than hand-listed: a
        hardcoded pair silently stops covering whatever gets added to
        `templates/` next (it had already missed `docs/specs/slice-template.md`,
        which `workflow.py` reads at runtime)."""
        src_root = REPO_ROOT / "templates"
        checked = 0
        for src in sorted(src_root.rglob("*")):
            if not src.is_file() or src.name.endswith(".md.template"):
                continue
            rel = src.relative_to(src_root)
            copied = (self.target / ".claude" / "templates" / rel)
            self.assertEqual(copied.read_bytes(), src.read_bytes(),
                             f"{rel} must be copied verbatim")
            checked += 1
        self.assertTrue(checked, "fixture check: no byte-copied templates found")

    # ----- The other two consumers (deviation log §2) ------------------------
    # The spec framed this as a two-helper family; it is five, and two of the
    # others silently change behaviour here. AC3 pins that their template files
    # are copied; these pin that the helpers actually USE them — which is the
    # claim, and the evidence that copying the whole tree beat an allowlist of
    # the two templates the ACs happened to name.

    def test_workflow_renders_the_real_slice_template_not_the_fallback(self):
        """`workflow.py` `_render_stub_slice` reads
        `parents[2]/templates/docs/specs/slice-template.md`, falling back to a
        degraded inline template when unreachable. In scaffold mode it now
        finds the real one. Distinguished by a marker only the on-disk
        template carries — asserting `is_file()` on the copy would prove
        nothing AC3 doesn't."""
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        env = self._scaffold_mode_env()
        for args in (["init", "-q"],
                     ["config", "commit.gpgsign", "false"],
                     ["checkout", "-q", "-b", "probe-branch"]):
            subprocess.run(["git", *args], cwd=str(self.target),
                           capture_output=True, text=True, env=env, check=True)

        helper = self._copied_helper("jig-spec-workflow", "workflow.py")
        r = subprocess.run(
            [sys.executable, str(helper), "new", "probe-spec", "--no-push",
             "--project-dir", str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0,
                         f"copied workflow.py new failed:\nstderr={r.stderr}")
        slices = sorted(
            (self.target / "docs" / "specs").glob("*-probe-spec/slice-01-*.md")
        )
        self.assertEqual(len(slices), 1, f"expected one slice, got {slices}")
        body = slices[0].read_text()
        marker = "kind: spike"
        self.assertIn(
            marker, body,
            "rendered from the degraded inline fallback, not the copied "
            "template — the fallback carries no spike-slice section",
        )

    def test_memory_bootstraps_people_md_from_the_copied_template(self):
        """`memory.py`'s people.md bootstrap reads
        `plugin_root()/templates/docs/memory/people.md.template`. Before this
        slice its degrade path fired in scaffold mode — its own message said
        the failure was "expected for a scaffold-mode target"."""
        people = self.target / "docs" / "memory" / "people.md"
        if people.exists():
            people.unlink()
        helper = self._copied_helper("jig-memory-sync", "memory.py")
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; from pathlib import Path;"
             f"sys.path.insert(0, {str(helper.parent)!r});"
             f"sys.path.insert(0, {str(helper.parent.parent)!r});"
             "import memory;"
             f"w, m = memory._bootstrap_people_md(Path({str(self.target)!r}));"
             "print(w); print(m)"],
            capture_output=True, text=True, env=self._scaffold_mode_env(),
        )
        self.assertEqual(r.returncode, 0,
                         f"copied memory.py failed:\nstderr={r.stderr}")
        self.assertTrue(r.stdout.startswith("True"),
                        f"bootstrap did not write people.md: {r.stdout}")
        self.assertTrue(people.is_file(), "people.md was not created")
    # ----- AC5: idempotent re-run -------------------------------------------
    def test_ac5_rerun_leaves_templates_byte_identical(self):
        """AC5 — `migrate copy-machinery` re-runs over an existing project to
        refresh machinery; the template copy must be idempotent."""
        before = self._templates_snapshot()
        r = run_scaffold_with_args(
            self.target, "--with-machinery", "--has-tests", "--force")
        self.assertEqual(r.returncode, 0, f"re-run failed: {r.stderr}")
        self.assertEqual(self._templates_snapshot(), before,
                         "re-run must leave .claude/templates/ unchanged")


class PluginOnlyTemplatesTests(unittest.TestCase):
    """Spec 095-01 AC6 — the template copy rides the machinery copy. In
    `--plugin-only` mode the plugin root IS the template home, so a copied
    tree would be dead weight."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-095-plugin-only-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_ac6_plugin_only_writes_no_templates(self):
        r = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (self.target / ".claude" / "templates").exists(),
            "--plugin-only must not create .claude/templates/",
        )


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
    "jig-project-orient.sh",
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
            # plain zip (no 3.10 strict=) — length already asserted equal above
            for src_entry, dst_entry in zip(src_event, dst_event):
                # matcher (when present) carries over
                self.assertEqual(
                    src_entry.get("matcher"), dst_entry.get("matcher"),
                    f"matcher drifted in {event}",
                )
                # Inner hook list shape — assert length, then plain zip (3.9-safe)
                self.assertEqual(
                    len(src_entry["hooks"]), len(dst_entry["hooks"]),
                    f"hook list length drifted in {event}",
                )
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

    def test_sessionstart_registers_project_orientation(self):
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        commands = [
            h.get("command", "")
            for entry in settings["hooks"]["SessionStart"]
            for h in entry.get("hooks", [])
        ]
        orient = [c for c in commands if "jig-project-orient.sh" in c]
        self.assertEqual(len(orient), 1, commands)
        self.assertIn("${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/", orient[0])
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", orient[0])


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
        # Slice 095-01 — same invariant for the template tree. Without this,
        # swapping `_check_hooks_safety` and `_copy_claude_templates` in
        # `copy_machinery` would strand a 25-file `.claude/templates/` tree on
        # a refused run while the suite stayed green.
        self.assertFalse(
            (self.target / ".claude" / "templates").exists(),
            "refused scaffold left a partial .claude/templates/ tree — the "
            "safety check must run BEFORE the template copy.",
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

    def test_default_off_writes_permissions_only_settings_no_hooks(self):
        """AC #1 — with --plugin-only, no hook scripts.

        Slice 099-01 (ADR-0041 OQ1) narrowed this: plugin mode still copies no
        hook *scripts*, but it now DOES write `.claude/settings.json` carrying
        the `permissions.deny` security floor — the one ADR-0013 part that
        cannot be served from the plugin root. The assertion is inverted, not
        deleted: settings.json must exist, and must carry permissions WITHOUT
        a hooks block."""
        r = run_scaffold_with_args(self.target, "--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (self.target / ".claude" / "hooks" / "scripts").exists(),
            ".claude/hooks/scripts must not exist with --plugin-only",
        )
        settings_path = self.target / ".claude" / "settings.json"
        self.assertTrue(
            settings_path.exists(),
            "--plugin-only must write settings.json for the permissions floor",
        )
        settings = json.loads(settings_path.read_text())
        self.assertIn("permissions", settings)
        self.assertIn(
            "Bash(rm -rf*)", settings["permissions"]["deny"],
            "plugin mode must seed the destructive-command deny defaults",
        )
        self.assertNotIn(
            "hooks", settings,
            "plugin mode must not materialize a hooks block — the plugin's "
            "own hooks.json serves those",
        )


# --------------------------------------------------------------------------
# Slice 016-03 (default flip to in-repo) + slice 099-01 (flipped back to
# plugin mode). `--plugin-only` is no longer an opt-out — see PluginOnlyFlagTests.
# --------------------------------------------------------------------------


class DefaultPluginModeTests(unittest.TestCase):
    """Slice 099-01 AC #1 (ADR-0041) — the default is now **plugin mode**,
    reversing slice 016-03's in-repo default. Running scaffold without a
    machinery flag copies NO machinery: no skills/, agents/, or hooks/scripts/
    under `.claude/`, and `scaffold_mode == 'plugin-only'`.

    `.claude/settings.json` IS written, and is not machinery: it carries the
    `permissions.deny` floor and no hooks block (ADR-0041 OQ1)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-099-01-default-plugin-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_is_plugin_mode(self):
        """AC #1 — no flag → plugin mode. No copied machinery; scaffold_mode
        is 'plugin-only'."""
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (self.target / ".claude" / "skills").exists(),
            "default scaffold must NOT copy skills/ (plugin mode)",
        )
        self.assertFalse(
            (self.target / ".claude" / "agents").exists(),
            "default scaffold must NOT copy agents/ (plugin mode)",
        )
        self.assertFalse(
            (self.target / ".claude" / "hooks" / "scripts").exists(),
            "default scaffold must NOT copy hooks/scripts/ (plugin mode)",
        )
        # Slice 099-01 (ADR-0041 OQ1): settings.json IS written in plugin mode
        # — permissions-only, no hooks. See
        # test_default_mode_seeds_permissions_deny_floor below.
        self.assertTrue(
            (self.target / ".claude" / "settings.json").exists(),
            "default scaffold writes a permissions-only settings.json",
        )
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "plugin-only")

    def test_default_mode_seeds_permissions_deny_floor(self):
        """Slice 099-01 / ADR-0041 OQ1 — plugin mode seeds the ADR-0013 part 3
        destructive-command guardrail.

        `permissions.deny` lives in the *project's* settings.json, so unlike
        the hooks and the primer block it cannot be served from the plugin
        root. Making plugin mode the default would otherwise have silently
        dropped the floor's one project-scoped part from every new project."""
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        deny = settings["permissions"]["deny"]
        for rule in ("Bash(git push --force*)", "Bash(git reset --hard*)",
                     "Bash(rm -rf*)"):
            self.assertIn(rule, deny, f"missing deny default: {rule}")
        self.assertNotIn(
            "hooks", settings,
            "plugin mode writes permissions ONLY — hooks come from the "
            "installed plugin, not a per-project copy",
        )

    def test_default_mode_permissions_write_preserves_user_settings(self):
        """The plugin-mode write merges; it does not clobber. A user's own
        settings.json — including hooks jig does not manage — survives, and
        their deny entries keep their order ahead of jig's."""
        settings_path = self.target / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({
            "model": "opus",
            "hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": []}]},
            "permissions": {"allow": ["Bash(ls*)"], "deny": ["Bash(curl*)"]},
        }))
        # Deliberately NO --force. `_write_permissions_deny_floor` never runs
        # the unmanaged-hooks refusal (it does not touch `hooks`), and this is
        # the test that proves it: a pre-existing settings.json carrying a
        # third-party hook must not make plugin mode refuse. Passing --force
        # here would mask exactly that, since --force also overrides the
        # refusal.
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        settings = json.loads(settings_path.read_text())
        self.assertEqual(settings.get("model"), "opus",
                         "unrelated user keys must survive")
        self.assertEqual(
            settings["hooks"]["PreToolUse"][0]["matcher"], "Edit",
            "plugin mode must not touch the user's own hooks",
        )
        self.assertEqual(settings["permissions"]["allow"], ["Bash(ls*)"],
                         "permissions.allow is not jig-managed")
        self.assertEqual(
            settings["permissions"]["deny"][0], "Bash(curl*)",
            "user deny entries stay first, in order",
        )
        self.assertIn("Bash(rm -rf*)", settings["permissions"]["deny"])

    def test_plugin_mode_notes_when_run_from_source_checkout(self):
        """Slice 099-01 (ADR-0041 OQ2) — plugin mode is only lean
        if a plugin is actually installed; otherwise it is empty, and silently
        so.

        `git clone … && python3 …/scaffold.py <project>` is a documented README
        install path with no plugin anywhere. Detected POSITIVELY (the run came
        out of a jig source checkout), not inferred from a missing env var —
        absence is one-sided and would also flag a plugin-installed user who
        simply used a terminal."""
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        r = run_scaffold_with_args(self.target, env=env)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn("source checkout", r.stdout)
        # Deliberately NOT asserting "--in-repo" here: that string comes from
        # the unconditional mode line, so it holds whether or not the note
        # fires, and it implies the note offers that remedy — it does not, it
        # points at the mode line. Pinned where it belongs instead, on the
        # mode-line tests.
        # The note states what was DETECTED (topology + no plugin host), never
        # the condition — a contributor with the plugin installed who ran from
        # a clone is a legitimate false positive and must not be told their
        # project is broken.
        self.assertIn("if you do have the jig plugin installed", r.stdout.lower())

    def test_plugin_mode_stays_quiet_when_plugin_driven(self):
        """The note is advisory and must not cry wolf: a set plugin-root
        variable means a plugin host is driving the run, which is what makes a
        checkout-shaped run legitimate (jig's own suite, contributors running
        from source). Well-grounded on Claude; weaker on Codex, which is why
        the unconditional mode line — not this note — carries the warning."""
        env = dict(os.environ)
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        r = run_scaffold_with_args(self.target, env=env)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertNotIn("source checkout", r.stdout)

    def test_in_repo_mode_never_notes_plugin_presence(self):
        """in-repo is self-contained by construction — a missing plugin is
        irrelevant there, so the note must not fire regardless of the env."""
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        r = run_scaffold_with_args(self.target, "--in-repo", env=env)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertNotIn("source checkout", r.stdout)

    def test_note_detects_installed_plugin_shape_as_quiet(self):
        """The other side of the discriminator, pinned on a REAL directory
        shape rather than a mock: an installed plugin is `hosts/claude`
        repackaged — `skills/` + `templates/`, no `hosts/`, no `scripts/`.
        Running from that shape must stay quiet even with no env var, because
        such a user is not in the failing population."""
        installed = Path(self.tmpdir) / "installed-plugin"
        shutil.copytree(REPO_ROOT / "hosts" / "claude", installed)
        self.assertFalse((installed / "hosts").exists())
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        r = subprocess.run(
            [sys.executable,
             str(installed / "skills" / "scaffold-init" / "scaffold.py"),
             str(self.target)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertNotIn("source checkout", r.stdout)

    def test_note_fires_on_codex_host_too(self):
        """The failing population is host-independent — README documents a
        Codex clone-and-run recipe as well. Pinned because the detection must
        NOT rest on any claim about Codex's environment: `docs/architecture.md`
        documents `PLUGIN_ROOT` for plugin *hooks*, which does not establish it
        in a skill subprocess, and `plugin_root()` does not trust it for Codex.
        The checkout-shape signal needs no such claim."""
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env.pop("PLUGIN_ROOT", None)
        r = run_scaffold_with_args(self.target, "--host", "codex", env=env)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn("source checkout", r.stdout)

    def test_plugin_mode_line_is_true_for_plugin_less_runs(self):
        """The mode line prints unconditionally, so its wording must hold for
        EVERY population — including the plugin-less shapes no detector catches
        (unzipped release package, copied plugin tree, cross-host run).

        It previously asserted "jig runs from the installed plugin" flatly: a
        fact about the user's machine the scaffold cannot know, and for those
        users an affirmative false statement — worse than the silence it
        replaced. Pinned because conditionalizing it is the residual's cheapest
        mitigation and needs no detection at all."""
        env = dict(os.environ)
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)   # note suppressed; line still prints
        r = run_scaffold_with_args(self.target, env=env)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertNotIn("source checkout", r.stdout)
        self.assertIn("if none is installed", r.stdout.lower())
        self.assertIn("--in-repo", r.stdout)

    def test_skill_md_documents_the_machinery_axis(self):
        """Slice 099-01 AC #4 — the skill contract must surface the axis and
        describe what the default actually produces.

        Added after review: AC #4 was the one AC with no fixture, and it was
        also the one that had drifted — the Output section still listed plugin
        mode's artifacts without `.claude/settings.json`, which the ADR-0041
        OQ1 fold-in made the default path write. A skill contract that
        understates a security-relevant artifact is exactly the kind of drift a
        pin catches and a reader does not."""
        skill = (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").read_text()
        # The sixth Q&A question must EXIST, not merely be alluded to. Asserting
        # `--in-repo` alone was vacuous: the invocation example already contains
        # it, so deleting the whole question left the test green.
        self.assertRegex(skill, r"(?m)^6\. \*\*Machinery vs\. plugin\*\*")
        self.assertIn("NOT be installed", skill,
                      "the question must state what it is actually asking")
        self.assertIn("plugin mode is the default", skill,
                      "and which way skipping it resolves")
        # Output must not understate the default path: a permissions floor IS
        # seeded, and the reason it is not "machinery" must be stated.
        self.assertIn("permissions", skill.lower())
        self.assertIn("deny floor", skill)
        # And it must not claim the old default.
        self.assertNotIn("in-repo (the default)", skill)

    def test_skill_md_output_survives_the_codex_translation(self):
        """The Output section is machine-translated per host, so a host named
        inside a conditional **inverts**.

        This shipped once: "Claude host only; Codex has no equivalent
        project-scoped permission surface" rendered as "**Codex** host only;
        Codex has no equivalent…" — self-contradictory, and it promised a Codex
        project the ADR-0013 destructive-command floor that `scaffold()` never
        writes there (`_write_permissions_deny_floor` is gated on
        `host == "claude"`). An understated security artifact was the bug this
        section was fixed for; overstating one on the other host is worse.

        Pinned against the RENDERED text, because the source read fine — that is
        precisely why the source-only assertion above did not catch it."""
        rendered = (REPO_ROOT / "hosts" / "codex" / "plugins" / "jig"
                    / "skills" / "scaffold-init" / "SKILL.md").read_text()
        # The scaffold never writes a Codex settings.json in either mode, so the
        # shipped Codex contract must not name one.
        self.assertNotIn(".codex/settings.json", rendered)
        # And the host-conditional must not have inverted into nonsense.
        self.assertNotIn("Codex host only", rendered)
        # Asserting the SHIPPED package, not a re-render, so this also fails if
        # the host build goes stale.
        self.assertIn("deny floor", rendered)

    def test_default_summary_names_plugin_mode(self):
        """AC #3 — the wizard summary names the chosen (plugin) mode and why."""
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn("mode: plugin", r.stdout)
        self.assertIn("--in-repo", r.stdout)

    def test_in_repo_flag_opts_into_machinery(self):
        """AC #2 — --in-repo copies the machinery and sets scaffold_mode
        'in-repo', and the summary names in-repo mode."""
        r = run_scaffold_with_args(self.target, "--in-repo")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertTrue(
            (self.target / ".claude" / "skills" / "jig-scaffold-init"
             / "SKILL.md").is_file(),
            "--in-repo should copy skills/",
        )
        self.assertTrue(
            (self.target / ".claude" / "settings.json").is_file(),
            "--in-repo should write settings.json",
        )
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "in-repo")
        self.assertIn("mode: in-repo", r.stdout)

    def test_codex_default_is_plugin_mode(self):
        """AC #1 for the OTHER host — the slice DoD names both hosts. The
        `with_machinery` branch is host-independent, but the codex suite
        injects --in-repo for its machinery assertions, so without this the
        codex *default* path would be exercised nowhere."""
        sub = Path(self.tmpdir) / "codex-default"
        sub.mkdir()
        r = run_scaffold_with_args(sub, "--host", "codex")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        for rel in (".codex/skills", ".codex/agents",
                    ".codex/hooks/scripts", ".codex/hooks.json",
                    ".codex/templates"):
            self.assertFalse(
                (sub / rel).exists(),
                f"codex default scaffold must NOT create {rel} (plugin mode)",
            )
        manifest = json.loads((sub / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "plugin-only")
        self.assertEqual(manifest.get("host_renderer"), "codex")

    def test_codex_summary_names_the_mode(self):
        """AC #3 for the OTHER host — the summary must be emitted before
        main()'s codex early-return, in both modes."""
        plugin_dir = Path(self.tmpdir) / "codex-sum-plugin"
        plugin_dir.mkdir()
        r = run_scaffold_with_args(plugin_dir, "--host", "codex")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn("mode: plugin", r.stdout)

        in_repo_dir = Path(self.tmpdir) / "codex-sum-inrepo"
        in_repo_dir.mkdir()
        r2 = run_scaffold_with_args(in_repo_dir, "--host", "codex", "--in-repo")
        self.assertEqual(r2.returncode, 0, f"stderr: {r2.stderr}")
        self.assertIn("mode: in-repo", r2.stdout)

    def test_in_repo_aliases_are_equivalent(self):
        """AC #2 — --with-machinery and --copy-machinery are aliases of
        --in-repo: each produces an in-repo scaffold."""
        for alias in ("--with-machinery", "--copy-machinery"):
            with self.subTest(alias=alias):
                sub = Path(self.tmpdir) / f"alias-{alias.strip('-')}"
                sub.mkdir()
                r = run_scaffold_with_args(sub, alias)
                self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
                manifest = json.loads((sub / "scaffold.json").read_text())
                self.assertEqual(
                    manifest.get("scaffold_mode"), "in-repo",
                    f"{alias} should be an --in-repo alias",
                )
                self.assertTrue(
                    (sub / ".claude" / "skills").is_dir(),
                    f"{alias} should copy machinery",
                )


class PluginOnlyFlagTests(unittest.TestCase):
    """`--plugin-only` selects plugin mode explicitly: `scaffold_mode:
    plugin-only`, no `.claude/skills/`, no `.claude/agents/`.

    Framing updated by slice 099-01. Under 016-03 this flag was an *opt-out*
    from an in-repo default, which is what the class was originally named for;
    since 099-01 flipped the default back, it opts out of nothing and is kept
    for back-compat and for stating the choice out loud. The assertions are
    unchanged — what the flag produces did not move, only what it is relative
    to."""

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
        # Slice 099-01 (ADR-0041 OQ1): settings.json IS written — the
        # permissions floor only, never hooks. What --plugin-only skips is the
        # copied *machinery*, which is what the assertions above pin.
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        self.assertNotIn(
            "hooks", settings,
            "--plugin-only settings.json must carry no hooks block",
        )
        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("scaffold_mode"), "plugin-only")

    def test_plugin_only_and_with_machinery_are_exclusive(self):
        """Passing both --plugin-only and --with-machinery is a usage
        error (argparse mutually-exclusive group, exit 2). Slice 099-01 AC #2
        names exit 2 specifically, so assert the code rather than merely
        non-zero — a bare `!= 0` also passes on an unrelated crash."""
        for in_repo_flag in ("--with-machinery", "--in-repo", "--copy-machinery"):
            with self.subTest(flag=in_repo_flag):
                r = run_scaffold_with_args(
                    self.target, "--plugin-only", in_repo_flag,
                )
                self.assertEqual(
                    r.returncode, 2,
                    f"--plugin-only with {in_repo_flag} must be an argparse "
                    f"usage error (exit 2); got {r.returncode}, "
                    f"stderr={r.stderr!r}",
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
        # The dogfood shape is the in-repo tree; since slice 099-01 (ADR-0041)
        # flipped the default to plugin mode, opt in explicitly with --in-repo.
        r = run_scaffold_with_args(self.target, "--in-repo")
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
        # These tests exercise the copied `.codex/` machinery tree. Since slice
        # 099-01 (ADR-0041) flipped the default to plugin mode, inject --in-repo
        # unless the caller already selected a mode explicitly (e.g. the
        # plugin-only leak test passes --plugin-only).
        mode_flags = {"--in-repo", "--with-machinery",
                      "--copy-machinery", "--plugin-only"}
        if not any(a in mode_flags for a in extra_args):
            extra_args = ("--in-repo", *extra_args)
        return run_scaffold_with_args(self.target, "--host", "codex", *extra_args)

    # ---- Bug 015: brief.md + seed spec must speak the host's vocabulary ----

    def _seed_and_brief_text(self, target: Path) -> str:
        """brief.md plus every seed-spec file, concatenated."""
        parts = [(target / "brief.md").read_text()]
        seed = target / "docs" / "specs" / "001-adopt-jig"
        # Assert the seed exists before globbing it. Without this, a regressed
        # seed emission yields an empty glob, and the `AGENTS.md` assertions
        # below would still pass off brief.md alone — the seed half of this
        # regression test would go vacuous silently.
        self.assertTrue(seed.is_dir(), f"seed spec missing at {seed}")
        seed_files = sorted(seed.glob("*.md"))
        self.assertTrue(seed_files, f"seed spec dir {seed} is empty")
        parts += [p.read_text() for p in seed_files]
        return "\n".join(parts)

    def test_codex_brief_and_seed_name_agents_md_plugin_mode(self):
        """Bug 015 — a Codex project's first-read documents must not tell the
        user to open `CLAUDE.md`, a file only Claude projects have.

        `brief.md` and the seed spec were rendered through paths that never
        received the host transform (`_render_brief` passed no hook;
        `_emit_seed_spec` built a layout-only one), so they kept the canonical
        templates' Claude vocabulary while every other rendered doc was
        translated."""
        r = self._run_codex_scaffold("--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        text = self._seed_and_brief_text(self.target)
        self.assertNotIn("CLAUDE.md", text)
        self.assertIn("AGENTS.md", text)

    def test_codex_brief_and_seed_name_agents_md_in_repo_mode(self):
        """Bug 015 affected BOTH modes — the fault was the render path, not the
        mode, so pin the other side too."""
        r = self._run_codex_scaffold("--with-machinery")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        text = self._seed_and_brief_text(self.target)
        self.assertNotIn("CLAUDE.md", text)
        self.assertIn("AGENTS.md", text)

    def test_codex_host_rewrite_does_not_mangle_project_name(self):
        """Bug 015's fix applies the host transform to the TEMPLATE, before
        substitution — not to the rendered output.

        The Codex transform contains a blanket `Claude` -> `Codex` replacement
        and `PROJECT_NAME` is user-derived, so post-substitution rewriting
        corrupts a project legitimately named after Claude. Pinned because the
        obvious one-line fix (`post_render=doc_rewrite`) passes the two tests
        above while silently renaming the user's project."""
        target = Path(self.tmpdir) / "Claude-Tools"
        target.mkdir()
        r = run_scaffold_with_args(target, "--host", "codex", "--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        text = self._seed_and_brief_text(target)
        self.assertIn("Claude-Tools", text,
                      "the project's own name must survive the host rewrite")
        self.assertNotIn("Codex-Tools", text)

    def test_claude_host_brief_and_seed_are_unchanged(self):
        """The control arm of the same gate (Claude host, despite the class
        name): these documents must still name `CLAUDE.md`. Guards against a
        fix that translates unconditionally.

        Both modes, because they exercise different transforms. `--plugin-only`
        passes `host_rewrite=None`; `--with-machinery` passes
        `_rewrite_skill_md_paths`, which bug 015 made newly reachable on these
        two documents. That path is inert against today's templates (neither
        carries a `${CLAUDE_PLUGIN_ROOT}/skills/` pattern) — pinned so it stays
        that way if the seed grows one, since the seed's whole job is to
        describe jig machinery."""
        for mode_flag in ("--plugin-only", "--with-machinery"):
            with self.subTest(mode=mode_flag):
                target = Path(self.tmpdir) / f"claude-project{mode_flag}"
                target.mkdir()
                r = run_scaffold_with_args(target, mode_flag)
                self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
                text = self._seed_and_brief_text(target)
                self.assertIn("CLAUDE.md", text)
                self.assertNotIn("AGENTS.md", text)

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

    def test_committed_codex_host_package_scaffold_runs(self):
        script = (
            REPO_ROOT / "hosts" / "codex" / "plugins" / "jig" / "skills"
            / "scaffold-init" / "scaffold.py"
        )
        r = subprocess.run(
            ["python3", str(script), "--host", "codex", "--in-repo",
             str(self.target)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout={r.stdout}")

        payload = json.loads((self.target / ".codex" / "hooks.json").read_text())
        self.assertEqual(set(payload), {"hooks"})
        manifest = json.loads((self.target / "scaffold.json").read_text())
        package_manifest = json.loads(
            (
                REPO_ROOT / "hosts" / "codex" / "plugins" / "jig"
                / ".codex-plugin" / "plugin.json"
            ).read_text()
        )
        self.assertEqual(manifest["jig_version"], package_manifest["version"])

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

    def test_codex_primer_guides_public_semantic_index_exploration(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        agents_md = (self.target / "AGENTS.md").read_text()
        self.assertIn("Semantic-index exploration", agents_md)
        self.assertIn("configured public semantic-index provider first", agents_md)
        self.assertIn("fall back to targeted search/read", agents_md)
        self.assertNotIn("Scout", agents_md)

        workflow = (self.target / "docs" / "workflow.md").read_text()
        self.assertIn("## Semantic-Index Exploration", workflow)
        self.assertIn("jig-semantic-index", workflow)
        self.assertIn(".jig/semantic-index.json", workflow)
        self.assertIn("auto_attach: true", workflow)
        self.assertIn("discovers the first installed supported", workflow)
        self.assertNotIn('"provider": "tokensave"', workflow)
        self.assertIn("none is installed", workflow)
        self.assertIn("never installs providers", workflow)
        self.assertNotIn("Scout", workflow)

    def test_codex_phase_mode_guidance_is_host_native(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        agents_md = (self.target / "AGENTS.md").read_text()
        workflow = (self.target / "docs" / "workflow.md").read_text()

        self.assertIn("Codex Plan mode", agents_md)
        self.assertIn("Default mode", agents_md)
        self.assertIn("jig specs, slices, and review artifacts", agents_md)
        self.assertIn("## Phase-Mode Guidance", workflow)
        self.assertIn("Codex Plan mode", workflow)
        self.assertIn("Default mode", workflow)
        self.assertIn("Do not treat Codex mode state as a lifecycle gate", workflow)
        self.assertIn("Host-native modes are advisory", workflow)
        self.assertNotIn("Claude Code plan mode", agents_md)
        self.assertNotIn("normal edit mode", workflow)

    def test_codex_plugin_only_docs_do_not_leak_claude_runtime_vars(self):
        r = self._run_codex_scaffold("--plugin-only")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout={r.stdout}")

        workflow = (self.target / "docs" / "workflow.md").read_text()
        primer = (self.target / "AGENTS.md").read_text()
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", workflow)
        self.assertNotIn("CLAUDE_PROJECT_DIR", workflow)
        self.assertNotIn(".claude/", workflow)
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", primer)

        # Slice 099-01 (ADR-0041 OQ3). This assertion is INVERTED, not deleted.
        # It used to require `${CODEX_PROJECT_DIR:-$PWD}/.codex` here — the
        # project-local runtime root — while the very same test asserted below
        # that `.codex/skills/` does not exist. Plugin mode copies nothing, so
        # those docs cited a tree that was never created. Plugin-mode docs now
        # name the INSTALLED plugin via Codex's own `${PLUGIN_ROOT}`, mirroring
        # what Claude plugin mode does with `${CLAUDE_PLUGIN_ROOT}`.
        self.assertIn("${PLUGIN_ROOT}/skills/", workflow)
        self.assertNotIn(
            "${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/", workflow,
            "plugin mode must not cite the project-local skills tree it "
            "never creates",
        )
        # The primer cites no runtime path at all — slice 099-01 moved its
        # Session Pickup line to the host-native `/jig:orient`, which resolves
        # in either mode and keeps slice 048-03 AC #5 (no plugin-root leakage
        # on the adoption surface) intact.
        self.assertNotIn("${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/", primer)
        self.assertNotIn("${PLUGIN_ROOT}/skills/", primer)

        manifest = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(manifest.get("host_renderer"), "codex")
        self.assertEqual(manifest.get("scaffold_mode"), "plugin-only")
        self.assertFalse((self.target / ".codex" / "skills").exists())

    def test_codex_docs_correct_when_scaffolded_from_the_shipped_package(self):
        """OQ3's mode gate must hold on the path real users take.

        Every other Codex test runs `scaffold.py` from the SOURCE tree, where
        `templates/` is canonical. The shipped Codex package used to
        pre-rewrite its templates to the in-repo shape at build time, which
        `scaffold()` could not undo — its gate keys on
        `${CLAUDE_PLUGIN_ROOT}/skills/`, already gone from a pre-rewritten
        template. So the gate was a no-op exactly where it mattered, and a
        plugin-mode scaffold from a real Codex install emitted docs citing a
        `.codex/skills/` tree it never created.

        Source-tree tests passed throughout. Second instance in this slice of
        "source is transformed before shipping, so a test on the source is not
        a test of the contract" — the first was the SKILL.md body."""
        pkg = REPO_ROOT / "hosts" / "codex" / "plugins" / "jig"
        for mode_flag, expect, forbid in (
            ("--plugin-only", "${PLUGIN_ROOT}/skills/",
             "${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/"),
            ("--in-repo", "${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/",
             "${PLUGIN_ROOT}/skills/"),
        ):
            with self.subTest(mode=mode_flag):
                target = Path(self.tmpdir) / f"pkg{mode_flag}"
                target.mkdir()
                r = subprocess.run(
                    [sys.executable,
                     str(pkg / "skills" / "scaffold-init" / "scaffold.py"),
                     "--host", "codex", "--solo", mode_flag, str(target)],
                    capture_output=True, text=True,
                )
                self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
                workflow = (target / "docs" / "workflow.md").read_text()
                self.assertIn(expect, workflow)
                self.assertNotIn(forbid, workflow)
                # The cited tree must match what was actually created.
                self.assertEqual(
                    (target / ".codex" / "skills").is_dir(),
                    mode_flag == "--in-repo",
                    "docs must cite a tree the scaffold actually creates",
                )

    def test_codex_in_repo_docs_still_use_project_local_paths(self):
        """The in-repo counterpart of the test above — slice 099-01 gated the
        Codex rewrite on mode, so pin the OTHER side of that gate. Here the
        machinery really is copied to `.codex/skills/`, so docs must name it
        and must NOT point at the plugin root."""
        r = self._run_codex_scaffold("--in-repo")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout={r.stdout}")

        workflow = (self.target / "docs" / "workflow.md").read_text()
        self.assertIn("${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/", workflow)
        self.assertNotIn("${PLUGIN_ROOT}/skills/", workflow)
        self.assertTrue(
            (self.target / ".codex" / "skills").exists(),
            "--in-repo must create the tree its docs cite",
        )

    def test_codex_project_local_templates_are_codex_native(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout={r.stdout}")

        workflow_template = (
            self.target / ".codex" / "templates" / "docs"
            / "workflow.md.template"
        ).read_text()
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", workflow_template)
        self.assertNotIn("CLAUDE_PROJECT_DIR", workflow_template)
        self.assertNotIn(".claude/", workflow_template)
        self.assertIn("${CODEX_PROJECT_DIR:-$PWD}/.codex", workflow_template)

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
            data = _load_agent_toml(agent.read_text())
            self.assertEqual(data["name"], f"jig-{role}")
            self.assertEqual(data["sandbox_mode"], sandbox)
            self.assertIn("Codex adapter note", data["developer_instructions"])
            self.assertIn("Semantic-index exploration", data["developer_instructions"])
            self.assertIn(
                "configured public semantic-index provider first",
                data["developer_instructions"],
            )
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
        data = _load_agent_toml((agents_dir / "jig-reviewer.toml").read_text())
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
        self.assertEqual(set(payload), {"hooks"})
        self.assertEqual(sorted(payload["hooks"].keys()), sorted(EXPECTED_HOOK_EVENTS))

        handlers = [
            hook
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
        ]
        self.assertGreater(len(handlers), 0)
        for hook in handlers:
            self.assertNotIn("async", hook)
            self.assertIn("statusMessage", hook)
            self.assertTrue(hook["statusMessage"].startswith("jig: "))
        self.assertIn(
            "jig: record task telemetry",
            {hook["statusMessage"] for hook in handlers},
        )

        text = hooks_path.read_text()
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", text)
        self.assertNotIn("CLAUDE_PROJECT_DIR", text)
        raw_text = (self.target / ".codex" / "hooks" / "hooks.json").read_text()
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", raw_text)
        self.assertNotIn("CLAUDE_PROJECT_DIR", raw_text)
        for script in EXPECTED_HOOK_SCRIPTS:
            self.assertIn(
                f"${{CODEX_PROJECT_DIR:-$PWD}}/.codex/hooks/scripts/{script}",
                text,
            )
            self.assertIn(
                f"${{CODEX_PROJECT_DIR:-$PWD}}/.codex/hooks/scripts/{script}",
                raw_text,
            )
            path = self.target / ".codex" / "hooks" / "scripts" / script
            self.assertTrue(path.is_file(), f"missing hook script: {path}")
            self.assertEqual(path.stat().st_mode & 0o777, 0o755)

        semantic_hook = (
            self.target / ".codex" / "hooks" / "scripts" / "jig-semantic-index.sh"
        ).read_text()
        self.assertNotIn("CLAUDE_PROJECT_DIR", semantic_hook)
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", semantic_hook)
        self.assertIn("CODEX_PROJECT_DIR", semantic_hook)
        self.assertIn("host='codex'", semantic_hook)
        self.assertIn("semantic-index-codex-hook.json", semantic_hook)
        attribution_helper = (
            self.target / ".codex" / "hooks" / "scripts" / "lib"
            / "read_attribution.py"
        ).read_text()
        self.assertNotIn(".claude", attribution_helper)
        self.assertNotIn("CLAUDE_PROJECT_DIR", attribution_helper)
        self.assertIn(".codex", attribution_helper)

    def test_codex_semantic_index_hook_uses_shared_contract(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        common_dir = Path(self.tmpdir) / "fake-common"
        common_dir.mkdir()
        (common_dir / "semantic_index.py").write_text(
            "class Result:\n"
            "    action = 'recommend'\n"
            "    outcome = 'provider_available'\n"
            "    provider = 'tokensave'\n"
            "    provider_profile = 'public'\n"
            "    recommendation = 'Enable semantic index via .jig/semantic-index.json'\n"
            "\n"
            "def activate(project_dir, host='unknown'):\n"
            "    assert host == 'codex'\n"
            "    return Result()\n"
        )

        script = self.target / ".codex" / "hooks" / "scripts" / "jig-semantic-index.sh"
        env = os.environ.copy()
        env["CODEX_PROJECT_DIR"] = str(self.target)
        env["JIG_SEMANTIC_INDEX_COMMON_DIR"] = str(common_dir)
        result = subprocess.run(
            ["bash", str(script)],
            input=json.dumps({"hook_event_name": "SessionStart", "session_id": "s1"}),
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["continue"])
        self.assertEqual(
            payload["additionalContext"],
            "Enable semantic index via .jig/semantic-index.json",
        )
        self.assertTrue(
            (self.target / ".jig" / "semantic-index-codex-hook.json").is_file()
        )

    def test_codex_project_orientation_hook_executes_generated_runtime(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        spec_dir = self.target / "docs" / "specs" / "002-first"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("---\nstatus: DRAFT\n---\n")
        (spec_dir / "slice-01-start.md").write_text(
            "---\nstatus: DRAFT\ndependencies: []\n---\n\n"
            "## Slice 002-01 - start\n"
        )

        script = (
            self.target / ".codex" / "hooks" / "scripts"
            / "jig-project-orient.sh"
        )
        env = os.environ.copy()
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env["CODEX_PROJECT_DIR"] = str(self.target)
        result = subprocess.run(
            ["bash", str(script)],
            input=json.dumps({"hook_event_name": "SessionStart", "session_id": "s1"}),
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["additionalContext"],
            "jig hint: Scaffolded jig project · active specs: 002 DRAFT · "
            "focus: 002-01 DRAFT",
        )
        self.assertFalse(any(self.target.rglob("__pycache__")))

    def test_codex_semantic_index_internal_overlay_fixture_activates_scout(self):
        r = self._run_codex_scaffold()
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

        state_path = self.target / ".jig" / "semantic-index.json"
        state_path.parent.mkdir(exist_ok=True)
        state_path.write_text(json.dumps({
            "auto_attach": True,
            "provider": "scout",
            "allowed_overlays": ["scout"],
            "timeout_seconds": 1.0,
        }) + "\n")

        calls_path = Path(self.tmpdir) / "scout-calls.jsonl"
        bin_dir = Path(self.tmpdir) / "bin"
        bin_dir.mkdir()
        scout = bin_dir / "scout"
        scout.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$SCOUT_CALLS\"\n"
            "if [ \"$1\" = \"status\" ]; then exit 1; fi\n"
            "exit 0\n"
        )
        scout.chmod(0o755)

        script = self.target / ".codex" / "hooks" / "scripts" / "jig-semantic-index.sh"
        env = os.environ.copy()
        env["CODEX_PROJECT_DIR"] = str(self.target)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env["SCOUT_CALLS"] = str(calls_path)
        result = subprocess.run(
            ["bash", str(script)],
            input=json.dumps({"hook_event_name": "SessionStart", "session_id": "s1"}),
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        calls = calls_path.read_text().splitlines()
        self.assertTrue(any(call.startswith("status ") for call in calls), calls)
        self.assertTrue(any(call.startswith("attach ") for call in calls), calls)
        telemetry = [
            json.loads(line)
            for line in (self.target / ".jig" / "semantic-index-events.jsonl")
            .read_text()
            .splitlines()
        ]
        self.assertEqual(telemetry[-1]["host"], "codex")
        self.assertEqual(telemetry[-1]["provider"], "scout")
        self.assertEqual(telemetry[-1]["provider_profile"], "internal-overlay")
        self.assertEqual(telemetry[-1]["action"], "attach")

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

    def test_codex_accepts_schema_clean_generated_hooks_on_rerun(self):
        hooks_path = self.target / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True)
        hooks_path.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Read",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "${CODEX_PROJECT_DIR:-$PWD}/.codex/"
                                    "hooks/scripts/jig-context-check.sh"
                                ),
                            }
                        ],
                    }
                ]
            }
        }, indent=2) + "\n")

        scaffold_mod._check_codex_hooks_safety(self.target)

    def test_codex_accepts_legacy_metadata_marker_for_repair(self):
        hooks_path = self.target / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True)
        hooks_path.write_text(json.dumps({
            "metadata": {"managed_by_jig": True},
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Read",
                        "hooks": [{"type": "command", "command": "./old.sh"}],
                    }
                ]
            }
        }, indent=2) + "\n")

        scaffold_mod._check_codex_hooks_safety(self.target)


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
        # non-zero exit (rc=3 per the CLI's UnmanagedHooksError branch). The
        # unmanaged-hooks check runs during the machinery copy, so this uses
        # in-repo mode (099-01 / ADR-0041 flipped the default to plugin mode,
        # which never copies machinery and so never reaches the check).
        r1 = run_scaffold_with_args(self.target, "--in-repo")
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
        r2 = run_scaffold_with_args(self.target, "--in-repo")
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
#         plugin-mode artifacts. NB: in-repo was the default under 016-03;
#         since 099-01 plugin mode is, so 'default' below means in-repo only
#         in the historical sense these tests were written in.
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
        # in-repo scaffold — machinery copied to .claude/skills (099-01 flipped
        # the default to plugin mode, so opt in explicitly).
        r = run_scaffold_with_args(self.target, "--in-repo")
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
        # in-repo scaffold: this test validates that the in-repo doc rewrite
        # produces relative links that resolve to the copied tree (099-01
        # flipped the default to plugin mode).
        r = run_scaffold_with_args(self.target, "--in-repo")
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
    command path in an in-repo scaffold (the default under 016-03; since 099-01
    the default is plugin mode), preserved under
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
        as a command path in an in-repo scaffold (099-01 flipped the default
        to plugin mode, which correctly PRESERVES those paths — see the
        companion test — so opt in explicitly here)."""
        target = self._scaffold("--in-repo")
        offenders = []
        for rel in _CORE_DOCS:
            doc = target / rel
            if not doc.is_file():
                continue
            if "${CLAUDE_PLUGIN_ROOT}/skills/" in doc.read_text():
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            "in-repo scaffold leaks ${CLAUDE_PLUGIN_ROOT}/skills/ "
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
