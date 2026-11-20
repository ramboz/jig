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
    `required_passes(stage, arch_review, code_health_review,
    frame_review)`. Slice 064-03 added the READY_FOR_REVIEW →
    `frame-critique` (iff `frame_review`) pre-implementation entry.
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
already rejects. Bug 039 narrowed the deferral: after a review
*back-edge* (which stamps `review_reopened_at`), a verdict not newer than the
stamp no longer clears — see `stale_after_reopen_problem`.
Selected static design evidence is the bounded exception: explicit raw
references and current source/build/delivery identities are revalidated,
without evaluating the UI or imposing general code freshness on other passes.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from _common.design_bindings import freshness_problem
from _common.parsing import (
    FRONTMATTER_TRUTHY,
    SliceLookupError,
    env_gate_enabled,
    frontmatter_flag_truthy,
    load_slice,
    parse_frontmatter,
)

# ADR-0014 §1: the review passes, one verdict file per (slice, pass).
# Slice 060-05 added the on-demand `code-health` pass (gated by a slice's
# `code_health_review: true` frontmatter flag, mirroring `arch`).
# Slice 064-03 added the on-demand `frame-critique` pass (gated by a slice's
# `frame_review: true` flag) — unlike the others it gates the
# READY_FOR_REVIEW (pre-implementation) stage, not REVIEWED (ADR-0020).
# Slice 071-01 added the on-demand, attest-only `design-review` pass (gated
# by a slice's `design_review: true` flag, mirroring `arch` at REVIEWED): a
# read-only reviewer ATTESTS an external non-deterministic eval's frozen
# verdict (servo's design-fidelity composite) — never re-deriving the score
# (the honesty boundary, ADR-0022).
# Spec 124-01 / ADR-0069 added the on-demand `owner-review` pass (gated by a
# slice's `owner_review: true` flag, at REVIEWED): the one pass whose author
# is a person. Its record carries the owner's quoted answer.
PASSES = ("compliance", "craft", "arch", "code-health", "reconciliation",
          "frame-critique", "design-review", "bug-review", "security",
          "owner-review")

# The passes that gate REVIEWED for a slice (always-on + flag-gated).
REVIEWED_STAGE_PASSES = ("compliance", "craft", "arch", "code-health",
                         "design-review", "owner-review")

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

# Slice 064-05 (ADR-0020 OQ2/OQ3): ADRs are NOT slices, so the ADR-side
# frame-critique evidence file is keyed on `adr` (the 4-digit number)
# instead of `slice`. Same six-field shape otherwise. The ADR gate lives
# at `adr.py accept`; this is the only place the field set diverges.
ADR_REQUIRED_FIELDS = (
    "adr",
    "pass",
    "verdict",
    "reviewer",
    "reviewed_at",
    "prompt_source",
)

