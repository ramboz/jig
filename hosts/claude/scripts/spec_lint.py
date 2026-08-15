"""
spec_lint.py — AC contradiction detector for jig specs.

Scans a spec file for acceptance criteria (ACs) within each slice and
reports cases where a phrase required verbatim in one AC is forbidden by
another AC in the same slice.

Motivating incident (slice 012-01, deviation log §1):
  AC #1 required the description contain "personal multi-persona reviewer".
  AC #3 forbade "multi-persona" anywhere in the description.
  The contradiction was unsatisfiable and discovered only at implementation time.

This helper detects such pairs before implementation begins, as a pre-transition
check when moving a slice to READY_FOR_IMPLEMENTATION.

Usage:
    python3 scripts/spec_lint.py <spec.md> [--slice <fragment>] [--strict]
    python3 scripts/spec_lint.py --all [--strict]
    python3 scripts/spec_lint.py            # no-arg form is equivalent to --all

Exit codes:
    0 — no contradictions (or --strict: no contradictions AND no parse warnings)
    1 — at least one AC contradiction found across the scanned specs
    2 — user error (file not found, ambiguous fragment, conflicting flags)

Options:
    --slice <fragment>   Lint only the matching slice (case-insensitive substring).
                         Requires a positional <spec.md>.
    --all                Lint every `docs/specs/*/spec.md` under the cwd.
                         Reports each spec, then aggregates exit codes.
    --strict             Exit 1 also on parse warnings (default: warnings are informational).
"""

import argparse
import re
import sys
from pathlib import Path

# Slice 018-02: route slice iteration through the shared common parser
# so spec_lint sees both file-per-slice and embedded-in-spec.md layouts.
# Kept inside a try/except so the script still runs (degraded — embedded
# only) if it's ever invoked outside a tree containing skills/_common/.
#
# Slice 029-01: also imports `parse_frontmatter` for the `kind` enum
# validation and spike body-shape soft-warn. Same try/except fallback.
try:
    _common_dir = Path(__file__).resolve().parent.parent / "skills" / "_common"
    if str(_common_dir) not in sys.path:
        sys.path.insert(0, str(_common_dir))
    from parsing import iter_slices as _iter_slices_common  # type: ignore
    from parsing import parse_frontmatter as _parse_frontmatter  # type: ignore
except ImportError:  # pragma: no cover — bare-script fallback
    _iter_slices_common = None
    _parse_frontmatter = None

# ---------------------------------------------------------------------------
# Slice parsing — historically mirrored _common/parsing.py to keep this
# script standalone. After 018-02 it routes through `_common.iter_slices`
# when present, falling back to this local scan over `spec.md` only.
# ---------------------------------------------------------------------------

_SLICE_HEADER_RE = re.compile(r"(?im)^##\s+Slice\s+([^\n]+)$")


def _iter_slices(spec_text: str):
    """Yield (label, section_text) for each ## Slice ... heading."""
    headers = list(_SLICE_HEADER_RE.finditer(spec_text))
    for i, header in enumerate(headers):
        label = header.group(1).strip()
        start = header.start()
        if i + 1 < len(headers):
            end = headers[i + 1].start()
        else:
            end = len(spec_text)
        yield label, spec_text[start:end]


# ---------------------------------------------------------------------------
# AC parsing — numbered list under **Acceptance Criteria:**
# ---------------------------------------------------------------------------

_AC_HEADER_RE = re.compile(r"\*\*Acceptance\s+Criteria:\*\*\s*\n", re.IGNORECASE)
_NUMBERED_ITEM_RE = re.compile(r"^(\d+)\.\s+(.*)$")


