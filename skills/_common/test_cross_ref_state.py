"""Tests for `_common/cross_ref_state.py` — the ref-aware lifecycle-state
primitive (ADR-0058 / spec 112-01).

Real git repos (not mocked subprocess) for the ref-reading behavior, mirroring
`test_reservation.py`'s `ScanMaxReservedNumber` fixtures — this primitive's
whole point is reading committed content off a DIFFERENT ref than the
checkout, which a single-branch mock can't exercise honestly.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import cross_ref_state as C  # noqa: E402


def _run(argv, cwd):
    subprocess.run(argv, cwd=str(cwd), check=True,
                   capture_output=True, text=True)


def _commit_all(cwd, message):
    _run(["git", "add", "-A"], cwd)
    _run(["git", "commit", "-qm", message], cwd)


class CrossRefStateSliceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _run(["git", "init", "-q", "-b", "main", str(self.root)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], self.root)
        _run(["git", "config", "user.name", "t"], self.root)
        # An initial commit so branches/refs have something to point at.
        (self.root / "README.md").write_text("x\n")
        _commit_all(self.root, "init")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_slice_file(self, spec_dir_name, slice_num, status):
        d = self.root / "docs" / "specs" / spec_dir_name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"slice-{slice_num}-thing.md").write_text(
            f"---\nstatus: {status}\n---\n\n## Slice 112-{slice_num} — thing\n"
        )

    def _write_embedded_spec(self, spec_dir_name, slice_label, status):
        d = self.root / "docs" / "specs" / spec_dir_name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.md").write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n"
            f"## Slice {slice_label}\n\n**STATUS: {status}**\n\n"
            "## Slice 112-02 — other\n\n**STATUS: DRAFT**\n"
        )

    # -- AC1: file-per-slice layout, status via frontmatter -----------------

    def test_slice_file_done_on_ref(self):
        self._write_slice_file("112-classa-land-backstop", "01", "DONE")
        _commit_all(self.root, "add slice")
        self.assertEqual(
            C.identifier_state_on_ref("112-01", "main", repo_root=self.root),
            "DONE",
        )

    def test_embedded_slice_section_status_via_prose_marker(self):
        self._write_embedded_spec(
            "112-cross-ref-lifecycle-state", "112-01 — classa-land-backstop",
            "IN_PROGRESS")
        _commit_all(self.root, "add embedded spec")
        self.assertEqual(
            C.identifier_state_on_ref("112-01", "main", repo_root=self.root),
            "IN_PROGRESS",
        )

    # -- AC3: absent → normal, not-blocking case -----------------------------

    def test_absent_when_identifier_not_on_ref(self):
        # Nothing committed for 112-01 at all.
        self.assertEqual(
            C.identifier_state_on_ref("112-01", "main", repo_root=self.root),
            C.ABSENT,
        )

    def test_absent_when_only_on_a_different_branch(self):
        _run(["git", "checkout", "-q", "-b", "feature"], self.root)
        self._write_slice_file("112-classa-land-backstop", "01", "DONE")
        _commit_all(self.root, "add slice on feature only")
        # `main` never saw this commit.
        self.assertEqual(
            C.identifier_state_on_ref("112-01", "main", repo_root=self.root),
            C.ABSENT,
        )
        # But it IS visible reading the feature ref.
        self.assertEqual(
            C.identifier_state_on_ref("112-01", "feature", repo_root=self.root),
            "DONE",
        )

    # -- AC3: equal/earlier state → not the integrated marker ---------------

    def test_non_integrated_status_returned_as_is(self):
        self._write_slice_file("112-classa-land-backstop", "01", "READY_FOR_IMPLEMENTATION")
        _commit_all(self.root, "add slice")
        self.assertEqual(
            C.identifier_state_on_ref("112-01", "main", repo_root=self.root),
            "READY_FOR_IMPLEMENTATION",
        )

    # -- Number-match survives a renamed slug --------------------------------

    def test_number_match_survives_renamed_slug(self):
        self._write_slice_file("112-old-slug-name", "01", "DONE")
        _commit_all(self.root, "add slice under old slug")
        _run(["git", "mv", "docs/specs/112-old-slug-name",
              "docs/specs/112-brand-new-slug"], self.root)
        _commit_all(self.root, "rename spec dir")
        self.assertEqual(
            C.identifier_state_on_ref("112-01", "main", repo_root=self.root),
            "DONE",
        )

    # -- AC4: unreachable ref/repo → unknown (None), never raises ------------

    def test_unreachable_ref_returns_none(self):
        self.assertIsNone(
            C.identifier_state_on_ref(
                "112-01", "origin/main-does-not-exist", repo_root=self.root)
        )

    def test_non_git_directory_returns_none(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            self.assertIsNone(
                C.identifier_state_on_ref(
                    "112-01", "main", repo_root=Path(not_a_repo))
            )

    # -- unrecognized identifier shape → best-effort unknown -----------------

    def test_unrecognized_identifier_shape_returns_none(self):
        self.assertIsNone(
            C.identifier_state_on_ref("not-an-id", "main", repo_root=self.root)
        )


class CrossRefStateAdrTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _run(["git", "init", "-q", "-b", "main", str(self.root)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], self.root)
        _run(["git", "config", "user.name", "t"], self.root)
        (self.root / "README.md").write_text("x\n")
        _commit_all(self.root, "init")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_adr(self, filename, status):
        d = self.root / "docs" / "decisions"
        d.mkdir(parents=True, exist_ok=True)
        (d / filename).write_text(f"---\nstatus: {status}\n---\n\n# ADR\n")

    def test_adr_accepted_on_ref(self):
        self._write_adr("adr-0058-cross-ref-lifecycle-state-check.md", "Accepted")
        _commit_all(self.root, "add adr")
        self.assertEqual(
            C.identifier_state_on_ref("0058", "main", repo_root=self.root),
            "Accepted",
        )

    def test_adr_absent(self):
        self.assertEqual(
            C.identifier_state_on_ref("0058", "main", repo_root=self.root),
            C.ABSENT,
        )

    def test_adr_number_match_survives_renamed_slug(self):
        self._write_adr("adr-0058-old-title.md", "Proposed")
        _commit_all(self.root, "add adr under old title")
        _run(["git", "mv", "docs/decisions/adr-0058-old-title.md",
              "docs/decisions/adr-0058-new-title.md"], self.root)
        _commit_all(self.root, "rename adr")
        self.assertEqual(
            C.identifier_state_on_ref("0058", "main", repo_root=self.root),
            "Proposed",
        )


class EvidenceCompleteOnRefTests(unittest.TestCase):
    """`evidence_complete_on_ref` — AC2's ref-committed baseline
    review-evidence read (`docs/specs/NNN-<slug>/reviews/slice-NN-*.md` /
    `docs/decisions/reviews/adr-NNNN-frame-critique.md`, present ON THE
    REF, distinct from ADR-0014's working-tree-at-transition-time read —
    see slice 112-03's Assumptions bridge caveat)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _run(["git", "init", "-q", "-b", "main", str(self.root)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], self.root)
        _run(["git", "config", "user.name", "t"], self.root)
        (self.root / "README.md").write_text("x\n")
        _commit_all(self.root, "init")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_slice_file(self, spec_dir_name, slice_num, status):
        d = self.root / "docs" / "specs" / spec_dir_name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"slice-{slice_num}-thing.md").write_text(
            f"---\nstatus: {status}\n---\n\n## Slice 112-{slice_num} — thing\n"
        )

    def _write_evidence(self, spec_dir_name, slice_num, passes):
        d = self.root / "docs" / "specs" / spec_dir_name / "reviews"
        d.mkdir(parents=True, exist_ok=True)
        for p in passes:
            (d / f"slice-{slice_num}-{p}.md").write_text("verdict: pass\n")

    def test_slice_evidence_complete_true(self):
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        self._write_evidence(
            "112-classc-sibling-done", "01",
            ["compliance", "craft", "reconciliation"])
        _commit_all(self.root, "add slice + evidence")
        self.assertTrue(
            C.evidence_complete_on_ref("112-01", "main", repo_root=self.root)
        )

    def test_slice_evidence_incomplete_missing_a_pass(self):
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        # Only compliance + craft — reconciliation missing.
        self._write_evidence(
            "112-classc-sibling-done", "01", ["compliance", "craft"])
        _commit_all(self.root, "add slice + partial evidence")
        self.assertFalse(
            C.evidence_complete_on_ref("112-01", "main", repo_root=self.root)
        )

    def test_slice_evidence_absent_no_reviews_dir(self):
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        _commit_all(self.root, "add slice, no reviews dir")
        self.assertFalse(
            C.evidence_complete_on_ref("112-01", "main", repo_root=self.root)
        )

    def test_slice_evidence_none_when_ref_unreadable(self):
        self.assertIsNone(
            C.evidence_complete_on_ref(
                "112-01", "does-not-exist", repo_root=self.root)
        )

    def test_adr_evidence_complete_true(self):
        d = self.root / "docs" / "decisions"
        d.mkdir(parents=True, exist_ok=True)
        (d / "adr-0058-cross-ref-lifecycle-state-check.md").write_text(
            "---\nstatus: Accepted\n---\n\n# ADR\n"
        )
        rd = d / "reviews"
        rd.mkdir()
        (rd / "adr-0058-frame-critique.md").write_text("verdict: pass\n")
        _commit_all(self.root, "add adr + evidence")
        self.assertTrue(
            C.evidence_complete_on_ref("0058", "main", repo_root=self.root)
        )

    def test_adr_evidence_incomplete_no_frame_critique_file(self):
        d = self.root / "docs" / "decisions"
        d.mkdir(parents=True, exist_ok=True)
        (d / "adr-0058-cross-ref-lifecycle-state-check.md").write_text(
            "---\nstatus: Accepted\n---\n\n# ADR\n"
        )
        _commit_all(self.root, "add adr, no evidence")
        self.assertFalse(
            C.evidence_complete_on_ref("0058", "main", repo_root=self.root)
        )