# Spec 058-04: bug records are not slices, so bug-review evidence is keyed
# on `bug` and stored beside docs/bugs/ under docs/bugs/reviews/.
BUG_REQUIRED_FIELDS = (
    "bug",
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

# Bug 039: a review back-edge stamps this frontmatter field on the
# record/slice (sites: `bug.py` `_BUG_REOPEN_TARGETS`, `workflow.py`
# `_REVIEW_STATES`). While it is set, a verdict clears only if its `reviewed_at`
# is STRICTLY later — the previous round's passes judged code that has since
# changed. Event-keyed, so it needs no deliverable mtime/git inspection (the
# general code-staleness gate stays deferred, ADR-0014 Scope).
REOPENED_FIELD = "review_reopened_at"


def now_iso8601() -> str:
    """UTC timestamp, second precision, trailing `Z` — the `reviewed_at`
    shape `review.py record-review` writes, so the two compare directly."""
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _parse_iso8601(value) -> "datetime.datetime | None":
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def stale_after_reopen_problem(verdict_fields: dict, reopened_at) -> str:
    """Return a problem string when a review back-edge (`reopened_at`) makes
    this verdict stale, else "". No reopen stamp → never stale. A malformed
    stamp or `reviewed_at` fails closed (it cannot be shown to be newer)."""
    if not str(reopened_at or "").strip():
        return ""
    reopened = _parse_iso8601(reopened_at)
    if reopened is None:
        return (f"malformed {REOPENED_FIELD}: {reopened_at!r} "
                "(expected ISO-8601, e.g. 2026-07-01T00:00:00Z)")
    reviewed_raw = verdict_fields.get("reviewed_at", "")
    reviewed = _parse_iso8601(reviewed_raw)
    if reviewed is None or reviewed <= reopened:
        return (f"verdict reviewed_at {reviewed_raw or '(empty)'} is not newer "
                f"than {REOPENED_FIELD} {reopened_at} — the review was "
                "reopened after this verdict; re-run the pass and re-record it")
    return ""

def evidence_gate_enabled() -> bool:
    """The review-evidence gate is enabled unless `JIG_REVIEW_EVIDENCE_GATE`
    is set to one of the falsey tokens (`_common.parsing.ENV_FALSEY`,
    case-insensitive). The gate is ON by default; this is the documented
    bypass for a deliberate actor / automation. Per ADR-0011 (cited by
    ADR-0014 §6), an in-process gate sits inside the agent's trust boundary —
    a *deliberateness* signal, not human-only enforcement — so an env escape
    hatch is consistent (cf. `JIG_CONVENTIONS_APPROVED`).

    The falsey vocabulary + this opt-out logic live in `_common.parsing`
    (`ENV_FALSEY` / `env_gate_enabled`) so every jig bypass gate reads one
    source and cannot drift — the load-bearing-consistency case ADR-0002 calls
    out. (`workflow.py` keeps `_evidence_gate_enabled` as an alias; the
    ADR-side accept gate in `adr.py` reads the same function.)"""
    return env_gate_enabled("JIG_REVIEW_EVIDENCE_GATE")


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
        well_formed: True iff the file exists, parses, carries every
            required field, and pass/verdict are in-vocabulary — whatever
            the verdict (spec 122-01 reads escalations only from these).
    """

    def __init__(self, path: Path, fields: dict, problems: list, clears: bool,
                 well_formed: bool = False):
        self.path = path
        self.fields = fields
        self.problems = problems
        self.clears = clears
        self.well_formed = well_formed


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
                    code_health_review: bool = False,
                    frame_review: bool = False,
                    design_review: bool = False,
                    owner_review: bool = False) -> tuple:
    """Return the passes required to enter `stage` (ADR-0014 §5 map).

    - ``READY_FOR_REVIEW`` → ``frame-critique`` iff the slice/spec
      declared ``frame_review: true`` (slice 064-03 / ADR-0020), else
      empty. This is the only PRE-implementation gate: the adversarial
      frame-critique runs before any code exists.
    - ``REVIEWED`` → ``compliance`` + ``craft`` (+ ``arch`` iff the slice
      declared ``arch_review: true``) (+ ``code-health`` iff the slice
      declared ``code_health_review: true`` — slice 060-05) (+
      ``design-review`` iff the slice declared ``design_review: true`` —
      slice 071-01) (+ ``owner-review`` iff the slice declared
      ``owner_review: true`` — spec 124-01).
    - ``RECONCILED`` → ``reconciliation``.

    `arch_review` / `code_health_review` / `design_review` are honored
    only for REVIEWED, `frame_review` only for READY_FOR_REVIEW (each is a
    stage-specific pass). All four flag kwargs default False so every
    existing slice (no flag) is unaffected — the frame-critique, arch,
    code-health, and design-review passes are all opt-in gates. An
    unflagged READY_FOR_REVIEW yields an EMPTY tuple → no gating (existing
    specs transition freely). Raises `EvidenceError` for an unknown stage.

    NOTE: the ``DONE`` re-validation (ADR-0014 §5) re-runs the REVIEWED +
    RECONCILED sets; that composition lives in the 045-03 gate, not here,
    so this stays a single-stage lookup. frame-critique is a ONE-TIME
    pre-implementation gate and is deliberately NOT re-validated at DONE.
    """
    if stage == "READY_FOR_REVIEW":
        return ("frame-critique",) if frame_review else ()
    if stage == "REVIEWED":
        passes = ["compliance", "craft"]
        if arch_review:
            passes.append("arch")
        if code_health_review:
            passes.append("code-health")
        if design_review:
            passes.append("design-review")
        if owner_review:
            passes.append("owner-review")
        return tuple(passes)
    if stage == "RECONCILED":
        return ("reconciliation",)
    raise EvidenceError(
        f"unknown transition stage '{stage}'; expected READY_FOR_REVIEW, "
        f"REVIEWED or RECONCILED"
    )


def required_bug_passes(stage: str, *, security_surface: bool = False) -> tuple:
    """Return the review passes required to enter a bug lifecycle stage.

    Spec 058-04 gates ``REVIEWED`` on a bug-tailored review pass plus the
    same craft pass used for slices. Bugs that declare ``security_surface:
    true`` also require the security pass. Other stages have no review
    evidence gate.
    """
    if stage == "REVIEWED":
        passes = ["bug-review", "craft"]
        if security_surface:
            passes.append("security")
        return tuple(passes)
    return ()


def verdict_clears(verdict: str) -> bool:
    """ADR-0014 §3 gate rule (uniform): an evidence file clears iff its
    verdict is exactly ``pass``. Any other in-vocabulary value
    (``fail``/``needs-changes``) — including a superseded-only verdict not
    yet overwritten by a later pass — does NOT clear, and neither does an
    out-of-vocabulary value.

    NOTE: `substrate:` (spec 096-05) is NOT consulted here — the gate stays a
    one-line predicate on `verdict:` alone (ADR-0014 §3 unchanged); the substrate
    is recorded + surfaced, never gated on."""
    return verdict == "pass"


# The closed `substrate:` vocabulary (spec 096-05 / ADR-0040 D3). Only `shown`
# is anomaly-eligible; the two *aggregated* signals for kill-criterion-1 are
# `not-shown` (the defect) and `non-interactive` (declared no-orchestrator).
# NOTE: `n/a` is a documented *conceptual* member — it is NEVER written to an
# artifact; it is represented as the substrate field being ABSENT (an out-of-
# scope pass, or a pre-096 artifact). Listed for vocabulary completeness.
SUBSTRATE_VALUES = ("config", "shown", "not-shown", "non-interactive", "n/a")


def substrate_anomaly(fields: dict) -> list:
    """Return the DECLINED high-confidence candidate names for a verdict record
    (spec 096-05 AC3) — the calibrated anomaly. Non-empty ⇒ "a richer skill was
    shown and not applied". Empty ⇒ no anomaly.

    Fires ONLY on `substrate: shown` (config / non-interactive / not-shown / n/a
    / absent → never). Calibrated to the **high-confidence** tier of the shown
    set (never the speculative tier or the raw nomination list, so a legitimate
    `none` while a briefing skill sat in speculative does not trip it). The
    `shown`-but-`applied_skill: unknown` state (no pick recorded — the cheapest
    defection) makes every high-confidence candidate count as declined.

    Backward-compatible + defensive: a record with no `substrate` / no
    `shown_candidates` (pre-096-05, hand-written, or malformed) yields `[]`.
    Never raises."""
    try:
        if (fields or {}).get("substrate") != "shown":
            return []
        shown = fields.get("shown_candidates") or []
        if isinstance(shown, str):  # tolerate a scalar / flow-parse miss
            shown = [shown] if shown else []
        high = []
        for entry in shown:
            name, _, tier = str(entry).partition(":")
            if tier == "high-confidence" and name:
                high.append(name)
        applied = fields.get("applied_skill")
        if applied == "unknown":
            return high  # shown, no pick recorded → all high-confidence declined
        return [n for n in high if n != applied]
    except (AttributeError, TypeError, ValueError):
        return []


def parse_verdict_file(path, required_fields=REQUIRED_FIELDS) -> VerdictRecord:
    """Read and validate one verdict file.

    Checks (ADR-0014 §2/§3):
      - file exists and is readable;
      - has a frontmatter block;
      - carries all `required_fields`;
      - `pass` and `verdict` are in-vocabulary;
      - `verdict == pass` to clear.

    `required_fields` defaults to the slice-evidence `REQUIRED_FIELDS`
    (six fields keyed on `slice`) so existing callers are unaffected.
    The ADR-side gate (slice 064-05) passes `ADR_REQUIRED_FIELDS` (keyed
    on `adr` instead of `slice`).

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
            f"{', '.join(required_fields)})"
        )
        # No fields to validate further.
        return VerdictRecord(path, fields, problems, False)

    for key in required_fields:
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

    well_formed = not problems and verdict_val is not None
    clears = (well_formed and verdict_val is not None
              and verdict_clears(verdict_val))
    if well_formed and not clears:
        # Well-formed but non-clearing (e.g. fail / needs-changes not yet
        # overwritten by a later pass — the superseded-only case, ADR §4).
        problems.append(
            f"{path.name}: verdict is '{verdict_val}', not 'pass' — this "
            f"pass does not clear the gate (re-run the review and "
            f"re-record a 'pass' once resolved)"
        )

    return VerdictRecord(path, fields, problems, clears,
                         well_formed=well_formed)