def _parse_ac_items(slice_text: str) -> list:
    """Return list of (ac_number: int, ac_text: str) for this slice's ACs.

    Multi-line ACs are joined into a single string. Parsing stops at the
    next bold H3/H4 header (e.g. **DoD**) or a line that starts a new top-
    level section (##).
    """
    m = _AC_HEADER_RE.search(slice_text)
    if not m:
        return []
    rest = slice_text[m.end():]
    items = []
    current_num = None
    current_lines = []

    for line in rest.splitlines():
        # End of AC block on next ## heading
        if re.match(r"^##", line):
            break
        # A new numbered item
        nm = _NUMBERED_ITEM_RE.match(line)
        if nm:
            if current_num is not None:
                items.append((current_num, " ".join(current_lines)))
            current_num = int(nm.group(1))
            current_lines = [nm.group(2)]
            continue
        # Blank line — might end the list if no current item
        if not line.strip():
            if current_num is not None and current_lines:
                # Allow one blank inside a multi-line AC; stop on bold header
                # or a second blank (we peek forward implicitly by continuing).
                current_lines.append("")
            continue
        # Non-blank continuation — belongs to current item if indented or if
        # we're still inside one, unless it's a bold section header.
        if current_num is not None:
            if re.match(r"^\*\*[A-Z][^*]+:\*\*", line):
                # New bold section — end of AC list
                break
            current_lines.append(line)

    if current_num is not None:
        items.append((current_num, " ".join(current_lines)))
    return items


# ---------------------------------------------------------------------------
# Phrase extraction
# ---------------------------------------------------------------------------

# Markers that introduce a REQUIRED exact phrase.
_REQUIRED_MARKERS = re.compile(
    r"(?:this exact phrasing|exact phrasing|exact phrase|exact wording"
    r"|exact text|exact order|using this exact|with this exact)",
    re.IGNORECASE,
)

# Markers that introduce FORBIDDEN phrases.
_FORBIDDEN_MARKERS = re.compile(
    r"(?:NOT\s+contain|does\s+not\s+contain|must\s+not\s+contain"
    r"|must\s+not\s+include|never\s+contain|must\s+never\s+contain"
    r"|is\s+forbidden|are\s+forbidden|prohibited)",
    re.IGNORECASE,
)

# A quoted string: `...` or "..." (non-greedy, single-line, 1–200 chars).
_QUOTED_RE = re.compile(r'["`]([^"`\n]{1,200})["`]')


def _extract_phrases_near(text: str, marker_re: re.Pattern, window: int = 600) -> list:
    """Find all matches of marker_re in text; for each, extract quoted strings
    within `window` characters after the match start.

    Returns a list of quoted strings (deduplicated, order-preserved).
    """
    seen = set()
    results = []
    for m in marker_re.finditer(text):
        segment = text[m.start(): m.start() + window]
        for qm in _QUOTED_RE.finditer(segment):
            phrase = qm.group(1)
            if phrase not in seen:
                seen.add(phrase)
                results.append(phrase)
    return results


# ---------------------------------------------------------------------------
# Slice 029-01: `kind:` enum validation + spike body-shape soft-warn.
#
# The `kind` field on slice frontmatter is a typed enum (default unset).
# Allowed values: `spike` (research/timeboxed unknown reduction), `feature`
# (documented explicit-default synonym for unset).
#
# `kind: spike` slices carry four labelled body blocks (Question /
# Time-box / Findings / Outcome). spec_lint hard-errors on unknown enum
# values and soft-warns on missing spike body labels (warns, not errors —
# mid-flight spikes legitimately have empty Findings/Outcome).
# ---------------------------------------------------------------------------

ALLOWED_KIND_VALUES = ("spike", "feature")

SPIKE_BODY_LABELS = (
    "**Question:**",
    "**Time-box:**",
    "**Findings:**",
    "**Outcome:**",
)


