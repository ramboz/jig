"""Tests for skills/_common/parsing.py."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsing import (
    find_slice_file,
    find_slice_section,
    iter_slices,
    load_slice,
    parse_frontmatter,
    set_frontmatter_field,
    SliceLocation,
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


SLICE_FILE_018_01 = """\
---
status: IN_PROGRESS
dependencies: []
last_verified:
---

## Slice 018-01 — parser-foundation-and-dual-read

**Goal:** Add dual-read to the slice parser.

Body of slice 018-01.
"""

SLICE_FILE_018_02 = """\
---
status: DRAFT
dependencies: [018-01]
last_verified:
---

## Slice 018-02 — caller-recognition

**Goal:** Validate every helper.

Body of slice 018-02.
"""

SPEC_MD_WITH_ONLY_018_03 = """\
---
status: DRAFT
skill: spec-workflow
---

# Spec 018: slice-per-file

## Overview

Stuff.

## Slice 018-03 — scaffold-defaults

**STATUS: DRAFT**

Body of slice 018-03 still inside spec.md.
"""


class _SpecDirFixture(unittest.TestCase):
    """Creates a tmpdir spec dir and tears it down. Subclasses add files."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-parse-"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class FindSliceFileTests(_SpecDirFixture):
    """Slice 018-01 AC #1–#3, #6: find_slice_file resolution."""

    def test_returns_path_when_one_file_matches_heading(self):
        f = self.tmpdir / "slice-01-parser-foundation.md"
        f.write_text(SLICE_FILE_018_01)
        result = find_slice_file(self.tmpdir, "018-01")
        self.assertEqual(result, f)

    def test_returns_none_when_no_file_matches(self):
        # Empty dir
        self.assertIsNone(find_slice_file(self.tmpdir, "999-99"))

    def test_returns_none_when_files_present_but_none_match(self):
        (self.tmpdir / "slice-01.md").write_text(SLICE_FILE_018_01)
        self.assertIsNone(find_slice_file(self.tmpdir, "999-99"))

    def test_returns_none_when_dir_missing(self):
        self.assertIsNone(find_slice_file(
            self.tmpdir / "does-not-exist", "018-01"))

    def test_raises_when_multiple_files_match(self):
        # Both files have a `## Slice 018-01` heading — ambiguous.
        (self.tmpdir / "slice-01-a.md").write_text(SLICE_FILE_018_01)
        (self.tmpdir / "slice-01-b.md").write_text(SLICE_FILE_018_01)
        with self.assertRaises(SliceLookupError) as cm:
            find_slice_file(self.tmpdir, "018-01")
        self.assertIn("ambiguous", str(cm.exception).lower())

    def test_non_md_files_ignored(self):
        (self.tmpdir / "slice-01-parser.md").write_text(SLICE_FILE_018_01)
        # Decoy with matching content but wrong extension
        (self.tmpdir / "slice-01.md.bak").write_text(SLICE_FILE_018_01)
        (self.tmpdir / "slice-01.txt").write_text(SLICE_FILE_018_01)
        result = find_slice_file(self.tmpdir, "018-01")
        self.assertEqual(result.name, "slice-01-parser.md")

    def test_heading_match_wins_not_filename(self):
        # Filename says 018-99 but heading inside is 018-01 — heading wins.
        misnamed = self.tmpdir / "slice-99-wrong-name.md"
        misnamed.write_text(SLICE_FILE_018_01)
        # A file whose filename matches '018-01' but whose heading doesn't
        decoy = self.tmpdir / "slice-01-018-01-in-name-only.md"
        decoy.write_text(SLICE_FILE_018_02)  # heading says 018-02
        result = find_slice_file(self.tmpdir, "018-01")
        self.assertEqual(result, misnamed)

    def test_spec_md_in_same_dir_is_ignored(self):
        # spec.md MUST be ignored even if it happens to contain a Slice heading.
        (self.tmpdir / "spec.md").write_text(SPEC_MD_WITH_ONLY_018_03)
        # No sibling slice file for 018-03 — should return None
        self.assertIsNone(find_slice_file(self.tmpdir, "018-03"))


