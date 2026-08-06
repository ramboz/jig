"""
Tests for scripts/scaffold_contract.py — slice 047-02
(scaffold-contract-validator).

Covers the *scaffold-target* install contract (the `.claude/` tree a
scaffolded project gets) as data + pure helpers, the parallel of slice
047-01's plugin/release contract in `install_contract.py`:

  - AC #1: copied-skill helper closure + tier-gated expected skill set +
    stale `${CLAUDE_PLUGIN_ROOT}/skills/...` helper-path detection.
  - AC #2: generated settings.json coherence — jig-managed hook entries
    point at copied scripts that exist, with the scaffold-mode command shape.
  - AC #3: scaffold.json metadata fields (incl. `jig_version`, spec 046-02),
    rejecting stale/missing values.
  - AC #4: local command/link smoke checks with path-specific diagnostics.

Plus the consistency test the restate-with-pointer convention requires
(047-01 precedent): the restated tier tables match scaffold._TIER_SKILLS.

Edge cases (per the slice DoD): a copied skill missing a referenced
helper; a scaffolded SKILL.md with a stale `${CLAUDE_PLUGIN_ROOT}` path; a
settings.json hook pointing at a missing script; scaffold.json missing
`jig_version` / carrying a stale value; a doc with a dangling local link.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scaffold_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixture: a minimal but contract-compliant scaffolded `.claude/` tree
# ---------------------------------------------------------------------------


def _make_scaffold_target(
    tmp: Path,
    *,
    installed_tiers=("tier-0",),
    jig_version="1.9.0",
) -> Path:
    """Build a scaffolded project tree that passes every scaffold-contract
    helper. Tier-0 skills only by default (the conservative install). Each
    user-facing skill gets a SKILL.md that references its own helper with the
    local `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/<helper>.py` shape,
    and the helper file exists. Tests that exercise a failure mode strip or
    corrupt one artifact off this complete fixture."""
    claude = tmp / ".claude"
    skills = claude / "skills"
    skills.mkdir(parents=True)

    # The tier-0 skills + a representative helper file per skill that has one.
    tier0 = scaffold_contract._TIER_SKILLS["tier-0"]
    helper_for = {
        "spec-workflow": "workflow.py",
        "independent-review": "review.py",
        "memory-sync": "memory.py",
        "migrate": "migrate.py",
        "scaffold-init": "scaffold.py",
    }
    for skill in tier0:
        d = skills / f"jig-{skill}"
        d.mkdir()
        helper = helper_for.get(skill)
        if helper:
            (d / helper).write_text("# helper\n")
            body = (
                f"# {skill}\n\n"
                "```bash\n"
                "python3 \"${CLAUDE_PROJECT_DIR}/.claude/skills/"
                f"jig-{skill}/{helper}\" --help\n"
                "```\n"
            )
        else:
            body = f"# {skill}\n\njudgment-only skill, no helper.\n"
        (d / "SKILL.md").write_text(body)

    # agents/ (mirrors verify_install's scaffold-mode requirement)
    agents = claude / "agents"
    agents.mkdir()
    for name in ("implementer", "reviewer", "architect"):
        (agents / f"jig-{name}.md").write_text(f"# {name}\n")

    # hooks/scripts/ — a representative copied hook script the settings
    # entry will reference.
    scripts = claude / "hooks" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "jig-context-check.sh").write_text("#!/bin/bash\n")
    (scripts / "jig-secret-scan.sh").write_text("#!/bin/bash\n")

    # settings.json — jig-managed entries pointing at the copied scripts with
    # the scaffold-mode project-dir command shape.
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "bash ${CLAUDE_PROJECT_DIR}/.claude/"
                                        "hooks/scripts/jig-context-check.sh"
                                    ),
                                }
                            ],
                            "metadata": {"managed_by_jig": True},
                        }
                    ],
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write|MultiEdit",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "bash ${CLAUDE_PROJECT_DIR}/.claude/"
                                        "hooks/scripts/jig-secret-scan.sh"
                                    ),
                                }
                            ],
                            "metadata": {"managed_by_jig": True},
                        }
                    ],
                }
            },
            indent=2,
        )
        + "\n"
    )

    # scaffold.json — the install-state manifest.
    (tmp / "scaffold.json").write_text(
        json.dumps(
            {
                "jig_version": jig_version,
                "timestamp": "2026-06-02T00:00:00Z",
                "project_name": tmp.name,
                "installed_tiers": list(installed_tiers),
                "installed_skills": [
                    f"{tier}/{skill}"
                    for tier in installed_tiers
                    for skill in scaffold_contract._TIER_SKILLS[tier]
                ],
                "scaffold_signals": {
                    "has_llm_agent_files": False,
                    "has_ci": False,
                    "has_tests": False,
                    "is_team": False,
                },
                "hook_profile": "standard",
                "scaffold_mode": "in-repo",
            },
            indent=2,
        )
        + "\n"
    )
    return tmp


# ---------------------------------------------------------------------------
# Consistency: restated tier tables must match scaffold._TIER_SKILLS
# ---------------------------------------------------------------------------


class TierTableConsistencyTests(unittest.TestCase):
    """The scaffold contract derives the expected skill set from the tier
    tables; restate-plus-consistency-test (047-01 precedent) pins the
    restated copy against scaffold.py so the two cannot drift."""

    def test_tier_skills_matches_scaffold(self):
        scaffold_dir = str(REPO_ROOT / "skills" / "scaffold-init")
        sys.path.insert(0, scaffold_dir)
        try:
            import scaffold  # noqa: E402

            self.assertEqual(
                scaffold_contract._TIER_SKILLS,
                scaffold._TIER_SKILLS,
                "scaffold_contract._TIER_SKILLS drifted from "
                "scaffold._TIER_SKILLS — update the restated table",
            )
        finally:
            if scaffold_dir in sys.path:
                sys.path.remove(scaffold_dir)


# ---------------------------------------------------------------------------
# AC #1 — tier-gated expected skill set
# ---------------------------------------------------------------------------


class ExpectedScaffoldSkillsTests(unittest.TestCase):
    def test_tier0_only(self):
        names = scaffold_contract.expected_scaffold_skills(
            {"installed_tiers": ["tier-0"]}
        )
        self.assertIn("jig-spec-workflow", names)
        self.assertIn("jig-contracts", names)
        # A tier-1 skill must NOT be expected when only tier-0 is installed.
        self.assertNotIn("jig-tdd-loop", names)

    def test_tier0_and_tier1(self):
        names = scaffold_contract.expected_scaffold_skills(
            {"installed_tiers": ["tier-0", "tier-1"]}
        )
        self.assertIn("jig-tdd-loop", names)
        self.assertIn("jig-analyze", names)

    def test_falls_back_to_installed_skills_when_no_tiers(self):
        """When `installed_tiers` is absent, derive from `installed_skills`
        (the `<tier>/<skill>` list) so the expectation still tracks the
        manifest."""
        names = scaffold_contract.expected_scaffold_skills(
            {"installed_skills": ["tier-0/spec-workflow", "tier-1/tdd-loop"]}
        )
        self.assertEqual(names, {"jig-spec-workflow", "jig-tdd-loop"})

    def test_unknown_tier_contributes_nothing(self):
        names = scaffold_contract.expected_scaffold_skills(
            {"installed_tiers": ["tier-0", "tier-99"]}
        )
        self.assertIn("jig-spec-workflow", names)


# ---------------------------------------------------------------------------
# AC #1 — copied-skill helper closure + stale plugin-root path detection
# ---------------------------------------------------------------------------


class ScaffoldSkillClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-047-02-skills-"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_fixture_has_no_skill_problems(self):
        _make_scaffold_target(self.tmp)
        self.assertEqual(scaffold_contract.scaffold_skill_problems(self.tmp), [])

    def test_missing_expected_skill_is_named(self):
        _make_scaffold_target(self.tmp)
        import shutil

        shutil.rmtree(self.tmp / ".claude" / "skills" / "jig-spec-workflow")
        problems = scaffold_contract.scaffold_skill_problems(self.tmp)
        joined = " ".join(problems)
        self.assertIn("jig-spec-workflow", joined)
        self.assertIn("SKILL.md", joined)

    def test_missing_referenced_helper_is_named(self):
        """Edge case: a copied skill whose SKILL.md references a helper that
        does not exist locally — the closure check names the offending skill,
        the missing helper, and the rule."""
        _make_scaffold_target(self.tmp)
        # Delete the helper but leave the SKILL.md referencing it.
        (
            self.tmp
            / ".claude"
            / "skills"
            / "jig-spec-workflow"
            / "workflow.py"
        ).unlink()
        problems = scaffold_contract.scaffold_skill_problems(self.tmp)
        joined = " ".join(problems)
        self.assertIn("workflow.py", joined)
        self.assertIn("jig-spec-workflow", joined)

    def test_stale_plugin_root_helper_path_fails(self):
        """Edge case: a scaffolded SKILL.md that still carries a
        `${CLAUDE_PLUGIN_ROOT}/skills/...` helper path (it should have been
        rewritten to a local path per spec 046-01) fails verification."""
        _make_scaffold_target(self.tmp)
        skill_md = (
            self.tmp / ".claude" / "skills" / "jig-spec-workflow" / "SKILL.md"
        )
        skill_md.write_text(
            "# spec-workflow\n\n```bash\n"
            "python3 ${CLAUDE_PLUGIN_ROOT}/skills/spec-workflow/workflow.py "
            "transition\n```\n"
        )
        problems = scaffold_contract.scaffold_skill_problems(self.tmp)
        joined = " ".join(problems)
        self.assertIn("CLAUDE_PLUGIN_ROOT", joined)
        self.assertIn("jig-spec-workflow", joined)

    def test_cross_skill_helper_reference_resolves(self):
        """A SKILL.md may reference a helper that lives under a *different*
        scaffolded skill dir (independent-review → spec-workflow/workflow.py);
        the closure check resolves it across the whole skills tree."""
        _make_scaffold_target(self.tmp)
        skill_md = (
            self.tmp
            / ".claude"
            / "skills"
            / "jig-independent-review"
            / "SKILL.md"
        )
        skill_md.write_text(
            "# independent-review\n\n```bash\n"
            "python3 \"${CLAUDE_PROJECT_DIR}/.claude/skills/"
            "jig-spec-workflow/workflow.py\" transition\n```\n"
        )
        self.assertEqual(scaffold_contract.scaffold_skill_problems(self.tmp), [])

    def test_prose_plugin_root_mention_is_tolerated(self):
        """A bare `${CLAUDE_PLUGIN_ROOT}` prose mention (NOT a
        `.../skills/...` helper path) must not false-fail — real scaffolded
        SKILL.md bodies legitimately describe the plugin's env var."""
        _make_scaffold_target(self.tmp)
        skill_md = (
            self.tmp / ".claude" / "skills" / "jig-migrate" / "SKILL.md"
        )
        skill_md.write_text(
            "# migrate\n\nIn plugin-only mode the machinery lives under "
            "`${CLAUDE_PLUGIN_ROOT}`.\n"
        )
        self.assertEqual(scaffold_contract.scaffold_skill_problems(self.tmp), [])

    def test_skills_dir_missing_fails(self):
        # No .claude/skills at all.
        (self.tmp / "scaffold.json").write_text(
            json.dumps({"installed_tiers": ["tier-0"]})
        )
        problems = scaffold_contract.scaffold_skill_problems(self.tmp)
        self.assertTrue(problems)
        self.assertIn("skills", " ".join(problems).lower())