def _extract_slice_frontmatter_scalar(section: str, field: str) -> str:
    """Return a scalar `field:` value from a slice section's frontmatter, or
    empty string when the field is absent.

    Handles both layouts (mirrors workflow.py's `_split_slice_section`):
      - File-per-slice: frontmatter at column 0 of `section`.
      - Embedded: section starts with `## Slice ...`; frontmatter, if
        any, follows on the next lines.

    Falls back to a regex-based scan when `_parse_frontmatter` isn't
    importable (bare-script invocation outside a jig tree).

    Slice 111-02 generalized this out of `_extract_kind` (ADR-0002
    extract-on-third-caller: `kind`, `status`, and `blocked_by` all read
    frontmatter scalars now).
    """
    if section.startswith("##"):
        nl = section.find("\n")
        body = section[nl + 1:] if nl >= 0 else ""
    else:
        body = section

    if _parse_frontmatter is not None:
        fields, _ = _parse_frontmatter(body)
        return str(fields.get(field, "")).strip()

    # Bare-script fallback: pull `field:` out of any leading `---` block.
    # Mirrors `_common.parsing._parse_scalar`: strip inline `# comment`
    # tail when value is unquoted, then strip matched surrounding quotes.
    m = re.match(r"\A(\s*\n)?---\n(.*?)\n---\n", body, re.DOTALL)
    if not m:
        return ""
    for line in m.group(2).splitlines():
        line = line.strip()
        if line.startswith(f"{field}:"):
            value = line.partition(":")[2].strip()
            if "#" in value and not (value.startswith('"') or value.startswith("'")):
                value = value.split("#", 1)[0].rstrip()
            if len(value) >= 2 and (
                (value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")
            ):
                value = value[1:-1]
            return value
    return ""


def _extract_kind(section: str) -> str:
    """Return the `kind:` scalar from a slice section's frontmatter, or
    empty string when no `kind:` field is present. Thin wrapper over
    `_extract_slice_frontmatter_scalar`."""
    return _extract_slice_frontmatter_scalar(section, "kind")


# Slice 111-02 (ADR-0057): a `blocked_by:` annotation is only meaningful on an
# ACTIONABLE slice — one whose next step is real work that is currently
# prevented. Mirror of workflow.py's `_BLOCKER_ACTIONABLE_STATUSES`
# (`_CLAIM_WORKING_STATUSES` + `READY_FOR_IMPLEMENTATION`); kept as a small
# inline mirror per ADR-0002 (two callers). If the actionable set changes in
# workflow.py, update this to match.
_BLOCKER_ACTIONABLE_STATUSES = frozenset({
    "READY_FOR_IMPLEMENTATION",
    "READY_FOR_REVIEW",
    "IN_PROGRESS",
    "REVIEWED",
    "RECONCILED",
})


def check_blocked_annotation(label: str, section: str) -> list:
    """Slice 111-02 (ADR-0057): return a soft-warning list when a slice carries
    a non-empty `blocked_by:` on a NON-actionable status
    (`DRAFT` / `DONE` / `DEFERRED` / `ABANDONED`) — where the annotation is
    almost certainly a misfiled `dependencies:` or `DEFERRED`. Returns [] for
    the valid actionable case and when `blocked_by:` is absent/whitespace-only.
    Warn-only: never contributes an error, so it cannot flip the exit code
    (soft unless the caller passes `--strict`)."""
    blocked_by = _extract_slice_frontmatter_scalar(section, "blocked_by")
    if not blocked_by.strip():
        return []
    status = _extract_slice_frontmatter_scalar(section, "status")
    if status in _BLOCKER_ACTIONABLE_STATUSES:
        return []
    return [
        f"`blocked_by:` is set on a non-actionable slice (status "
        f"{status or 'unset'}); a first-class blocker belongs on an actionable "
        f"slice (READY_FOR_IMPLEMENTATION or a working state). This looks like a "
        f"misfiled `dependencies:` or a `DEFERRED` parking — see ADR-0057."
    ]


def check_kind_and_body_shape(label: str, section: str) -> tuple:
    """Return (errors: list[str], warnings: list[str]).

    Errors fire when `kind:` is set to an unknown enum value. Each error
    names the offending value AND the allowed values so the author can
    fix the typo without consulting docs.

    Warnings fire when `kind: spike` is set but one or more of the four
    labelled body blocks is missing. Each warning names the missing
    label(s). Spikes mid-flight legitimately have empty Findings/Outcome,
    so this is soft-warn — not a hard refusal.
    """
    errors: list = []
    warnings: list = []

    kind = _extract_kind(section)
    if not kind:
        return errors, warnings

    if kind not in ALLOWED_KIND_VALUES:
        allowed = ", ".join(repr(v) for v in ALLOWED_KIND_VALUES)
        errors.append(
            f"unknown `kind:` value {kind!r}; allowed values: {allowed}"
        )
        return errors, warnings

    if kind == "spike":
        missing = [lbl for lbl in SPIKE_BODY_LABELS if lbl not in section]
        if missing:
            shown = ", ".join(missing)
            warnings.append(
                "spike slice missing body label(s): " + shown
            )

    return errors, warnings


# ---------------------------------------------------------------------------
# Contradiction detection
# ---------------------------------------------------------------------------

class Contradiction:
    def __init__(self, required: str, req_ac: int, forbidden: str, forbid_ac: int):
        self.required = required      # full required phrase
        self.forbidden = forbidden    # the forbidden substring
        self.req_ac = req_ac
        self.forbid_ac = forbid_ac

    def __repr__(self):
        return (
            f"Contradiction(required={self.required!r}, req_ac={self.req_ac}, "
            f"forbidden={self.forbidden!r}, forbid_ac={self.forbid_ac})"
        )


def check_slice(label: str, slice_text: str) -> tuple:
    """Return (contradictions: list[Contradiction], warnings: list[str]).

    A contradiction is found when:
      - AC #X says phrase P must appear verbatim
      - AC #Y (Y ≠ X) says substring S must NOT appear
      - S appears (case-insensitively) inside P

    Note: this function checks ACs for phrase contradictions only.
    Slice 029-01 added a separate `check_kind_and_body_shape` helper for
    `kind:` enum + spike body-shape validation; `lint()` calls both and
    merges the results. Existing callers of `check_slice` are unaffected.
    """
    ac_items = _parse_ac_items(slice_text)
    contradictions = []
    warnings = []

    if not ac_items:
        return contradictions, warnings

    # Collect per-AC required and forbidden phrases.
    required_by_ac = {}   # {ac_num: [phrase, ...]}
    forbidden_by_ac = {}  # {ac_num: [phrase, ...]}

    for ac_num, ac_text in ac_items:
        req = _extract_phrases_near(ac_text, _REQUIRED_MARKERS)
        forb = _extract_phrases_near(ac_text, _FORBIDDEN_MARKERS)
        if req:
            required_by_ac[ac_num] = req
        if forb:
            forbidden_by_ac[ac_num] = forb

    # Cross-check: required phrase in AC #X vs forbidden phrase in AC #Y (X≠Y).
    for req_ac, req_phrases in required_by_ac.items():
        for forb_ac, forb_phrases in forbidden_by_ac.items():
            if req_ac == forb_ac:
                continue
            for req_phrase in req_phrases:
                for forb_phrase in forb_phrases:
                    if forb_phrase.lower() in req_phrase.lower():
                        contradictions.append(
                            Contradiction(req_phrase, req_ac, forb_phrase, forb_ac)
                        )

    return contradictions, warnings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def render_report(results: list, spec_path: Path) -> tuple:
    """Return (report_text: str, exit_code: int).

    Each row in `results` is one of:
      - (slice_label, contradictions, warnings)            — legacy 3-tuple
      - (slice_label, contradictions, errors, warnings)    — slice 029-01 shape

    Slice 029-01 added a per-slice `errors` channel for `kind:` enum
    validation. Errors are hard failures (exit 1) — distinct from
    contradictions, which are also exit 1, and from warnings, which are
    informational unless --strict is set.
    """
    lines = [f"## Spec lint: {spec_path}", ""]
    any_contradiction = False
    any_error = False

    for row in results:
        if len(row) == 4:
            label, contradictions, errors, warnings = row
        else:
            # Legacy 3-tuple — fill missing errors.
            label, contradictions, warnings = row
            errors = []

        lines.append(f"### Slice {label}")
        lines.append("")
        if not contradictions and not errors and not warnings:
            lines.append("✓ No AC contradictions detected.")
        else:
            for c in contradictions:
                any_contradiction = True
                lines.append(
                    f"⚠  AC #{c.req_ac} × AC #{c.forbid_ac} contradiction:"
                )
                lines.append(f"   Required phrase  (AC #{c.req_ac}): \"{c.required}\"")
                lines.append(f"   Forbidden term   (AC #{c.forbid_ac}): \"{c.forbidden}\"")
                lines.append(
                    f"   \"{c.forbidden}\" appears inside the required phrase."
                )
            for e in errors:
                any_error = True
                lines.append(f"✗  {e}")
            for w in warnings:
                lines.append(f"⚐  {w}")
        lines.append("")

    exit_code = 1 if (any_contradiction or any_error) else 0
    return "\n".join(lines), exit_code


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spec_lint.py",
        description="Detect AC phrase contradictions in a jig spec.",
    )
    p.add_argument(
        "spec",
        nargs="?",
        default=None,
        help="path to spec.md (omit with --all to lint every spec)",
    )
    p.add_argument(
        "--slice",
        default=None,
        metavar="FRAGMENT",
        help="lint only the matching slice (case-insensitive substring)",
    )
    p.add_argument(
        "--all",
        dest="all_specs",
        action="store_true",
        help="lint every docs/specs/*/spec.md (the no-arg default)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 also on parse warnings",
    )
    return p


