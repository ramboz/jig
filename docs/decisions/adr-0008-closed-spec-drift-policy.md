---
dependencies: []
last_verified: 2026-05-27
---

# ADR-0008: Closed-spec drift policy

## Status

Accepted (2026-05-27)

Superseded by [ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md) (2026-05-29)

## Context

jig's process treats ADRs as immutable per ADR-0006 / Nygard. Closed
specs (status `DONE` or `SUPERSEDED`) have no equivalent rule. In
practice, closed specs drift as the implementation evolves around
them: a count cited in load-bearing prose changes, a SKILL.md
description claims a sibling skill doesn't ship when it now does,
status-board claims about pending slices stay frozen after those
slices land. Five such drifts are live in the repo today (verified
2026-05-26; see [spec 036](../specs/036-closed-spec-drift/spec.md)
"Current state" table).

The cost of these drifts is not uniform:

- Some are merely confusing (the README's "5 Tier 0 skills" claim
  when the codebase has 7).
- Some influence router behavior (`pr-review/SKILL.md` saying
  "jig does not ship an arch-review skill today" — the SKILL
  description string is what Claude reads when deciding whether
  to route arch-review work; the false claim biases the router
  toward `pr-review`).
- Some surface and re-surface as cargo-culted conventions
  (`docs/workflow.md`'s `disable-model-invocation: true` claim for
  three skills that no longer carry the flag).

The **dogfooding moment** that prompted this ADR: slice 005-03's
close-out swept a six-→-seven hook count in the **code** but did
not sweep [spec 016](../specs/016-scaffold-mode/spec.md)'s prose
saying "the same five jig hooks" (line 72 and three other places).
The author had every incentive to keep the spec aligned with reality
and still missed it, because the convention for *how* to edit a
closed spec did not exist. Closed-spec drift is not a discipline
failure; it is a missing rule.

This ADR establishes the rule. The rule must:

1. Cover both closed specs and load-bearing skill/router prose
   (per spec 036 clarification Q2). The `pr-review` SKILL.md case
   is the same kind of artifact for policy purposes — its
   accuracy is load-bearing for jig's process behavior.
2. Apply to `DONE` and `SUPERSEDED` specs but not to
   `IN_PROGRESS`, `READY_FOR_REVIEW`, `REVIEWED`, `RECONCILED`,
   `DRAFT`, or `DEFERRED` ones (per Q1 + Q3).
3. Be cheap enough to actually use. A rule that costs more than
   the drift itself will be ignored, and we will end up where we
   started.

[Spec 042](../specs/042-spec-gate-model/spec.md) is in flight on
the adjacent question of how `docs/conventions.md` gates spec
edits in general. This ADR scopes the *drift* question; 042 may
later scope the *edit-permission* question. Coordination noted in
"Relationship to other decisions" below.

## Decision Options Considered

### Option A: Immutable closed specs; deltas land as new ADRs or `docs/inbox.md` entries

Treat closed specs the same way ADR-0006 treats accepted ADRs: the
file is frozen at the `DONE` / `SUPERSEDED` transition. Subsequent
deltas land elsewhere — a new ADR for decision-content changes, a
`docs/inbox.md` entry for transient notes that don't warrant
permanent record.

- **Cost:** High per-delta. Five live drifts → up to five new
  ADRs or inbox entries to land them. ADR overhead is real: slug,
  context, options, decision, consequences, index regeneration.
- **Discoverability:** Indirect. A reader of a closed spec sees
  the original prose and must cross-reference an ADR index or
  inbox to learn current state. Cross-file navigation is friction.
- **Audit trail:** Strongest of the three options. Every delta
  produces a first-class, indexed, dated record. The spec's
  history is reconstructable from the ADR / inbox stream without
  reading the spec body itself.

### Option B: `## Amendments` section appended to the drifted artifact

Allow exactly one new section, `## Amendments`, at the end of the
closed artifact. In-body edits to original prose remain forbidden.
Each amendment is a dated, linked, single-purpose entry that names
what changed and why. The shape (locked in by spec 036's
clarification Q5):

