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

    def test_provider_missing_emits_one_actionable_non_blocking_recommendation(self):
        common = _write_fake_common(
            self.tmpdir,
            """
            from types import SimpleNamespace

            def activate(project_dir, host='unknown'):
                return SimpleNamespace(
                    provider='tokensave',
                    provider_profile='public',
                    action='recommend',
                    outcome='provider_missing',
                    recommendation=(
                        'No supported semantic index provider is installed. '
                        'Configure .jig/semantic-index.json.'
                    ),
                )
            """,
        )

        result = run_hook(self.project, common)
        second = run_hook(self.project, common)

        self.assertEqual(result.returncode, 0, result.stderr)
        out = parse_stdout(result)
        self.assertIn(".jig/semantic-index.json", out["additionalContext"])
        self.assertIsNone(parse_stdout(second))

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


class Bug040RepoScopedSuggestionTests(unittest.TestCase):
    """Bug 040: the suggestion is once per repository, not per checkout.

    Hosts that cut a fresh worktree per session (Copilot CLI) must not see the
    missing-provider suggestion again, and a committed explicit
    ``"auto_attach": false`` must silence it.
    """

    REAL_COMMON = REPO_ROOT / "skills" / "_common"

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-bug-040-"))
        self.repo = self.tmpdir / "repo"
        self.repo.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _git(self, *args, cwd=None):
        subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo,
            check=True,
            capture_output=True,
            text=True,
        )

    def _init_repo(self, state: dict):
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.repo / ".jig").mkdir()
        (self.repo / ".jig" / "semantic-index.json").write_text(json.dumps(state))
        self._git("add", ".jig/semantic-index.json")
        self._git("-c", "commit.gpgsign=false", "commit", "-q", "--no-verify", "-m", "opt-in")

    def _worktree(self, name: str) -> Path:
        path = self.tmpdir / name
        self._git("worktree", "add", "-q", str(path), "-b", name)
        return path

    def _run(self, project_dir: Path):
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        env["JIG_SEMANTIC_INDEX_COMMON_DIR"] = str(self.REAL_COMMON)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env.pop("JIG_SEMANTIC_INDEX_INTERNAL", None)
        return subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"session_id": "s", "hook_event_name": "SessionStart"}),
            capture_output=True,
            text=True,
            env=env,
        )

    def test_missing_provider_suggestion_not_repeated_in_fresh_worktree(self):
        self._init_repo({"auto_attach": True, "provider": "bug040-absent-provider"})

        first = self._run(self.repo)
        again = self._run(self.repo)
        fresh = self._run(self._worktree("session-2"))

        self.assertEqual(first.returncode, 0, first.stderr)
        msg = parse_stdout(first)["additionalContext"]
        self.assertIn("bug040-absent-provider", msg)
        self.assertIsNone(parse_stdout(again))
        self.assertIsNone(parse_stdout(fresh), "re-suggested in a fresh worktree")

    def test_committed_auto_attach_false_silences_missing_provider(self):
        self._init_repo({"auto_attach": False, "provider": "bug040-absent-provider"})

        primary = self._run(self.repo)
        fresh = self._run(self._worktree("session-2"))

        self.assertEqual(primary.returncode, 0, primary.stderr)
        self.assertIsNone(parse_stdout(primary))
        self.assertIsNone(parse_stdout(fresh))

    def test_missing_provider_text_points_install_outside_the_session(self):
        self._init_repo({"auto_attach": True, "provider": "bug040-absent-provider"})

        msg = parse_stdout(self._run(self.repo))["additionalContext"]

        self.assertIn("own shell", msg)
        self.assertIn('"auto_attach": false', msg)


if __name__ == "__main__":
    unittest.main()
