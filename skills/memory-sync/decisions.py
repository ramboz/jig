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
import sys
from collections import namedtuple
from pathlib import Path

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


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="jig lightweight-decisions helper (add-lightweight)")
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
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