# ---------------------------------------------------------------------------
# AC #2 — generated settings.json coherence
# ---------------------------------------------------------------------------


class ScaffoldSettingsValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-047-02-settings-"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_fixture_settings_valid(self):
        _make_scaffold_target(self.tmp)
        self.assertEqual(
            scaffold_contract.validate_scaffold_settings(self.tmp), []
        )

    def test_hook_pointing_at_missing_script_fails(self):
        """Edge case: a settings.json hook command points at a script not
        present under .claude/hooks/scripts/ — named with the offending
        script + rule."""
        _make_scaffold_target(self.tmp)
        (
            self.tmp / ".claude" / "hooks" / "scripts" / "jig-secret-scan.sh"
        ).unlink()
        problems = scaffold_contract.validate_scaffold_settings(self.tmp)
        joined = " ".join(problems)
        self.assertIn("jig-secret-scan.sh", joined)
        self.assertTrue(
            "does not exist" in joined or "missing" in joined.lower(),
            joined,
        )

    def test_plugin_root_command_shape_fails_in_scaffold_mode(self):
        """A scaffold-mode hook command must use
        `${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/<name>`, not the plugin
        prefix — a leftover `${CLAUDE_PLUGIN_ROOT}/...` is flagged."""
        _make_scaffold_target(self.tmp)
        settings = self.tmp / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        data["hooks"]["SessionStart"][0]["hooks"][0]["command"] = (
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-context-check.sh"
        )
        settings.write_text(json.dumps(data, indent=2) + "\n")
        problems = scaffold_contract.validate_scaffold_settings(self.tmp)
        joined = " ".join(problems)
        self.assertIn("CLAUDE_PROJECT_DIR", joined)

    def test_bare_command_name_fails(self):
        _make_scaffold_target(self.tmp)
        settings = self.tmp / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        data["hooks"]["SessionStart"][0]["hooks"][0]["command"] = (
            "jig-context-check.sh"
        )
        settings.write_text(json.dumps(data, indent=2) + "\n")
        problems = scaffold_contract.validate_scaffold_settings(self.tmp)
        self.assertTrue(problems)
        self.assertIn("CLAUDE_PROJECT_DIR", " ".join(problems))

    def test_no_jig_managed_entry_fails(self):
        _make_scaffold_target(self.tmp)
        settings = self.tmp / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        for entries in data["hooks"].values():
            for entry in entries:
                entry.pop("metadata", None)
        settings.write_text(json.dumps(data, indent=2) + "\n")
        problems = scaffold_contract.validate_scaffold_settings(self.tmp)
        self.assertTrue(problems)
        self.assertIn("jig", " ".join(problems).lower())

    def test_settings_missing_fails(self):
        _make_scaffold_target(self.tmp)
        (self.tmp / ".claude" / "settings.json").unlink()
        problems = scaffold_contract.validate_scaffold_settings(self.tmp)
        self.assertTrue(problems)
        self.assertIn("settings.json", " ".join(problems))

    def test_invalid_json_fails(self):
        _make_scaffold_target(self.tmp)
        (self.tmp / ".claude" / "settings.json").write_text("not json {")
        problems = scaffold_contract.validate_scaffold_settings(self.tmp)
        self.assertTrue(problems)
        self.assertIn("JSON", " ".join(problems))


