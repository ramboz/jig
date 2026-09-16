"""
Tests for scripts/build_host_packages.py — slice 061-02 (unified host-package
build entry point) + slice 061-03 (drift guard).

AC #5 (061-02): the Claude builder (061-01) and the Codex builder are invocable
together through a single entry point so 061-03 can regenerate both in one step.

061-03 adds a regenerate-and-diff drift guard (`--check`), a determinism
assertion, and CI enforcement.
"""

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

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


class CopilotPackageBuiltByBuildAllTests(unittest.TestCase):
    """Slice 113-02 — `build_all` builds the Copilot skeleton package
    (skills + manifest — no pre-rendered instructions file, per the 113-02
    review fix) alongside Claude and Codex."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-host-pkgs-copilot-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_all_also_builds_copilot(self):
        out = io.StringIO()
        code = build_host_packages.build_all(
            source_root=REPO_ROOT, hosts_root=self.tmp, out=out
        )
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue((self.tmp / "copilot" / ".plugin" / "plugin.json").is_file())
        self.assertTrue(
            (
                self.tmp / "copilot" / ".github" / "skills" / "scaffold-init"
                / "SKILL.md"
            ).is_file()
        )
        self.assertFalse(
            (self.tmp / "copilot" / ".github" / "copilot-instructions.md").exists()
        )

    def test_reports_copilot_target(self):
        out = io.StringIO()
        build_host_packages.build_all(
            source_root=REPO_ROOT, hosts_root=self.tmp, out=out
        )
        self.assertIn("copilot", out.getvalue())

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
        hosts = self._seed_committed()
        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=REPO_ROOT, hosts_root=hosts, out=out
        )
        self.assertEqual(code, 0, out.getvalue())

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

    def test_check_ignores_runtime_hook_logs(self):
        # A hook fired during the test suite (project_dir resolving to the repo)
        # writes per-checkout runtime state under a `.claude/` dir — e.g.
        # hooks/scripts/.claude/context-growth-read-events.jsonl. The builders
        # never emit these, so the freshly-built scratch tree lacks them; the
        # guard must treat them as ephemeral or a stray log reads as drift.
        hosts = self._seed_committed()
        log_dir = hosts / "claude" / "hooks" / "scripts" / ".claude"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "context-growth-read-events.jsonl").write_text(
            '{"event": "stray"}\n'
        )
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

    def test_check_detects_stale_copilot_file(self):
        # Slice 113-02: the drift guard is host-agnostic (walks the whole
        # hosts_root), so it must catch a stale Copilot file with no
        # Copilot-specific code — this proves that, rather than assuming it.
        hosts = self._seed_committed()
        stale = hosts / "copilot" / ".plugin" / "plugin.json"
        stale.write_text("DRIFTED\n")
        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=REPO_ROOT, hosts_root=hosts, out=out
        )
        self.assertNotEqual(code, 0)
        self.assertIn("copilot/.plugin/plugin.json", out.getvalue())

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
        # NOTE: this mutation appends a sibling `_v` field rather than
        # changing "version"'s VALUE, so it does not exercise the Copilot
        # manifest (which derives its version from that field's semantic
        # value, not the manifest file's raw bytes) — see
        # `test_copilot_manifest_reflects_an_actual_version_bump` below for
        # the assertion that DOES touch the version value.

    def test_copilot_manifest_reflects_an_actual_version_bump(self):
        # Unlike Claude/Codex (which copy .claude-plugin/.codex-plugin's
        # manifest file byte-for-byte), the Copilot manifest is derived from
        # the "version" FIELD'S VALUE (see build_copilot_plugin.build) — so
        # only a change to that value, not an unrelated byte in the file,
        # should flag hosts/copilot/.plugin/plugin.json as stale.
        src = self.tmp / "src2"
        shutil.copytree(
            REPO_ROOT,
            src,
            ignore=shutil.ignore_patterns(
                ".git", "hosts", "dist", "__pycache__", "*.pyc",
                ".pytest_cache", ".mypy_cache",
            ),
        )
        hosts = self.tmp / "hosts2"
        self.assertEqual(
            0,
            build_host_packages.build_all(
                source_root=src, hosts_root=hosts, out=io.StringIO()
            ),
        )
        claude_manifest = src / ".claude-plugin" / "plugin.json"
        data = json.loads(claude_manifest.read_text())
        data["version"] = "9.9.9"
        claude_manifest.write_text(json.dumps(data))

        out = io.StringIO()
        code = build_host_packages.check_drift(
            source_root=src, hosts_root=hosts, out=out
        )
        self.assertNotEqual(code, 0)
        self.assertIn("copilot/.plugin/plugin.json", out.getvalue())

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
