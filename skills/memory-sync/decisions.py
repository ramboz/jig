#!/usr/bin/env python3
"""jig lightweight-decisions helper (083-05).

Lives in the **tier-0** memory-sync skill (alongside `memory.py`) so the
always-scaffolded surfaces that reference it — the session-end memory-sync prompt
and `docs/decisions/lightweight-decisions.md` — keep their scaffold helper-closure
intact. `adr.py` (tier-1) manages the heavyweight `adr-*.md` records; this helper
manages the lightweight `lightweight-decisions.md` home — an idempotent append in
the file's own template format, so Phase 1's nudge-only file gains the
helper-backed determinism the rest of jig has. It is **not** a `memory.py`
subcommand (that helper owns `docs/memory/`; this file lives in `docs/decisions/`).

`ADR_TRIGGER` is the **single canonical source** (mirroring
[ADR-0031](../../docs/decisions/adr-0031-load-bearing-decision-adr-trigger.md))
for the load-bearing-decision ADR trigger sentence. Four consumer sites quote
it verbatim — this helper's routing rubric in `lightweight-decisions.md`, the two
reconcile checklists (`docs/workflow.md`, `skills/spec-workflow/SKILL.md`), and
the memory-sync session-end prompt (`skills/memory-sync/SKILL.md`).
`test_decisions.py` asserts the string appears in all four, so drift fails CI.

Self-contained by design: it does NOT import the 083-04 scan lib
(`hooks/scripts/lib/decision_scan.py`) nor `memory.py`, so the host-packaging
step can copy the skill tree whole without a cross-tree dependency.

`promote` (096-03) is the one deliberate exception, and only at the process
boundary: it shells `adr.py new` as a SUBPROCESS (`subprocess.run`), never
an `import adr`. A subprocess is not an import — it does not create a
Python-level cross-tree dependency, so the host-packaging step can still
copy this skill's tree whole; it just also needs `adr-workflow`'s tree
present beside it at runtime, which `_adr_py_path` locates and, failing
that, refuses cleanly rather than importing around the gap.

`evaluate_routing_signals` + `flags_adr_routing` are a pure, importable
lexical evaluator of `ADR_TRIGGER`'s two criteria. Per
[ADR-0039](../../docs/decisions/adr-0039-decision-routing-gate.md) they back
**only** the advisory `lint` (096-04) — a report-only sweep of records already
on disk. They deliberately do NOT gate any write path: the maintainer's call on
[#121](https://github.com/ramboz/jig/issues/121) is that keyword-matching is too
brittle to block a write, so the real routing judgement is the assistant's,
prompted by memory-sync's `SKILL.md` (096-01), at the moment a decision is
updated.
"""

import argparse
import datetime
import os
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import project_layout  # noqa: E402

# --- Single canonical ADR-trigger sentence (mirrors ADR-0031) ---------------
# Edit here AND in ADR-0031; the four consumer sites quote this verbatim and
# test_decisions.py fails CI on drift. The em-dashes (U+2014) are significant.
# NOTE: assembled from adjacent string literals, so a grep for the full
# sentence won't match *this* file — the test imports the constant, not the text.
ADR_TRIGGER = (
    "A load-bearing design choice with rejected alternatives — one a future "
    "agent would need to know about to avoid undoing it — warrants an ADR even "
    "when it changes no module boundary or public contract."
)

_LIGHTWEIGHT_REL = Path("docs/decisions/lightweight-decisions.md")
_ENTRIES_HEADING = "## Entries"

# The `## Entries` placeholder the template ships (honest copy for an empty
# file, stale the moment an entry lands — entries append at end-of-file, so
# nothing else clears it). Anchored on the template's own opening words and
# closed at the first line-terminal `_`, so it cannot swallow a project's own
# italic note under the same heading. Keyed to the template's wording, so
# test_decisions.py drift-guards this pattern against the shipped file: reword
# the template and the strip silently stops working.
_ENTRIES_PLACEHOLDER_RE = re.compile(r"^_No entries yet\..*?_$\n?",
                                     re.MULTILINE | re.DOTALL)

# Resolved the same way `adr.py` resolves its ADR template. Both host packages
# ship `templates/` as a sibling of `skills/`, and the Codex build pre-renders
# the plugin-root paths inside `*.md.template` (build_codex_plugin.py
# `_copy_templates`), so the text read here is already host-correct. A data
# read, not an import — the module docstring's no-cross-tree-import rule holds.
# Reachable in all four install modes since slice 095-01 (ADR-0038): both
# scaffold hosts copy `templates/` beside the copied machinery, so `parents[2]`
# finds it there too. Do not "clean up" `.claude/templates/` — this read is what
# it is for.
_TEMPLATE_RELATIVE = (
    Path("templates") / "docs" / "decisions"
    / "lightweight-decisions.md.template"
)


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _template_path() -> Path:
    return _plugin_root() / _TEMPLATE_RELATIVE


def lightweight_path(project_dir: Path) -> Path:
    """Path to the project's lightweight-decisions file."""
    return project_layout.decisions_dir(project_dir) / "lightweight-decisions.md"


def _display_path(project_dir: Path) -> str:
    """Project-relative path for messages. Resolves through project_layout, so
    a `layout.docs_root: "."` corpus (spec 084) is reported where the file
    actually lands rather than at the hardcoded default.

    Falls back to the absolute path when the docs root resolves outside
    `project_dir`: unusual, but naming the real location beats printing a
    relative default that is then certainly wrong.
    """
    target = lightweight_path(project_dir)
    try:
        return str(target.relative_to(project_dir))
    except ValueError:
        return str(target)


def _require_entry_fields(title: str, decision: str) -> None:
    """Validate the two mandatory fields. Shared by `add_lightweight` and the
    CLI, which checks up-front so a rejected call cannot seed as a side
    effect."""
    if not (title or "").strip():
        raise ValueError("title is required")
    if not (decision or "").strip():
        raise ValueError("decision is required")


