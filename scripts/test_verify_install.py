"""
Tests for scripts/verify_install.py — slice 011-01 (local-plugin-install).

Covers AC #1 (marketplace descriptor), AC #4 headless mode, AC #5
(integration into test suite), AC #7 (architect probe is check-only),
and the probe-prompt generator that the live runbook in CONTRIBUTING.md
calls into.
"""

import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import install_contract  # noqa: E402
import scaffold_contract  # noqa: E402  — slice 047-02 scaffold contract
import verify_install  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _make_fake_plugin_root(tmpdir: Path) -> Path:
    """Build a full-contract plugin root that passes every plugin-mode check.

    Updated for slice 047-01: the plugin-mode checks now assert the *full*
    install contract (every expected skill, the hooks.json command shape +
    script existence, full manifest fields), so the shared fixture builder
    must produce a complete, contract-compliant tree. Tests that exercise a
    specific failure mode strip the relevant artifact off this complete
    fixture."""
    (tmpdir / ".claude-plugin").mkdir(parents=True)
    (tmpdir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(
            {"name": "jig", "version": "0.1.0", "description": "test plugin"}
        )
    )
    (tmpdir / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "jig",
                "owner": {"name": "ramboz"},
                "plugins": [
                    {
                        "name": "jig",
                        "source": {
                            "source": "git-subdir",
                            "url": "https://example/jig.git",
                            "path": ".",
                        },
                        "description": "test plugin",
                    }
                ],
            }
        )
    )
    (tmpdir / "agents").mkdir()
    for name in install_contract.REQUIRED_AGENTS:
        (tmpdir / "agents" / f"{name}.md").write_text(f"# {name}\n")
    skills = tmpdir / "skills"
    skills.mkdir()
    for skill in install_contract.EXPECTED_SKILLS:
        (skills / skill).mkdir()
        (skills / skill / "SKILL.md").write_text(f"# {skill}\n")
    # hooks.json + the scripts it references (one well-formed entry per
    # registered script), so the hook-contract check passes on the fixture.
    hooks_scripts = tmpdir / "hooks" / "scripts"
    hooks_scripts.mkdir(parents=True)
    hook_entries = []
    for script in verify_install._EXPECTED_HOOK_SCRIPTS:
        (hooks_scripts / script).write_text("#!/bin/bash\n")
        hook_entries.append(
            {
                "type": "command",
                "command": (
                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/" + script
                ),
            }
        )
    (tmpdir / "hooks" / "hooks.json").write_text(
        json.dumps(
            {"hooks": {"PreToolUse": [{"matcher": "Task", "hooks": hook_entries}]}}
        )
    )
    return tmpdir


# Source of truth: scaffold.py `_PERMISSIONS_DENY_DEFAULTS` (slice 052-03)
# and `_GITIGNORE_SECRET_PATTERNS` / `_GITIGNORE_BLOCK_BEGIN` (slice 052-02).
# These literals mirror the AC1-named representative subset the floor checks
# assert; verify_install.py is stdlib-only and cannot import scaffold, so the
# fixtures hardcode the same markers the production checks do.
_FLOOR_DENY_GLOBS = (
    "Bash(git push --force*)",
    "Bash(git reset --hard*)",
    "Bash(rm -rf*)",
)
_FLOOR_GITIGNORE_MARKER = "# >>> jig secret-ignore >>>"


