"""
Link-reachability + reading-path coherence lint for jig's entry-doc set
(spec 054-04).

The "front door" is a small set of docs a newcomer reads in sequence:
README -> philosophy -> adoption-readiness -> prompt cookbook -> workflow.
This lint pins two things:

1. **Every relative link in those docs resolves — file AND #anchor.** Slice
   054-03 broke an *inbound* anchor by renaming a README section
   (`#installation` -> `#install-shapes`); plain file-existence would not have
   caught it, so this guards that whole class. Links shown as examples inside
   fenced code blocks are ignored (the cookbook is full of them), and heading
   slugs are computed GitHub-style (link text only, punctuation dropped).
2. **The reading path is wired both ways.** The README routes to
   philosophy + cookbook + adoption-readiness, and adoption-readiness (which
   predates the philosophy doc and the cookbook) links onward to both, so it
   is not a one-directional dead-end.

Run:
    python3 scripts/test_docs_reading_path.py
    # or from repo root:
    python3 -m unittest scripts.test_docs_reading_path
"""

import re
import unittest
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

ENTRY_DOCS = [
    REPO_ROOT / "README.md",
    DOCS / "philosophy.md",
    DOCS / "adoption-readiness.md",
    DOCS / "prompts.md",
    DOCS / "workflow.md",
]

REL_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:)([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.MULTILINE)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")  # [text](url) -> text


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _strip_code_fences(text: str) -> str:
    """Drop ``` fenced code blocks so links/headings shown as examples inside
    them aren't treated as live links or real headings."""
    out, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


@lru_cache(maxsize=None)
def _slugs(path: Path) -> frozenset:
    """GitHub-style heading slugs for a markdown file: strip fenced blocks,
    reduce `[text](url)` to `text`, lowercase, drop punctuation (keep word
    chars / spaces / hyphens), spaces -> hyphens."""
    out = set()
    for heading in HEADING_RE.findall(_strip_code_fences(_read(path))):
        heading = MD_LINK_RE.sub(r"\1", heading)
        slug = re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")
        out.add(slug)
    return frozenset(out)


class EntryDocLinksResolve(unittest.TestCase):
    """AC#4: every relative link in the entry-doc set resolves — file + anchor."""

    def test_links_and_anchors_resolve(self) -> None:
        failures = []
        for doc in ENTRY_DOCS:
            self.assertTrue(doc.is_file(), f"entry doc missing: {doc}")
            for target in REL_LINK_RE.findall(_strip_code_fences(_read(doc))):
                if target.startswith("#"):
                    fpath, anchor = doc, target[1:]
                else:
                    rel, _, anchor = target.partition("#")
                    fpath = doc.parent / rel
                if not fpath.exists():
                    failures.append(f"{doc.name} -> {target} (file missing)")
                    continue
                if anchor and fpath.suffix == ".md" \
                        and anchor not in _slugs(fpath):
                    failures.append(f"{doc.name} -> {target} (anchor missing)")
        self.assertEqual(
            failures, [],
            "broken links/anchors in the entry-doc set:\n  "
            + "\n  ".join(failures),
        )


class ReadingPathIsWired(unittest.TestCase):
    """AC#1-3: the path routes forward, and adoption-readiness is not a
    dead-end now that the philosophy doc and cookbook exist."""

    def setUp(self) -> None:
        self.readme = _read(REPO_ROOT / "README.md")
        self.adopt = _read(DOCS / "adoption-readiness.md")

    def test_readme_routes_to_path(self) -> None:
        for token in ("docs/philosophy.md", "docs/prompts.md",
                      "docs/adoption-readiness.md"):
            with self.subTest(token=token):
                self.assertIn(
                    token, self.readme,
                    f"README must route to {token} (reading path AC#1)",
                )

    def test_adoption_readiness_links_onward(self) -> None:
        # adoption-readiness predates philosophy.md + the cookbook; it must now
        # point onward to both so the path isn't one-directional (AC#3).
        for token in ("philosophy.md", "prompts.md"):
            with self.subTest(token=token):
                self.assertIn(
                    token, self.adopt,
                    f"adoption-readiness.md must link {token} so the reading "
                    f"path continues onward (AC#3)",
                )


if __name__ == "__main__":
    unittest.main()
