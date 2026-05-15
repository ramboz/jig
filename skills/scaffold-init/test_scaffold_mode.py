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
# Default-off behavior (AC #1 + AC #8 (g)): scaffolding WITHOUT
# --with-machinery must leave .claude/skills and .claude/agents alone.
# --------------------------------------------------------------------------


class DefaultOffMachineryTests(unittest.TestCase):
    """AC #1 + AC #8 (g) — without the flag, the new copy logic is dormant."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-016-default-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_g_no_skills_or_agents_dir_without_flag(self):
        """AC #8 (g) — without --with-machinery, .claude/skills and
        .claude/agents are NOT created. Pure existing-behavior preservation."""
        r = run_scaffold_with_args(self.target)
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (self.target / ".claude" / "skills").exists(),
            ".claude/skills must not exist without --with-machinery",
        )
        self.assertFalse(
            (self.target / ".claude" / "agents").exists(),
            ".claude/agents must not exist without --with-machinery",
        )

    def test_scaffold_mode_defaults_to_plugin_only(self):
        """AC #7 — without --with-machinery, scaffold.json.scaffold_mode
        is 'plugin-only'."""
        r = run_scaffold_with_args(self.target)
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


if __name__ == "__main__":
    unittest.main()
