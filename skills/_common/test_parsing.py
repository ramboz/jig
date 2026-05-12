"""Tests for skills/_common/parsing.py."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsing import find_slice_section, SliceLookupError


SPEC_TWO_SLICES = """\
# Spec X

Some preamble.

## Slice X-01 — alpha

**STATUS: DONE**

Body of slice alpha.

## Slice X-02 — beta

**STATUS: DRAFT**

Body of slice beta.

## Trailing section

Not a slice.
"""


class FindSliceSectionTests(unittest.TestCase):

    def test_unique_fragment_returns_start_end_label(self):
        start, end, label = find_slice_section(SPEC_TWO_SLICES, "X-01")
        # start is at the `##` of the matched header
        self.assertEqual(SPEC_TWO_SLICES[start:start + 2], "##")
        # section runs until the next `## ` heading
        self.assertIn("Body of slice alpha.", SPEC_TWO_SLICES[start:end])
        self.assertNotIn("Body of slice beta.", SPEC_TWO_SLICES[start:end])
        # label is the trimmed header text after `Slice `
        self.assertEqual(label, "X-01 — alpha")

    def test_section_ends_at_next_h2(self):
        start, end, _ = find_slice_section(SPEC_TWO_SLICES, "X-01")
        # End boundary is BEFORE the next `## ` (the Slice X-02 header)
        next_header_idx = SPEC_TWO_SLICES.index("## Slice X-02")
        self.assertEqual(end, next_header_idx)

    def test_last_slice_section_ends_at_next_h2(self):
        # Even a "trailing" non-slice `## ` counts as the next H2
        start, end, _ = find_slice_section(SPEC_TWO_SLICES, "X-02")
        trailing_idx = SPEC_TWO_SLICES.index("## Trailing section")
        self.assertEqual(end, trailing_idx)

    def test_case_insensitive_match(self):
        _, _, label = find_slice_section(SPEC_TWO_SLICES, "x-01")
        self.assertEqual(label, "X-01 — alpha")
        _, _, label = find_slice_section(SPEC_TWO_SLICES, "ALPHA")
        self.assertEqual(label, "X-01 — alpha")

    def test_substring_match_against_label_text(self):
        _, _, label = find_slice_section(SPEC_TWO_SLICES, "alpha")
        self.assertEqual(label, "X-01 — alpha")

    def test_missing_fragment_raises(self):
        with self.assertRaises(SliceLookupError) as cm:
            find_slice_section(SPEC_TWO_SLICES, "nonexistent")
        self.assertIn("slice not found", str(cm.exception))

    def test_ambiguous_fragment_raises(self):
        spec = SPEC_TWO_SLICES + "\n## Slice X-01 — alpha-bis\n\nBody.\n"
        with self.assertRaises(SliceLookupError) as cm:
            find_slice_section(spec, "X-01")
        self.assertIn("ambiguous", str(cm.exception))

    def test_no_headers_at_all_raises(self):
        with self.assertRaises(SliceLookupError) as cm:
            find_slice_section("# Title\n\nNo slices here.\n", "anything")
        self.assertIn("no '## Slice", str(cm.exception))

    def test_eof_terminates_section_when_no_trailing_h2(self):
        spec = "# Title\n\n## Slice Y-01 — only\n\n**STATUS: DONE**\n\nBody.\n"
        start, end, _ = find_slice_section(spec, "Y-01")
        self.assertEqual(end, len(spec))


class CrossCallerCompatibilityTests(unittest.TestCase):
    """Smoke-test against the three callers' historical fixture shapes."""

    def test_jig_real_spec_resolves(self):
        """Against jig's own spec 005, fragment '005-01' returns the right
        header and label."""
        repo_root = Path(__file__).resolve().parents[2]
        spec_path = repo_root / "docs/specs/005-adr-workflow/spec.md"
        if not spec_path.is_file():
            self.skipTest("Spec 005 not present at expected path")
        text = spec_path.read_text()
        start, end, label = find_slice_section(text, "005-01")
        self.assertTrue(text[start:].startswith("## Slice 005-01"))
        self.assertIn("adr-helper", label)
        # Section must contain its own deviation log
        section = text[start:end]
        self.assertIn("Deviation log", section)


if __name__ == "__main__":
    unittest.main()
