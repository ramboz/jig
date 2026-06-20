"""Docs-presence guard for the semantic-index guidance (spec 079-01).

Slice 079-01 adds a standing-guidance subsection to `docs/workflow.md`'s
context-cost discipline: *when* a semantic/code index pays for itself, *which*
standard options to reach for, and the detect-installed-else-recommend /
install-nothing stance — pointing jig's lean-context advice at the
highest-leverage deterministic turn-count lever (EngTip #26 / #23).

This test fails if that subsection goes missing or loses a load-bearing claim,
mirroring the sibling `test_context_cost_discipline.py` style. The guidance is
docs-only (AC #4): no new skill, no `.py`, nothing added to the always-loaded
`CLAUDE.md`.

Run:
    python3 scripts/test_semantic_index_guidance.py
    # or from repo root:
    python3 -m unittest scripts.test_semantic_index_guidance
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / "docs" / "workflow.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

HEADING = "Reach for a semantic/code index"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _subsection(text: str) -> str:
    """Return just the `### Reach for a semantic/code index` subsection body
    (from its heading to the next `###`/`##`), so assertions pin the new
    paragraphs rather than co-occurring words elsewhere in the file."""
    start = text.find(f"### {HEADING}")
    if start == -1:
        return ""
    rest = text[start + len(HEADING):]
    nxt = min(
        (i for i in (rest.find("\n### "), rest.find("\n## ")) if i != -1),
        default=len(rest),
    )
    return rest[:nxt]


class GuidanceSectionExists(unittest.TestCase):
    """AC #1 — the section exists under the context-cost-discipline guidance,
    covering when / which / detect-and-defer."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(WORKFLOW)
        cls.lower = cls.text.lower()
        cls.sub = _subsection(cls.text).lower()

    def test_heading_present(self):
        self.assertIn(
            f"### {HEADING}", self.text,
            "docs/workflow.md must carry the semantic-index guidance heading",
        )

    def test_lives_under_context_cost_discipline(self):
        # The subsection must sit inside the Context-cost discipline section,
        # not float elsewhere — it is a sibling of the other cost levers.
        cc = self.text.find("## Context-cost discipline")
        sec = self.text.find(f"### {HEADING}")
        nxt = self.text.find("\n## ", cc + 1)  # next top-level section
        self.assertGreater(sec, cc, "guidance must come after the section start")
        self.assertTrue(
            nxt == -1 or sec < nxt,
            "guidance must be inside the Context-cost discipline section",
        )

    def test_states_the_when(self):
        # The "when it pays for itself" threshold (repo size / turn count).
        # Scoped to the subsection so co-occurring words elsewhere in the
        # Context-cost section can't false-pass it.
        self.assertIn("when it pays for itself", self.sub)
        self.assertTrue(
            "turn" in self.sub and "grep" in self.sub,
            "the 'when' must frame the turn-count / search-round-trip tradeoff",
        )

    def test_states_the_which_portable_first(self):
        # Portable/public options centered; internal ones only "if available".
        # Use distinctive tokens ("lsp", not the substring "ide" which matches
        # "guide"/"provide"/etc.) so each is a real guard.
        for token in ("lsp", "tree-sitter", "glean", "kythe"):
            self.assertIn(token, self.sub, f"missing portable option: {token}")
        self.assertIn("if available", self.sub,
                      "internal tools must be qualified as 'if available'")

    def test_detect_installed_else_recommend(self):
        self.assertIn("detect-installed", self.sub)


class GuidanceInstallsNothing(unittest.TestCase):
    """AC #2 — install-nothing framing is explicit (recommend/orchestrate,
    never vendor or auto-install)."""

    def test_install_nothing_caveat(self):
        lower = _read(WORKFLOW).lower()
        self.assertIn("install nothing", lower)
        self.assertTrue(
            "never vendors or auto-installs" in lower
            or ("vendor" in lower and "auto-install" in lower),
            "must state jig never vendors / auto-installs an indexer",
        )


class GuidanceHonestAboutLimits(unittest.TestCase):
    """AC #3 — a recommendation is not a savings guarantee (context isn't
    free)."""

    def test_not_a_savings_guarantee(self):
        lower = _read(WORKFLOW).lower()
        self.assertIn("not a savings guarantee", lower)

    def test_context_isnt_free_caution(self):
        lower = _read(WORKFLOW).lower()
        self.assertIn("context isn't free", lower)


class GuidanceAddsNoAlwaysLoadedSurface(unittest.TestCase):
    """AC #4 — docs-only: the always-loaded CLAUDE.md gains no semantic-index
    section (the whole point is on-path-only-when-read guidance)."""

    def test_not_in_claude_md(self):
        self.assertNotIn(
            HEADING, _read(CLAUDE_MD),
            "the guidance must stay in docs/workflow.md, not the hot cache",
        )


if __name__ == "__main__":
    unittest.main()
