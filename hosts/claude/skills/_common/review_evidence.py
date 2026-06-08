"""Review-evidence verdict schema — the single source of truth shared by
`review.py` (writer) and `workflow.py transition` (gate).

Slice 045-02 (review-artifact-recorder). Contract: ADR-0014
(review-evidence model). Extracted to `_common/` per ADR-0014 §7 / ADR-0003
("two callers of the same helper → extract"): the writer records verdicts
here, and slice 045-03's transition gate imports `validate_evidence` to
enforce the §5 transition map.

What this module owns (ADR-0014):
  - §1 file layout: a verdict file lives at
    `docs/specs/NNN-slug/reviews/slice-NN-<pass>.md`. The `NN` is derived
    from the resolved slice file's name (`slice-NN-*.md`), NOT from the
    caller's fragment — `evidence_path` resolves the slice first.
  - §1/§3 vocabularies: `PASSES` and `VERDICTS`.
  - §5 transition map:
    `required_passes(stage, arch_review, code_health_review)`.
  - §2 schema: `parse_verdict_file(path)` checks the six required
    frontmatter fields and in-vocabulary `pass`/`verdict`.
  - §3 gate rule (uniform): an evidence file *clears* iff `verdict: pass`.
    `verdict_clears(value)` is the one-line predicate.
  - `validate_evidence(spec, slice, stage)` → list of human-readable
    diagnostics (empty = clears). This is what 045-03's gate calls.

Deferred (ADR-0014 Scope / docs/refinement-todo.md): **code-staleness**
detection — a `pass` artifact whose `reviewed_at` predates a later change
to the deliverable (stale-but-passing). This module does NOT compare
deliverable mtime/git-log against `reviewed_at`. The *superseded-only*
case (a `fail`/`needs-changes` not yet overwritten by a later `pass`) IS
enforced here — it reduces to `verdict != pass`, which `verdict_clears`
already rejects.
"""

from __future__ import annotations

from pathlib import Path

from _common.parsing import (
    FRONTMATTER_TRUTHY,
    SliceLookupError,
    frontmatter_flag_truthy,
    load_slice,
    parse_frontmatter,
)

# ADR-0014 §1: the review passes, one verdict file per (slice, pass).
# Slice 060-05 added the on-demand `code-health` pass (gated by a slice's
# `code_health_review: true` frontmatter flag, mirroring `arch`).
PASSES = ("compliance", "craft", "arch", "code-health", "reconciliation")

# ADR-0014 §3: allowed verdict values.
VERDICTS = ("pass", "fail", "needs-changes")

# ADR-0014 §2: frontmatter fields every verdict file must carry.
REQUIRED_FIELDS = (
    "slice",
    "pass",
    "verdict",
    "reviewer",
    "reviewed_at",
    "prompt_source",
)

# Command the diagnostics point at when evidence is missing/non-clearing
# (ADR-0014 Consequences: "the gate names the missing artifact and the
# command to produce it"). Kept as a constant so writer + gate agree.
RECORD_CMD = "review.py record-review"


class EvidenceError(RuntimeError):
    """User-facing evidence error. Callers (review.py / workflow.py) map
    this to their own CLI exit-2 convention, mirroring how review.py wraps
    SliceLookupError as ReviewError."""


class VerdictRecord:
    """Parsed result of one verdict file.

    Attributes:
        path: the file parsed.
        fields: frontmatter dict (may be partial/empty on malformed input).
        problems: list of human-readable diagnostics; empty iff the file
            is well-formed AND clears the gate.
        clears: True iff the file exists, parses, pass/verdict are
            in-vocabulary, and `verdict == pass` (ADR-0014 §3).
    """

    def __init__(self, path: Path, fields: dict, problems: list, clears: bool):
        self.path = path
        self.fields = fields
        self.problems = problems
        self.clears = clears


def _slice_number(spec_path, slice_fragment: str) -> tuple:
    """Resolve `slice_fragment` to its slice file and return
    ``(spec_dir, slice_no, label)``.

    `slice_no` is the `NN` parsed from the resolved slice file name
    (`slice-NN-*.md`) per ADR-0014 §1 — the evidence filename mirrors the
    slice filename, not the caller's fragment. Raises `EvidenceError`
    (wrapping `SliceLookupError`) on miss/ambiguity, and when the resolved
    location is an embedded `## Slice` section in spec.md (no slice file →
    no `NN` to mirror).
    """
    spec_path = Path(spec_path)
    try:
        loc = load_slice(spec_path, slice_fragment)
    except SliceLookupError as exc:
        raise EvidenceError(str(exc)) from exc

    name = loc.path.name
    if not name.startswith("slice-"):
        # Embedded section in spec.md — the evidence path convention
        # (slice-NN-<pass>.md) needs a sibling slice file to mirror.
        raise EvidenceError(
            f"slice '{slice_fragment}' resolved to an embedded section in "
            f"{name}, not a sibling slice-NN-*.md file; review evidence "
            f"requires the file-per-slice layout (spec 018)"
        )
    # `slice-NN-<rest>.md` → NN is the second hyphen-delimited token and must
    # be numeric (`.isdigit()` also rejects the empty token), so a
    # heading-matched but misnamed `slice-foo-bar.md` fails loudly here rather
    # than silently producing a malformed `reviews/slice-foo-<pass>.md` path.
    parts = name.split("-")
    if len(parts) < 3 or not parts[1].isdigit():
        raise EvidenceError(
            f"cannot derive slice number from file name {name!r}"
        )
    return loc.path.parent, parts[1], loc.label


