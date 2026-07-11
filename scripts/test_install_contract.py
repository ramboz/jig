"""
Tests for scripts/install_contract.py — slice 047-01
(plugin-release-contract-validator).

Covers the plugin/release install contract as data + pure helpers:
  - AC #1: manifest field requirements (plugin.json + marketplace.json),
    including relative-source-path enforcement.
  - AC #2: hook-command shape (`bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...`),
    no bare names, and dangling-script-reference detection.
  - AC #3: explicit expected skill set + excluded-path predicate.
  - AC #4: every helper's diagnostics name the offending path/field and rule.

Plus the two consistency tests the restate-with-pointer convention requires:
  - EXPECTED_SKILLS == union of scaffold._TIER_SKILLS.
  - REQUIRED_AGENTS == verify_install._REQUIRED_AGENTS.

As of spec 069-01 this module also OWNS the release-zip file set (include
roots/files + the runtime-scripts allowlist) and a pure `iter_release_files`
enumerator the builder consumes — so the former
`test_exclusion_predicate_matches_build_release_zip` guard (which pinned a
duplicate list in build_release_zip equal to this one) is gone: there is no
second copy left to keep in sync.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import install_contract  # noqa: E402
import verify_install  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Consistency: the restated contract sets must match their sources of truth
# ---------------------------------------------------------------------------


class ContractConsistencyTests(unittest.TestCase):
    """The DoR requires the contract live in one testable structure. These
    tests pin the restated tuples against their single sources of truth so
    they cannot silently drift (the restate-plus-consistency-test convention
    `verify_install._EXPECTED_HOOK_SCRIPTS` already uses)."""

    def test_expected_skills_matches_tier_skills_union(self):
        # scaffold.py lives under skills/scaffold-init/; importing it here
        # (the test, not the stdlib-only module) is fine. Restore sys.path
        # in finally so the insert can't leak into later tests.
        scaffold_dir = str(REPO_ROOT / "skills" / "scaffold-init")
        sys.path.insert(0, scaffold_dir)
        try:
            import scaffold  # noqa: E402

            union = {
                skill
                for skills in scaffold._TIER_SKILLS.values()
                for skill in skills
            }
        finally:
            if scaffold_dir in sys.path:
                sys.path.remove(scaffold_dir)
        self.assertEqual(
            set(install_contract.EXPECTED_SKILLS),
            union,
            "install_contract.EXPECTED_SKILLS drifted from "
            "scaffold._TIER_SKILLS — update the restated tuple",
        )

    def test_required_agents_matches_verify_install(self):
        self.assertEqual(
            install_contract.REQUIRED_AGENTS,
            verify_install._REQUIRED_AGENTS,
        )


# ---------------------------------------------------------------------------
# Spec 069-01 — install_contract now OWNS the release-zip file set (include
# roots/files + the runtime-scripts allowlist) and a pure enumerator the
# builder consumes. These tests pin the include-side data + exercise the
# enumerator against a synthesized source tree (AC #1 / AC #4 entry-set
# stability), without a brittle full-namelist golden constant.
# ---------------------------------------------------------------------------


class ReleaseFileSetTests(unittest.TestCase):
    def test_include_side_data_present(self):
        """The contract owns the include roots, top-level include files, and
        the runtime `scripts/*.py` allowlist as module-level data."""
        self.assertEqual(
            install_contract.RELEASE_INCLUDE_ROOTS,
            (
                ".claude-plugin",
                ".codex-plugin",
                "agents",
                "skills",
                "hooks",
                "templates",
            ),
        )
        self.assertEqual(
            install_contract.RELEASE_INCLUDE_FILES,
            ("README.md", "LICENSE", "jig.png"),
        )
        self.assertEqual(
            install_contract.RELEASE_INCLUDE_SCRIPT_FILES,
            (
                "scripts/verify_install.py",
                "scripts/install_contract.py",
                "scripts/scaffold_contract.py",
                "scripts/spec_lint.py",
            ),
        )

    def test_iter_release_files_is_pure(self):
        """The enumerator must not mutate or create anything on disk — it
        only reads the source tree and yields relative Paths (matches the
        module's stdlib-only, side-effect-free style)."""
        tmp = Path(tempfile.mkdtemp(prefix="jig-069-pure-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        (tmp / "skills" / "demo").mkdir(parents=True)
        (tmp / "skills" / "demo" / "SKILL.md").write_text("# x\n")
        before = sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob("*"))
        list(install_contract.iter_release_files(tmp))
        after = sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob("*"))
        self.assertEqual(before, after, "iter_release_files must not touch disk")


class IterReleaseFilesEntrySetTests(unittest.TestCase):
    """Spec 069-01 (AC #1 / AC #4): the enumerator includes representative
    runtime files + the runtime-scripts allowlist and excludes representative
    junk (test_*.py, __pycache__, *.pyc, fixtures/, .DS_Store) — a
    non-brittle stability check over a synthesized source tree rather than a
    full-namelist golden that would break on every skill edit."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-069-iter-"))
        # An included root with runtime + junk content.
        skill = self.tmp / "skills" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# kept\n")
        (skill / "runtime.py").write_text("# kept\n")
        (skill / "test_demo.py").write_text("# junk\n")
        (skill / "module.pyc").write_text("junk\n")
        (skill / ".DS_Store").write_text("junk\n")
        cache = skill / "__pycache__"
        cache.mkdir()
        (cache / "x.pyc").write_text("junk\n")
        fixtures = skill / "fixtures"
        fixtures.mkdir()
        (fixtures / "case.txt").write_text("junk\n")
        # A non-included top-level dir must be ignored outright.
        docs = self.tmp / "docs"
        docs.mkdir()
        (docs / "x.md").write_text("not shipped\n")
        # Top-level include file present, plus the runtime-scripts allowlist.
        (self.tmp / "README.md").write_text("readme\n")
        scripts = self.tmp / "scripts"
        scripts.mkdir()
        for rel in install_contract.RELEASE_INCLUDE_SCRIPT_FILES:
            (self.tmp / rel).write_text("# runtime module\n")
        # A dev-only script that must NOT ship.
        (scripts / "run_tests.py").write_text("# dev only\n")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rels(self) -> set[str]:
        return {p.as_posix() for p in install_contract.iter_release_files(self.tmp)}

    def test_includes_representative_runtime_files(self):
        rels = self._rels()
        self.assertIn("skills/demo-skill/SKILL.md", rels)
        self.assertIn("skills/demo-skill/runtime.py", rels)
        self.assertIn("README.md", rels)

    def test_yields_runtime_scripts_allowlist(self):
        rels = self._rels()
        for allowed in install_contract.RELEASE_INCLUDE_SCRIPT_FILES:
            self.assertIn(allowed, rels)
        # ...and only the allowlisted scripts, never dev-only tooling.
        self.assertNotIn("scripts/run_tests.py", rels)

    def test_excludes_representative_junk(self):
        rels = self._rels()
        offenders = sorted(
            r for r in rels if install_contract.is_excluded_release_path(r)
        )
        self.assertEqual(
            offenders, [],
            f"iter_release_files yielded excluded path(s): {offenders!r}",
        )
        # Spell out the categories so a regression names the culprit.
        self.assertNotIn("skills/demo-skill/test_demo.py", rels)
        self.assertNotIn("skills/demo-skill/module.pyc", rels)
        self.assertNotIn("skills/demo-skill/.DS_Store", rels)
        self.assertNotIn("skills/demo-skill/__pycache__/x.pyc", rels)
        self.assertFalse(any("fixtures" in Path(r).parts for r in rels))

    def test_ignores_non_included_top_level_dirs(self):
        rels = self._rels()
        self.assertFalse(any(r.startswith("docs/") for r in rels))

    def test_skips_missing_optional_include_file(self):
        # LICENSE is absent in the synthesized tree; the enumerator must not
        # yield it (it yields only present top-level include files).
        rels = self._rels()
        self.assertNotIn("LICENSE", rels)


# ---------------------------------------------------------------------------
# AC #1 — plugin.json manifest requirements
# ---------------------------------------------------------------------------


class PluginManifestValidationTests(unittest.TestCase):
    def _valid(self) -> dict:
        return {"name": "jig", "version": "1.0.0", "description": "d"}

    def test_full_manifest_valid(self):
        self.assertEqual(install_contract.validate_plugin_manifest(self._valid()), [])

    def test_missing_version_flagged_with_field_and_file(self):
        data = self._valid()
        del data["version"]
        problems = install_contract.validate_plugin_manifest(data)
        self.assertTrue(problems)
        joined = " ".join(problems)
        self.assertIn("plugin.json", joined)
        self.assertIn("version", joined)

    def test_missing_description_flagged(self):
        data = self._valid()
        del data["description"]
        problems = install_contract.validate_plugin_manifest(data)
        self.assertTrue(any("description" in p for p in problems))

    def test_empty_name_flagged(self):
        data = self._valid()
        data["name"] = ""
        problems = install_contract.validate_plugin_manifest(data)
        self.assertTrue(any("name" in p for p in problems))

    def test_non_object_rejected(self):
        self.assertTrue(install_contract.validate_plugin_manifest(["not", "obj"]))


# ---------------------------------------------------------------------------
# AC #1 / slice 033-06 — .codex-plugin/plugin.json manifest requirements
# ---------------------------------------------------------------------------


class CodexPluginManifestValidationTests(unittest.TestCase):
    def _valid(self) -> dict:
        return {
            "name": "jig",
            "version": "1.0.0",
            "description": "d",
            "author": {"name": "ramboz"},
            "skills": "./skills/",
            "interface": {
                "displayName": "jig",
                "shortDescription": "d",
                "longDescription": "d",
                "developerName": "ramboz",
                "category": "Engineering",
                "capabilities": ["Interactive", "Read", "Write"],
                "defaultPrompt": ["Set up this project"],
            },
        }

    def test_full_manifest_valid(self):
        self.assertEqual(
            install_contract.validate_codex_plugin_manifest(self._valid()), []
        )

    def test_missing_interface_field_flagged_with_codex_path(self):
        data = self._valid()
        del data["interface"]["shortDescription"]
        problems = install_contract.validate_codex_plugin_manifest(data)
        self.assertTrue(problems)
        joined = " ".join(problems)
        self.assertIn(".codex-plugin/plugin.json", joined)
        self.assertIn("shortDescription", joined)

    def test_bad_skills_pointer_rejected(self):
        data = self._valid()
        data["skills"] = "./codex-skills/"
        problems = install_contract.validate_codex_plugin_manifest(data)
        self.assertTrue(any("./skills/" in p for p in problems), problems)

    def test_missing_author_name_flagged(self):
        data = self._valid()
        data["author"] = {}
        problems = install_contract.validate_codex_plugin_manifest(data)
        self.assertTrue(any("author.name" in p for p in problems), problems)

    def test_default_prompt_is_capped_at_three(self):
        data = self._valid()
        data["interface"]["defaultPrompt"] = ["a", "b", "c", "d"]
        problems = install_contract.validate_codex_plugin_manifest(data)
        self.assertTrue(any("at most 3" in p for p in problems), problems)

    def test_non_object_rejected(self):
        self.assertTrue(
            install_contract.validate_codex_plugin_manifest(["not", "obj"])
        )


# ---------------------------------------------------------------------------
# AC #1 — marketplace.json manifest requirements + relative source path
# ---------------------------------------------------------------------------


class MarketplaceManifestValidationTests(unittest.TestCase):
    def _valid(self) -> dict:
        return {
            "name": "jig",
            "owner": {"name": "ramboz"},
            "plugins": [
                {
                    "name": "jig",
                    "source": {"source": "git-subdir", "url": "u", "path": "."},
                    "description": "d",
                }
            ],
        }

    def test_full_manifest_valid(self):
        self.assertEqual(
            install_contract.validate_marketplace_manifest(self._valid()), []
        )

    def test_string_relative_source_valid(self):
        data = self._valid()
        data["plugins"][0]["source"] = "./"
        self.assertEqual(
            install_contract.validate_marketplace_manifest(data), []
        )

    def test_missing_owner_name_flagged(self):
        data = self._valid()
        data["owner"] = {}
        problems = install_contract.validate_marketplace_manifest(data)
        self.assertTrue(any("owner.name" in p for p in problems))

    def test_empty_plugins_flagged(self):
        data = self._valid()
        data["plugins"] = []
        problems = install_contract.validate_marketplace_manifest(data)
        self.assertTrue(any("plugins" in p for p in problems))

    def test_plugin_entry_missing_description_flagged(self):
        data = self._valid()
        del data["plugins"][0]["description"]
        problems = install_contract.validate_marketplace_manifest(data)
        self.assertTrue(
            any("plugins[0]" in p and "description" in p for p in problems)
        )

    def test_plugin_entry_missing_name_flagged(self):
        data = self._valid()
        del data["plugins"][0]["name"]
        problems = install_contract.validate_marketplace_manifest(data)
        self.assertTrue(
            any("plugins[0]" in p and "name" in p for p in problems)
        )

    def test_absolute_object_source_path_rejected(self):
        data = self._valid()
        data["plugins"][0]["source"]["path"] = "/abs"
        problems = install_contract.validate_marketplace_manifest(data)
        self.assertTrue(
            any("plugins[0]" in p and "not relative" in p for p in problems),
            problems,
        )

    def test_absolute_string_source_rejected(self):
        data = self._valid()
        data["plugins"][0]["source"] = "/abs/path"
        problems = install_contract.validate_marketplace_manifest(data)
        self.assertTrue(any("absolute" in p for p in problems), problems)

    def test_dotdot_escaping_object_source_path_rejected(self):
        data = self._valid()
        data["plugins"][0]["source"]["path"] = "../escape"
        problems = install_contract.validate_marketplace_manifest(data)
        self.assertTrue(
            any("plugins[0]" in p and "escapes" in p for p in problems),
            problems,
        )

    def test_object_source_without_path_is_ok(self):
        data = self._valid()
        data["plugins"][0]["source"] = {"source": "github", "repo": "ramboz/jig"}
        self.assertEqual(
            install_contract.validate_marketplace_manifest(data), []
        )


# ---------------------------------------------------------------------------
# AC #2 — hook command shape + script existence
# ---------------------------------------------------------------------------


class HookValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-047-hooks-"))
        self.scripts = self.tmp / "hooks" / "scripts"
        self.scripts.mkdir(parents=True)
        (self.scripts / "jig-a.sh").write_text("#!/bin/bash\n")
        (self.scripts / "jig-b.sh").write_text("#!/bin/bash\n")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _hooks(self, *commands: str) -> dict:
        return {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Task",
                        "hooks": [
                            {"type": "command", "command": c} for c in commands
                        ],
                    }
                ]
            }
        }

    def test_well_formed_commands_validate(self):
        data = self._hooks(
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-a.sh",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-b.sh",
        )
        self.assertEqual(install_contract.validate_hooks(data, self.scripts), [])

    def test_bare_script_name_flagged(self):
        data = self._hooks("jig-a.sh")
        problems = install_contract.validate_hooks(data, self.scripts)
        self.assertTrue(problems)
        joined = " ".join(problems)
        self.assertIn("jig-a.sh", joined)
        self.assertIn("CLAUDE_PLUGIN_ROOT", joined)

    def test_wrong_env_var_flagged(self):
        data = self._hooks(
            "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/jig-a.sh"
        )
        problems = install_contract.validate_hooks(data, self.scripts)
        self.assertTrue(problems)
        self.assertIn("CLAUDE_PLUGIN_ROOT", " ".join(problems))

    def test_dangling_script_reference_flagged(self):
        data = self._hooks(
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-missing.sh"
        )
        problems = install_contract.validate_hooks(data, self.scripts)
        self.assertTrue(problems)
        joined = " ".join(problems)
        self.assertIn("jig-missing.sh", joined)
        self.assertIn("does not exist", joined)

    def test_missing_hooks_object_flagged(self):
        problems = install_contract.validate_hooks({}, self.scripts)
        self.assertTrue(problems)
        self.assertIn("hooks", " ".join(problems))

    def test_parse_hook_script_names_collects_basenames(self):
        data = self._hooks(
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-a.sh",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-b.sh",
        )
        self.assertEqual(
            install_contract.parse_hook_script_names(data),
            {"jig-a.sh", "jig-b.sh"},
        )


# ---------------------------------------------------------------------------
# AC #2 / drift fix — the real hooks.json validates against the real scripts
# ---------------------------------------------------------------------------


class RealHooksJsonTests(unittest.TestCase):
    def test_real_hooks_json_validates(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        problems = install_contract.validate_hooks(
            data, REPO_ROOT / "hooks" / "scripts"
        )
        self.assertEqual(problems, [], problems)

    def test_real_hooks_json_references_thirteen_scripts(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        names = install_contract.parse_hook_script_names(data)
        # Registration source of truth currently lists 13 scripts
        # (jig-claim-check.sh added on Stop for the refinement-todo
        # "memory-recall verification" mitigation).
        self.assertEqual(len(names), 13, sorted(names))
        self.assertIn("jig-skill-trace.sh", names)
        self.assertIn("jig-semantic-index.sh", names)
        self.assertIn("jig-decision-capture.sh", names)
        self.assertIn("jig-decision-inflight.sh", names)
        self.assertIn("jig-claim-check.sh", names)


# ---------------------------------------------------------------------------
# AC #3 — excluded-path predicate
# ---------------------------------------------------------------------------


class ExcludedPathPredicateTests(unittest.TestCase):
    def test_fixtures_at_any_depth(self):
        self.assertTrue(
            install_contract.is_excluded_release_path("skills/x/fixtures/c.txt")
        )
        self.assertTrue(
            install_contract.is_excluded_release_path(
                "skills/x/sub/deeper/fixtures/n.txt"
            )
        )

    def test_test_py_basename(self):
        self.assertTrue(
            install_contract.is_excluded_release_path("scripts/test_x.py")
        )

    def test_pyc_and_pycache_and_dsstore(self):
        self.assertTrue(install_contract.is_excluded_release_path("a/b.pyc"))
        self.assertTrue(
            install_contract.is_excluded_release_path("a/__pycache__/b.pyc")
        )
        self.assertTrue(install_contract.is_excluded_release_path("a/.DS_Store"))

    def test_runtime_file_not_excluded(self):
        self.assertFalse(
            install_contract.is_excluded_release_path("skills/x/SKILL.md")
        )
        self.assertFalse(
            install_contract.is_excluded_release_path("hooks/scripts/jig-a.sh")
        )


# ---------------------------------------------------------------------------
# AC #3 / #4 — skill / agent presence helpers
# ---------------------------------------------------------------------------


class PresenceHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-047-presence-"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_all_skills(self):
        for skill in install_contract.EXPECTED_SKILLS:
            d = self.tmp / "skills" / skill
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("# x\n")

    def _seed_all_agents(self):
        agents = self.tmp / "agents"
        agents.mkdir(parents=True)
        for agent in install_contract.REQUIRED_AGENTS:
            (agents / f"{agent}.md").write_text("# x\n")

    def test_missing_skills_empty_when_all_present(self):
        self._seed_all_skills()
        self.assertEqual(install_contract.missing_skills(self.tmp), [])

    def test_missing_skill_named_with_rule(self):
        self._seed_all_skills()
        import shutil

        shutil.rmtree(self.tmp / "skills" / "analyze")
        problems = install_contract.missing_skills(self.tmp)
        self.assertTrue(problems)
        joined = " ".join(problems)
        self.assertIn("skills/analyze", joined)
        self.assertIn("SKILL.md", joined)

    def test_missing_agents_empty_when_all_present(self):
        self._seed_all_agents()
        self.assertEqual(install_contract.missing_agents(self.tmp), [])

    def test_missing_agent_named(self):
        self._seed_all_agents()
        (self.tmp / "agents" / "reviewer.md").unlink()
        problems = install_contract.missing_agents(self.tmp)
        self.assertTrue(any("agents/reviewer.md" in p for p in problems))


# ---------------------------------------------------------------------------
# Real-repo integration: the live plugin satisfies its own contract
# ---------------------------------------------------------------------------


class RealRepoContractTests(unittest.TestCase):
    def test_real_plugin_manifest_valid(self):
        data = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
        )
        self.assertEqual(install_contract.validate_plugin_manifest(data), [])

    def test_real_codex_plugin_manifest_valid(self):
        data = json.loads(
            (REPO_ROOT / ".codex-plugin" / "plugin.json").read_text()
        )
        self.assertEqual(
            install_contract.validate_codex_plugin_manifest(data), []
        )

    def test_real_marketplace_manifest_valid(self):
        data = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text()
        )
        self.assertEqual(
            install_contract.validate_marketplace_manifest(data), []
        )

    def test_real_repo_has_all_expected_skills(self):
        self.assertEqual(install_contract.missing_skills(REPO_ROOT), [])

    def test_real_repo_has_all_required_agents(self):
        self.assertEqual(install_contract.missing_agents(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
