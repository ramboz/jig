"""Shipped jig lexicon + project-glossary overlay loader (spec 065-01).

Implements [ADR-0021]: jig ships a single canonical definition per term in
`lexicon.json` (sibling of this file). A consuming project may specialize or
extend that vocabulary via its `docs/memory/glossary.md`; the project layer
**wins** on a collision.

Two layers:
  - Shipped layer: `lexicon.json`, resolved relative to ``__file__`` so it is
    found whether this module is imported via ``sys.path`` (the _common test
    idiom), copied as scaffold/migrate machinery, or loaded by file path from
    a `python3 -c` hook with an arbitrary CWD.
  - Project layer: the project's `docs/memory/glossary.md`, parsed in its
    documented canonical format — each ``## Term`` (H2) heading followed by its
    first paragraph (the directive in `glossary.md.template`: *"Format:
    `## TERM`, followed by definition prose"*). Only H2 headings count; H3
    (``### ``) and other shapes contribute no override.

Term-key convention: keys are the **lowercased, whitespace-collapsed** term
(e.g. ``"spidr"``, ``"vertical slice"``, ``"adr"``). The overlay matcher
lowercases the glossary heading the same way, so a glossary ``## SPIDR``
overrides the shipped ``"spidr"`` entry case-insensitively.

Fail-soft: a missing project dir, a missing glossary, or a glossary that does
not match the documented format degrades to the shipped lexicon unchanged and
never raises.

Stdlib-only (no third-party imports) so the surfacing hook can parse it inside
a `python3 -c` invocation.
"""

import json
import re
from pathlib import Path

# Resolve the shipped lexicon relative to THIS file, not the CWD — so a hook
# running `python3 -c` from an arbitrary directory, and a scaffolded copy under
# `.claude/skills/_common/`, both find it.
_LEXICON_PATH = Path(__file__).resolve().parent / "lexicon.json"

# An H2 heading line: `## Term`. Captures the term text. Anchored to the start
# of a line; deliberately does NOT match `### ` (H3) or deeper — `^##` followed
# by a non-`#` rules those out.
_H2_RE = re.compile(r"(?m)^##(?!#)\s+(.+?)\s*$")


def _term_key(term: str) -> str:
    """Normalize a term into its stable lexicon key: lowercased with internal
    whitespace collapsed to single spaces. Matches glossary headings to shipped
    keys case-insensitively (``## SPIDR`` -> ``spidr``)."""
    return " ".join(term.lower().split())


def load_shipped() -> "dict[str, dict]":
    """Return the shipped lexicon (term key -> entry dict) from `lexicon.json`.

    Fail-soft: if the shipped file is somehow missing or unreadable, returns an
    empty dict rather than raising — the loader's contract is to never raise on
    a degraded environment.
    """
    try:
        data = json.loads(_LEXICON_PATH.read_text(errors="replace"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _parse_glossary_overlay(text: str) -> "dict[str, dict]":
    """Parse a project glossary's prose into an overlay dict.

    Each ``## Term`` (H2) heading -> a term key; the first non-blank paragraph
    after it -> the definition prose, stored as both ``short`` and ``plain`` (a
    prose glossary carries one definition, not the shipped two-tier split).

    Only H2 headings are recognized. Best-effort and total: any shape that does
    not match yields no entries (caller stays shipped-only).
    """
    overlay: "dict[str, dict]" = {}
    matches = list(_H2_RE.finditer(text))
    for i, m in enumerate(matches):
        term = m.group(1).strip()
        if not term:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        paragraph = _first_paragraph(body)
        if not paragraph:
            continue
        overlay[_term_key(term)] = {"short": paragraph, "plain": paragraph}
    return overlay


def _first_paragraph(body: str) -> str:
    """Return the first non-blank paragraph in `body` as a single-spaced
    string, or '' if there is none. Paragraphs are blank-line separated."""
    para_lines: "list[str]" = []
    for line in body.splitlines():
        if line.strip():
            para_lines.append(line.strip())
        elif para_lines:
            # Blank line after we started collecting -> paragraph ended.
            break
    return " ".join(para_lines)


def load(project_dir) -> "dict[str, dict]":
    """Return the merged lexicon: shipped definitions with the project's
    `docs/memory/glossary.md` overlay applied on top (project wins).

    `project_dir` is the root of the consuming project. The overlay is read
    from ``<project_dir>/docs/memory/glossary.md`` in its documented canonical
    format (``## Term`` H2 heading + first paragraph). A term present only in
    the shipped layer is kept; a term present only in the project glossary is
    added; a term in both resolves to the **project** definition.

    Fail-soft: a missing project dir / glossary, or a glossary that does not
    match the format, returns the shipped lexicon unchanged. Never raises.
    """
    merged = load_shipped()
    try:
        gloss_path = Path(project_dir) / "docs" / "memory" / "glossary.md"
        if not gloss_path.is_file():
            return merged
        text = gloss_path.read_text(errors="replace")
        overlay = _parse_glossary_overlay(text)
    except (OSError, ValueError):
        return merged
    merged.update(overlay)
    return merged
