"""Budget + relocation guard for the lean always-loaded primer (spec 076-01).

Spec 076 leans jig's own `CLAUDE.md`: the Hot Cache is re-partitioned into an
*index* of one-line claims + links, while the dense decision-summary prose is
relocated to `docs/memory/glossary.md` (reachable on demand via `/jig:explain`
through the merged lexicon). This test pins the slice's acceptance criteria so
the primer cannot silently regrow back into the heavy shape:

  AC #2 — every relocated term resolves via the merged lexicon loader.
  AC #3 — the Hot Cache is the index shape (no dense multi-sentence ADR
          paragraphs left in the always-loaded file).
  AC #4 — a budget guard fails when `CLAUDE.md` regrows past the cap.
  AC #5 — the every-turn "keep-inline" facts stay present in `CLAUDE.md`.

Run:
    python3 scripts/test_lean_primer.py
    # or from repo root:
    python3 -m unittest scripts.test_lean_primer
"""

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
GLOSSARY = REPO_ROOT / "docs" / "memory" / "glossary.md"

# AC #4 — the always-on budget, resolved during DRAFT review (spec 076-01).
# Tied to spec-055's "dumb zone" framing: the always-loaded primer is re-read
# every turn, so it must stay small. Caps are ~half the DRAFT-time size
# (109 lines / 27,802 bytes).
MAX_LINES = 70
MAX_BYTES = 14336  # 14 KiB

sys.path.insert(0, str(REPO_ROOT / "skills" / "_common"))
import lexicon  # noqa: E402


