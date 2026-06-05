"""Shared spec-parsing helpers used by multiple jig skills.

Extracted per ADR-0002's "three callers needing the same helper" trigger.
Today's callers: workflow.py / review.py / land.py — all three resolve
`## Slice <label>` headers via lenient case-insensitive substring matching
against a user-supplied fragment. adr.py uses a divergent
`### Decision: ...` shape and stays standalone.

Helpers in this module:
  - find_slice_section(text, fragment) -> (start, end, label)
  - find_slice_file(spec_dir, fragment) -> Path | None  (slice 018-01)
    Resolves a fragment to a sibling slice file in `spec_dir`. Match is
    on the `## Slice` heading inside each `slice-*.md` file, not the
    filename. Returns None on miss; raises SliceLookupError on ambiguity.
    `spec.md` itself is excluded — only `slice-*.md` files are walked.
  - load_slice(spec_path, fragment) -> SliceLocation  (slice 018-01)
    Dual-read: tries find_slice_file(spec_path.parent, fragment) first;
    on hit, returns the slice file's full content. Otherwise reads
    `spec_path` and falls back to `find_slice_section`. Callers get
    `loc.text[loc.start:loc.end]` uniformly without branching on layout.
  - iter_slices(spec_path) -> Iterable[SliceLocation]  (slice 018-02)
    All slices in a spec directory. Walks sibling `slice-*.md` files
    first (sorted), then embedded `## Slice` sections inside spec.md.
    Each yielded SliceLocation is independently slice-able via
    `loc.text[loc.start:loc.end]`. Used by status-board and lint
    callers that need every slice, not just one by fragment.
  - parse_frontmatter(text) -> (fields, body_offset) — extracts a leading
    `---\\n...\\n---` YAML-lite block from the head of a body (e.g. a
    slice section's content, after the `## Slice ...` heading line).
    Supports scalar values, flow-style lists `[a, b, c]`, and
    block-style lists. Returns ({}, 0) when no block is present.
  - set_frontmatter_field(text, key, value) -> new_text — idempotent
    in-place field update. Adds the field at the end of an existing
    block when missing. Creates a fresh block at the head of `text`
    when absent. Lists serialized as flow style `[a, b]`.

Callers wrap `SliceLookupError` to re-raise as their own user-facing
error type (WorkflowError / ReviewError / LandError) so CLI messages
keep their original prefix.
"""

import re
from collections import namedtuple
from pathlib import Path

# Tokens treated as truthy in a YAML-lite frontmatter boolean-ish field
# (e.g. a slice's `arch_review:`). The YAML-permissive set so a hand-edit
# isn't punished by token choice; PyYAML is not a jig dependency, so the
# set is hardcoded. Slice 045-03 lifts this here from the two prior copies
# (`workflow.py:_ARCH_REVIEW_TRUTHY` + `review_evidence._ARCH_REVIEW_TRUTHY`)
# so the orchestrator that *spawns* the arch pass and the gate that
# *requires* its evidence read one source and cannot drift. It lives in
# `parsing.py` — not `review_evidence.py` — because reading a truthy
# frontmatter flag is a generic parsing concern, and `workflow.py` already
# imports `parsing` (so it need not depend on a review-specific module just
# for a truthiness tuple).
FRONTMATTER_TRUTHY = ("true", "yes", "on", "1")


def frontmatter_flag_truthy(value) -> bool:
    """Return True iff `value` is a recognized truthy frontmatter token
    (`true`/`yes`/`on`/`1`, case-insensitive). Conservative: any non-string
    (list/None/other YAML shape) or unrecognized token is False."""
    if not isinstance(value, str):
        return False
    return value.strip().lower() in FRONTMATTER_TRUTHY


# Slice 007-01 introduced this `### Deviation log` heading-presence check in
# `land.py`; slice 045-03 lifted it here so the transition gate can reuse the
# SAME predicate (ADR-0014 §5: "045-03 should share that predicate … a
# `_common` move is a reasonable refactor") without a cross-skill import or a
# second copy of the regex. `land.py` re-exports it for its callers.
_DEVIATION_LOG_RE = re.compile(r"(?im)^###\s+deviation\s+log\b")


