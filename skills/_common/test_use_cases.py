"""Tests for skills/_common/use_cases.py (spec slice 068-02).

Covers the use-case trace surface that slice 02 establishes and slice 03
reuses:
  - parse_use_cases(vision_text)  -> ordered {UC-id: goal} (tolerant of the
    id-less legacy shape — id-less bullets reported as unresolvable-but-present)
  - resolve_use_cases(cited, vision_text) -> ResolveResult(resolved, unresolvable)
  - classify_spec(spec_use_cases, vision_text) -> one of
    {no_section, empty, resolved, unresolvable}  (AC5's mechanical trigger)
  - next_use_case_id(vision_text) -> "UC-N"  (AC5b: max existing + 1, never reuse)

Plain-`python3`-runnable like the other _common tests; stdlib-only.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import use_cases  # noqa: E402

# A vision section with UC-N ids in the canonical shape.
VISION_WITH_IDS = """\
# Product vision

## Scope

- something

## Use cases

<!-- elicited: 2026-05-15 / status: filled -->

> _goal-level guidance prose here, [actor] can [goal]._

- UC-1: A crafter can search for a yarn by name
- UC-2: A crafter can see regional matches ranked by closeness
- UC-3: A crafter can filter matches by any region

## Stack

- node
"""

# Legacy id-less shape (what slice 01 shipped before this slice).
VISION_IDLESS = """\
## Use cases

<!-- elicited: 2026-05-15 / status: filled -->

- A crafter can search for a yarn by name
- A crafter can see regional matches ranked by closeness

## Stack
"""

# Mixed: some bullets carry ids, some are legacy id-less.
VISION_MIXED = """\
## Use cases

- UC-1: A crafter can search for a yarn by name
- A crafter can browse without an id
- UC-4: A crafter can open a retailer link

## Stack
"""

# No `## Use cases` section at all — the layer is not adopted (e.g. jig itself).
VISION_NO_SECTION = """\
# Product vision

## Scope

- something

## Stack

- python
"""

# Section present but empty (skipped / unfilled).
VISION_EMPTY_SECTION = """\
## Use cases

<!-- elicited: PENDING / status: unfilled -->

## Stack
"""


class ParseUseCasesTests(unittest.TestCase):
    """parse_use_cases reads the `## Use cases` body into an ordered map."""

    def test_parses_uc_n_ids_in_order(self):
        got = use_cases.parse_use_cases(VISION_WITH_IDS)
        self.assertEqual(
            list(got.keys()), ["UC-1", "UC-2", "UC-3"],
            "ids must be returned in document order",
        )
        self.assertEqual(
            got["UC-1"], "A crafter can search for a yarn by name",
        )
        self.assertEqual(
            got["UC-3"], "A crafter can filter matches by any region",
        )

    def test_no_section_returns_empty_map(self):
        self.assertEqual(use_cases.parse_use_cases(VISION_NO_SECTION), {})

    def test_empty_section_returns_empty_map(self):
        self.assertEqual(use_cases.parse_use_cases(VISION_EMPTY_SECTION), {})

    def test_idless_legacy_bullets_do_not_crash(self):
        # Tolerant of the id-less legacy shape: it must not raise. Id-less
        # bullets contribute no resolvable id (they are present-but-
        # unresolvable, surfaced via parse_use_cases reporting zero ids).
        got = use_cases.parse_use_cases(VISION_IDLESS)
        self.assertEqual(got, {}, "id-less bullets yield no resolvable ids")

    def test_idless_bullets_counted_as_present(self):
        # The presence of id-less bullets is observable so a caller can tell
        # "section has entries but none carry ids" apart from "empty section".
        self.assertTrue(use_cases.has_entries(VISION_IDLESS))
        self.assertFalse(use_cases.has_entries(VISION_EMPTY_SECTION))
        self.assertFalse(use_cases.has_entries(VISION_NO_SECTION))

    def test_mixed_section_parses_only_the_id_bearing_bullets(self):
        got = use_cases.parse_use_cases(VISION_MIXED)
        self.assertEqual(list(got.keys()), ["UC-1", "UC-4"])

    def test_section_presence_predicate(self):
        self.assertTrue(use_cases.has_use_cases_section(VISION_WITH_IDS))
        self.assertTrue(use_cases.has_use_cases_section(VISION_EMPTY_SECTION))
        self.assertFalse(use_cases.has_use_cases_section(VISION_NO_SECTION))


class ResolveUseCasesTests(unittest.TestCase):
    """resolve_use_cases links a spec's cited ids to vision entries."""

    def test_resolved_id(self):
        res = use_cases.resolve_use_cases(["UC-3"], VISION_WITH_IDS)
        self.assertEqual(res.resolved, ["UC-3"])
        self.assertEqual(res.unresolvable, [])

    def test_unresolvable_id_is_reported_not_raised(self):
        res = use_cases.resolve_use_cases(["UC-9"], VISION_WITH_IDS)
        self.assertEqual(res.resolved, [])
        self.assertEqual(res.unresolvable, ["UC-9"])

    def test_mixed_resolved_and_unresolvable(self):
        res = use_cases.resolve_use_cases(["UC-1", "UC-9"], VISION_WITH_IDS)
        self.assertEqual(res.resolved, ["UC-1"])
        self.assertEqual(res.unresolvable, ["UC-9"])

    def test_empty_cited_list_resolves_to_nothing(self):
        res = use_cases.resolve_use_cases([], VISION_WITH_IDS)
        self.assertEqual(res.resolved, [])
        self.assertEqual(res.unresolvable, [])

    def test_no_section_makes_every_cited_id_unresolvable(self):
        res = use_cases.resolve_use_cases(["UC-1"], VISION_NO_SECTION)
        self.assertEqual(res.resolved, [])
        self.assertEqual(res.unresolvable, ["UC-1"])

    def test_resolved_predicate_helper(self):
        # Convenience predicate used by classify and slice 03.
        self.assertTrue(use_cases.is_resolved("UC-2", VISION_WITH_IDS))
        self.assertFalse(use_cases.is_resolved("UC-9", VISION_WITH_IDS))