# ---------------------------------------------------------------------------
# Spec 122-01: escalations — decisions only a person can make.
#
# An arch reviewer reports a decision the implementer must not make (a
# duplicated path, effort past plan, a slice tied to no goal line, a
# hard-to-reverse choice) as a `[blocker]` SPECIFIC ISSUES entry whose
# description starts with `ESCALATE:`. Such a record still blocks (it is not
# `pass`); these helpers let `record-review` and the gate say "a person
# decides" instead of "re-run the review". The orchestrator then parks the
# decision with `memory.py add-inbox` and marks the slice `blocked_by:`.
# ---------------------------------------------------------------------------

# An envelope section heading: `SPECIFIC ISSUES:` (the reviewer envelope),
# `## SPECIFIC ISSUES` (ADR-0014 §2's recorded-body example), a bold
# `**SPECIFIC ISSUES:**`, or an annotated `SPECIFIC ISSUES (round 2):` (seen
# in recorded bodies). `VERDICT: fail` and `REASONING: …` may carry content
# on the same line.
_ENVELOPE_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?\**\s*"
    r"(VERDICT|REASONING|SPECIFIC ISSUES|RECONCILIATION NOTES)"
    r"\s*(?:\([^)\n]*\))?\s*\**\s*(?::.*)?$"
)
# A tagged entry: `- [blocker][spec] <description>`.
_TAGGED_ENTRY_RE = re.compile(r"^\s*[-*]\s+((?:\[[^\]\n]*\]\s*)+)(.*)$")
# The description starts with `ESCALATE:`, directly or after an anchor (which
# may be empty) and a ` — ` / ` – ` / ` - ` separator. The anchor may not
# itself contain a separator, so a later "… — then ESCALATE:" does not count.
# The token is matched case-insensitively and may be bold (`**ESCALATE:**`):
# a missed escalation would hand a person's decision back to the fix loop.
_ESCALATE_DESC_RE = re.compile(
    r"^(?:(?:(?!\s[—–-]\s).)*?\s*[—–-]\s+)?"
    r"\**(?i:escalate)\**:\**"
    r"\s*(?P<decision>.*)$"
)