def _glossary_sections(text: str) -> "dict[str, str]":
    """Map each `## Term` H2 key -> its section body (until the next H2),
    using the same H2 recognition + key normalization as the lexicon loader."""
    out: "dict[str, str]" = {}
    matches = list(lexicon._H2_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[lexicon._term_key(m.group(1).strip())] = text[start:end]
    return out

# AC #2 — definitional Hot Cache entries relocated to the glossary. Each must
# resolve through the merged lexicon loader (the /jig:explain home). Listed by
# their human term; normalized to the loader's key via lexicon._term_key.
RELOCATED_TERMS = [
    "Lifecycle-family spine",
    "Closed-spec drift",
    "Spec-gate model",
    "Security floor",
    "Review-evidence gate",
    "Worktree-aware reservation",
    "Context-cost discipline",
    "Thin-orchestrator",
    "Token-usage tracking",
    "Slice-claim on IN_PROGRESS",
    "Solo→team re-detection",
    "Vocabulary barrier / lexicon",
    "Status board",
]

# AC #5 — the known behavioral guards (push, not pull) that MUST stay inline in
# the primer. A guard relocated to the glossary stops guarding, since
# /jig:explain is pull. Each string is the *full directive* (not a weak word
# like "v2" or "compress"), so relocating the directive — not just deleting the
# word — fails CI. NB (honest scope, per frame-critique round 2): this is a
# whitelist backstop for KNOWN guards; it cannot prove an *unlisted* guard
# wasn't relocated. Completeness is upheld by the slice AC #1 classification
# rule applied at authoring/memory-sync time + caught in review — not by this
# test alone.
KEEP_INLINE_MARKERS = [
    "MERGING main→v2 (not rebase)",    # branch-routing directive (not just "v2")
    "PARKED — don't re-propose",       # don't re-propose the servo oracle boundary
    "only at the *third*",             # extract-at-third-transition rule
    "Do not modify [docs/conventions.md](docs/conventions.md) without explicit human approval",
    "Reviewer subagent is read-only",  # reviewer write-ban
    "${CLAUDE_PLUGIN_ROOT}",           # hook-path rule
    "never bare names",                # the hook-path directive itself
    "never jq",                        # Python-3-for-JSON rule
    "adr-NNNN-<slug>.md",              # ADR/slice path convention
    "**compress** its Active-specs entry",  # compress-on-spec-close rule
]

# AC #3 — dense phrasing that lived in the heavy Hot Cache and now belongs only
# in the glossary. Its absence from CLAUDE.md is the "index shape" signal. This
# is a representative sample, not an exhaustive set — enough to prove the dense
# bodies moved.
RELOCATED_PROSE_FRAGMENTS = [
    "pushing from the temp worktree breaks relative-`origin` repos",
    "cache-TTL and model-downgrade were falsified",
    "Opus hand-rolled ran ~3× high",
]


class BudgetGuard(unittest.TestCase):
    """AC #4 — CLAUDE.md stays under the line AND byte cap."""

    @classmethod
    def setUpClass(cls):
        cls.text = CLAUDE_MD.read_text(encoding="utf-8")
        cls.raw = CLAUDE_MD.read_bytes()

    def test_line_budget(self):
        n = self.text.count("\n") + (0 if self.text.endswith("\n") else 1)
        self.assertLessEqual(
            n, MAX_LINES,
            f"CLAUDE.md has {n} lines; budget is {MAX_LINES} (spec 076-01 / "
            f"spec-055 dumb-zone). Relocate prose to docs/memory/glossary.md.",
        )

    def test_byte_budget(self):
        self.assertLessEqual(
            len(self.raw), MAX_BYTES,
            f"CLAUDE.md is {len(self.raw)} bytes; budget is {MAX_BYTES} "
            f"(spec 076-01). Relocate prose to docs/memory/glossary.md.",
        )


class RelocatedTermsResolve(unittest.TestCase):
    """AC #2 — every relocated term resolves through the merged lexicon."""

    @classmethod
    def setUpClass(cls):
        cls.merged = lexicon.load(REPO_ROOT)

    def test_each_relocated_term_resolvable(self):
        for term in RELOCATED_TERMS:
            key = lexicon._term_key(term)
            with self.subTest(term=term):
                self.assertIn(
                    key, self.merged,
                    f"'{term}' (key '{key}') must resolve via /jig:explain — "
                    f"add a `## {term}` entry to docs/memory/glossary.md.",
                )
                entry = self.merged[key]
                self.assertTrue(
                    (entry.get("plain") or entry.get("short") or "").strip(),
                    f"'{term}' resolves but has empty definition prose.",
                )

    def test_index_display_term_equals_resolvable_key(self):
        # Frame-critique round 3 — the user-facing recovery starts from the BOLD
        # index term in CLAUDE.md, then runs /jig:explain on it. So the displayed
        # term must equal the resolvable lexicon key, or the reader copies a term
        # that misses. Assert each relocated term appears verbatim as **term** in
        # the primer (ties this hand-list to the real index; catches drift like
        # index "Thin-orchestrator" vs glossary "Thin-orchestrator discipline").
        claude = CLAUDE_MD.read_text(encoding="utf-8")
        for term in RELOCATED_TERMS:
            with self.subTest(term=term):
                self.assertIn(
                    f"**{term}**", claude,
                    f"index display term for '{term}' must equal its glossary "
                    f"key so /jig:explain on the copied index term resolves.",
                )

    def test_each_relocated_entry_links_canonical_source(self):
        # AC #2(b) — the glossary entry is a *summary*; full detail stays in the
        # linked ADR/spec (the source of truth). Each relocated entry must carry
        # at least one markdown link so detail is recoverable in one hop.
        for term in RELOCATED_TERMS:
            key = lexicon._term_key(term)
            with self.subTest(term=term):
                prose = self.merged.get(key, {}).get("plain", "")
                self.assertIn(
                    "](", prose,
                    f"relocated entry '{term}' must link its canonical "
                    f"ADR/spec source (recoverability, not lossless copy).",
                )

    def test_relocated_entries_are_single_paragraph(self):
        # Latent-bug guard (frame-critique round 2): the loader recovers only the
        # FIRST paragraph after each `## Term` H2 (lexicon._first_paragraph). If a
        # relocated entry grows a second paragraph, /jig:explain silently drops
        # it while the resolvability test still passes. Pin every relocated entry
        # to a single paragraph so on-demand recovery stays lossless.
        sections = _glossary_sections(GLOSSARY.read_text(encoding="utf-8"))
        for term in RELOCATED_TERMS:
            key = lexicon._term_key(term)
            body = sections.get(key, "")
            paras = [p for p in re.split(r"\n[ \t]*\n", body.strip()) if p.strip()]
            with self.subTest(term=term):
                self.assertEqual(
                    len(paras), 1,
                    f"relocated '{term}' must be ONE paragraph so the loader "
                    f"recovers it whole; found {len(paras)} (detail past para 1 "
                    f"is silently dropped from /jig:explain).",
                )


class IndexShape(unittest.TestCase):
    """AC #3 — the dense ADR paragraphs are gone from the always-loaded file
    and the relocation is recorded (not left implicit)."""

    @classmethod
    def setUpClass(cls):
        cls.claude = CLAUDE_MD.read_text(encoding="utf-8")
        cls.glossary = GLOSSARY.read_text(encoding="utf-8")

    def test_dense_prose_relocated(self):
        for frag in RELOCATED_PROSE_FRAGMENTS:
            with self.subTest(fragment=frag):
                self.assertNotIn(
                    frag, self.claude,
                    "dense prose must live in the glossary, not the primer",
                )
                self.assertIn(
                    frag, self.glossary,
                    "relocated prose must be present in the glossary",
                )

    def test_relocation_recorded(self):
        # AC #1/#3 — the classification/relocation rule is recorded, not implicit.
        self.assertIn("Relocated from the CLAUDE.md Hot Cache", self.glossary)


class KeepInlineSet(unittest.TestCase):
    """AC #5 — the every-turn facts remain inline in the primer."""

    @classmethod
    def setUpClass(cls):
        cls.text = CLAUDE_MD.read_text(encoding="utf-8")

    def test_keep_inline_markers_present(self):
        for marker in KEEP_INLINE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(
                    marker, self.text,
                    f"every-turn fact '{marker}' must stay inline in CLAUDE.md",
                )


if __name__ == "__main__":
    unittest.main()