def evidence_path(spec_path, slice_fragment: str, pass_name: str) -> Path:
    """Resolve the verdict-file path for a (slice, pass).

    Returns ``<spec_dir>/reviews/slice-NN-<pass>.md`` (ADR-0014 §1).
    Raises `EvidenceError` for an unknown pass name or an unresolvable
    slice fragment.
    """
    if pass_name not in PASSES:
        raise EvidenceError(
            f"unknown pass '{pass_name}'; expected one of "
            f"{', '.join(PASSES)}"
        )
    spec_dir, slice_no, _label = _slice_number(spec_path, slice_fragment)
    return spec_dir / "reviews" / f"slice-{slice_no}-{pass_name}.md"


def required_passes(stage: str, *, arch_review: bool,
                    code_health_review: bool = False) -> tuple:
    """Return the passes required to enter `stage` (ADR-0014 §5 map).

    - ``REVIEWED`` → ``compliance`` + ``craft`` (+ ``arch`` iff the slice
      declared ``arch_review: true``) (+ ``code-health`` iff the slice
      declared ``code_health_review: true`` — slice 060-05).
    - ``RECONCILED`` → ``reconciliation``.

    `arch_review` and `code_health_review` are honored only for the
    REVIEWED stage (both are REVIEWED-stage passes). `code_health_review`
    defaults False so every existing slice (no flag) is unaffected — the
    code-health pass is opt-in, gated like arch. Raises `EvidenceError`
    for an unknown stage.

    NOTE: the ``DONE`` re-validation (ADR-0014 §5) re-runs the REVIEWED +
    RECONCILED sets; that composition lives in the 045-03 gate, not here,
    so this stays a single-stage lookup.
    """
    if stage == "REVIEWED":
        passes = ["compliance", "craft"]
        if arch_review:
            passes.append("arch")
        if code_health_review:
            passes.append("code-health")
        return tuple(passes)
    if stage == "RECONCILED":
        return ("reconciliation",)
    raise EvidenceError(
        f"unknown transition stage '{stage}'; expected REVIEWED or RECONCILED"
    )


def verdict_clears(verdict: str) -> bool:
    """ADR-0014 §3 gate rule (uniform): an evidence file clears iff its
    verdict is exactly ``pass``. Any other in-vocabulary value
    (``fail``/``needs-changes``) — including a superseded-only verdict not
    yet overwritten by a later pass — does NOT clear, and neither does an
    out-of-vocabulary value."""
    return verdict == "pass"


