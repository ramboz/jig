"""Hook-integration tests for hooks/scripts/jig-semantic-index.sh.

Run from the repo root:
    python3 hooks/scripts/test_jig_semantic_index.py
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-semantic-index.sh"


def _write_fake_common(base: Path, body: str) -> Path:
    common = base / "common"
    common.mkdir()
    (common / "semantic_index.py").write_text(textwrap.dedent(body))
    return common


def run_hook(project_dir: Path, common_dir: Path, *, payload: dict | None = None):
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["JIG_SEMANTIC_INDEX_COMMON_DIR"] = str(common_dir)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    payload = payload or {"session_id": "sess-080", "hook_event_name": "SessionStart"}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def parse_stdout(result: subprocess.CompletedProcess):
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


class SemanticIndexHookTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-080-02-"))
        self.project = self.tmpdir / "project"
        self.project.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_provider_missing_is_silent_and_non_blocking(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            from types import SimpleNamespace

            def activate(project_dir, host='unknown'):
                return SimpleNamespace(
                    provider='tokensave',
                    provider_profile='public',
                    action='detect',
                    outcome='provider_missing',
                    recommendation=None,
                )
            """,
        )

        result = run_hook(self.project, common)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(parse_stdout(result))

    def test_public_recommendation_emits_once(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            from types import SimpleNamespace

            def activate(project_dir, host='unknown'):
                return SimpleNamespace(
                    provider='tokensave',
                    provider_profile='public',
                    action='recommend',
                    outcome='not_opted_in',
                    recommendation=(
                        'Semantic index provider tokensave is available. '
                        'Opt in via .jig/semantic-index.json.'
                    ),
                )
            """,
        )

        first = run_hook(self.project, common)
        second = run_hook(self.project, common)

        self.assertEqual(first.returncode, 0, first.stderr)
        out = parse_stdout(first)
        self.assertIs(out.get("continue"), True)
        self.assertIn(".jig/semantic-index.json", out.get("additionalContext", ""))
        self.assertIsNone(parse_stdout(second))

    def test_internal_overlay_recommendation_stays_silent(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            from types import SimpleNamespace

            def activate(project_dir, host='unknown'):
                return SimpleNamespace(
                    provider='scout',
                    provider_profile='internal-overlay',
                    action='recommend',
                    outcome='not_opted_in',
                    recommendation='Scout is available.',
                )
            """,
        )

        result = run_hook(self.project, common)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(parse_stdout(result))

    def test_opted_in_fallback_warns_compactly(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            from types import SimpleNamespace

            def activate(project_dir, host='unknown'):
                return SimpleNamespace(
                    provider='tokensave',
                    provider_profile='public',
                    action='fallback',
                    outcome='not_ready',
                    recommendation=None,
                )
            """,
        )

        result = run_hook(self.project, common)

        self.assertEqual(result.returncode, 0, result.stderr)
        out = parse_stdout(result)
        self.assertIs(out.get("continue"), True)
        msg = out.get("additionalContext", "")
        self.assertIn("tokensave", msg)
        self.assertIn("fallback", msg)

    def test_opted_in_ready_is_silent_but_calls_claude_activation(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            import json
            from pathlib import Path
            from types import SimpleNamespace

            def activate(project_dir, host='unknown'):
                Path(project_dir, '.jig').mkdir(exist_ok=True)
                Path(project_dir, '.jig', 'activation-call.json').write_text(
                    json.dumps({'host': host, 'project_dir': str(project_dir)})
                )
                return SimpleNamespace(
                    provider='tokensave',
                    provider_profile='public',
                    action='ready',
                    outcome='ready',
                    recommendation=None,
                )
            """,
        )

        result = run_hook(self.project, common)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(parse_stdout(result))
        call = json.loads((self.project / ".jig" / "activation-call.json").read_text())
        self.assertEqual(call["host"], "claude")
        self.assertEqual(call["project_dir"], str(self.project))

    def test_opted_in_attach_started_is_silent(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            from types import SimpleNamespace

            def activate(project_dir, host='unknown'):
                return SimpleNamespace(
                    provider='tokensave',
                    provider_profile='public',
                    action='attach',
                    outcome='attach_started',
                    recommendation=None,
                )
            """,
        )

        result = run_hook(self.project, common)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(parse_stdout(result))

    def test_malformed_payload_still_exits_zero(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            from pathlib import Path

            def activate(project_dir, host='unknown'):
                Path(project_dir, '.jig').mkdir(exist_ok=True)
                Path(project_dir, '.jig', 'unexpected-call').write_text('called')
                return None
            """,
        )
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(self.project)
        env["JIG_SEMANTIC_INDEX_COMMON_DIR"] = str(common)

        result = subprocess.run(
            ["bash", str(HOOK)],
            input="not-json",
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.project / ".jig" / "unexpected-call").exists())

    def test_hook_registration_timeout_covers_bounded_activation_budget(self):
        hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())["hooks"]
        semantic_hook = None
        for event_groups in hooks.values():
            for group in event_groups:
                for hook in group.get("hooks", []):
                    if hook.get("command", "").endswith("/jig-semantic-index.sh"):
                        semantic_hook = hook
                        break

        self.assertIsNotNone(semantic_hook)
        self.assertGreaterEqual(semantic_hook.get("timeout", 0), 25)


if __name__ == "__main__":
    unittest.main()