class ClassifySpecTests(unittest.TestCase):
    """classify_spec — the deterministic AC5 trigger predicate.

    Returns one of: no_section / empty / resolved / unresolvable.
    """

    def test_no_section_is_the_no_op_dogfood_case(self):
        # CRITICAL: a project with specs but no use-case layer (jig itself)
        # must classify as no_section so NOTHING prompts or errors (AC5).
        self.assertEqual(
            use_cases.classify_spec(["UC-1"], VISION_NO_SECTION),
            "no_section",
        )
        # Even with an empty cited list, a missing section is no_section.
        self.assertEqual(
            use_cases.classify_spec([], VISION_NO_SECTION),
            "no_section",
        )

    def test_empty_field_trips_the_prompt(self):
        # AC4/AC5: the empty `use_cases:` field is the state a gap-creating
        # author actually produces — it must classify as `empty` (the trigger).
        self.assertEqual(
            use_cases.classify_spec([], VISION_WITH_IDS), "empty",
        )

    def test_resolved_when_all_cited_ids_resolve(self):
        self.assertEqual(
            use_cases.classify_spec(["UC-1", "UC-2"], VISION_WITH_IDS),
            "resolved",
        )

    def test_unresolvable_when_a_cited_id_is_missing(self):
        # AC5: an author who typed an unresolvable id ALSO trips the prompt.
        self.assertEqual(
            use_cases.classify_spec(["UC-9"], VISION_WITH_IDS),
            "unresolvable",
        )

    def test_partial_resolution_is_unresolvable(self):
        # Any unresolvable id taints the whole classification → prompt.
        self.assertEqual(
            use_cases.classify_spec(["UC-1", "UC-9"], VISION_WITH_IDS),
            "unresolvable",
        )

    def test_none_cited_list_treated_as_empty(self):
        # `use_cases:` absent from frontmatter → parse_frontmatter omits the
        # key → caller passes None. With a section present that is `empty`.
        self.assertEqual(
            use_cases.classify_spec(None, VISION_WITH_IDS), "empty",
        )

    def test_no_section_wins_even_with_unresolvable_id(self):
        # Section absence is checked first: layer-not-adopted always no_section.
        self.assertEqual(
            use_cases.classify_spec(["UC-9"], VISION_NO_SECTION),
            "no_section",
        )


class NextUseCaseIdTests(unittest.TestCase):
    """next_use_case_id — AC5b additive allocation (max existing + 1)."""

    def test_next_after_three(self):
        self.assertEqual(use_cases.next_use_case_id(VISION_WITH_IDS), "UC-4")

    def test_first_id_when_section_empty(self):
        self.assertEqual(
            use_cases.next_use_case_id(VISION_EMPTY_SECTION), "UC-1",
        )

    def test_first_id_when_no_section(self):
        self.assertEqual(use_cases.next_use_case_id(VISION_NO_SECTION), "UC-1")

    def test_never_reuses_a_retired_number(self):
        # Max + 1, not count + 1: a gap (UC-2 deleted) must not be back-filled.
        vision = (
            "## Use cases\n\n"
            "- UC-1: a can x\n"
            "- UC-3: a can z\n"
            "- UC-7: a can w\n\n"
            "## Stack\n"
        )
        self.assertEqual(use_cases.next_use_case_id(vision), "UC-8")

    def test_first_id_with_idless_legacy_entries(self):
        # No UC-N ids present yet (legacy) → start at UC-1 even though the
        # section has bullets.
        self.assertEqual(use_cases.next_use_case_id(VISION_IDLESS), "UC-1")


class NearDuplicateTests(unittest.TestCase):
    """is_near_duplicate — AC5b(ii) grow-quality guard helper.

    The confirm step routes an apparent match back to (a)-cite rather than
    minting a duplicate. The predicate is a deterministic textual signal the
    conversational confirm step consults — judgment still owns the final call.
    """

    def test_exact_match_is_near_duplicate(self):
        existing = use_cases.parse_use_cases(VISION_WITH_IDS)
        hit = use_cases.is_near_duplicate(
            "A crafter can search for a yarn by name", existing,
        )
        self.assertEqual(hit, "UC-1")

    def test_case_and_whitespace_insensitive(self):
        existing = use_cases.parse_use_cases(VISION_WITH_IDS)
        hit = use_cases.is_near_duplicate(
            "  a CRAFTER can   search for a yarn by name ", existing,
        )
        self.assertEqual(hit, "UC-1")

    def test_distinct_entry_is_not_a_duplicate(self):
        existing = use_cases.parse_use_cases(VISION_WITH_IDS)
        self.assertIsNone(
            use_cases.is_near_duplicate(
                "An admin can revoke a teammate's access", existing,
            )
        )


if __name__ == "__main__":
    unittest.main()
