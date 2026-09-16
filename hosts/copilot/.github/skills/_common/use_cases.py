"""Use-case trace resolver + mechanical trigger predicate (spec 068-02).

The use-case breadth layer ([ADR-0025](../../docs/decisions/adr-0025-use-cases-breadth-layer.md))
captures a project's intended user-facing behaviors as a `## Use cases`
section in the project vision (slice 068-01 — a *seed*). Slice 068-02 makes
each entry **machine-resolvable** by giving it a stable `UC-N` id and lets a
spec record which use case(s) it serves via a `use_cases:` frontmatter list.

This module is the deterministic core of that trace surface — a sibling of
`parsing.py` / `lexicon.py`, stdlib-only:

  - ``parse_use_cases(vision_text)`` — read the `## Use cases` section body
    into an ordered ``{UC-id: goal-text}`` mapping. **Tolerant of the id-less
    legacy shape** slice 01 shipped: a bullet with no `UC-N:` prefix is
    *present-but-unresolvable*, contributing no id (never crashes).
  - ``resolve_use_cases(cited, vision_text)`` — given a spec's cited ids,
    report which **resolve** to a vision entry and which are **unresolvable**.
  - ``classify_spec(spec_use_cases, vision_text)`` — the AC5 **mechanical
    trigger** predicate: one of ``no_section`` / ``empty`` / ``resolved`` /
    ``unresolvable`` for a single spec. ``no_section`` (the layer is not
    adopted — e.g. jig's own repo) is the **no-op** state: nothing prompts.
  - ``next_use_case_id(vision_text)`` — AC5(b) additive allocation: the next
    free ``UC-N`` (``max(existing) + 1``; **never reuses a retired number**).
  - ``is_near_duplicate(text, existing)`` — AC5(b)(ii) grow-quality guard: a
    deterministic textual signal the conversational confirm step consults to
    route an apparent match back to *cite* instead of minting a duplicate.
    (Signature note: unlike the other readers, this takes the **pre-parsed**
    ``{UC-id: goal}`` map from ``parse_use_cases`` — not raw ``vision_text`` —
    because the confirm step has already parsed the section to display it.)

**Id format = ``UC-N``** — a plain integer, append-only, stable under
reorder/edit/delete (mirrors jig's spec ``NNN`` / ADR ``NNNN`` numbering
culture; slug-safe so it round-trips through `parsing.py`'s unquoted flow-list
serializer). Each `## Use cases` entry is e.g.
``- UC-1: A crafter can search for a yarn by name``.

Slice 03 (the project-wide bidirectional coverage check) reuses
``parse_use_cases`` + ``resolve_use_cases`` — the API is shaped for that reuse.
This module does **not** build slice 03's coverage check.
"""

import re

# Classification outcomes for `classify_spec` — the AC5 mechanical trigger.
# `RESOLVED` is the only non-prompting outcome when a section exists;
# `NO_SECTION` is the layer-not-adopted no-op (nothing prompts or errors).
NO_SECTION = "no_section"
EMPTY = "empty"
RESOLVED = "resolved"
UNRESOLVABLE = "unresolvable"

# A `## Use cases` H2 heading line. Anchored to line start; `(?!#)` rules out
# `### ` (H3) and deeper — same shape as lexicon.py's `_H2_RE`.
_USE_CASES_HEADING_RE = re.compile(r"(?im)^##(?!#)\s+use\s+cases\s*$")

# A bullet carrying a `UC-N:` id, e.g. `- UC-1: A crafter can search ...`.
# Captures the integer and the goal text. Tolerant of `*`/`+` bullet markers
# and extra leading whitespace; case-insensitive on the `UC` prefix.
_UC_BULLET_RE = re.compile(
    r"(?im)^\s*[-*+]\s+UC-(\d+)\s*:\s*(.+?)\s*$"
)

# Any list bullet (id-bearing or not) — used to tell "section has id-less
# legacy entries" apart from "section is empty". Excludes blockquote (`>`)
# guidance lines, which are prose, not entries.
_ANY_BULLET_RE = re.compile(r"(?im)^\s*[-*+]\s+(?!>)\S")


