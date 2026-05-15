"""Tests for skills/_common/parsing.py."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsing import (
    find_slice_section,
    parse_frontmatter,
    set_frontmatter_field,
    SliceLookupError,
)


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


class ParseFrontmatterTests(unittest.TestCase):
    """Slice 014-01: leading `---\\n...\\n---` extraction."""

    def test_no_frontmatter_returns_empty(self):
        fields, off = parse_frontmatter("Just some body text.\n")
        self.assertEqual(fields, {})
        self.assertEqual(off, 0)

    def test_scalar_fields(self):
        text = "---\nstatus: DRAFT\nlast_verified: 2026-05-15\n---\nBody.\n"
        fields, off = parse_frontmatter(text)
        self.assertEqual(fields["status"], "DRAFT")
        self.assertEqual(fields["last_verified"], "2026-05-15")
        self.assertEqual(text[off:], "Body.\n")

    def test_flow_list(self):
        text = "---\ndependencies: [007-02, adr-0004]\n---\nBody.\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["dependencies"], ["007-02", "adr-0004"])

    def test_empty_flow_list(self):
        text = "---\ndependencies: []\n---\nBody.\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["dependencies"], [])

    def test_block_list(self):
        text = "---\ndependencies:\n  - 003-04\n  - adr-0001\n---\nBody.\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["dependencies"], ["003-04", "adr-0001"])

    def test_quoted_scalar_stripped(self):
        text = '---\ntitle: "Hello: world"\n---\nBody.\n'
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["title"], "Hello: world")

    def test_leading_blank_lines_tolerated(self):
        text = "\n\n---\nstatus: DONE\n---\nBody.\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["status"], "DONE")


class SetFrontmatterFieldTests(unittest.TestCase):
    """Slice 014-01: idempotent in-place frontmatter mutation."""

    def test_creates_block_when_absent(self):
        new = set_frontmatter_field("Body only.\n", "status", "DRAFT")
        self.assertTrue(new.startswith("---\nstatus: DRAFT\n---\n"))
        self.assertIn("Body only.", new)

    def test_updates_existing_scalar(self):
        text = "---\nstatus: DRAFT\nfoo: bar\n---\nBody.\n"
        new = set_frontmatter_field(text, "status", "DONE")
        fields, _ = parse_frontmatter(new)
        self.assertEqual(fields["status"], "DONE")
        self.assertEqual(fields["foo"], "bar")  # preserved

    def test_appends_when_key_missing(self):
        text = "---\nstatus: DRAFT\n---\nBody.\n"
        new = set_frontmatter_field(text, "last_verified", "2026-05-15")
        fields, _ = parse_frontmatter(new)
        self.assertEqual(fields["status"], "DRAFT")
        self.assertEqual(fields["last_verified"], "2026-05-15")

    def test_list_value_serialized_flow(self):
        text = "---\nstatus: DRAFT\n---\nBody.\n"
        new = set_frontmatter_field(text, "dependencies", ["007-02", "adr-0004"])
        self.assertIn("dependencies: [007-02, adr-0004]", new)

    def test_block_list_collapsed_to_flow_on_update(self):
        text = ("---\ndependencies:\n  - old-1\n  - old-2\n"
                "status: DRAFT\n---\nBody.\n")
        new = set_frontmatter_field(text, "dependencies", ["new-1"])
        self.assertIn("dependencies: [new-1]", new)
        self.assertNotIn("- old-1", new)
        # Ensure surrounding fields preserved
        fields, _ = parse_frontmatter(new)
        self.assertEqual(fields["status"], "DRAFT")

    def test_idempotent(self):
        text = "---\nstatus: DRAFT\n---\nBody.\n"
        once = set_frontmatter_field(text, "status", "DONE")
        twice = set_frontmatter_field(once, "status", "DONE")
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