def _foreign_format_error(project_dir: Path) -> str:
    """The loud refusal for a file that exists but is not in jig's format.

    Must name the expected shape AND a remedy: an agent told only that
    `## Entries` is missing will hand-roll a format rather than fix one.

    Takes `project_dir` so the offending file is named where it actually lives
    — a `layout.docs_root: "."` corpus (spec 084) is not at docs/decisions/.
    """
    return (
        "%s exists but is not in jig's lightweight-decisions format: no `%s` "
        "heading, so there is nowhere to place the entry. Nothing was "
        "written.\n\n"
        "Expected shape — an `%s` section holding one block per decision:\n\n"
        "    %s\n\n"
        "    ### 2026-07-16 — Short title\n\n"
        "    **Decision:** what was decided\n\n"
        "    **Context:** why — constraint, user feedback, design call\n\n"
        "    **Scope:** which screen / component / string / asset\n\n"
        # Host-neutral on purpose: skills/*.py ship verbatim to the Codex
        # package (only hooks/ and *.md.template get plugin-root rewrites),
        # so naming ${CLAUDE_PLUGIN_ROOT} here would hand a Codex user a
        # Claude-only variable.
        "Remedy — either:\n"
        "  1. add an `%s` heading to the existing file (entries append at "
        "end-of-file, so your existing content is left where it is); or\n"
        "  2. move the file aside, seed jig's template with `/jig:migrate`'s "
        "seed-decisions op (`migrate.py seed-decisions <project-dir>`), then "
        "port the existing entries across."
        % (_display_path(project_dir), _ENTRIES_HEADING, _ENTRIES_HEADING,
           _ENTRIES_HEADING, _ENTRIES_HEADING)
    )


def seed_lightweight(project_dir: Path) -> bool:
    """Create the lightweight-decisions home from the shipped template.

    Returns True when the file was created, False when it already exists
    (never overwrites — the existing file may be the owner's hand-rolled
    record, and clobbering it would destroy the very decisions this home is
    meant to preserve).

    Raises FileNotFoundError when the plugin's template is unreachable.
    """
    path = lightweight_path(project_dir)
    if path.exists():
        return False
    template = _template_path()
    if not template.is_file():
        # No install mode reaches here by design any more: plugin installs
        # resolve the template under the plugin root, and both scaffold hosts
        # copy templates/ beside the copied machinery (slice 095-01 for
        # Claude, `_copy_codex_templates` for Codex — see ADR-0038). So this
        # now means a BROKEN install: a copy that predates 095-01, a partial
        # tree, or CLAUDE_PLUGIN_ROOT pointed at a non-jig root. It still must
        # name a remedy that works, or it is the original bug (012) wearing a
        # new costume.
        raise FileNotFoundError(
            "lightweight-decisions template not found: %s\n\n"
            "jig ships it at templates/docs/decisions/. A scaffolded project "
            "carries its own copy beside its copied machinery; a plugin "
            "install reads it from the plugin root. Reaching this means "
            "neither is in place. Either:\n"
            "  1. refresh this project's copied machinery from a jig install "
            "(`migrate.py copy-machinery <project-dir>`), which brings "
            "templates/ with it; or\n"
            "  2. point CLAUDE_PLUGIN_ROOT at a jig plugin/checkout root and "
            "re-run this command; or\n"
            "  3. seed just this file from a jig install with `/jig:migrate`'s "
            "seed-decisions op (`migrate.py seed-decisions <project-dir>`)."
            % template)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace for case/spacing-insensitive matching."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _entry_key(date: str, title: str) -> str:
    return _normalize("%s — %s" % (date, title))


def _existing_keys(file_text: str) -> set:
    """Normalized `date — title` keys for every `### ` heading present.

    Deliberately scans all `### ` headings (not only the `## Entries` section),
    so the illustrative worked-example entry and the `### [Date] — [Short title]`
    line inside the `## Template` fence are also keyed. Inert: a real decision
    would only false-no-op if titled the literal `[Short title]` on date
    `[Date]`. The breadth keeps the matcher simple and section-order-agnostic.
    """
    keys = set()
    for line in file_text.splitlines():
        if line.startswith("### "):
            keys.add(_normalize(line[len("### "):]))
    return keys


# --- Two-signal ADR-routing evaluator (096-01 / ADR-0039) -------------------
# `ADR_TRIGGER` above states the rule; until this, nothing evaluated a
# decision against it. The rubric it is transcribed from
# (docs/decisions/lightweight-decisions.md's routing table) states TWO
# independent criteria, not one flat list of ADR-ish words:
#   (a) "A load-bearing design choice with rejected alternatives..." — a
#       CONJUNCTION: needs both halves.
#   (b) "Also: any change to a module boundary, public contract, or
#       cross-cutting policy." — UNCONDITIONAL.
# A flat keyword scan collapses that distinction and breaks on jig's own
# corpus: the illustrative lightweight entry ("Onboarding CTA copy: 'Get
# started' over 'Sign up'") is a rejected alternative in the plainest sense,
# and the rubric routes it to the LIGHTWEIGHT home by name ("UI string or
# translation choices"). The rubric's own hedge — "no REAL rejected
# alternatives" — is what saves it: criterion (a)'s conjunction IS that test.
# See ADR-0039 (Option A vs B) for the full argument against the flat list.

RoutingMatch = namedtuple("RoutingMatch", "group phrase")

_GROUP_BOUNDARY = "BOUNDARY"
_GROUP_ALTERNATIVES = "ALTERNATIVES"
_GROUP_LOAD_BEARING = "LOAD_BEARING"

