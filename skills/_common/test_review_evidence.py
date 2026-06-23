"""AC verification tests for `skills/_common/review_evidence.py`
(slice 045-02 — review-artifact-recorder).

This module is the single source of truth for the review-evidence
verdict schema (ADR-0014 §2/§3/§7), shared by `review.py` (writer, this
slice) and `workflow.py transition` (gate, slice 045-03).

Run from the repo root:
    python3 skills/_common/test_review_evidence.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import review_evidence as ev  # noqa: E402

# ---------------------------------------------------------------------------
# Fixture builders — synthetic spec dirs + verdict files in temp dirs.
# Per the slice brief: fixtures live in temp dirs, NEVER in the real
# docs/specs/ tree.
# ---------------------------------------------------------------------------


def write_spec_with_slice(spec_dir: Path, slice_no: str, slug: str,
                          *, arch_review: bool = False,
                          code_health_review: bool = False,
                          frame_review: bool = False,
                          design_review: bool = False) -> Path:
    """Create `spec_dir/spec.md` + a sibling `slice-NN-<slug>.md` file.

    Returns the spec.md path. The slice file carries `arch_review: true`,
    `code_health_review: true`, `frame_review: true`, and/or
    `design_review: true` in its frontmatter when set, so `required_passes`
    can be exercised against each shape.
    """
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec = spec_dir / "spec.md"
    spec.write_text(
        "---\nstatus: IN_PROGRESS\n---\n\n# Spec\n\n## Overview\n\nStuff.\n"
    )
    fm = "---\nstatus: IN_PROGRESS\ndependencies: []\n"
    if arch_review:
        fm += "arch_review: true\n"
    if code_health_review:
        fm += "code_health_review: true\n"
    if frame_review:
        fm += "frame_review: true\n"
    if design_review:
        fm += "design_review: true\n"
    fm += "---\n"
    slice_file = spec_dir / f"slice-{slice_no}-{slug}.md"
    slice_file.write_text(
        f"{fm}\n## Slice 0XX-{slice_no} — {slug}\n\n**Goal:** placeholder.\n"
    )
    return spec


def write_verdict_file(spec_dir: Path, slice_no: str, pass_name: str,
                       *, verdict: str = "pass",
                       reviewer: str = "jig:reviewer",
                       reviewed_at: str = "2026-06-02T14:30:00Z",
                       prompt_source: str = "review.py implementation x",
                       slice_field: str = "0XX-02",
                       body: str = "## VERDICT\npass\n",
                       omit: tuple = (),
                       raw: str = None) -> Path:
    """Write a `reviews/slice-NN-<pass>.md` file directly (bypassing the
    recorder) so the validator can be exercised against hand-crafted
    good/bad shapes. `omit` drops named frontmatter keys; `raw` overrides
    the whole file content."""
    reviews = spec_dir / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    target = reviews / f"slice-{slice_no}-{pass_name}.md"
    if raw is not None:
        target.write_text(raw)
        return target
    fields = {
        "slice": slice_field,
        "pass": pass_name,
        "verdict": verdict,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "prompt_source": prompt_source,
    }
    lines = ["---"]
    for k, v in fields.items():
        if k in omit:
            continue
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    target.write_text("\n".join(lines) + "\n" + body)
    return target


# ---------------------------------------------------------------------------
# Vocabularies (ADR-0014 §1 passes, §3 verdicts)
# ---------------------------------------------------------------------------


class VocabularyTests(unittest.TestCase):
    def test_pass_vocabulary(self):
        # Slice 060-05 added the gated `code-health` pass; slice 064-03
        # added the gated, pre-implementation `frame-critique` pass; slice
        # 071-01 added the gated, attest-only `design-review` pass; spec
        # 058-04 added bug-side `bug-review` and security-surface `security`.
        self.assertEqual(
            set(ev.PASSES),
            {"compliance", "craft", "arch", "code-health", "reconciliation",
             "frame-critique", "design-review", "bug-review", "security"},
        )

    def test_verdict_vocabulary(self):
        self.assertEqual(
            set(ev.VERDICTS),
            {"pass", "fail", "needs-changes"},
        )


# ---------------------------------------------------------------------------
# Path resolution (ADR-0014 §1)
# ---------------------------------------------------------------------------


class PathResolverTests(unittest.TestCase):
    """`evidence_path(spec, slice_fragment, pass)` resolves to
    `docs/specs/NNN-slug/reviews/slice-NN-<pass>.md`, deriving NN from the
    resolved slice file name."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-ev-path-"))
        self.spec = write_spec_with_slice(self.tmp / "045-foo", "02", "bar")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_path_lands_in_reviews_dir(self):
        p = ev.evidence_path(self.spec, "0XX-02", "compliance")
        self.assertEqual(p.parent.name, "reviews")
        self.assertEqual(p.parent.parent, self.spec.parent)

    def test_path_filename_carries_slice_number_and_pass(self):
        p = ev.evidence_path(self.spec, "0XX-02", "craft")
        self.assertEqual(p.name, "slice-02-craft.md")

    def test_path_derives_number_from_slice_file_name(self):
        # The NN comes from the slice-NN-*.md filename, not the fragment.
        p = ev.evidence_path(self.spec, "0XX-02", "reconciliation")
        self.assertEqual(p.name, "slice-02-reconciliation.md")

    def test_code_health_path_filename(self):
        # Slice 060-05: the code-health pass picks up the same path convention.
        p = ev.evidence_path(self.spec, "0XX-02", "code-health")
        self.assertEqual(p.name, "slice-02-code-health.md")

    def test_frame_critique_path_filename(self):
        # Slice 064-03: the frame-critique pass picks up the same convention.
        p = ev.evidence_path(self.spec, "0XX-02", "frame-critique")
        self.assertEqual(p.name, "slice-02-frame-critique.md")

    def test_design_review_path_filename(self):
        # Slice 071-01: the design-review pass picks up the same convention.
        p = ev.evidence_path(self.spec, "0XX-02", "design-review")
        self.assertEqual(p.name, "slice-02-design-review.md")

    def test_unknown_pass_rejected(self):
        with self.assertRaises(ev.EvidenceError):
            ev.evidence_path(self.spec, "0XX-02", "bogus-pass")

    def test_invalid_slice_target_raises(self):
        with self.assertRaises(ev.EvidenceError):
            ev.evidence_path(self.spec, "999-99", "compliance")

    def test_non_numeric_slice_number_rejected(self):
        # A heading-matched but misnamed slice file (non-numeric NN) must fail
        # loudly rather than silently build a malformed reviews/slice-foo-*.md.
        spec = write_spec_with_slice(self.tmp / "046-misnamed", "foo", "bar")
        with self.assertRaises(ev.EvidenceError):
            ev.evidence_path(spec, "0XX-foo", "compliance")


class BugPathResolverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-ev-bug-path-"))
        self.bug = self.tmp / "docs" / "bugs" / "001-cache-race.md"
        self.bug.parent.mkdir(parents=True)
        self.bug.write_text("---\nsecurity_surface: false\n---\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bug_path_lands_in_reviews_dir(self):
        p = ev.bug_evidence_path(self.bug, "bug-review")
        self.assertEqual(p.parent, self.bug.parent / "reviews")
        self.assertEqual(p.name, "bug-001-bug-review.md")

    def test_bug_path_rejects_malformed_bug_filename(self):
        with self.assertRaises(ev.EvidenceError):
            ev.bug_evidence_path(self.bug.parent / "README.md", "bug-review")


# ---------------------------------------------------------------------------
# required_passes (ADR-0014 §5 transition map)
# ---------------------------------------------------------------------------


class RequiredPassesTests(unittest.TestCase):
    def test_reviewed_requires_compliance_and_craft(self):
        req = ev.required_passes("REVIEWED", arch_review=False)
        self.assertEqual(set(req), {"compliance", "craft"})

    def test_reviewed_adds_arch_when_flagged(self):
        req = ev.required_passes("REVIEWED", arch_review=True)
        self.assertEqual(set(req), {"compliance", "craft", "arch"})

    def test_reconciled_requires_reconciliation(self):
        req = ev.required_passes("RECONCILED", arch_review=False)
        self.assertEqual(set(req), {"reconciliation"})

    def test_reconciled_arch_flag_irrelevant(self):
        # arch is a REVIEWED-stage pass; it never enters the RECONCILED set.
        req = ev.required_passes("RECONCILED", arch_review=True)
        self.assertEqual(set(req), {"reconciliation"})

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ev.EvidenceError):
            ev.required_passes("BOGUS", arch_review=False)

    def test_bug_reviewed_requires_bug_review_and_craft(self):
        req = ev.required_bug_passes("REVIEWED", security_surface=False)
        self.assertEqual(set(req), {"bug-review", "craft"})

    def test_bug_reviewed_adds_security_when_surface_truthy(self):
        req = ev.required_bug_passes("REVIEWED", security_surface=True)
        self.assertEqual(set(req), {"bug-review", "craft", "security"})

    # Slice 060-05: the gated code-health pass.
    def test_code_health_in_passes(self):
        self.assertIn("code-health", ev.PASSES)

    def test_reviewed_adds_code_health_when_flagged(self):
        req = ev.required_passes("REVIEWED", arch_review=False,
                                 code_health_review=True)
        self.assertEqual(set(req), {"compliance", "craft", "code-health"})

    def test_reviewed_omits_code_health_by_default(self):
        # Default code_health_review=False → existing slices unaffected.
        req = ev.required_passes("REVIEWED", arch_review=False)
        self.assertNotIn("code-health", req)

    def test_reviewed_adds_both_arch_and_code_health(self):
        req = ev.required_passes("REVIEWED", arch_review=True,
                                 code_health_review=True)
        self.assertEqual(set(req),
                         {"compliance", "craft", "arch", "code-health"})

    def test_reconciled_ignores_code_health_flag(self):
        req = ev.required_passes("RECONCILED", arch_review=False,
                                 code_health_review=True)
        self.assertEqual(set(req), {"reconciliation"})

    # Slice 064-03 / ADR-0020: the gated, pre-implementation frame-critique.
    def test_frame_critique_in_passes(self):
        self.assertIn("frame-critique", ev.PASSES)

    def test_ready_for_review_requires_frame_when_flagged(self):
        req = ev.required_passes("READY_FOR_REVIEW", arch_review=False,
                                 frame_review=True)
        self.assertEqual(set(req), {"frame-critique"})

    def test_ready_for_review_empty_when_unflagged(self):
        # The no-regression guarantee: an unflagged slice's
        # DRAFT→READY_FOR_REVIEW has nothing to gate.
        req = ev.required_passes("READY_FOR_REVIEW", arch_review=False)
        self.assertEqual(req, ())

    def test_reviewed_ignores_frame_flag(self):
        # frame-critique is a READY_FOR_REVIEW-only pass — never required
        # at REVIEWED even if the flag is set.
        req = ev.required_passes("REVIEWED", arch_review=False,
                                 frame_review=True)
        self.assertNotIn("frame-critique", req)
        self.assertEqual(set(req), {"compliance", "craft"})

    # Slice 071-01: the gated, attest-only design-review pass (mirrors arch).
    def test_design_review_in_passes(self):
        self.assertIn("design-review", ev.PASSES)

    def test_reviewed_adds_design_review_when_flagged(self):
        req = ev.required_passes("REVIEWED", arch_review=False,
                                 design_review=True)
        self.assertEqual(set(req), {"compliance", "craft", "design-review"})

    def test_reviewed_omits_design_review_by_default(self):
        # Default design_review=False → existing slices unaffected.
        req = ev.required_passes("REVIEWED", arch_review=False)
        self.assertNotIn("design-review", req)

    def test_reviewed_adds_arch_and_design_review(self):
        req = ev.required_passes("REVIEWED", arch_review=True,
                                 design_review=True)
        self.assertEqual(set(req),
                         {"compliance", "craft", "arch", "design-review"})

    def test_reconciled_ignores_design_review_flag(self):
        # design-review is a REVIEWED-stage pass; never enters RECONCILED.
        req = ev.required_passes("RECONCILED", arch_review=False,
                                 design_review=True)
        self.assertEqual(set(req), {"reconciliation"})


