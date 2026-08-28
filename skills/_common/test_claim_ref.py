"""Tests for `_common/claim_ref.py` — the CAS-ref claim reservation
primitive (ADR-0058 Class B / spec 112-05).

Real git repos (bare + clone, mirroring `test_reservation.py`) for the
local CAS, the simultaneous-create race, and the remote push behaviors —
this primitive's whole point is atomic ref-creation semantics, which a
mocked subprocess can't exercise honestly for the race case. Per the task
instructions, no real claim ref is ever pushed to the actual `origin`
remote — every fixture here is a local bare repo standing in for it.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import claim_ref as CR  # noqa: E402


def _run(argv, cwd):
    subprocess.run(argv, cwd=str(cwd), check=True,
                   capture_output=True, text=True)


def _capture(argv, cwd):
    """Like `_run`, but returns `(rc, stdout)` without asserting success —
    for read-only probes (`for-each-ref` / `ls-remote`) where a non-zero rc
    or empty output is itself part of what a test checks."""
    result = subprocess.run(argv, cwd=str(cwd), check=False,
                            capture_output=True, text=True)
    return result.returncode, result.stdout


def _init_repo(root):
    _run(["git", "init", "-q", "-b", "main", str(root)], root)
    _run(["git", "config", "user.email", "t@t.t"], root)
    _run(["git", "config", "user.name", "t"], root)
    (root / "README.md").write_text("x\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-qm", "init"], root)


def _init_bare_remote(bare_dir):
    """`git init --bare` PLUS resetting `core.hookspath` to the repo-local
    default — a global `core.hookspath` override (e.g. a developer's own
    dotfiles-managed hooks dir) would otherwise silently shadow the
    fixture's own `hooks/pre-receive`, so the fallback test would see the
    push succeed instead of being rejected by the fixture's hook."""
    _run(["git", "init", "--bare", "-q", str(bare_dir)], bare_dir.parent)
    _run(["git", "config", "core.hookspath", "hooks"], bare_dir)


def _init_clone(bare_dir, work_dir, *, parent):
    _run(["git", "clone", "-q", str(bare_dir), str(work_dir)], parent)
    _run(["git", "config", "user.email", "t@t.t"], work_dir)
    _run(["git", "config", "user.name", "t"], work_dir)


class ClaimRefNamingTests(unittest.TestCase):
    def test_claim_ref_name(self):
        self.assertEqual(CR.claim_ref_name("200-01"), "refs/claims/200-01")

    def test_reservation_branch_name(self):
        self.assertEqual(
            CR.reservation_branch_name("200-01"), "reserve/claim-200-01")


class CreateLocalClaimTests(unittest.TestCase):
    """AC1 (reserve) / AC5 (simultaneous-create race) / A2 (spike): the
    local CAS ref is created atomically and a second create against the
    SAME ref store loses cleanly."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_create_wins(self):
        won, detail = CR.create_local_claim("200-01", self.root)
        self.assertTrue(won)
        self.assertEqual(detail, "")
        _rc, out = _capture(
            ["git", "for-each-ref", "refs/claims/"], self.root)
        self.assertIn("refs/claims/200-01", out)

    def test_simultaneous_create_race_exactly_one_winner(self):
        # AC5 — two callers racing to create the SAME claim ref: exactly
        # one wins, the other is told (False, not an exception).
        won1, _ = CR.create_local_claim("200-01", self.root)
        won2, detail2 = CR.create_local_claim("200-01", self.root)
        self.assertTrue(won1)
        self.assertFalse(won2)
        self.assertIn("already exists", detail2.lower())

    def test_create_is_visible_from_a_linked_worktree(self):
        # A2 (spike 112-04, verified) — linked worktrees share the ref
        # store, so a claim created in one is visible from a sibling
        # WITHOUT a push.
        won, _ = CR.create_local_claim("200-01", self.root)
        self.assertTrue(won)
        wt = self.root / "wt"
        _run(["git", "worktree", "add", "-q", "--detach", str(wt), "main"],
             self.root)
        _rc, out = _capture(["git", "for-each-ref", "refs/claims/"], wt)
        self.assertIn("refs/claims/200-01", out)
        # A second create attempt from the SIBLING worktree also loses.
        won2, _ = CR.create_local_claim("200-01", wt)
        self.assertFalse(won2)

    def test_unreadable_repo_is_unknown_not_a_collision(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            won, detail = CR.create_local_claim("200-01", Path(not_a_repo))
        self.assertIsNone(won)
        self.assertNotEqual(detail, "")


class ReleaseLocalClaimTests(unittest.TestCase):
    """AC4 — stale-claim release: `--release` clears the CAS ref, so a
    crashed session's claim is not a chronic false-halt."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_release_clears_the_ref(self):
        CR.create_local_claim("200-01", self.root)
        CR.release_local_claim("200-01", self.root)
        _rc, out = _capture(
            ["git", "for-each-ref", "refs/claims/"], self.root)
        self.assertNotIn("refs/claims/200-01", out)

    def test_a_fresh_create_succeeds_after_release(self):
        # The stale-claim escape: release, then re-claim cleanly.
        CR.create_local_claim("200-01", self.root)
        CR.release_local_claim("200-01", self.root)
        won, _ = CR.create_local_claim("200-01", self.root)
        self.assertTrue(won)

    def test_release_of_an_absent_ref_is_a_silent_no_op(self):
        # Idempotent — never raises.
        CR.release_local_claim("200-99", self.root)