class ResolveResult:
    """Outcome of `resolve_use_cases`: which cited ids resolve, which don't.

    Attributes:
      - ``resolved`` — cited ids that map to a vision `UC-N` entry, in the
        order they were cited.
      - ``unresolvable`` — cited ids with no matching vision entry, in cited
        order. **Reported, never raised** (AC3).
    """

    __slots__ = ("resolved", "unresolvable")

    def __init__(self, resolved, unresolvable):
        self.resolved = resolved
        self.unresolvable = unresolvable

    def __repr__(self):  # pragma: no cover — debugging aid only
        return (f"ResolveResult(resolved={self.resolved!r}, "
                f"unresolvable={self.unresolvable!r})")

    def __eq__(self, other):  # pragma: no cover — test convenience
        return (isinstance(other, ResolveResult)
                and self.resolved == other.resolved
                and self.unresolvable == other.unresolvable)


def _use_cases_section_body(vision_text: str):
    """Return the `## Use cases` section body (text between its heading and the
    next H2 / EOF), or ``None`` when the section is absent.

    The absence vs. empty-body distinction is load-bearing: ``None`` ⇒ the
    layer is not adopted (``no_section``); ``""`` ⇒ adopted but empty.
    """
    m = _USE_CASES_HEADING_RE.search(vision_text)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"(?m)^##(?!#)\s", vision_text[start:])
    end = start + (nxt.start() if nxt else len(vision_text) - start)
    return vision_text[start:end]


def has_use_cases_section(vision_text: str) -> bool:
    """True iff the vision carries a `## Use cases` H2 section (filled or not).

    The negation is the no-op signal: no section ⇒ the breadth layer is not
    adopted for this project, so AC5's trigger must stay silent.
    """
    return _USE_CASES_HEADING_RE.search(vision_text) is not None


def has_entries(vision_text: str) -> bool:
    """True iff the `## Use cases` section contains at least one list bullet
    (id-bearing OR id-less legacy). Distinguishes a populated-but-id-less
    legacy section from a truly empty one. False when the section is absent."""
    body = _use_cases_section_body(vision_text)
    if not body:
        return False
    return _ANY_BULLET_RE.search(body) is not None


def parse_use_cases(vision_text: str) -> "dict[str, str]":
    """Parse the `## Use cases` section into an ordered ``{UC-id: goal}`` map.

    Only bullets carrying a ``UC-N:`` id contribute. Id-less legacy bullets
    (the slice-01 shape) are tolerated — they are *present-but-unresolvable*
    and contribute no id, so a legacy section parses to ``{}`` without raising
    (use ``has_entries`` to detect that they exist). Ids are normalized to the
    canonical ``UC-N`` form. Insertion order = document order.

    Returns ``{}`` when the section is absent or carries no id-bearing bullet.

    Two limitations slice 03 inherits when it reuses this: **(1) no
    fenced-code awareness** — a ``- UC-N:`` line inside a fenced code block in
    the section body is parsed as a real entry (the same class of limitation
    `lexicon.py` carries; a real `## Use cases` body holds entries, not fences,
    so practical risk is low). **(2) duplicate ``UC-N`` ids last-win** silently
    — a hand-edit data error that repeats an id keeps only the last occurrence,
    with no signal; slice 03's coverage query would see only that one entry.
    """
    body = _use_cases_section_body(vision_text)
    if not body:
        return {}
    out: "dict[str, str]" = {}
    for m in _UC_BULLET_RE.finditer(body):
        uc_id = f"UC-{int(m.group(1))}"
        out[uc_id] = m.group(2).strip()
    return out


def _normalize_id(uc_id: str) -> str:
    """Normalize a cited id to the canonical ``UC-N`` form (strip, uppercase
    the prefix, drop a leading zero). A non-matching token is returned trimmed
    and uppercased so it compares cleanly and is reported verbatim-ish as
    unresolvable rather than silently dropped."""
    s = (uc_id or "").strip()
    m = re.fullmatch(r"(?i)uc-(\d+)", s)
    if m:
        return f"UC-{int(m.group(1))}"
    return s.upper()