def _discover_specs(cwd: Path) -> list:
    """Return a sorted list of `docs/specs/*/spec.md` paths relative to cwd.

    A spec is `docs/specs/<NNN-slug>/spec.md`. Order is lexicographic on the
    spec-dir name so 001-... comes before 002-..., which is the natural
    reading order for the status board.
    """
    specs_root = cwd / "docs" / "specs"
    if not specs_root.is_dir():
        return []
    found = []
    for child in sorted(specs_root.iterdir()):
        candidate = child / "spec.md"
        if candidate.is_file():
            found.append(candidate)
    return found


def lint_all(specs: list, strict: bool = False) -> tuple:
    """Lint every spec in `specs`. Returns (report_text, exit_code).

    The exit code is the max of the per-spec codes: 0 if all green, 1 if any
    contradictions (or warnings under --strict), 2 if any spec failed to
    parse (file missing or no '## Slice' headings).
    """
    parts = []
    worst = 0
    for spec in specs:
        report, code = lint(spec, slice_fragment=None, strict=strict)
        parts.append(report.rstrip())
        if code > worst:
            worst = code
    summary = (
        f"\n## Summary\n\n"
        f"Linted {len(specs)} spec(s); "
        f"{'no contradictions found' if worst == 0 else f'contradictions found (exit {worst})'}.\n"
    )
    parts.append(summary)
    return "\n\n".join(parts), worst