```markdown
## Amendments

### 2026-05-27 — Hook count: five → seven
Slice 005-03's six-→-seven hook sweep landed in code but not in
this spec's prose at lines 72, 412, 445, 471. Original claim
preserved above; current count is seven hooks.

- Link: [slice 005-03](../005-adr-workflow/spec.md)
```

(Paths in real amendments are relative to the amended artifact; the
above is what a `## Amendments` block on spec 016 would look like.)

- **Cost:** Low per-delta. A 3–6 line markdown block per drift.
  No ADR ceremony.
- **Discoverability:** Strongest of the three options. The delta
  lives in the same file as the original prose. A reader of spec
  016 sees both "the same five jig hooks" and the amendment that
  corrects it, without leaving the file.
- **Audit trail:** Adequate. Dated entries with links preserve
  the timeline; the `## Amendments` heading is greppable; the
  entries are append-only by convention. Weaker than Option A's
  indexed-ADR trail, stronger than free-form prose edits.

### Option C: Hybrid — `## Amendments` for prose, new ADR for decision changes

Default to Option B. Carve out an exception: if the delta changes
the *decision* a spec recorded — a contract, an interface, a
behavior the spec committed to — it warrants a new ADR (or a
superseding spec), not an amendment.

- **Cost:** Lowest in expectation. Prose drift (the common case)
  is cheap; decision drift (the rare case) gets appropriate ADR
  weight. Of the five live drifts, all are prose; zero would
  require an ADR under the carve-out.
- **Discoverability:** Same as Option B for the common case.
  Decision changes route through the ADR index, same as Option A.
- **Audit trail:** Strong for both axes. Prose drift gets a dated
  amendment beside the original; decision drift gets a first-class
  ADR. The author must judge which axis applies — a known fuzzy
  edge that ADR-0006's Option C carve-out also has.

### Option D: Status quo — no rule

Continue as today: closed-spec prose drifts silently; reconcilers
fix it ad hoc; SKILL descriptions stay wrong; the dogfooding
moment from slice 005-03 keeps repeating.

- **Cost:** Zero up-front. Cumulative cost grows with every drift
  not swept.
- **Discoverability:** None. Drift compounds invisibly.
- **Audit trail:** None. There is no record of what the spec
  originally said versus what it says now, and no record of who
  decided the silent edit was acceptable.

## Recommended Decision

**Option C — `## Amendments` as the default; new ADR (or
superseding spec) for decision-content changes.**

Three reasons:

1. **All five live drifts are prose drift.** None involve a
   decision change. Option C handles 100% of the actual workload
   at Option B's cost. The carve-out is precautionary; it covers
   the next case, not this one.
2. **Option C inherits ADR-0006's "default + narrow carve-out"
   shape.** That ADR's Recommended Decision is Option A (the
   canonical `new → edit → index (preview) → accept → index (final)`
   lifecycle) **plus** Option C (Context cosmetic edits are not
   decision-content and do not violate immutability) — a default
   rule with a scoped exception. It has held up. Option C here
   mirrors that structure: amendments are the default; decision-
   content changes are the scoped exception (warranting a new ADR
   or a superseding spec). Same discipline, different surface.
3. **The dogfooding moment supports B-over-A.** The slice 005-03
   miss happened because the spec-edit cost felt higher than the
   value at that moment. Option A would have made the cost higher
   still; Option B (and therefore C) brings the cost low enough
   that the sweep is actually likely to happen at close-out.
   `/jig:spec-workflow`'s reconciliation checklist will gain a
   one-line pointer to this ADR (slice 036-02), which closes the
   loop.

The fuzzy boundary at "is this prose or decision content?" is
real. The working rule: if the change would have warranted an
ADR if the spec author had foreseen it at draft time, it warrants
an ADR now. Counts, dates, status references, "this skill exists"
claims, and stub-flag claims are prose. Interface shapes,
contract surfaces, refusals, and policy commitments are decision
content. When in doubt, default to ADR — the higher cost is paid
by the editor, not by every future reader.

## Consequences

**Becomes easier:**

- Closed-spec drift has a named, cheap fix. Reconcilers who notice
  a prior closed-spec inaccuracy follow ADR-0008 instead of
  inventing convention per situation.
