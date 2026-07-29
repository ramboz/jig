"""Tests for `_common/review_config.py` — spec 096-01 (ADR-0040 D1) config
resolution. Hermetic: every test injects `$HOME` + a tmp project dir and never
reads the developer's real `~/.claude` or scaffold.json.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import review_config as rc


class ReviewConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        (self.home / ".claude" / "skills").mkdir(parents=True)
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.home)
        self.proj = self.root / "proj"
        self.proj.mkdir()

    def tearDown(self) -> None:
        if self._old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._old_home
        self._tmp.cleanup()

    # -- fixtures ---------------------------------------------------------
    def _install_user_skill(self, name: str) -> Path:
        d = self.home / ".claude" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        skill = d / "SKILL.md"
        skill.write_text(f"---\nname: {name}\n---\n# {name}\n", encoding="utf-8")
        return skill

    def _write_scaffold(self, obj) -> None:
        (self.proj / "scaffold.json").write_text(
            json.dumps(obj), encoding="utf-8"
        )

    # -- AC1: name/path resolution ---------------------------------------
    def test_bare_name_resolves_at_user_scope(self):
        skill = self._install_user_skill("review-pr-deep")
        self._write_scaffold({"review": {"pr_review_skill": "review-pr-deep"}})
        self.assertEqual(
            rc.configured_skill(self.proj, "pr_review"), str(skill)
        )

    def test_explicit_file_path_used_as_is(self):
        skill = self._install_user_skill("x")
        self._write_scaffold({"review": {"arch_review_skill": str(skill)}})
        self.assertEqual(
            rc.configured_skill(self.proj, "arch_review"), str(skill)
        )

    def test_explicit_dir_path_appends_skill_md(self):
        skill = self._install_user_skill("x")
        self._write_scaffold(
            {"review": {"code_health_skill": str(skill.parent)}}
        )
        self.assertEqual(
            rc.configured_skill(self.proj, "code_health"), str(skill)
        )

    def test_absent_scaffold_json_returns_none(self):
        self.assertIsNone(rc.configured_skill(self.proj, "pr_review"))

    def test_absent_review_block_returns_none(self):
        self._write_scaffold({"layout": {"docs_root": "docs"}})
        self.assertIsNone(rc.configured_skill(self.proj, "pr_review"))

    def test_absent_category_key_returns_none(self):
        self._install_user_skill("review-pr-deep")
        self._write_scaffold({"review": {"pr_review_skill": "review-pr-deep"}})
        self.assertIsNone(rc.configured_skill(self.proj, "arch_review"))

    def test_empty_string_value_returns_none(self):
        self._write_scaffold({"review": {"pr_review_skill": ""}})
        self.assertIsNone(rc.configured_skill(self.proj, "pr_review"))

    # -- AC2: runtime absence quiet; structural malformation loud ---------
    def test_wellformed_name_not_installed_returns_none(self):
        # A committed, team-shared config naming a skill this machine lacks must
        # fall back to baseline, NOT raise (ADR-0040 D1).
        self._write_scaffold({"review": {"pr_review_skill": "not-installed"}})
        self.assertIsNone(rc.configured_skill(self.proj, "pr_review"))

    def test_non_object_review_raises(self):
        self._write_scaffold({"review": "oops"})
        with self.assertRaises(rc.ReviewConfigError):
            rc.configured_skill(self.proj, "pr_review")

    def test_non_string_value_raises(self):
        self._write_scaffold({"review": {"pr_review_skill": 123}})
        with self.assertRaises(rc.ReviewConfigError):
            rc.configured_skill(self.proj, "pr_review")

    def test_non_string_value_raises_lists_key(self):
        self._write_scaffold({"review": {"arch_review_skill": ["a"]}})
        with self.assertRaises(rc.ReviewConfigError) as ctx:
            rc.configured_skill(self.proj, "arch_review")
        self.assertIn("arch_review_skill", str(ctx.exception))

    def test_malformed_json_is_treated_as_no_config(self):
        # A broken-but-unrelated scaffold.json must not break a review pass:
        # config resolution returns None rather than raising here (the *review*
        # block's structural validation is what fails loud).
        (self.proj / "scaffold.json").write_text("{ not json", encoding="utf-8")
        self.assertIsNone(rc.configured_skill(self.proj, "pr_review"))

    # -- edge cases -------------------------------------------------------
    # -- 096-02: config bare-name resolution is now multi-scope/host --------
    def test_bare_name_resolves_at_project_scope(self):
        # 096-02 upgrade: a bare config name resolves at PROJECT scope too, not
        # just user scope (096-01 was user-scope only).
        d = self.proj / ".claude" / "skills" / "team-pr"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: team-pr\n---\n")
        self._write_scaffold({"review": {"pr_review_skill": "team-pr"}})
        self.assertEqual(
            rc.configured_skill(self.proj, "pr_review"), str(d / "SKILL.md")
        )

    def test_bare_name_resolves_on_codex_scope(self):
        # Closes the 096-01 Codex bare-name seam: a bare name installed under
        # Codex's user scope resolves.
        d = self.home / ".agents" / "skills" / "cdx-pr"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: cdx-pr\n---\n")
        self._write_scaffold({"review": {"arch_review_skill": "cdx-pr"}})
        self.assertEqual(
            rc.configured_skill(self.proj, "arch_review"), str(d / "SKILL.md")
        )

    def test_relative_explicit_path_anchored_to_project(self):
        # A relative explicit path in the committed scaffold.json anchors to the
        # project dir, not the process CWD.
        d = self.proj / "tools" / "my-review"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: my-review\n---\n")
        self._write_scaffold(
            {"review": {"pr_review_skill": "tools/my-review"}}
        )
        self.assertEqual(
            rc.configured_skill(self.proj, "pr_review"), str(d / "SKILL.md")
        )

    def test_config_bare_name_does_not_exclude_jig_baseline(self):
        # AC7: config resolution does NOT apply the discovery exclusion — a user
        # who names a jig-prefixed project skill in config gets it.
        d = self.proj / ".claude" / "skills" / "jig-pr-review"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: pr-review\n---\n")
        self._write_scaffold({"review": {"pr_review_skill": "jig-pr-review"}})
        self.assertEqual(
            rc.configured_skill(self.proj, "pr_review"), str(d / "SKILL.md")
        )

    def test_docs_root_dot_project_is_sentinel_anchored(self):
        # A docs_root="." project still keeps scaffold.json at the project root,
        # so config discovery is unaffected.
        skill = self._install_user_skill("team-pr")
        self._write_scaffold(
            {"layout": {"docs_root": "."},
             "review": {"pr_review_skill": "team-pr"}}
        )
        self.assertEqual(
            rc.configured_skill(self.proj, "pr_review"), str(skill)
        )

    def test_jig_baseline_path_is_allowed(self):
        # Configuring jig's own baseline path is explicit user intent — allowed
        # (the exclusion is a discovery filter, not a config filter).
        baseline = self.proj / ".claude" / "skills" / "jig-pr-review"
        baseline.mkdir(parents=True)
        (baseline / "SKILL.md").write_text("---\nname: pr-review\n---\n")
        self._write_scaffold(
            {"review": {"pr_review_skill": str(baseline / "SKILL.md")}}
        )
        self.assertEqual(
            rc.configured_skill(self.proj, "pr_review"),
            str(baseline / "SKILL.md"),
        )

    def test_unknown_category_raises(self):
        with self.assertRaises(rc.ReviewConfigError):
            rc.configured_skill(self.proj, "security_review")

    # -- module-level contracts ------------------------------------------
    def test_categories_are_exactly_three(self):
        self.assertEqual(
            rc.CATEGORIES, ("pr_review", "arch_review", "code_health")
        )
        self.assertNotIn("security_review", rc.CATEGORIES)
        self.assertNotIn("design_review", rc.CATEGORIES)

    # -- configured_value: the portable raw identifier (096-01 evidence) ---
    def test_configured_value_returns_raw_bare_name_unresolved(self):
        # Records the identifier as written — no resolution, no absolute path —
        # even when the named skill is NOT installed on this machine.
        self._write_scaffold({"review": {"pr_review_skill": "review-pr-deep"}})
        self.assertEqual(
            rc.configured_value(self.proj, "pr_review"), "review-pr-deep"
        )

    def test_configured_value_none_when_absent(self):
        self.assertIsNone(rc.configured_value(self.proj, "pr_review"))

    def test_configured_value_raises_on_non_string(self):
        self._write_scaffold({"review": {"arch_review_skill": 5}})
        with self.assertRaises(rc.ReviewConfigError):
            rc.configured_value(self.proj, "arch_review")

    def test_pass_to_category_mapping(self):
        self.assertEqual(rc.PASS_TO_CATEGORY["craft"], "pr_review")
        self.assertEqual(rc.PASS_TO_CATEGORY["arch"], "arch_review")
        self.assertEqual(rc.PASS_TO_CATEGORY["code-health"], "code_health")
        # never-defer / follow-up passes map to nothing
        for p in ("compliance", "reconciliation", "frame-critique",
                  "design-review", "bug-review", "security"):
            self.assertNotIn(p, rc.PASS_TO_CATEGORY)


if __name__ == "__main__":
    unittest.main()
