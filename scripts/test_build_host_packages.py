"""
Tests for scripts/build_host_packages.py — slice 061-02 (unified host-package
build entry point) + slice 061-03 (drift guard).

AC #5 (061-02): the Claude builder (061-01) and the Codex builder are invocable
together through a single entry point so 061-03 can regenerate both in one step.

061-03 adds a regenerate-and-diff drift guard (`--check`), a determinism
assertion, and CI enforcement.
"""

import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_host_packages  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _file_map(root: Path) -> dict[str, bytes]:
    """Map every file under `root` to its bytes, keyed by posix relpath."""
    out: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


class BuildHostPackagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-host-pkgs-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_builds_both_packages(self):
        out = io.StringIO()
        code = build_host_packages.build_all(
            source_root=REPO_ROOT,
            hosts_root=self.tmp,
            out=out,
        )
        self.assertEqual(code, 0, out.getvalue())
        # Claude package
        self.assertTrue(
            (self.tmp / "claude" / ".claude-plugin" / "plugin.json").is_file()
        )
        # Codex package + marketplace descriptor
        self.assertTrue(
            (self.tmp / "codex" / ".agents" / "plugins" / "marketplace.json").is_file()
        )
        self.assertTrue(
            (
                self.tmp
                / "codex"
                / "plugins"
                / "jig"
                / ".codex-plugin"
                / "plugin.json"
            ).is_file()
        )

    def test_reports_both_targets(self):
        out = io.StringIO()
        build_host_packages.build_all(
            source_root=REPO_ROOT, hosts_root=self.tmp, out=out
        )
        log = out.getvalue()
        self.assertIn("claude", log)
        self.assertIn("codex", log)

    def test_main_default_targets_repo_hosts(self):
        # main() with no args should default to the repo hosts/ dir; we don't
        # run it here (it would rewrite the committed tree), but the parser
        # default must be None so build_all picks <source-root>/hosts.
        ns = build_host_packages._build_parser().parse_args([])
        self.assertIsNone(ns.hosts_root)


