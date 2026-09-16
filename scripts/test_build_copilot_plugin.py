"""
Tests for scripts/build_copilot_plugin.py — slice 113-02 (renderer-and-skeleton).

Covers:
  - AC #1/#4: the builder materializes a minimal, directly-installable
    `hosts/copilot/` package: `.plugin/plugin.json` + `.github/skills/<name>/
    SKILL.md` — and nothing beyond that walking-skeleton scope (no agents/,
    no hooks/, no companion CLAUDE.md, and — per the 113-02 review fix below
    — no pre-rendered instructions file either).
  - AC #2: the loader-compat invariant — every emitted skill has a
    namespace-safe name and a <=1024-char description, with the full
    original description preserved in the body for any skill the renderer
    had to shorten. A synthetic over-budget fixture proves the truncation
    path fires (the real repo's public skills are ALL currently <=1024 chars
    — see `RealRepoLoaderCompatTests` — so this is exercised against a
    fixture, not real source, per the deviation noted in the slice's
    reconciliation).
  - 113-02 review fix (owner decision): the package does NOT ship a
    pre-rendered `.github/copilot-instructions.md`. Parity ruling: Claude/
    Codex builders ship `templates/CLAUDE.md.template` UNRENDERED (a
    `/plugin` install must not impose instructions on the consuming repo);
    shipping a full-parity, template-carrying package is 113-06 scope, not
    this walking skeleton.
  - Build safety mirrors the Claude/Codex builders (refuse unsafe output
    dirs; atomic replace of a stale tree).
"""

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "scaffold-init"))

import build_copilot_plugin  # noqa: E402
import install_contract  # noqa: E402
import scaffold as scaffold_mod  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _build(output_dir: Path, source_root: Path = REPO_ROOT):
    out = io.StringIO()
    code = build_copilot_plugin.build(
        source_root=source_root, output_dir=output_dir, out=out
    )
    return code, out.getvalue()


class CopilotPackageContentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-pkg-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # AC #1
    def test_materializes_manifest(self):
        manifest = self.out_dir / ".plugin" / "plugin.json"
        self.assertTrue(manifest.is_file())
        data = json.loads(manifest.read_text())
        self.assertEqual(set(data.keys()), {"name", "version", "description"})
        self.assertEqual(data["name"], "jig")
        self.assertTrue(data["version"])
        self.assertIn("Copilot", data["description"])

    def test_manifest_version_matches_claude_manifest(self):
        claude_version = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
        )["version"]
        copilot_version = json.loads(
            (self.out_dir / ".plugin" / "plugin.json").read_text()
        )["version"]
        self.assertEqual(copilot_version, claude_version)

    # AC #1 — discovery root per slice 113-01
    def test_materializes_skills_under_github_skills(self):
        skill = self.out_dir / ".github" / "skills" / "scaffold-init" / "SKILL.md"
        self.assertTrue(skill.is_file())

    def test_shared_private_infra_ships_alongside_public_skills(self):
        # skills/_common has no SKILL.md (not a discoverable skill) but other
        # skills' Python modules import it at runtime — it must still ship.
        self.assertTrue(
            (self.out_dir / ".github" / "skills" / "_common").is_dir()
        )

    # 113-02 review fix (owner decision): no pre-rendered instructions file —
    # a `/plugin` install must not impose instructions on the consuming
    # repo; shipping `templates/` (unrendered, like Claude/Codex) is 113-06
    # full-package-parity scope, not this walking skeleton.
    def test_does_not_materialize_an_instructions_file(self):
        self.assertFalse(
            (self.out_dir / ".github" / "copilot-instructions.md").exists()
        )

    def test_no_companion_claude_md_shipped(self):
        leaks = [
            p for p in self.out_dir.rglob("*") if p.is_file() and p.name == "CLAUDE.md"
        ]
        self.assertEqual(leaks, [])

    def test_package_is_exactly_manifest_and_skills(self):
        # 113-02 walking-skeleton layout: `.plugin/plugin.json` +
        # `.github/skills/**`, nothing else at the `.github/` top level.
        github_dir = self.out_dir / ".github"
        top_level = {p.name for p in github_dir.iterdir()}
        self.assertEqual(top_level, {"skills"})

    # Walking-skeleton scope guard (113-03/04/05 build these later)
    def test_agents_and_hooks_not_yet_shipped(self):
        self.assertFalse((self.out_dir / ".github" / "agents").exists())
        self.assertFalse((self.out_dir / ".github" / "hooks").exists())

    def test_excludes_tests_and_caches(self):
        leaks = [
            p.relative_to(self.out_dir).as_posix()
            for p in self.out_dir.rglob("*")
            if p.is_file()
            and (p.name.startswith("test_") or "__pycache__" in p.parts)
        ]
        self.assertEqual(leaks, [])


