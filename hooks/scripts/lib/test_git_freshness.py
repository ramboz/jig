"""AC verification tests for spec 103-01 (SessionStart git-freshness nudge).

Run from the repo root:
    python3 -m unittest hooks/scripts/lib/test_git_freshness.py
or from this directory:
    python3 -m unittest test_git_freshness
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(HERE),):
    if p not in sys.path:
        sys.path.insert(0, p)

import git_freshness  # noqa: E402

_REAL_RUN = subprocess.run


# --------------------------------------------------------------------------- #
# git fixture helpers — real local repos, no network. A local-disk BARE
# "origin.git" remote lets `git fetch`/`push` run for real (fast, offline,
# and never hits `receive.denyCurrentBranch` since a bare repo has no
# checked-out branch) so the tests exercise actual git plumbing rather than
# a hand-rolled mock of every command.
# --------------------------------------------------------------------------- #
def _git(args, cwd, check=True):
    return subprocess.run(
        ["git"] + args, cwd=str(cwd), capture_output=True, text=True, check=check,
    )


def _init_bare(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q", "--bare", str(path)], cwd=path.parent)
    return path


def _init_repo(path: Path) -> Path:
    """A standalone (non-bare) repo with no remote — used for the
    nothing-resolves fixture only."""
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q", str(path)], cwd=path.parent)
    _git(["config", "user.email", "test@example.com"], path)
    _git(["config", "user.name", "Test"], path)
    return path


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
    """A bare `origin.git` seeded with one commit on `branch`, via a
    throwaway seed clone (all writes go through a real push, never a direct
    write to the bare repo). Sets the bare repo's HEAD symref to `branch` so
    later clones actually check it out (a fresh `--bare` init's HEAD may
    point at a differently-named default branch that doesn't exist yet —
    e.g. a `master`-only bootstrap under a `main`-default git config)."""
    bare = _init_bare(root / "origin.git")
    seed = _clone(bare, root / "seed")
    _git(["checkout", "-q", "-b", branch], seed)
    _commit(seed, "initial")
    _git(["push", "-q", "-u", "origin", branch], seed)
    _git(["symbolic-ref", "HEAD", f"refs/heads/{branch}"], bare)
    return bare


class GitFreshnessTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()


# --------------------------------------------------------------------------- #
# AC5 + anti-dead-gate — behind vs. up-to-date
# --------------------------------------------------------------------------- #
class BehindAndSilentTests(GitFreshnessTestBase):
    def test_behind_branch_nudges_with_count_and_base_and_review_command(self):
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _commit(other, "third")
        _git(["push", "-q", "origin", "main"], other)

        nudge = git_freshness.evaluate({}, work)
        self.assertIsNotNone(nudge)
        self.assertIn("2", nudge)
        self.assertIn("origin/main", nudge)
        self.assertIn("git log HEAD..origin/main --oneline", nudge)
        self.assertIn("sync", nudge.lower())
        self.assertIn("stale", nudge.lower())

    def test_anti_dead_gate_up_to_date_branch_is_silent(self):
        """A dead gate is also silent — this pins the positive case above
        against it."""
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")

        nudge = git_freshness.evaluate({}, work)
        self.assertIsNone(nudge)


# --------------------------------------------------------------------------- #
# AC3 — the smart-target resolution rule (load-bearing)
# --------------------------------------------------------------------------- #
class TargetResolutionTests(GitFreshnessTestBase):
    def test_own_remote_guard_regression_jig_case(self):
        """A pushed task branch whose @{upstream} is origin/<branch> (itself
        0 behind its own remote) but whose origin/main base has advanced N
        commits must nudge against origin/main. A rule preferring
        @{upstream} would go silent here — this is the #105-shaped case."""
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        _git(["checkout", "-q", "-b", "task/foo"], work)
        _commit(work, "task work")
        _git(["push", "-q", "-u", "origin", "task/foo"], work)

        # Advance origin/main underneath the task branch via a second clone.
        other = _clone(bare, self.root / "other")
        _commit(other, "main advances 1")
        _commit(other, "main advances 2")
        _commit(other, "main advances 3")
        _git(["push", "-q", "origin", "main"], other)

        nudge = git_freshness.evaluate({}, work)
        self.assertIsNotNone(
            nudge, "own-remote guard must fall through to origin/main")
        self.assertIn("origin/main", nudge)
        self.assertIn("3", nudge)

    def test_non_own_upstream_wins_git_flow_case(self):
        """A branch whose @{upstream} is origin/develop (not its own remote)
        and is behind it, while origin/main also resolves and is NOT
        behind, must nudge against origin/develop — not origin/main."""
        bare = _bootstrap_origin(self.root, branch="main")
        seed_develop = _clone(bare, self.root / "seed-develop")
        _git(["checkout", "-q", "-b", "develop"], seed_develop)
        _git(["push", "-q", "-u", "origin", "develop"], seed_develop)

        work = _clone(bare, self.root / "work")
        _git(["checkout", "-q", "-b", "feature/x", "origin/develop"], work)
        # Pin the upstream explicitly rather than relying on git's default
        # branch.autoSetupMerge (a contributor with it disabled would otherwise
        # get no @{upstream} and the fixture would silently degrade).
        _git(["branch", "--set-upstream-to=origin/develop", "feature/x"], work)

        other = _clone(bare, self.root / "other")
        _git(["checkout", "-q", "develop"], other)
        _commit(other, "develop advances")
        _git(["push", "-q", "origin", "develop"], other)
        # origin/main is untouched — behind count against it would be 0.

        nudge = git_freshness.evaluate({}, work)
        self.assertIsNotNone(nudge)
        self.assertIn("origin/develop", nudge)
        self.assertNotIn("origin/main", nudge)

    def test_not_a_git_work_tree_is_silent(self):
        plain = self.root / "plain"
        plain.mkdir()
        nudge = git_freshness.evaluate({}, plain)
        self.assertIsNone(nudge)

    def test_nothing_resolves_is_silent(self):
        """A repo with no remote at all: no @{upstream}, no origin/main,
        no origin/master."""
        lone = _init_repo(self.root / "lone")
        _commit(lone, "solo")
        nudge = git_freshness.evaluate({}, lone)
        self.assertIsNone(nudge)

    def test_resolution_precedence_falls_back_to_origin_master(self):
        """No non-own upstream, no origin/main → falls to origin/master."""
        bare = _bootstrap_origin(self.root, branch="master")
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "master"], other)

        nudge = git_freshness.evaluate({}, work)
        self.assertIsNotNone(nudge)
        self.assertIn("origin/master", nudge)

    def test_resolution_precedence_prefers_origin_main_over_master(self):
        bare = _bootstrap_origin(self.root, branch="main")
        seed_master = _clone(bare, self.root / "seed-master")
        _git(["checkout", "-q", "-b", "master"], seed_master)
        _git(["push", "-q", "-u", "origin", "master"], seed_master)

        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "main advances")
        _git(["push", "-q", "origin", "main"], other)

        nudge = git_freshness.evaluate({}, work)
        self.assertIsNotNone(nudge)
        self.assertIn("origin/main", nudge)


