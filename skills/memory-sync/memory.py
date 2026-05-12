"""
jig memory-sync — slice 002-01 (explicit-sync)

Deterministic helper for persisting context to the memory layer. Claude makes
the decisions (what to persist where); this script does the file I/O,
idempotency, and self-healing of missing memory structure.

Usage:
    python3 memory.py <command> [args] <target-dir>

Commands:
    add-term <name> <definition>           → docs/memory/glossary.md
    add-learning <title> [--body=<text>]   → docs/memory/learnings.md
        (body from --body, or stdin if --body omitted)
    add-inbox <text>                       → docs/inbox.md (dated)
    promote <term> <definition>            → CLAUDE.md Hot Cache → Key terms
    summary                                → counts of memory files
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# Heading marker used to find the Key terms list inside CLAUDE.md Hot Cache.
HOT_CACHE_KEY_TERMS_HEADING = "### Key terms"

# Placeholder line inserted by scaffold-init under Key terms; replaced on first promote.
HOT_CACHE_PLACEHOLDER = re.compile(
    r"^- \(populated as the project grows.*?\)\s*$", re.MULTILINE
)


def plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _ensure_file(path: Path, default_content: str) -> None:
    """Create a file with default_content if it doesn't exist. Self-healing."""
    if path.exists():
        return
    _ensure_dir(path.parent)
    path.write_text(default_content)


def _glossary_path(target: Path) -> Path:
    path = target / "docs" / "memory" / "glossary.md"
    _ensure_file(path, "# Glossary\n\n> Status: Draft (self-healed by memory-sync)\n\n")
    return path


def _learnings_path(target: Path) -> Path:
    path = target / "docs" / "memory" / "learnings.md"
    _ensure_file(path, "# Learnings\n\n> Status: Draft (self-healed by memory-sync)\n\n")
    return path


def _inbox_path(target: Path) -> Path:
    path = target / "docs" / "inbox.md"
    _ensure_file(path, "# Inbox\n\n> Status: Draft (self-healed by memory-sync)\n\n")
    return path


def _claude_md_path(target: Path) -> Path:
    """Returns CLAUDE.md path; does not create. Callers handle absence."""
    return target / "CLAUDE.md"


def _append_section(path: Path, heading: str, body: str) -> bool:
    """Append `## <heading>\\n<body>` to `path` unless an exact `## <heading>\\n`
    already exists. Returns True if appended, False if skipped (idempotent)."""
    text = path.read_text()
    marker = f"\n## {heading}\n"
    if marker in text:
        return False
    if not text.endswith("\n"):
        text += "\n"
    text += marker + body
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text)
    return True


def add_term(target: Path, term: str, definition: str) -> bool:
    """Append a term to glossary.md. Idempotent on exact term name."""
    return _append_section(_glossary_path(target), term, definition + "\n")


def add_learning(target: Path, title: str, body: str) -> bool:
    """Append a learning to learnings.md. Idempotent on exact title."""
    return _append_section(_learnings_path(target), title, body + "\n")


def add_inbox(target: Path, item: str) -> bool:
    """Append a dated bullet to inbox.md. Always appends (no idempotency check
    — inbox is a stream, duplicate-ish entries are acceptable)."""
    path = _inbox_path(target)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = f"- [{date}] {item}\n"
    with open(path, "a") as f:
        f.write(line)
    return True


