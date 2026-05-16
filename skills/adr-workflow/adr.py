"""
jig adr-workflow helper — slice 005-01 (adr-helper) + 008-03 (ADR-0004 shape)

Deterministic ADR lifecycle helper:
  - `new`          : scaffold a new ADR from the template, auto-numbered.
  - `accept`       : flip Status from Proposed to Accepted (atomic write).
  - `index`        : regenerate the `## Index` section of
                     docs/decisions/README.md.
  - `resolve-todo` : strike through a refinement-todo entry and link the
                     resolving ADR.

Mirrors the shape of workflow.py / review.py / memory.py / scaffold.py.

Usage:
    python3 adr.py new <slug> [--title "<Title>"]
    python3 adr.py accept <NNNN>
    python3 adr.py index <decisions-dir>
    python3 adr.py resolve-todo <NNNN> "<heading fragment>"

Run from the project root that contains `docs/decisions/` (for `new`,
`accept`, `resolve-todo`); `index` takes an explicit `<decisions-dir>`
argument. Files are named `adr-NNNN-<slug>.md` per ADR-0004.
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.parsing import set_frontmatter_field as _set_frontmatter_field


class AdrError(RuntimeError):
    """User-facing error; CLI exits with status 2."""


# Template/placeholder constants — kept in module scope so tests can read them.
PLACEHOLDER_NUMBER = "{{NUMBER}}"
PLACEHOLDER_TITLE = "{{TITLE}}"
PLACEHOLDER_DATE = "{{DATE}}"

TEMPLATE_RELATIVE = (
    Path("templates") / "docs" / "decisions" / "adr-0000-template.md"
)


# ---------- shared helpers ----------


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


def _atomic_write(path: Path, content: str) -> None:
    """Write `content` to `path` via a `.tmp` sibling + os.replace.
    Crash-safe on same-FS rename (POSIX-atomic)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _template_path() -> Path:
    return _plugin_root() / TEMPLATE_RELATIVE