def lint(spec_path: Path, slice_fragment: str = None, strict: bool = False) -> tuple:
    """Lint a spec file. Returns (report_text, exit_code)."""
    if not spec_path.is_file():
        return f"spec not found: {spec_path}\n", 2

    # Slice 018-02: prefer the common iterator (sees slice files too)
    # when available. Fall back to embedded-only scan otherwise.
    if _iter_slices_common is not None:
        slices = [(loc.label, loc.text[loc.start:loc.end])
                  for loc in _iter_slices_common(spec_path)]
    else:
        text = spec_path.read_text()
        slices = list(_iter_slices(text))

    if not slices:
        return f"no '## Slice ...' headings found in {spec_path}\n", 2

    if slice_fragment:
        needle = slice_fragment.lower()
        slices = [(lbl, sec) for lbl, sec in slices if needle in lbl.lower()]
        if not slices:
            return f"slice not found: '{slice_fragment}'\n", 2
        if len(slices) > 1:
            names = [lbl for lbl, _ in slices]
            return f"ambiguous slice fragment '{slice_fragment}' matches: {names}\n", 2

    results = []
    for label, section in slices:
        contradictions, warnings = check_slice(label, section)
        # Slice 029-01: also check `kind:` enum + spike body shape.
        kind_errors, kind_warnings = check_kind_and_body_shape(label, section)
        # Slice 111-02: soft-warn a `blocked_by:` on a non-actionable slice.
        blocked_warnings = check_blocked_annotation(label, section)
        # Merge the kind + blocked warnings into the per-slice warnings channel.
        all_warnings = warnings + kind_warnings + blocked_warnings
        results.append((label, contradictions, kind_errors, all_warnings))

    report, code = render_report(results, spec_path)

    if strict:
        has_warnings = any(w for row in results for w in row[-1])
        if has_warnings:
            code = 1

    return report, code


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    # Validate flag combinations.
    if ns.all_specs and ns.spec:
        sys.stderr.write(
            "spec_lint: --all is mutually exclusive with a positional spec path.\n"
        )
        return 2
    if ns.all_specs and ns.slice:
        sys.stderr.write(
            "spec_lint: --slice requires a positional spec path; cannot combine with --all.\n"
        )
        return 2

    # No-arg form is equivalent to --all.
    walk_all = ns.all_specs or ns.spec is None

    if walk_all:
        specs = _discover_specs(Path.cwd())
        if not specs:
            sys.stderr.write(
                "spec_lint: no docs/specs/*/spec.md found under cwd.\n"
            )
            return 2
        report, code = lint_all(specs, strict=ns.strict)
    else:
        report, code = lint(Path(ns.spec), slice_fragment=ns.slice, strict=ns.strict)

    sys.stdout.write(report)
    if not report.endswith("\n"):
        sys.stdout.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