class LoadSliceTests(_SpecDirFixture):
    """Slice 018-01 AC #4, #6: load_slice dual-read."""

    def test_hits_slice_file_when_present(self):
        slice_path = self.tmpdir / "slice-01-foo.md"
        slice_path.write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text(SPEC_MD_WITH_ONLY_018_03)  # has 018-03, not 018-01

        loc = load_slice(spec_path, "018-01")
        self.assertEqual(loc.path, slice_path)
        self.assertEqual(loc.text, SLICE_FILE_018_01)
        self.assertEqual(loc.start, 0)
        self.assertEqual(loc.end, len(SLICE_FILE_018_01))
        self.assertEqual(loc.label, "018-01 — parser-foundation-and-dual-read")

    def test_falls_back_to_spec_md_when_no_slice_file(self):
        # Only spec.md, no slice file for 018-03
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text(SPEC_MD_WITH_ONLY_018_03)

        loc = load_slice(spec_path, "018-03")
        self.assertEqual(loc.path, spec_path)
        self.assertEqual(loc.text, SPEC_MD_WITH_ONLY_018_03)
        # Offsets span just the section, not the whole file
        self.assertGreater(loc.start, 0)
        self.assertLessEqual(loc.end, len(SPEC_MD_WITH_ONLY_018_03))
        self.assertIn("Slice 018-03", loc.text[loc.start:loc.end])
        self.assertEqual(loc.label, "018-03 — scaffold-defaults")

    def test_uniform_slicing_pattern_works_for_both_layouts(self):
        """Critical regression: callers can do loc.text[loc.start:loc.end]
        without branching on layout."""
        # Slice file
        slice_path = self.tmpdir / "slice-01-foo.md"
        slice_path.write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text(SPEC_MD_WITH_ONLY_018_03)

        loc_file = load_slice(spec_path, "018-01")
        loc_section = load_slice(spec_path, "018-03")

        # Both produce a usable "section" via the same access pattern
        section_file = loc_file.text[loc_file.start:loc_file.end]
        section_section = loc_section.text[loc_section.start:loc_section.end]

        self.assertIn("Slice 018-01", section_file)
        self.assertIn("Body of slice 018-01", section_file)
        self.assertIn("Slice 018-03", section_section)
        self.assertIn("Body of slice 018-03", section_section)

    def test_returns_slice_location_namedtuple(self):
        slice_path = self.tmpdir / "slice-01.md"
        slice_path.write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec\n")
        loc = load_slice(spec_path, "018-01")
        # SliceLocation has the documented field shape
        self.assertIsInstance(loc, SliceLocation)
        self.assertEqual(set(loc._fields),
                         {"path", "text", "start", "end", "label"})

    def test_no_slice_file_and_no_section_raises(self):
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec\n\nNo slices here.\n")
        with self.assertRaises(SliceLookupError):
            load_slice(spec_path, "999-99")

    def test_ambiguous_slice_file_raises(self):
        (self.tmpdir / "slice-01-a.md").write_text(SLICE_FILE_018_01)
        (self.tmpdir / "slice-01-b.md").write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec\n")
        with self.assertRaises(SliceLookupError):
            load_slice(spec_path, "018-01")

    def test_slice_file_with_leading_blank_lines_parses(self):
        slice_path = self.tmpdir / "slice-01.md"
        slice_path.write_text("\n\n" + SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec\n")
        loc = load_slice(spec_path, "018-01")
        self.assertEqual(loc.path, slice_path)
        self.assertIn("018-01", loc.label)


class IterSlicesTests(_SpecDirFixture):
    """Slice 018-02: iter_slices walks both file-per-slice and
    embedded-section layouts deterministically."""

    def test_all_in_spec_md_yields_embedded_sections(self):
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text(
            "# Spec X\n\n## Slice X-01 — alpha\n\nBody alpha.\n\n"
            "## Slice X-02 — beta\n\nBody beta.\n"
        )
        locs = list(iter_slices(spec_path))
        self.assertEqual([l.label for l in locs], ["X-01 — alpha", "X-02 — beta"])
        for loc in locs:
            self.assertEqual(loc.path, spec_path)
            self.assertIn("Slice " + loc.label[:4], loc.text[loc.start:loc.end])

    def test_all_in_slice_files_yields_files(self):
        (self.tmpdir / "slice-01-alpha.md").write_text(SLICE_FILE_018_01)
        (self.tmpdir / "slice-02-beta.md").write_text(SLICE_FILE_018_02)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec X\n\n## Overview\n\nNo slices here.\n")

        locs = list(iter_slices(spec_path))
        labels = [l.label for l in locs]
        self.assertEqual(labels, [
            "018-01 — parser-foundation-and-dual-read",
            "018-02 — caller-recognition",
        ])
        # Each yielded loc maps to a distinct slice file
        paths = {l.path for l in locs}
        self.assertEqual(len(paths), 2)
        self.assertTrue(all(p.suffix == ".md" and p.name != "spec.md"
                            for p in paths))

    def test_mixed_layout_yields_files_then_sections(self):
        (self.tmpdir / "slice-01-foo.md").write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text(SPEC_MD_WITH_ONLY_018_03)

        locs = list(iter_slices(spec_path))
        # File-based slice comes first (file walk), then embedded section.
        self.assertEqual(len(locs), 2)
        self.assertEqual(locs[0].label, "018-01 — parser-foundation-and-dual-read")
        self.assertEqual(locs[0].path.name, "slice-01-foo.md")
        self.assertEqual(locs[1].label, "018-03 — scaffold-defaults")
        self.assertEqual(locs[1].path, spec_path)

    def test_each_yielded_loc_supports_uniform_slicing(self):
        (self.tmpdir / "slice-01-foo.md").write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text(SPEC_MD_WITH_ONLY_018_03)

        for loc in iter_slices(spec_path):
            section = loc.text[loc.start:loc.end]
            self.assertIn("## Slice", section, f"empty section for {loc.label}")

    def test_no_slices_anywhere_yields_empty(self):
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec X\n\nNo slices.\n")
        self.assertEqual(list(iter_slices(spec_path)), [])

    def test_missing_spec_md_only_yields_slice_files(self):
        (self.tmpdir / "slice-01-foo.md").write_text(SLICE_FILE_018_01)
        # spec.md does not exist
        locs = list(iter_slices(self.tmpdir / "spec.md"))
        self.assertEqual(len(locs), 1)
        self.assertEqual(locs[0].path.name, "slice-01-foo.md")

    def test_slice_files_sorted_by_filename(self):
        # Deliberately create out-of-order
        (self.tmpdir / "slice-02-beta.md").write_text(SLICE_FILE_018_02)
        (self.tmpdir / "slice-01-alpha.md").write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec X\n")
        locs = list(iter_slices(spec_path))
        self.assertEqual([l.path.name for l in locs],
                         ["slice-01-alpha.md", "slice-02-beta.md"])

    def test_file_with_no_slice_header_is_skipped(self):
        # A `slice-*.md` file lacking a `## Slice` heading is silently
        # skipped — it's not a valid slice file.
        bad = self.tmpdir / "slice-99-not-a-slice.md"
        bad.write_text("Just some random content.\n")
        (self.tmpdir / "slice-01-good.md").write_text(SLICE_FILE_018_01)
        spec_path = self.tmpdir / "spec.md"
        spec_path.write_text("# Spec X\n")
        locs = list(iter_slices(spec_path))
        self.assertEqual([l.path.name for l in locs], ["slice-01-good.md"])


if __name__ == "__main__":
    unittest.main()
