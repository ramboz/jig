"""
Tests for scripts/build_claude_plugin.py — slice 061-01
(committed Claude package + repoint marketplace).

Covers:
  - AC #1: a builder materializes hosts/claude/ from canonical source
    (agents/, skills/, hooks/, templates/, .claude-plugin/plugin.json,
    README/LICENSE when present), reusing the release-zip runtime
    include/exclude set rather than restating it.
  - AC #2: the package is runtime-only — excludes docs/, .github/, tests,
    fixtures, caches, and dev scripts; includes only the runtime scripts
    allowlist; preserves nested runtime paths (hooks/scripts/, templates/docs/);
    does NOT contain .claude-plugin/marketplace.json or any
    .codex-plugin/ content.
  - AC #3: the root marketplace pointer resolves to ./hosts/claude.
  - AC #4: build safety mirrors Codex (refuse unsafe output dirs; atomic
    replace of a stale tree).
  - AC #5: install_contract accepts hosts/claude/ as the Claude install tree.
  - Edge cases: missing optional LICENSE/README warn but build; a stale
    pre-existing tree is fully replaced (not merged).
"""

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_claude_plugin  # noqa: E402
import build_release_zip  # noqa: E402
import install_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _build(output_dir: Path, source_root: Path = REPO_ROOT):
    out = io.StringIO()
    code = build_claude_plugin.build(
        source_root=source_root, output_dir=output_dir, out=out
    )
    return code, out.getvalue()


class ClaudePackageContentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-claude-pkg-"))
        self.out_dir = self.tmp / "claude"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # AC #1
    def test_materializes_runtime_roots_and_manifest(self):
        self.assertTrue((self.out_dir / ".claude-plugin" / "plugin.json").is_file())
        for root in ("agents", "skills", "hooks", "templates"):
            self.assertTrue((self.out_dir / root).is_dir(), root)

    def test_copies_optional_top_level_files_when_present(self):
        self.assertTrue((self.out_dir / "README.md").is_file())
        self.assertTrue((self.out_dir / "LICENSE").is_file())

    # AC #2 — runtime-only excludes
    def test_excludes_source_only_top_level_dirs(self):
        for root in ("docs", ".github"):
            self.assertFalse((self.out_dir / root).exists(), root)

    def test_copies_only_runtime_scripts_allowlist(self):
        scripts = {
            p.relative_to(self.out_dir).as_posix()
            for p in (self.out_dir / "scripts").glob("*.py")
        }
        self.assertEqual(
            scripts,
            set(install_contract.RELEASE_INCLUDE_SCRIPT_FILES),
        )

    def test_excludes_codex_plugin_content(self):
        self.assertFalse((self.out_dir / ".codex-plugin").exists())

    def test_does_not_contain_marketplace_json(self):
        self.assertFalse(
            (self.out_dir / ".claude-plugin" / "marketplace.json").exists()
        )

    def test_excludes_tests_and_caches(self):
        leaks = [
            p.relative_to(self.out_dir).as_posix()
            for p in self.out_dir.rglob("*")
            if p.is_file()
            and install_contract.is_excluded_release_path(
                p.relative_to(self.out_dir).as_posix()
            )
        ]
        self.assertEqual(leaks, [], f"runtime package leaked excluded paths: {leaks}")

    # AC #2 — preserves nested runtime paths
    def test_preserves_nested_runtime_paths(self):
        self.assertTrue(
            (self.out_dir / "hooks" / "scripts").is_dir(),
            "hooks/scripts/ (the actual hook scripts) must survive",
        )
        self.assertTrue((self.out_dir / "templates" / "docs").is_dir())

    # AC #5
    def test_install_contract_accepts_the_package(self):
        problems = install_contract.validate_claude_package(self.out_dir)
        self.assertEqual(problems, [], problems)

    def test_install_contract_finds_skills_and_agents(self):
        self.assertEqual(install_contract.missing_skills(self.out_dir), [])
        self.assertEqual(install_contract.missing_agents(self.out_dir), [])


class ClaudePackageReusesReleaseSubsetTests(unittest.TestCase):
    """AC #1: the builder reuses the release-zip include/exclude logic rather
    than restating it."""

    def test_reuses_release_zip_exclusion_predicates(self):
        # The Claude builder must route through build_release_zip's exclusion
        # predicates, not maintain a private copy.
        self.assertIs(
            build_claude_plugin._is_excluded_file,
            build_release_zip._is_excluded_file,
        )
        self.assertIs(
            build_claude_plugin._is_excluded_dir,
            build_release_zip._is_excluded_dir,
        )