def promote(target: Path, term: str, definition: str) -> bool:
    """Add a term to CLAUDE.md Hot Cache → Key terms.
    If CLAUDE.md is absent (pre-scaffold-init project), fall back to glossary
    and warn on stderr. Idempotent on exact `- **<term>**` presence."""
    claude_md = _claude_md_path(target)
    if not claude_md.exists():
        sys.stderr.write(
            "warning: CLAUDE.md not found at target root; "
            "falling back to glossary.md for term '%s'\n" % term
        )
        return add_term(target, term, definition)

    text = claude_md.read_text()
    if HOT_CACHE_KEY_TERMS_HEADING not in text:
        sys.stderr.write(
            "warning: CLAUDE.md missing Key terms section; "
            "falling back to glossary.md for term '%s'\n" % term
        )
        return add_term(target, term, definition)

    entry = f"- **{term}** — {definition}"
    # Idempotency: already promoted? Anchor to line start to avoid false positives
    # when the marker appears inside another bullet's prose.
    if re.search(rf"(?m)^- \*\*{re.escape(term)}\*\*", text):
        return False

    # Replace the placeholder line if present (first promotion);
    # otherwise insert the new bullet right after the heading.
    if HOT_CACHE_PLACEHOLDER.search(text):
        new_text = HOT_CACHE_PLACEHOLDER.sub(entry, text, count=1)
    else:
        # Insert after the Key terms heading and any existing bullets — find
        # the line right after the section heading and append within the section.
        heading_idx = text.index(HOT_CACHE_KEY_TERMS_HEADING)
        line_end = text.index("\n", heading_idx)
        # Insert after the heading line; will become first bullet, others shift.
        new_text = text[: line_end + 1] + entry + "\n" + text[line_end + 1 :]

    claude_md.write_text(new_text)
    return True


def summary(target: Path) -> str:
    """Return a one-line-per-file count summary of the memory layer state."""
    lines = ["# Memory Summary", ""]

    def count_sections(path: Path) -> int:
        if not path.exists():
            return 0
        return len(re.findall(r"(?m)^## ", path.read_text()))

    def count_bullets(path: Path) -> int:
        if not path.exists():
            return 0
        return len(re.findall(r"(?m)^- ", path.read_text()))

    g = count_sections(target / "docs/memory/glossary.md")
    le = count_sections(target / "docs/memory/learnings.md")
    inb = count_bullets(target / "docs/inbox.md")
    lines.append(f"- glossary entries: **{g}**")
    lines.append(f"- learnings entries: **{le}**")
    lines.append(f"- inbox items: **{inb}**")
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="memory.py",
                                description="jig memory-sync helper")
    sub = p.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("add-term")
    pt.add_argument("term")
    pt.add_argument("definition")
    pt.add_argument("target")

    pl = sub.add_parser("add-learning")
    pl.add_argument("title")
    pl.add_argument("--body", default=None,
                    help="learning body; if omitted, read from stdin")
    pl.add_argument("target")

    pi = sub.add_parser("add-inbox")
    pi.add_argument("item")
    pi.add_argument("target")

    pp = sub.add_parser("promote")
    pp.add_argument("term")
    pp.add_argument("definition")
    pp.add_argument("target")

    ps = sub.add_parser("summary")
    ps.add_argument("target")

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    target = Path(ns.target).resolve()
    if not target.exists():
        sys.stderr.write(f"target does not exist: {target}\n")
        return 1

    try:
        if ns.command == "add-term":
            added = add_term(target, ns.term, ns.definition)
            print(f"glossary: {'added' if added else 'already present'} '{ns.term}'")
        elif ns.command == "add-learning":
            body = ns.body if ns.body is not None else sys.stdin.read().rstrip()
            if not body.strip():
                sys.stderr.write(
                    "warning: add-learning called with empty body — entry "
                    f"'{ns.title}' will have no content; consider passing --body or piping text\n"
                )
            added = add_learning(target, ns.title, body)
            print(f"learnings: {'added' if added else 'already present'} '{ns.title}'")
        elif ns.command == "add-inbox":
            add_inbox(target, ns.item)
            print(f"inbox: parked '{ns.item}'")
        elif ns.command == "promote":
            added = promote(target, ns.term, ns.definition)
            print(f"hot cache: {'promoted' if added else 'already present'} '{ns.term}'")
        elif ns.command == "summary":
            sys.stdout.write(summary(target))
    except Exception as exc:
        sys.stderr.write(f"memory-sync failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