def check_deviation_log(section: str) -> bool:
    """Look for a `### Deviation log` (case-insensitive prefix) within the
    slice section. `### Deviation log` and `### Deviation log (after
    reconciliation)` both count. Heading-presence ONLY — whether the log is
    real prose vs. the template's `_TODO.` stub is attested by the
    reconciliation reviewer's verdict, not re-derived here (ADR-0014 §5)."""
    return bool(_DEVIATION_LOG_RE.search(section))


class SliceLookupError(RuntimeError):
    """Raised when a slice fragment can't be uniquely resolved in a spec."""


SliceLocation = namedtuple("SliceLocation", "path text start end label")
"""Result of `load_slice`. `text[start:end]` is the slice body; `path` is
the file the body came from (slice-NN-*.md or spec.md)."""


_SLICE_HEADER_RE = re.compile(r"(?im)^##\s+Slice\s+([^\n]+)$")


def find_slice_section(spec_text: str, slice_fragment: str):
    """Locate the `## Slice ...` H2 whose label contains `slice_fragment`
    (case-insensitive substring match). Returns ``(start, end, label)``:

    - ``start`` — byte offset of the opening ``##`` in the header line.
    - ``end`` — byte offset of the next ``^##\\s`` heading, or EOF.
    - ``label`` — trimmed header text after ``Slice `` (e.g.
      ``001-01 — greenfield-scaffold``).

    Raises ``SliceLookupError`` on zero or multiple matches.
    """
    headers = list(_SLICE_HEADER_RE.finditer(spec_text))
    if not headers:
        raise SliceLookupError("no '## Slice ...' headings found in spec")
    needle = slice_fragment.lower()
    matches = [h for h in headers if needle in h.group(0).lower()]
    if not matches:
        raise SliceLookupError(f"slice not found: '{slice_fragment}'")
    if len(matches) > 1:
        names = [h.group(1).strip() for h in matches]
        raise SliceLookupError(
            f"ambiguous slice fragment '{slice_fragment}' matches: {names}"
        )
    header = matches[0]
    rest = spec_text[header.end():]
    nxt = re.search(r"(?m)^##\s", rest)
    end = header.end() + (nxt.start() if nxt else len(rest))
    label = header.group(1).strip()
    return header.start(), end, label


# ---------- file-based slice resolution (slice 018-01) ----------


def find_slice_file(spec_dir, slice_fragment: str):
    """Locate a sibling `slice-*.md` file in `spec_dir` whose `## Slice`
    heading contains `slice_fragment` (case-insensitive substring).

    Returns the matching `pathlib.Path`, or `None` when no match is found
    (including: dir missing, no slice files, none match). Raises
    `SliceLookupError` when two or more slice files match.

    Only files matching `slice-*.md` are considered — `spec.md`, `.bak`,
    `.txt`, etc. are ignored. Match is on the H2 heading content inside
    each file, not the filename, so a misnamed file still resolves
    correctly (and a filename-only match without the corresponding
    heading does not).

    Only the first `## Slice` heading per file is considered. The
    file-per-slice convention this spec establishes means there should
    be exactly one. If a future slice needs multiple, revisit.
    """
    p = Path(spec_dir)
    if not p.is_dir():
        return None
    needle = slice_fragment.lower()
    matches = []
    for candidate in sorted(p.glob("slice-*.md")):
        # Read just enough to find the first `## Slice ...` heading.
        try:
            text = candidate.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        m = _SLICE_HEADER_RE.search(text)
        if m and needle in m.group(0).lower():
            matches.append(candidate)
    if not matches:
        return None
    if len(matches) > 1:
        names = [m.name for m in matches]
        raise SliceLookupError(
            f"ambiguous slice fragment '{slice_fragment}' matches "
            f"multiple files: {names}"
        )
    return matches[0]