class ClaudePackageBuildSafetyTests(unittest.TestCase):
    """AC #4 — refuse unsafe output dirs; replace atomically."""

    def test_refuses_source_root(self):
        code, log = _build(REPO_ROOT)
        self.assertNotEqual(code, 0)
        self.assertTrue((REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").is_file())

    def test_refuses_source_owned_runtime_path(self):
        code, log = _build(REPO_ROOT / "skills")
        self.assertNotEqual(code, 0)
        self.assertTrue(
            (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").is_file()
        )

    def test_refuses_ancestor_of_source_root(self):
        code, log = _build(REPO_ROOT.parent)
        self.assertNotEqual(code, 0)

    def test_stale_tree_is_fully_replaced_not_merged(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-claude-stale-"))
        try:
            out_dir = tmp / "claude"
            out_dir.mkdir()
            stale = out_dir / "STALE_LEFTOVER.txt"
            stale.write_text("should be wiped")
            code, log = _build(out_dir)
            self.assertEqual(code, 0, log)
            self.assertFalse(stale.exists(), "stale file survived a rebuild")
            self.assertTrue((out_dir / ".claude-plugin" / "plugin.json").is_file())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ClaudePackageOptionalFileWarningTests(unittest.TestCase):
    """Edge case: missing optional LICENSE/README warns but builds anyway."""

    def _fake_source(self) -> Path:
        src = Path(tempfile.mkdtemp(prefix="jig-claude-src-"))
        (src / ".claude-plugin").mkdir()
        (src / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "jig", "version": "0.0.0", "description": "x"})
        )
        skill = src / "skills" / "demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# demo\n")
        (src / "agents").mkdir()
        (src / "hooks").mkdir()
        (src / "templates").mkdir()
        return src

    def test_missing_optional_files_warn_but_build(self):
        src = self._fake_source()
        tmp = Path(tempfile.mkdtemp(prefix="jig-claude-out-"))
        try:
            out_dir = tmp / "claude"
            code, log = _build(out_dir, source_root=src)
            self.assertEqual(code, 0, log)
            self.assertIn("README.md", log)
            self.assertIn("LICENSE", log)
            self.assertIn("WARN", log)
            self.assertFalse((out_dir / "README.md").exists())
            self.assertTrue((out_dir / ".claude-plugin" / "plugin.json").is_file())
        finally:
            shutil.rmtree(src, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)


class RootMarketplaceRepointTests(unittest.TestCase):
    """AC #3 — the committed root pointer resolves to ./hosts/claude while
    keeping the git-subdir / owner / description shape."""

    def setUp(self):
        self.data = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text()
        )

    def test_root_marketplace_points_at_hosts_claude(self):
        plugin = self.data["plugins"][0]
        source = plugin["source"]
        self.assertEqual(source["source"], "git-subdir")
        self.assertEqual(source["path"], "hosts/claude")
        self.assertNotEqual(source["path"], ".")

    def test_root_marketplace_keeps_owner_and_description_shape(self):
        self.assertEqual(self.data["owner"]["name"], "ramboz")
        self.assertEqual(self.data["plugins"][0]["name"], "jig")
        self.assertIn("description", self.data["plugins"][0])
        self.assertIn(
            "github.com/ramboz/jig", self.data["plugins"][0]["source"]["url"]
        )

    def test_root_marketplace_still_validates(self):
        self.assertEqual(
            install_contract.validate_marketplace_manifest(self.data), []
        )


class CommittedClaudePackageTests(unittest.TestCase):
    """The package is committed per ADR-0018; the checked-in tree must match a
    fresh build and satisfy the contract."""

    def test_committed_package_exists_and_is_runtime_only(self):
        pkg = REPO_ROOT / "hosts" / "claude"
        self.assertTrue(
            (pkg / ".claude-plugin" / "plugin.json").is_file(),
            "committed hosts/claude package missing",
        )
        self.assertFalse((pkg / ".codex-plugin").exists())
        self.assertFalse((pkg / ".claude-plugin" / "marketplace.json").exists())
        scripts = {
            p.relative_to(pkg).as_posix()
            for p in (pkg / "scripts").glob("*.py")
        }
        self.assertEqual(
            scripts,
            set(install_contract.RELEASE_INCLUDE_SCRIPT_FILES),
        )
        self.assertEqual(install_contract.validate_claude_package(pkg), [])


if __name__ == "__main__":
    unittest.main()