- Downstream specs (038 tier-reconciliation, 039 review-queue,
  040 isolation-honesty) operate under one rule when they edit
  closed-spec or load-bearing prose. Each cluster no longer
  reinvents the convention.
- Spec 036-02's one-time sweep of the four remaining live drifts
  (drift #5 is deferred to spec 038 to avoid double-edit) has a
  concrete form to follow: append `## Amendments` to each drifted
  artifact, one dated entry per drift, linked back to the slice
  / ADR / PR that caused the drift.
- Load-bearing skill/router prose (SKILL.md descriptions,
  workflow.md routing prose, README claims that drive decisions)
  inherits the same rule. The `pr-review/SKILL.md` arch-review
  drift is a prose-drift case under Option C.

**Becomes harder:**

- The "is this prose or decision content?" call sits with the
  editor. The boundary is fuzzy in the same way ADR-0006's
  Context-cosmetic carve-out is fuzzy. Mitigation: the default-to-
  ADR rule above shifts borderline cases toward higher rigor.
- Closed specs become two-section reads: original body + amendments.
  Readers must internalize that the amendments override the
  body where they overlap. The single-file co-location is a
  net benefit, but the convention has to be taught once.
- The `## Amendments` heading becomes a convention the team must
  hold to — accidental in-body edits to original prose still
  violate the rule. No mechanical enforcement ships with this
  ADR (per spec 036's "No new tooling" non-goal); the rule is
  for humans.

**Implementation status:**

- This ADR codifies the policy. The retroactive sweep of four
  live drifts (excluding drift #5, which spec 038 owns) lands
  in slice 036-02.
- The reconciliation-checklist line in
  `skills/spec-workflow/SKILL.md` pointing future reconcilers to
  this ADR also lands in slice 036-02.
- No tooling work falls out of this ADR. If the rule starts to
  fail (e.g., in-body edits keep slipping in despite the
  convention), a follow-up slice can add a `spec_lint.py` check
  that warns when a closed spec's body changes without an
  `## Amendments` entry in the same diff. That work is out of
  scope here; the rule first has to fail under enforcement before
  we add enforcement.

## Scope

**In scope:**

- Specs with `status:` frontmatter `DONE` or `SUPERSEDED`.
- Load-bearing skill / router prose: SKILL.md descriptions,
  `docs/workflow.md` routing prose, README claims that drive
  decisions.

**Out of scope:**

- Specs with `status:` `DRAFT`, `READY_FOR_REVIEW`,
  `READY_FOR_IMPLEMENTATION`, `IN_PROGRESS`, `REVIEWED`, or
  `RECONCILED` — these are still being shaped; in-body edits are
  normal.
- Slices with `status:` `DEFERRED` — there is no shipped behavior
  to drift from.
- ADRs — governed by ADR-0006 and the Nygard immutability
  baseline. This ADR does not change ADR rules.

**"Closed spec" defined for policy purposes:** a `spec.md` or
slice file whose `status:` frontmatter is `DONE` or `SUPERSEDED`.
No other state qualifies.

## Relationship to other decisions

- **ADR-0006 (adr.py accept-then-index ordering).** Baseline
  immutability discipline this ADR extends from ADRs to closed
  specs. The "Option C carve-out shape" pattern is borrowed
  directly.
- **Spec 042 (spec-gate model).** Light coupling: if 042 picks a
  stricter immutability gate on `docs/conventions.md` edits, this
  ADR is the more general rule and 042's gate becomes one
  specific case. The two should not contradict; if they do, the
  one that lands later supersedes by amendment.
- **Spec 036-02 (sweep-and-reconciliation-hook).** Downstream
  consumer of this ADR. Applies the rule to the four sweep-able
  drifts and adds the reconciliation-checklist line in
  `skills/spec-workflow/SKILL.md`.
- **Specs 038, 039, 040.** All edit closed-spec or load-bearing
  prose; all operate under this ADR.

## Open questions

None. Scope is bounded; the policy shape is fixed; the carve-out
discipline mirrors a working precedent (ADR-0006); the worked-
example sweep lands in 036-02.
