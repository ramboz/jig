"""
Tests that README.md's first-read status is current (spec 048-01).

The pre-048 README carried a stale `## Status` block claiming Tier 0
skills were "in spec/draft phase" and naming `001-01 greenfield-scaffold`
as the "First implementation slice" — both false now that Tier 0 + Tier 1
are effectively complete. Slice 048-01 replaced it with a current
`## Status & roadmap` section plus a gap-response table that links each
known comparison gap to its owner spec/slice.

This suite pins the fix so a future edit can't silently reintroduce the
stale wording or drop the gap map.

Run:
    python3 scripts/test_readme_status_current.py
    # or from repo root:
    python3 -m unittest scripts.test_readme_status_current
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

# Stale phrases the 048-01 fix removed; their return is a regression.
STALE_PHRASES = (
    "in spec/draft phase",
    "First implementation slice",
)

# External owner specs the gap-response map must link so future readers
# don't have to rediscover the triage (AC #4). These are the spec dir
# names, which appear in the link hrefs.
OWNER_SPECS = (
    "033-host-adapter-portability",
    "038-tier-reconciliation",
    "040-isolation-honesty",
    "045-review-lifecycle-gates",
    "046-scaffold-artifact-fidelity",
    "047-install-contract-verification",
    # Net-new security/secrets floor finding from the 2026-06-01 re-review,
    # routed to spec 052 (extended AC #2, landed via #26).
    "052-security-scaffold",
)

GAP_TABLE_HEADER_RE = re.compile(r"^\|\s*Gap\s*\|", re.MULTILINE)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _gap_table_region(text: str) -> str:
    """Return README text from the gap-response table header to the next
    section heading (or EOF), or '' if the table is absent. Scoping
    assertions to this region stops a stray owner-spec mention elsewhere
    in the README from satisfying AC #4 vacuously."""
    m = GAP_TABLE_HEADER_RE.search(text)
    if not m:
        return ""
    rest = text[m.start():]
    nxt = re.search(r"^#{1,6}\s", rest[1:], re.MULTILINE)
    return rest if nxt is None else rest[: nxt.start() + 1]


class ReadmeStatusIsCurrent(unittest.TestCase):
    """AC #1: README no longer implies early-draft status."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_no_stale_draft_status_wording(self) -> None:
        for phrase in STALE_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase, self.text,
                    f"README reintroduced stale status wording {phrase!r} "
                    f"(spec 048-01 removed it; Tier 0/1 are effectively complete)",
                )


class ReadmeHasGapResponseMap(unittest.TestCase):
    """AC #2 / AC #4: a gap-response table that links each gap's owner."""

    def setUp(self) -> None:
        self.text = _read(README)
        self.table = _gap_table_region(self.text)

    def test_gap_response_table_present(self) -> None:
        self.assertRegex(
            self.text, GAP_TABLE_HEADER_RE,
            "README must carry a gap-response table (a '| Gap |' header row) "
            "so a reader can see which comparison gaps are owned here vs. "
            "delegated to an owner spec (spec 048-01 AC #2)",
        )

    def test_gap_table_lists_at_least_eight_gaps(self) -> None:
        # AC #2 enumerates eight minimum gaps. Count table data rows
        # (pipe-leading lines in the region, minus the header and the
        # `|---|` separator) so a present-but-empty table can't pass.
        rows = [ln for ln in self.table.splitlines()
                if ln.lstrip().startswith("|") and "---" not in ln]
        data_rows = max(len(rows) - 1, 0)  # drop the header row
        self.assertGreaterEqual(
            data_rows, 8,
            f"gap-response table must list at least 8 gaps (AC #2); "
            f"found {data_rows} data rows",
        )

    def test_gap_map_links_owner_specs_in_table(self) -> None:
        for owner in OWNER_SPECS:
            with self.subTest(owner=owner):
                self.assertIn(
                    owner, self.table,
                    f"gap-response map must link owner spec {owner} inside the "
                    f"table region, not merely somewhere in the README (AC #4)",
                )

    def test_links_to_routed_gap_inventory(self) -> None:
        # Extended AC #2 (landed via #26): net-new gaps may be summarized
        # and linked to the spec's full routed inventory rather than
        # reproduced row-by-row. Pin that link so the route stays reachable.
        self.assertIn(
            "048-guidelines-gap-response/spec.md#gap-inventory-routed",
            self.table,
            "the gap map must link spec 048's full routed inventory so the "
            "net-new gaps stay discoverable (spec 048-01 extended AC #2)",
        )


if __name__ == "__main__":
    unittest.main()
