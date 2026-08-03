"""Hook-integration (wrapper) smoke tests for
hooks/scripts/jig-git-freshness.sh (spec 103-01 / ADR-0048).

The bulk of the AC coverage lives in the testable helper's own suite,
hooks/scripts/lib/test_git_freshness.py. This file exercises the thin `.sh`
wrapper: stdin marshaling, `additionalContext` printing, the audit-log
write, opt-out, and malformed-input robustness — end to end via a real
subprocess invocation of the script.

Run from the repo root:
    python3 hooks/scripts/test_jig_git_freshness.py
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-git-freshness.sh"


def _git(args, cwd, check=True):
    return subprocess.run(
        ["git"] + args, cwd=str(cwd), capture_output=True, text=True, check=check,
    )


def _clone(remote: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git(["clone", "-q", str(remote), str(dest)], cwd=dest.parent)
    _git(["config", "user.email", "test@example.com"], dest)
    _git(["config", "user.name", "Test"], dest)
    return dest


def _commit(repo: Path, message: str = "commit") -> None:
    marker = repo / "f.txt"
    existing = marker.read_text() if marker.is_file() else ""
    marker.write_text(existing + message + "\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", message], repo)


def _bootstrap_origin(root: Path, branch: str = "main") -> Path:
    bare = root / "origin.git"
    bare.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q", "--bare", str(bare)], cwd=bare.parent)
    seed = _clone(bare, root / "seed")
    _git(["checkout", "-q", "-b", branch], seed)
    _commit(seed, "initial")
    _git(["push", "-q", "-u", "origin", branch], seed)
    _git(["symbolic-ref", "HEAD", f"refs/heads/{branch}"], bare)
    return bare


def run_hook(project_dir: Path, *, payload=None,
             env_overrides: dict = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env.pop("JIG_GIT_FRESHNESS", None)
    env.pop("JIG_GIT_FRESHNESS_TIMEOUT", None)
    if env_overrides:
        env.update(env_overrides)
    if payload is None:
        payload = {"hook_event_name": "SessionStart", "session_id": "test"}
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        ["bash", str(HOOK)], input=body, capture_output=True, text=True, env=env,
    )


def parse_or_none(result: subprocess.CompletedProcess):
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def read_growth_events(project_dir: Path) -> list:
    log = project_dir / ".claude" / "context-growth-read-events.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()
            if line.strip()]


class BehindBranchFiresTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-git-freshness-hook-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_behind_branch_emits_nudge_and_audit_event(self):
        bare = _bootstrap_origin(self.tmp)
        work = _clone(bare, self.tmp / "work")
        other = _clone(bare, self.tmp / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        result = run_hook(work)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = parse_or_none(result)
        self.assertIsNotNone(out, f"expected a nudge; stdout={result.stdout}")
        self.assertTrue(out.get("continue"))
        self.assertIn("origin/main", out["additionalContext"])

        events = [e for e in read_growth_events(work) if e.get("event") == "additional_context"]
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["source_hook"], "jig-git-freshness")
        self.assertEqual(event["kind"], "branch_behind_upstream")

    def test_up_to_date_branch_is_silent(self):
        bare = _bootstrap_origin(self.tmp)
        work = _clone(bare, self.tmp / "work")

        result = run_hook(work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(parse_or_none(result))
        self.assertEqual(result.stdout, "")


class RobustnessAndOptOutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-git-freshness-hook-rob-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_malformed_stdin_exits_zero_no_output(self):
        target = self.tmp / "plain"
        target.mkdir()
        result = run_hook(target, payload="not-json-at-all{{{")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_opt_out_is_silent(self):
        bare = _bootstrap_origin(self.tmp)
        work = _clone(bare, self.tmp / "work")
        other = _clone(bare, self.tmp / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        for value in ("0", "false", "off", "no"):
            result = run_hook(work, env_overrides={"JIG_GIT_FRESHNESS": value})
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "", f"value={value!r} should opt out")

    def test_missing_project_dir_still_exits_zero(self):
        # No CLAUDE_PROJECT_DIR: the wrapper defaults project_dir to ".", so the
        # subprocess MUST run in an isolated non-repo cwd — otherwise "." is the
        # real repo and the hook would fetch the live remote and write its audit
        # log into the source tree (test-isolation leak).
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        isolated = self.tmp / "no-project-dir"
        isolated.mkdir()
        result = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"hook_event_name": "SessionStart", "session_id": "t"}),
            capture_output=True, text=True, env=env, cwd=str(isolated),
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_not_a_git_work_tree_is_silent(self):
        target = self.tmp / "plain"
        target.mkdir()
        result = run_hook(target)
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(parse_or_none(result))

    def test_compact_source_is_silent(self):
        bare = _bootstrap_origin(self.tmp)
        work = _clone(bare, self.tmp / "work")
        other = _clone(bare, self.tmp / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        result = run_hook(work, payload={
            "hook_event_name": "SessionStart", "session_id": "s1",
            "source": "compact",
        })
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(parse_or_none(result))


if __name__ == "__main__":
    unittest.main()