# ---------------------------------------------------------------------------
# AC #3 — scaffold.json metadata
# ---------------------------------------------------------------------------


class ScaffoldManifestValidationTests(unittest.TestCase):
    def _valid(self) -> dict:
        return {
            "jig_version": "1.9.0",
            "timestamp": "2026-06-02T00:00:00Z",
            "project_name": "demo",
            "installed_tiers": ["tier-0"],
            "installed_skills": ["tier-0/spec-workflow"],
            "scaffold_mode": "in-repo",
        }

    def test_full_manifest_valid(self):
        self.assertEqual(
            scaffold_contract.validate_scaffold_manifest(self._valid()), []
        )

    def test_missing_jig_version_flagged(self):
        """Edge case: scaffold.json missing `jig_version` (spec 046-02) is
        rejected, naming the field + file."""
        data = self._valid()
        del data["jig_version"]
        problems = scaffold_contract.validate_scaffold_manifest(data)
        joined = " ".join(problems)
        self.assertIn("scaffold.json", joined)
        self.assertIn("jig_version", joined)

    def test_empty_jig_version_flagged(self):
        """Edge case: a stale/empty `jig_version` value is rejected, not just
        an absent key."""
        data = self._valid()
        data["jig_version"] = ""
        problems = scaffold_contract.validate_scaffold_manifest(data)
        self.assertTrue(any("jig_version" in p for p in problems))

    def test_placeholder_jig_version_flagged(self):
        """A manifest that leaked the unrendered `{{JIG_VERSION}}`
        placeholder is a stale value and must be rejected."""
        data = self._valid()
        data["jig_version"] = "{{JIG_VERSION}}"
        problems = scaffold_contract.validate_scaffold_manifest(data)
        self.assertTrue(any("jig_version" in p for p in problems))

    def test_missing_installed_tiers_flagged(self):
        data = self._valid()
        del data["installed_tiers"]
        problems = scaffold_contract.validate_scaffold_manifest(data)
        self.assertTrue(any("installed_tiers" in p for p in problems))

    def test_installed_tiers_must_be_list(self):
        data = self._valid()
        data["installed_tiers"] = "tier-0"
        problems = scaffold_contract.validate_scaffold_manifest(data)
        self.assertTrue(any("installed_tiers" in p for p in problems))

    def test_installed_skills_tier_invariant_violation_flagged(self):
        """ADR-0007 invariant: every installed_skills entry's tier prefix
        must be in installed_tiers. A skill from an uninstalled tier is a
        manifest incoherence."""
        data = self._valid()
        data["installed_skills"] = ["tier-0/spec-workflow", "tier-1/tdd-loop"]
        problems = scaffold_contract.validate_scaffold_manifest(data)
        joined = " ".join(problems)
        self.assertIn("tier-1", joined)

    def test_non_object_rejected(self):
        self.assertTrue(
            scaffold_contract.validate_scaffold_manifest(["not", "obj"])
        )