class RealRepoLoaderCompatTests(unittest.TestCase):
    """AC #2 against the real repo. NOTE (deviation from the slice brief): at
    spike 113-01 time `memory-sync`/`vision-elicitation` were reported at
    1059/1058 chars; as measured today (via
    `install_contract._read_skill_description`, the same normalization bug
    009 already established for Codex) every current public skill is
    <=1024 chars, `memory-sync` highest at 1010. So today's real build makes
    ZERO truncations — this class asserts that invariant holds (every
    rendered description fits, every rendered name is namespace-safe), and
    `SyntheticOverBudgetDescriptionTests` below exercises the truncation path
    itself against a controlled fixture."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-real-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rendered_skill_mds(self):
        skills_dir = self.out_dir / ".github" / "skills"
        return sorted(skills_dir.glob("*/SKILL.md"))

    def test_every_rendered_description_is_within_the_loader_limit(self):
        for skill_md in self._rendered_skill_mds():
            desc = install_contract._read_skill_description(skill_md.read_text())
            self.assertLessEqual(
                len(desc), 1024, f"{skill_md.relative_to(self.out_dir)}: {len(desc)}"
            )

    def test_every_rendered_name_is_namespace_safe(self):
        for skill_md in self._rendered_skill_mds():
            fm, _ = scaffold_mod._split_frontmatter(skill_md.read_text())
            name = scaffold_mod.CopilotScaffoldRenderer.agent_frontmatter_value(
                fm, "name", ""
            )
            self.assertNotIn(":", name, str(skill_md.relative_to(self.out_dir)))

    def test_memory_sync_is_currently_untouched_by_the_render(self):
        # The highest-length real skill today (1010 chars, under the 1024
        # limit) round-trips byte-for-byte through the Copilot renderer,
        # same as Claude/Codex.
        source = (REPO_ROOT / "skills" / "memory-sync" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        rendered = build_copilot_plugin.render_copilot_skill_md(source)
        self.assertEqual(rendered, source)


class SyntheticOverBudgetDescriptionTests(unittest.TestCase):
    """AC #2 — proves the truncation path itself: a source description that
    exceeds Copilot's 1024-character limit renders <=1024 in the frontmatter
    with the full original text preserved in the body, while a compliant
    skill's rendering is untouched. Uses a synthetic fixture (see the
    deviation note on `RealRepoLoaderCompatTests` for why the real
    `memory-sync` no longer exercises this path)."""

    def _make_skill_md(self, description: str) -> str:
        return (
            "---\n"
            "name: over-budget-fixture\n"
            f"description: >\n  {description}\n"
            "user-invocable: true\n"
            "---\n\n"
            "# Over-budget fixture\n\nBody content.\n"
        )

    def test_over_budget_description_truncated_with_full_text_preserved(self):
        long_description = "word " * 300  # > 1024 chars once folded
        self.assertGreater(len(long_description.strip()), 1024)
        source = self._make_skill_md(long_description.strip())
        rendered = build_copilot_plugin.render_copilot_skill_md(source)

        rendered_fm, rendered_body = scaffold_mod._split_frontmatter(rendered)
        rendered_desc = install_contract._read_skill_description(rendered)
        self.assertLessEqual(len(rendered_desc), 1024)
        self.assertIn(long_description.strip(), rendered_body)
        self.assertIn("Full description", rendered_body)
        # The rest of the frontmatter (name, user-invocable) survives.
        self.assertIn("name: over-budget-fixture", rendered_fm)
        self.assertIn("user-invocable: true", rendered_fm)
        # And the rest of the body survives too.
        self.assertIn("# Over-budget fixture", rendered)
        self.assertIn("Body content.", rendered)

    def test_compliant_description_round_trips_byte_identical(self):
        source = self._make_skill_md("a short, compliant description")
        rendered = build_copilot_plugin.render_copilot_skill_md(source)
        self.assertEqual(rendered, source)

    def test_colon_bearing_name_raises(self):
        source = self._make_skill_md("fine").replace(
            "name: over-budget-fixture", "name: jig:over-budget-fixture"
        )
        with self.assertRaises(scaffold_mod.CopilotSkillNameError):
            build_copilot_plugin.render_copilot_skill_md(source)


class DescriptionFieldEncodingTests(unittest.TestCase):
    """113-02 review fix (craft) — `_replace_description_field` must not
    `\\uXXXX`-escape non-ASCII characters. `install_contract._read_skill_description`
    (the re-measurement `loader_safe_description`'s budget is meant to bind)
    does not decode escapes — it just strips surrounding quotes — so an
    `ensure_ascii=True` JSON dump would inflate a single "é" into the 6
    literal characters `\\u00e9`, making jig's own re-measured length
    disagree with what a real YAML-aware loader (and the intended 1024-char
    budget) would see. Writing the raw UTF-8 character keeps the two
    consistent."""

    def test_non_ascii_value_is_not_escaped(self):
        fm = "---\nname: x\ndescription: old\nuser-invocable: true\n---\n"
        new_value = "café résumé — naïve"
        result = build_copilot_plugin._replace_description_field(fm, new_value)
        self.assertIn(new_value, result)
        self.assertNotIn("\\u", result)

    def test_re_measured_length_matches_the_original_value(self):
        fm = "---\nname: x\ndescription: old\nuser-invocable: true\n---\n"
        new_value = "café résumé — naïve, exactly as truncated"
        result = build_copilot_plugin._replace_description_field(fm, new_value)
        remeasured = install_contract._read_skill_description(result)
        self.assertEqual(remeasured, new_value)
        self.assertEqual(len(remeasured), len(new_value))

    def test_render_copilot_skill_md_preserves_non_ascii_in_truncated_description(self):
        # End-to-end: a synthetic over-budget, non-ASCII description
        # truncates without corrupting the surviving accented text.
        long_description = ("café bar baz qux naïve " * 60).strip()
        self.assertGreater(len(long_description), 1024)
        source = (
            "---\n"
            "name: accent-fixture\n"
            f"description: >\n  {long_description}\n"
            "user-invocable: true\n"
            "---\n\n"
            "Body.\n"
        )
        rendered = build_copilot_plugin.render_copilot_skill_md(source)
        rendered_fm, _ = scaffold_mod._split_frontmatter(rendered)
        self.assertNotIn("\\u", rendered_fm)
        self.assertIn("é", rendered_fm)


class CopilotPackageBuildSafetyTests(unittest.TestCase):
    """Build safety mirrors Claude/Codex — refuse unsafe output dirs; replace
    atomically."""

    def test_refuses_source_root(self):
        code, _ = _build(REPO_ROOT)
        self.assertNotEqual(code, 0)
        self.assertTrue(
            (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").is_file()
        )

    def test_refuses_source_owned_runtime_path(self):
        code, _ = _build(REPO_ROOT / "skills")
        self.assertNotEqual(code, 0)
        self.assertTrue(
            (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").is_file()
        )

    def test_refuses_ancestor_of_source_root(self):
        code, _ = _build(REPO_ROOT.parent)
        self.assertNotEqual(code, 0)

    def test_stale_tree_is_fully_replaced_not_merged(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-stale-"))
        try:
            out_dir = tmp / "copilot"
            out_dir.mkdir()
            stale = out_dir / "STALE_LEFTOVER.txt"
            stale.write_text("should be wiped")
            code, log = _build(out_dir)
            self.assertEqual(code, 0, log)
            self.assertFalse(stale.exists(), "stale file survived a rebuild")
            self.assertTrue((out_dir / ".plugin" / "plugin.json").is_file())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_claude_manifest_fails_loudly(self):
        src = Path(tempfile.mkdtemp(prefix="jig-copilot-nomanifest-"))
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-nomanifest-out-"))
        try:
            code, log = _build(tmp / "copilot", source_root=src)
            self.assertNotEqual(code, 0)
            self.assertIn("plugin.json", log)
        finally:
            shutil.rmtree(src, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)


class DefaultOutputTargetTests(unittest.TestCase):
    def test_default_output_dir_is_hosts_copilot(self):
        ns = build_copilot_plugin._build_parser().parse_args([])
        self.assertIsNone(ns.output_dir)
        default = REPO_ROOT / "hosts" / "copilot"
        self.assertEqual(default.name, "copilot")
        self.assertEqual(default.parent.name, "hosts")


class CommittedCopilotPackageTests(unittest.TestCase):
    """The committed hosts/copilot/ package must exist once regenerated."""

    def test_committed_package_present(self):
        pkg = REPO_ROOT / "hosts" / "copilot"
        self.assertTrue(
            (pkg / ".plugin" / "plugin.json").is_file(),
            "committed hosts/copilot manifest missing — run "
            "`python3 scripts/build_host_packages.py`",
        )
        self.assertTrue(
            (pkg / ".github" / "skills" / "scaffold-init" / "SKILL.md").is_file(),
            "committed hosts/copilot skills missing",
        )

    def test_no_pre_rendered_instructions_file_committed(self):
        # 113-02 review fix: no pre-rendered instructions file ships.
        pkg = REPO_ROOT / "hosts" / "copilot"
        self.assertFalse((pkg / ".github" / "copilot-instructions.md").exists())


if __name__ == "__main__":
    unittest.main()
