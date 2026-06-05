"""
Tests for scripts/codex_install_smoke.py — slice 059-03.

The live Codex CLI portion is exercised with an injected command runner so CI
does not need an actual Codex install to verify the contract. The script still
uses the real build_codex_plugin path and the real generated package when run
locally.
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

import codex_install_smoke  # noqa: E402
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


def _fake_codex_bin(tmp: Path) -> Path:
    path = tmp / "codex"
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return path


def _all_skill_prompt_json() -> str:
    names = "\n".join(f"- jig:{skill}: visible" for skill in install_contract.EXPECTED_SKILLS)
    return json.dumps(
        [
            {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": names}],
            }
        ]
    )


class CodexSmokeStaticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-codex-smoke-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_static_smoke_builds_package_and_installs_agents(self):
        results = codex_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            skip_live_codex=True,
        )
        by_name = {result.name: result for result in results}
        self.assertEqual(by_name["build-generated-package"].status, codex_install_smoke.PASS)
        self.assertEqual(by_name["generated-package"].status, codex_install_smoke.PASS)
        self.assertEqual(by_name["codex-agent-install"].status, codex_install_smoke.PASS)
        self.assertEqual(by_name["codex-live-surfaces"].status, codex_install_smoke.UNAVAILABLE)
        self.assertEqual(
            codex_install_smoke.exit_code(results, require_live_codex=False),
            0,
        )

    def test_missing_codex_cli_is_unavailable_not_silent_pass(self):
        results = codex_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.tmp / "missing-codex"),
        )
        cli = [result for result in results if result.name == "codex-cli"][0]
        self.assertEqual(cli.status, codex_install_smoke.UNAVAILABLE)
        self.assertIn("not found", cli.message)
        self.assertEqual(
            codex_install_smoke.exit_code(results, require_live_codex=False),
            0,
        )
        self.assertEqual(
            codex_install_smoke.exit_code(results, require_live_codex=True),
            2,
        )

        required_results = codex_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "required-work",
            codex_home=self.tmp / "required-codex-home",
            codex_bin=str(self.tmp / "missing-codex"),
            require_live_codex=True,
        )
        required_cli = [
            result for result in required_results if result.name == "codex-cli"
        ][0]
        self.assertEqual(required_cli.status, codex_install_smoke.UNAVAILABLE)
        self.assertEqual(
            codex_install_smoke.exit_code(
                required_results,
                require_live_codex=True,
            ),
            2,
        )


class CodexSmokeLiveProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-codex-live-test-"))
        self.codex_bin = _fake_codex_bin(self.tmp)
        self.calls: list[list[str]] = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _runner(
        self,
        args,
        cwd,
        env,
        timeout,
    ) -> subprocess.CompletedProcess[str]:
        args = list(args)
        if args[0] != str(self.codex_bin):
            return codex_install_smoke._run_command(args, cwd, env, timeout)
        self.calls.append(args)
        codex_home = Path(env["CODEX_HOME"])
        command = args[1:]
        if command == ["--version"]:
            return _completed(args, stdout="codex-cli 9.9.9\n")
        if command[:3] == ["plugin", "marketplace", "add"]:
            return _completed(args, stdout=f"Added marketplace `jig` from {command[3]}.\n")
        if command == ["plugin", "list"]:
            return _completed(
                args,
                stdout=(
                    "Marketplace `jig`\n"
                    "PLUGIN   STATUS              VERSION  PATH\n"
                    "jig@jig  installed, enabled  1.10.0   /tmp/plugins/jig\n"
                ),
            )
        if command == ["plugin", "add", "jig@jig"]:
            source = self.tmp / "work" / "codex-plugin" / "plugins" / "jig"
            installed = codex_home / "plugins" / "cache" / "jig" / "jig" / "1.10.0"
            if installed.exists():
                shutil.rmtree(installed)
            shutil.copytree(source, installed)
            config = codex_home / "config.toml"
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text('[plugins."jig@jig"]\nenabled = true\n')
            return _completed(args, stdout=f"Installed plugin root: {installed}\n")
        if command == ["debug", "prompt-input", codex_install_smoke._SKILL_VISIBILITY_PROMPT]:
            return _completed(args, stdout=_all_skill_prompt_json())
        if command == ["--help"]:
            return _completed(args, stdout="--dangerously-bypass-hook-trust\n")
        if command == ["features", "list"]:
            return _completed(args, stdout="hooks stable true\nplugin_hooks stable true\n")
        return _completed(args, returncode=99, stderr=f"unexpected command: {command}\n")

    def test_live_probe_exercises_marketplace_plugin_skill_hook_and_trust_surfaces(self):
        results = codex_install_smoke.run_smoke(
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
            "codex-hook-config",
            "codex-skill-visibility",
            "codex-hook-trust-state",
        ):
            self.assertEqual(by_name[name].status, codex_install_smoke.PASS, by_name[name])
        called_commands = [call[1:] for call in self.calls if call[0] == str(self.codex_bin)]
        self.assertIn(
            ["plugin", "marketplace", "add", str(self.tmp / "work" / "codex-plugin")],
            called_commands,
        )
        self.assertIn(["plugin", "add", "jig@jig"], called_commands)
        self.assertIn(
            ["debug", "prompt-input", codex_install_smoke._SKILL_VISIBILITY_PROMPT],
            called_commands,
        )

    def test_missing_debug_prompt_surface_is_reported_unavailable(self):
        def runner(args, cwd, env, timeout):
            args = list(args)
            if args[1:] == ["debug", "prompt-input", codex_install_smoke._SKILL_VISIBILITY_PROMPT]:
                return _completed(args, returncode=2, stderr="unknown command debug prompt-input\n")
            return self._runner(args, cwd, env, timeout)

        results = codex_install_smoke.run_smoke(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=runner,
        )
        skill = [result for result in results if result.name == "codex-skill-visibility"][0]
        self.assertEqual(skill.status, codex_install_smoke.UNAVAILABLE)

    def test_hook_trust_requires_distinct_hooks_feature(self):
        result = codex_install_smoke._validate_hook_trust_surface(
            "--dangerously-bypass-hook-trust\n",
            "plugin_hooks stable true\n",
            self.tmp / "codex-home",
        )
        self.assertEqual(result.status, codex_install_smoke.UNAVAILABLE)
        self.assertIn("hooks/plugin_hooks", result.message)

    def test_command_timeout_returns_structured_result(self):
        result = codex_install_smoke._run_command(
            [sys.executable, "-c", "import time; time.sleep(1)"],
            None,
            {},
            0.01,
        )
        self.assertEqual(result.returncode, 124)
        self.assertIn("timed out", result.stderr)


class CodexSmokeDocsTests(unittest.TestCase):
    def test_readme_documents_codex_smoke_command_and_isolation(self):
        text = (REPO_ROOT / "README.md").read_text()
        self.assertIn("scripts/codex_install_smoke.py", text)
        self.assertIn("JIG_CODEX_SMOKE_CODEX_HOME", text)
        self.assertIn("CODEX_HOME", text)

    def test_contributing_documents_codex_smoke_for_release_checks(self):
        text = (REPO_ROOT / "CONTRIBUTING.md").read_text()
        self.assertIn("python3 scripts/codex_install_smoke.py", text)
        self.assertIn("--require-live-codex", text)


if __name__ == "__main__":
    unittest.main()
