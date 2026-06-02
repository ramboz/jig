"""
Tests that README.md's first-read status is current AND that the public README
stays a lean routing hub (specs 048-01, 054-03).

History:
- 048-01 replaced a stale `## Status` block and ADDED a gap-response table to
  the README so a reader could see which comparison gaps were owned where.
- 054-03 moved that gap-response table OUT of the public README into
  CONTRIBUTING.md (its contributor-facing home), keeping the README a lean
  routing hub that links the philosophy doc + prompt cookbook. The
  stale-status guard stays on the README; the gap-table guards now target
  CONTRIBUTING.md, plus an inverse guard that the README no longer carries the
  table.

This suite pins both halves so a future edit can't silently reintroduce the
stale wording, re-bloat the README with the triage table, or drop the gap map
from CONTRIBUTING.

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
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"

# Stale phrases the 048-01 fix removed; their return to README is a regression.
STALE_PHRASES = (
    "in spec/draft phase",
    "First implementation slice",
)

# Owner specs the gap-response map must link (now inside CONTRIBUTING.md). The
# dir names appear in the link hrefs.
OWNER_SPECS = (
    "033-host-adapter-portability",
    "038-tier-reconciliation",
    "040-isolation-honesty",
    "045-review-lifecycle-gates",
    "046-scaffold-artifact-fidelity",
    "047-install-contract-verification",
    "052-security-scaffold",
)

GAP_TABLE_HEADER_RE = re.compile(r"^\|\s*Gap\s*\|", re.MULTILINE)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _gap_table_region(text: str) -> str:
    """Text from the gap-response table header to the next section heading (or
    EOF), or '' if the table is absent. Scoping assertions to this region stops
    a stray owner-spec mention elsewhere from satisfying the link checks
    vacuously."""
    m = GAP_TABLE_HEADER_RE.search(text)
    if not m:
        return ""
    rest = text[m.start():]
    nxt = re.search(r"^#{1,6}\s", rest[1:], re.MULTILINE)
    return rest if nxt is None else rest[: nxt.start() + 1]


class ReadmeStatusIsCurrent(unittest.TestCase):
    """AC #1 (048-01): README no longer implies early-draft status."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_no_stale_draft_status_wording(self) -> None:
        for phrase in STALE_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase, self.text,
                    f"README reintroduced stale status wording {phrase!r} "
                    f"(spec 048-01 removed it; Tier 0/1 are complete)",
                )


class ReadmeIsLeanRoutingHub(unittest.TestCase):
    """054-03: the public README is a routing hub — no internal gap triage,
    and it routes to the philosophy doc + the prompt cookbook."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_readme_has_no_gap_table(self) -> None:
        self.assertNotRegex(
            self.text, GAP_TABLE_HEADER_RE,
            "the gap-response table must NOT live in the public README — "
            "054-03 moved it to CONTRIBUTING.md to keep the front door lean",
        )

    def test_readme_routes_to_philosophy(self) -> None:
        self.assertIn(
            "docs/philosophy.md", self.text,
            "README must link docs/philosophy.md (the Why teaser routes there)",
        )

    def test_readme_routes_to_prompt_cookbook(self) -> None:
        self.assertIn(
            "docs/prompts.md", self.text,
            "README must link the prompt cookbook (docs/prompts.md)",
        )


class ContributingHasGapResponseMap(unittest.TestCase):
    """054-03: the gap-response map moved to CONTRIBUTING.md (048-01 AC #2/#4,
    retargeted)."""

    def setUp(self) -> None:
        self.text = _read(CONTRIBUTING)
        self.table = _gap_table_region(self.text)

    def test_gap_response_table_present(self) -> None:
        self.assertRegex(
            self.text, GAP_TABLE_HEADER_RE,
            "CONTRIBUTING.md must carry the gap-response table (a '| Gap |' "
            "header row) so contributors can see which comparison gaps are "
            "owned where (spec 048-01 AC #2, relocated by 054-03)",
        )

    def test_gap_table_lists_at_least_eight_gaps(self) -> None:
        rows = [ln for ln in self.table.splitlines()
                if ln.lstrip().startswith("|") and "---" not in ln]
        data_rows = max(len(rows) - 1, 0)  # drop the header row
        self.assertGreaterEqual(
            data_rows, 8,
            f"gap-response table must list at least 8 gaps (AC #2); "
            f"found {data_rows} data rows in CONTRIBUTING.md",
        )

    def test_gap_map_links_owner_specs_in_table(self) -> None:
        for owner in OWNER_SPECS:
            with self.subTest(owner=owner):
                self.assertIn(
                    owner, self.table,
                    f"gap-response map must link owner spec {owner} inside the "
                    f"table region of CONTRIBUTING.md (AC #4)",
                )

    def test_links_to_routed_gap_inventory(self) -> None:
        self.assertIn(
            "048-guidelines-gap-response/spec.md#gap-inventory-routed",
            self.table,
            "the gap map must link spec 048's full routed inventory so the "
            "net-new gaps stay discoverable (spec 048-01 extended AC #2)",
        )


if __name__ == "__main__":
    unittest.main()
