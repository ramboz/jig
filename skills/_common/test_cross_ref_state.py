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
