"""Hook-integration tests for hooks/scripts/jig-project-orient.sh."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-project-orient.sh"


class ProjectOrientHookTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-hook-orient-"))
        self.project = self.tmpdir / "project"
        spec_dir = self.project / "docs" / "specs" / "002-first"
        spec_dir.mkdir(parents=True)
        (self.project / "scaffold.json").write_text("{}\n")
        (spec_dir / "spec.md").write_text("---\nstatus: DRAFT\n---\n")
        (spec_dir / "slice-01-start.md").write_text(
            "---\nstatus: DRAFT\ndependencies: []\n---\n\n"
            "## Slice 002-01 — start\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, payload, *, hook=HOOK, unset_env=(), **extra_env):
        env = os.environ.copy()
        for name in unset_env:
            env.pop(name, None)
        env["CLAUDE_PROJECT_DIR"] = str(self.project)
        env.update(extra_env)
        return subprocess.run(
            ["bash", str(hook)],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )

    def test_sessionstart_injects_exact_orientation_headline(self):
        result = self._run({"hook_event_name": "SessionStart", "session_id": "s1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["continue"])
        self.assertEqual(
            payload["additionalContext"],
            "jig hint: Scaffolded jig project · active specs: 002 DRAFT · focus: 002-01 DRAFT",
        )

    def test_non_sessionstart_malformed_and_opt_out_are_silent(self):
        cases = [
            self._run({"hook_event_name": "UserPromptSubmit"}),
            self._run("not-json"),
            self._run(
                {"hook_event_name": "SessionStart"},
                JIG_PROJECT_ORIENT="0",
            ),
        ]
        for result in cases:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_orientation_failure_is_silent_and_non_blocking(self):
        isolated_hook = self.tmpdir / "isolated" / "hooks" / "scripts" / HOOK.name
        isolated_hook.parent.mkdir(parents=True)
        import shutil
        shutil.copy2(HOOK, isolated_hook)
        result = self._run(
            {"hook_event_name": "SessionStart"},
            hook=isolated_hook,
            unset_env=("CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT", "CODEX_HOME"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_registered_once_on_sessionstart(self):
        hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())["hooks"]
        commands = [
            hook.get("command", "")
            for group in hooks["SessionStart"]
            for hook in group.get("hooks", [])
        ]
        self.assertEqual(
            sum(command.endswith("/jig-project-orient.sh") for command in commands),
            1,
        )


if __name__ == "__main__":
    unittest.main()
