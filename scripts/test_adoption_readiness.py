"""
Docs-lint for the adoption-readiness guide (spec 048-02).

Slice 048-02 added `docs/adoption-readiness.md` — a jig-sized guide for
deciding whether and how to adopt jig — and linked it from the public
entry points. This is jig's first link-reachability assertion: it fails
if the guide goes missing or README's pointer to it dangles, so the
"entry points link to it" promise (AC #4/#5) can't silently rot.

Run:
    python3 scripts/test_adoption_readiness.py
    # or from repo root:
    python3 -m unittest scripts.test_adoption_readiness
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
PRODUCT_VISION = REPO_ROOT / "docs" / "product-vision.md"
GUIDE = REPO_ROOT / "docs" / "adoption-readiness.md"

MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _links_to(doc: Path, target_rel: str) -> bool:
    """True iff `doc` contains a markdown link whose href (minus any
    #anchor) resolves on disk to REPO_ROOT/target_rel. External and
    empty hrefs are ignored."""
    target = (REPO_ROOT / target_rel).resolve()
    base = doc.parent
    for href in MD_LINK_RE.findall(_read(doc)):
        href = href.split("#", 1)[0].strip()
        if not href or href.startswith(("http://", "https://", "mailto:")):
            continue
        if (base / href).resolve() == target:
            return True
    return False


class AdoptionGuideExists(unittest.TestCase):
    """AC #1 / AC #2: the guide is present and carries a readiness checklist."""

    def test_guide_file_present(self) -> None:
        self.assertTrue(
            GUIDE.is_file(),
            "docs/adoption-readiness.md must exist (spec 048-02 AC #1)",
        )

    def test_guide_has_readiness_checklist(self) -> None:
        self.assertIn(
            "readiness checklist", _read(GUIDE).lower(),
            "the guide must include a concrete readiness checklist "
            "(spec 048-02 AC #2)",
        )


class AdoptionGuideIsReachable(unittest.TestCase):
    """AC #4 / AC #5: the public entry points point at the guide and the
    links resolve. AC #5 requires README specifically; AC #4 names both
    README and product-vision, so we lint both entry points."""

    def test_readme_links_resolve_to_guide(self) -> None:
        self.assertTrue(
            _links_to(README, "docs/adoption-readiness.md"),
            "README.md must link to docs/adoption-readiness.md and the link "
            "must resolve to the on-disk guide (spec 048-02 AC #4/#5)",
        )

    def test_product_vision_links_resolve_to_guide(self) -> None:
        self.assertTrue(
            _links_to(PRODUCT_VISION, "docs/adoption-readiness.md"),
            "docs/product-vision.md must link to docs/adoption-readiness.md "
            "and the link must resolve to the on-disk guide (spec 048-02 "
            "AC #4)",
        )


if __name__ == "__main__":
    unittest.main()