def load_slice(spec_path, slice_fragment: str) -> SliceLocation:
    """Resolve `slice_fragment` against either a sibling slice file or
    a section inside `spec_path`, returning a uniform `SliceLocation`.

    Dual-read order:
      1. `find_slice_file(spec_path.parent, slice_fragment)` — if a
         slice file matches, returns
         `SliceLocation(slice_file_path, slice_file_text, 0,
         len(slice_file_text), label)` where `label` is parsed from the
         `## Slice` heading inside the file.
      2. Otherwise reads `spec_path` and delegates to
         `find_slice_section`, returning
         `SliceLocation(spec_path, spec_text, start, end, label)`.

    Either way, the caller does `loc.text[loc.start:loc.end]` to get
    the slice body — the layout is invisible at the call site.

    Raises `SliceLookupError` if no slice file matches AND the
    fragment is not present in `spec_path`. Re-raises ambiguity
    errors from either resolver unchanged.
    """
    spec_path = Path(spec_path)
    spec_dir = spec_path.parent

    slice_file = find_slice_file(spec_dir, slice_fragment)
    if slice_file is not None:
        text = slice_file.read_text()
        m = _SLICE_HEADER_RE.search(text)
        # find_slice_file already verified a matching heading exists.
        label = m.group(1).strip() if m else slice_fragment
        return SliceLocation(slice_file, text, 0, len(text), label)

    # Fallback: scan spec.md for the section.
    spec_text = spec_path.read_text()
    start, end, label = find_slice_section(spec_text, slice_fragment)
    return SliceLocation(spec_path, spec_text, start, end, label)


def iter_slices(spec_path):
    """Yield a `SliceLocation` for every slice in this spec's directory.

    Walk order:
      1. Sibling `slice-*.md` files, sorted by filename — each
         yielded as a whole-file SliceLocation (start=0, end=len(text)).
      2. Embedded `## Slice` sections inside `spec_path`, in document
         order — yielded with section offsets.

    A spec may have ANY mix: all slices in spec.md (legacy), all in
    sibling files (new shape), or both (mid-migration). The iter order
    is deterministic but does NOT sort by numeric label — callers that
    care about ordering by slice number should sort by `loc.label`.

    Skips files that fail to read or contain no `## Slice` heading.
    """
    spec_path = Path(spec_path)
    spec_dir = spec_path.parent

    # (1) Sibling slice files.
    if spec_dir.is_dir():
        for candidate in sorted(spec_dir.glob("slice-*.md")):
            try:
                text = candidate.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            m = _SLICE_HEADER_RE.search(text)
            if not m:
                continue
            label = m.group(1).strip()
            yield SliceLocation(candidate, text, 0, len(text), label)

    # (2) Embedded ## Slice sections in spec.md.
    if not spec_path.is_file():
        return
    spec_text = spec_path.read_text()
    headers = list(_SLICE_HEADER_RE.finditer(spec_text))
    for i, header in enumerate(headers):
        label = header.group(1).strip()
        start = header.start()
        if i + 1 < len(headers):
            end = headers[i + 1].start()
        else:
            # Bound at the next `## ` heading (any H2), or EOF.
            rest = spec_text[header.end():]
            nxt = re.search(r"(?m)^##\s", rest)
            end = header.end() + (nxt.start() if nxt else len(rest))
        yield SliceLocation(spec_path, spec_text, start, end, label)


# ---------- frontmatter (slice 014-01) ----------

# Matches a leading frontmatter block: `---\n<lines>\n---\n` at the very
# start of `text` (after optional leading blank lines, since slice
# sections begin with a newline after the `## Slice ...` header line).
_FM_BLOCK_RE = re.compile(r"\A(\s*\n)?---\n(.*?)\n---\n", re.DOTALL)


def _parse_scalar(raw: str) -> str:
    """Strip surrounding quotes and inline `# comment` tails."""
    s = raw.strip()
    # Strip inline comment (best effort — does not handle quoted '#')
    if "#" in s and not (s.startswith('"') or s.startswith("'")):
        s = s.split("#", 1)[0].rstrip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1]
    return s


def _parse_flow_list(raw: str) -> list:
    """Parse `[a, b, c]` into a list of stripped scalars. `[]` → []."""
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(p) for p in inner.split(",") if p.strip()]