def resolve_use_cases(cited, vision_text: str) -> ResolveResult:
    """Split a spec's cited use-case ids into resolved vs. unresolvable.

    ``cited`` is the spec's ``use_cases:`` frontmatter list (``parse_frontmatter``
    returns a list of strings); ``None`` is treated as the empty list. An id
    resolves iff a `UC-N` bullet with that id exists in the vision's
    `## Use cases` section. Unresolvable ids are **reported**, never raised
    (AC3). When the section is absent, every cited id is unresolvable.
    """
    known = parse_use_cases(vision_text)
    resolved, unresolvable = [], []
    for raw in (cited or []):
        uc_id = _normalize_id(raw)
        if uc_id in known:
            resolved.append(uc_id)
        else:
            unresolvable.append(uc_id)
    return ResolveResult(resolved, unresolvable)


def is_resolved(uc_id: str, vision_text: str) -> bool:
    """True iff ``uc_id`` resolves to a `UC-N` entry in the vision."""
    return _normalize_id(uc_id) in parse_use_cases(vision_text)


def classify_spec(spec_use_cases, vision_text: str) -> str:
    """Classify a single spec's trace state — the AC5 mechanical trigger.

    Returns exactly one of:
      - ``NO_SECTION`` — the vision has **no** `## Use cases` section: the
        breadth layer is not adopted (e.g. jig's own repo). **No-op state** —
        AC5's prompt must stay silent and nothing errors. Checked **first**, so
        a stray cited id on a layer-less project still classifies as no_section.
      - ``EMPTY`` — section present, but the spec cites **nothing**
        (``use_cases:`` empty or absent). This is the state a gap-creating
        author most naturally produces, and AC4 blesses it as non-erroring —
        so it is precisely what trips AC5's prompt.
      - ``RESOLVED`` — section present and **every** cited id resolves.
      - ``UNRESOLVABLE`` — section present and **at least one** cited id does
        not resolve (also trips the prompt: the author typed a bad id).

    ``spec_use_cases`` is the spec's ``use_cases:`` list (or ``None``).
    """
    if not has_use_cases_section(vision_text):
        return NO_SECTION
    cited = spec_use_cases or []
    if not cited:
        return EMPTY
    result = resolve_use_cases(cited, vision_text)
    if result.unresolvable:
        return UNRESOLVABLE
    return RESOLVED


def next_use_case_id(vision_text: str) -> str:
    """Return the next free ``UC-N`` id for an additive grow (AC5b).

    ``max(existing) + 1`` — **never** ``count + 1`` — so a retired number is
    never reused (a deleted ``UC-2`` is not back-filled). ``UC-1`` when the
    section is absent, empty, or carries only id-less legacy bullets.
    """
    existing = parse_use_cases(vision_text)
    if not existing:
        return "UC-1"
    highest = max(int(k.split("-", 1)[1]) for k in existing)
    return f"UC-{highest + 1}"


def _dedupe_key(text: str) -> str:
    """Normalize a goal string for duplicate comparison: lowercased, internal
    whitespace collapsed, surrounding whitespace stripped. (Same normalization
    idiom as lexicon.py's `_term_key`.)"""
    return " ".join((text or "").lower().split())


def is_near_duplicate(text: str, existing: "dict[str, str]"):
    """Return the ``UC-id`` of a near-duplicate existing entry, or ``None``.

    The AC5(b)(ii) grow-quality guard: before minting a new ``UC-N`` the
    confirm step checks the proposed goal against the seeded existing entries
    and, on an apparent match, routes back to path (a)-**cite** rather than
    creating a duplicate. This is a deterministic textual signal
    (whitespace/case-insensitive equality); the **judgment-driven confirm step
    owns the final call** — the predicate informs it, it does not replace it.

    ``existing`` is the ``{UC-id: goal}`` map from ``parse_use_cases``.
    """
    target = _dedupe_key(text)
    if not target:
        return None
    for uc_id, goal in existing.items():
        if _dedupe_key(goal) == target:
            return uc_id
    return None
