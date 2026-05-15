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

import verify_install  # noqa: E402


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _make_fake_plugin_root(tmpdir: Path) -> Path:
    """Build a minimum-shape plugin root that passes every headless check."""
    (tmpdir / ".claude-plugin").mkdir(parents=True)
    (tmpdir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "jig", "version": "0.1.0"})
    )
    (tmpdir / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "jig",
                "owner": {"name": "ramboz"},
                "plugins": [{"name": "jig", "source": "./"}],
            }
        )
    )
    (tmpdir / "agents").mkdir()
    for name in ("implementer", "reviewer", "architect"):
        (tmpdir / "agents" / f"{name}.md").write_text(f"# {name}\n")
    (tmpdir / "skills").mkdir()
    (tmpdir / "skills" / "scaffold-init").mkdir()
    (tmpdir / "skills" / "scaffold-init" / "SKILL.md").write_text("# scaffold-init\n")
    return tmpdir


def _make_fake_scaffold_root(tmpdir: Path) -> Path:
    """Build a minimum-shape scaffolded project that passes every
    scaffold-mode check (slice 016-03 AC #4)."""
    claude = tmpdir / ".claude"
    # skills/
    skills = claude / "skills"
    skills.mkdir(parents=True)
    (skills / "jig-scaffold-init").mkdir()
    (skills / "jig-scaffold-init" / "SKILL.md").write_text("# scaffold-init\n")
    # agents/
    agents = claude / "agents"
    agents.mkdir()
    for name in ("implementer", "reviewer", "architect"):
        (agents / f"jig-{name}.md").write_text(f"# {name}\n")
    # hooks/scripts/
    scripts = claude / "hooks" / "scripts"
    scripts.mkdir(parents=True)
    for name in (
        "jig-context-check.sh",
        "jig-memory-scan.sh",
        "jig-spec-gate.sh",
        "jig-task-capture.sh",
        "jig-telemetry.sh",
    ):
        s = scripts / name
        s.write_text("#!/bin/bash\n")
        s.chmod(0o755)
    # settings.json with at least one jig-managed hook entry
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
                    ]
                }
            },
            indent=2,
        )
        + "\n"
    )
    return tmpdir


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
        # Source resolves relative to the marketplace.json's parent (the
        # .claude-plugin/ dir); the plugin root is one level up.
        resolved = (self.repo_root / ".claude-plugin" / source).resolve()
        # The source should point at a directory that contains plugin.json.
        self.assertTrue(
            (resolved / ".claude-plugin" / "plugin.json").is_file()
            or (resolved / "plugin.json").is_file(),
            f"source {source!r} doesn't resolve to a plugin root with plugin.json",
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
            # 4 checks (marketplace / manifest / agents / skills) + 1 summary
            self.assertGreaterEqual(len(lines), 5)
            self.assertTrue(
                any("summary" in ln.lower() or "passed" in ln.lower() for ln in lines),
                f"expected a summary line; got:\n{buf.getvalue()}",
            )


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
