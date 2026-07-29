"""Tests for `_common/skill_discovery.py` — spec 096-02 (ADR-0040 D2).
Hermetic: every scope root is injected under a tmp dir; no test reads the
developer's real `~/.claude` or `~/.agents`.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import skill_discovery as sd


def _skill(root: Path, name: str, *, desc: str = "d") -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    md = d / "SKILL.md"
    md.write_text(f"---\nname: {name}\ndescription: {desc}\n---\n# {name}\n")
    return md


class ResolveSkillPathTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.proj = self.root / "proj"
        self.proj_skills = self.proj / ".claude" / "skills"
        self.user_skills = self.home / ".claude" / "skills"
        self.admin = self.root / "admin"

    def tearDown(self):
        self._tmp.cleanup()

    def _resolve(self, name, **kw):
        return sd.resolve_skill_path(
            name, host=sd.CLAUDE, project_dir=self.proj, home=self.home,
            admin_roots=[self.admin], **kw
        )

    # -- AC1: resolution across scopes, precedence, conservatism ----------
    def test_resolves_user_scope(self):
        md = _skill(self.user_skills, "review-pr-deep")
        self.assertEqual(self._resolve("review-pr-deep"), str(md))

    def test_resolves_project_scope(self):
        md = _skill(self.proj_skills, "team-review")
        self.assertEqual(self._resolve("team-review"), str(md))

    def test_resolves_admin_scope(self):
        md = _skill(self.admin, "org-review")
        self.assertEqual(self._resolve("org-review"), str(md))

    def test_project_scope_wins_over_user(self):
        proj_md = _skill(self.proj_skills, "dup")
        _skill(self.user_skills, "dup")
        self.assertEqual(self._resolve("dup"), str(proj_md),
                         "most-specific (project) scope must win")

    def test_returns_none_when_unresolvable(self):
        self.assertIsNone(self._resolve("nonexistent"))

    def test_skill_dir_without_skill_md_skipped(self):
        (self.user_skills / "empty").mkdir(parents=True)
        self.assertIsNone(self._resolve("empty"))

    def test_missing_scope_root_is_skipped_not_an_error(self):
        # No scope dirs exist at all → None, no raise.
        self.assertIsNone(self._resolve("anything"))

    def test_honors_injected_home(self):
        md = _skill(self.user_skills, "scoped")
        # Resolution used self.home (injected), not the real ~/.claude.
        self.assertEqual(self._resolve("scoped"), str(md))

    # -- Codex host --------------------------------------------------------
    def test_codex_scopes(self):
        codex_user = self.home / ".agents" / "skills"
        md = _skill(codex_user, "cdx-review")
        got = sd.resolve_skill_path(
            "cdx-review", host=sd.CODEX, project_dir=self.proj,
            home=self.home, admin_roots=[]
        )
        self.assertEqual(got, str(md))

    def test_etc_codex_absent_skipped_silently(self):
        # Default Codex admin root /etc/codex/skills almost never exists; a
        # miss there must not raise.
        got = sd.resolve_skill_path(
            "nope", host=sd.CODEX, project_dir=self.proj, home=self.home
        )
        self.assertIsNone(got)

    # -- AC3 / AC5: jig-baseline exclusion in discovery mode --------------
    def test_jig_prefixed_project_dir_excluded_in_discovery(self):
        _skill(self.proj_skills, "jig-pr-review")
        self.assertIsNone(
            self._resolve("jig-pr-review", exclude_jig_baselines=True)
        )

    def test_jig_prefixed_still_resolvable_without_exclusion(self):
        # AC7: config mode (default) does NOT exclude — explicit config wins.
        md = _skill(self.proj_skills, "jig-pr-review")
        self.assertEqual(self._resolve("jig-pr-review"), str(md))

    def test_genuine_richer_not_excluded(self):
        md = _skill(self.proj_skills, "review-pr-deep")
        self.assertEqual(
            self._resolve("review-pr-deep", exclude_jig_baselines=True),
            str(md),
        )

    def test_symlinked_skill_dir_resolved(self):
        # The documented unblock for the reported bug is `ln -s`; a symlinked
        # skill dir must resolve through (is_file follows symlinks).
        _skill(self.user_skills, "real-skill")
        link = self.user_skills / "linked-skill"
        try:
            link.symlink_to(self.user_skills / "real-skill")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unsupported on this platform")
        self.assertEqual(
            self._resolve("linked-skill"),
            str(link / "SKILL.md"),
        )

    def test_project_scope_under_jig_named_root_resolves_in_discovery(self):
        # End-to-end: a genuine richer skill at project scope whose project_dir
        # path contains a `jig` segment is NOT excluded (the anchoring fix).
        jig_named_proj = self.root / "misc" / "jig" / "checkout"
        pskills = jig_named_proj / ".claude" / "skills"
        md = _skill(pskills, "review-pr-deep")
        got = sd.resolve_skill_path(
            "review-pr-deep", host=sd.CLAUDE, project_dir=jig_named_proj,
            home=self.home, admin_roots=[], exclude_jig_baselines=True,
        )
        self.assertEqual(got, str(md))

    def test_plugin_scope_jig_skill_excluded_in_discovery(self):
        # A jig plugin-scope baseline (unprefixed skill dir under a `jig`
        # plugin segment) is excluded by the path test.
        plugin_admin = self.root / "plugins" / "jig" / "skills"
        _skill(plugin_admin, "pr-review")
        got = sd.resolve_skill_path(
            "pr-review", host=sd.CLAUDE, project_dir=self.proj,
            home=self.home, admin_roots=[plugin_admin],
            exclude_jig_baselines=True,
        )
        self.assertIsNone(got)


class DefaultAdminRootsTest(unittest.TestCase):
    def test_globs_plugin_skills_dirs(self):
        with TemporaryDirectory() as td:
            home = Path(td) / "home"
            p = home / ".claude" / "plugins" / "cache" / "jig" / "jig" / \
                "2.5.0" / "skills"
            p.mkdir(parents=True)
            roots = sd._default_claude_admin_roots(home)
            self.assertIn(p, roots)

    def test_absent_plugins_dir_yields_empty(self):
        with TemporaryDirectory() as td:
            self.assertEqual(
                sd._default_claude_admin_roots(Path(td) / "home"), []
            )


class IsJigBaselinePathTest(unittest.TestCase):
    def test_prefixed_project_dir(self):
        self.assertTrue(
            sd.is_jig_baseline_path(
                Path("/x/proj/.claude/skills/jig-arch-review/SKILL.md")
            )
        )

    def test_jig_plugin_segment(self):
        self.assertTrue(
            sd.is_jig_baseline_path(
                Path("/h/.claude/plugins/cache/jig/jig/2.5.0/skills/"
                     "pr-review/SKILL.md")
            )
        )

    def test_genuine_richer_not_baseline(self):
        self.assertFalse(
            sd.is_jig_baseline_path(
                Path("/x/proj/.claude/skills/review-pr-deep/SKILL.md")
            )
        )

    def test_jig_named_ancestor_without_plugins_not_baseline(self):
        # A genuine richer skill at project scope inside a `jig`-named path
        # (jig's own repo while dogfooding, or a checkout under .../misc/jig/...)
        # must NOT be misclassified — the admin test is anchored to `plugins/`.
        self.assertFalse(
            sd.is_jig_baseline_path(
                Path("/Users/x/Projects/misc/jig/.claude/skills/"
                     "review-pr-deep/SKILL.md")
            )
        )
        self.assertFalse(
            sd.is_jig_baseline_path(
                Path("/w/.claude/worktrees/spec-096-jig-x/.claude/skills/"
                     "team-review/SKILL.md")
            )
        )

    def test_jig_before_plugins_not_matched(self):
        # `jig` appearing BEFORE the plugins segment is not a plugin baseline.
        self.assertFalse(
            sd.is_jig_baseline_path(
                Path("/home/jig/x/plugins/other/skills/review/SKILL.md")
            )
        )

    def test_user_scope_named_pr_review_not_baseline(self):
        # A user's own skill literally named `pr-review` at user scope is NOT a
        # jig baseline (no jig- prefix, no jig plugin segment).
        self.assertFalse(
            sd.is_jig_baseline_path(
                Path("/h/.claude/skills/pr-review/SKILL.md")
            )
        )


class ParseSkillFrontmatterTest(unittest.TestCase):
    def test_plain(self):
        got = sd.parse_skill_frontmatter(
            "---\nname: pr-review\ndescription: Team baseline\n---\nbody"
        )
        self.assertEqual(got, {"name": "pr-review",
                               "description": "Team baseline"})

    def test_folded_scalar(self):
        got = sd.parse_skill_frontmatter(
            "---\nname: x\ndescription: >\n  line one\n  line two\n---\n"
        )
        self.assertEqual(got["description"], "line one line two")

    def test_literal_scalar(self):
        got = sd.parse_skill_frontmatter(
            "---\nname: x\ndescription: |\n  a\n  b\n---\n"
        )
        self.assertEqual(got["description"], "a\nb")

    def test_quoted_value_unquoted(self):
        got = sd.parse_skill_frontmatter('---\nname: "quoted"\n---\n')
        self.assertEqual(got["name"], "quoted")

    def test_absent_frontmatter_returns_none(self):
        self.assertIsNone(sd.parse_skill_frontmatter("no frontmatter"))

    def test_missing_keys_simply_absent(self):
        got = sd.parse_skill_frontmatter("---\nother: 1\n---\n")
        self.assertNotIn("name", got)
        self.assertNotIn("description", got)

    def test_malformed_body_never_raises(self):
        # Weird but non-crashing content.
        got = sd.parse_skill_frontmatter("---\n: : :\nname: ok\n---\n")
        self.assertEqual(got.get("name"), "ok")


class ScaffoldExclusionInvariantTest(unittest.TestCase):
    """AC3's load-bearing invariant, tested against the REAL scaffold writer:
    every project-scope skill dir a jig scaffold writes that carries a
    `SKILL.md` is `jig-` prefixed, and every UNprefixed dir it writes carries
    no `SKILL.md`. This is what lets `is_jig_baseline_path`'s prefix test
    cleanly separate jig baselines from genuine richer skills."""

    def test_scaffolded_skill_dirs_prefixed_or_have_no_skill_md(self):
        import sys
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "skills" / "scaffold-init"))
        import scaffold  # noqa: E402
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            scaffold._copy_skills_and_agents(repo_root, target)
            skills_dst = target / ".claude" / "skills"
            self.assertTrue(skills_dst.is_dir(), "scaffold wrote no skills")
            offenders = []
            for d in sorted(skills_dst.iterdir()):
                if not d.is_dir():
                    continue
                has_skill_md = (d / "SKILL.md").is_file()
                if has_skill_md and not d.name.startswith("jig-"):
                    offenders.append(d.name)
            self.assertEqual(
                offenders, [],
                "unprefixed project-scope skill dir(s) carry a SKILL.md — "
                f"the jig- exclusion invariant is broken: {offenders}",
            )
            # And every jig baseline the scaffold wrote IS excluded by the
            # discovery predicate (end-to-end).
            for d in sorted(skills_dst.iterdir()):
                md = d / "SKILL.md"
                if md.is_file():
                    self.assertTrue(
                        sd.is_jig_baseline_path(md),
                        f"scaffolded baseline {d.name} not excluded",
                    )


if __name__ == "__main__":
    unittest.main()
