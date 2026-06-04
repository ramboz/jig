"""Tests for the shared team-signal module (slice 050-02).

`skills/_common/team_signal.py` is the single home (ADR-0002 rule-of-three:
scaffold-init / memory-sync / spec-workflow) for the team-context detection
logic: the contributor count, the >= 2 threshold, the `.jig/no-people-md`
opt-out marker contract, and the composite `team_context_drift` predicate
shared by memory-sync's nudge and `workflow.py stale`.

Run from the repo root:
    python3 skills/_common/test_team_signal.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills"))

from _common import team_signal  # noqa: E402


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


class MarkerContractTests(unittest.TestCase):
    """The `.jig/no-people-md` opt-out marker contract lives here (moved
    from scaffold.py per the rule-of-three extraction)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-ts-marker-")
        self.target = Path(self.tmpdir) / "proj"
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_relpath_constant(self):
        self.assertEqual(team_signal.NO_PEOPLE_MD_RELPATH, (".jig", "no-people-md"))

    def test_marker_path_resolves_under_target(self):
        self.assertEqual(
            team_signal.no_people_md_marker_path(self.target),
            self.target / ".jig" / "no-people-md",
        )

    def test_write_marker_creates_file_idempotently(self):
        p = team_signal.write_no_people_md_marker(self.target)
        self.assertTrue(p.exists())
        self.assertEqual(p, self.target / ".jig" / "no-people-md")
        # Idempotent — a second write does not raise and leaves it present.
        team_signal.write_no_people_md_marker(self.target)
        self.assertTrue(p.exists())

    def test_people_md_path(self):
        self.assertEqual(
            team_signal.people_md_path(self.target),
            self.target / "docs" / "memory" / "people.md",
        )


class ThresholdTests(unittest.TestCase):
    """The >= 2 threshold lives in exactly one place."""

    def test_threshold_is_two(self):
        self.assertEqual(team_signal.TEAM_THRESHOLD, 2)


@unittest.skipUnless(_git_available(), "git not available")
class CountAndSignalTests(unittest.TestCase):
    """`count_team_contributors` (int) + `team_signal_fires` (bool) agree on
    the threshold across the fixture matrix; behavior is preserved verbatim
    from the scaffold.py original (mailmap, monorepo guard, fail-soft)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-ts-count-")
        self.target = Path(self.tmpdir) / "proj"
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _git(self, *args, env_extra=None):
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["git", "-C", str(self.target), *args],
            capture_output=True, text=True, env=env, check=True,
        )

    def _commit_as(self, name, email, filename):
        (self.target / filename).write_text("seed")
        self._git("add", filename)
        env = {
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        }
        self._git("commit", "-m", f"add {filename}", env_extra=env)

    def _assert_parity(self, expected):
        count = team_signal.count_team_contributors(self.target)
        self.assertEqual(count, expected)
        self.assertEqual(team_signal.team_signal_fires(self.target),
                         count >= team_signal.TEAM_THRESHOLD)

    def test_solo(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Alice", "alice@example.com", "b.txt")
        self._assert_parity(1)

    def test_team_2(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Bob", "bob@example.com", "b.txt")
        self._assert_parity(2)

    def test_mailmap_coalesced(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@work.com", "a.txt")
        self._commit_as("Alice", "alice@personal.com", "b.txt")
        (self.target / ".mailmap").write_text(
            "Alice <alice@work.com> <alice@personal.com>\n"
        )
        self._assert_parity(1)

    def test_monorepo_parent_guarded_to_zero(self):
        parent = Path(self.tmpdir)
        env = os.environ.copy()
        subprocess.run(["git", "-C", str(parent), "init", "-q"],
                       capture_output=True, env=env, check=True)
        for name, email, fn in [("Alice", "alice@x.com", "pa.txt"),
                                 ("Bob", "bob@x.com", "pb.txt")]:
            (parent / fn).write_text("x")
            subprocess.run(["git", "-C", str(parent), "add", fn],
                           capture_output=True, env=env, check=True)
            env_extra = {
                **env,
                "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
                "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
            }
            subprocess.run(["git", "-C", str(parent), "commit", "-q", "-m", fn],
                           capture_output=True, env=env_extra, check=True)
        # self.target is a subdir of parent (not its own repo root) → 0.
        self._assert_parity(0)

    def test_non_git_fail_soft(self):
        self._assert_parity(0)


@unittest.skipUnless(_git_available(), "git not available")
class TeamContextDriftTests(unittest.TestCase):
    """`team_context_drift(target)` returns the contributor count N iff the
    signal fires AND people.md is absent AND the opt-out marker is absent;
    None otherwise. This is the shared decision used by memory team-check
    and `workflow.py stale`."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-ts-drift-")
        self.target = Path(self.tmpdir) / "proj"
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _git(self, *args, env_extra=None):
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["git", "-C", str(self.target), *args],
            capture_output=True, text=True, env=env, check=True,
        )

    def _commit_as(self, name, email, filename):
        (self.target / filename).write_text("seed")
        self._git("add", filename)
        env = {
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        }
        self._git("commit", "-m", f"add {filename}", env_extra=env)

    def _make_team(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Bob", "bob@example.com", "b.txt")

    def test_drift_fires_returns_count(self):
        self._make_team()
        self.assertEqual(team_signal.team_context_drift(self.target), 2)

    def test_no_drift_when_people_md_present(self):
        self._make_team()
        people = team_signal.people_md_path(self.target)
        people.parent.mkdir(parents=True, exist_ok=True)
        people.write_text("# People\n")
        self.assertIsNone(team_signal.team_context_drift(self.target))

    def test_no_drift_when_marker_present(self):
        self._make_team()
        team_signal.write_no_people_md_marker(self.target)
        self.assertIsNone(team_signal.team_context_drift(self.target))

    def test_no_drift_on_solo(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self.assertIsNone(team_signal.team_context_drift(self.target))


if __name__ == "__main__":
    unittest.main()
