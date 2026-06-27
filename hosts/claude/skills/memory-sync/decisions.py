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
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

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


def lightweight_path(project_dir: Path) -> Path:
    """Path to the project's lightweight-decisions file."""
    return project_dir / _LIGHTWEIGHT_REL


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
    Raises FileNotFoundError when the project has no lightweight-decisions file
    (it is seeded by scaffold-init / Phase 1; this helper does not create it).
    """
    title = (title or "").strip()
    decision = (decision or "").strip()
    context = (context or "").strip()
    scope = (scope or "").strip()
    if not title:
        raise ValueError("title is required")
    if not decision:
        raise ValueError("decision is required")
    date = date.strip() if date else _today()

    path = lightweight_path(project_dir)
    if not path.exists():
        raise FileNotFoundError(
            "no %s — scaffold the lightweight-decisions home first "
            "(jig:scaffold-init seeds it)" % _LIGHTWEIGHT_REL)

    text = path.read_text(encoding="utf-8")
    if _entry_key(date, title) in _existing_keys(text):
        return False
    if _ENTRIES_HEADING not in text:
        raise ValueError(
            "%s is missing its `%s` heading — cannot place the entry"
            % (_LIGHTWEIGHT_REL, _ENTRIES_HEADING))

    entry = render_entry(title, decision, context, scope, commit, date)
    new_text = text.rstrip("\n") + "\n\n" + entry
    # Plain write (not _common.atomic_io) — deliberate: this helper is
    # self-contained by DoR (no cross-tree import), and the file is an
    # owner-gated, single-writer, human-browsable doc, not a hot concurrent path.
    path.write_text(new_text, encoding="utf-8")
    return True


def _cmd_add_lightweight(args) -> int:
    project_dir = Path(args.project_dir).resolve()
    try:
        appended = add_lightweight(
            project_dir, args.title, args.decision, args.context, args.scope,
            commit=args.commit or "", date=args.date or "")
    except (FileNotFoundError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    rel = _LIGHTWEIGHT_REL
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