def _adr_files(adrs_dir: Path) -> list:
    """Return sorted list of `adr-NNNN-*.md` files under `adrs_dir`,
    excluding README.md. Files whose basename does not start with
    `adr-NNNN-` are also excluded (per ADR-0004's canonical shape)."""
    if not adrs_dir.is_dir():
        return []
    out = []
    for p in sorted(adrs_dir.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        if not re.match(r"^adr-\d{4}-", p.name):
            continue
        out.append(p)
    return out


def _parse_adr_number(filename: str) -> int:
    m = re.match(r"^adr-(\d{4})-", filename)
    if not m:
        raise AdrError(
            f"file does not start with `adr-NNNN-` prefix: {filename}"
        )
    return int(m.group(1))


def _slug_to_title(slug: str) -> str:
    """`my-decision` → `My Decision`. Empty/edge-case slugs are passed through."""
    parts = [p for p in re.split(r"[-_]", slug) if p]
    return " ".join(p[0].upper() + p[1:] if p else p for p in parts)


# ---------- new ----------


def cmd_new(adrs_dir: Path, slug: str, title: str) -> Path:
    """Scaffold `docs/decisions/adr-NNNN-<slug>.md` from the template."""
    if not slug or not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise AdrError(
            f"invalid slug: '{slug}' (use lowercase letters, digits, hyphens)"
        )
    if not adrs_dir.is_dir():
        raise AdrError(f"decisions directory not found: {adrs_dir}")

    template = _template_path()
    if not template.is_file():
        raise AdrError(f"template not found: {template}")

    # Slug collision check — ANY existing `adr-NNNN-<slug>.md` with the
    # same slug body is a conflict, even at a different number.
    existing = _adr_files(adrs_dir)
    for p in existing:
        # Strip leading "adr-NNNN-" prefix (9 chars) and trailing ".md".
        body = p.stem[9:] if len(p.stem) > 9 else ""
        if body == slug:
            raise AdrError(f"slug collision: {p.name} already exists")

    # Auto-number: max existing + 1, or 1 if none. Zero-padded to 4 digits.
    if existing:
        next_n = max(_parse_adr_number(p.name) for p in existing) + 1
    else:
        next_n = 1
    number = f"{next_n:04d}"

    if not title:
        title = _slug_to_title(slug)

    content = template.read_text()
    content = content.replace(PLACEHOLDER_NUMBER, number)
    content = content.replace(PLACEHOLDER_TITLE, title)
    content = content.replace(PLACEHOLDER_DATE, _today())

    target = adrs_dir / f"adr-{number}-{slug}.md"
    if target.exists():  # Defensive — auto-num should have prevented this.
        raise AdrError(f"target already exists: {target}")
    _atomic_write(target, content)
    return target


# ---------- accept ----------


def _find_adr_by_number(adrs_dir: Path, number: str) -> Path:
    """Locate the single `adr-NNNN-*.md` file matching `number`
    (zero-padded). Raises on miss or ambiguity."""
    if not re.match(r"^\d{4}$", number):
        raise AdrError(f"NNNN must be 4-digit zero-padded: '{number}'")
    matches = list(adrs_dir.glob(f"adr-{number}-*.md"))
    if not matches:
        raise AdrError(f"ADR not found: NNNN={number}")
    if len(matches) > 1:
        names = sorted(p.name for p in matches)
        raise AdrError(
            f"ambiguous ADR prefix '{number}' matches: {names}"
        )
    return matches[0]


# Match a Status line body of `Proposed (YYYY-MM-DD)` (or with extra trailing
# content). Captures the date so we can preserve formatting if needed.
_STATUS_PROPOSED_RE = re.compile(
    r"(?m)^(Proposed)[ \t]*\(([0-9]{4}-[0-9]{2}-[0-9]{2})\)[ \t]*$"
)


def cmd_accept(adrs_dir: Path, number: str) -> Path:
    """Flip the Status from Proposed → Accepted (today's date)."""
    adr_path = _find_adr_by_number(adrs_dir, number)
    text = adr_path.read_text()

    # Scope the search to the `## Status` section only.
    status_match = re.search(r"(?m)^##\s+Status\s*$", text)
    if not status_match:
        raise AdrError(f"ADR has no '## Status' section: {adr_path.name}")
    rest = text[status_match.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    section_end = status_match.end() + (next_h2.start() if next_h2 else len(rest))
    section_body = text[status_match.end():section_end]

    if not _STATUS_PROPOSED_RE.search(section_body):
        # Distinguish already-Accepted / Superseded for a useful error message.
        if re.search(r"(?m)^Accepted\s*\(", section_body):
            raise AdrError(
                f"ADR {adr_path.name} is already Accepted; refusing to re-accept "
                "(ADRs are immutable — supersede instead)"
            )
        raise AdrError(
            f"ADR {adr_path.name} Status is not 'Proposed (...)'. "
            "Refusing to flip; only Proposed → Accepted is supported in this slice."
        )

    new_body = _STATUS_PROPOSED_RE.sub(
        lambda _m: f"Accepted ({_today()})", section_body, count=1
    )
    new_text = text[:status_match.end()] + new_body + text[section_end:]
    # Slice 014-01: stamp `last_verified: <today>` in the ADR frontmatter
    # at the single point where an ADR becomes decision-of-record. Adds
    # the frontmatter block if absent; updates the field if present.
    new_text = _set_frontmatter_field(new_text, "last_verified", _today())
    _atomic_write(adr_path, new_text)
    return adr_path


# ---------- index ----------


def _extract_title(adr_text: str) -> str:
    m = re.search(r"(?m)^#\s+ADR-\d{4}:\s+(.+?)\s*$", adr_text)
    return m.group(1).strip() if m else "(untitled)"


def _extract_status_and_date(adr_text: str) -> tuple:
    """Returns (status, date) extracted from the first non-empty line of the
    `## Status` section. Falls back to ('(unknown)', '') on miss."""
    m = re.search(r"(?m)^##\s+Status\s*$", adr_text)
    if not m:
        return ("(unknown)", "")
    rest = adr_text[m.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    body = rest[: next_h2.start()] if next_h2 else rest
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        sm = re.match(r"^([A-Za-z][A-Za-z _-]*?)\s*\(([0-9]{4}-[0-9]{2}-[0-9]{2})\)\s*$",
                      line)
        if sm:
            return (sm.group(1).strip(), sm.group(2))
        # Free-form fallback: take the first word as status, no date.
        return (line.split()[0], "")
    return ("(unknown)", "")


_DESCRIPTION_MAX = 120

# Inbox 2026-05-12 refinement: common abbreviations whose trailing period is
# NOT a sentence boundary. The detector below looks back from each candidate
# period and refuses to truncate when one of these endings matches.
# Kept intentionally small: this is a sentence-boundary heuristic, not NLP.
_ABBREVIATIONS = (
    "e.g.", "i.e.", "etc.", "cf.", "vs.", "viz.",
    "al.", "et al.",
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "St.",
)


def _is_abbreviation_ending_at(text: str, period_index: int) -> bool:
    """Return True iff `text[: period_index + 1]` ends with a known
    abbreviation. `period_index` points at the candidate `.`.

    Match is case-sensitive on purpose: `Mr.` should match but a stray `e.g.`
    in a code-style identifier won't accidentally match `E.G.`.
    """
    head = text[: period_index + 1]
    for abbr in _ABBREVIATIONS:
        if head.endswith(abbr):
            # Boundary check: the char before the abbreviation must not be a
            # letter (otherwise `mile.` would accidentally match `le.`).
            before_idx = len(head) - len(abbr) - 1
            if before_idx < 0 or not head[before_idx].isalpha():
                return True
    return False


def _extract_description(adr_text: str) -> str:
    """First non-empty paragraph from `## Context`, truncated at first
    sentence-ending punctuation if multi-line or > 120 chars.

    Returns '' on miss (caller fills in)."""
    m = re.search(r"(?m)^##\s+Context\s*$", adr_text)
    if not m:
        return ""
    rest = adr_text[m.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    body = rest[: next_h2.start()] if next_h2 else rest

    # First non-empty paragraph: contiguous lines separated by blank lines.
    paragraph_lines = []
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if paragraph_lines:
                break
            continue
        paragraph_lines.append(line.strip())
    if not paragraph_lines:
        return ""
    paragraph = " ".join(paragraph_lines)

    multi_line = len(paragraph_lines) > 1
    too_long = len(paragraph) > _DESCRIPTION_MAX

    if multi_line or too_long:
        # Truncate at first sentence-ending punctuation (`.` / `?` / `!`) when
        # followed by space or EOL. Walk char-by-char and skip periods that
        # belong to known abbreviations (`e.g.`, `i.e.`, `etc.` …).
        for i, ch in enumerate(paragraph):
            if ch in ".?!":
                after = paragraph[i + 1: i + 2]
                if after == "" or after.isspace():
                    if ch == "." and _is_abbreviation_ending_at(paragraph, i):
                        continue
                    return paragraph[: i + 1]
        # No sentence boundary found → hard-truncate.
        return paragraph[: _DESCRIPTION_MAX].rstrip() + "…"
    return paragraph


def _render_index_entries(adr_paths: list) -> list:
    """Return one bullet line per ADR, sorted ascending by NNNN."""
    rows = []
    for p in sorted(adr_paths, key=lambda x: _parse_adr_number(x.name)):
        text = p.read_text()
        number = f"{_parse_adr_number(p.name):04d}"
        title = _extract_title(text)
        status, date_str = _extract_status_and_date(text)
        description = _extract_description(text) or "(no description)"
        # Filename stem is `adr-NNNN-<slug>` (9-char prefix to strip).
        slug = p.stem[9:] if len(p.stem) > 9 else p.stem
        meta = f"({date_str}, {status})" if date_str else f"({status})"
        rows.append(
            f"- [ADR-{number}: {title}](adr-{number}-{slug}.md) — "
            f"{description} {meta}"
        )
    return rows


def cmd_index(adrs_dir: Path) -> Path:
    """Regenerate the `## Index` section of `<decisions-dir>/README.md`."""
    if not adrs_dir.is_dir():
        raise AdrError(f"decisions directory not found: {adrs_dir}")
    readme = adrs_dir / "README.md"
    if not readme.is_file():
        raise AdrError(f"README.md not found in: {adrs_dir}")
    text = readme.read_text()

    # Match the `## Index` heading line. Use `[ \t]*$` instead of `\s*$` so the
    # regex does NOT consume the trailing newline — preserving it keeps our
    # replacement boundary clean (and idempotent).
    index_h2 = re.search(r"(?m)^##[ \t]+Index[ \t]*$", text)
    if not index_h2:
        raise AdrError(
            f"README.md has no '## Index' heading: {readme}"
        )
    # Find the next `## ` heading (or EOF) to bound the section we replace.
    rest = text[index_h2.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    section_end = index_h2.end() + (next_h2.start() if next_h2 else len(rest))

    adrs = _adr_files(adrs_dir)
    bullets = _render_index_entries(adrs)

    # New body: two blank lines after the heading, then bullets (or empty if
    # none), then a trailing blank line before the next section (preserves
    # spacing for readability).
    if bullets:
        body = "\n\n" + "\n".join(bullets) + "\n\n"
    else:
        body = "\n\n"
    new_text = text[: index_h2.end()] + body + text[section_end:]

    if new_text == text:
        # Idempotent no-op.
        return readme
    _atomic_write(readme, new_text)
    return readme


# ---------- resolve-todo ----------


def _is_struck_through(heading_line: str) -> bool:
    """Heading already wrapped in strikethrough? Detect by `### ~~` prefix."""
    return bool(re.match(r"^###\s+~~", heading_line))


def _find_todo_section(todo_text: str, fragment: str) -> tuple:
    """Locate the H3 section whose heading text contains `fragment`
    (case-insensitive substring). Returns (header_start, header_end,
    section_end, heading_line). Raises on miss/ambiguity."""
    headers = list(re.finditer(r"(?im)^###\s+[^\n]+$", todo_text))
    if not headers:
        raise AdrError("no '### ' headings found in refinement-todo.md")
    needle = fragment.lower()
    matches = [h for h in headers if needle in h.group(0).lower()]
    if not matches:
        raise AdrError(f"section not found: fragment '{fragment}' matches nothing")
    if len(matches) > 1:
        names = [h.group(0).strip() for h in matches]
        raise AdrError(
            f"ambiguous fragment '{fragment}' matches: {names}"
        )
    header = matches[0]
    heading_line = header.group(0)
    rest = todo_text[header.end():]
    nxt = re.search(r"(?m)^(?:##|###)\s", rest)
    section_end = header.end() + (nxt.start() if nxt else len(rest))
    return header.start(), header.end(), section_end, heading_line


def cmd_resolve_todo(project_dir: Path, number: str, fragment: str) -> Path:
    """Strikethrough a refinement-todo section + append Resolved-by link.

    `project_dir` must contain both `docs/decisions/` and
    `docs/refinement-todo.md`."""
    adrs_dir = project_dir / "docs" / "decisions"
    todo_path = project_dir / "docs" / "refinement-todo.md"

    if not todo_path.is_file():
        raise AdrError(f"refinement-todo.md not found: {todo_path}")
    if not adrs_dir.is_dir():
        raise AdrError(
            f"docs/decisions/ not found in project: {project_dir}"
        )

    # Resolve ADR + verify Accepted state.
    adr_path = _find_adr_by_number(adrs_dir, number)
    adr_text = adr_path.read_text()
    status, _ = _extract_status_and_date(adr_text)
    if status != "Accepted":
        raise AdrError(
            f"ADR {adr_path.name} is not Accepted (status={status}); "
            "refusing to resolve-todo. Accept the ADR first."
        )
    title = _extract_title(adr_text)

    todo_text = todo_path.read_text()
    h_start, h_end, s_end, heading_line = _find_todo_section(todo_text, fragment)

    if _is_struck_through(heading_line):
        raise AdrError(
            f"section already struck through: '{heading_line}'. "
            "Refusing to double-resolve."
        )

    # 1) Rewrite the heading: `### Decision: Foo` → `### ~~Decision: Foo~~ — RESOLVED YYYY-MM-DD`.
    new_heading = _strikethrough_heading(heading_line)

    # 2) Wrap the first **Deferred:** line in the section body.
    body = todo_text[h_end:s_end]
    new_body = _strikethrough_first_deferred(body)

    # 3) Append Resolved-by line at the section's end. Preserve trailing
    # whitespace pattern: insert before any trailing newlines so the next
    # heading still has its leading blank line.
    # Filename stem is `adr-NNNN-<slug>` (9-char prefix to strip).
    slug = adr_path.stem[9:] if len(adr_path.stem) > 9 else adr_path.stem
    number_str = f"{_parse_adr_number(adr_path.name):04d}"
    resolved_line = (
        f"**Resolved by:** [ADR-{number_str}: {title}]"
        f"(decisions/adr-{number_str}-{slug}.md).\n"
    )
    new_body = _append_to_section(new_body, resolved_line)

    new_text = todo_text[:h_start] + new_heading + new_body + todo_text[s_end:]
    _atomic_write(todo_path, new_text)
    return todo_path


def _strikethrough_heading(heading_line: str) -> str:
    """`### Decision: Foo` → `### ~~Decision: Foo~~ — RESOLVED YYYY-MM-DD`."""
    m = re.match(r"^(###\s+)(.+?)\s*$", heading_line)
    if not m:
        # Defensive — _find_todo_section already enforced the prefix.
        return f"### ~~{heading_line.lstrip('# ').rstrip()}~~ — RESOLVED {_today()}\n"
    return f"{m.group(1)}~~{m.group(2)}~~ — RESOLVED {_today()}"


def _strikethrough_first_deferred(section_body: str) -> str:
    """Wrap the first `**Deferred:** ...` line in `~~...~~`.

    If no Deferred line is found, the body is returned unchanged."""
    lines = section_body.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.lstrip().startswith("**Deferred:**"):
            stripped = line.rstrip("\n")
            trailing = line[len(stripped):]
            # Avoid double-wrapping if (somehow) already struck.
            if stripped.lstrip().startswith("~~") and stripped.rstrip().endswith("~~"):
                return section_body
            lines[i] = f"~~{stripped}~~{trailing}"
            break
    return "".join(lines)


def _append_to_section(section_body: str, line: str) -> str:
    """Append `line` to the end of the section body, preserving the trailing
    blank-line buffer before the next heading. Idempotent on exact-line presence."""
    if line.rstrip() in section_body:
        return section_body  # Already appended (defensive).

    # Strip trailing newlines, append, then restore one trailing blank line.
    stripped = section_body.rstrip("\n")
    return stripped + "\n" + line + "\n"


# ---------- CLI plumbing ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="adr.py",
        description="jig adr-workflow helper (new / accept / index / resolve-todo)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("new", help="scaffold a new ADR file")
    pn.add_argument("slug", help="kebab-case slug, e.g. my-decision")
    pn.add_argument("--title", default="", help="Title (default: title-cased slug)")

    pa = sub.add_parser("accept", help="flip an ADR's Status from Proposed → Accepted")
    pa.add_argument("number", help="4-digit ADR number (e.g. 0003)")

    pi = sub.add_parser("index", help="regenerate the Index section of ADR README.md")
    pi.add_argument("adrs_dir", help="path to docs/decisions/")

    pr = sub.add_parser("resolve-todo",
                        help="mark a refinement-todo section resolved by an ADR")
    pr.add_argument("number", help="4-digit ADR number")
    pr.add_argument("fragment", help="case-insensitive substring of the heading text")

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        if ns.cmd == "new":
            adrs_dir = Path.cwd() / "docs" / "decisions"
            target = cmd_new(adrs_dir, ns.slug, ns.title)
            print(str(target.relative_to(Path.cwd())) if target.is_relative_to(Path.cwd())
                  else str(target))
        elif ns.cmd == "accept":
            adrs_dir = Path.cwd() / "docs" / "decisions"
            target = cmd_accept(adrs_dir, ns.number)
            print(str(target.relative_to(Path.cwd())) if target.is_relative_to(Path.cwd())
                  else str(target))
        elif ns.cmd == "index":
            adrs_dir = Path(ns.adrs_dir).resolve()
            target = cmd_index(adrs_dir)
            print(str(target))
        elif ns.cmd == "resolve-todo":
            project_dir = Path.cwd()
            target = cmd_resolve_todo(project_dir, ns.number, ns.fragment)
            print(str(target.relative_to(Path.cwd())) if target.is_relative_to(Path.cwd())
                  else str(target))
    except AdrError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:  # noqa: BLE001 — surface programming errors clearly.
        sys.stderr.write(f"adr.py failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