class ArchReviewTruthyTokenTests(unittest.TestCase):
    """`_arch_review_flag` must accept the same truthy set as
    `workflow.py:slice_needs_arch_review` (`true`/`yes`/`on`/`1`,
    case-insensitive). Otherwise a slice authored `arch_review: yes`
    triggers an arch pass in the orchestrator yet clears REVIEWED without
    arch evidence in the gate. (045-02 reviewer Medium finding.)"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-ev-arch-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _spec_with_arch_value(self, value: str) -> Path:
        spec_dir = self.tmp / f"047-arch-{value or 'empty'}"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "spec.md").write_text("---\nstatus: IN_PROGRESS\n---\n\n# Spec\n")
        fm = (
            "---\nstatus: IN_PROGRESS\ndependencies: []\n"
            f"arch_review: {value}\n---\n"
        )
        (spec_dir / "slice-03-thing.md").write_text(
            f"{fm}\n## Slice 0XX-03 — thing\n\n**Goal:** x.\n"
        )
        return spec_dir / "spec.md"

    def test_permissive_truthy_tokens_require_arch(self):
        for tok in ("true", "yes", "on", "1", "YES", "On", "TRUE"):
            spec = self._spec_with_arch_value(tok)
            self.assertTrue(
                ev._arch_review_flag(spec, "0XX-03"),
                f"arch_review: {tok!r} should require arch evidence",
            )

    def test_non_truthy_values_do_not_require_arch(self):
        for tok in ("false", "no", "maybe", "0"):
            spec = self._spec_with_arch_value(tok)
            self.assertFalse(
                ev._arch_review_flag(spec, "0XX-03"),
                f"arch_review: {tok!r} should not require arch evidence",
            )


class DesignReviewTruthyTokenTests(unittest.TestCase):
    """Slice 071-01: `_design_review_flag` must accept the same truthy set
    as `workflow.py:slice_needs_design_review` (`true`/`yes`/`on`/`1`,
    case-insensitive) — the same drift guard the arch pass has, so a slice
    authored `design_review: yes` both triggers the design-review pass in
    the orchestrator AND is required by the gate at REVIEWED."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-ev-design-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _spec_with_design_value(self, value: str) -> Path:
        spec_dir = self.tmp / f"070-design-{value or 'empty'}"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "spec.md").write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n# Spec\n")
        fm = (
            "---\nstatus: IN_PROGRESS\ndependencies: []\n"
            f"design_review: {value}\n---\n"
        )
        (spec_dir / "slice-03-thing.md").write_text(
            f"{fm}\n## Slice 0XX-03 — thing\n\n**Goal:** x.\n"
        )
        return spec_dir / "spec.md"

    def test_permissive_truthy_tokens_require_design_review(self):
        for tok in ("true", "yes", "on", "1", "YES", "On", "TRUE"):
            spec = self._spec_with_design_value(tok)
            self.assertTrue(
                ev._design_review_flag(spec, "0XX-03"),
                f"design_review: {tok!r} should require design-review evidence",
            )

    def test_non_truthy_values_do_not_require_design_review(self):
        for tok in ("false", "no", "maybe", "0"):
            spec = self._spec_with_design_value(tok)
            self.assertFalse(
                ev._design_review_flag(spec, "0XX-03"),
                f"design_review: {tok!r} should not require design-review",
            )

    def test_missing_field_returns_false(self):
        spec_dir = self.tmp / "070-design-absent"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "spec.md").write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n# Spec\n")
        (spec_dir / "slice-03-thing.md").write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\n---\n"
            "\n## Slice 0XX-03 — thing\n\n**Goal:** x.\n"
        )
        self.assertFalse(
            ev._design_review_flag(spec_dir / "spec.md", "0XX-03"))