# ---------------------------------------------------------------------------
# AC #4 — local command/link smoke checks (path-specific diagnostics)
# ---------------------------------------------------------------------------


class ScaffoldDocSmokeCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-047-02-docs-"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_fixture_has_no_doc_problems(self):
        _make_scaffold_target(self.tmp)
        self.assertEqual(scaffold_contract.scaffold_doc_problems(self.tmp), [])

    def test_broken_local_helper_command_is_named(self):
        """Edge case: a doc references a local helper path that doesn't exist
        — the diagnostic names the doc, the missing target, and the rule."""
        _make_scaffold_target(self.tmp)
        doc = self.tmp / "docs" / "workflow.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "Run the helper:\n\n```bash\n"
            "python3 \"${CLAUDE_PROJECT_DIR}/.claude/skills/jig-spec-workflow/"
            "does-not-exist.py\" status-board\n```\n"
        )
        problems = scaffold_contract.scaffold_doc_problems(self.tmp)
        joined = " ".join(problems)
        self.assertIn("workflow.md", joined)
        self.assertIn("does-not-exist.py", joined)

    def test_dangling_local_markdown_link_is_named(self):
        """Edge case: a relative markdown link whose target file is absent is
        flagged with the offending doc + the missing target."""
        _make_scaffold_target(self.tmp)
        doc = self.tmp / "docs" / "guide.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("See [the plan](./missing-plan.md) for details.\n")
        problems = scaffold_contract.scaffold_doc_problems(self.tmp)
        joined = " ".join(problems)
        self.assertIn("guide.md", joined)
        self.assertIn("missing-plan.md", joined)

    def test_resolving_local_link_is_ok(self):
        _make_scaffold_target(self.tmp)
        doc = self.tmp / "docs" / "guide.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        (doc.parent / "target.md").write_text("# target\n")
        doc.write_text("See [target](./target.md).\n")
        self.assertEqual(scaffold_contract.scaffold_doc_problems(self.tmp), [])

    def test_external_link_ignored(self):
        _make_scaffold_target(self.tmp)
        doc = self.tmp / "docs" / "guide.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("See [home](https://example.com/x).\n")
        self.assertEqual(scaffold_contract.scaffold_doc_problems(self.tmp), [])

    def test_anchor_only_link_ignored(self):
        _make_scaffold_target(self.tmp)
        doc = self.tmp / "docs" / "guide.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("Jump to [section](#a-heading).\n")
        self.assertEqual(scaffold_contract.scaffold_doc_problems(self.tmp), [])

    def test_link_anchor_stripped_before_resolution(self):
        """A link target with an #anchor resolves against the file path with
        the anchor stripped."""
        _make_scaffold_target(self.tmp)
        doc = self.tmp / "docs" / "guide.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        (doc.parent / "target.md").write_text("# target\n")
        doc.write_text("See [target](./target.md#heading).\n")
        self.assertEqual(scaffold_contract.scaffold_doc_problems(self.tmp), [])


# ---------------------------------------------------------------------------
# Real-repo integration: scaffolding jig itself yields a coherent target
# ---------------------------------------------------------------------------


class RealScaffoldContractTests(unittest.TestCase):
    """End-to-end: scaffold jig into a temp dir with the real generator, then
    assert every scaffold-contract helper passes — the strongest guard that
    the contract encodes the *intended* scaffold output (spec 046 coordinated
    output), not a hand-built fixture."""

    @classmethod
    def setUpClass(cls):
        import os
        import subprocess

        cls.tmp = Path(tempfile.mkdtemp(prefix="jig-047-02-real-"))
        cls.target = cls.tmp / "demo-project"
        cls.target.mkdir()
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        scaffold_py = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
        # The scaffold-contract helpers (skill closure, settings coherence)
        # validate the in-repo materialized tree; scaffold in-repo explicitly
        # since slice 099-01 / ADR-0041 flipped the default to plugin mode.
        result = subprocess.run(
            [sys.executable, str(scaffold_py), "--in-repo", str(cls.target)],
            capture_output=True,
            text=True,
            env=env,
        )
        cls.scaffold_rc = result.returncode
        cls.scaffold_err = result.stderr

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(
            self.scaffold_rc, 0, f"scaffold failed: {self.scaffold_err}"
        )

    def test_real_scaffold_skill_closure_clean(self):
        problems = scaffold_contract.scaffold_skill_problems(self.target)
        self.assertEqual(problems, [], problems)

    def test_real_scaffold_settings_coherent(self):
        problems = scaffold_contract.validate_scaffold_settings(self.target)
        self.assertEqual(problems, [], problems)

    def test_real_scaffold_manifest_valid(self):
        data = json.loads((self.target / "scaffold.json").read_text())
        problems = scaffold_contract.validate_scaffold_manifest(data)
        self.assertEqual(problems, [], problems)

    def test_real_scaffold_docs_clean(self):
        problems = scaffold_contract.scaffold_doc_problems(self.target)
        self.assertEqual(problems, [], problems)


if __name__ == "__main__":
    unittest.main()
