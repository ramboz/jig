---
status: DRAFT
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 025: CLAUDE.md hygiene (compress-on-close-out)

## Overview

CLAUDE.md is jig's hot cache — the per-session context loaded every
conversation. The slice close-out rule today is **additive**: every
closed slice's template instructs the implementer to "add a hot-cache
entry for this spec/slice." After 24 specs, the file has accumulated
~110 lines of mostly-historical paragraphs that duplicate content
already in `docs/specs/<NNN>/spec.md`. As of 2026-05-18, every spec
listed in CLAUDE.md's "Active specs" section is closed (zero specs have
a non-terminal slice). The hot-cache principle CLAUDE.md itself cites
("Dumb zone = >40% context fill; above this, model recall degrades")
is violated by CLAUDE.md's own accumulation.

The accumulating record already has a designed home: `docs/specs/README.md`
is the status board, maintained by `workflow.py status-board`, with a
Notes column the board's own header documents as preserved across regen
("curate it freely"). It's the right surface for per-slice load-bearing
invariants. CLAUDE.md should carry only what a fresh session actually
needs: active in-flight work + a few cross-cutting invariants.

This spec reframes the close-out rule from "add hot-cache entry" to
"compress to invariant-only OR remove if no invariant remains," applies
the new rule retroactively to today's CLAUDE.md, and codifies the rule
in both the slice template and the spec-workflow reconciliation
checklist so it holds going forward.

## Why now

- **Empirical trigger.** Today CLAUDE.md has 24 spec entries listed as
  "active"; **none** of them are. The drift is observable, not
  hypothetical.
- **The fix is structurally cheap.** The status board already
  accumulates and the Notes column is already documented as
  curate-freely. No new helper, no new doc, no new artifact — just a
  rule change + a retroactive sweep.
