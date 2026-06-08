---
slice: 02 — grounding-requirement
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-08T04:24:49Z
prompt_source: review.py implementation docs/specs/064-spec-frame-hardening/spec.md grounding-requirement <6 deliverables>
---

VERDICT: pass

REASONING:
All 3 ACs met. AC1: both templates carry a risk-gated `## Assumptions` (ADR template also `## Kill criteria`) with explicit "omit/None, don't pad boilerplate" guidance; the spec stub in `_render_stub_spec` gained an `## Assumptions` block (Overview→Assumptions→Decomposition) and the existing stub test was extended to assert presence + placement. AC2: both `agents/architect.md` and `skills/spec-workflow/SKILL.md` carry the probe-first / mark-the-rest / never-assert contract as prose, framed as making the existing "Current state (verified …)" discipline mandatory+derived (064-01 emphasis), not net-new. AC3: ADR-0020 (`## Assumptions` A1 RESOLVED-via-probe, A2–A4 marked Unverified, `## Kill criteria`) + retro.md (3 load-bearing claims probe-verified) are a genuine worked example, referenced from the SKILL.md guidance. Soft-not-hard honored (spec_lint unchanged, no presence enforcement); conventions.md untouched; SKILL.md links resolve; full suite green (exit 0).

RECONCILIATION NOTES:
- The roadmap.md/CLAUDE.md deltas the reviewer saw in `git diff main` are NOT this slice's changes — the worktree base is behind current main (main gained docs/roadmap.md via #48 after branch point; `git log main..HEAD` is empty). They reconcile on rebase. Note in deviation log to avoid confusion.
- 064-01 emphasis (grounding-first; frame-critique gated/kill-criterion-watched) is already reflected in the SKILL.md + stub framing — priority note, no rework.