# ---------------------------------------------------------------------------
# parse_verdict_file — required-field + in-vocabulary validation
# ---------------------------------------------------------------------------


class ParseVerdictFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-ev-parse-"))
        self.spec_dir = self.tmp / "045-foo"
        write_spec_with_slice(self.spec_dir, "02", "bar")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_well_formed_file_parses(self):
        p = write_verdict_file(self.spec_dir, "02", "compliance")
        rec = ev.parse_verdict_file(p)
        self.assertEqual(rec.fields["verdict"], "pass")
        self.assertEqual(rec.fields["pass"], "compliance")
        self.assertEqual(rec.problems, [])
        self.assertTrue(rec.clears)

    def test_missing_required_field_reported(self):
        p = write_verdict_file(self.spec_dir, "02", "compliance",
                               omit=("reviewer",))
        rec = ev.parse_verdict_file(p)
        self.assertFalse(rec.clears)
        self.assertTrue(any("reviewer" in d for d in rec.problems),
                        f"problems should name missing field: {rec.problems}")

    def test_unknown_pass_value_reported(self):
        p = write_verdict_file(self.spec_dir, "02", "compliance")
        # Hand-corrupt the `pass:` value to something out of vocabulary.
        text = p.read_text().replace("pass: compliance", "pass: smoke-test")
        p.write_text(text)
        rec = ev.parse_verdict_file(p)
        self.assertFalse(rec.clears)
        self.assertTrue(any("pass" in d for d in rec.problems),
                        f"problems should flag unknown pass: {rec.problems}")

    def test_unknown_verdict_value_reported(self):
        p = write_verdict_file(self.spec_dir, "02", "compliance",
                               verdict="approved")
        rec = ev.parse_verdict_file(p)
        self.assertFalse(rec.clears)
        self.assertTrue(any("verdict" in d for d in rec.problems),
                        f"problems should flag unknown verdict: {rec.problems}")

    def test_malformed_frontmatter_reported(self):
        p = write_verdict_file(self.spec_dir, "02", "compliance",
                               raw="no frontmatter here at all\n")
        rec = ev.parse_verdict_file(p)
        self.assertFalse(rec.clears)
        self.assertTrue(rec.problems,
                        "missing frontmatter must produce a diagnostic")

    def test_fail_verdict_does_not_clear(self):
        p = write_verdict_file(self.spec_dir, "02", "compliance",
                               verdict="fail")
        rec = ev.parse_verdict_file(p)
        self.assertFalse(rec.clears)

    def test_needs_changes_verdict_does_not_clear(self):
        p = write_verdict_file(self.spec_dir, "02", "craft",
                               verdict="needs-changes")
        rec = ev.parse_verdict_file(p)
        self.assertFalse(rec.clears)


