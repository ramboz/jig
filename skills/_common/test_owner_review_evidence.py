"""Spec 124-01 / ADR-0069: the `owner-review` pass in the shared evidence
module — vocabulary, the `owner_review` flag, the body check, and the
gate's diagnostics.

Run from the repo root:
    python3 skills/_common/test_owner_review_evidence.py
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import review_evidence as ev  # noqa: E402

GOOD_BODY = (
    "VERDICT: pass\n\n"
    "TRIED: typed 12 into the amount field and saved\n\n"
    "SURFACE: iPhone 15, TestFlight build 41\n\n"
    "OWNER SAID:\n> works, ship it\n"
)


def make_slice(root: Path, flag=None) -> Path:
    spec_dir = root / "docs" / "specs" / "900-demo"
    spec_dir.mkdir(parents=True)
    spec = spec_dir / "spec.md"
    spec.write_text("---\nstatus: IN_PROGRESS\n---\n\n# Spec\n")
    fm = "---\nstatus: IN_PROGRESS\ndependencies: []\n"
    if flag is not None:
        fm += f"owner_review: {flag}\n"
    (spec_dir / "slice-01-thing.md").write_text(
        fm + "---\n\n## Slice 900-01 — thing\n\n**Goal:** x.\n")
    return spec


def write_verdict(spec: Path, pass_name: str, verdict: str = "pass",
                  body: str = "VERDICT: pass\n") -> Path:
    reviews = spec.parent / "reviews"
    reviews.mkdir(exist_ok=True)
    path = reviews / f"slice-01-{pass_name}.md"
    path.write_text(
        "---\nslice: 900-01 — thing\n"
        f"pass: {pass_name}\nverdict: {verdict}\nreviewer: someone\n"
        "reviewed_at: 2026-11-20T10:00:00Z\nprompt_source: review.py x\n"
        "---\n\n" + body)
    return path


class VocabularyTests(unittest.TestCase):
    def test_owner_review_is_a_pass(self):
        self.assertIn("owner-review", ev.PASSES)

    def test_reviewed_adds_owner_review_when_flagged(self):
        req = ev.required_passes("REVIEWED", arch_review=False,
                                 owner_review=True)
        self.assertEqual(set(req), {"compliance", "craft", "owner-review"})

    def test_reviewed_omits_owner_review_by_default(self):
        self.assertNotIn(
            "owner-review", ev.required_passes("REVIEWED", arch_review=False))

    def test_other_stages_ignore_the_flag(self):
        self.assertEqual(
            ev.required_passes("RECONCILED", arch_review=False,
                               owner_review=True), ("reconciliation",))
        self.assertEqual(
            ev.required_passes("READY_FOR_REVIEW", arch_review=False,
                               owner_review=True), ())


class BodyCheckTests(unittest.TestCase):
    def test_complete_body_has_no_problem(self):
        self.assertEqual(ev.owner_review_problem(GOOD_BODY), "")

    def test_each_missing_part_is_named(self):
        for label in ("TRIED:", "SURFACE:", "OWNER SAID:"):
            lines = [ln for ln in GOOD_BODY.splitlines()
                     if not ln.startswith(label)]
            if label == "OWNER SAID:":
                lines = [ln for ln in lines if not ln.startswith(">")]
            problem = ev.owner_review_problem("\n".join(lines))
            self.assertIn(label, problem)

    def test_blank_parts_do_not_count(self):
        body = "TRIED:   \nSURFACE:\nOWNER SAID:\n>\n"
        problem = ev.owner_review_problem(body)
        for label in ("TRIED:", "SURFACE:", "OWNER SAID:"):
            self.assertIn(label, problem)

    def test_quote_must_be_a_blockquote_under_the_label(self):
        body = GOOD_BODY.replace("> works, ship it", "works, ship it")
        self.assertIn("OWNER SAID:", ev.owner_review_problem(body))


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-owner-ev-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _spec(self, flag="true"):
        spec = make_slice(self.tmp, flag)
        write_verdict(spec, "compliance")
        write_verdict(spec, "craft")
        return spec

    def test_truthy_tokens_require_the_pass(self):
        for i, tok in enumerate(("true", "yes", "on", "1", "TRUE")):
            spec = make_slice(self.tmp / str(i), tok)
            self.assertTrue(ev._owner_review_flag(spec, "900-01"), tok)

    def test_absent_or_false_flag_requires_nothing(self):
        for i, tok in enumerate((None, "false", "no", "")):
            spec = make_slice(self.tmp / str(i), tok)
            write_verdict(spec, "compliance")
            write_verdict(spec, "craft")
            self.assertEqual(
                ev.validate_evidence(spec, "900-01", "REVIEWED"), [], tok)

    def test_missing_verdict_blocks_and_says_to_ask_the_owner(self):
        diags = ev.validate_evidence(self._spec(), "900-01", "REVIEWED")
        self.assertEqual(len(diags), 1)
        self.assertIn("[owner-review]", diags[0])
        self.assertIn("review.py owner-review", diags[0])
        self.assertIn("ask the owner", diags[0].lower())
        # The generic hint invites recording a pass outright; the owner
        # pass must not carry it.
        self.assertNotIn("--verdict pass", diags[0])

    def test_complete_pass_clears(self):
        spec = self._spec()
        write_verdict(spec, "owner-review", body=GOOD_BODY)
        self.assertEqual(ev.validate_evidence(spec, "900-01", "REVIEWED"), [])

    def test_pass_without_the_quote_does_not_clear(self):
        spec = self._spec()
        write_verdict(spec, "owner-review", body="VERDICT: pass\nLooks fine.\n")
        diags = ev.validate_evidence(spec, "900-01", "REVIEWED")
        self.assertEqual(len(diags), 1)
        self.assertIn("OWNER SAID:", diags[0])
        self.assertIn("TRIED:", diags[0])

    def test_rejection_keeps_the_slice_in_progress(self):
        for verdict in ("needs-changes", "fail"):
            spec = self._spec() if verdict == "needs-changes" else spec
            write_verdict(spec, "owner-review", verdict=verdict,
                          body=GOOD_BODY)
            diags = ev.validate_evidence(spec, "900-01", "REVIEWED")
            self.assertEqual(len(diags), 1, diags)
            text = diags[0]
            self.assertIn("[owner-review]", text)
            self.assertIn("owner asked for changes", text)
            self.assertIn("IN_PROGRESS", text)
            self.assertIn("reconciliation", text.lower())
            self.assertIn("ask the owner again", text)

    def test_reopen_makes_an_earlier_owner_pass_stale(self):
        spec = self._spec()
        write_verdict(spec, "owner-review", body=GOOD_BODY)
        slice_file = spec.parent / "slice-01-thing.md"
        slice_file.write_text(slice_file.read_text().replace(
            "owner_review: true\n",
            "owner_review: true\nreview_reopened_at: 2026-11-21T00:00:00Z\n"))
        diags = ev.validate_evidence(spec, "900-01", "REVIEWED")
        self.assertTrue(any("[owner-review]" in d and "not newer" in d
                            for d in diags), diags)


if __name__ == "__main__":
    unittest.main()