# --------------------------------------------------------------------------- #
# AC4 — always fetch, timeout-guarded, best-effort
# --------------------------------------------------------------------------- #
class FetchTests(GitFreshnessTestBase):
    def test_fetch_is_attempted_with_configured_timeout(self):
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        calls = []

        def recording(args, **kwargs):
            calls.append((args, kwargs))
            return _REAL_RUN(args, **kwargs)

        with patch.object(git_freshness.subprocess, "run", side_effect=recording):
            git_freshness.evaluate({}, work)

        self.assertTrue(calls, "expected at least one git subprocess call")
        fetch_calls = [c for c in calls if c[0][:2] == ["git", "fetch"]]
        self.assertTrue(fetch_calls, "expected a git fetch call")
        for _, kwargs in calls:
            self.assertIn("timeout", kwargs,
                          "every git subprocess.run must set timeout")

    def test_fetch_timeout_or_failure_falls_through_to_last_known_ref(self):
        """A failed/timed-out fetch must not error — the hook still computes
        `behind` against the last-known (already-fetched) ref and nudges."""
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        # Establish a real "last-known" local origin/main ref in work BEFORE
        # the fetch that will be made to fail below.
        _git(["fetch", "-q", "origin", "main"], work)

        # Advance origin AGAIN — work never re-fetches successfully, so its
        # local origin/main ref stays at "second" (stale but real).
        _commit(other, "third")
        _git(["push", "-q", "origin", "main"], other)

        def failing_fetch(args, **kwargs):
            if args[:2] == ["git", "fetch"]:
                raise subprocess.TimeoutExpired(cmd="git fetch", timeout=5)
            return _REAL_RUN(args, **kwargs)

        with patch.object(git_freshness.subprocess, "run",
                          side_effect=failing_fetch):
            nudge = git_freshness.evaluate({}, work)

        self.assertIsNotNone(
            nudge, "a failed fetch must still nudge from the last-known ref")
        # Only "second" is visible via the last-known ref — "third" never
        # made it into work's local origin/main since the fetch failed.
        self.assertIn("1", nudge)
        self.assertIn("origin/main", nudge)

    def test_git_freshness_timeout_out_of_range_or_non_numeric_falls_back(self):
        for raw in ("not-a-number", "-5", "0", ""):
            self.assertEqual(
                git_freshness._resolve_timeout({"JIG_GIT_FRESHNESS_TIMEOUT": raw}),
                git_freshness._DEFAULT_TIMEOUT,
                f"raw={raw!r} should fall back to default",
            )
        self.assertEqual(
            git_freshness._resolve_timeout({}), git_freshness._DEFAULT_TIMEOUT)
        self.assertEqual(
            git_freshness._resolve_timeout({"JIG_GIT_FRESHNESS_TIMEOUT": "2"}), 2.0)

    def test_git_freshness_timeout_is_clamped_below_hook_budget(self):
        # AC4 invariant: the subprocess timeout must stay strictly under the
        # 10s hook-level timeout. An oversized override is clamped, not obeyed.
        self.assertEqual(
            git_freshness._resolve_timeout({"JIG_GIT_FRESHNESS_TIMEOUT": "999"}),
            git_freshness._MAX_TIMEOUT,
        )
        self.assertLess(git_freshness._MAX_TIMEOUT, 10.0)