def escalations(text: str) -> list:
    """Return the decision text of each escalated entry in a verdict body.

    An entry counts when it sits under `SPECIFIC ISSUES`, carries a
    `[blocker]` tag, and its description starts with `ESCALATE:` (see
    `_ESCALATE_DESC_RE`). Indented continuation lines are joined onto their
    entry. Code-fence lines are skipped and never start or end a section:
    a fence can wrap the envelope or a snippet inside an entry, and telling
    them apart risks dropping an escalation. Erring this way can only read
    an extra escalation, never miss one. Returns `[]` when there is no
    `SPECIFIC ISSUES` section. Never raises.
    """
    found: list = []
    in_issues = False
    entry = None  # (tags, description) of the entry being read

    def flush():
        nonlocal entry
        if entry is not None:
            tags, desc = entry
            if "blocker" in tags:
                m = _ESCALATE_DESC_RE.match(desc.strip())
                if m:
                    found.append(m.group("decision").strip()
                                 or "(decision text missing)")
        entry = None

    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            continue  # neutral: see the docstring
        heading = _ENVELOPE_HEADING_RE.match(line)
        if heading:
            flush()
            in_issues = heading.group(1) == "SPECIFIC ISSUES"
            continue
        if not in_issues:
            continue
        tagged = _TAGGED_ENTRY_RE.match(line)
        if tagged:
            flush()
            tags = {t.strip().lower()
                    for t in re.findall(r"\[([^\]\n]*)\]", tagged.group(1))}
            entry = (tags, tagged.group(2))
        elif entry is not None and line[:1].isspace() and line.strip():
            entry = (entry[0], f"{entry[1]} {line.strip()}")
        else:
            flush()
    flush()
    return found