# Each marker is (display phrase, compiled regex). Regexes run against
# `_normalize()`-d text (lowercase, whitespace collapsed to single spaces),
# so patterns are plain lowercase with literal single spaces between words —
# no re.IGNORECASE needed. `\b` on both ends stops a marker firing INSIDE a
# longer word it happens to prefix: `alternative` must not fire on
# `alternatively`, `interface` must not fire on `interfaces` (096-01 edge
# cases, both asserted in test_decisions.py). Deliberately NOT a blanket
# `s?` suffix on every marker — that would defeat the boundary guard for
# exactly the markers where the plural is the false-positive case.
_MARKER_TABLE = (
    (_GROUP_BOUNDARY, (
        # The rubric's own three phrases (criterion b, verbatim) plus
        # synonym-expansions a real decision is more likely to use in
        # practice — "the public interface changed" says the same thing as
        # "changed the public contract" without quoting the rubric.
        ("module boundary", re.compile(r"\bmodule boundary\b")),
        ("public contract", re.compile(r"\bpublic contract\b")),
        ("cross-cutting policy", re.compile(r"\bcross-cutting policy\b")),
        ("protocol", re.compile(r"\bprotocol\b")),
        ("schema", re.compile(r"\bschema\b")),
        ("public api surface", re.compile(r"\bpublic api surface\b")),
        # Qualified, never bare `interface`. "user interface" is ordinary
        # vocabulary in exactly the decisions the rubric routes HERE by name
        # (UI strings, visual choices), and BOUNDARY flags on its own — a bare
        # marker refuses "Use 'Preferences' over 'Settings' in the user
        # interface" and teaches the operator to reach for the escape hatch,
        # which is the Option-A failure ADR-0039 rejects.
        ("public interface", re.compile(r"\bpublic interface\b")),
    )),
    (_GROUP_ALTERNATIVES, (
        ("rejected", re.compile(r"\brejected\b")),
        ("ruled out", re.compile(r"\bruled out\b")),
        ("discarded", re.compile(r"\bdiscarded\b")),
        ("instead of", re.compile(r"\binstead of\b")),
        ("rather than", re.compile(r"\brather than\b")),
        ("as opposed to", re.compile(r"\bas opposed to\b")),
        ("in favour/favor of", re.compile(r"\bin favou?r of\b")),
        ("alternative(s)", re.compile(r"\balternatives?\b")),
        ("trade-off", re.compile(r"\btrade-off\b")),
    )),
    (_GROUP_LOAD_BEARING, (
        ("load-bearing", re.compile(r"\bload-bearing\b")),
        ("architectural", re.compile(r"\barchitectural\b")),
        ("structural", re.compile(r"\bstructural\b")),
        ("replaces/replacing", re.compile(r"\breplac(?:es|ing)\b")),
        ("native implementation", re.compile(r"\bnative implementation\b")),
        ("vendored", re.compile(r"\bvendored\b")),
        ("dependency", re.compile(r"\bdependency\b")),
        ("coupling", re.compile(r"\bcoupling\b")),
        ("invariant", re.compile(r"\binvariant\b")),
        ("migration", re.compile(r"\bmigration\b")),
        ("irreversible", re.compile(r"\birreversible\b")),
        ("hard to reverse", re.compile(r"\bhard to reverse\b")),
    )),
)


def evaluate_routing_signals(title: str, decision: str, context: str,
                             scope: str) -> list:
    """Pure lexical evaluator of `ADR_TRIGGER`'s two criteria (ADR-0039).

    Scans the record's four fields for the marker groups above and returns
    every hit as a `RoutingMatch(group, phrase)`. Module-level and
    side-effect-free — no filesystem or environment access.

    **Advisory only.** Per ADR-0039 this backs the report-only `lint`
    (096-04) and nothing else: keyword-matching is too brittle to gate a
    write (a prototype refused an ordinary "user interface" copy decision
    until the marker was narrowed), so it lives on the one surface where a
    false positive costs a glance rather than a blocked write. Do not wire
    it into `add-lightweight` or `update` — that gate was built and removed.

    Does not decide whether to flag — see `flags_adr_routing`, which applies
    the two-signal rule to this function's output. Kept separate so the lint
    can also just enumerate matches for its report.
    """
    corpus = _normalize(
        " ".join(t or "" for t in (title, decision, context, scope)))
    matches = []
    for group, markers in _MARKER_TABLE:
        for phrase, pattern in markers:
            if pattern.search(corpus):
                matches.append(RoutingMatch(group, phrase))
    return matches


def flags_adr_routing(matches) -> bool:
    """Apply the two-signal rule to `evaluate_routing_signals()`'s output.

    Flag iff BOUNDARY matched on its own (criterion b is unconditional — the
    rubric says "ANY change to a module boundary...", no second signal
    required), or ALTERNATIVES and LOAD_BEARING matched together (criterion
    a's conjunction — neither is evidence alone; together they are the
    rubric's "load-bearing... with rejected alternatives"). See ADR-0039 for
    why this is a conjunction rather than a flat OR across every marker.
    """
    groups = {m.group for m in matches}
    return (_GROUP_BOUNDARY in groups
            or (_GROUP_ALTERNATIVES in groups
                and _GROUP_LOAD_BEARING in groups))


def render_entry(title: str, decision: str, context: str, scope: str,
                 commit: str = "", date: str = "") -> str:
    """Render one entry in the file's `### [Date] — [Title]` template shape."""
    lines = [
        "### %s — %s" % (date, title),
        "",
        "**Decision:** %s" % decision,
        "",
        "**Context:** %s" % context,
        "",
        "**Scope:** %s" % scope,
    ]
    if commit:
        lines += ["", "**Commit:** %s" % commit]
    return "\n".join(lines) + "\n"


# --- Entry parsing for `update` (096-02) ------------------------------------
# `_existing_keys` above deliberately scans EVERY `### ` heading in the file,
# including two pieces of documentation-in-entry-clothing this file ships:
# the `## Template` fence's `### [Date] — [Short title]` placeholder, and (in
# jig's own docs/decisions/lightweight-decisions.md) the illustrative worked
# example. That breadth is exactly right for idempotency — "is this key
# already taken?" only needs to know a heading exists, not whether it is a
# real record. `update` needs the opposite question — "which of these may I
# rewrite?" — so it needs a narrower notion, built once here and reused by
# 096-03 (`promote`) and 096-04 (`lint`), both of which need the same "which
# headings are real records" answer.

Entry = namedtuple("Entry", "date title decision context scope commit start end")

# A `### ` heading, split on the FIRST ` — ` (matching `render_entry`'s own
# `"### %s — %s" % (date, title)` join, so parsing agrees with rendering on
# where the date ends and the title begins). Non-greedy on date: an ISO date
# never itself contains ` — `, so this never has to disambiguate a title that
# happens to contain a second em dash.
_ENTRY_HEADING_RE = re.compile(r"^### (?P<date>.*?) — (?P<title>[^\n]+)$",
                               re.MULTILINE)

# The blockquote jig's own file uses immediately above its worked example to
# say "this one is documentation, not a record" (see
# docs/decisions/lightweight-decisions.md's `## Entries` section). A
# STRUCTURAL marker, not a hardcoded title — so it also protects a project
# that adopts the same convention for its own illustrative note, and it does
# not need updating if the worked example's title or wording ever changes.
_ILLUSTRATIVE_MARKER_RE = re.compile(r"^> _Illustrative only\b", re.MULTILINE)

