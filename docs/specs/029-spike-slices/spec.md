---
status: DONE
skill: spec-workflow
tier: 0
---

# Spec 029: Spike slices (typed `kind: spike` + body shape + status-board marker)

## Overview

SPIDR (Spike / Paths / Interfaces / Data / Rules) is jig's documented
story-splitting framework — see [docs/spec-workflow/spidr-primer.md](../../spec-workflow/spidr-primer.md).
Of the five techniques, **S — Spike** is the only one without a
machine-readable footprint today. The primer names it; nothing else
in the toolchain recognizes a "spike slice" as structurally distinct
from a feature slice.

This is a real gap. Spike-shaped work — timeboxed investigation to
reduce an unknown before committing to a design — happens in practice
(the [aso-shallow-validator](https://github.com/ramboz/aso-shallow-validator)
project ships flat slice files where several are explicitly
spike-shaped). Jig today either:

- **Pretends the spike is a regular slice.** Acceptance criteria
  contort into "research-shaped" prose; reviewers don't know whether
  to evaluate "did the code do what the AC says" or "did the
  investigation produce defensible findings."
- **Skips the spike.** Implementer guesses, ships, and the deviation
  log carries the unknown forward.

Spec 029 promotes the SPIDR "S" from decorative to load-bearing:

- **Typed frontmatter.** Slice frontmatter gains a `kind` enum;
  `kind: spike` is the first non-default value. `spec_lint.py`
  validates the enum.
- **Documented body shape.** Spike slices carry four extra labelled
  blocks (**Question** / **Time-box** / **Findings** / **Outcome**)
  alongside the standard Goal / DoR / AC / DoD scaffolding. Outcome
  is one of: `ADR-NNNN created` / `spec NNN-NN unblocked` /
  `abandoned (reason)`. Multiple outcomes allowed.
- **Decomposition guidance.** SPIDR primer + spec-workflow SKILL.md
  document the rule: "when SPIDR's S fires during decomposition,
  mark the slice `kind: spike` and use the body shape."
- **Always nested.** Spikes live inside a real spec, never as a
  standalone artifact. The 1-slice-spec case (no clear downstream
  spec yet, just an investigation) collapses to "spawn a normal
  spec where the only slice is `kind: spike`." Forces the
  investigator to articulate the downstream change up front.
- **Abandoned-spike manual reshape.** If a spike concludes
  `abandoned`, dependents are flagged for the human to audit — no
  automatic cascade. Documented as a failure mode in SKILL.md.
- **Status-board marker.** `workflow.py status-board` renders spike
  slices with a visible marker so risk-shaped decomposition is
  scannable.

The design was firmed up in the 2026-05-18 conversation that authored
this spec. Two key judgment calls landed:

1. **Typed frontmatter, not body-only convention.** Machine-readable
   so future helpers (e.g., a hypothetical `workflow.py spike
   conclude --adr NNNN`) and the status-board marker have a
   reliable signal.
2. **Always nested, no standalone artifact.** Resists creating a
   third numbered family (`docs/spikes/`) when the existing slice
   format already carries the shape cleanly.

## Why now

- **Direct gap surfaced from a real project (2026-05-18).** The
  aso-shallow-validator project ships spike-shaped work in a flat
  slice layout. When migrating downstream projects to jig (per spec
  020's slice-to-spec workflow), spike-shaped slices have nowhere
  natural to land today — they're forced into the feature-slice
  shape.
- **SPIDR vocabulary already in place.** The 2026-05-15 SPIDR primer
  landed the five techniques as a teaching artifact. Promoting "S"
  from teaching to runtime is incremental.
- **Sequencing fits 2026-05-18 lifecycle work.** Specs 023 (clarify)
  and 024 (analyze) added two pre-implementation lifecycle stages
  (ambiguity scan + cross-artifact consistency). Spec 029 adds the
  third missing pre-implementation concept (timeboxed unknown
  reduction). The three together close the spec-kit gap analysis
  cleanly.
- **Cheap, no architecture rework.** All the machinery already
  exists: frontmatter taxonomy from spec 015, enum validation in
  `spec_lint.py`, dual-read slice parsing from spec 018, status-board
  rendering in `workflow.py`. Spec 029 wires them up; it doesn't
  invent.

## Goals

1. **`kind: spike` as a typed slice frontmatter field.** Default
   unset (or `kind: feature` if we choose to make the default
   explicit). `spec_lint.py` validates the enum and refuses unknown
   values with a clear error.
2. **Body shape convention** documented in `templates/docs/specs/slice-template.md`
   and `skills/spec-workflow/SKILL.md`:
   - **Question** — one-sentence statement of the unknown being
     investigated. Set at DRAFT.
   - **Time-box** — explicit budget (e.g., "1 day", "4 hours"). Set
     at DRAFT.
   - **Findings** — evidence collected during the spike. Filled
     during IN_PROGRESS.
   - **Outcome** — one of `ADR-NNNN created`, `spec NNN-NN
     unblocked`, `abandoned (reason)`. Multiple outcomes allowed
     (e.g., `ADR-0007 created; spec 030-XX unblocked`). Set at DONE.
3. **SPIDR primer extension.** `docs/spec-workflow/spidr-primer.md`
   gains an explicit "when the S axis fires, the resulting slice is
   `kind: spike`" rule, with a worked example.
4. **spec-workflow SKILL.md guidance.** A short "Spike slices"
   sub-section covering (a) when to introduce a spike during
   decomposition, (b) the body shape, (c) the abandoned-spike
   manual-reshape pattern.
5. **Status-board marker.** `workflow.py status-board` renders spike
   slices with a visible marker (e.g., a leading `🔬` icon or a
   `[spike]` prefix — pick during implementation). Markers are
   preserved across regens.
6. **Abandoned-spike failure mode documented.** When a spike's
   `Outcome` is `abandoned`, SKILL.md instructs the human to audit
   each dependent slice for whether the original design still
   holds. No automatic dependent-cascade in workflow.py.
7. **Self-dogfood.** Spec 029 itself does not need a spike (the
   design landed without one), but the SPIDR primer and SKILL.md
   guidance include a worked spike example so the shape is
   demonstrated end-to-end.

## Non-goals

- **No standalone `docs/spikes/` artifact.** Rejected in the design
  conversation: spec+slice layout carries the shape; a third
  numbered family is net cost (migration surface, numbering
  collisions, lifecycle vocabulary). Resist unless empirical signal
  emerges.
- **No automatic dependent-cascade on abandoned outcome.** The human
  audits. Automation here over-fires: "approach A abandoned" often
  means "approach B from the same findings still satisfies
  dependents."
- **No `workflow.py spike conclude` helper in MVP.** Setting
  `status: DONE` + filling the `Outcome` block is enough. If
  authoring friction surfaces three times, a follow-up slice can
  add the helper.
- **No new lifecycle states.** Spike slices use the same DRAFT →
  READY_FOR_IMPLEMENTATION → IN_PROGRESS → REVIEWED → RECONCILED →
  DONE machine. Spike-specific behavior is in the body shape, not
  the state.
- **No retroactive migration of past slices.** No existing jig
  slices are spike-shaped; none need backfilling. If a downstream
  project's migration via [spec 020](../020-migrate-slice-to-spec/spec.md)
  reveals spike-shaped slices, they get `kind: spike` then.
- **No `kind` values beyond `spike` in this spec.** The enum is
  extensible (`kind: refactor`, `kind: docs`, etc.) but only
  `spike` is wired in 029. Future slices can add values; the spec
  029 design just plants the field.

## Open questions

- **Default `kind` value.** Two options: (a) `kind` unset means
  "feature" implicitly, (b) `kind: feature` is the explicit default
  in the template and spec_lint treats unset as a soft warning.
  Lean (a) — minimizes migration churn for existing slices, keeps
  spike-as-exception in the surface. Decide in slice 029-01.
- **Body-shape validation strictness.** `spec_lint.py` validates
  the `kind` enum. Does it also validate that `kind: spike` slices
  carry the four labelled blocks (Question / Time-box / Findings /
  Outcome)? Lean: yes, but as a **soft warning** rather than a
  refusal. Hard refusals on missing body labels are punitive for a
  pattern that's still settling. Revisit if signal emerges.
- **Status-board marker form.** Three candidates: leading icon
  (`🔬`), prefix tag (`[spike]`), or new column. Lean: leading icon
  in the existing "slice" column — cheapest, no schema churn,
  reuses the spec 028 pattern. Pick in slice 029-02.
- **Outcome enum: free-form `abandoned (reason)` vs structured.**
  The "abandoned" case carries a reason in prose. Two structures:
  (a) free-form trailing parenthesis, (b) sub-field
  `abandoned_reason:`. Lean (a) — readability beats parsability
  for a field humans write and humans read. spec_lint shouldn't
  parse this.

## Decomposition

Two slices, sequenced. SPIDR analysis:

| Technique | Question | Outline |
|---|---|---|
| **S** — Spike | Spike to clarify how `kind: spike` interacts with existing frontmatter or status-board rendering? | **No spike needed.** Frontmatter taxonomy (spec 015) already accommodates new fields; `spec_lint.py` already validates enums; status-board rendering is well-trodden territory after specs 003 and 028. Design firmed up in conversation. |
| **P** — Path | One big slice or split machinery from visual? | **Split.** Slice 029-01 = authoring surface (frontmatter + body shape + docs); slice 029-02 = rendering surface (status-board marker). Each ships end-to-end value: 029-01 makes spike slices authorable + validated; 029-02 makes them scannable. |
| **I** — Interface | Where does `kind: spike` surface? | Four surfaces — frontmatter, body shape, SPIDR primer, status board. 029-01 handles the first three (authoring); 029-02 handles the fourth (rendering). |
| **D** — Data | What does `kind: spike` consume and produce? | **Consumes:** slice files with `kind: spike` frontmatter and the four body labels. **Produces:** validated frontmatter (029-01) + visible-in-status-board markers (029-02) + optional forward-links via the Outcome field (no new machinery — same conventions as existing dependencies). No persistent state outside slice files. |
| **R** — Rules | What governs validity, sequencing, and failure modes? | (a) `kind` is enum-validated by spec_lint; (b) `kind: spike` body shape is soft-warn validated; (c) `dependencies:` field handles ordering (existing); (d) abandoned outcome = manual dependent audit (SKILL.md, no automation); (e) status-board marker preserved across regens (existing Notes-column pattern). |

### Slices

- [029-01 — kind-frontmatter-and-body-shape](slice-01-kind-frontmatter-and-body-shape.md) — DRAFT
- [029-02 — status-board-spike-marker](slice-02-status-board-spike-marker.md) — DRAFT

## Out of scope for spec 029 (any slice)

- **Other `kind` values** (`refactor`, `docs`, `infra`, etc.).
  Field is extensible; this spec only wires `spike`. Adding more
  values is cheap once the enum exists; deferred until signal.
- **`workflow.py spike` subcommand** for create/conclude/audit
  helpers. The hand-authoring loop is enough for MVP. Helper lands
  if friction surfaces.
- **Retroactive labelling of past slices.** No jig slices today are
  spike-shaped; nothing to backfill.
- **CI integration.** spec_lint already runs in CI per spec 013;
  enum validation comes along for free. No new CI plumbing.
- **Cross-spec spike discovery** ("show me every open spike across
  all specs"). Could fall out of status-board rendering as a
  natural side effect; if it doesn't, a separate `workflow.py
  spikes` subcommand can land later. Out of scope for 029.

## References

- **Originating conversation:** 2026-05-18 — "shallow validator has
  spikes, jig doesn't plan for those" → design discussion → typed
  frontmatter + always-nested + manual reshape decisions.
- **SPIDR primer:** [docs/spec-workflow/spidr-primer.md](../../spec-workflow/spidr-primer.md)
  — the five techniques, including the "S" axis that this spec
  promotes from teaching to runtime.
- **Frontmatter precedent:** [spec 015 — structured-lifecycle-metadata](../015-structured-lifecycle-metadata/spec.md)
  established the per-slice frontmatter pattern that 029-01 extends.
- **Body-shape precedent:** every slice template since spec 018 uses
  bold-labelled blocks (`**Goal:**`, `**DoR:**`, `**AC:**`, etc.).
  Spike slices add four more.
- **Status-board marker precedent:** the Notes-column preservation
  pattern from `workflow.py status-board` (preserved across regens).
- **Always-nested-not-standalone reasoning:** jig today has two
  numbered families (specs+slices, ADRs). Adding a third
  (`docs/spikes/`) is net cost; spec+slice already carries the
  shape.
- **Downstream evidence:** aso-shallow-validator ships flat slice
  files where several are spike-shaped — the motivating real-world
  example.
