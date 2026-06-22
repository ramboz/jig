"""
Codex plugin packaging contract tests — slice 033-06.

These tests pin the centralized Codex plugin surface without adding a second
Codex implementation path. The package must keep using the root
skills/hooks/agents source tree that scaffold mode already renders from, while
documenting the Codex hook trust step that runs after plugin installation.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_codex_plugin  # noqa: E402

CLAUDE_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"
CODEX_MANIFEST = REPO_ROOT / ".codex-plugin" / "plugin.json"


def _section_between(text: str, start: str, end: str) -> str:
    start_idx = text.index(start)
    end_idx = text.index(end, start_idx)
    return text[start_idx:end_idx]


def _build_codex_plugin_dir() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="jig-codex-plugin-"))
    plugin_dir = tmp / "jig"
    code = build_codex_plugin.build(
        source_root=REPO_ROOT,
        output_dir=plugin_dir,
    )
    if code != 0:
        raise RuntimeError(f"build_codex_plugin exited {code}")
    return plugin_dir


def _hook_handlers(data: dict) -> list[dict]:
    return [
        hook
        for entries in data.get("hooks", {}).values()
        for entry in entries
        for hook in entry.get("hooks", [])
    ]


class CodexPluginManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(CODEX_MANIFEST.read_text())
        self.claude_manifest = json.loads(CLAUDE_MANIFEST.read_text())

    def test_codex_plugin_manifest_exists(self):
        self.assertTrue(CODEX_MANIFEST.is_file())

    def test_manifest_name_matches_plugin_folder_name(self):
        self.assertEqual(self.manifest["name"], "jig")

    def test_manifest_version_matches_claude_plugin(self):
        self.assertEqual(
            self.manifest["version"],
            self.claude_manifest["version"],
        )

    def test_manifest_points_at_shared_skill_source(self):
        self.assertEqual(self.manifest["skills"], "./skills/")
        self.assertTrue((REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").is_file())
        self.assertFalse(
            (REPO_ROOT / "codex-skills").exists(),
            "Codex plugin packaging must not fork a second skill tree",
        )

    def test_manifest_omits_unsupported_agent_field(self):
        self.assertNotIn("agents", self.manifest)

    def test_interface_has_codex_required_fields(self):
        interface = self.manifest["interface"]
        for key in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "capabilities",
            "defaultPrompt",
        ):
            self.assertIn(key, interface)
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)

    def test_manifest_warns_hooks_need_trust_before_running(self):
        description = self.manifest["interface"]["longDescription"]
        self.assertIn("review and trust bundled hooks via /hooks", description)
        self.assertIn("before they run", description)


class CodexPluginRuntimeTests(unittest.TestCase):
    def test_default_hooks_config_is_packaged_at_codex_default_path(self):
        hooks = REPO_ROOT / "hooks" / "hooks.json"
        self.assertTrue(hooks.is_file())
        data = json.loads(hooks.read_text())
        self.assertIn("hooks", data)

    def test_hook_commands_remain_plugin_root_compatible(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        commands = [
            hook.get("command", "")
            for entries in data.get("hooks", {}).values()
            for entry in entries
            for hook in entry.get("hooks", [])
        ]
        self.assertGreater(len(commands), 0)
        self.assertTrue(
            all("${CLAUDE_PLUGIN_ROOT}/hooks/scripts/" in command for command in commands),
            "Codex plugin hooks rely on Codex's CLAUDE_PLUGIN_ROOT compatibility env",
        )

    def test_committed_codex_hooks_are_codex_runtime_compatible(self):
        data = json.loads(
            (
                REPO_ROOT
                / "hosts"
                / "codex"
                / "plugins"
                / "jig"
                / "hooks"
                / "hooks.json"
            ).read_text()
        )
        handlers = _hook_handlers(data)
        self.assertGreater(len(handlers), 0)
        commands = [
            hook["command"]
            for hook in handlers
            if hook.get("type") == "command"
        ]
        self.assertTrue(
            all(command.startswith("bash ${PLUGIN_ROOT}/hooks/scripts/")
                for command in commands),
            commands,
        )
        self.assertFalse(
            any("CLAUDE_PLUGIN_ROOT" in command or "CLAUDE_PROJECT_DIR" in command
                for command in commands),
            commands,
        )
        for hook in handlers:
            self.assertNotIn("async", hook)
            self.assertIn("statusMessage", hook)
            self.assertTrue(hook["statusMessage"].startswith("jig: "))
        self.assertIn(
            "jig: record task telemetry",
            {hook["statusMessage"] for hook in handlers},
        )

    def test_canonical_agent_prompts_are_bundled_once(self):
        agents = sorted(path.name for path in (REPO_ROOT / "agents").glob("*.md"))
        self.assertEqual(agents, ["architect.md", "implementer.md", "reviewer.md"])
        self.assertFalse(
            (REPO_ROOT / "codex-agents").exists(),
            "Codex plugin packaging must reuse the canonical agent source",
        )

    def test_scaffold_renderer_remains_the_codex_agent_materializer(self):
        text = (REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py").read_text()
        self.assertIn("class CodexScaffoldRenderer", text)
        self.assertIn("def render_codex_agent", text)


class CodexPluginBuilderTests(unittest.TestCase):
    def setUp(self):
        self.plugin_dir = _build_codex_plugin_dir()

    def tearDown(self):
        shutil.rmtree(self.plugin_dir.parent, ignore_errors=True)

    def test_builder_renders_plugin_manifest(self):
        self.assertTrue((self.plugin_dir / ".codex-plugin" / "plugin.json").is_file())

    def test_builder_renders_codex_skill_copy_from_shared_source(self):
        skill = self.plugin_dir / "skills" / "scaffold-init" / "SKILL.md"
        text = skill.read_text()
        self.assertIn("Codex", text)
        self.assertIn("${PLUGIN_ROOT}/skills/scaffold-init/scaffold.py", text)
        self.assertIn("--host codex", text)
        self.assertNotIn("${CODEX_PROJECT_DIR:-$PWD}/.codex/skills", text)

    def test_builder_renders_codex_override_guidance(self):
        for skill in ("pr-review", "arch-review", "contracts"):
            text = (self.plugin_dir / "skills" / skill / "SKILL.md").read_text()
            self.assertIn(
                f"$HOME/.agents/skills/{skill}/",
                text,
                f"Codex plugin {skill} should name Codex's user skill path",
            )
            self.assertNotIn(
                "~/.claude/skills",
                text,
                f"Codex plugin {skill} leaked Claude skill path guidance",
            )
            self.assertNotIn(
                "~/.codex/skills",
                text,
                f"Codex plugin {skill} invented an unsupported skill path",
            )
            self.assertNotIn(
                "Codex skill router",
                text,
                f"Codex plugin {skill} should use documented skill-selection wording",
            )
            self.assertNotIn(
                "router will prefer",
                text,
                f"Codex plugin {skill} should not promise router precedence",
            )

        pr_review = (
            self.plugin_dir / "skills" / "pr-review" / "SKILL.md"
        ).read_text()
        self.assertIn(
            "Codex-rendered guidance keeps richer-skill deferral to "
            "interactive skill selection or explicit invocation",
            pr_review,
        )

    def test_builder_copies_hooks_templates_and_agent_prompts(self):
        for rel in (
            "hooks/hooks.json",
            "hooks/scripts/jig-context-check.sh",
            "templates/AGENTS.md.template",
            "agents/reviewer.md",
        ):
            self.assertTrue((self.plugin_dir / rel).is_file(), rel)

    def test_builder_renders_codex_compatible_hook_metadata(self):
        data = json.loads((self.plugin_dir / "hooks" / "hooks.json").read_text())
        handlers = _hook_handlers(data)
        self.assertGreater(len(handlers), 0)
        for hook in handlers:
            self.assertNotIn("async", hook)
            self.assertIn("statusMessage", hook)
            self.assertTrue(hook["statusMessage"].startswith("jig: "))
        messages = {hook["statusMessage"] for hook in handlers}
        self.assertIn("jig: record skill usage", messages)
        self.assertIn("jig: record task telemetry", messages)

    def test_builder_renders_codex_agent_toml_templates(self):
        agent = self.plugin_dir / "agents" / "jig-reviewer.toml"
        self.assertTrue(agent.is_file())
        data = tomllib.loads(agent.read_text())
        self.assertEqual(data["name"], "jig-reviewer")
        self.assertEqual(data["sandbox_mode"], "read-only")
        self.assertIn("developer_instructions", data)
        self.assertIn("You are an independent reviewer", data["developer_instructions"])

    def test_generated_plugin_helper_installs_codex_agent_templates(self):
        agents_dir = self.plugin_dir.parent / "global-codex-agents"
        helper = self.plugin_dir / "skills" / "scaffold-init" / "scaffold.py"
        result = subprocess.run(
            [
                sys.executable,
                str(helper),
                "--install-codex-agents",
                "--codex-agents-dir",
                str(agents_dir),
            ],
            cwd=self.plugin_dir,
            capture_output=True,
            text=True,
            env={},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("installed 3 Codex agent(s)", result.stdout)
        agent = agents_dir / "jig-reviewer.toml"
        data = tomllib.loads(agent.read_text())
        self.assertEqual(data["name"], "jig-reviewer")
        self.assertEqual(data["sandbox_mode"], "read-only")

    def test_builder_writes_codex_marketplace_descriptor(self):
        marketplace = self.plugin_dir.parent / ".agents" / "plugins" / "marketplace.json"
        data = json.loads(marketplace.read_text())
        self.assertEqual(data["name"], "jig")
        plugin = data["plugins"][0]
        self.assertEqual(plugin["name"], "jig")
        self.assertEqual(plugin["source"]["path"], "./jig")

    def test_builder_refuses_to_delete_source_root(self):
        code = build_codex_plugin.build(
            source_root=REPO_ROOT,
            output_dir=REPO_ROOT,
        )
        self.assertNotEqual(code, 0)
        self.assertTrue(CODEX_MANIFEST.is_file())

    def test_builder_refuses_to_delete_source_owned_directory(self):
        existing_source_dir = REPO_ROOT / "skills"
        code = build_codex_plugin.build(
            source_root=REPO_ROOT,
            output_dir=existing_source_dir,
        )
        self.assertNotEqual(code, 0)
        self.assertTrue((existing_source_dir / "scaffold-init" / "SKILL.md").is_file())

    def test_builder_refuses_sibling_host_package_output(self):
        sentinel = REPO_ROOT / "hosts" / "claude" / ".claude-plugin" / "plugin.json"
        before = sentinel.read_text()
        code = build_codex_plugin.build(
            source_root=REPO_ROOT,
            output_dir=REPO_ROOT / "hosts" / "claude",
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(sentinel.read_text(), before)


class CodexPluginDocsTests(unittest.TestCase):
    def test_readme_names_all_supported_distribution_modes(self):
        text = (REPO_ROOT / "README.md").read_text()
        for phrase in (
            "Claude scaffold",
            "Claude plugin",
            "Codex scaffold",
            "Codex plugin",
        ):
            self.assertIn(phrase, text)

    def test_architecture_marks_codex_plugin_supported(self):
        text = (REPO_ROOT / "docs" / "architecture.md").read_text()
        self.assertIn("| Codex | Plugin | v2 supported |", text)

    def test_architecture_records_codex_plugin_hook_trust_runtime(self):
        text = (REPO_ROOT / "docs" / "architecture.md").read_text()
        section = _section_between(
            text,
            "### Codex plugin packaging",
            "### Context economy",
        )
        self.assertIn("plugin-bundled command hooks", section)
        self.assertIn("review and trust them through `/hooks`", section)
        self.assertIn("changed hook definitions require renewed trust", section)

    def test_readme_places_hook_trust_step_after_codex_plugin_add(self):
        text = (REPO_ROOT / "README.md").read_text()
        section = _section_between(
            text,
            "### Codex plugin (central install)",
            "### From source (contributors)",
        )
        install_idx = section.index("codex plugin add jig@jig")
        trust_idx = section.index("open `/hooks`")
        package_idx = section.index("The Codex plugin package includes")
        self.assertLess(install_idx, trust_idx)
        self.assertLess(trust_idx, package_idx)
        self.assertIn("reviewed and trusted before they run", section)
        self.assertIn("skips the hook gates", section)
        self.assertIn("current hook definition hash", section)

    def test_claude_plugin_install_docs_do_not_carry_codex_hook_trust(self):
        text = (REPO_ROOT / "README.md").read_text()
        section = _section_between(
            text,
            "**1. Acquire the plugin**",
            "## Codex Distribution",
        )
        self.assertNotIn("/hooks", section)
        self.assertNotIn("Codex requires", section)
        self.assertNotIn("hook definition hash", section)

    def test_generated_plugin_readme_keeps_hook_trust_step(self):
        plugin_dir = _build_codex_plugin_dir()
        try:
            section = _section_between(
                (plugin_dir / "README.md").read_text(),
                "### Codex plugin (central install)",
                "### From source (contributors)",
            )
            self.assertIn("codex plugin add jig@jig", section)
            self.assertIn("open `/hooks`", section)
            self.assertIn("skips the hook gates", section)
        finally:
            shutil.rmtree(plugin_dir.parent, ignore_errors=True)

    def test_docs_record_plugin_agent_discovery_deviation(self):
        readme = (REPO_ROOT / "README.md").read_text()
        architecture = (REPO_ROOT / "docs" / "architecture.md").read_text()
        refinement = (REPO_ROOT / "docs" / "refinement-todo.md").read_text()
        slice_doc = (
            REPO_ROOT
            / "docs"
            / "specs"
            / "033-host-adapter-portability"
            / "slice-06-codex-plugin-packaging.md"
        ).read_text()
        self.assertIn("Codex custom-agent discovery uses TOML", readme)
        self.assertIn("explicit post-install step", readme)
        self.assertIn("unsupported `agents` field", architecture)
        self.assertIn("TOML custom-agent templates", architecture)
        self.assertIn("plugin-level custom-agent discovery", refinement)
        self.assertIn("AC #3 deviation: custom-agent discovery", slice_doc)


if __name__ == "__main__":
    unittest.main()
