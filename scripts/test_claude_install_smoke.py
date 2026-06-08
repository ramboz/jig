"""
Tests for scripts/claude_install_smoke.py — slice 061-06.

The live Claude CLI portion is exercised with an injected command runner (and a
stub `claude` bin) so CI does not need a real Claude install — and so tests
never mutate global Claude config (no `marketplace add` / `plugin install`; the
smoke uses only the read-only `claude plugin validate`). The static substitute
runs against the real committed hosts/claude package.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import claude_install_smoke  # noqa: E402
import install_contract  # noqa: E402


def _completed(
    args: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args, returncode=returncode, stdout=stdout, stderr=stderr
    )


def _fake_claude_bin(tmp: Path) -> Path:
    path = tmp / "claude"
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return path


def _claude_shaped_tree(root: Path) -> Path:
    """Build a minimal hosts/claude-shaped tree that passes the contract."""
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "jig", "version": "1.0.0", "description": "x"})
    )
    skills = root / "skills"
    for skill in install_contract.EXPECTED_SKILLS:
        (skills / skill).mkdir(parents=True)
        (skills / skill / "SKILL.md").write_text("# skill\n")
    agents = root / "agents"
    agents.mkdir()
    for agent in install_contract.REQUIRED_AGENTS:
        (agents / f"{agent}.md").write_text("# agent\n")
    return root


# ---------------------------------------------------------------------------
# AC1 — committed package is Claude-shaped
# ---------------------------------------------------------------------------
class CommittedPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-claude-committed-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_tree_passes(self):
        tree = _claude_shaped_tree(self.tmp / "pkg")
        result = claude_install_smoke._validate_committed_package(tree)
        self.assertEqual(result.status, claude_install_smoke.PASS, result.message)

    def test_codex_plugin_dir_fails_naming_path(self):
        tree = _claude_shaped_tree(self.tmp / "pkg")
        (tree / ".codex-plugin").mkdir()
        result = claude_install_smoke._validate_committed_package(tree)
        self.assertEqual(result.status, claude_install_smoke.FAIL)
        self.assertIn(".codex-plugin", result.message)

    def test_in_package_marketplace_fails_naming_path(self):
        tree = _claude_shaped_tree(self.tmp / "pkg")
        (tree / ".claude-plugin" / "marketplace.json").write_text("{}")
        result = claude_install_smoke._validate_committed_package(tree)
        self.assertEqual(result.status, claude_install_smoke.FAIL)
        self.assertIn("marketplace.json", result.message)

    def test_dev_dirs_in_package_fail(self):
        tree = _claude_shaped_tree(self.tmp / "pkg")
        (tree / "scripts").mkdir()
        (tree / "scripts" / "x.py").write_text("x")
        result = claude_install_smoke._validate_committed_package(tree)
        self.assertEqual(result.status, claude_install_smoke.FAIL)
        self.assertIn("scripts", result.message)

    def test_real_committed_package_passes(self):
        result = claude_install_smoke._validate_committed_package(
            REPO_ROOT / "hosts" / "claude"
        )
        self.assertEqual(result.status, claude_install_smoke.PASS, result.message)


# ---------------------------------------------------------------------------
# AC2 — remote-install pointer
# ---------------------------------------------------------------------------
class RemotePointerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-claude-pointer-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_marketplace(self, path_value: str) -> Path:
        mp = self.tmp / ".claude-plugin"
        mp.mkdir(parents=True)
        (mp / "marketplace.json").write_text(
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
                                "path": path_value,
                            },
                            "description": "d",
                        }
                    ],
                }
            )
        )
        return self.tmp

    def test_hosts_claude_path_passes(self):
        root = self._write_marketplace("hosts/claude")
        result = claude_install_smoke._validate_remote_pointer(root)
        self.assertEqual(result.status, claude_install_smoke.PASS, result.message)
        self.assertIn("hosts/claude", result.message)

    def test_dot_path_fails(self):
        root = self._write_marketplace(".")
        result = claude_install_smoke._validate_remote_pointer(root)
        self.assertEqual(result.status, claude_install_smoke.FAIL)
        self.assertIn("Claude", result.message)

    def test_real_root_marketplace_passes(self):
        result = claude_install_smoke._validate_remote_pointer(REPO_ROOT)
        self.assertEqual(result.status, claude_install_smoke.PASS, result.message)


# ---------------------------------------------------------------------------
# AC3 — release archive
# ---------------------------------------------------------------------------
class ReleaseArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-claude-archive-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_built_zip_extracts_flat_and_passes(self):
        result = claude_install_smoke._validate_release_archive(
            source_root=REPO_ROOT, work_root=self.tmp
        )
        self.assertEqual(result.status, claude_install_smoke.PASS, result.message)

    def test_tampered_zip_fails(self):
        import zipfile

        bad = self.tmp / "bad.zip"
        with zipfile.ZipFile(bad, "w") as zf:
            # Nested (non-flat) shape: plugin.json buried under a subdir, so the
            # extract root does NOT carry .claude-plugin/plugin.json.
            zf.writestr("nested/.claude-plugin/plugin.json", "{}")
        result = claude_install_smoke._smoke_zip(bad)
        self.assertEqual(result.status, claude_install_smoke.FAIL)
        self.assertIn("Claude", result.message)


# ---------------------------------------------------------------------------
# AC5 — scaffold-helper execution (deterministic substitute)
# ---------------------------------------------------------------------------
class ScaffoldHelperTests(unittest.TestCase):
    def test_real_helper_runs(self):
        result = claude_install_smoke._validate_scaffold_helper(
            REPO_ROOT / "hosts" / "claude"
        )
        self.assertEqual(result.status, claude_install_smoke.PASS, result.message)

    def test_missing_helper_fails_clearly(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-claude-helper-"))
        try:
            result = claude_install_smoke._validate_scaffold_helper(tmp)
            self.assertEqual(result.status, claude_install_smoke.FAIL)
            self.assertIn("scaffold", result.message)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# AC4 / AC5 — live probe vs honest fallback
# ---------------------------------------------------------------------------
class LiveProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-claude-live-"))
        self.claude_bin = _fake_claude_bin(self.tmp)
        self.calls: list[list[str]] = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _runner(self, args, cwd, env, timeout):
        args = list(args)
        if args[0] != str(self.claude_bin):
            return claude_install_smoke._run_command(args, cwd, env, timeout)
        self.calls.append(args)
        command = args[1:]
        if command == ["--version"]:
            return _completed(args, stdout="2.1.142 (Claude Code)\n")
        if command[:2] == ["plugin", "validate"]:
            return _completed(args, stdout="✔ Validation passed\n")
        return _completed(args, returncode=99, stderr=f"unexpected: {command}\n")

    def test_live_probe_records_command_and_version(self):
        results = claude_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            claude_bin=str(self.claude_bin),
            runner=self._runner,
        )
        by_name = {r.name: r for r in results}
        cli = by_name["claude-cli"]
        self.assertEqual(cli.status, claude_install_smoke.PASS, cli.message)
        self.assertIn("2.1.142", cli.message)
        self.assertEqual(
            by_name["claude-validate-package"].status, claude_install_smoke.PASS
        )
        called = [c[1:] for c in self.calls]
        self.assertIn(
            ["plugin", "validate", str(REPO_ROOT / "hosts" / "claude")], called
        )
        self.assertEqual(
            claude_install_smoke.exit_code(results, require_live_claude=False), 0
        )

    def test_missing_claude_cli_is_unavailable_not_fail(self):
        results = claude_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            claude_bin=str(self.tmp / "missing-claude"),
        )
        cli = [r for r in results if r.name == "claude-cli"][0]
        self.assertEqual(cli.status, claude_install_smoke.UNAVAILABLE)
        self.assertIn("not found", cli.message)
        # The deterministic substitute still ran and is the pass/fail basis.
        by_name = {r.name: r for r in results}
        for name in (
            "claude-committed-package",
            "claude-remote-pointer",
            "claude-release-archive",
            "claude-scaffold-helper",
        ):
            self.assertEqual(by_name[name].status, claude_install_smoke.PASS, name)
        self.assertEqual(
            claude_install_smoke.exit_code(results, require_live_claude=False), 0
        )
        self.assertEqual(
            claude_install_smoke.exit_code(results, require_live_claude=True), 2
        )

    def test_skip_live_flag_marks_unavailable(self):
        results = claude_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            skip_live_claude=True,
        )
        live = [r for r in results if r.name == "claude-live-surfaces"][0]
        self.assertEqual(live.status, claude_install_smoke.UNAVAILABLE)
        self.assertEqual(
            claude_install_smoke.exit_code(results, require_live_claude=False), 0
        )

    def test_unrecognized_subcommand_degrades_to_unavailable(self):
        def runner(args, cwd, env, timeout):
            args = list(args)
            if args[0] == str(self.claude_bin) and args[1:3] == ["plugin", "validate"]:
                return _completed(
                    args, returncode=2, stderr="unrecognized subcommand 'validate'\n"
                )
            return self._runner(args, cwd, env, timeout)

        results = claude_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            claude_bin=str(self.claude_bin),
            runner=runner,
        )
        pkg = [r for r in results if r.name == "claude-validate-package"][0]
        self.assertEqual(pkg.status, claude_install_smoke.UNAVAILABLE)
        self.assertEqual(
            claude_install_smoke.exit_code(results, require_live_claude=False), 0
        )


# ---------------------------------------------------------------------------
# AC6 — failure diagnostics name the host
# ---------------------------------------------------------------------------
class HostNamingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-claude-naming-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_result_name_is_claude_prefixed(self):
        results = claude_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            skip_live_claude=True,
        )
        for result in results:
            self.assertTrue(
                result.name.startswith("claude-"),
                f"result {result.name!r} is not claude-prefixed",
            )

    def test_forced_failure_message_names_claude(self):
        tree = _claude_shaped_tree(self.tmp / "pkg")
        (tree / ".codex-plugin").mkdir()
        result = claude_install_smoke._validate_committed_package(tree)
        self.assertEqual(result.status, claude_install_smoke.FAIL)
        self.assertIn("Claude", result.message)


class TimeoutTests(unittest.TestCase):
    def test_command_timeout_returns_structured_result(self):
        result = claude_install_smoke._run_command(
            [sys.executable, "-c", "import time; time.sleep(1)"],
            None,
            {},
            0.01,
        )
        self.assertEqual(result.returncode, 124)
        self.assertIn("timed out", result.stderr)


if __name__ == "__main__":
    unittest.main()