# The four fields in the fixed order `render_entry` always emits them, each
# non-greedy up to the next field's literal marker (or end of block for the
# last one present) — so a field value that itself contains blank lines or
# `### `-looking text (096-02's stated edge case) cannot be mistaken for a
# later field or a new heading; only the literal `\n\n**Context:**` /
# `\n\n**Scope:**` / `\n\n**Commit:**` markers end a field. `re.DOTALL` makes
# `.` span newlines, since a field value is not guaranteed single-line.
# Anchored `\A`...`\Z` (not `^`/`$`) so `.match()` requires the WHOLE block to
# conform — a malformed block (hand-edited, or from a foreign format) simply
# fails to match rather than parsing garbage, and `_real_entries` treats a
# non-match as "not addressable" rather than crashing.
_FIELD_RE = re.compile(
    r"\A\n*\*\*Decision:\*\* (?P<decision>.*?)\n\n"
    r"\*\*Context:\*\* (?P<context>.*?)\n\n"
    r"\*\*Scope:\*\* (?P<scope>.*?)"
    r"(?:\n\n\*\*Commit:\*\* (?P<commit>.*?))?"
    r"\n*\Z",
    re.DOTALL)


def _real_entries(file_text: str) -> list:
    """Every REAL entry under `## Entries`, as parsed `Entry` records.

    `start`/`end` are byte offsets into `file_text` spanning the entry's own
    block — heading through its last field — EXCLUDING the blank-line
    separator that follows it. That is the span `update_lightweight`
    replaces in place; the separator is left untouched so a following entry
    (096-02's stated edge case) is never disturbed.

    Two restrictions make this narrower than `_existing_keys`:
      - only `### ` headings AFTER the `## Entries` heading are considered,
        which excludes the `## Template` fence for free — `## Template`
        precedes `## Entries` in every shipped copy of this file, so the
        fence's placeholder heading is textually out of scope before any
        illustrative-marker check even runs; and
      - a heading immediately preceded (allowing intervening blank lines) by
        the `_ILLUSTRATIVE_MARKER_RE` blockquote is skipped — jig's own
        worked example is marked this way, and any project using the same
        convention for its own illustrative note gets the same protection.

    A `### ` heading whose body does not match `_FIELD_RE` (hand-edited into
    something the helper never wrote) is also skipped rather than raising —
    "not addressable" is the correct outcome for update, not a crash.
    """
    idx = file_text.find(_ENTRIES_HEADING)
    if idx == -1:
        return []
    body_start = idx + len(_ENTRIES_HEADING)
    section = file_text[body_start:]
    headings = list(_ENTRY_HEADING_RE.finditer(section))
    entries = []
    prev_block_end = 0
    for i, m in enumerate(headings):
        heading_start = m.start()
        block_end = (headings[i + 1].start() if i + 1 < len(headings)
                    else len(section))
        gap = section[prev_block_end:heading_start]
        prev_block_end = block_end
        if _ILLUSTRATIVE_MARKER_RE.search(gap):
            continue
        field_text = section[m.end():block_end]
        fm = _FIELD_RE.match(field_text)
        if not fm:
            continue
        entries.append(Entry(
            date=m.group("date"), title=m.group("title"),
            decision=fm.group("decision"), context=fm.group("context"),
            scope=fm.group("scope"), commit=fm.group("commit") or "",
            start=body_start + heading_start, end=body_start + block_end))
    return entries


def _find_entry(file_text: str, title: str, date: Optional[str] = None) -> Entry:
    """Locate the single REAL entry (see `_real_entries`) matching `title`,
    normalized the same way the idempotency key already is (`_normalize`),
    so `update` and `add-lightweight` agree on what counts as "the same
    entry" (096-02 AC5). `date` narrows to one when a title recurs.

    Raises `ValueError` for every refusal shape `update` needs:
      - no match — covers a genuinely missing title AND a title that only
        exists as the illustrative example or the `## Template` fence, since
        `_real_entries` already excludes both; there is no second "that's
        documentation" code path (AC7 rides on AC4's refusal for free).
      - an ambiguous match — more than one entry shares the normalized
        title and no (or a non-narrowing) `--date` was given; lists the
        competing dates rather than guessing (AC6).
    """
    entries = _real_entries(file_text)
    norm_title = _normalize(title)
    candidates = [e for e in entries if _normalize(e.title) == norm_title]
    if date:
        norm_date = _normalize(date)
        candidates = [e for e in candidates if _normalize(e.date) == norm_date]
    if not candidates:
        raise ValueError(
            "no entry titled %r found under `## Entries`%s. Nothing was "
            "written." % (title, " for date %s" % date if date else ""))
    if len(candidates) > 1:
        dates = ", ".join(sorted(e.date for e in candidates))
        raise ValueError(
            "title %r matches more than one entry (dates: %s) — pass "
            "--date to disambiguate. Nothing was written." % (title, dates))
    return candidates[0]


def _today() -> str:
    return datetime.date.today().isoformat()


def add_lightweight(project_dir: Path, title: str, decision: str, context: str,
                    scope: str, commit: str = "", date: str = "") -> bool:
    """Idempotently append a lightweight-decision entry.

    Returns True when an entry was appended, False when it was a no-op because an
    entry with the same normalized `date — title` heading already exists.

    Seeds the lightweight-decisions home from the shipped template when the
    project has none. This reverses an earlier contract ("seeded by
    scaffold-init; this helper does not create it") — scaffold-init cannot be
    re-run on a scaffolded project, so refusing left the recording path
    unrecoverable (bug 012).

    Raises ValueError when the file exists but is not in jig's format — that
    case stays loud (see `_foreign_format_error`), because appending jig
    entries to a foreign document would silently split the record in two.
    """
    _require_entry_fields(title, decision)
    title = title.strip()
    decision = decision.strip()
    context = (context or "").strip()
    scope = (scope or "").strip()
    date = date.strip() if date else _today()

    path = lightweight_path(project_dir)
    seed_lightweight(project_dir)

    text = path.read_text(encoding="utf-8")
    # Format gate BEFORE the idempotency no-op: a foreign file that happens to
    # carry a matching `### <date> — <title>` heading would otherwise return a
    # silent "already recorded" and the divergence would never surface.
    if _ENTRIES_HEADING not in text:
        raise ValueError(_foreign_format_error(project_dir))
    if _entry_key(date, title) in _existing_keys(text):
        return False

    entry = render_entry(title, decision, context, scope, commit, date)
    body = _ENTRIES_PLACEHOLDER_RE.sub("", text, count=1)
    new_text = body.rstrip("\n") + "\n\n" + entry
    # Plain write (not _common.atomic_io) — deliberate: this helper is
    # self-contained by DoR (no cross-tree import), and the file is an
    # owner-gated, single-writer, human-browsable doc, not a hot concurrent path.
    path.write_text(new_text, encoding="utf-8")
    return True