# --------------------------------------------------------------------------- #
# AC7 — compact-source skip
# --------------------------------------------------------------------------- #
class CompactSourceTests(GitFreshnessTestBase):
    def test_compact_source_skips_fetch_and_stays_silent(self):
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        def guard_no_calls(*args, **kwargs):
            raise AssertionError("no subprocess call should happen on compact")

        with patch.object(git_freshness.subprocess, "run",
                          side_effect=guard_no_calls):
            nudge = git_freshness.evaluate({"source": "compact"}, work)

        self.assertIsNone(nudge)

    def test_absent_source_runs_normally(self):
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        nudge = git_freshness.evaluate({}, work)
        self.assertIsNotNone(nudge)

    def test_other_source_runs_normally(self):
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        nudge = git_freshness.evaluate({"source": "startup"}, work)
        self.assertIsNotNone(nudge)


# --------------------------------------------------------------------------- #
# AC8 — opt-out
# --------------------------------------------------------------------------- #
class OptOutTests(GitFreshnessTestBase):
    def test_opt_out_values_are_silent(self):
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        for value in ("0", "false", "off", "no", "FALSE", "Off"):
            nudge = git_freshness.evaluate(
                {}, work, env={"JIG_GIT_FRESHNESS": value})
            self.assertIsNone(nudge, f"value={value!r} should opt out")

    def test_non_disable_value_still_runs(self):
        bare = _bootstrap_origin(self.root)
        work = _clone(bare, self.root / "work")
        other = _clone(bare, self.root / "other")
        _commit(other, "second")
        _git(["push", "-q", "origin", "main"], other)

        nudge = git_freshness.evaluate({}, work, env={"JIG_GIT_FRESHNESS": "1"})
        self.assertIsNotNone(nudge)


# --------------------------------------------------------------------------- #
# AC6 — fail-open on malformed input
# --------------------------------------------------------------------------- #
class RobustnessTests(GitFreshnessTestBase):
    def test_non_dict_payload_is_silent(self):
        self.assertIsNone(git_freshness.evaluate(None, self.root))
        self.assertIsNone(git_freshness.evaluate("not-a-dict", self.root))
        self.assertIsNone(git_freshness.evaluate([], self.root))

    def test_missing_fields_against_a_non_repo_is_silent(self):
        plain = self.root / "plain"
        plain.mkdir()
        self.assertIsNone(git_freshness.evaluate({}, plain))


if __name__ == "__main__":
    unittest.main()