- **Recurring close-out drift.** The 012-01 reconciliation reviewer
  flagged "stale CLAUDE.md labels" (§7 of that slice's deviation log);
  multiple subsequent slices repeated similar drift (017-* staleness
  pattern hit 7 times). The current close-out rule produces the drift
  by design; reframing it removes the cause.
- **No dependency blockers.** The change touches `CLAUDE.md`,
  `templates/docs/specs/slice-template.md`, and
  `skills/spec-workflow/SKILL.md`. All three are owned in this repo;
  no upstream coordination needed.

## Goals

1. **CLAUDE.md "Active specs" section reflects only currently
   in-flight work** — specs with at least one slice in DRAFT /
   READY_FOR_REVIEW / READY_FOR_IMPLEMENTATION / IN_PROGRESS.
2. **Load-bearing invariants migrate to the status board Notes
   column** for the relevant slice, OR to docs/decisions/ for ADR-shaped
   invariants. Each migration is auditable from the deviation log.
3. **Stale "Current sprint focus" and "Prior context" stanzas removed**;
   replaced by either a one-line pointer to the status board or by an
   accurate description of what's actually next.
4. **Skills in this repo table rows are slimmed** to active-trigger
   summary (1-2 lines per skill), no slice-by-slice implementation
   history.
5. **ADR stanzas replaced** with a single index pointer to
   `docs/decisions/`.
6. **Slice template close-out section** reframed so the default
   instruction is **compression**, not addition. Promotion-to-Skills-table
   stays as a sub-rule when the slice introduces a new skill.
7. **Reconciliation checklist** in `skills/spec-workflow/SKILL.md`
   gains a "CLAUDE.md hygiene" gate pointing at the new template
   language.
8. **No load-bearing fact is silently dropped** — the deviation log
   enumerates every fact removed from CLAUDE.md and names where it
   went (status board Notes / ADR / dropped as derivable).

## Non-goals

- **No `workflow.py audit-claude-md` helper in this spec.** The
  rule-change is the structural fix. A helper that diffs CLAUDE.md
  Active-specs against the status board is candidate slice 025-02,
  DEFERRED on empirical signal.
- **No changes to `templates/CLAUDE.md.template`** (the
  scaffold-init template for new projects). That template is already
  lean — the bloat is jig-specific.
- **No changes to `docs/memory/learnings.md` or
  `docs/memory/glossary.md`.** Memory layer is orthogonal.
- **No changes to the status board generator (`workflow.py
  status-board`).** The Notes column is already curate-preserving;
  no behavior change needed.
- **No new ADR.** This is a process change codified in the template
  and SKILL.md, not a hard-to-reverse architectural decision.

## Decomposition

One active slice + one deferred follow-up. SPIDR-split:

| Technique | Question | Outline |
|---|---|---|
| **S** — Spike | Spike on "what counts as a load-bearing invariant worth keeping in the hot cache vs. moving to status board Notes"? | **No spike needed.** Decision rule: if a future contributor needs the fact to make a correct call without reading the spec dir, it's load-bearing. The deviation log records one line per migration, so the reviewer can audit each judgment call. |
| **P** — Path | Compress retroactively first, then change the rule? Or rule-first, then enforce retroactively? | **Both in one slice.** They're coupled — the new rule's dogfood IS the retroactive sweep. Splitting would ship the new template language without the cleanup that validates it. |
| **I** — Interface | Where does the rule live — template, SKILL.md, or conventions.md? | **Template + SKILL.md.** Template carries the slice-level instruction; reconciliation checklist points at it. `conventions.md` is intentionally untouched (the rule isn't an authoring standard for skills/hooks/agents). |
| **D** — Data | What gets removed from CLAUDE.md? What gets preserved where? | Per AC #1-#5: Active-specs section collapsed, ADR stanzas → pointer, Skills table rows slimmed, Sprint-focus rewritten. Status board Notes column receives any fact that's load-bearing for a specific slice. |
| **R** — Rules | What governs the compression decision per spec entry? | Three-way decision: (a) **drop** if derivable from spec dir + status board, (b) **migrate to Notes** if load-bearing for that slice specifically, (c) **migrate to ADR** if it's a cross-cutting decision (none expected for closed specs — those already have ADRs). |

### Slices

- [025-01 — cleanup-and-close-out-rule](slice-01-cleanup-and-close-out-rule.md) — DRAFT
- 025-02 — audit-claude-md helper — DEFERRED (no slice file yet; promote to DRAFT and add a slice file if the empirical trigger fires)

## Out of scope for spec 025 (any slice)

- **`workflow.py audit-claude-md` helper** that diffs CLAUDE.md
  Active-specs against the status board. Deferred to 025-02; promotion
  gated on 3+ closed specs lingering in CLAUDE.md after slice 025-01
  lands (drift recurrence) OR an explicit user request for the helper.
- **Migration of scaffolded-project CLAUDE.md files.** Only jig's own
  CLAUDE.md is touched. `templates/CLAUDE.md.template` is not changed.
- **Status-board generator changes.** The Notes column already
  preserves across regen; no helper changes needed.
- **`docs/inbox.md` triage process changes.** Slice 002-04 already
  wired inbox triage into the reconciliation checklist; this spec
  doesn't revisit that gate.

## Open questions

- **Compression vocabulary.** The new close-out language could say
  "compress" (preferred), "trim", or "retire". Lean: "compress" —
  matches the conceptual move (preserve invariant, drop history).
  Pick during implementation.
- **Where load-bearing invariants land when they span >1 slice.**
  Most facts are slice-scoped (one row in the status board Notes
  column). For cross-slice invariants (e.g., "ADR-0004: docs/decisions/
  is the layout"), the ADR doc itself is canonical; CLAUDE.md may
  keep a one-line index pointer. Decide per-entry in the deviation
  log.

## References

- **Originating conversation:** 2026-05-18 — user asked "review CLAUDE.md
  + refinement-todo + inbox; what can we clean up?" Reviewer surfaced
  that all 24 spec entries in CLAUDE.md are closed. User confirmed
  the framing ("we should be accumulating spec status in
  docs/specs/README.md more than CLAUDE.md itself") and picked
  full-sweep-plus-spec.
- **Status board curate-preservation:** `docs/specs/README.md` header
  documents Notes-column preservation across `workflow.py status-board`
  regen.
- **Close-out section precedent:** slice 009-01 introduced the
  `### Close-out (post-DONE)` subsection convention; this spec
  reframes what one of its checkboxes (CLAUDE.md updates) means.
- **Hot-cache "Dumb zone" principle:** CLAUDE.md's own Key terms
  section cites Horthy's >40% context fill threshold for model recall
  degradation. The current file's accumulation violates the cited rule.
- **Drift-recurrence evidence:** 012-01 deviation log §7 ("stale
  CLAUDE.md labels"); 017 spec deviation log catalog (7 staleness
  incidents); 022-02 implementation review surfaced "stale SKILL.md
  prose at 4 locations."

## Clarifications

> Produced by a manual application of `/jig:clarify`'s six-category
> algorithm on 2026-05-18 (the clarify skill itself ships in this
> branch's source but is not registered in the active session, so the
> algorithm was run inline against [skills/clarify/SKILL.md](../../../skills/clarify/SKILL.md)).
> Three prioritized questions asked; two of the six categories
> remained Partial-but-declined (canonical-term variants in
> Terminology; mid-flight slice conflict + reviewer-rollback edges in
> Edge Cases). User declined to ask the canonical-term Q4 — leaving
> as implementer judgment.

### Q1: When does slice 025-01's self-dogfood (compressing its own CLAUDE.md entry per AC #9) happen?
_(category: Edge Cases & Failure Modes)_

Post-DONE close-out. Standard close-out: after RECONCILED → DONE,
separate commit per checklist item. Matches every prior slice's
pattern (e.g. 013-04 close-out items). Two commits instead of one,
but consistent with the close-out convention slice 009-01
established.

### Q2: How should AC #2's three-way compression rule be biased when the implementer/reviewer disagree on whether a fact is "load-bearing"?
_(category: Acceptance Criteria Testability)_

Implementer judgment. No structural bias — the implementer makes
per-entry calls and the deviation log enumerates each; reviewer
audits the diff. Same shape as 022-02's contract-surface detection
decisions. Most flexible; most reviewer load.

### Q3: Should CLAUDE.md gain a small "Key invariants" subsection for cross-cutting facts (ADR-0004 layout rule, hook scripts use Python 3, etc.), or stay purely active-work-only with index pointers?
_(category: Scope & Boundaries)_

Extend Constraints section. The existing `## Constraints for agents
working on this repo` section (5 items) already serves this purpose.
Promote ADR-0004 layout and any other cross-cutting invariant into
bullets there. Zero new sections; reuses existing structure.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved (Q3) |
| Acceptance Criteria Testability | Resolved (Q2) |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Clear (N/A by judgment-skill / content-only convention) |
| Edge Cases & Failure Modes | Partial — Q1 closed dogfood-timing; mid-flight conflict + reviewer-rollback edges declined-to-ask (low stakes; no in-flight slices today) |
| Terminology Consistency | Partial — canonical-term variants ("compress-on-close-out" / "compress on close-out" / "CLAUDE.md hygiene") left to implementer judgment |
