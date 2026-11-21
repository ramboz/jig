"""Spec 124-01 / ADR-0069: `review.py owner-review` (the ask) and
`record-review --pass owner-review` (the owner's quoted answer).

Run from the repo root:
    python3 skills/independent-review/test_owner_review.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW = REPO_ROOT / "skills" / "independent-review" / "review.py"


def run_review(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(REVIEW), *args], input=stdin,
        capture_output=True, text=True,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)})


class OwnerReviewBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-owner-rev-"))
        spec_dir = self.tmp / "docs" / "specs" / "900-demo"
        spec_dir.mkdir(parents=True)
        self.spec = spec_dir / "spec.md"
        self.spec.write_text("---\nstatus: IN_PROGRESS\n---\n\n# Spec\n")
        (spec_dir / "slice-01-entry.md").write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\n"
            "owner_review: true\n---\n\n"
            "## Slice 900-01 — typed entry\n\n**Goal:** typed entry.\n\n"
            "**Acceptance Criteria:**\n\n"
            "1. Out-of-range input is refused, not clamped.\n")
        self.verdict = spec_dir / "reviews" / "slice-01-owner-review.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def record(self, *extra, verdict="pass", owner=True, stdin=None):
        args = ["record-review", str(self.spec), "900-01",
                "--pass", "owner-review", "--verdict", verdict,
                "--reviewer", "owner", "--prompt-source",
                "review.py owner-review docs/specs/900-demo/spec.md 900-01"]
        if owner:
            args += ["--tried", "typed 12 and saved",
                     "--surface", "iPhone 15, build 41",
                     "--owner-quote", "works,\nship it"]
        return run_review(*args, *extra, stdin=stdin)


class AskTests(OwnerReviewBase):
    def test_ask_carries_the_slice_the_question_and_the_rules(self):
        r = run_review("owner-review", str(self.spec), "900-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("900-01 — typed entry", out)
        self.assertIn("Out-of-range input is refused, not clamped.", out)
        self.assertIn("record-review", out)
        self.assertIn("--owner-quote", out)
        low = out.lower()
        for phrase in ("ask the owner", "wait for", "quote", "never infer",
                       "silence", "record nothing", "deliberateness"):
            self.assertIn(phrase, low, phrase)

    def test_ask_stamps_when_the_owner_was_asked(self):
        path = self.spec.parent / "slice-01-entry.md"
        r = run_review("owner-review", str(self.spec), "900-01")
        self.assertRegex(path.read_text(),
                         r"(?m)^owner_review_asked_at: \d{4}-\d\d-\d\dT")
        self.assertIn("owner_review_asked_at", r.stderr)
        self.assertIn("record every non-`pass` verdict", r.stdout)
        self.assertIn("answers the earlier ask", r.stdout)

    def test_ask_on_an_unflagged_slice_stamps_nothing(self):
        path = self.spec.parent / "slice-01-entry.md"
        path.write_text(path.read_text().replace("owner_review: true\n", ""))
        run_review("owner-review", str(self.spec), "900-01")
        self.assertNotIn("owner_review_asked_at", path.read_text())

    def test_ask_refuses_an_unknown_slice(self):
        r = run_review("owner-review", str(self.spec), "999-99")
        self.assertEqual(r.returncode, 2)

    def test_ask_notes_when_the_flag_is_not_set(self):
        slice_file = self.spec.parent / "slice-01-entry.md"
        slice_file.write_text(
            slice_file.read_text().replace("owner_review: true\n", ""))
        r = run_review("owner-review", str(self.spec), "900-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("owner_review: true", r.stderr)


class RecordTests(OwnerReviewBase):
    def test_records_the_owners_answer(self):
        r = self.record()
        self.assertEqual(r.returncode, 0, r.stderr)
        text = self.verdict.read_text()
        self.assertIn("pass: owner-review\n", text)
        self.assertIn("verdict: pass\n", text)
        self.assertIn("reviewer: owner\n", text)
        self.assertIn("TRIED: typed 12 and saved\n", text)
        self.assertIn("SURFACE: iPhone 15, build 41\n", text)
        self.assertIn("OWNER SAID:\n> works,\n> ship it\n", text)
        check = run_review("check-reviews", str(self.spec), "900-01")
        self.assertNotIn("owner-review", check.stderr)

    def test_summary_file_is_optional_and_appended_as_notes(self):
        r = self.record("--summary-file", "-", stdin="Checked twice.\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("NOTES:\nChecked twice.\n", self.verdict.read_text())

    def test_each_owner_argument_is_required(self):
        base = {"--tried": "x", "--surface": "y", "--owner-quote": "z"}
        for missing in base:
            for blank in (None, "  "):
                args = []
                for key, value in base.items():
                    if key == missing:
                        if blank is not None:
                            args += [key, blank]
                    else:
                        args += [key, value]
                r = self.record(*args, owner=False)
                self.assertEqual(r.returncode, 2, (missing, blank))
                self.assertIn(missing, r.stderr)
                self.assertFalse(self.verdict.exists())

    def test_non_interactive_is_refused(self):
        r = self.record("--non-interactive")
        self.assertEqual(r.returncode, 2)
        self.assertIn("owner", r.stderr.lower())
        self.assertFalse(self.verdict.exists())

    def test_owner_arguments_are_refused_on_other_passes(self):
        r = run_review(
            "record-review", str(self.spec), "900-01", "--pass", "craft",
            "--verdict", "pass", "--reviewer", "jig:reviewer",
            "--prompt-source", "review.py pr-review x",
            "--summary-file", "-", "--owner-quote", "fine",
            stdin="VERDICT: pass\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("owner-review", r.stderr)
        self.assertFalse(
            (self.spec.parent / "reviews" / "slice-01-craft.md").exists())

    def test_rejection_is_recorded_and_says_what_to_do(self):
        r = self.record(verdict="needs-changes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("verdict: needs-changes\n", self.verdict.read_text())
        self.assertIn("IN_PROGRESS", r.stdout)
        self.assertIn("ask the owner again", r.stdout)
        self.assertIn("reconciliation", r.stdout.lower())
        check = run_review("check-reviews", str(self.spec), "900-01")
        self.assertEqual(check.returncode, 2)
        self.assertIn("owner asked for changes", check.stderr)

    def test_a_pass_prints_no_rejection_notice(self):
        r = self.record()
        self.assertNotIn("IN_PROGRESS", r.stdout)


class ReopenBatchTests(OwnerReviewBase):
    """AC7 / ADR-0069 decision 6: one rejection reopens the batch."""

    def slice_text(self):
        return (self.spec.parent / "slice-01-entry.md").read_text()

    def record_other(self, pass_name, verdict):
        return run_review(
            "record-review", str(self.spec), "900-01", "--pass", pass_name,
            "--verdict", verdict, "--reviewer", "jig:reviewer",
            "--prompt-source", "review.py x", "--summary-file", "-",
            stdin=f"VERDICT: {verdict}\n")

    def test_automated_rejection_makes_the_owner_pass_stale(self):
        self.assertEqual(self.record().returncode, 0)
        self.assertEqual(self.record_other("compliance", "pass").returncode, 0)
        r = self.record_other("craft", "needs-changes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("review_reopened_at: ", self.slice_text())
        self.assertIn("ask the owner again", r.stdout)
        self.assertIn("re-run every review pass", r.stdout)
        check = run_review("check-reviews", str(self.spec), "900-01")
        self.assertEqual(check.returncode, 2)
        stale = [ln for ln in check.stderr.splitlines()
                 if "[owner-review]" in ln]
        self.assertEqual(len(stale), 1, check.stderr)
        self.assertIn("not newer", stale[0])
        self.assertIn("ask the owner first", stale[0])

    def test_late_reply_to_an_earlier_ask_does_not_clear(self):
        # Asked (T0) → craft rejects (T1, reopen) → the owner's reply to the
        # T0 ask arrives and is recorded after the fix. It is about the old
        # build, so it must not clear until the owner is asked again.
        path = self.spec.parent / "slice-01-entry.md"
        path.write_text(path.read_text().replace(
            "owner_review: true\n",
            "owner_review: true\n"
            "owner_review_asked_at: 2026-01-01T00:00:00Z\n"
            "review_reopened_at: 2026-01-02T00:00:00Z\n"))
        self.record_other("compliance", "pass")
        self.record_other("craft", "pass")
        self.assertEqual(self.record().returncode, 0)
        check = run_review("check-reviews", str(self.spec), "900-01")
        self.assertEqual(check.returncode, 2, check.stdout)
        self.assertIn("[owner-review]", check.stderr)
        self.assertIn("answer to the earlier ask", check.stderr)
        # Asking again (after the reopen) makes a fresh answer count.
        ask = run_review("owner-review", str(self.spec), "900-01")
        self.assertEqual(ask.returncode, 0, ask.stderr)
        self.assertEqual(self.record().returncode, 0)
        check = run_review("check-reviews", str(self.spec), "900-01")
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_no_reopen_means_no_ask_time_requirement(self):
        self.record_other("compliance", "pass")
        self.record_other("craft", "pass")
        self.assertEqual(self.record().returncode, 0)
        self.assertNotIn("owner_review_asked_at", self.slice_text())
        check = run_review("check-reviews", str(self.spec), "900-01")
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_owner_rejection_stamps_too(self):
        r = self.record(verdict="needs-changes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("review_reopened_at: ", self.slice_text())

    def test_pass_and_reconciliation_verdicts_stamp_nothing(self):
        self.record()
        self.record_other("craft", "pass")
        self.record_other("reconciliation", "needs-changes")
        self.assertNotIn("review_reopened_at", self.slice_text())

    def test_unflagged_slice_is_never_stamped(self):
        path = self.spec.parent / "slice-01-entry.md"
        path.write_text(path.read_text().replace("owner_review: true\n", ""))
        r = self.record_other("craft", "needs-changes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("review_reopened_at", self.slice_text())
        self.assertNotIn("reopened the review batch", r.stdout)


if __name__ == "__main__":
    unittest.main()