def update_lightweight(project_dir: Path, title: str,
                       decision: Optional[str] = None,
                       context: Optional[str] = None,
                       scope: Optional[str] = None,
                       commit: Optional[str] = None,
                       date: Optional[str] = None) -> bool:
    """Revise fields on an already-recorded lightweight-decision entry, in
    place, through the helper (096-02) — the code path #121's routing
    failure never had (revision was a hand-edit) and spec 083's OQ2
    anticipated (adding a `**Commit:**` SHA retroactively) but left no way
    to do.

    `decision`/`context`/`scope`/`commit` default to `None`, meaning "leave
    as recorded" — deliberately NOT `""` (`add_lightweight`'s default),
    which would be indistinguishable from "clear this field" (AC2). Passing
    an explicit empty string DOES set the field to empty; only omitting the
    keyword argument (or, on the CLI, the flag) preserves it.

    Returns True when the file was rewritten, False when every supplied
    field already matched what was recorded — a no-op, mirroring
    `add_lightweight`'s idempotency contract rather than rewriting a file
    that would come out byte-identical anyway.

    Raises ValueError when: `title` is blank; the file does not exist yet
    (nothing to update); the file exists but is not in jig's format
    (`_foreign_format_error`); or `_find_entry` refuses — missing, ambiguous,
    or a title that only resolves to the illustrative example / template
    fence (see its docstring).

    Deliberately carries no routing judgement and no `--confirm-lightweight`
    (096-02 AC8 / ADR-0039): every refusal above is about MATCHING an entry,
    never about the decision's content. Whether a revision now warrants
    promotion to an ADR is the assistant's judgement, prompted by
    memory-sync's `SKILL.md` (096-01) — not this helper's to gate.
    """
    if not (title or "").strip():
        raise ValueError("title is required")
    path = lightweight_path(project_dir)
    if not path.is_file():
        raise ValueError(
            "%s does not exist yet — there is nothing to update. Record it "
            "first with `add-lightweight`." % _display_path(project_dir))
    text = path.read_text(encoding="utf-8")
    if _ENTRIES_HEADING not in text:
        raise ValueError(_foreign_format_error(project_dir))

    entry = _find_entry(text, title, date)
    merged_decision = decision.strip() if decision is not None else entry.decision
    merged_context = context.strip() if context is not None else entry.context
    merged_scope = scope.strip() if scope is not None else entry.scope
    merged_commit = commit.strip() if commit is not None else entry.commit

    if (merged_decision == entry.decision and merged_context == entry.context
            and merged_scope == entry.scope and merged_commit == entry.commit):
        return False

    rendered = render_entry(entry.title, merged_decision, merged_context,
                            merged_scope, merged_commit, entry.date)
    # `entry.end` reaches true EOF for the file's last entry (`_real_entries`
    # scopes the Entries section to end-of-file, matching add_lightweight's
    # own always-append-at-EOF behaviour) — nothing follows to preserve. An
    # entry with a sibling after it has `entry.end` landing exactly at the
    # next entry's `### `, so the one blank line `add_lightweight` always
    # leaves between entries has to be re-supplied here, or the rewritten
    # block would run straight into the next heading — the "followed by
    # another entry" edge case this slice calls out explicitly.
    if entry.end >= len(text):
        new_text = text[:entry.start] + rendered
    else:
        new_text = text[:entry.start] + rendered + "\n" + text[entry.end:]
    # Plain write — same rationale as `add_lightweight`'s (self-contained
    # helper, owner-gated single-writer doc, not a hot concurrent path).
    path.write_text(new_text, encoding="utf-8")
    return True



# --- `promote` (096-03 / ADR-0039) -------------------------------------
# Moves a lightweight entry to an ADR via `adr.py new` (subprocess — see the
# module docstring's carve-out), seeds the created ADR from the entry's own
# fields, and rewrites the entry into a forward-linking stub. The ordering
# in `promote_lightweight` below is deliberately staged so failure is
# atomic (AC6): everything that can fail happens BEFORE
# `lightweight-decisions.md` is touched.


