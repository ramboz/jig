"""jig dogfoods its three derived-index checks against its own records.

Three files in this repo are *derived* — every column is computed from a
directory of numbered records, and hand-editing them is always a mistake:

    docs/bugs/README.md       <- docs/bugs/NNN-<slug>.md
    docs/specs/README.md      <- docs/specs/NNN-<slug>/
    docs/decisions/README.md  <- docs/decisions/adr-NNNN-<slug>.md

Every parallel PR appends to the same end-of-table position in one of them, so
every parallel PR conflicts (#143 / #144 / #145 in one afternoon on the bug
board alone). The plan is to stop hand-resolving those conflicts — but
silencing a conflict is only safe if something else catches what the marker was
accidentally catching: two branches allocating the same number, which every
renderer emits as duplicate rows without complaint.

These tests are that guard, run on jig itself. A failure here means one of:

  - the index wasn't regenerated after a record changed — re-run the family's
    generator (`status-board` / `adr.py index`) and commit the result;
  - two records claim one number — renumber one before landing;
  - an index row was edited by hand — the edit will be overwritten on the next
    regen, so move the wording into the record the row is generated from.

The spec board is the one that matters most: 265 commits in six months against
18 for the bug board.

See https://github.com/ramboz/jig/issues/149 (indexes as derived artifacts) and
https://github.com/ramboz/jig/issues/147 (why the numbers collide at all).
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BugBoardIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.bug = _load(
            "bug_module_board", REPO_ROOT / "skills" / "bug-fix" / "bug.py"
        )

    def test_no_bug_id_is_claimed_twice(self):
        duplicates = self.bug._duplicate_ids(REPO_ROOT)
        self.assertEqual(
            duplicates, {},
            "two bug records share an id — renumber one before landing:\n"
            + "\n".join(f"  {k}: {', '.join(v)}" for k, v in duplicates.items()),
        )

    def test_board_matches_the_records(self):
        board = REPO_ROOT / "docs" / "bugs" / "README.md"
        existing = board.read_text(encoding="utf-8")
        self.assertEqual(
            existing, self.bug._compose_board(REPO_ROOT, existing),
            "docs/bugs/README.md is stale — run `python3 "
            "skills/bug-fix/bug.py status-board --project-dir .` and commit it",
        )

    def test_check_board_reports_clean(self):
        """The shipped entry point, exercised end to end on the real repo —
        so the subcommand adopters get is the one jig proves works."""
        self.assertEqual(self.bug.check_board(REPO_ROOT), [])


class SpecBoardIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.workflow = _load(
            "workflow_module_board",
            REPO_ROOT / "skills" / "spec-workflow" / "workflow.py",
        )

    def test_no_spec_number_is_claimed_twice(self):
        duplicates = self.workflow._duplicate_spec_ids(REPO_ROOT)
        self.assertEqual(
            duplicates, {},
            "two spec directories share a number — renumber one before "
            "landing:\n"
            + "\n".join(f"  {k}: {', '.join(v)}" for k, v in duplicates.items()),
        )

    def test_board_matches_the_records(self):
        board = REPO_ROOT / "docs" / "specs" / "README.md"
        existing = board.read_text(encoding="utf-8")
        self.assertEqual(
            existing, self.workflow._compose_board(REPO_ROOT, existing),
            "docs/specs/README.md is stale — run `python3 "
            "skills/spec-workflow/workflow.py status-board .` and commit it",
        )

    def test_check_board_reports_clean(self):
        self.assertEqual(self.workflow.check_board(REPO_ROOT), [])

    def test_the_curated_notes_column_is_still_there(self):
        """The Notes column is the one part of the board with no source file
        (143 entries, ~57k characters), preserved across regens by scraping
        the previous board. If a regen ever writes it away, the drift check
        above goes green on the loss — it only compares against what the
        generator would produce. So assert the content is still present."""
        board = (REPO_ROOT / "docs" / "specs" / "README.md").read_text(
            encoding="utf-8"
        )
        notes = self.workflow.parse_existing_notes(board)
        populated = [v for v in notes.values() if v.strip()]
        self.assertGreater(
            len(populated), 100,
            "the spec board's Notes column has collapsed — it held 143 "
            "curated entries and they have no other home; check the last "
            "regen before committing",
        )


class AdrIndexIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.adr = _load(
            "adr_module_index", REPO_ROOT / "skills" / "adr-workflow" / "adr.py"
        )
        self.decisions = REPO_ROOT / "docs" / "decisions"

    def test_no_adr_number_is_claimed_twice(self):
        duplicates = self.adr._duplicate_adr_numbers(self.decisions)
        self.assertEqual(
            duplicates, {},
            "two ADRs share a number — renumber one before landing:\n"
            + "\n".join(f"  {k}: {', '.join(v)}" for k, v in duplicates.items()),
        )

    def test_index_matches_the_adr_files(self):
        readme = self.decisions / "README.md"
        existing = readme.read_text(encoding="utf-8")
        self.assertEqual(
            existing, self.adr._compose_index(self.decisions, existing),
            "docs/decisions/README.md is stale — run `python3 "
            "skills/adr-workflow/adr.py index docs/decisions` and commit it. "
            "If the difference is a summary someone improved by hand, move "
            "the wording into that ADR's `## Context` opening instead",
        )

    def test_check_index_reports_clean(self):
        self.assertEqual(self.adr.check_index(self.decisions), [])


if __name__ == "__main__":
    unittest.main()
