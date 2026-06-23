"""
Tests for scripts/codex_agent_discovery_probe.py - slice 059-06.

The live Codex CLI path uses an injected command runner so CI can verify the
agent-discovery decision without requiring a local Codex install.
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

import codex_agent_discovery_probe as discovery_probe  # noqa: E402


def _completed(
    args: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _fake_codex_bin(tmp: Path) -> Path:
    path = tmp / "codex"
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return path


def _prompt_json(text: str) -> str:
    return json.dumps(
        [
            {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": text}],
            }
        ]
    )


class CodexAgentDiscoveryStaticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-agent-discovery-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_static_probe_builds_agent_templates_without_manifest_agent_field(self):
        results = discovery_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            skip_live_codex=True,
        )
        by_name = {result.name: result for result in results}
        self.assertEqual(by_name["build-generated-package"].status, discovery_probe.PASS)
        self.assertEqual(
            by_name["generated-plugin-agent-shape"].status,
            discovery_probe.PASS,
        )
        self.assertIn(
            "unsupported agent fields",
            by_name["generated-plugin-agent-shape"].message,
        )
        self.assertEqual(
            by_name["codex-live-agent-discovery"].status,
            discovery_probe.UNAVAILABLE,
        )
        self.assertEqual(
            discovery_probe.exit_code(results, require_live_codex=False),
            0,
        )

    def test_manifest_agent_field_is_a_static_failure(self):
        plugin_dir = self.tmp / "plugin"
        (plugin_dir / ".codex-plugin").mkdir(parents=True)
        (plugin_dir / "agents").mkdir(parents=True)
        (plugin_dir / ".codex-plugin" / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "jig",
                    "version": "1.0.0",
                    "skills": "./skills/",
                    "agents": "./agents/",
                }
            )
        )
        for agent in discovery_probe.ROLE_AGENT_NAMES:
            (plugin_dir / "agents" / f"{agent}.toml").write_text(
                f'name = "{agent}"\n'
            )

        result = discovery_probe._validate_generated_agent_shape(plugin_dir)
        self.assertEqual(result.status, discovery_probe.FAIL)
        self.assertIn("unsupported plugin custom-agent field", result.message)

    def test_require_live_codex_turns_skip_into_exit_two(self):
        results = discovery_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            skip_live_codex=True,
        )
        self.assertEqual(
            discovery_probe.exit_code(results, require_live_codex=True),
            2,
        )


class CodexAgentDiscoveryLiveProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-agent-discovery-live-test-"))
        self.codex_bin = _fake_codex_bin(self.tmp)
        self.calls: list[list[str]] = []
        self.prompt_text = "jig:scaffold-init is visible; no custom agents here"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _runner(
        self,
        args,
        cwd,
        env,
        timeout,
    ) -> subprocess.CompletedProcess[str]:
        args = [str(arg) for arg in args]
        if args[0] != str(self.codex_bin):
            return discovery_probe._run_command(args, cwd, env, timeout)
        self.calls.append(args)
        codex_home = Path(env["CODEX_HOME"])
        command = args[1:]
        if command == ["--version"]:
            return _completed(args, stdout="codex-cli 9.9.9\n")
        if command[:3] == ["plugin", "marketplace", "add"]:
            return _completed(args, stdout=f"Added marketplace `jig` from {command[3]}.\n")
        if command == ["plugin", "add", "jig@jig"]:
            source = self.tmp / "work" / "codex-plugin" / "plugins" / "jig"
            installed = codex_home / "plugins" / "cache" / "jig" / "jig" / "1.10.0"
            if installed.exists():
                shutil.rmtree(installed)
            shutil.copytree(source, installed)
            return _completed(args, stdout=f"Installed plugin root: {installed}\n")
        if command == ["debug", "prompt-input", discovery_probe.DISCOVERY_PROMPT]:
            return _completed(args, stdout=_prompt_json(self.prompt_text))
        return _completed(args, returncode=99, stderr=f"unexpected command: {command}\n")

    def test_live_probe_records_absent_plugin_native_agent_discovery(self):
        results = discovery_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=self._runner,
        )
        by_name = {result.name: result for result in results}
        for name in (
            "codex-cli",
            "codex-marketplace-add",
            "codex-plugin-add",
            "codex-plugin-cache-agent-templates",
            "codex-plugin-agent-discovery",
        ):
            self.assertEqual(by_name[name].status, discovery_probe.PASS, by_name[name])
        self.assertIn(
            "not exposed as custom agents",
            by_name["codex-plugin-agent-discovery"].message,
        )
        called_commands = [call[1:] for call in self.calls]
        self.assertIn(
            ["plugin", "marketplace", "add", str(self.tmp / "work" / "codex-plugin")],
            called_commands,
        )
        self.assertIn(["plugin", "add", "jig@jig"], called_commands)
        self.assertIn(
            ["debug", "prompt-input", discovery_probe.DISCOVERY_PROMPT],
            called_commands,
        )

    def test_live_probe_can_report_plugin_native_agent_discovery_if_it_appears(self):
        self.prompt_text = "\n".join(discovery_probe.ROLE_AGENT_NAMES)
        results = discovery_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=self._runner,
        )
        result = [
            item for item in results
            if item.name == "codex-plugin-agent-discovery"
        ][0]
        self.assertEqual(result.status, discovery_probe.PASS)
        self.assertIn("plugin-native custom-agent discovery observed", result.message)
        self.assertIn("follow-up adapter slice", result.message)

    def test_live_probe_reports_partial_plugin_native_agent_discovery(self):
        self.prompt_text = discovery_probe.ROLE_AGENT_NAMES[0]
        results = discovery_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=self._runner,
        )
        result = [
            item for item in results
            if item.name == "codex-plugin-agent-discovery"
        ][0]
        self.assertEqual(result.status, discovery_probe.PASS)
        self.assertIn("plugin-native custom-agent discovery observed", result.message)
        self.assertIn("missing expected role(s)", result.message)
        self.assertIn("follow-up adapter slice", result.message)

    def test_missing_debug_prompt_surface_is_unavailable(self):
        def runner(args, cwd, env, timeout):
            args = [str(arg) for arg in args]
            if args[0] == str(self.codex_bin) and args[1:] == [
                "debug",
                "prompt-input",
                discovery_probe.DISCOVERY_PROMPT,
            ]:
                return _completed(args, returncode=2, stderr="unknown command debug prompt-input\n")
            return self._runner(args, cwd, env, timeout)

        results = discovery_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=runner,
        )
        result = [
            item for item in results
            if item.name == "codex-plugin-agent-discovery"
        ][0]
        self.assertEqual(result.status, discovery_probe.UNAVAILABLE)


class CodexAgentDiscoveryDocsTests(unittest.TestCase):
    def test_contributor_docs_document_agent_discovery_probe_and_current_contract(self):
        text = (REPO_ROOT / "docs" / "refinement-todo.md").read_text()
        self.assertIn("scripts/codex_agent_discovery_probe.py", text)
        self.assertIn("plugin-native custom-agent discovery observed", text)

    def test_architecture_records_no_plugin_native_agent_discovery(self):
        text = (REPO_ROOT / "docs" / "architecture.md").read_text()
        self.assertIn("Codex plugin agent-discovery spike", text)
        self.assertIn("codex_agent_discovery_probe.py", text)
        self.assertIn("did not expose those", text)
        self.assertIn("--install-codex-agents", text)

    def test_refinement_todo_names_future_trigger(self):
        text = (REPO_ROOT / "docs" / "refinement-todo.md").read_text()
        self.assertIn("rechecked by [slice 059-06]", text)
        self.assertIn("codex_agent_discovery_probe.py", text)
        self.assertIn("plugin-native custom-agent discovery observed", text)

    def test_slice_records_docs_cli_and_adapter_decision(self):
        text = (
            REPO_ROOT
            / "docs"
            / "specs"
            / "059-codex-port-polish"
            / "slice-06-codex-plugin-agent-discovery-spike.md"
        ).read_text()
        self.assertIn("codex-plugin-agent-discovery-spike", text)
        self.assertIn("Official Codex documentation was rechecked", text)
        self.assertIn("codex-cli 0.133.0", text)
        self.assertIn("--install-codex-agents", text)


if __name__ == "__main__":
    unittest.main()
