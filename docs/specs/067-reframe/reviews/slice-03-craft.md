---
slice: 067-03 — The noticing nudge (standing practice)
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T17:28:01Z
prompt_source: review.py craft docs/specs/067-reframe/spec.md 067-03 <deliverables>
---

VERDICT: pass

REASONING:
The slice ships exactly what 067-03 specifies: a soft marker-delimited reframe-practice block
in jig's docs/workflow.md (AC1), a writer called by both scaffold() and copy_machinery() so
downstream inherits it (AC2), one-line /jig:reframe cross-refs in spec-workflow + adr-workflow
SKILL.md (AC3), and no new hook (AC4). The ADR-0002 rule-of-three extraction is clean and
behavior-preserving: _upsert_marked_block is a pure (existing, begin, end, block) -> str
transform with file-I/O + the file-absent create branch left to each caller; all three writers
delegate with identical idempotent replace/append semantics. Tests are structural but
meaningful (idempotency, non-clobbering append, both call sites, extracted-helper invariant).

SPECIFIC ISSUES:
- [strength] _upsert_marked_block extraction is textbook rule-of-three: pure transform,
  centralized separator logic, docstring naming all 3 prior inline copies, per-file create
  branch left to callers; the three writers collapsed to identical 4-line merge tails.
- [strength] Tests assert the refactor invariant directly (3rd caller) + both call sites +
  idempotency + non-clobbering append — extraction and dual-path wiring are guarded.
- [strength] Correctly leaves the practice OUT of the static template and injects via the
  runtime managed-block writer (065-04 forward-only path), so already-scaffolded projects pick
  it up on next copy-machinery.
- [nit] _upsert_marked_block "begin without matching end" fall-through appends a fresh block but
  leaves the orphaned begin marker; docstring acknowledges the malformed-input choice, but it is
  untested — a one-line test would lock the behavior in.
- [nit] duplicated "# Workflow\n\n" create-branch header across the self-defining + reframe
  ensure functions; a shared _ensure_workflow_managed_block wrapper would finish the DRY-up.
  Reasonable to defer.

RECONCILIATION NOTES:
- Both nits are log-not-block. Fold the orphaned-marker test in; defer the wrapper DRY-up.
- AC2 "scaffolded workflow template" realized as a runtime managed block (065-04 precedent) —
  note in the deviation log.
