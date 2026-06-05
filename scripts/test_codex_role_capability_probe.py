"""
Tests for scripts/codex_role_capability_probe.py - slice 059-05.

The live Codex CLI portions use an injected command runner so CI can pin the
role-capability contract without requiring a local Codex install.
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

import codex_role_capability_probe as role_probe  # noqa: E402


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


def _prompt_json_with_roles() -> str:
    text = "\n".join(role_probe.ROLE_SANDBOX)
    return json.dumps(
        [
            {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": text}],
            }
        ]
    )


class CodexRoleStaticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-codex-role-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_static_probe_installs_and_validates_all_three_roles(self):
        results = role_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            skip_live_codex=True,
        )
        by_name = {result.name: result for result in results}
        self.assertEqual(by_name["codex-agent-roster"].status, role_probe.PASS)
        self.assertEqual(by_name["jig-implementer"].status, role_probe.PASS)
        self.assertIn("workspace-write", by_name["jig-implementer"].message)
        self.assertEqual(by_name["jig-reviewer"].status, role_probe.PASS)
        self.assertIn("read-only", by_name["jig-reviewer"].message)
        self.assertEqual(by_name["jig-architect"].status, role_probe.PASS)
        self.assertIn("read-only", by_name["jig-architect"].message)
        self.assertEqual(
            by_name["codex-live-role-surfaces"].status,
            role_probe.UNAVAILABLE,
        )
        self.assertEqual(
            role_probe.exit_code(results, require_live_codex=False),
            0,
        )

    def test_require_live_codex_turns_unavailable_into_exit_two(self):
        results = role_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            skip_live_codex=True,
        )
        self.assertEqual(
            role_probe.exit_code(results, require_live_codex=True),
            2,
        )


class CodexRoleLiveProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-codex-role-live-test-"))
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
        args = [str(arg) for arg in args]
        if args[0] != str(self.codex_bin):
            return role_probe._run_command(args, cwd, env, timeout)
        self.calls.append(args)
        command = args[1:]
        if command == ["--version"]:
            return _completed(args, stdout="codex-cli 9.9.9\n")
        if command[:4] == [
            "-C",
            str(self.tmp / "work" / "codex-role-project"),
            "debug",
            "prompt-input",
        ]:
            return _completed(args, stdout=_prompt_json_with_roles())
        if command[:5] == [
            "sandbox",
            "macos",
            "--permissions-profile",
            ":read-only",
            "-C",
        ]:
            return _completed(
                args,
                returncode=1,
                stderr="PermissionError: [Errno 1] Operation not permitted\n",
            )
        if command[:5] == [
            "sandbox",
            "macos",
            "--permissions-profile",
            ":workspace",
            "-C",
        ]:
            project = Path(command[5])
            (project / "allowed.txt").write_text("ok")
            return _completed(args)
        return _completed(args, returncode=99, stderr=f"unexpected command: {command}\n")

    def test_live_probe_records_cli_prompt_surface_and_sandbox_semantics(self):
        results = role_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=self._runner,
            platform_name="Darwin",
        )
        by_name = {result.name: result for result in results}
        self.assertEqual(by_name["codex-cli"].status, role_probe.PASS)
        self.assertEqual(
            by_name["codex-agent-prompt-surface"].status,
            role_probe.PASS,
        )
        self.assertEqual(
            by_name["codex-sandbox-read-only-write-block"].status,
            role_probe.PASS,
        )
        self.assertEqual(
            by_name["codex-sandbox-workspace-write"].status,
            role_probe.PASS,
        )
        called_commands = [call[1:] for call in self.calls]
        self.assertIn(["--version"], called_commands)
        self.assertTrue(
            any(command[:3] == ["sandbox", "macos", "--permissions-profile"]
                for command in called_commands)
        )

    def test_prompt_input_without_custom_agents_is_reported_unavailable(self):
        def runner(args, cwd, env, timeout):
            args = [str(arg) for arg in args]
            if args[0] == str(self.codex_bin) and args[1:5] == [
                "-C",
                str(self.tmp / "work" / "codex-role-project"),
                "debug",
                "prompt-input",
            ]:
                return _completed(
                    args,
                    stdout=json.dumps([{"type": "message", "content": []}]),
                )
            return self._runner(args, cwd, env, timeout)

        results = role_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=runner,
            platform_name="Darwin",
        )
        prompt = [
            result for result in results
            if result.name == "codex-agent-prompt-surface"
        ][0]
        self.assertEqual(prompt.status, role_probe.UNAVAILABLE)
        self.assertIn("did not expose custom-agent entries", prompt.message)

    def test_nested_sandbox_setup_failure_is_unavailable_not_failed(self):
        def runner(args, cwd, env, timeout):
            args = [str(arg) for arg in args]
            if args[0] == str(self.codex_bin) and args[1:5] == [
                "sandbox",
                "macos",
                "--permissions-profile",
                ":read-only",
            ]:
                return _completed(
                    args,
                    returncode=71,
                    stderr="sandbox-exec: sandbox_apply: Operation not permitted\n",
                )
            if args[0] == str(self.codex_bin) and args[1:5] == [
                "sandbox",
                "macos",
                "--permissions-profile",
                ":workspace",
            ]:
                return _completed(
                    args,
                    returncode=71,
                    stderr="sandbox-exec: sandbox_apply: Operation not permitted\n",
                )
            return self._runner(args, cwd, env, timeout)

        results = role_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=runner,
            platform_name="Darwin",
        )
        by_name = {result.name: result for result in results}
        self.assertEqual(
            by_name["codex-sandbox-read-only-write-block"].status,
            role_probe.UNAVAILABLE,
        )
        self.assertEqual(
            by_name["codex-sandbox-workspace-write"].status,
            role_probe.UNAVAILABLE,
        )
        self.assertEqual(
            role_probe.exit_code(results, require_live_codex=False),
            0,
        )

    def test_unsupported_sandbox_command_is_unavailable_not_denial(self):
        def runner(args, cwd, env, timeout):
            args = [str(arg) for arg in args]
            if args[0] == str(self.codex_bin) and args[1:5] in (
                ["sandbox", "macos", "--permissions-profile", ":read-only"],
                ["sandbox", "macos", "--permissions-profile", ":workspace"],
            ):
                return _completed(
                    args,
                    returncode=2,
                    stderr="unrecognized subcommand sandbox\n",
                )
            return self._runner(args, cwd, env, timeout)

        results = role_probe.run_probe(
            source_root=REPO_ROOT,
            work_root=self.tmp / "work",
            codex_home=self.tmp / "codex-home",
            codex_bin=str(self.codex_bin),
            runner=runner,
            platform_name="Darwin",
        )
        by_name = {result.name: result for result in results}
        self.assertEqual(
            by_name["codex-sandbox-read-only-write-block"].status,
            role_probe.UNAVAILABLE,
        )
        self.assertIn(
            "probe unavailable",
            by_name["codex-sandbox-read-only-write-block"].message,
        )
        self.assertEqual(
            by_name["codex-sandbox-workspace-write"].status,
            role_probe.UNAVAILABLE,
        )


class CodexRoleDocsTests(unittest.TestCase):
    def test_readme_documents_role_probe_command(self):
        text = (REPO_ROOT / "README.md").read_text()
        self.assertIn("scripts/codex_role_capability_probe.py", text)
        self.assertIn("jig-implementer", text)
        self.assertIn("jig-reviewer", text)
        self.assertIn("jig-architect", text)

    def test_architecture_records_role_sandbox_mapping(self):
        text = (REPO_ROOT / "docs" / "architecture.md").read_text()
        self.assertIn("Codex role capability dogfood", text)
        self.assertIn("workspace-write", text)
        self.assertIn("read-only", text)

    def test_role_capability_doc_names_interactive_fallback(self):
        text = (REPO_ROOT / "docs" / "codex-role-capability.md").read_text()
        self.assertIn("codex_role_capability_probe.py", text)
        self.assertIn("/agent", text)
        self.assertIn("noninteractive", text)


if __name__ == "__main__":
    unittest.main()
