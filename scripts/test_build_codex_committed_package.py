"""
Tests for scripts/build_codex_plugin.py committed-package retarget — slice
061-02 (committed Codex package peer at hosts/codex/).

Covers:
  - AC #1: the builder's default output targets hosts/codex/ — the marketplace
    descriptor lands at hosts/codex/.agents/plugins/marketplace.json and the
    nested plugin at hosts/codex/plugins/jig/.codex-plugin/plugin.json.
  - AC #2: the package is the full Codex install payload (rendered Codex skills,
    generated role-agent TOML, hooks, templates).
  - AC #3: the marketplace descriptor's plugin source.path resolves to the
    nested plugin from hosts/codex/.
  - AC #4: _validate_output_dir accepts hosts/codex/ and still refuses the
    source root, source-owned runtime paths, and ancestors of the source root.
  - Edge case: a stale pre-existing hosts/codex/ plugin dir is fully replaced.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_codex_plugin  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


class CodexDefaultOutputTargetTests(unittest.TestCase):
    """AC #1 — default output dir resolves to hosts/codex/plugins/jig."""

    def test_default_output_dir_is_hosts_codex(self):
        ns = build_codex_plugin._build_parser().parse_args([])
        self.assertIsNone(ns.output_dir)
        # main() computes the default from the source root.
        default = REPO_ROOT / "hosts" / "codex" / "plugins" / "jig"
        marketplace_root = build_codex_plugin._marketplace_root_for(default)
        self.assertEqual(marketplace_root, REPO_ROOT / "hosts" / "codex")

    def test_default_help_names_hosts_codex(self):
        parser = build_codex_plugin._build_parser()
        help_text = parser.format_help()
        self.assertIn("hosts/codex", help_text)
        self.assertNotIn("dist/codex-plugin", help_text)


class CodexCommittedPackageBuildTests(unittest.TestCase):
    """AC #1/#2/#3 — build into a hosts/codex-shaped layout."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-codex-host-"))
        self.host_root = self.tmp / "codex"
        self.plugin_dir = self.host_root / "plugins" / "jig"
        code = build_codex_plugin.build(
            source_root=REPO_ROOT,
            output_dir=self.plugin_dir,
        )
        self.assertEqual(code, 0)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # AC #1
    def test_marketplace_descriptor_at_host_root(self):
        self.assertTrue(
            (self.host_root / ".agents" / "plugins" / "marketplace.json").is_file()
        )

    # AC #1
    def test_nested_plugin_manifest(self):
        self.assertTrue(
            (self.plugin_dir / ".codex-plugin" / "plugin.json").is_file()
        )

    # AC #2 — full Codex install payload
    def test_payload_has_rendered_skills_hooks_templates_agents(self):
        skill = self.plugin_dir / "skills" / "scaffold-init" / "SKILL.md"
        self.assertTrue(skill.is_file())
        text = skill.read_text()
        self.assertIn("Codex", text)
        self.assertIn("${PLUGIN_ROOT}/skills/scaffold-init/scaffold.py", text)
        for rel in (
            "hooks/hooks.json",
            "hooks/scripts/jig-context-check.sh",
            "templates/AGENTS.md.template",
            "agents/reviewer.md",
        ):
            self.assertTrue((self.plugin_dir / rel).is_file(), rel)

    # AC #2 — generated role-agent TOML
    def test_payload_has_role_agent_toml(self):
        agent = self.plugin_dir / "agents" / "jig-reviewer.toml"
        self.assertTrue(agent.is_file())
        data = tomllib.loads(agent.read_text())
        self.assertEqual(data["name"], "jig-reviewer")
        self.assertEqual(data["sandbox_mode"], "read-only")

    # AC #3 — package-relative marketplace path
    def test_marketplace_source_path_resolves_to_plugin(self):
        descriptor = (
            self.host_root / ".agents" / "plugins" / "marketplace.json"
        )
        data = json.loads(descriptor.read_text())
        self.assertEqual(data["name"], "jig")
        plugin = data["plugins"][0]
        self.assertEqual(plugin["name"], "jig")
        rel_path = plugin["source"]["path"]
        self.assertEqual(rel_path, "./plugins/jig")
        resolved = (self.host_root / rel_path).resolve()
        self.assertEqual(resolved, self.plugin_dir.resolve())

    # Edge case — stale tree fully replaced, not merged
    def test_stale_plugin_dir_fully_replaced(self):
        stale = self.plugin_dir / "STALE_LEFTOVER.txt"
        stale.write_text("wipe me")
        code = build_codex_plugin.build(
            source_root=REPO_ROOT,
            output_dir=self.plugin_dir,
        )
        self.assertEqual(code, 0)
        self.assertFalse(stale.exists(), "stale file survived a rebuild")
        self.assertTrue(
            (self.plugin_dir / ".codex-plugin" / "plugin.json").is_file()
        )


class CodexValidateOutputDirTests(unittest.TestCase):
    """AC #4 — hosts/codex/ accepted; unsafe targets refused."""

    def test_accepts_hosts_codex(self):
        ok, reason = build_codex_plugin._validate_output_dir(
            REPO_ROOT, REPO_ROOT / "hosts" / "codex" / "plugins" / "jig"
        )
        self.assertTrue(ok, reason)

    def test_still_accepts_dist(self):
        ok, reason = build_codex_plugin._validate_output_dir(
            REPO_ROOT, REPO_ROOT / "dist" / "codex-plugin" / "plugins" / "jig"
        )
        self.assertTrue(ok, reason)

    def test_refuses_source_root(self):
        ok, _ = build_codex_plugin._validate_output_dir(REPO_ROOT, REPO_ROOT)
        self.assertFalse(ok)

    def test_refuses_source_owned_runtime_path(self):
        ok, _ = build_codex_plugin._validate_output_dir(
            REPO_ROOT, REPO_ROOT / "skills"
        )
        self.assertFalse(ok)

    def test_refuses_other_in_tree_path(self):
        ok, _ = build_codex_plugin._validate_output_dir(
            REPO_ROOT, REPO_ROOT / "scratch" / "codex"
        )
        self.assertFalse(ok)

    def test_refuses_ancestor_of_source_root(self):
        ok, _ = build_codex_plugin._validate_output_dir(
            REPO_ROOT, REPO_ROOT.parent
        )
        self.assertFalse(ok)


class CodexCommittedTreeTests(unittest.TestCase):
    """The committed hosts/codex/ tree exists and is coherent."""

    def test_committed_package_present(self):
        host_root = REPO_ROOT / "hosts" / "codex"
        self.assertTrue(
            (host_root / ".agents" / "plugins" / "marketplace.json").is_file(),
            "committed hosts/codex marketplace descriptor missing",
        )
        self.assertTrue(
            (host_root / "plugins" / "jig" / ".codex-plugin" / "plugin.json").is_file(),
            "committed hosts/codex plugin manifest missing",
        )


if __name__ == "__main__":
    unittest.main()