def parse_frontmatter(text: str) -> tuple:
    """Extract a leading frontmatter block from `text`.

    Returns ``(fields, body_offset)``:
      - ``fields`` — dict mapping keys to values. Scalar fields are
        strings; lists (flow or block) become Python lists of strings.
        Empty/missing values are the empty string for scalars or
        empty list for keys declared as block-list with no items.
      - ``body_offset`` — number of bytes consumed by the frontmatter
        block (including the trailing newline after the closing `---`).
        0 when no block is present, so ``text[body_offset:]`` is the
        body in both cases.

    YAML-lite: tolerates `key: value`, `key: [a, b, c]`, and block-list
    form `key:\\n  - a\\n  - b`. Unknown shapes are stored as raw
    strings — the caller decides how to interpret. No PyYAML dependency.
    """
    m = _FM_BLOCK_RE.match(text)
    if not m:
        return {}, 0
    body = m.group(2)
    fields: dict = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        # Expect `key: rest` at column 0 (not indented — that's a list item).
        if line.startswith((" ", "\t")):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest.startswith("["):
            fields[key] = _parse_flow_list(rest)
            i += 1
            continue
        if rest == "":
            # Look ahead for block-list items.
            items = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if not nxt.strip():
                    j += 1
                    continue
                stripped = nxt.lstrip()
                if stripped.startswith("- "):
                    items.append(_parse_scalar(stripped[2:]))
                    j += 1
                    continue
                break
            if items:
                fields[key] = items
                i = j
                continue
            # Truly empty scalar.
            fields[key] = ""
            i += 1
            continue
        fields[key] = _parse_scalar(rest)
        i += 1
    return fields, m.end()


def _serialize_list(values: list) -> str:
    """Flow-style: `[a, b, c]` with no quoting (jig deps are slugs)."""
    return "[" + ", ".join(values) + "]"


def set_frontmatter_field(text: str, key: str, value) -> str:
    """Idempotent in-place update of a single frontmatter field.

    Behavior:
      - If a frontmatter block exists AND the key is present: replace
        the value on the existing `key:` line. Block-list form is
        rewritten to flow style (jig's canonical shape).
      - If a frontmatter block exists AND the key is absent: append
        the field at the end of the block (before the closing `---`).
      - If no frontmatter block exists: create one at the head of
        `text` containing just this field.

    `value` may be a string or a list of strings.
    """
    if isinstance(value, list):
        serialized = _serialize_list(value)
    else:
        serialized = str(value)

    m = _FM_BLOCK_RE.match(text)
    if not m:
        block = f"---\n{key}: {serialized}\n---\n"
        return block + text

    body = m.group(2)
    lines = body.splitlines()
    # Locate existing key line (at column 0, `<key>:` prefix).
    key_re = re.compile(r"^" + re.escape(key) + r":\s*(.*)$")
    idx = None
    for i, line in enumerate(lines):
        if line.startswith((" ", "\t")):
            continue
        if key_re.match(line):
            idx = i
            break
    if idx is None:
        new_body = body + "\n" + f"{key}: {serialized}"
    else:
        # Replace the value on this line AND drop any block-list
        # continuation lines (indented `- item` rows).
        new_lines = lines[:idx]
        new_lines.append(f"{key}: {serialized}")
        j = idx + 1
        while j < len(lines) and (lines[j].startswith((" ", "\t"))
                                  and lines[j].lstrip().startswith("- ")):
            j += 1
        new_lines.extend(lines[j:])
        new_body = "\n".join(new_lines)

    leading = m.group(1) or ""
    new_block = f"{leading}---\n{new_body}\n---\n"
    return new_block + text[m.end():]


def clear_frontmatter_field(text: str, key: str) -> str:
    """Idempotent removal of a single frontmatter field.

    Drops the `key:` line (and any indented block-list continuation
    rows beneath it). No-op when the key is absent or no frontmatter
    block exists — the input is returned unchanged. Used by the
    slice-claim flow (spec 049-01) to clear `claimed_by:` on release
    and on forward / back transitions.
    """
    m = _FM_BLOCK_RE.match(text)
    if not m:
        return text

    body = m.group(2)
    lines = body.splitlines()
    key_re = re.compile(r"^" + re.escape(key) + r":\s*(.*)$")
    idx = None
    for i, line in enumerate(lines):
        if line.startswith((" ", "\t")):
            continue
        if key_re.match(line):
            idx = i
            break
    if idx is None:
        return text

    # Drop the key line plus any indented block-list continuation rows.
    j = idx + 1
    while j < len(lines) and (lines[j].startswith((" ", "\t"))
                              and lines[j].lstrip().startswith("- ")):
        j += 1
    new_lines = lines[:idx] + lines[j:]
    leading = m.group(1) or ""
    if new_lines:
        new_block = f"{leading}---\n" + "\n".join(new_lines) + "\n---\n"
    else:
        # The block held only this field — leave an empty (but valid) block.
        new_block = f"{leading}---\n---\n"
    return new_block + text[m.end():]