class DriftCheckTests(unittest.TestCase):
    """061-03 AC #2: a drift check regenerates and diffs against committed
    packages, exiting non-zero with an actionable summary naming the stale
    path + the regenerate command when they differ."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-drift-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_committed(self) -> Path:
        """Build a fresh, in-sync committed hosts/ tree for the repo source."""
        hosts = self.tmp / "hosts"
        code = build_host_packages.build_all(
            source_root=REPO_ROOT, hosts_root=hosts, out=io.StringIO()
        )
        self.assertEqual(code, 0)
        return hosts

    def test_check_passes_when_in_sync(self):
        diagnostics_enabled = (
            os.environ.get(build_host_packages.DIAGNOSTICS_ENV) == "1"
        )
        source_manifest = REPO_ROOT / build_host_packages.CLAUDE_MANIFEST_REL
        source_before_seed = (
            build_host_packages._file_diagnostic(source_manifest)
            if diagnostics_enabled
            else ""
        )
        hosts = self._seed_committed()
        source_between_builds = (
            build_host_packages._file_diagnostic(source_manifest)
            if diagnostics_enabled
            else ""
        )
        out = io.StringIO()
        if diagnostics_enabled:
            with patch.dict(
                os.environ,
                {build_host_packages.PRESERVE_SCRATCH_ENV: "1"},
            ):
                code = build_host_packages.check_drift(
                    source_root=REPO_ROOT, hosts_root=hosts, out=out
                )
        else:
            code = build_host_packages.check_drift(
                source_root=REPO_ROOT, hosts_root=hosts, out=out
            )
        message = out.getvalue()
        if code != 0 and diagnostics_enabled:
            message += (
                "Seed-build diagnostics:\n"
                f"  source-before-seed: {source_before_seed}\n"
                f"  source-between-builds: {source_between_builds}\n"
            )
        self.assertEqual(code, 0, message)

    def test_diagnostic_mode_preserves_and_describes_manifest_omission(self):
        hosts = self._seed_committed()
        original_iter = build_host_packages.build_claude_plugin._iter_package_files

        def omit_manifest(source_root):
            return [
                rel
                for rel in original_iter(source_root)
                if rel.as_posix() != ".claude-plugin/plugin.json"
            ]

        out = io.StringIO()
        with (
            patch.dict(
                os.environ,
                {
                    "JIG_HOST_DRIFT_DIAGNOSTICS": "1",
                    "JIG_HOST_DRIFT_PRESERVE_SCRATCH": "1",
                },
            ),
            patch.object(
                build_host_packages.build_claude_plugin,
                "_iter_package_files",
                side_effect=omit_manifest,
            ),
        ):
            code = build_host_packages.check_drift(
                source_root=REPO_ROOT, hosts_root=hosts, out=out
            )

        self.assertEqual(code, 1)
        log = out.getvalue()
        self.assertIn("Host drift diagnostics:", log)
        self.assertRegex(
            log,
            r"source-before: present size=\d+ sha256=[0-9a-f]{64} mtime_ns=\d+",
        )
        self.assertRegex(
            log,
            r"source-after: present size=\d+ sha256=[0-9a-f]{64} mtime_ns=\d+",
        )
        self.assertIn("scratch: absent", log)
        self.assertRegex(
            log,
            r"committed: present size=\d+ sha256=[0-9a-f]{64} mtime_ns=\d+",
        )
        self.assertIn("claude-manifest-enumerated: no", log)

        match = re.search(r"scratch-preserved: (.+)", log)
        self.assertIsNotNone(match, log)
        scratch = Path(match.group(1).strip())
        try:
            self.assertTrue(scratch.is_dir())
            self.assertFalse(
                (scratch / "claude" / ".claude-plugin" / "plugin.json").exists()
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_diagnostic_mode_cleans_scratch_without_preserve_opt_in(self):
        hosts = self._seed_committed()
        original_iter = build_host_packages.build_claude_plugin._iter_package_files
        scratch = self.tmp / "controlled-scratch"

        def omit_manifest(source_root):
            return [
                rel
                for rel in original_iter(source_root)
                if rel.as_posix() != ".claude-plugin/plugin.json"
            ]

        def make_scratch(prefix):
            self.assertEqual(prefix, "jig-host-drift-")
            scratch.mkdir()
            return str(scratch)

        out = io.StringIO()
        with (
            patch.dict(
                os.environ,
                {
                    "JIG_HOST_DRIFT_DIAGNOSTICS": "1",
                    "JIG_HOST_DRIFT_PRESERVE_SCRATCH": "0",
                },
            ),
            patch.object(
                build_host_packages.build_claude_plugin,
                "_iter_package_files",
                side_effect=omit_manifest,
            ),
            patch.object(
                build_host_packages.tempfile,
                "mkdtemp",
                side_effect=make_scratch,
            ),
        ):
            code = build_host_packages.check_drift(
                source_root=REPO_ROOT, hosts_root=hosts, out=out
            )

        self.assertEqual(code, 1)
        self.assertIn("Host drift diagnostics:", out.getvalue())
        self.assertIn("scratch-preserved: no", out.getvalue())
        self.assertFalse(scratch.exists())

    def test_check_does_not_mutate_committed_tree(self):
        hosts = self._seed_committed()
        before = _file_map(hosts)
        build_host_packages.check_drift(
            source_root=REPO_ROOT, hosts_root=hosts, out=io.StringIO()
        )
        self.assertEqual(_file_map(hosts), before)

    def test_check_ignores_ephemeral_bytecode_caches(self):
        # CI runs the test suite *before* the drift guard; importing a module
        # out of hosts/ seeds a __pycache__ the freshly-built scratch tree
        # lacks. The builders exclude __pycache__, so the guard must too —
        # otherwise it spuriously reads as drift.
        hosts = self._seed_committed()
        cache = hosts / "codex" / "plugins" / "jig" / "skills" / "_common" / "__pycache__"
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "atomic_io.cpython-312.pyc").write_bytes(b"\x00stray bytecode")
        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=REPO_ROOT, hosts_root=hosts, out=out
        )
        self.assertEqual(code, 0, out.getvalue())

    def test_check_detects_stale_modified_file(self):
        hosts = self._seed_committed()
        # Simulate a committed package that lags source (an edited file).
        stale = hosts / "claude" / ".claude-plugin" / "plugin.json"
        stale.write_text("DRIFTED\n")
        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=REPO_ROOT, hosts_root=hosts, out=out
        )
        self.assertNotEqual(code, 0)
        log = out.getvalue()
        self.assertIn("claude/.claude-plugin/plugin.json", log)
        # Names the regenerate command.
        self.assertIn("scripts/build_host_packages.py", log)

    def test_check_detects_missing_file(self):
        hosts = self._seed_committed()
        (hosts / "claude" / ".claude-plugin" / "plugin.json").unlink()
        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=REPO_ROOT, hosts_root=hosts, out=out
        )
        self.assertNotEqual(code, 0)
        self.assertIn("claude/.claude-plugin/plugin.json", out.getvalue())

    def test_check_detects_extra_file(self):
        hosts = self._seed_committed()
        extra = hosts / "claude" / "STALE_ARTIFACT.txt"
        extra.write_text("left over\n")
        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=REPO_ROOT, hosts_root=hosts, out=out
        )
        self.assertNotEqual(code, 0)
        self.assertIn("claude/STALE_ARTIFACT.txt", out.getvalue())

    def test_check_flag_wires_to_check_drift(self):
        hosts = self._seed_committed()
        (hosts / "claude" / ".claude-plugin" / "plugin.json").write_text("x\n")
        code = build_host_packages.main(
            [
                "build_host_packages.py",
                "--source-root",
                str(REPO_ROOT),
                "--hosts-root",
                str(hosts),
                "--check",
            ]
        )
        self.assertNotEqual(code, 0)


class DeterminismTests(unittest.TestCase):
    """061-03 AC #4: regenerating twice produces byte-identical output."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-determinism-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_two_builds_are_byte_identical(self):
        first = self.tmp / "first"
        second = self.tmp / "second"
        self.assertEqual(
            0,
            build_host_packages.build_all(
                source_root=REPO_ROOT, hosts_root=first, out=io.StringIO()
            ),
        )
        self.assertEqual(
            0,
            build_host_packages.build_all(
                source_root=REPO_ROOT, hosts_root=second, out=io.StringIO()
            ),
        )
        self.assertEqual(_file_map(first), _file_map(second))