def _make_fake_scaffold_root(tmpdir: Path) -> Path:
    """Build a minimum-shape scaffolded project that passes every
    scaffold-mode check (slice 016-03 AC #4, extended by slice 052-04 with
    the security floor: secret-scan registration, `permissions.deny`, and
    the `.gitignore` secret block; extended by slice 047-02 with the tier-0
    skill set, a valid `scaffold.json`, and helper-free SKILL.md bodies so
    the strengthened scaffold-contract checks — skill closure, settings
    coherence, manifest, docs — all pass on this fixture)."""
    claude = tmpdir / ".claude"
    # skills/ — the full tier-0 set (slice 047-02 strengthened the skills
    # check to assert the tier-gated expected set declared in scaffold.json,
    # so the fixture must carry every tier-0 skill, not just one). Each
    # SKILL.md is helper-free local prose (no `${CLAUDE_PROJECT_DIR}` helper
    # refs to resolve, no stale `${CLAUDE_PLUGIN_ROOT}/skills/` path).
    skills = claude / "skills"
    skills.mkdir(parents=True)
    _FIXTURE_TIER0_SKILLS = (
        "scaffold-init",
        "memory-sync",
        "spec-workflow",
        "independent-review",
        "migrate",
        "vision-elicitation",
        "contracts",
    )
    for skill in _FIXTURE_TIER0_SKILLS:
        (skills / f"jig-{skill}").mkdir()
        (skills / f"jig-{skill}" / "SKILL.md").write_text(f"# {skill}\n")
    # agents/
    agents = claude / "agents"
    agents.mkdir()
    for name in ("implementer", "reviewer", "architect"):
        (agents / f"jig-{name}.md").write_text(f"# {name}\n")
    # hooks/scripts/
    scripts = claude / "hooks" / "scripts"
    scripts.mkdir(parents=True)
    # Mirrors the full set scaffold.py copies (glob `jig-*.sh`) — kept equal
    # to verify_install._EXPECTED_HOOK_SCRIPTS, which slice 047-01 corrected
    # to include jig-skill-trace.sh.
    for name in verify_install._EXPECTED_HOOK_SCRIPTS:
        s = scripts / name
        s.write_text("#!/bin/bash\n")
        s.chmod(0o755)
    # settings.json with a jig-managed SessionStart entry PLUS the security
    # floor: a jig-managed Edit|Write|MultiEdit secret-scan registration and
    # the conservative permissions.deny guardrails (slice 052-04).
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
                                        "bash "
                                        "${CLAUDE_PROJECT_DIR}/.claude/"
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
                                        "bash "
                                        "${CLAUDE_PROJECT_DIR}/.claude/"
                                        "hooks/scripts/jig-secret-scan.sh"
                                    ),
                                }
                            ],
                            "metadata": {"managed_by_jig": True},
                        }
                    ],
                },
                "permissions": {"deny": list(_FLOOR_DENY_GLOBS)},
            },
            indent=2,
        )
        + "\n"
    )
    # .gitignore secret floor (slice 052-02).
    (tmpdir / ".gitignore").write_text(
        _FLOOR_GITIGNORE_MARKER + "\n.env\n*.pem\n# <<< jig secret-ignore <<<\n"
    )
    # scaffold.json install-state manifest (slice 047-02 manifest check).
    # Declares the tier-0 set the skills/ dir above carries, with the
    # `<tier>/<skill>` installed_skills derived from it (ADR-0007 invariant).
    (tmpdir / "scaffold.json").write_text(
        json.dumps(
            {
                "jig_version": "1.9.0",
                "timestamp": "2026-06-02T00:00:00Z",
                "project_name": tmpdir.name,
                "installed_tiers": ["tier-0"],
                "installed_skills": [
                    f"tier-0/{skill}" for skill in _FIXTURE_TIER0_SKILLS
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
    return tmpdir


def _make_full_floor_scaffold_root(tmpdir: Path) -> Path:
    """Alias for `_make_fake_scaffold_root` — the base fixture now includes
    the full security floor (slice 052-04). Kept as a descriptively-named
    helper for the floor presence/absence tests, which strip individual
    artifacts off this complete fixture to drive each absence case."""
    return _make_fake_scaffold_root(tmpdir)


# --------------------------------------------------------------------------
# AC #1 — marketplace descriptor checked in (against jig's real repo)
# --------------------------------------------------------------------------


class MarketplaceDescriptorIntegrationTests(unittest.TestCase):
    """Asserts the descriptor checked in at jig's repo root is well-shaped."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent

    def test_marketplace_descriptor_exists(self):
        self.assertTrue(
            (self.repo_root / ".claude-plugin" / "marketplace.json").is_file(),
            "marketplace descriptor missing at .claude-plugin/marketplace.json",
        )

    def test_marketplace_descriptor_valid_json(self):
        text = (self.repo_root / ".claude-plugin" / "marketplace.json").read_text()
        json.loads(text)  # raises on invalid

    def test_marketplace_descriptor_lists_jig_plugin(self):
        data = json.loads(
            (self.repo_root / ".claude-plugin" / "marketplace.json").read_text()
        )
        plugins = data.get("plugins") or []
        names = [p.get("name") for p in plugins if isinstance(p, dict)]
        self.assertIn("jig", names, f"marketplace.json must list 'jig'; got {names!r}")

    def test_marketplace_descriptor_jig_source_resolves(self):
        data = json.loads(
            (self.repo_root / ".claude-plugin" / "marketplace.json").read_text()
        )
        jig_entry = next(p for p in data["plugins"] if p.get("name") == "jig")
        source = jig_entry.get("source")
        self.assertIsNotNone(source, "jig plugin entry missing source")
        # Source must be a git-subdir object (the CLI rejects bare string paths).
        self.assertIsInstance(source, dict, "source must be an object, not a bare path string")
        self.assertEqual(source.get("source"), "git-subdir")
        self.assertIn("url", source, "git-subdir source must include 'url'")
        self.assertIn("path", source, "git-subdir source must include 'path'")
        # The path within the repo should resolve to a directory with plugin.json.
        path = source.get("path", ".")
        resolved = (self.repo_root / path).resolve()
        self.assertTrue(
            (resolved / ".claude-plugin" / "plugin.json").is_file()
            or (resolved / "plugin.json").is_file(),
            f"source path {path!r} doesn't resolve to a plugin root with plugin.json",
        )


# --------------------------------------------------------------------------
# AC #4 — headless mode
# --------------------------------------------------------------------------


class HeadlessChecksOnFixtureTests(unittest.TestCase):
    """Unit-test the individual checks against synthesized fake plugin roots."""

    def test_full_fixture_passes_all_checks(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            results = verify_install.run_all_checks(root)
            self.assertTrue(
                all(passed for passed, _ in results),
                f"all checks should pass on a full fixture; got {results!r}",
            )

    def test_missing_marketplace_descriptor_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            (root / ".claude-plugin" / "marketplace.json").unlink()
            passed, msg = verify_install.check_marketplace_descriptor(root)
            self.assertFalse(passed)
            self.assertIn("marketplace.json", msg)

    def test_invalid_plugin_json_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            (root / ".claude-plugin" / "plugin.json").write_text("not json")
            passed, msg = verify_install.check_plugin_manifest(root)
            self.assertFalse(passed)
            self.assertIn("plugin.json", msg)

    def test_missing_agent_file_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            (root / "agents" / "reviewer.md").unlink()
            passed, msg = verify_install.check_agents_present(root)
            self.assertFalse(passed)
            self.assertIn("reviewer", msg)

    def test_missing_skills_dir_fails(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            shutil.rmtree(root / "skills")
            passed, msg = verify_install.check_active_skills_present(root)
            self.assertFalse(passed)
            self.assertIn("skill", msg.lower())


class HeadlessRunnerTests(unittest.TestCase):
    """End-to-end behavior of run_headless()."""

    def test_run_headless_exit_zero_on_full_fixture(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            buf = io.StringIO()
            rc = verify_install.run_headless(root, out=buf)
            self.assertEqual(rc, 0, msg=f"output was:\n{buf.getvalue()}")

    def test_run_headless_exit_one_when_a_check_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            (root / "agents" / "reviewer.md").unlink()
            buf = io.StringIO()
            rc = verify_install.run_headless(root, out=buf)
            self.assertEqual(rc, 1)

    def test_run_headless_exit_two_when_plugin_not_installed(self):
        """No plugin.json + no marketplace.json + no agents dir — clear
        actionable error per AC #5."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            buf = io.StringIO()
            rc = verify_install.run_headless(root, out=buf)
            self.assertEqual(rc, 2)
            self.assertIn("plugin not installed", buf.getvalue().lower())

    def test_run_headless_output_has_one_line_per_check_plus_summary(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            buf = io.StringIO()
            verify_install.run_headless(root, out=buf)
            lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
            # 5 checks (marketplace / manifest / agents / skills / hooks) +
            # 1 summary line (slice 047-01 added the hook-contract check).
            self.assertGreaterEqual(len(lines), 6)
            self.assertTrue(
                any("summary" in ln.lower() or "passed" in ln.lower() for ln in lines),
                f"expected a summary line; got:\n{buf.getvalue()}",
            )


# --------------------------------------------------------------------------
# Slice 047-01 — plugin-mode install-contract checks
# --------------------------------------------------------------------------


class HookScriptDriftConsistencyTests(unittest.TestCase):
    """Slice 047-01 item 5 (drift fix). `_EXPECTED_HOOK_SCRIPTS` is a
    restated constant; pin it equal to the set hooks.json actually
    registers so it cannot silently drift (it was missing
    `jig-skill-trace.sh` before this slice)."""

    def test_expected_hook_scripts_matches_hooks_json(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        registered = install_contract.parse_hook_script_names(data)
        self.assertEqual(
            set(verify_install._EXPECTED_HOOK_SCRIPTS),
            registered,
            "verify_install._EXPECTED_HOOK_SCRIPTS drifted from the set "
            "hooks.json registers — update the restated constant",
        )

    def test_skill_trace_hook_is_listed(self):
        self.assertIn(
            "jig-skill-trace.sh", verify_install._EXPECTED_HOOK_SCRIPTS
        )


class PluginModeSkillContractTests(unittest.TestCase):
    """AC #3 — plugin-mode skill check asserts the FULL expected skill set,
    not just 'at least one'. AC #4 — a missing skill is named."""

    def test_full_skill_set_passes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            passed, msg = verify_install.check_active_skills_present(root)
            self.assertTrue(passed, msg)

    def test_missing_expected_skill_fails_and_is_named(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            # Remove one expected skill from the otherwise-complete fixture.
            shutil.rmtree(root / "skills" / "analyze")
            passed, msg = verify_install.check_active_skills_present(root)
            self.assertFalse(passed)
            self.assertIn("analyze", msg)
            self.assertIn("SKILL.md", msg)

    def test_real_repo_has_full_skill_set(self):
        passed, msg = verify_install.check_active_skills_present(REPO_ROOT)
        self.assertTrue(passed, msg)


class PluginModeHookContractTests(unittest.TestCase):
    """AC #2 — plugin mode now validates hooks.json command shape + script
    existence (it checked NO hooks before this slice)."""

    def test_real_repo_hook_contract_passes(self):
        passed, msg = verify_install.check_hook_contract(REPO_ROOT)
        self.assertTrue(passed, msg)

    def test_hook_check_in_plugin_check_list(self):
        names = [name for name, _ in verify_install._CHECKS]
        self.assertIn("hooks", names)

    def test_bare_hook_command_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            scripts = root / "hooks" / "scripts"
            (scripts / "jig-x.sh").write_text("#!/bin/bash\n")
            # Overwrite the well-formed fixture hooks.json with a bare-name
            # entry (the failure under test).
            (root / "hooks" / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Task",
                                    "hooks": [
                                        {"type": "command", "command": "jig-x.sh"}
                                    ],
                                }
                            ]
                        }
                    }
                )
            )
            passed, msg = verify_install.check_hook_contract(root)
            self.assertFalse(passed)
            self.assertIn("jig-x.sh", msg)
            self.assertIn("CLAUDE_PLUGIN_ROOT", msg)

    def test_dangling_hook_script_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            # Reference a script that was never written into hooks/scripts/.
            (root / "hooks" / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Task",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": (
                                                "bash ${CLAUDE_PLUGIN_ROOT}"
                                                "/hooks/scripts/jig-missing.sh"
                                            ),
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                )
            )
            passed, msg = verify_install.check_hook_contract(root)
            self.assertFalse(passed)
            self.assertIn("jig-missing.sh", msg)

    def test_missing_hooks_json_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            # Remove the fixture's hooks.json so the check has none to read.
            (root / "hooks" / "hooks.json").unlink()
            passed, msg = verify_install.check_hook_contract(root)
            self.assertFalse(passed)
            self.assertIn("hooks.json", msg)


# --------------------------------------------------------------------------
# Slice 016-03 AC #4 — scaffold-mode checks (--mode scaffold)
# --------------------------------------------------------------------------


class ScaffoldModeChecksTests(unittest.TestCase):
    """Each of the four scaffold-mode checks fires on a synthetic scaffold
    tree, and each fails when its target artifact is missing."""

    def test_scaffold_full_fixture_passes_all_checks(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            results = verify_install.run_all_scaffold_checks(project)
            self.assertTrue(
                all(passed for passed, _ in results),
                f"scaffold-mode checks should pass on a full fixture; "
                f"got {results!r}",
            )

    def test_scaffold_skills_check_fails_when_missing(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            shutil.rmtree(project / ".claude" / "skills")
            passed, msg = verify_install.check_scaffold_skills_present(project)
            self.assertFalse(passed)
            self.assertIn("skill", msg.lower())

    def test_scaffold_agents_check_fails_when_missing(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            shutil.rmtree(project / ".claude" / "agents")
            passed, msg = verify_install.check_scaffold_agents_present(project)
            self.assertFalse(passed)
            self.assertIn("agent", msg.lower())

    def test_scaffold_hook_scripts_check_fails_when_missing(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            shutil.rmtree(project / ".claude" / "hooks")
            passed, msg = verify_install.check_scaffold_hook_scripts_present(
                project
            )
            self.assertFalse(passed)
            self.assertIn("hook", msg.lower())

    def test_scaffold_settings_check_fails_when_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            (project / ".claude" / "settings.json").unlink()
            passed, msg = verify_install.check_scaffold_settings_registration(
                project
            )
            self.assertFalse(passed)
            self.assertIn("settings", msg.lower())

    def test_scaffold_settings_check_fails_without_jig_marker(self):
        """A settings.json missing any managed_by_jig marker is not a
        valid scaffold-mode registration."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            (project / ".claude" / "settings.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": (
                                                "bash ./user-hook.sh"
                                            ),
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                )
            )
            passed, msg = verify_install.check_scaffold_settings_registration(
                project
            )
            self.assertFalse(passed)
            self.assertIn("jig", msg.lower())

    def test_run_headless_scaffold_returns_exit_zero(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            buf = io.StringIO()
            rc = verify_install.run_headless_scaffold(project, out=buf)
            self.assertEqual(rc, 0, msg=f"output was:\n{buf.getvalue()}")

    def test_run_headless_scaffold_returns_two_when_not_scaffolded(self):
        """A project with no .claude/ at all is `not scaffolded` — exit 2."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            buf = io.StringIO()
            rc = verify_install.run_headless_scaffold(project, out=buf)
            self.assertEqual(rc, 2)
            self.assertIn(
                "not scaffolded", buf.getvalue().lower(),
                f"expected 'not scaffolded' message; got:\n{buf.getvalue()}",
            )


# --------------------------------------------------------------------------
# Slice 047-02 — scaffold-contract checks wired into scaffold mode
# --------------------------------------------------------------------------


class ScaffoldContractWiringTests(unittest.TestCase):
    """Slice 047-02 strengthens the scaffold-mode checks and adds two new
    ones, all delegating to `scaffold_contract`. These tests confirm the
    checks are wired into `_SCAFFOLD_CHECKS` (so they run via the
    scaffold-mode verifier, AC #4) and that each strengthened/new check
    fails when its target contract is violated — not just 'something exists'.
    Each driven off the shared `_make_fake_scaffold_root` fixture (now a full
    tier-0 scaffold with a valid scaffold.json)."""

    def test_new_checks_registered_in_scaffold_check_list(self):
        names = [name for name, _ in verify_install._SCAFFOLD_CHECKS]
        for expected in ("skill-closure", "manifest", "docs"):
            self.assertIn(expected, names, names)

    def test_full_fixture_passes_all_scaffold_checks(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            results = verify_install.run_all_scaffold_checks(project)
            self.assertTrue(
                all(passed for passed, _ in results),
                f"all scaffold checks should pass on the full fixture; "
                f"got {results!r}",
            )

    # ---- AC #1: helper closure wired into the skills/skill-closure check ----
    def test_skill_closure_check_fails_on_dangling_helper(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            # Add a SKILL.md referencing a local helper that doesn't exist.
            skill_md = (
                project / ".claude" / "skills" / "jig-spec-workflow"
                / "SKILL.md"
            )
            skill_md.write_text(
                "# spec-workflow\n\n```bash\n"
                "python3 \"${CLAUDE_PROJECT_DIR}/.claude/skills/"
                "jig-spec-workflow/workflow.py\" new x\n```\n"
            )  # workflow.py NOT created in the fixture
            passed, msg = verify_install.check_scaffold_skill_closure(project)
            self.assertFalse(passed)
            self.assertIn("workflow.py", msg)

    def test_skill_closure_check_fails_on_stale_plugin_root_path(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            skill_md = (
                project / ".claude" / "skills" / "jig-migrate" / "SKILL.md"
            )
            skill_md.write_text(
                "# migrate\n\n```bash\n"
                "python3 ${CLAUDE_PLUGIN_ROOT}/skills/migrate/migrate.py "
                "report .\n```\n"
            )
            passed, msg = verify_install.check_scaffold_skill_closure(project)
            self.assertFalse(passed)
            self.assertIn("CLAUDE_PLUGIN_ROOT", msg)

    # ---- AC #2: settings coherence (strengthened) ----
    def test_settings_check_fails_on_dangling_hook_script(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            # Remove a script a settings hook command references.
            (
                project / ".claude" / "hooks" / "scripts"
                / "jig-secret-scan.sh"
            ).unlink()
            passed, msg = (
                verify_install.check_scaffold_settings_registration(project)
            )
            self.assertFalse(passed)
            self.assertIn("jig-secret-scan.sh", msg)

    # ---- AC #3: manifest check wired in ----
    def test_manifest_check_fails_when_jig_version_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            manifest = project / "scaffold.json"
            data = json.loads(manifest.read_text())
            del data["jig_version"]
            manifest.write_text(json.dumps(data, indent=2) + "\n")
            passed, msg = verify_install.check_scaffold_manifest(project)
            self.assertFalse(passed)
            self.assertIn("jig_version", msg)

    def test_manifest_check_fails_when_manifest_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            (project / "scaffold.json").unlink()
            passed, msg = verify_install.check_scaffold_manifest(project)
            self.assertFalse(passed)
            self.assertIn("scaffold.json", msg)

    # ---- AC #4: docs smoke check wired in + runnable via the verifier ----
    def test_docs_check_fails_on_dangling_local_link(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            doc = project / "docs" / "guide.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("See [the plan](./missing.md).\n")
            passed, msg = verify_install.check_scaffold_docs(project)
            self.assertFalse(passed)
            self.assertIn("missing.md", msg)

    def test_docs_check_runnable_via_scaffold_mode_runner(self):
        """AC #4 — the docs smoke check runs as part of the scaffold-mode
        verifier: a dangling local link makes `run_headless_scaffold` exit
        non-zero and name the offending doc."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            doc = project / "docs" / "guide.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("Broken [link](./nope.md).\n")
            buf = io.StringIO()
            rc = verify_install.run_headless_scaffold(project, out=buf)
            self.assertEqual(rc, 1, msg=buf.getvalue())
            self.assertIn("nope.md", buf.getvalue())


# --------------------------------------------------------------------------
# Slice 052-04 AC3/AC4 — security-floor presence checks
# --------------------------------------------------------------------------


class SecurityFloorChecksTests(unittest.TestCase):
    """The three new scaffold-mode floor checks (slice 052-04, ADR-0013):
    secret-scan registration, `permissions.deny` defaults, and the
    `.gitignore` secret floor. Presence (full fixture passes) + per-artifact
    absence (removing each one fails exactly its own check)."""

    # ----- presence: full floor passes all three -----
    def test_full_floor_fixture_passes_all_three_checks(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            for check in (
                verify_install.check_scaffold_secret_scan_registered,
                verify_install.check_scaffold_permissions_deny_floor,
                verify_install.check_scaffold_gitignore_secret_floor,
            ):
                passed, msg = check(project)
                self.assertTrue(passed, f"{check.__name__}: {msg}")

    def test_full_floor_fixture_in_scaffold_check_list(self):
        """The three checks are registered in `_SCAFFOLD_CHECKS`, so
        `run_all_scaffold_checks` exercises them on a full-floor fixture."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            results = verify_install.run_all_scaffold_checks(project)
            self.assertTrue(
                all(passed for passed, _ in results),
                f"all scaffold checks should pass on a full-floor fixture; "
                f"got {results!r}",
            )
            names = [name for name, _ in verify_install._SCAFFOLD_CHECKS]
            for expected in (
                "secret-scan",
                "permissions-deny",
                "gitignore-floor",
            ):
                self.assertIn(expected, names)

    # ----- absence: secret-scan registration missing -----
    def test_secret_scan_check_fails_when_registration_absent(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            # Strip the PreToolUse secret-scan group, leaving the other
            # jig-managed (SessionStart) hook — the generic registration
            # check would still pass, but this stronger check must fail.
            project = _make_full_floor_scaffold_root(Path(td))
            settings_path = project / ".claude" / "settings.json"
            data = json.loads(settings_path.read_text())
            data["hooks"].pop("PreToolUse", None)
            settings_path.write_text(json.dumps(data, indent=2) + "\n")
            passed, msg = verify_install.check_scaffold_secret_scan_registered(
                project
            )
            self.assertFalse(passed)
            self.assertIn("secret-scan", msg.lower())

    def test_secret_scan_check_fails_when_settings_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            (project / ".claude" / "settings.json").unlink()
            passed, msg = verify_install.check_scaffold_secret_scan_registered(
                project
            )
            self.assertFalse(passed)
            self.assertIn("settings", msg.lower())

    def test_secret_scan_check_fails_when_entry_not_jig_managed(self):
        """A secret-scan command without the jig marker doesn't count."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            settings_path = project / ".claude" / "settings.json"
            data = json.loads(settings_path.read_text())
            for entry in data["hooks"]["PreToolUse"]:
                entry.pop("metadata", None)
            settings_path.write_text(json.dumps(data, indent=2) + "\n")
            passed, _ = verify_install.check_scaffold_secret_scan_registered(
                project
            )
            self.assertFalse(passed)

    # ----- absence: permissions.deny floor missing -----
    def test_permissions_deny_check_fails_when_absent(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            settings_path = project / ".claude" / "settings.json"
            data = json.loads(settings_path.read_text())
            data.pop("permissions", None)  # no deny floor at all
            settings_path.write_text(json.dumps(data, indent=2) + "\n")
            passed, msg = verify_install.check_scaffold_permissions_deny_floor(
                project
            )
            self.assertFalse(passed)
            self.assertIn("deny", msg.lower())

    def test_permissions_deny_check_fails_when_partial(self):
        """A deny array missing one of the representative guardrails fails."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            settings_path = project / ".claude" / "settings.json"
            data = json.loads(settings_path.read_text())
            data["permissions"]["deny"] = ["Bash(rm -rf*)"]  # drop two
            settings_path.write_text(json.dumps(data, indent=2) + "\n")
            passed, _ = verify_install.check_scaffold_permissions_deny_floor(
                project
            )
            self.assertFalse(passed)

    def test_permissions_deny_check_tolerates_extra_user_entries(self):
        """An issubset check tolerates user-added deny entries."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            settings_path = project / ".claude" / "settings.json"
            data = json.loads(settings_path.read_text())
            data["permissions"]["deny"].append("Bash(curl*evil*)")
            settings_path.write_text(json.dumps(data, indent=2) + "\n")
            passed, msg = verify_install.check_scaffold_permissions_deny_floor(
                project
            )
            self.assertTrue(passed, msg)

    # ----- absence: .gitignore secret floor missing -----
    def test_gitignore_floor_check_fails_when_file_absent(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            (project / ".gitignore").unlink()  # no .gitignore at all
            passed, msg = verify_install.check_scaffold_gitignore_secret_floor(
                project
            )
            self.assertFalse(passed)
            self.assertIn(".gitignore", msg.lower())

    def test_gitignore_floor_check_fails_when_marker_absent(self):
        """A .gitignore without the jig secret-ignore marker fails."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_full_floor_scaffold_root(Path(td))
            (project / ".gitignore").write_text("node_modules/\ndist/\n")
            passed, msg = verify_install.check_scaffold_gitignore_secret_floor(
                project
            )
            self.assertFalse(passed)
            self.assertIn("secret-ignore", msg.lower())


# --------------------------------------------------------------------------
# Slice 048-06 — scaffold-completion verification (seed check + summary)
# --------------------------------------------------------------------------


def _add_seed(project_root: Path) -> Path:
    """Drop the slice 048-05 worked-example seed files under docs/specs/."""
    specs = project_root / "docs" / "specs"
    (specs / "001-adopt-jig").mkdir(parents=True, exist_ok=True)
    (specs / "002-first-spec").mkdir(parents=True, exist_ok=True)
    (specs / "001-adopt-jig" / "spec.md").write_text("# adopt jig\n")
    (specs / "001-adopt-jig" / "slice-01-bootstrap.md").write_text("# bootstrap\n")
    (specs / "002-first-spec" / "spec.md").write_text("# first spec\n")
    (specs / "README.md").write_text("# status board\n")
    return project_root


class SeedPresenceCheckTests(unittest.TestCase):
    """AC #3 — the worked-example seed is in the expected set."""

    def test_seed_check_passes_when_all_files_present(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _add_seed(Path(td))
            passed, msg = verify_install.check_scaffold_seed_present(project)
            self.assertTrue(passed, msg)

    def test_seed_check_fails_when_a_file_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _add_seed(Path(td))
            (project / "docs/specs/001-adopt-jig/slice-01-bootstrap.md").unlink()
            passed, msg = verify_install.check_scaffold_seed_present(project)
            self.assertFalse(passed)
            self.assertIn("slice-01-bootstrap.md", msg)

    def test_seed_check_fails_when_status_board_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _add_seed(Path(td))
            (project / "docs/specs/README.md").unlink()
            passed, msg = verify_install.check_scaffold_seed_present(project)
            self.assertFalse(passed)
            self.assertIn("README.md", msg)


class CompletionSummaryTests(unittest.TestCase):
    """AC #1 / #2 / #4 + mode-awareness for run_completion_summary."""

    def test_in_repo_good_scaffold_passes_including_seed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            _add_seed(project)
            buf = io.StringIO()
            rc = verify_install.run_completion_summary(
                project, with_machinery=True, seed_expected=True, out=buf,
            )
            out = buf.getvalue()
            self.assertEqual(rc, 0, msg=out)
            self.assertIn("in-repo", out)
            self.assertIn("seed", out)
            self.assertIn("verified", out.lower())

    def test_plugin_only_good_scaffold_passes_without_machinery_false_fail(self):
        """A plugin-only scaffold has no .claude/ machinery — the machinery
        checks must be skipped, not false-failed; the seed still verifies."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            # NB: no _make_fake_scaffold_root — there is no .claude/ tree.
            project = _add_seed(Path(td))
            buf = io.StringIO()
            rc = verify_install.run_completion_summary(
                project, with_machinery=False, seed_expected=True, out=buf,
            )
            out = buf.getvalue()
            self.assertEqual(rc, 0, msg=out)
            self.assertIn("plugin-only", out)
            # Machinery checks must NOT appear in plugin-only mode.
            self.assertNotIn("[FAIL]", out)
            self.assertNotIn("skills:", out)
            self.assertIn("seed", out)

    def test_missing_machinery_artifact_fails_loudly(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            _add_seed(project)
            # Remove a required agent file.
            (project / ".claude/agents/jig-reviewer.md").unlink()
            buf = io.StringIO()
            rc = verify_install.run_completion_summary(
                project, with_machinery=True, seed_expected=True, out=buf,
            )
            out = buf.getvalue()
            self.assertEqual(rc, 1, msg=out)
            self.assertIn("FAILED", out)
            self.assertIn("agents", out)

    def test_missing_seed_file_fails_loudly(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            _add_seed(project)
            (project / "docs/specs/001-adopt-jig/spec.md").unlink()
            buf = io.StringIO()
            rc = verify_install.run_completion_summary(
                project, with_machinery=True, seed_expected=True, out=buf,
            )
            out = buf.getvalue()
            self.assertEqual(rc, 1, msg=out)
            self.assertIn("FAILED", out)
            self.assertIn("seed", out)

    def test_non_greenfield_skipped_seed_is_not_a_failure(self):
        """When seed_expected=False (non-greenfield scaffold legitimately
        skipped the seed), its absence must NOT be reported as a failure."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            # No seed files at all.
            buf = io.StringIO()
            rc = verify_install.run_completion_summary(
                project, with_machinery=True, seed_expected=False, out=buf,
            )
            out = buf.getvalue()
            self.assertEqual(rc, 0, msg=out)
            self.assertNotIn("seed", out)
            self.assertIn("verified", out.lower())


# --------------------------------------------------------------------------
# Live-mode probe prompts (AC #4 live mode, AC #7 architect coverage)
# --------------------------------------------------------------------------


class ProbePromptTests(unittest.TestCase):
    def test_probe_prompt_includes_temp_path(self):
        prompt = verify_install.probe_prompt("reviewer", "/tmp/jig-probe-abc.txt")
        self.assertIn("/tmp/jig-probe-abc.txt", prompt)

    def test_probe_prompt_instructs_write_attempt(self):
        prompt = verify_install.probe_prompt("reviewer", "/tmp/x.txt")
        self.assertRegex(prompt.lower(), r"\bwrite\b")

    def test_probe_prompts_exist_for_each_agent(self):
        for agent in ("reviewer", "implementer", "architect"):
            prompt = verify_install.probe_prompt(agent, "/tmp/x.txt")
            self.assertTrue(prompt and prompt.strip())

    def test_probe_prompt_rejects_unknown_agent(self):
        with self.assertRaises(verify_install.VerifyError):
            verify_install.probe_prompt("bogus", "/tmp/x.txt")


# --------------------------------------------------------------------------
# CLI plumbing
# --------------------------------------------------------------------------


class CliTests(unittest.TestCase):
    def test_cli_headless_default(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = verify_install.main(
                    ["verify_install.py", "--plugin-root", str(root)]
                )
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0, msg=f"output was:\n{captured.getvalue()}")

    def test_cli_mode_plugin_runs_plugin_checks(self):
        """Slice 016-03 AC #4 — `--mode plugin` runs the existing four
        plugin-mode checks (today's default behavior)."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = _make_fake_plugin_root(Path(td))
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = verify_install.main(
                    [
                        "verify_install.py",
                        "--plugin-root",
                        str(root),
                        "--mode",
                        "plugin",
                    ]
                )
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0, msg=f"output was:\n{captured.getvalue()}")
            self.assertIn("marketplace", captured.getvalue())

    def test_cli_mode_scaffold_runs_scaffold_checks(self):
        """Slice 016-03 AC #4 — `--mode scaffold` runs the new
        scaffold-mode checks against a scaffolded `.claude/` tree."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project = _make_fake_scaffold_root(Path(td))
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = verify_install.main(
                    [
                        "verify_install.py",
                        "--project-root",
                        str(project),
                        "--mode",
                        "scaffold",
                    ]
                )
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0, msg=f"output was:\n{captured.getvalue()}")

    def test_cli_probe_subcommand_emits_prompt_to_stdout(self):
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            rc = verify_install.main(
                [
                    "verify_install.py",
                    "probe",
                    "reviewer",
                    "--temp-path",
                    "/tmp/jig-probe-xyz.txt",
                ]
            )
        finally:
            sys.stdout = old_stdout
        self.assertEqual(rc, 0)
        self.assertIn("/tmp/jig-probe-xyz.txt", captured.getvalue())

    def test_cli_unknown_agent_in_probe_exits_two(self):
        # argparse will reject unknown choice with exit code 2
        with self.assertRaises(SystemExit) as cm:
            verify_install.main(
                [
                    "verify_install.py",
                    "probe",
                    "bogus",
                    "--temp-path",
                    "/tmp/x",
                ]
            )
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
