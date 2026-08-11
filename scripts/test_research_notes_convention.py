"""
Tests the living research-note home convention (spec 108-01, ADR-0054).

This is a documentation + template convention, not a code path: there is no
`research.py` helper (deferred by ADR-0054). These tests pin the mechanical
acceptance criteria on the two shipped artifacts:

- AC#1 — `docs/research/TEMPLATE.md` carries the ADR-0054 frontmatter keys
  and body skeleton.
- AC#2 — `docs/research/README.md` declares the `00`-`09` seed boundary.
- AC#3/#4 — the index documents the `R-NNN` local-and-cheap numbering
  convention and the living-notes table.
- AC#5 — both hand-offs (inbox -> note, note -> decision/work) are
  documented, and the sequential (not competing) relationship to
  `docs/refinement-todo.md` is stated.
- AC#6 — the seed corpus (`00`-`09`) is still present (not renamed or
  deleted), and no research-note template leaked into the scaffold source
  under `templates/`. Content-level byte-equality is guarded by git and
  review, not asserted here (no in-repo baseline digest exists).

Run:
    python3 scripts/test_research_notes_convention.py
    # or from repo root:
    python3 -m unittest scripts.test_research_notes_convention
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "docs" / "research"
TEMPLATE = RESEARCH / "TEMPLATE.md"
INDEX = RESEARCH / "README.md"

SEED_FILES = (
    "00-starter-prompt.md",
    "01-research-skills-and-triggering.md",
    "02-research-hooks.md",
    "03-research-subagents-and-isolation.md",
    "04-research-spec-driven-and-spidr.md",
    "05-research-eval-driven-development.md",
    "06-research-12-factor-and-operations.md",
    "07-research-contracts-and-architecture.md",
    "08-research-ecc-lessons.md",
    "09-addition-memory-layer.md",
)

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TemplateExists(unittest.TestCase):
    def test_template_file_exists(self) -> None:
        self.assertTrue(
            TEMPLATE.is_file(),
            "docs/research/TEMPLATE.md must exist (AC#1)",
        )


class TemplateFrontmatter(unittest.TestCase):
    """AC#1: light frontmatter keys per ADR-0054."""

    def test_frontmatter_block_present(self) -> None:
        match = FRONTMATTER_RE.search(_read(TEMPLATE))
        self.assertIsNotNone(
            match,
            "docs/research/TEMPLATE.md must open with a YAML frontmatter "
            "block delimited by '---' (AC#1)",
        )

    def test_frontmatter_has_required_keys(self) -> None:
        match = FRONTMATTER_RE.search(_read(TEMPLATE))
        self.assertIsNotNone(match, "frontmatter block missing")
        block = match.group(1)
        for key in ("status", "topic", "created", "related"):
            with self.subTest(key=key):
                self.assertRegex(
                    block, rf"(?m)^{key}:",
                    f"TEMPLATE.md frontmatter must carry a {key!r} key (AC#1)",
                )

    def test_status_options_documented(self) -> None:
        text = _read(TEMPLATE)
        for option in ("OPEN", "CONCLUDED", "PARKED", "ABANDONED"):
            with self.subTest(option=option):
                self.assertIn(
                    option, text,
                    f"TEMPLATE.md must document the {option!r} status option "
                    "(AC#1)",
                )


class TemplateBodySkeleton(unittest.TestCase):
    """AC#1: question -> sources/findings -> pros/cons -> open questions ->
    conclusion, plus a Promoted to: hand-off line."""

    def test_has_question_section(self) -> None:
        self.assertRegex(
            _read(TEMPLATE), r"(?m)^##\s+Question",
            "TEMPLATE.md must carry a '## Question' section (AC#1)",
        )

    def test_has_conclusion_section(self) -> None:
        self.assertRegex(
            _read(TEMPLATE), r"(?m)^##\s+Conclusion",
            "TEMPLATE.md must carry a '## Conclusion' section (AC#1)",
        )

    def test_has_promoted_to_line(self) -> None:
        self.assertRegex(
            _read(TEMPLATE), r"(?m)^Promoted to:",
            "TEMPLATE.md must carry a 'Promoted to:' hand-off line (AC#1, "
            "AC#5)",
        )


class IndexExists(unittest.TestCase):
    def test_index_file_exists(self) -> None:
        self.assertTrue(
            INDEX.is_file(),
            "docs/research/README.md must exist (AC#2)",
        )


