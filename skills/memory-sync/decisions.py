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
the memory-sync session-end prompt (`skills/memory-sync/SKILL.md`). The scaffold
template those rubrics are seeded from quotes it too
(`templates/docs/decisions/lightweight-decisions.md.template`).
`test_decisions.py` asserts the string appears in all five, so drift fails CI.

Self-contained by design: it does NOT import the 083-04 scan lib
(`hooks/scripts/lib/decision_scan.py`) nor `memory.py`, so the host-packaging
step can copy the skill tree whole without a cross-tree dependency.
"""

import argparse
import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import project_layout  # noqa: E402

# --- Single canonical ADR-trigger sentence (mirrors ADR-0031) ---------------
# Edit here AND in ADR-0031; the four consumer sites and the scaffold template
# quote this verbatim and test_decisions.py fails CI on drift. The em-dashes
# (U+2014) are significant.
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
