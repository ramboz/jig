"""
Tests for scripts/build_host_packages.py — slice 061-02 (unified host-package
build entry point).

AC #5: the Claude builder (061-01) and the Codex builder are invocable together
through a single entry point so 061-03 can regenerate both in one step.
"""

import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_host_packages  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


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


if __name__ == "__main__":
    unittest.main()