class IndexDeclaresSeedBoundary(unittest.TestCase):
    """AC#2: the 00-09 corpus is formally labeled frozen seed research."""

    def test_names_frozen(self) -> None:
        self.assertIn(
            "frozen", _read(INDEX).lower(),
            "README.md must declare the 00-09 corpus 'frozen' (AC#2)",
        )

    def test_names_seed_boundary_files(self) -> None:
        text = _read(INDEX)
        self.assertIn(
            "00-starter-prompt.md", text,
            "README.md must reference 00-starter-prompt.md by name (AC#2)",
        )
        self.assertIn(
            "09-addition-memory-layer.md", text,
            "README.md must reference 09-addition-memory-layer.md by name "
            "(AC#2)",
        )


class IndexDocumentsLivingNotes(unittest.TestCase):
    """AC#3/#4: living-notes table + R-NNN local-and-cheap numbering."""

    def test_has_living_notes_heading(self) -> None:
        self.assertRegex(
            _read(INDEX), r"(?m)^##\s+Living notes",
            "README.md must carry a '## Living notes' heading (AC#3)",
        )

    def test_documents_r_nnn_pattern(self) -> None:
        self.assertIn(
            "R-NNN", _read(INDEX),
            "README.md must document the R-NNN naming pattern (AC#4)",
        )

    def test_documents_local_and_cheap_numbering(self) -> None:
        self.assertIn(
            "local-and-cheap", _read(INDEX),
            "README.md must state numbering is 'local-and-cheap' (AC#4)",
        )


class IndexDocumentsHandoffs(unittest.TestCase):
    """AC#5: both hand-off directions, and the sequential (not competing)
    relationship to refinement-todo."""

    def test_documents_inbox_to_note_handoff(self) -> None:
        text = _read(INDEX).lower()
        # Assert the specific hand-off label, not just the words "inbox"/"note"
        # (which appear elsewhere). Tolerate the ASCII "->" or the "→" arrow.
        self.assertTrue(
            "inbox → note" in text or "inbox -> note" in text,
            "README.md must document the 'Inbox → note' hand-off direction "
            "(AC#5)",
        )
        # ...and the one-line inbox pointer to an R-NNN note it prescribes.
        self.assertRegex(
            text, r"→\s*r-\d|->\s*r-\d|pointer.{0,40}r-",
            "README.md must show the inbox one-line pointer to an R-NNN note "
            "(AC#5)",
        )

    def test_documents_note_to_decision_handoff(self) -> None:
        text = _read(INDEX).lower()
        self.assertTrue(
            "concluded" in text or "promoted to" in text,
            "README.md must document the note -> decision/work hand-off "
            "(AC#5)",
        )

    def test_documents_refinement_todo_relationship(self) -> None:
        self.assertIn(
            "refinement-todo", _read(INDEX),
            "README.md must describe the sequential relationship to "
            "docs/refinement-todo.md (AC#5)",
        )


class SeedCorpusPresent(unittest.TestCase):
    """AC#6: the seed corpus files are still present (not renamed or
    deleted). Content-level byte-equality is guarded by git and review, not
    asserted here — there is no in-repo baseline digest to compare against."""

    def test_all_seed_files_present(self) -> None:
        for name in SEED_FILES:
            with self.subTest(name=name):
                self.assertTrue(
                    (RESEARCH / name).is_file(),
                    f"seed corpus file {name!r} must still exist under "
                    "docs/research/ (AC#6)",
                )


class NoTemplateLeakIntoScaffoldSource(unittest.TestCase):
    """AC#1: the template is jig-internal, not shipped to adopters."""

    def test_no_research_dir_under_templates(self) -> None:
        self.assertFalse(
            (ROOT / "templates" / "docs" / "research").exists(),
            "no research-note template may leak into templates/ "
            "(scaffold source) — AC#1 non-goal",
        )

    def test_no_research_note_template_leaks_anywhere_under_templates(
        self,
    ) -> None:
        # Robust against the leak landing at any path (e.g. templates/TEMPLATE.md
        # or templates/research/): flag any file whose NAME or CONTENT signature
        # marks it a research-note template, not just the one hard-coded dir.
        templates = ROOT / "templates"
        offenders = []
        for path in templates.rglob("*"):
            if not path.is_file():
                continue
            if "research" in path.name.lower():
                offenders.append(path)
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            # The research-note template's unmistakable content signature.
            if "Promoted to:" in text and "open investigation" in text.lower():
                offenders.append(path)
        self.assertEqual(
            [str(p.relative_to(ROOT)) for p in offenders], [],
            "no research-note template may leak into templates/ "
            "(scaffold source) — AC#1 non-goal",
        )


if __name__ == "__main__":
    unittest.main()
