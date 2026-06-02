"""
Tests that docs/philosophy.md is a lean, skimmable external "why" doc
(spec 054-01).

Pins the mechanical acceptance criteria; the judgment ACs (prose quality,
no forked positioning vs. product-vision) are left to the reviewer subagent.

- AC#1 — the doc exists, has a single H1, and carries no forward-broken
  relative links.
- AC#2 — claims lead with skimmable bolded theses.
- AC#3 — it names jig's failure modes as sticky concepts.
- AC#4 — it handles objections, including the reviewer-isolation honesty
  (an independent check, not a hard sandbox / not a replacement for human
  review).
- AC#5 — it links product-vision.md for depth.

Run:
    python3 scripts/test_philosophy_doc.py
    # or from repo root:
    python3 -m unittest scripts.test_philosophy_doc
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
PHILOSOPHY = DOCS / "philosophy.md"

# Named failure modes the doc must present (AC#3). Matched case-insensitively
# on the sticky concept name so surrounding prose can vary.
FAILURE_MODES = (
    "horizontal drift",
    "scope creep",
    "dumb zone",
    "grading your own homework",
    "amnesia",
)

# Relative markdown links, excluding external (http/mailto) and pure anchors.
REL_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")


def _read() -> str:
    return PHILOSOPHY.read_text(encoding="utf-8")


class PhilosophyDocExists(unittest.TestCase):
    def test_exists(self) -> None:
        self.assertTrue(
            PHILOSOPHY.is_file(),
            "docs/philosophy.md must exist (spec 054-01 AC#1)",
        )

    def test_single_h1(self) -> None:
        h1s = [ln for ln in _read().splitlines() if ln.startswith("# ")]
        self.assertEqual(
            len(h1s), 1,
            f"philosophy.md must have exactly one H1; found {len(h1s)}",
        )


class PhilosophyLinksResolve(unittest.TestCase):
    """AC#1: no forward-broken relative links."""

    def test_relative_links_resolve_on_disk(self) -> None:
        targets = REL_LINK_RE.findall(_read())
        self.assertTrue(targets, "expected at least one relative link")
        for target in targets:
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue  # pure in-page anchor
            resolved = (DOCS / path_part).resolve()
            with self.subTest(link=target):
                self.assertTrue(
                    resolved.is_file(),
                    f"philosophy.md links {target!r} but {resolved} does not "
                    f"exist (forward-broken link — AC#1)",
                )


class PhilosophyIsSkimmable(unittest.TestCase):
    """AC#2: claims lead with bolded theses."""

    def test_has_multiple_bolded_theses(self) -> None:
        bold_leads = [
            ln for ln in _read().splitlines() if ln.lstrip().startswith("**")
        ]
        self.assertGreaterEqual(
            len(bold_leads), 6,
            f"philosophy.md should lead its claims with skimmable bolded "
            f"theses; found {len(bold_leads)} bold-lead lines (AC#2)",
        )


class PhilosophyNamesFailureModes(unittest.TestCase):
    """AC#3."""

    def test_names_failure_modes(self) -> None:
        low = _read().lower()
        for mode in FAILURE_MODES:
            with self.subTest(mode=mode):
                self.assertIn(
                    mode, low,
                    f"philosophy.md must name the {mode!r} failure mode (AC#3)",
                )


class PhilosophyHandlesObjections(unittest.TestCase):
    """AC#4: objections section + reviewer-isolation honesty."""

    def test_has_objections_section(self) -> None:
        self.assertRegex(
            _read(), r"(?im)^#{2,3}\s+.*objection",
            "philosophy.md must carry an objections section (AC#4)",
        )

    def test_reviewer_isolation_not_overclaimed(self) -> None:
        low = _read().lower()
        self.assertTrue(
            "not a hard sandbox" in low
            or "not a substitute" in low
            or "not a replacement" in low,
            "philosophy.md must not overclaim reviewer isolation — frame it as "
            "an independent check, not a sandbox or a replacement for human "
            "review (AC#4; aligns with workflow.md + product-vision)",
        )


class PhilosophyDefersToProductVision(unittest.TestCase):
    """AC#5."""

    def test_links_product_vision(self) -> None:
        self.assertIn(
            "product-vision.md", _read(),
            "philosophy.md must link product-vision.md for depth (AC#5)",
        )


if __name__ == "__main__":
    unittest.main()