class PushClaimTests(unittest.TestCase):
    """AC1 (cross-machine reserve) / AC5 (remote race) / AC6 (offline) /
    the custom-ref-rejected fallback — a local BARE repo stands in for
    `origin`; no real claim ref is ever pushed to the actual project
    remote."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.remote = self.root / "remote.git"
        _init_bare_remote(self.remote)
        self.work = self.root / "work"
        _init_clone(self.remote, self.work, parent=self.root)
        (self.work / "README.md").write_text("x\n")
        _run(["git", "add", "-A"], self.work)
        _run(["git", "commit", "-qm", "init"], self.work)
        _run(["git", "push", "-q", "origin", "HEAD:main"], self.work)

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_push_reserves_the_claim_ref_on_origin(self):
        status, detail = CR.push_claim("200-01", self.work)
        self.assertEqual(status, "pushed")
        self.assertEqual(detail, "")
        _rc, out = _capture(
            ["git", "ls-remote", str(self.remote), "refs/claims/200-01"],
            self.work)
        self.assertIn("refs/claims/200-01", out)

    def test_second_push_from_a_different_clone_is_a_race(self):
        # AC5 — cross-machine simultaneous create: the SECOND pusher (with
        # a genuinely different commit — pushing the identical SHA already
        # on the ref is a git no-op regardless of the lease) is rejected
        # (lease expected the ref absent), and told, not hung.
        status1, _ = CR.push_claim("200-01", self.work)
        self.assertEqual(status1, "pushed")

        clone2 = self.root / "clone2"
        _init_clone(self.remote, clone2, parent=self.root)
        (clone2 / "clone2-only.txt").write_text("y\n")
        _run(["git", "add", "-A"], clone2)
        _run(["git", "commit", "-qm", "clone2 commit"], clone2)
        status2, detail2 = CR.push_claim("200-01", clone2)
        self.assertEqual(status2, "race")
        self.assertNotEqual(detail2, "")

    def test_offline_remote_degrades_without_hanging(self):
        # AC6 — an unreachable origin degrades gracefully (no exception,
        # no hang; the test itself completing IS the no-hang assertion).
        _run(["git", "remote", "set-url", "origin",
              str(self.root / "does-not-exist.git")], self.work)
        status, detail = CR.push_claim("200-01", self.work)
        self.assertEqual(status, "offline")
        self.assertNotEqual(detail, "")

    def test_custom_ref_namespace_rejected_falls_back_to_reservation_branch(self):
        # The ADR-0053-shaped fallback: a host that classifies the refusal
        # as "protection" (a pre-receive hook standing in for a real
        # org policy, mirroring test_reservation.py's captured GH006/GH013
        # fixtures) routes to a plain `refs/heads/reserve/claim-<N>` push,
        # which the fixture's own hook does not block.
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text(
            "#!/bin/sh\n"
            "while read old new ref; do\n"
            '  case "$ref" in\n'
            "    refs/claims/*)\n"
            '      echo "remote: error: GH006: Protected branch update '
            'failed for $ref." >&2\n'
            '      echo "! [remote rejected] -> $ref (pre-receive hook '
            'declined)" >&2\n'
            "      exit 1\n"
            "      ;;\n"
            "  esac\n"
            "done\n"
            "exit 0\n"
        )
        hook.chmod(0o755)

        status, detail = CR.push_claim("200-01", self.work)
        self.assertEqual(status, "fallback-pushed")
        self.assertEqual(detail, "reserve/claim-200-01")
        _rc, out = _capture(
            ["git", "ls-remote", str(self.remote),
             "refs/heads/reserve/claim-200-01"],
            self.work)
        self.assertIn("reserve/claim-200-01", out)
        # The rejected custom-namespace ref itself was never created.
        _rc2, out2 = _capture(
            ["git", "ls-remote", str(self.remote), "refs/claims/200-01"],
            self.work)
        self.assertEqual(out2.strip(), "")


class ReleaseRemoteClaimTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.remote = self.root / "remote.git"
        _init_bare_remote(self.remote)
        self.work = self.root / "work"
        _init_clone(self.remote, self.work, parent=self.root)
        (self.work / "README.md").write_text("x\n")
        _run(["git", "add", "-A"], self.work)
        _run(["git", "commit", "-qm", "init"], self.work)
        _run(["git", "push", "-q", "origin", "HEAD:main"], self.work)

    def tearDown(self):
        self._tmp.cleanup()

    def test_release_deletes_the_remote_claim_ref(self):
        CR.push_claim("200-01", self.work)
        CR.release_remote_claim("200-01", self.work)
        _rc, out = _capture(
            ["git", "ls-remote", str(self.remote), "refs/claims/200-01"],
            self.work)
        self.assertEqual(out.strip(), "")

    def test_release_of_unreachable_origin_never_raises(self):
        _run(["git", "remote", "set-url", "origin",
              str(self.root / "does-not-exist.git")], self.work)
        CR.release_remote_claim("200-01", self.work)  # must not raise


if __name__ == "__main__":
    unittest.main()
