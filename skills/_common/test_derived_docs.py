"""Tests for `_common/derived_docs.py`."""

from __future__ import annotations

import unittest
from pathlib import Path

from derived_docs import duplicate_ids, id_from_numeric_prefix


class DuplicateIdsTests(unittest.TestCase):
    def test_no_duplicates_returns_empty(self):
        self.assertEqual(
            duplicate_ids([("001", "001-a.md"), ("002", "002-b.md")]), {}
        )

    def test_reports_the_id_and_every_claimant(self):
        self.assertEqual(
            duplicate_ids([
                ("017", "017-first.md"),
                ("018", "018-other.md"),
                ("017", "017-second.md"),
            ]),
            {"017": ["017-first.md", "017-second.md"]},
        )

    def test_claimants_are_sorted_so_the_message_is_stable(self):
        """Two runs over the same tree must name the colliding files in the
        same order — CI output that reorders itself reads as a new failure."""
        forward = duplicate_ids([("017", "b.md"), ("017", "a.md")])
        reverse = duplicate_ids([("017", "a.md"), ("017", "b.md")])
        self.assertEqual(forward, reverse)
        self.assertEqual(forward["017"], ["a.md", "b.md"])

    def test_ids_are_sorted_so_the_message_is_stable(self):
        dupes = duplicate_ids([
            ("020", "020-a.md"), ("020", "020-b.md"),
            ("003", "003-a.md"), ("003", "003-b.md"),
        ])
        self.assertEqual(list(dupes), ["003", "020"])

    def test_three_claimants_all_reported(self):
        """Renumbering one of three still leaves a collision, so the message
        has to name all of them, not just the first pair."""
        dupes = duplicate_ids([("017", "c.md"), ("017", "a.md"), ("017", "b.md")])
        self.assertEqual(dupes, {"017": ["a.md", "b.md", "c.md"]})

    def test_empty_input(self):
        self.assertEqual(duplicate_ids([]), {})


class IdFromNumericPrefixTests(unittest.TestCase):
    def test_reads_the_leading_digits(self):
        self.assertEqual(id_from_numeric_prefix(Path("017-some-slug.md")), "017")

    def test_directory_name_works_the_same(self):
        self.assertEqual(id_from_numeric_prefix(Path("/x/099-a-spec")), "099")

    def test_adr_style_prefix_is_read_after_its_word_prefix(self):
        self.assertEqual(
            id_from_numeric_prefix(Path("adr-0041-slug.md"), prefix="adr-"),
            "0041",
        )

    def test_unnumbered_name_returns_none(self):
        self.assertIsNone(id_from_numeric_prefix(Path("README.md")))

    def test_wrong_word_prefix_returns_none(self):
        self.assertIsNone(
            id_from_numeric_prefix(Path("017-bug.md"), prefix="adr-")
        )

    def test_id_keeps_its_leading_zeros(self):
        """`017` and `17` are the same number but different ids on disk; the
        board renders the padded form, so collisions are compared padded."""
        self.assertEqual(id_from_numeric_prefix(Path("007-x.md")), "007")


if __name__ == "__main__":
    unittest.main()