# ---------------------------------------------------------------------------
# Gate predicate (ADR-0014 §3 uniform rule: clears iff verdict == pass)
# ---------------------------------------------------------------------------


class GatePredicateTests(unittest.TestCase):
    def test_verdict_pass_clears(self):
        self.assertTrue(ev.verdict_clears("pass"))

    def test_verdict_fail_does_not_clear(self):
        self.assertFalse(ev.verdict_clears("fail"))

    def test_verdict_needs_changes_does_not_clear(self):
        self.assertFalse(ev.verdict_clears("needs-changes"))

    def test_unknown_verdict_does_not_clear(self):
        self.assertFalse(ev.verdict_clears("approved"))


# ---------------------------------------------------------------------------
# validate_evidence(spec, slice, stage) — the function 045-03's gate calls.
# Returns a list of human-readable diagnostics; empty = clears.
# ---------------------------------------------------------------------------


class ValidateEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-ev-validate-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _spec(self, slug, slice_no, *, arch_review=False,
              code_health_review=False, frame_review=False,
              design_review=False):
        spec_dir = self.tmp / slug
        return write_spec_with_slice(spec_dir, slice_no, "thing",
                                     arch_review=arch_review,
                                     code_health_review=code_health_review,
                                     frame_review=frame_review,
                                     design_review=design_review)

    def test_reviewed_clears_when_compliance_and_craft_pass(self):
        spec = self._spec("045-a", "02")
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertEqual(diags, [], f"expected clean, got: {diags}")

    def test_reviewed_blocks_when_craft_missing(self):
        spec = self._spec("045-b", "02")
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(diags, "missing craft must block REVIEWED")
        self.assertTrue(any("craft" in d for d in diags),
                        f"diagnostic should name the missing craft pass: {diags}")

    def test_reviewed_blocks_when_arch_required_but_missing(self):
        spec = self._spec("045-c", "02", arch_review=True)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(any("arch" in d for d in diags),
                        f"arch_review: true → missing arch must block: {diags}")

    def test_reviewed_clears_with_arch_when_flagged_and_present(self):
        spec = self._spec("045-d", "02", arch_review=True)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        write_verdict_file(spec.parent, "02", "arch", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertEqual(diags, [], f"expected clean, got: {diags}")

    def test_reviewed_ignores_arch_when_not_flagged(self):
        # arch_review NOT set → arch is not required even if absent.
        spec = self._spec("045-e", "02", arch_review=False)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertEqual(diags, [])

    # Slice 060-05: the gated code-health pass in validate_evidence.
    def test_reviewed_blocks_when_code_health_required_but_missing(self):
        spec = self._spec("060-c", "02", code_health_review=True)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(
            any("code-health" in d for d in diags),
            f"code_health_review: true → missing code-health must block: {diags}")

    def test_reviewed_clears_with_code_health_when_flagged_and_present(self):
        spec = self._spec("060-d", "02", code_health_review=True)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        write_verdict_file(spec.parent, "02", "code-health", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertEqual(diags, [], f"expected clean, got: {diags}")

    def test_reviewed_ignores_code_health_when_not_flagged(self):
        # Back-compat: a slice WITHOUT the flag never requires code-health.
        spec = self._spec("060-e", "02", code_health_review=False)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertEqual(diags, [], f"unflagged slice must not need code-health: {diags}")

    def test_code_health_review_flag_truthy_tokens(self):
        for tok in ("true", "yes", "on", "1", "YES"):
            spec = self._spec(f"060-flag-{tok}", "02")
            # rewrite slice with the raw token value
            slc = spec.parent / "slice-02-thing.md"
            slc.write_text(
                "---\nstatus: IN_PROGRESS\ndependencies: []\n"
                f"code_health_review: {tok}\n---\n\n## Slice 0XX-02 — thing\n"
            )
            self.assertTrue(
                ev._code_health_review_flag(spec, "0XX-02"),
                f"code_health_review: {tok!r} should require code-health",
            )
        for tok in ("false", "no", "0"):
            spec = self._spec(f"060-flag-neg-{tok}", "02")
            slc = spec.parent / "slice-02-thing.md"
            slc.write_text(
                "---\nstatus: IN_PROGRESS\ndependencies: []\n"
                f"code_health_review: {tok}\n---\n\n## Slice 0XX-02 — thing\n"
            )
            self.assertFalse(
                ev._code_health_review_flag(spec, "0XX-02"),
                f"code_health_review: {tok!r} should not require code-health",
            )

    # Slice 071-01: the gated, attest-only design-review pass in
    # validate_evidence — mirrors arch at the REVIEWED stage.
    def test_reviewed_blocks_when_design_review_required_but_missing(self):
        spec = self._spec("070-c", "02", design_review=True)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(
            any("design-review" in d for d in diags),
            f"design_review: true → missing design-review must block: {diags}")

    def test_reviewed_clears_with_design_review_when_flagged_and_present(self):
        spec = self._spec("070-d", "02", design_review=True)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        write_verdict_file(spec.parent, "02", "design-review", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertEqual(diags, [], f"expected clean, got: {diags}")

    def test_reviewed_ignores_design_review_when_not_flagged(self):
        # Back-compat: a slice WITHOUT the flag never requires design-review.
        spec = self._spec("070-e", "02", design_review=False)
        write_verdict_file(spec.parent, "02", "compliance", verdict="pass")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertEqual(
            diags, [],
            f"unflagged slice must not need design-review: {diags}")

    def test_reconciled_ignores_design_review_flag(self):
        # design-review is a REVIEWED-stage pass; the RECONCILED set only
        # needs reconciliation even when the slice is flagged.
        spec = self._spec("070-f", "02", design_review=True)
        write_verdict_file(spec.parent, "02", "reconciliation", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "RECONCILED")
        self.assertEqual(diags, [], f"expected clean, got: {diags}")

    # Slice 064-03 / ADR-0020: the gated, pre-implementation frame-critique
    # at the READY_FOR_REVIEW stage.
    def test_ready_for_review_blocks_when_frame_required_but_missing(self):
        spec = self._spec("064-c", "02", frame_review=True)
        diags = ev.validate_evidence(spec, "0XX-02", "READY_FOR_REVIEW")
        self.assertTrue(
            any("frame-critique" in d for d in diags),
            f"frame_review: true → missing frame-critique must block: {diags}")

    def test_ready_for_review_clears_with_frame_when_flagged_and_present(self):
        spec = self._spec("064-d", "02", frame_review=True)
        write_verdict_file(spec.parent, "02", "frame-critique", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "READY_FOR_REVIEW")
        self.assertEqual(diags, [], f"expected clean, got: {diags}")

    def test_ready_for_review_ignores_frame_when_not_flagged(self):
        # No regression: an unflagged slice transitions freely (empty set).
        spec = self._spec("064-e", "02", frame_review=False)
        diags = ev.validate_evidence(spec, "0XX-02", "READY_FOR_REVIEW")
        self.assertEqual(
            diags, [], f"unflagged slice must not need frame-critique: {diags}")

    def test_frame_review_flag_truthy_tokens(self):
        for tok in ("true", "yes", "on", "1", "YES"):
            spec = self._spec(f"064-flag-{tok}", "02")
            slc = spec.parent / "slice-02-thing.md"
            slc.write_text(
                "---\nstatus: IN_PROGRESS\ndependencies: []\n"
                f"frame_review: {tok}\n---\n\n## Slice 0XX-02 — thing\n"
            )
            self.assertTrue(
                ev._frame_review_flag(spec, "0XX-02"),
                f"frame_review: {tok!r} should require frame-critique",
            )
        for tok in ("false", "no", "0"):
            spec = self._spec(f"064-flag-neg-{tok}", "02")
            slc = spec.parent / "slice-02-thing.md"
            slc.write_text(
                "---\nstatus: IN_PROGRESS\ndependencies: []\n"
                f"frame_review: {tok}\n---\n\n## Slice 0XX-02 — thing\n"
            )
            self.assertFalse(
                ev._frame_review_flag(spec, "0XX-02"),
                f"frame_review: {tok!r} should not require frame-critique",
            )

    def test_frame_review_flag_missing_returns_false(self):
        spec = self._spec("064-flag-absent", "02")
        self.assertFalse(ev._frame_review_flag(spec, "0XX-02"))

    def test_superseded_only_fail_blocks_with_actionable_diag(self):
        """ADR §3/§4: a required pass file that exists but is `fail` (not
        yet overwritten by a later `pass`) is the 'superseded-only /
        non-clearing' case. It MUST block and name the offending pass +
        verdict. This is distinct from stale-but-passing (deferred)."""
        spec = self._spec("045-f", "02")
        write_verdict_file(spec.parent, "02", "compliance", verdict="fail")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(diags, "non-clearing compliance must block")
        joined = " ".join(diags)
        self.assertIn("compliance", joined)
        self.assertIn("fail", joined,
                      f"diagnostic should surface the non-pass verdict: {diags}")

    def test_needs_changes_only_blocks(self):
        spec = self._spec("045-g", "02")
        write_verdict_file(spec.parent, "02", "compliance",
                           verdict="needs-changes")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(any("needs-changes" in d for d in diags),
                        f"needs-changes must surface in diagnostics: {diags}")

    def test_malformed_frontmatter_blocks(self):
        spec = self._spec("045-h", "02")
        write_verdict_file(spec.parent, "02", "compliance",
                           raw="garbage, no frontmatter\n")
        write_verdict_file(spec.parent, "02", "craft", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(diags, "malformed compliance frontmatter must block")

    def test_reconciled_requires_reconciliation_pass(self):
        spec = self._spec("045-i", "02")
        diags = ev.validate_evidence(spec, "0XX-02", "RECONCILED")
        self.assertTrue(any("reconciliation" in d for d in diags),
                        f"missing reconciliation must block RECONCILED: {diags}")

    def test_reconciled_clears_when_reconciliation_passes(self):
        spec = self._spec("045-j", "02")
        write_verdict_file(spec.parent, "02", "reconciliation", verdict="pass")
        diags = ev.validate_evidence(spec, "0XX-02", "RECONCILED")
        self.assertEqual(diags, [], f"expected clean, got: {diags}")

    def test_invalid_slice_target_reported(self):
        spec = self._spec("045-k", "02")
        diags = ev.validate_evidence(spec, "999-99", "REVIEWED")
        self.assertTrue(diags, "invalid slice target must produce a diagnostic")

    def test_diagnostics_name_the_record_command(self):
        """A blocked validation should be self-explanatory: name the
        command that produces the missing artifact (ADR Consequences:
        'the gate names the missing artifact and the command to produce
        it')."""
        spec = self._spec("045-l", "02")
        diags = ev.validate_evidence(spec, "0XX-02", "REVIEWED")
        self.assertTrue(any("record-review" in d for d in diags),
                        f"diagnostics should point at record-review: {diags}")


class GateEnableTests(unittest.TestCase):
    """Slice 064-05: the gate-enable predicate moved here from workflow.py
    so the spec gate + the ADR gate read JIG_REVIEW_EVIDENCE_GATE
    identically (ADR-0002 load-bearing-consistency)."""

    def setUp(self):
        self._saved = os.environ.pop("JIG_REVIEW_EVIDENCE_GATE", None)

    def tearDown(self):
        os.environ.pop("JIG_REVIEW_EVIDENCE_GATE", None)
        if self._saved is not None:
            os.environ["JIG_REVIEW_EVIDENCE_GATE"] = self._saved

    def test_enabled_by_default(self):
        self.assertTrue(ev.evidence_gate_enabled())

    def test_disable_tokens(self):
        for token in ("0", "false", "off", "no", "FALSE", "Off", " no "):
            os.environ["JIG_REVIEW_EVIDENCE_GATE"] = token
            self.assertFalse(ev.evidence_gate_enabled(),
                             f"{token!r} should disable the gate")

    def test_other_values_keep_enabled(self):
        for token in ("1", "true", "on", "yes", "anything"):
            os.environ["JIG_REVIEW_EVIDENCE_GATE"] = token
            self.assertTrue(ev.evidence_gate_enabled(),
                            f"{token!r} should keep the gate enabled")


class AdrEvidencePathTests(unittest.TestCase):
    """Slice 064-05 AC #1: the ADR-side verdict file has a defined home."""

    def test_path_lands_in_decisions_reviews(self):
        p = ev.adr_evidence_path(Path("/x/docs/decisions"), "0020",
                                 "frame-critique")
        self.assertEqual(p.parent.name, "reviews")
        self.assertEqual(p.parent.parent.name, "decisions")

    def test_filename_carries_zero_padded_number_and_pass(self):
        p = ev.adr_evidence_path(Path("/x/docs/decisions"), "20",
                                 "frame-critique")
        self.assertEqual(p.name, "adr-0020-frame-critique.md")

    def test_unknown_pass_rejected(self):
        with self.assertRaises(ev.EvidenceError):
            ev.adr_evidence_path(Path("/x"), "0020", "smoke")


class AdrRequiredFieldsTests(unittest.TestCase):
    """Slice 064-05: ADR_REQUIRED_FIELDS mirrors REQUIRED_FIELDS but keys on
    `adr` instead of `slice`; parse_verdict_file accepts the field set."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-adr-ev-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_adr_required_fields_shape(self):
        self.assertEqual(ev.ADR_REQUIRED_FIELDS,
                         ("adr", "pass", "verdict", "reviewer",
                          "reviewed_at", "prompt_source"))
        self.assertNotIn("slice", ev.ADR_REQUIRED_FIELDS)

    def _write(self, **kw):
        defaults = {
            "adr": "0020", "pass": "frame-critique", "verdict": "pass",
            "reviewer": "jig:reviewer",
            "reviewed_at": "2026-06-08T00:00:00Z",
            "prompt_source": "review.py frame-critique x",
        }
        defaults.update(kw)
        lines = ["---"]
        for k, v in defaults.items():
            if v is not None:
                lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        p = self.tmp / "adr-0020-frame-critique.md"
        p.write_text("\n".join(lines) + "\n## VERDICT\npass\n")
        return p

    def test_well_formed_adr_verdict_clears(self):
        p = self._write()
        rec = ev.parse_verdict_file(p, required_fields=ev.ADR_REQUIRED_FIELDS)
        self.assertTrue(rec.clears, rec.problems)

    def test_missing_adr_field_reported(self):
        p = self._write(adr=None)
        rec = ev.parse_verdict_file(p, required_fields=ev.ADR_REQUIRED_FIELDS)
        self.assertFalse(rec.clears)
        self.assertTrue(any("'adr'" in pr for pr in rec.problems),
                        rec.problems)

    def test_default_field_set_unchanged(self):
        """Backward-compat: default required_fields is still the slice set."""
        # An ADR-keyed file is MISSING `slice` under the default field set.
        p = self._write()
        rec = ev.parse_verdict_file(p)  # default REQUIRED_FIELDS
        self.assertFalse(rec.clears)
        self.assertTrue(any("'slice'" in pr for pr in rec.problems),
                        rec.problems)


class ValidateAdrEvidenceTests(unittest.TestCase):
    """Slice 064-05 AC #2 support: validate_adr_evidence clears on a passing
    verdict, fails (named diagnostic) when absent / fail."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-adr-val-"))
        self.dec = self.tmp / "docs" / "decisions"
        (self.dec / "reviews").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _verdict(self, verdict="pass"):
        (self.dec / "reviews" / "adr-0020-frame-critique.md").write_text(
            "---\n"
            "adr: 0020\n"
            "pass: frame-critique\n"
            f"verdict: {verdict}\n"
            "reviewer: jig:reviewer\n"
            "reviewed_at: 2026-06-08T00:00:00Z\n"
            "prompt_source: review.py frame-critique x\n"
            "---\n\n## VERDICT\n" + verdict + "\n"
        )

    def test_clears_on_passing_verdict(self):
        self._verdict("pass")
        diags = ev.validate_adr_evidence(self.dec, "0020", "frame-critique")
        self.assertEqual(diags, [], diags)

    def test_absent_artifact_reported(self):
        diags = ev.validate_adr_evidence(self.dec, "0020", "frame-critique")
        self.assertTrue(diags)
        joined = "\n".join(diags)
        self.assertIn("adr-0020-frame-critique.md", joined)
        self.assertIn("record-review", joined)
        self.assertIn("--adr", joined)

    def test_fail_verdict_does_not_clear(self):
        self._verdict("fail")
        diags = ev.validate_adr_evidence(self.dec, "0020", "frame-critique")
        self.assertTrue(diags)


if __name__ == "__main__":
    unittest.main()