class FindSiblingDoneTests(unittest.TestCase):
    """`find_sibling_done` — AC1/AC3/AC5 (spec 112-03): the sibling-ref scan
    that closes the reported Class-C incident. Real bare+clone git fixtures
    for the own-remote-exclusion case (mirrors `test_reservation.py`); plain
    local-branch fixtures for the rest."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _run(["git", "init", "-q", "-b", "main", str(self.root)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], self.root)
        _run(["git", "config", "user.name", "t"], self.root)
        (self.root / "README.md").write_text("x\n")
        _commit_all(self.root, "init")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_slice_file(self, spec_dir_name, slice_num, status):
        d = self.root / "docs" / "specs" / spec_dir_name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"slice-{slice_num}-thing.md").write_text(
            f"---\nstatus: {status}\n---\n\n## Slice 112-{slice_num} — thing\n"
        )

    def _write_evidence(self, spec_dir_name, slice_num,
                        passes=("compliance", "craft", "reconciliation")):
        d = self.root / "docs" / "specs" / spec_dir_name / "reviews"
        d.mkdir(parents=True, exist_ok=True)
        for p in passes:
            (d / f"slice-{slice_num}-{p}.md").write_text("verdict: pass\n")

    def test_sibling_evidence_complete_done_is_the_hit(self):
        # AC1/AC2/AC3 — a sibling branch (not the current one) with an
        # evidence-complete DONE for 112-01 is returned as the hit.
        _run(["git", "checkout", "-q", "-b", "sibling-done"], self.root)
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        self._write_evidence("112-classc-sibling-done", "01")
        _commit_all(self.root, "finish 112-01 on sibling-done")
        _run(["git", "checkout", "-q", "main"], self.root)

        hit, warnings = C.find_sibling_done(
            "112-01", self.root, current_branch="main")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.ref, "sibling-done")
        self.assertTrue(hit.evidence_complete)

    def test_sibling_done_marker_without_evidence_warns_not_refuses(self):
        # AC2 — the chosen posture: a bare DONE marker with no evidence
        # files committed on that ref downgrades to a non-blocking warning,
        # not a hit.
        _run(["git", "checkout", "-q", "-b", "sibling-spike"], self.root)
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        _commit_all(self.root, "mark 112-01 DONE, no evidence, on spike")
        _run(["git", "checkout", "-q", "main"], self.root)

        hit, warnings = C.find_sibling_done(
            "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)
        self.assertTrue(
            any("sibling-spike" in w and "evidence" in w for w in warnings),
            warnings,
        )

    def test_no_sibling_passes_silently(self):
        # AC3 (converse) — nothing else claims 112-01; no hit, no warnings.
        hit, warnings = C.find_sibling_done(
            "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)
        self.assertEqual(warnings, [])

    def test_current_branch_excluded(self):
        # AC1 — the identifier being DONE + evidence-complete on the
        # CURRENT branch itself must never self-match as a "sibling".
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        self._write_evidence("112-classc-sibling-done", "01")
        _commit_all(self.root, "finish 112-01 on main (current branch)")

        hit, warnings = C.find_sibling_done(
            "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)

    def test_own_remote_tracking_ref_excluded(self):
        # AC1 — a pushed copy of the CURRENT branch (its own remote-tracking
        # ref) is not a sibling either, real bare+clone fixture.
        bare = self.root / "remote.git"
        _run(["git", "init", "--bare", "-q", "-b", "main", str(bare)], self.root)
        work = self.root / "work"
        _run(["git", "clone", "-q", str(bare), str(work)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], work)
        _run(["git", "config", "user.name", "t"], work)
        (work / "README.md").write_text("x\n")
        _commit_all(work, "init")
        _run(["git", "checkout", "-q", "-b", "feature"], work)
        d = work / "docs" / "specs" / "112-classc-sibling-done"
        d.mkdir(parents=True)
        (d / "slice-01-thing.md").write_text(
            "---\nstatus: DONE\n---\n\n## Slice 112-01 — thing\n"
        )
        rd = d / "reviews"
        rd.mkdir()
        for p in ("compliance", "craft", "reconciliation"):
            (rd / f"slice-01-{p}.md").write_text("verdict: pass\n")
        _commit_all(work, "finish 112-01 on feature")
        _run(["git", "push", "-q", "origin", "feature:feature"], work)
        _run(["git", "fetch", "-q", "origin"], work)

        hit, warnings = C.find_sibling_done(
            "112-01", work, current_branch="feature")
        self.assertIsNone(hit)

    def test_exclude_refs_skips_the_named_ref(self):
        # AC1 — the caller (workflow.py's Class-C guard) excludes
        # `origin/main`: that's Class A's territory, already checked
        # elsewhere; Class C must not re-match it as a "sibling".
        bare = self.root / "remote.git"
        _run(["git", "init", "--bare", "-q", "-b", "main", str(bare)], self.root)
        work = self.root / "work"
        _run(["git", "clone", "-q", str(bare), str(work)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], work)
        _run(["git", "config", "user.name", "t"], work)
        (work / "README.md").write_text("x\n")
        d = work / "docs" / "specs" / "112-classc-sibling-done"
        d.mkdir(parents=True)
        (d / "slice-01-thing.md").write_text(
            "---\nstatus: DONE\n---\n\n## Slice 112-01 — thing\n"
        )
        rd = d / "reviews"
        rd.mkdir()
        for p in ("compliance", "craft", "reconciliation"):
            (rd / f"slice-01-{p}.md").write_text("verdict: pass\n")
        _commit_all(work, "finish 112-01 on main")
        _run(["git", "push", "-q", "origin", "main:main"], work)
        _run(["git", "checkout", "-q", "-b", "feature"], work)
        # Only `refs/remotes/origin/main` should carry the finished commit
        # from here on — delete the local `main` branch so the test isolates
        # `exclude_refs` excluding origin/main specifically, rather than
        # incidentally hiding a SECOND, non-excluded sibling ref (local
        # `main`) that also happens to carry the same content.
        _run(["git", "branch", "-D", "main"], work)
        _run(["git", "fetch", "-q", "origin"], work)

        hit, warnings = C.find_sibling_done(
            "112-01", work, current_branch="feature",
            exclude_refs={"origin/main"})
        self.assertIsNone(hit)

    def test_ref_enumeration_failure_is_silent_not_a_warning(self):
        # Not a git repository at all (a brand-new local-only project, or a
        # test fixture with no `.git`) degrades to an empty scan with NO
        # warning — the routine "not set up yet" case, mirroring
        # `workflow.py`'s `_origin_slice_state` "no-origin" convention.
        # Never a raise either way.
        with tempfile.TemporaryDirectory() as not_a_repo:
            hit, warnings = C.find_sibling_done(
                "112-01", Path(not_a_repo), current_branch="main")
        self.assertIsNone(hit)
        self.assertEqual(warnings, [])

    def test_unreachable_ref_warns_and_evidence_complete_sibling_still_wins(self):
        # AC5 — an individual ref that fails/times out degrades to a
        # warning and the scan continues; a later evidence-complete sibling
        # is still found. Uses the `run=` injection seam (mirrors
        # `CrossRefStateInjectedRunTests`) since a real timeout is slow and
        # flaky to fixture.
        calls = []

        def fake_run(argv, cwd):
            calls.append(argv)
            joined = " ".join(argv)
            if argv[:2] == ["git", "for-each-ref"]:
                return (0,
                        "refs/heads/sibling-timeout\n"
                        "refs/heads/zzz-sibling-ok\n",
                        "")
            if "sibling-timeout" in joined:
                return 1, "", "simulated timeout"
            if argv[:2] == ["git", "ls-tree"] and argv[-1] == "docs/specs/":
                return 0, "112-fake-slug\n", ""
            if (argv[:2] == ["git", "ls-tree"]
                    and argv[-1] == "docs/specs/112-fake-slug/"):
                return 0, "slice-01-fake.md\n", ""
            if (argv[:2] == ["git", "ls-tree"]
                    and argv[-1] == "docs/specs/112-fake-slug/reviews/"):
                return (0,
                        "slice-01-compliance.md\nslice-01-craft.md\n"
                        "slice-01-reconciliation.md\n", "")
            if argv[:2] == ["git", "show"]:
                return 0, "---\nstatus: DONE\n---\n", ""
            return 1, "", "unexpected call: " + joined

        hit, warnings = C.find_sibling_done(
            "112-01", Path("/nonexistent"), current_branch=None,
            run=fake_run)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.ref, "zzz-sibling-ok")
        self.assertTrue(hit.evidence_complete)
        self.assertTrue(
            any("sibling-timeout" in w for w in warnings), warnings)

    def test_marker_only_hit_does_not_block_a_later_evidence_complete_hit(self):
        # AC2 — scan order: a marker-only DONE ref sorts BEFORE an
        # evidence-complete one; the marker-only hit downgrades to a
        # warning and the scan keeps going to the real (evidence-complete)
        # hit rather than stopping early.
        _run(["git", "checkout", "-q", "-b", "aaa-marker-only"], self.root)
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        _commit_all(self.root, "mark DONE, no evidence")
        _run(["git", "checkout", "-q", "main"], self.root)
        _run(["git", "checkout", "-q", "-b", "zzz-evidence-complete"],
             self.root)
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        self._write_evidence("112-classc-sibling-done", "01")
        _commit_all(self.root, "finish with evidence")
        _run(["git", "checkout", "-q", "main"], self.root)

        hit, warnings = C.find_sibling_done(
            "112-01", self.root, current_branch="main")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.ref, "zzz-evidence-complete")
        self.assertTrue(
            any("aaa-marker-only" in w for w in warnings), warnings)

    def test_total_time_budget_truncates_scan(self):
        # AC5 — a large/slow ref set never hangs the command: the scan
        # bails past a wall-clock budget rather than checking every ref,
        # leaving a truncation warning.
        from unittest.mock import patch
        _run(["git", "checkout", "-q", "-b", "sibling-a"], self.root)
        self._write_slice_file("112-classc-sibling-done", "01", "DONE")
        self._write_evidence("112-classc-sibling-done", "01")
        _commit_all(self.root, "finish on sibling-a")
        _run(["git", "checkout", "-q", "main"], self.root)
        _run(["git", "checkout", "-q", "-b", "aaa-sibling-b"], self.root)
        (self.root / "unrelated.md").write_text("x\n")
        _commit_all(self.root, "unrelated commit")
        _run(["git", "checkout", "-q", "main"], self.root)

        # Force the budget check to read as already-exceeded on the very
        # first candidate, without a real multi-second sleep.
        with patch.object(C.time, "monotonic", side_effect=[0, 999999]):
            hit, warnings = C.find_sibling_done(
                "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)
        self.assertTrue(any("time budget" in w for w in warnings), warnings)


class FindSiblingInProgressClaimTests(unittest.TestCase):
    """`find_sibling_in_progress_claim` — ADR-0058 Class B (spec 112-05):
    extends `_refuse_start_collision`'s READ SCOPE to sibling/remote refs
    WITHOUT changing when the both-ends-`IN_PROGRESS` halt fires. Real git
    fixtures, mirroring `FindSiblingDoneTests`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _run(["git", "init", "-q", "-b", "main", str(self.root)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], self.root)
        _run(["git", "config", "user.name", "t"], self.root)
        (self.root / "README.md").write_text("x\n")
        _commit_all(self.root, "init")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_slice_file(self, spec_dir_name, slice_num, status,
                          claimed_by=None):
        d = self.root / "docs" / "specs" / spec_dir_name
        d.mkdir(parents=True, exist_ok=True)
        claim_line = f"claimed_by: {claimed_by}\n" if claimed_by else ""
        (d / f"slice-{slice_num}-thing.md").write_text(
            f"---\nstatus: {status}\n{claim_line}---\n\n"
            f"## Slice 112-{slice_num} — thing\n"
        )

    def test_sibling_foreign_in_progress_claim_is_the_hit(self):
        # AC1/AC2 — a sibling branch (not the current one) with 112-01
        # IN_PROGRESS under a foreign claim is returned as the hit.
        _run(["git", "checkout", "-q", "-b", "sibling-building"], self.root)
        self._write_slice_file("112-classb-claim-reservation", "01",
                               "IN_PROGRESS", claimed_by="peer-machine")
        _commit_all(self.root, "claim 112-01 on sibling-building")
        _run(["git", "checkout", "-q", "main"], self.root)

        hit, warnings = C.find_sibling_in_progress_claim(
            "112-01", self.root, current_branch="main")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.ref, "sibling-building")
        self.assertEqual(hit.claimed_by, "peer-machine")
        self.assertEqual(warnings, [])

    def test_no_sibling_passes_silently(self):
        hit, warnings = C.find_sibling_in_progress_claim(
            "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)
        self.assertEqual(warnings, [])

    def test_sibling_in_a_non_in_progress_working_state_is_not_a_hit(self):
        # AC3 — ADR-0045 preserved EXACTLY: a foreign claim on a sibling in
        # REVIEWED (a non-build working state) must NEVER be reported as a
        # Class-B hit — only both-ends-IN_PROGRESS halts. This is the
        # regression guard for the "do not re-block the sanctioned
        # implementer -> reviewer handoff" constraint.
        _run(["git", "checkout", "-q", "-b", "sibling-reviewing"], self.root)
        self._write_slice_file("112-classb-claim-reservation", "01",
                               "REVIEWED", claimed_by="reviewer-peer")
        _commit_all(self.root, "reviewer holds 112-01 on sibling-reviewing")
        _run(["git", "checkout", "-q", "main"], self.root)

        hit, warnings = C.find_sibling_in_progress_claim(
            "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)

    def test_current_branch_excluded(self):
        # The identifier being IN_PROGRESS + claimed on the CURRENT branch
        # itself must never self-match as a "sibling".
        self._write_slice_file("112-classb-claim-reservation", "01",
                               "IN_PROGRESS", claimed_by="wt-me")
        _commit_all(self.root, "claim 112-01 on main (current branch)")

        hit, warnings = C.find_sibling_in_progress_claim(
            "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)

    def test_exclude_refs_skips_the_named_ref(self):
        # `_refuse_start_collision` excludes `origin/main` — that's its OWN
        # territory, already checked separately.
        bare = self.root / "remote.git"
        _run(["git", "init", "--bare", "-q", "-b", "main", str(bare)], self.root)
        work = self.root / "work"
        _run(["git", "clone", "-q", str(bare), str(work)], self.root)
        _run(["git", "config", "user.email", "t@t.t"], work)
        _run(["git", "config", "user.name", "t"], work)
        (work / "README.md").write_text("x\n")
        d = work / "docs" / "specs" / "112-classb-claim-reservation"
        d.mkdir(parents=True)
        (d / "slice-01-thing.md").write_text(
            "---\nstatus: IN_PROGRESS\nclaimed_by: peer\n---\n\n"
            "## Slice 112-01 — thing\n"
        )
        _commit_all(work, "claim 112-01 on main")
        _run(["git", "push", "-q", "origin", "main:main"], work)
        _run(["git", "checkout", "-q", "-b", "feature"], work)
        _run(["git", "branch", "-D", "main"], work)
        _run(["git", "fetch", "-q", "origin"], work)

        hit, warnings = C.find_sibling_in_progress_claim(
            "112-01", work, current_branch="feature",
            exclude_refs={"origin/main"})
        self.assertIsNone(hit)

    def test_ref_enumeration_failure_is_silent(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            hit, warnings = C.find_sibling_in_progress_claim(
                "112-01", Path(not_a_repo), current_branch="main")
        self.assertIsNone(hit)
        self.assertEqual(warnings, [])

    def test_unreachable_ref_warns_and_scan_continues(self):
        # AC5/AC6 — one unreadable sibling ref does not hide a LATER
        # genuine hit, and degrades to a warning rather than raising.
        def fake_run(argv, cwd):
            if argv[:2] == ["git", "for-each-ref"]:
                return (0,
                        "refs/heads/sibling-timeout\n"
                        "refs/heads/zzz-sibling-claimed\n", "")
            if "sibling-timeout" in " ".join(argv):
                return 1, "", "simulated timeout"
            if argv[:2] == ["git", "ls-tree"] and argv[-1] == "docs/specs/":
                return 0, "112-fake-slug\n", ""
            if (argv[:2] == ["git", "ls-tree"]
                    and argv[-1] == "docs/specs/112-fake-slug/"):
                return 0, "slice-01-fake.md\n", ""
            if argv[:2] == ["git", "show"]:
                return (0,
                       "---\nstatus: IN_PROGRESS\nclaimed_by: peer\n---\n",
                       "")
            return 1, "", "unexpected call: " + " ".join(argv)

        hit, warnings = C.find_sibling_in_progress_claim(
            "112-01", Path("/nonexistent"), current_branch=None,
            run=fake_run)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.ref, "zzz-sibling-claimed")
        self.assertEqual(hit.claimed_by, "peer")
        self.assertTrue(
            any("sibling-timeout" in w for w in warnings), warnings)

    def test_non_slice_identifier_returns_no_hit(self):
        # ADRs carry no claim concept.
        hit, warnings = C.find_sibling_in_progress_claim(
            "0058", self.root, current_branch="main")
        self.assertIsNone(hit)
        self.assertEqual(warnings, [])

    def test_total_time_budget_truncates_scan(self):
        from unittest.mock import patch
        _run(["git", "checkout", "-q", "-b", "sibling-a"], self.root)
        self._write_slice_file("112-classb-claim-reservation", "01",
                               "IN_PROGRESS", claimed_by="peer")
        _commit_all(self.root, "claim on sibling-a")
        _run(["git", "checkout", "-q", "main"], self.root)

        with patch.object(C.time, "monotonic", side_effect=[0, 999999]):
            hit, warnings = C.find_sibling_in_progress_claim(
                "112-01", self.root, current_branch="main")
        self.assertIsNone(hit)
        self.assertTrue(any("time budget" in w for w in warnings), warnings)


class CrossRefStateInjectedRunTests(unittest.TestCase):
    """Fast, non-git tests for the `run=` injection seam (mirrors
    `scan_max_reserved_number`'s pattern)."""

    def test_run_injection_used_for_ls_tree_and_show(self):
        calls = []

        def fake_run(argv, cwd):
            calls.append(argv)
            if argv[:2] == ["git", "ls-tree"] and argv[-1] == "docs/specs/112-fake-slug/":
                return 0, "slice-01-fake.md\n", ""
            if argv[:2] == ["git", "ls-tree"] and argv[-1] == "docs/specs/":
                return 0, "112-fake-slug\n", ""
            if argv[:2] == ["git", "show"]:
                return 0, "---\nstatus: DONE\n---\n", ""
            return 1, "", "unexpected call"

        state = C.identifier_state_on_ref(
            "112-01", "origin/main", repo_root=Path("/nonexistent"),
            run=fake_run)
        self.assertEqual(state, "DONE")
        self.assertTrue(any(c[:2] == ["git", "show"] for c in calls))


if __name__ == "__main__":
    unittest.main()