def escalation_guidance(decisions: list, record) -> str:
    """The shared "a person decides" message for `decisions` escalated in
    the arch record at `record` (used by the gate and by `record-review`)."""
    listed = "; ".join(f"({i}) {d}" for i, d in enumerate(decisions, 1))
    return (
        f"escalated — {len(decisions)} decision(s) a person must decide: "
        f"{listed}. Do not fix these or re-run the arch pass. "
        f"Park each one in the project inbox with its options and the "
        f"record path {record} (`memory.py add-inbox`), set `blocked_by:` "
        f"and a `**Blocked:**` line on the slice, and stop work on it. "
        f"Re-run the arch pass once a person has decided (spec-workflow "
        f"SKILL.md, \"Escalated arch finding\")."
    )


def escalated_decisions(rec: VerdictRecord) -> list:
    """Escalations in a well-formed, non-`pass` verdict record; `[]` for a
    clearing, missing or malformed record (those keep their own
    diagnostics). Read for the diagnostic only — never for clearing, which
    stays `verdict: pass` alone (ADR-0014 §3)."""
    if rec.clears or not rec.well_formed:
        return []
    try:
        return escalations(rec.path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return []


# Slice 045-03 (must-do d): the arch-review truthy set is now owned by
# `_common.parsing.FRONTMATTER_TRUTHY` and shared with
# `workflow.slice_needs_arch_review` so the orchestrator that *spawns* the
# arch pass and this gate that *requires* its evidence cannot drift (the
# 045-02 reviewer's Medium finding). The module-level name is kept as an
# alias to that single source — pinned to be the SAME object by
# `ArchReviewTruthyUnificationTests`.
_ARCH_REVIEW_TRUTHY = FRONTMATTER_TRUTHY


def _review_flag(spec_path, slice_fragment: str, field: str) -> bool:
    """Read a resolved slice's `<field>:` frontmatter flag.

    Shared body for the `_arch_review_flag` / `_code_health_review_flag` /
    `_frame_review_flag` / `_design_review_flag` family (parametrized per
    the refinement-todo "parametrize the four `_*_review_flag` helpers"
    entry — folded into spec 078 since it touches this module's gate logic
    anyway). Returns True iff the slice declares a truthy token
    (`true`/`yes`/`on`/`1`, case-insensitive — the shared
    `frontmatter_flag_truthy` predicate). Conservative: any miss (no
    frontmatter, field absent, unrecognized value) returns False, so every
    existing slice (no flag) stays unaffected — each of these passes is
    opt-in. Raises `EvidenceError` only when the slice itself can't be
    resolved (the caller wants that surfaced as an invalid-target
    diagnostic).
    """
    return frontmatter_flag_truthy(_slice_field(spec_path, slice_fragment, field))


def _slice_field(spec_path, slice_fragment: str, field: str) -> str:
    """Raw `<field>:` frontmatter value of a resolved slice ("" when absent).
    Raises `EvidenceError` when the slice itself can't be resolved."""
    try:
        loc = load_slice(Path(spec_path), slice_fragment)
    except SliceLookupError as exc:
        raise EvidenceError(str(exc)) from exc
    fields, _ = parse_frontmatter(loc.text[loc.start:loc.end])
    return str(fields.get(field, "") or "").strip()


def _arch_review_flag(spec_path, slice_fragment: str) -> bool:
    """`arch_review:` flag — same set as `workflow.py:slice_needs_arch_review`."""
    return _review_flag(spec_path, slice_fragment, "arch_review")


def _code_health_review_flag(spec_path, slice_fragment: str) -> bool:
    """`code_health_review:` flag (slice 060-05)."""
    return _review_flag(spec_path, slice_fragment, "code_health_review")


def _frame_review_flag(spec_path, slice_fragment: str) -> bool:
    """`frame_review:` flag (slice 064-03 / ADR-0020)."""
    return _review_flag(spec_path, slice_fragment, "frame_review")


def _design_review_flag(spec_path, slice_fragment: str) -> bool:
    """`design_review:` flag (slice 071-01), same source as
    `workflow.py:slice_needs_design_review` — the no-drift invariant: the
    gate reads the flag itself, the same flag the orchestrator reads to
    spawn the pass."""
    return _review_flag(spec_path, slice_fragment, "design_review")


def _owner_review_flag(spec_path, slice_fragment: str) -> bool:
    """`owner_review:` flag (spec 124-01), same source as
    `workflow.py:slice_needs_owner_review`."""
    return _review_flag(spec_path, slice_fragment, "owner_review")


# ---------------------------------------------------------------------------
# Spec 124-01 / ADR-0069: the owner-review pass — a verdict whose author is
# a person. The record body carries what the owner tried, on what surface,
# and their quoted answer. The file is agent-writable, so this is a
# deliberateness gate (ADR-0011), not proof that a person tried anything.
# ---------------------------------------------------------------------------

OWNER_REVIEW_PASS = "owner-review"

# (label, what it holds, regex that finds a non-empty value). TRIED/SURFACE
# hold their value on the label's line; the quote is a blockquote under it.
_OWNER_REVIEW_PARTS = (
    ("TRIED:", "what the owner tried",
     re.compile(r"(?m)^TRIED:[ \t]*\S")),
    ("SURFACE:", "the device or surface they used",
     re.compile(r"(?m)^SURFACE:[ \t]*\S")),
    ("OWNER SAID:", "the owner's answer, quoted as a `> ` blockquote",
     re.compile(r"(?m)^OWNER SAID:[ \t]*\n(?:[ \t]*\n)*>[ \t]*\S")),
)


def owner_review_problem(body: str) -> str:
    """Return a problem string naming each part an owner-review body lacks,
    or "" when all three are present and non-empty. Shared by the writer
    (`record-review`) and the gate."""
    missing = [f"`{label}` ({what})"
               for label, what, pattern in _OWNER_REVIEW_PARTS
               if not pattern.search(body or "")]
    if not missing:
        return ""
    return ("owner-review record is missing " + ", ".join(missing)
            + " — it must carry the owner's own answer")


def owner_review_body(tried: str, surface: str, quote: str,
                      verdict: str, notes: str = "") -> str:
    """Compose the owner-review record body from the owner's answer."""
    def one_line(value) -> str:
        return " ".join(str(value).split())

    quoted = "\n".join(f"> {line.strip()}" if line.strip() else ">"
                       for line in str(quote).strip().splitlines())
    body = (f"VERDICT: {verdict}\n\n"
            f"TRIED: {one_line(tried)}\n\n"
            f"SURFACE: {one_line(surface)}\n\n"
            f"OWNER SAID:\n{quoted}\n")
    if notes.strip():
        body += f"\nNOTES:\n{notes.strip()}\n"
    return body


def owner_ask_hint(slice_fragment: str) -> str:
    """How to produce an owner-review record: ask, never just record."""
    return (f"ask the owner first: `review.py owner-review <spec> "
            f"{slice_fragment}` prints what to ask; record only their "
            f"quoted answer, never an inferred one")


def owner_rejection_guidance(slice_fragment: str) -> str:
    """The shared notice for a non-`pass` owner verdict (gate + writer)."""
    return (
        "the owner asked for changes. The slice stays IN_PROGRESS: do not "
        "move it to REVIEWED and do not start reconciliation (no deviation "
        "log, sweep or decision records yet). Make the changes, re-run the "
        "automated review passes on the changed deliverable, then ask the "
        f"owner again (`review.py owner-review <spec> {slice_fragment}`) "
        "and record their new answer."
    )


def design_freshness_problem(spec_path, slice_fragment: str, body: str) -> str:
    """Shared writer/reuse check for an explicitly selected static contract."""
    try:
        loc = load_slice(Path(spec_path), slice_fragment)
    except SliceLookupError as exc:
        raise EvidenceError(str(exc)) from exc
    return freshness_problem(loc.text[loc.start:loc.end], body)


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
    # Resolve the arch + code-health + frame + design flags + slice first;
    # an unresolvable slice is a single actionable diagnostic, not an
    # exception. Reading the flags HERE (rather than in the caller) keeps
    # the spawner and the gate from drifting — the same per-stage flag
    # determines both what runs and what the gate requires.
    try:
        arch = _arch_review_flag(spec_path, slice_fragment)
        code_health = _code_health_review_flag(spec_path, slice_fragment)
        frame = _frame_review_flag(spec_path, slice_fragment)
        design = _design_review_flag(spec_path, slice_fragment)
        owner = _owner_review_flag(spec_path, slice_fragment)
    except EvidenceError as exc:
        return [f"invalid slice target: {exc}"]

    try:
        needed = required_passes(stage, arch_review=arch,
                                 code_health_review=code_health,
                                 frame_review=frame,
                                 design_review=design,
                                 owner_review=owner)
    except EvidenceError as exc:
        return [str(exc)]

    reopened_at = _slice_field(spec_path, slice_fragment, REOPENED_FIELD)
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
        if pass_name == "arch":
            # Spec 122-01: an escalated arch record still blocks, but the
            # next step is a person's decision, not a re-run.
            decisions = escalated_decisions(rec)
            if decisions:
                diagnostics.append(
                    f"[arch] {path.name}: "
                    f"{escalation_guidance(decisions, path)}"
                )
                continue
        if (pass_name == OWNER_REVIEW_PASS and rec.well_formed
                and not rec.clears):
            # Spec 124-01: an owner rejection is not "re-record a pass".
            diagnostics.append(
                f"[{pass_name}] {path.name}: "
                f"{owner_rejection_guidance(slice_fragment)}")
            continue
        problems = list(rec.problems) if not rec.clears else []
        if rec.clears and stage != "READY_FOR_REVIEW":
            # Bug 039: frame-critique (READY_FOR_REVIEW) is a one-time
            # pre-implementation pass a back-edge does not invalidate.
            stale = stale_after_reopen_problem(rec.fields, reopened_at)
            if stale:
                problems.append(stale)
            if pass_name == "design-review":
                try:
                    body = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    problems.append("design-freshness: inaccessible attestation; obtain "
                                    "fresh producer evidence and independent attestation")
                else:
                    freshness = design_freshness_problem(spec_path, slice_fragment, body)
                    if freshness:
                        problems.append(freshness)
            if pass_name == OWNER_REVIEW_PASS:
                try:
                    incomplete = owner_review_problem(
                        path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError):
                    incomplete = "owner-review record is unreadable"
                if incomplete:
                    problems.append(incomplete)
        for problem in problems:
            if pass_name == OWNER_REVIEW_PASS:
                # Never hint "record a pass": the verdict is the owner's.
                hint = owner_ask_hint(slice_fragment)
            else:
                hint = (f"produce with: {RECORD_CMD} <spec> {slice_fragment} "
                        f"--pass {pass_name} --verdict pass ...")
            diagnostics.append(f"[{pass_name}] {problem} ({hint})")
    return diagnostics


# ---------------------------------------------------------------------------
# ADR-side evidence (slice 064-05 / ADR-0020 OQ2/OQ3).
#
# ADRs are NOT slices, so the `reviews/slice-NN-<pass>.md` path under a
# spec dir doesn't apply. The ADR-side frame-critique verdict lives under
# `docs/decisions/reviews/adr-NNNN-<pass>.md`, mirroring the slice layout
# one level up — a `reviews/` subdir beside the artifacts it judges. The
# gate is enforced at `adr.py accept` (the ADR's pre-commitment moment),
# not at a workflow transition.
# ---------------------------------------------------------------------------


def adr_evidence_path(decisions_dir, adr_num, pass_name: str) -> Path:
    """Resolve the ADR verdict-file path for an (adr, pass).

    Returns ``<decisions_dir>/reviews/adr-NNNN-<pass>.md`` with the ADR
    number zero-padded to 4 digits (mirroring adr.py's `adr-NNNN-` file
    convention). Raises `EvidenceError` for an unknown pass name.
    """
    if pass_name not in PASSES:
        raise EvidenceError(
            f"unknown pass '{pass_name}'; expected one of "
            f"{', '.join(PASSES)}"
        )
    num = f"{int(adr_num):04d}"
    return Path(decisions_dir) / "reviews" / f"adr-{num}-{pass_name}.md"


def validate_adr_evidence(decisions_dir, adr_num, pass_name: str) -> list:
    """Validate the ADR-side verdict file for an (adr, pass).

    Returns a list of human-readable diagnostics; an empty list means the
    verdict clears (exists, well-formed against `ADR_REQUIRED_FIELDS`, and
    `verdict: pass`). Mirrors `validate_evidence`'s diagnostic style and
    names the missing artifact + the command to produce it (ADR-0014
    Consequences). The ADR gate (`adr.py accept`) calls this.
    """
    num = f"{int(adr_num):04d}"
    try:
        path = adr_evidence_path(decisions_dir, adr_num, pass_name)
    except EvidenceError as exc:
        return [str(exc)]
    rec = parse_verdict_file(path, required_fields=ADR_REQUIRED_FIELDS)
    diagnostics: list = []
    if not rec.clears:
        for problem in rec.problems:
            diagnostics.append(
                f"[{pass_name}] {problem} "
                f"(produce with: {RECORD_CMD} --adr {num} "
                f"--pass {pass_name} --verdict pass ...)"
            )
    return diagnostics


# ---------------------------------------------------------------------------
# Bug-side evidence (spec 058-04).
#
# Bug records live in docs/bugs/NNN-slug.md and do not have a spec/slice
# target. Their review evidence mirrors the slice/ADR shape but lives at
# docs/bugs/reviews/bug-NNN-<pass>.md and is keyed by `bug`.
# ---------------------------------------------------------------------------


def _bug_number_from_path(bug_path: Path) -> str:
    match = re.match(r"^(\d{3})-.+\.md$", Path(bug_path).name)
    if not match:
        raise EvidenceError(
            f"cannot derive bug number from file name {Path(bug_path).name!r}; "
            "expected NNN-slug.md"
        )
    return match.group(1)


def bug_evidence_path(bug_path, pass_name: str) -> Path:
    """Resolve the verdict-file path for a (bug, pass).

    Returns ``<docs/bugs>/reviews/bug-NNN-<pass>.md``. Raises
    `EvidenceError` for an unknown pass or malformed bug filename.
    """
    if pass_name not in PASSES:
        raise EvidenceError(
            f"unknown pass '{pass_name}'; expected one of "
            f"{', '.join(PASSES)}"
        )
    bug_path = Path(bug_path)
    bug_num = _bug_number_from_path(bug_path)
    return bug_path.parent / "reviews" / f"bug-{bug_num}-{pass_name}.md"


def validate_bug_evidence(bug_path, stage: str) -> list:
    """Validate the evidence set required to enter a bug lifecycle stage.

    The validator parses ``security_surface`` through the shared
    `_common.parsing.frontmatter_flag_truthy` / `FRONTMATTER_TRUTHY`
    predicate so bug orchestration and evidence gating cannot drift.
    """
    if not evidence_gate_enabled():
        return []
    bug_path = Path(bug_path)
    try:
        text = bug_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"invalid bug target: cannot read {bug_path}: {exc}"]
    fields, _ = parse_frontmatter(text)
    security_surface = frontmatter_flag_truthy(fields.get("security_surface", ""))
    needed = required_bug_passes(stage, security_surface=security_surface)
    diagnostics: list = []
    try:
        bug_num = _bug_number_from_path(bug_path)
    except EvidenceError as exc:
        return [f"invalid bug target: {exc}"]
    for pass_name in needed:
        try:
            path = bug_evidence_path(bug_path, pass_name)
        except EvidenceError as exc:
            diagnostics.append(str(exc))
            continue
        rec = parse_verdict_file(path, required_fields=BUG_REQUIRED_FIELDS)
        problems = list(rec.problems) if not rec.clears else []
        if rec.clears:
            stale = stale_after_reopen_problem(
                rec.fields, fields.get(REOPENED_FIELD, ""))
            if stale:
                problems.append(stale)
        for problem in problems:
            diagnostics.append(
                f"[{pass_name}] {problem} "
                f"(produce with: {RECORD_CMD} --bug {bug_num} "
                f"--pass {pass_name} --verdict pass ...)"
            )
    return diagnostics
