"""jig dogfoods `bug.py check-board` against its own bug records.

`docs/bugs/README.md` is a derived file: every column is computed from
`docs/bugs/*.md` and the Notes column is empty across all rows today. Every
parallel PR appends a row at the same end-of-table position, so every parallel
PR conflicts on it (#143 / #144 / #145 in one afternoon). The plan is to stop
hand-resolving it — but silencing a conflict is only safe if something else
catches what the marker was accidentally catching: two branches allocating the
same bug id, which the renderer emits as two rows without complaint.

This test is that guard, run on jig itself. A failure here means either the
board wasn't regenerated after a record changed (`bug.py status-board`), or two
records claim one id and one of them must be renumbered before landing.

See https://github.com/ramboz/jig/issues/149 (boards as derived artifacts) and
https://github.com/ramboz/jig/issues/147 (why the ids collide in the first
place).
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUG_PY = REPO_ROOT / "skills" / "bug-fix" / "bug.py"


def _load_bug_module():
    spec = importlib.util.spec_from_file_location("bug_module_board", BUG_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BugBoardIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.bug = _load_bug_module()

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


if __name__ == "__main__":
    unittest.main()