class EdgeCaseTests(unittest.TestCase):
    """061-03 edge cases: a version-only source-manifest change reflects into
    BOTH committed packages; a partially-built hosts/ is fully replaced."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-edge-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_version_only_change_reflects_into_both_packages(self):
        # Mirror the repo source into a scratch root we can mutate.
        src = self.tmp / "src"
        shutil.copytree(
            REPO_ROOT,
            src,
            ignore=shutil.ignore_patterns(
                ".git", "hosts", "dist", "__pycache__", "*.pyc",
                ".pytest_cache", ".mypy_cache",
            ),
        )
        hosts = self.tmp / "hosts"
        self.assertEqual(
            0,
            build_host_packages.build_all(
                source_root=src, hosts_root=hosts, out=io.StringIO()
            ),
        )

        # Bump the version in BOTH source manifests (a release-bump scenario),
        # then confirm a drift check flags BOTH committed packages as stale.
        claude_manifest = src / ".claude-plugin" / "plugin.json"
        codex_manifest = src / ".codex-plugin" / "plugin.json"
        for manifest in (claude_manifest, codex_manifest):
            text = manifest.read_text()
            manifest.write_text(text.replace("\n}", '\n  ,"_v": "edge"\n}', 1))

        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=src, hosts_root=hosts, out=out
        )
        self.assertNotEqual(code, 0)
        log = out.getvalue()
        self.assertIn("claude/.claude-plugin/plugin.json", log)
        self.assertIn("plugins/jig/.codex-plugin/plugin.json", log)

    def test_partial_hosts_is_fully_replaced_not_merged(self):
        hosts = self.tmp / "hosts"
        # Leave behind a stale artifact from a notional interrupted run.
        stale = hosts / "claude" / "LEFTOVER.txt"
        stale.parent.mkdir(parents=True)
        stale.write_text("interrupted\n")

        self.assertEqual(
            0,
            build_host_packages.build_all(
                source_root=REPO_ROOT, hosts_root=hosts, out=io.StringIO()
            ),
        )
        # The full rmtree+recreate means the leftover is gone, not merged.
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