def _adr_py_path() -> Optional[Path]:
    """Locate the sibling adr-workflow skill's `adr.py`.

    `decisions.py` lives in a skill directory named either `memory-sync`
    (plugin install) or `jig-memory-sync` (Claude scaffold install, which
    prefixes every copied skill dir with `jig-`). `adr-workflow` is its
    sibling under the same `skills/` tree, named `adr-workflow` or
    `jig-adr-workflow` respectively — the prefix is derived from
    decisions.py's OWN directory name, so both install modes resolve
    without reading any config. A `CLAUDE_PLUGIN_ROOT`-rooted candidate is
    also tried, for a (currently theoretical) copy that carries
    decisions.py without its usual sibling.

    Returns None — never raises — when neither resolves: a tier-0-only
    install genuinely has no ADR helper, and `promote_lightweight` turns
    that into a clean refusal rather than a traceback.
    """
    own = Path(__file__).resolve().parent
    prefix = "jig-" if own.name.startswith("jig-") else ""
    candidates = [own.parent / (prefix + "adr-workflow") / "adr.py"]
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidates.append(
            Path(plugin_root) / "skills" / "adr-workflow" / "adr.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


# Stricter than adr.py's OWN `_validate_slug` (`^[a-z0-9][a-z0-9-]*$`, which
# deliberately accepts a leading digit) — this only gates the DEFAULT slug
# `promote` derives from an entry's title; an explicit `--slug` bypasses it
# entirely and is handed to `adr.py new` verbatim, which applies its own
# (looser) rule. A derived slug this malformed means the title didn't
# kebab-case cleanly, and guessing a "fixed" form on the caller's behalf
# would be exactly the silent mangling this slice's edge cases rule out —
# refuse and name the violated rule instead.
_DERIVED_SLUG_OK_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def _default_slug_from_title(title: str) -> str:
    """Kebab-case `title` into a slug: lowercase, then each character that
    is not `[a-z0-9]` becomes one literal `-` — char-for-char, NOT
    collapsing runs. Collapsing multiple punctuation/whitespace characters
    into a single `-` would itself be a silent repair, and it would make
    the double-hyphen edge case unreachable (a title like "A -- B" would
    quietly become "a-b" instead of being refused).

    Validates the result against `_DERIVED_SLUG_OK_RE` and raises
    ValueError naming the violated rule (empty / leading digit or hyphen /
    consecutive hyphens / trailing hyphen) rather than repairing it.
    """
    raw = re.sub(r"[^a-z0-9]", "-", title.strip().lower())
    if _DERIVED_SLUG_OK_RE.match(raw):
        return raw
    if not raw or not raw[0].isalpha():
        reason = "is empty" if not raw else "starts with a digit or hyphen"
    elif "--" in raw:
        reason = "would contain consecutive hyphens"
    elif raw.endswith("-"):
        reason = "would end with a hyphen"
    else:
        reason = "is not a valid ADR slug"  # defensive; should be unreachable
    raise ValueError(
        "title %r kebab-cases to %r, which %s. Pass --slug explicitly to "
        "name the ADR's slug yourself." % (title, raw, reason))


def _adr_new_argv(adr_py: Path, slug: str, title: str, project_dir: Path,
                  no_push: bool, pr_mode: bool) -> list:
    """Build the `adr.py new` argv (AC1 + AC5's --no-push/--pr threading).
    Pure/no I/O, so the flag-threading can be pinned without a real
    subprocess for every combination — see `_run_adr_new` for the actual
    invocation."""
    argv = [sys.executable, str(adr_py), "new", slug, "--title", title,
           "--project-dir", str(project_dir)]
    if no_push:
        argv.append("--no-push")
    if pr_mode:
        argv.append("--pr")
    return argv


def _run_adr_new(adr_py: Path, slug: str, title: str, project_dir: Path,
                 no_push: bool, pr_mode: bool):
    """Run `adr.py new` as a SUBPROCESS (never an import — see this file's
    module docstring). No `env=` override is passed: the child inherits
    this process's environment as-is, so a caller's `CLAUDE_PLUGIN_ROOT` or
    git identity variables reach the ADR helper unchanged. Returns the
    `subprocess.CompletedProcess`; `promote_lightweight` decides how to
    react to a non-zero exit."""
    argv = _adr_new_argv(adr_py, slug, title, project_dir, no_push, pr_mode)
    return subprocess.run(argv, capture_output=True, text=True)


def _h2_pattern(heading: str) -> str:
    """Match a `## <heading>` line, stopping AT the newline.

    `[ \\t]*$` rather than `\\s*$` on purpose: `\\s` matches newlines, so a
    greedy `\\s*` swallows the blank line after the heading and every caller
    that then re-adds its own spacing emits one blank line too many (the
    seeded ADR rendered `## Context` followed by two blank lines). Keeping the
    match inside the line makes the heading's end unambiguous.
    """
    return r"(?m)^##[ \t]+" + re.escape(heading) + r"[ \t]*$"


def _get_md_section(text: str, heading: str) -> str:
    """Body of the `## <heading>` section in `text` (stripped), or '' if the
    heading is absent. A small, LOCAL section-locator — decisions.py cannot
    import adr.py's own `_status_section_body` (self-contained by DoR), so
    this is a minimal, purpose-built duplicate rather than a shared import."""
    m = re.search(_h2_pattern(heading), text)
    if not m:
        return ""
    rest = text[m.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    body = rest[:next_h2.start()] if next_h2 else rest
    return body.strip()


def _replace_md_section(text: str, heading: str, new_body: str) -> str:
    """Replace the body of the `## <heading>` section with `new_body`,
    preserving everything else (including the heading line and the
    surrounding blank-line spacing style the ADR template uses). Raises
    ValueError if `heading` is absent — should not happen against a freshly
    `adr.py new`-created file; a raise here is more honest than silently
    no-op-ing against a template that has drifted."""
    m = re.search(_h2_pattern(heading), text)
    if not m:
        raise ValueError("ADR has no '## %s' section" % heading)
    rest = text[m.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    section_end = m.end() + (next_h2.start() if next_h2 else len(rest))
    return (text[:m.end()] + "\n\n" + new_body.strip() + "\n\n"
           + text[section_end:])


_ADR_TITLE_RE = re.compile(r"(?m)^#\s+ADR-\d{4}:\s+(.+?)\s*$")


def _adr_title(adr_path: Path) -> str:
    """The `<Title>` from a `# ADR-NNNN: <Title>` heading. Falls back to the
    file's stem if the heading is somehow absent (defensive; adr.py always
    writes it)."""
    m = _ADR_TITLE_RE.search(adr_path.read_text(encoding="utf-8"))
    return m.group(1).strip() if m else adr_path.stem


# There is no dedicated `## Scope` heading in the ADR template
# (templates/docs/decisions/adr-0000-template.md) — the entry's Scope field
# is folded into `## Context` (see `_seed_adr_from_entry`). This is the
# fallback text when Scope was left blank at write time (it is optional —
# `_require_entry_fields` only requires title + decision), reusing the same
# "which screen / component / string / asset" wording
# `_foreign_format_error` already quotes, so the vocabulary for what Scope
# MEANS stays single-sourced even though this is a different string.
_ADR_SCOPE_PLACEHOLDER = "_TODO: which screen / component / string / asset._"


def _seed_adr_from_entry(adr_path: Path, entry: Entry) -> None:
    """AC2 + AC4: fill the freshly-created ADR's `## Context` and
    `## Recommended Decision` sections from the entry's own fields, and
    append a back-link naming the entry's original date.

    `## Recommended Decision` becomes exactly `entry.decision` — that field
    is mandatory at write time, so it is never empty here. `## Context` is
    composed from `entry.context` (or, when empty, the template's OWN
    placeholder prose — captured from THIS file before it is touched, so
    the fallback can never drift from whatever `adr.py new`'s template
    actually shipped), a **Scope:** line (placeholder-backed the same way
    when empty), and the back-link.
    """
    text = adr_path.read_text(encoding="utf-8")
    context_placeholder = _get_md_section(text, "Context")
    context_prose = entry.context if entry.context else context_placeholder
    scope_text = entry.scope if entry.scope else _ADR_SCOPE_PLACEHOLDER
    context_body = (
        "%s\n\n**Scope:** %s\n\n"
        "_Promoted from the lightweight-decision entry dated %s — see "
        "lightweight-decisions.md._"
        % (context_prose, scope_text, entry.date)
    )
    text = _replace_md_section(text, "Context", context_body)
    text = _replace_md_section(text, "Recommended Decision", entry.decision)
    adr_path.write_text(text, encoding="utf-8")


# The promoted-stub shape `_render_promoted_stub` writes and
# `_find_promoted_stub` reads back — deliberately NOT `render_entry`'s
# Decision/Context/Scope shape (`_FIELD_RE`). A distinct, parseable marker
# (`**Promoted:**`) is what lets `_find_promoted_stub` tell "already
# promoted" apart from "genuinely missing" (AC8); a body that matched
# `_FIELD_RE` would look like an ordinary revisable entry instead, and a
# re-run of `promote` would only ever see `_find_entry`'s generic "no entry
# titled ... found".
_PROMOTED_STUB_RE = re.compile(
    r"\A\n*\*\*Promoted:\*\* moved to \[ADR-\d{4}: [^\]]*\]"
    r"\((?P<filename>adr-\d{4}-[a-z0-9][a-z0-9-]*\.md)\)\.\n*\Z")

_ADR_FILENAME_RE = re.compile(r"^adr-(?P<number>\d{4})-")


def _find_promoted_stub(file_text: str, title: str,
                        date: Optional[str] = None) -> Optional[str]:
    """AC8: is `title` (optionally narrowed by `date`) already a promoted
    stub? Scans the same `### ` headings AFTER `## Entries` that
    `_real_entries` scans, but tests bodies against `_PROMOTED_STUB_RE`
    instead of `_FIELD_RE`.

    Returns the `adr-NNNN-slug.md` filename the entry points to, or None.
    """
    idx = file_text.find(_ENTRIES_HEADING)
    if idx == -1:
        return None
    body_start = idx + len(_ENTRIES_HEADING)
    section = file_text[body_start:]
    headings = list(_ENTRY_HEADING_RE.finditer(section))
    norm_title = _normalize(title)
    norm_date = _normalize(date) if date else None
    for i, m in enumerate(headings):
        if _normalize(m.group("title")) != norm_title:
            continue
        if norm_date and _normalize(m.group("date")) != norm_date:
            continue
        block_end = (headings[i + 1].start() if i + 1 < len(headings)
                    else len(section))
        field_text = section[m.end():block_end]
        sm = _PROMOTED_STUB_RE.match(field_text)
        if sm:
            return sm.group("filename")
    return None


def _render_promoted_stub(entry: Entry, adr_path: Path) -> str:
    """AC3: the forward-linking stub that replaces a promoted entry's body.
    The heading (`### <date> — <title>`) is left exactly as it was — only
    the body below it changes — so an old link to this entry still lands on
    something, not a gap (never delete a promoted entry)."""
    m = _ADR_FILENAME_RE.match(adr_path.name)
    number = m.group("number") if m else "????"
    title = _adr_title(adr_path)
    return (
        "### %s — %s\n\n"
        "**Promoted:** moved to [ADR-%s: %s](%s).\n"
        % (entry.date, entry.title, number, title, adr_path.name)
    )


def _replace_entry_with_stub(text: str, entry: Entry, adr_path: Path) -> str:
    """Rewrite `entry`'s span (`entry.start:entry.end`, per `_real_entries`'
    contract) into its promoted stub, in place — mirrors
    `update_lightweight`'s own last-entry-vs-followed-by-another-entry
    handling, since a promoted entry can be anywhere in the file."""
    stub = _render_promoted_stub(entry, adr_path)
    if entry.end >= len(text):
        return text[:entry.start] + stub
    return text[:entry.start] + stub + "\n" + text[entry.end:]


def promote_lightweight(project_dir: Path, title: str,
                        date: Optional[str] = None,
                        slug: Optional[str] = None,
                        no_push: bool = False, pr_mode: bool = False) -> Path:
    """Move a lightweight-decision entry to an ADR via `adr.py new` (096-03
    / ADR-0039), seed the ADR from the entry's own fields, and replace the
    entry with a forward-linking stub. Returns the created ADR's path.

    Ordering is deliberately staged so failure is atomic (AC6): everything
    that can fail — finding the entry, deriving/validating the slug,
    locating and running `adr.py new` — happens BEFORE
    `lightweight-decisions.md` is touched. Only once `adr.py new` has
    actually succeeded does this function seed the ADR and rewrite the
    entry; a failure at any earlier step leaves the file byte-identical.

    Raises ValueError for every refusal shape: `title` blank; the file
    missing or foreign-format; `title` already points to a promoted stub
    (AC8); `_find_entry`'s missing/ambiguous/illustrative/fence refusals
    (AC7, AC9 — reused verbatim, same messages `update` gives); a derived
    slug that doesn't kebab-case cleanly (edge cases); no adr-workflow
    skill found beside this file; or `adr.py new` itself failing.
    """
    if not (title or "").strip():
        raise ValueError("title is required")
    path = lightweight_path(project_dir)
    if not path.is_file():
        raise ValueError(
            "%s does not exist yet — there is nothing to promote. Record "
            "it first with `add-lightweight`." % _display_path(project_dir))
    text = path.read_text(encoding="utf-8")
    if _ENTRIES_HEADING not in text:
        raise ValueError(_foreign_format_error(project_dir))

    # AC8 — a specific refusal for a re-run on an already-promoted entry,
    # checked BEFORE `_find_entry` (whose generic "no entry titled ..." is
    # all a stub's body — which never matches `_FIELD_RE` — would otherwise
    # produce).
    already = _find_promoted_stub(text, title, date)
    if already is not None:
        raise ValueError(
            "%r is already promoted to %s; nothing to do. Edit that ADR "
            "directly for further changes." % (title, already))

    # AC7 / AC9 — reuses 096-02's entry-matching contract unchanged: missing,
    # ambiguous, illustrative-example, or `## Template`-fence titles all
    # raise here with the SAME messages `update` gives.
    entry = _find_entry(text, title, date)

    final_slug = (slug or "").strip()
    if not final_slug:
        final_slug = _default_slug_from_title(entry.title)

    adr_py = _adr_py_path()
    if adr_py is None:
        raise ValueError(
            "promote needs the adr-workflow skill's adr.py, which was not "
            "found beside %s. A tier-0-only install has no ADR helper — "
            "install the adr-workflow skill (or add it to this project's "
            "copied machinery), then re-run `promote`."
            % Path(__file__).name)

    result = _run_adr_new(adr_py, final_slug, entry.title, project_dir,
                          no_push, pr_mode)
    if result.returncode != 0:
        raise ValueError(
            "adr.py new failed (exit %d); %s was left untouched:\n%s"
            % (result.returncode, _display_path(project_dir),
               (result.stderr or result.stdout).strip()))
    stdout_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if not stdout_lines:
        raise ValueError(
            "adr.py new exited 0 but printed nothing; could not determine "
            "the created ADR's path. %s was left untouched."
            % _display_path(project_dir))
    adr_path = Path(stdout_lines[-1].strip())
    if not adr_path.is_file():
        raise ValueError(
            "adr.py new reported a path that does not exist: %s. %s was "
            "left untouched." % (adr_path, _display_path(project_dir)))

    # From here on, adr.py has already succeeded — seed + stub are the only
    # remaining steps, both against files that now exist.
    _seed_adr_from_entry(adr_path, entry)
    new_text = _replace_entry_with_stub(text, entry, adr_path)
    path.write_text(new_text, encoding="utf-8")
    return adr_path


def _cmd_add_lightweight(args) -> int:
    project_dir = Path(args.project_dir).resolve()
    try:
        # Validate BEFORE seeding: a rejected call must not leave a record
        # home behind as a side effect. add_lightweight would seed too, but
        # seeding here lets the creation be reported — a file appearing with
        # no signal is the same silence bug 012 is about.
        _require_entry_fields(args.title, args.decision)
        seeded = seed_lightweight(project_dir)
        appended = add_lightweight(
            project_dir, args.title, args.decision, args.context, args.scope,
            commit=args.commit or "", date=args.date or "")
    except (FileNotFoundError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    # Report the real path, not the default: under `layout.docs_root: "."`
    # (spec 084) the file is NOT at docs/decisions/.
    rel = _display_path(project_dir)
    if seeded:
        print("seeded %s from jig's template (this project had none)" % rel)
    if appended:
        print("recorded lightweight decision in %s: %s" % (rel, args.title))
    else:
        print("no-op: an entry for '%s' (%s) is already recorded in %s"
              % (args.title, args.date or _today(), rel))
    return 0


def _cmd_update(args) -> int:
    project_dir = Path(args.project_dir).resolve()
    try:
        changed = update_lightweight(
            project_dir, args.title, decision=args.decision,
            context=args.context, scope=args.scope, commit=args.commit,
            date=args.date)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    rel = _display_path(project_dir)
    if changed:
        print("updated lightweight decision in %s: %s" % (rel, args.title))
    else:
        print("no-op: '%s' already matches the supplied fields in %s"
              % (args.title, rel))
    return 0


def _cmd_promote(args) -> int:
    project_dir = Path(args.project_dir).resolve()
    try:
        adr_path = promote_lightweight(
            project_dir, args.title, date=args.date, slug=args.slug,
            no_push=args.no_push, pr_mode=args.pr)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    rel = _display_path(project_dir)
    print("promoted lightweight decision in %s to %s: %s"
          % (rel, adr_path, args.title))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=("jig lightweight-decisions helper "
                     "(add-lightweight, update, promote)"))
    sub = p.add_subparsers(dest="command", required=True)

    al = sub.add_parser(
        "add-lightweight",
        help="idempotently append a lightweight decision entry")
    al.add_argument("--title", required=True, help="short decision title")
    al.add_argument("--decision", required=True, help="what was decided")
    al.add_argument("--context", default="", help="why — constraint / feedback")
    al.add_argument("--scope", default="",
                    help="which screen / component / string / asset")
    al.add_argument("--commit", default="", help="optional git SHA or PR")
    al.add_argument("--date", default="",
                    help="ISO date (default: today) — for deterministic runs")
    al.add_argument("--project-dir", default=".",
                    help="project root (default: cwd)")
    al.set_defaults(func=_cmd_add_lightweight)

    up = sub.add_parser(
        "update",
        help="revise fields on an existing lightweight decision entry")
    up.add_argument("--title", required=True,
                    help="title of the existing entry to revise")
    # Defaults are None here, NOT "" like add-lightweight's — None is the
    # sentinel meaning "omitted, leave as recorded" (096-02 AC2). An
    # explicit empty string ("--decision ''") is a real value and clears
    # the field; see `update_lightweight`'s docstring.
    up.add_argument("--decision", default=None, help="revised decision text")
    up.add_argument("--context", default=None, help="revised context text")
    up.add_argument("--scope", default=None, help="revised scope text")
    up.add_argument("--commit", default=None, help="revised commit SHA or PR")
    up.add_argument("--date", default=None,
                    help="disambiguate when --title matches more than one "
                         "date; does not change the entry's own date")
    up.add_argument("--project-dir", default=".",
                    help="project root (default: cwd)")
    up.set_defaults(func=_cmd_update)
    # No --confirm-lightweight here, deliberately (096-02 AC8 / ADR-0039):
    # `update` refuses only on matching grounds (missing / ambiguous /
    # documentation-only title), never on the decision's content — there is
    # no routing gate to confirm past. Do not add one; see the ADR.

    pp = sub.add_parser(
        "promote",
        help="move a lightweight decision entry to an ADR via `adr.py new`")
    pp.add_argument("--title", required=True,
                    help="title of the existing entry to promote")
    pp.add_argument("--date", default=None,
                    help="disambiguate when --title matches more than one "
                         "date")
    pp.add_argument("--slug", default=None,
                    help="ADR slug override (default: kebab-cased entry "
                         "title)")
    # Mirrors adr.py new's own mutually-exclusive push group (AC5) — both
    # flags are threaded straight through to the `adr.py new` subprocess.
    promote_push_group = pp.add_mutually_exclusive_group()
    promote_push_group.add_argument(
        "--no-push", action="store_true",
        help="skip the direct push to origin/main (local-only allocation) "
             "— passed through to `adr.py new`")
    promote_push_group.add_argument(
        "--pr", action="store_true",
        help="skip the direct-push attempt; go straight to branch + PR — "
             "passed through to `adr.py new`")
    pp.add_argument("--project-dir", default=".",
                    help="project root (default: cwd)")
    pp.set_defaults(func=_cmd_promote)

    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
