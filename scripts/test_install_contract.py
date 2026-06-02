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
  - the restated exclusion rules match build_release_zip's predicates.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_release_zip  # noqa: E402
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

    def test_exclusion_predicate_matches_build_release_zip(self):
        """The restated exclusion rules agree with build_release_zip's
        per-file/per-dir predicates across the *full* excluded set — this
        slice is about drift-proofing, so sample the real constant rather
        than a hand-picked subset."""
        # The restated dir-name set must equal build_release_zip's, not just
        # overlap on a couple of sampled names.
        self.assertEqual(
            install_contract._EXCLUDED_DIR_NAMES,
            build_release_zip._EXCLUDE_DIR_NAMES,
            "install_contract._EXCLUDED_DIR_NAMES drifted from "
            "build_release_zip._EXCLUDE_DIR_NAMES",
        )
        # ...and the predicate agrees behaviourally for every excluded dir
        # (covers .pytest_cache / .mypy_cache, not just fixtures/__pycache__).
        for d in build_release_zip._EXCLUDE_DIR_NAMES:
            self.assertTrue(
                install_contract.is_excluded_release_path(f"skills/x/{d}/y.txt")
            )
            self.assertTrue(build_release_zip._is_excluded_dir(d))
        # File patterns.
        for f in ("test_foo.py", "x.pyc", ".DS_Store"):
            self.assertTrue(
                install_contract.is_excluded_release_path(f"skills/x/{f}")
            )
            self.assertTrue(build_release_zip._is_excluded_file(f))
        # A normal runtime file is excluded by neither.
        self.assertFalse(
            install_contract.is_excluded_release_path("skills/x/runtime.py")
        )
        self.assertFalse(build_release_zip._is_excluded_file("runtime.py"))


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

    def test_real_hooks_json_references_nine_scripts(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        names = install_contract.parse_hook_script_names(data)
        # Registration source of truth currently lists 9 scripts.
        self.assertEqual(len(names), 9, sorted(names))
        self.assertIn("jig-skill-trace.sh", names)


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
