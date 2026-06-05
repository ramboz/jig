"""Regression guard for slice 032-01 — atomic-write-helper sweep.

After the sweep, no targeted helper `.py` should contain a literal
`\\.write_text\\(` token. This test reads each targeted file from disk
(no import side effects) and asserts the regex match count is zero.

If you legitimately need a non-atomic write in one of these helpers in
the future, prefer:
  1. Adding a new shared helper to `_common/` and using it; OR
  2. Documenting the carve-out here, adjusting the count assertion.

Targets are the six helpers listed in slice 032-01 AC #3.
"""

import re
import unittest
from pathlib import Path

# slice 032-01 AC #3 sweep targets (paths are relative to repo root).
SWEPT_HELPERS = (
    "skills/scaffold-init/scaffold.py",
    "skills/spec-workflow/workflow.py",
    "skills/memory-sync/memory.py",
    "skills/adr-workflow/adr.py",
    "skills/slice-land/land.py",
    "skills/independent-review/review.py",
)


def _repo_root() -> Path:
    """`skills/_common/test_atomic_io_sweep.py` → repo root is 2 parents up."""
    return Path(__file__).resolve().parents[2]


class AtomicWriteSweepTests(unittest.TestCase):
    def test_no_write_text_callsite_remains_in_swept_helpers(self):
        """AC #4: every targeted helper has zero `\\.write_text\\(` matches."""
        root = _repo_root()
        offenders = {}
        for rel in SWEPT_HELPERS:
            path = root / rel
            self.assertTrue(
                path.exists(),
                f"sweep target missing on disk: {rel}",
            )
            text = path.read_text(encoding="utf-8")
            matches = re.findall(r"\.write_text\(", text)
            if matches:
                offenders[rel] = len(matches)
        self.assertEqual(
            offenders,
            {},
            "found non-atomic .write_text(...) calls in swept helpers: "
            f"{offenders}. Use `atomic_write_text` from "
            "`_common.atomic_io` instead.",
        )


if __name__ == "__main__":
    unittest.main()
