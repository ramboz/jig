#!/usr/bin/env python3
"""Tests for `_common/reservation.py` — the shared push-failure classifier and
the in-flight number scan (spec 107 / ADR-0053).

The push-failure fixtures are CAPTURED, not hand-typed: each was produced by a
real `git push` against a local bare repo (a pre-receive hook standing in for
GitHub's protected-branch / ruleset refusal). The old, mirrored fixtures
omitted the ` ! [remote rejected]` line real git always prints — the exact line
that carries `rejected` and made the classifier misread protection as a race.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import reservation as R  # noqa: E402

# --- Captured push-failure stderr -----------------------------------------

# `git push origin HEAD:main` into a bare repo that another clone had advanced.
CAPTURED_RACE = (
    "To /tmp/remote.git\n"
    " ! [rejected]        HEAD -> main (fetch first)\n"
    "error: failed to push some refs to '/tmp/remote.git'\n"
    "hint: Updates were rejected because the remote contains work that you do\n"
    "hint: not have locally. This is usually caused by another repository\n"
    "hint: pushing to the same ref. If you want to integrate the remote\n"
    "hint: changes, use 'git pull' before pushing again.\n"
)

# `git push` refused by a pre-receive hook emitting GitHub's GH006 lines.
CAPTURED_GH006 = (
    "remote: error: GH006: Protected branch update failed for refs/heads/main.\n"
    "remote: error: Changes must be made through a pull request.\n"
    "To /tmp/remote.git\n"
    " ! [remote rejected] HEAD -> main (pre-receive hook declined)\n"
    "error: failed to push some refs to '/tmp/remote.git'\n"
)

# GitHub repository-rulesets refusal (GH013). The trailer here is
# `push declined due to repository rule violations`, which none of the older
# protection signals matched — issue #147 gap 1.
CAPTURED_GH013 = (
    "remote: error: GH013: Repository rule violations found for refs/heads/main.\n"
    "remote: error: Changes must be made through a pull request.\n"
    "To github.com:ramboz/jig.git\n"
    " ! [remote rejected] HEAD -> main (push declined due to repository rule violations)\n"
    "error: failed to push some refs to 'github.com:ramboz/jig.git'\n"
)


class ClassifyPushFailure(unittest.TestCase):
    def test_gh006_is_protection(self):
        # AC1 — full captured stderr, including the ` ! [remote rejected]` line.
        self.assertEqual(R.classify_push_failure(CAPTURED_GH006), "protection")

    def test_gh013_ruleset_is_protection(self):
        # AC1 — the rulesets mechanism, previously unrecognised.
        self.assertEqual(R.classify_push_failure(CAPTURED_GH013), "protection")

    def test_race_is_race(self):
        # AC2 — a genuine non-fast-forward still routes to race recovery.
        self.assertEqual(R.classify_push_failure(CAPTURED_RACE), "race")

    def test_protection_beats_race_when_both_markers_present(self):
        # AC4 — the GH006 capture also contains the substring `rejected`; the
        # old ordering returned "race" for exactly this string.
        self.assertIn("rejected", CAPTURED_GH006.lower())
        self.assertEqual(R.classify_push_failure(CAPTURED_GH006), "protection")

    def test_bare_rejected_without_specific_marker_is_other(self):
        # AC3 — a failure that only says `rejected` (no non-fast-forward /
        # fetch first / stale info, no protection marker) is NOT a race. Telling
        # the user to re-run would be wrong.
        stderr = (
            "To github.com:ramboz/jig.git\n"
            " ! [remote rejected] HEAD -> main (some transient server hiccup)\n"
            "error: failed to push some refs\n"
        )
        self.assertEqual(R.classify_push_failure(stderr), "other")

    def test_specific_race_markers(self):
        for marker in ("non-fast-forward", "fetch first", "stale info"):
            self.assertEqual(
                R.classify_push_failure(f"! [rejected] main ({marker})"),
                "race",
                marker,
            )

    def test_unknown_is_other(self):
        self.assertEqual(
            R.classify_push_failure("fatal: unable to access: timed out"),
            "other",
        )


# --- In-flight number scan -------------------------------------------------

def _run(argv, cwd):
    subprocess.run(argv, cwd=str(cwd), check=True,
                   capture_output=True, text=True)


class ScanMaxReservedNumber(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.remote = self.root / "remote.git"
        _run(["git", "init", "--bare", "-q", str(self.remote)], self.root)
        self.work = self.root / "work"
        _run(["git", "clone", "-q", str(self.remote), str(self.work)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], self.work)
        _run(["git", "config", "user.name", "t"], self.work)

    def tearDown(self):
        self._tmp.cleanup()

    def _commit_bug(self, num, on_branch="main"):
        d = self.work / "docs" / "bugs"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{num:03d}-slug.md").write_text("x\n")
        _run(["git", "add", "-A"], self.work)
        _run(["git", "commit", "-qm", f"bug {num}"], self.work)

    def test_max_across_working_tree(self):
        # AC1 — working-tree files count.
        self._commit_bug(23)
        d = self.work / "docs" / "bugs"
        (d / "024-uncommitted.md").write_text("x\n")
        n = R.scan_max_reserved_number(
            self.work, "docs/bugs", R.BUG_NUMBER_RE,
            local_dir=d, fetch=False,
        )
        self.assertEqual(n, 24)

    def test_max_across_remote_tracking_branch(self):
        # AC1 / AC6 — a number on an unmerged pushed branch is seen.
        self._commit_bug(23)
        _run(["git", "push", "-q", "origin", "HEAD:main"], self.work)
        # A second clone pushes bug 024 to a side branch (a reservation).
        clone2 = self.root / "clone2"
        _run(["git", "clone", "-q", str(self.remote), str(clone2)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], clone2)
        _run(["git", "config", "user.name", "t"], clone2)
        d2 = clone2 / "docs" / "bugs"
        d2.mkdir(parents=True, exist_ok=True)
        (d2 / "024-reserve.md").write_text("x\n")
        _run(["git", "add", "-A"], clone2)
        _run(["git", "commit", "-qm", "reserve 024"], clone2)
        _run(["git", "push", "-q", "origin", "HEAD:refs/heads/reserve/bug-024"],
             clone2)
        # The first clone fetches and scans: it must see 024 on the side branch.
        _run(["git", "fetch", "-q", "origin"], self.work)
        n = R.scan_max_reserved_number(
            self.work, "docs/bugs", R.BUG_NUMBER_RE, fetch=False,
        )
        self.assertEqual(n, 24)

    def test_ref_without_docs_dir_contributes_zero(self):
        # AC4 — an empty repo / ref lacking docs/bugs is not an error.
        n = R.scan_max_reserved_number(
            self.work, "docs/bugs", R.BUG_NUMBER_RE, fetch=False,
        )
        self.assertEqual(n, 0)

    def test_non_conforming_entries_ignored(self):
        # AC5 — README.md, reviews/, wrong-width names don't count.
        d = self.work / "docs" / "bugs"
        d.mkdir(parents=True, exist_ok=True)
        (d / "README.md").write_text("x\n")
        (d / "reviews").mkdir()
        (d / "9999-too-wide.md").write_text("x\n")  # 4 digits, not a bug id
        (d / "007-real.md").write_text("x\n")
        n = R.scan_max_reserved_number(
            self.work, "docs/bugs", R.BUG_NUMBER_RE, local_dir=d, fetch=False,
        )
        self.assertEqual(n, 7)

    def test_adr_width(self):
        # AC1 — ADR ids are four digits.
        d = self.work / "docs" / "decisions"
        d.mkdir(parents=True, exist_ok=True)
        (d / "adr-0046-x.md").write_text("x\n")
        (d / "README.md").write_text("x\n")
        n = R.scan_max_reserved_number(
            self.work, "docs/decisions", R.ADR_NUMBER_RE,
            local_dir=d, fetch=False,
        )
        self.assertEqual(n, 46)

    def test_failed_fetch_warns_and_continues(self):
        # AC3 — a broken remote makes fetch fail; the scan still returns from
        # the local cache and writes a warning rather than raising.
        self._commit_bug(12)
        _run(["git", "remote", "set-url", "origin",
              str(self.root / "does-not-exist.git")], self.work)
        import io
        warn = io.StringIO()
        d = self.work / "docs" / "bugs"
        n = R.scan_max_reserved_number(
            self.work, "docs/bugs", R.BUG_NUMBER_RE,
            local_dir=d, fetch=True, warn=warn,
        )
        self.assertEqual(n, 12)
        self.assertIn("git fetch", warn.getvalue())


if __name__ == "__main__":
    unittest.main()