def parse_verdict_file(path) -> VerdictRecord:
    """Read and validate one verdict file.

    Checks (ADR-0014 §2/§3):
      - file exists and is readable;
      - has a frontmatter block;
      - carries all six `REQUIRED_FIELDS`;
      - `pass` and `verdict` are in-vocabulary;
      - `verdict == pass` to clear.

    Returns a `VerdictRecord`. Never raises for content problems — every
    failure mode becomes a `problems` entry so callers can aggregate
    diagnostics across the whole evidence set. (An unreadable file is
    reported as a problem, not raised.)
    """
    path = Path(path)
    if not path.is_file():
        return VerdictRecord(
            path, {},
            [f"missing evidence file: {path}"],
            False,
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return VerdictRecord(
            path, {},
            [f"unreadable evidence file {path}: {exc}"],
            False,
        )

    fields, consumed = parse_frontmatter(text)
    problems: list = []
    if consumed == 0 or not fields:
        problems.append(
            f"{path.name}: missing or malformed frontmatter block "
            f"(need a leading `---` … `---` block with "
            f"{', '.join(REQUIRED_FIELDS)})"
        )
        # No fields to validate further.
        return VerdictRecord(path, fields, problems, False)

    for key in REQUIRED_FIELDS:
        val = fields.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            problems.append(f"{path.name}: missing required field '{key}'")

    pass_val = fields.get("pass")
    if pass_val is not None and pass_val not in PASSES:
        problems.append(
            f"{path.name}: unknown pass '{pass_val}'; expected one of "
            f"{', '.join(PASSES)}"
        )

    verdict_val = fields.get("verdict")
    if verdict_val is not None and verdict_val not in VERDICTS:
        problems.append(
            f"{path.name}: unknown verdict '{verdict_val}'; expected one "
            f"of {', '.join(VERDICTS)}"
        )

    clears = (
        not problems
        and verdict_val is not None
        and verdict_clears(verdict_val)
    )
    if not problems and not clears:
        # Well-formed but non-clearing (e.g. fail / needs-changes not yet
        # overwritten by a later pass — the superseded-only case, ADR §4).
        problems.append(
            f"{path.name}: verdict is '{verdict_val}', not 'pass' — this "
            f"pass does not clear the gate (re-run the review and "
            f"re-record a 'pass' once resolved)"
        )

    return VerdictRecord(path, fields, problems, clears)


# Slice 045-03 (must-do d): the arch-review truthy set is now owned by
# `_common.parsing.FRONTMATTER_TRUTHY` and shared with
# `workflow.slice_needs_arch_review` so the orchestrator that *spawns* the
# arch pass and this gate that *requires* its evidence cannot drift (the
# 045-02 reviewer's Medium finding). The module-level name is kept as an
# alias to that single source — pinned to be the SAME object by
# `ArchReviewTruthyUnificationTests`.
_ARCH_REVIEW_TRUTHY = FRONTMATTER_TRUTHY


def _arch_review_flag(spec_path, slice_fragment: str) -> bool:
    """Read the resolved slice's `arch_review:` frontmatter flag.

    Returns True iff the slice declares a truthy `arch_review` token
    (`true`/`yes`/`on`/`1`, case-insensitive — same set as
    `workflow.py:slice_needs_arch_review`, now via the shared
    `frontmatter_flag_truthy` predicate). Conservative: any miss (no
    frontmatter, field absent, unrecognized value) returns False. Raises
    `EvidenceError` only when the slice itself can't be resolved (the caller
    wants that surfaced as an invalid-target diagnostic).
    """
    spec_path = Path(spec_path)
    try:
        loc = load_slice(spec_path, slice_fragment)
    except SliceLookupError as exc:
        raise EvidenceError(str(exc)) from exc
    body = loc.text[loc.start:loc.end]
    fields, _ = parse_frontmatter(body)
    return frontmatter_flag_truthy(fields.get("arch_review", ""))


def _code_health_review_flag(spec_path, slice_fragment: str) -> bool:
    """Read the resolved slice's `code_health_review:` frontmatter flag
    (slice 060-05). Mirrors `_arch_review_flag` exactly.

    Returns True iff the slice declares a truthy `code_health_review`
    token (`true`/`yes`/`on`/`1`, case-insensitive — the shared
    `frontmatter_flag_truthy` predicate). Conservative: any miss (no
    frontmatter, field absent, unrecognized value) returns False, so
    every existing slice (no flag) stays unaffected — the code-health
    pass is opt-in. Raises `EvidenceError` only when the slice itself
    can't be resolved.
    """
    spec_path = Path(spec_path)
    try:
        loc = load_slice(spec_path, slice_fragment)
    except SliceLookupError as exc:
        raise EvidenceError(str(exc)) from exc
    body = loc.text[loc.start:loc.end]
    fields, _ = parse_frontmatter(body)
    return frontmatter_flag_truthy(fields.get("code_health_review", ""))


def validate_evidence(spec_path, slice_fragment: str, stage: str) -> list:
    """Validate the evidence set required to enter `stage` for one slice.

    Returns a list of human-readable diagnostics; an empty list means the
    required evidence clears (ADR-0014 §3/§5). This is the function the
    045-03 transition gate calls.

    Diagnostics are actionable (AC2): they name the offending pass, the
    problem (missing / malformed / unknown pass / unknown verdict /
    non-clearing verdict / invalid slice target), and the command to
    produce the artifact.

    Does NOT raise for an invalid slice target — that becomes the first
    diagnostic (so the gate can report it uniformly rather than crashing).
    """
    # Resolve the arch + code-health flags + slice first; an unresolvable
    # slice is a single actionable diagnostic, not an exception.
    try:
        arch = _arch_review_flag(spec_path, slice_fragment)
        code_health = _code_health_review_flag(spec_path, slice_fragment)
    except EvidenceError as exc:
        return [f"invalid slice target: {exc}"]

    try:
        needed = required_passes(stage, arch_review=arch,
                                 code_health_review=code_health)
    except EvidenceError as exc:
        return [str(exc)]

    diagnostics: list = []
    for pass_name in needed:
        try:
            path = evidence_path(spec_path, slice_fragment, pass_name)
        except EvidenceError as exc:
            # Slice already resolved above, so this only fires on an
            # internal inconsistency; surface it rather than swallow.
            diagnostics.append(str(exc))
            continue
        rec = parse_verdict_file(path)
        if not rec.clears:
            for problem in rec.problems:
                diagnostics.append(
                    f"[{pass_name}] {problem} "
                    f"(produce with: {RECORD_CMD} <spec> {slice_fragment} "
                    f"--pass {pass_name} --verdict pass ...)"
                )
    return diagnostics
