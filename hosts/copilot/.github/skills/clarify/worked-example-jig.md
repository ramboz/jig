# Worked example: clarify against an early-DRAFT spec 018-slice-per-file

> **Purpose.** Demonstrates the six-category ambiguity scan against a
> reconstructed-DRAFT snapshot of [spec 018-slice-per-file](../../docs/specs/018-slice-per-file/spec.md)
> as it might have looked before slice 018-01 nailed down the
> dual-read contract. Shows the model's internal coverage scan,
> the prioritized questions chosen, the verbatim user answers,
> and the appended `## Clarifications` section.
>
> The snapshot is intentionally rough — the kind of DRAFT a spec
> author would type up in 20 minutes and then call clarify on
> before promoting to `READY_FOR_REVIEW`.

## Input excerpt: reconstructed early-DRAFT spec 018

```markdown
---
status: DRAFT
skill: (none — layout refactor)
tier: (n/a)
---

# Spec 018: per-slice files

## Overview

Today every slice lives as a `## Slice` section inside `spec.md`.
That doesn't work for downstream projects that want one file per
slice. Move each slice into its own file.

## Why now

Downstream cross-project comparison surfaced that other projects
treat slices as one-file-each. Our monolithic spec.md doesn't map.

## Goals

- One file per slice
- Existing callers keep working
- Migration helper for old specs

## Decomposition

A few slices: parser changes, caller migration, scaffold defaults,
migration helper.
```

That's all the spec author wrote before calling
`/jig:clarify` against `docs/specs/018-slice-per-file/spec.md`.

## Internal coverage scan (not shown to user)

| Category | Status | Notes |
|---|---|---|
| Scope & Boundaries | Partial | "Existing callers keep working" — but what about the existing `## Slice` sections that already exist in monolithic spec.md files? Are they migrated or left in place? |
| Acceptance Criteria Testability | Missing | No ACs in the spec body yet (which is expected at DRAFT, but the goals are also not testable as written: "existing callers keep working" → tested how?). |
| Dependencies & Blockers | Clear | No dependencies declared, none implied; layout refactor is self-contained. |
| Non-functional Requirements | Partial | No mention of performance, but file I/O at parse time matters for big specs; no mention of backwards-compat semantics. |
| Edge Cases & Failure Modes | Missing | What happens if a slice file is malformed? If the parent spec.md still has a `## Slice` section? If two slice files claim the same number? |
| Terminology Consistency | Partial | "slice" used clearly; "spec" sometimes means the directory, sometimes the file. |

Three Partial + two Missing + one Clear. The model picks four
questions across the four worst-rated categories, leaving one
question of budget unspent because terminology consistency
resolves on a single answer.

## Q&A trace

### Q1: When a project already has slices inside `spec.md`, does the spec 018 refactor require migrating them all to per-slice files, or are both layouts supported indefinitely?

**(category: Scope & Boundaries)**

**User answers:**

> Both layouts are supported indefinitely. Existing specs keep their
> monolithic shape; new specs scaffold per-slice. A migration helper
> (slice 018-04) is offered but optional.

### Q2: What's the testable form of "existing callers keep working"? For example, does `review.py find_slice_label` need to find labels in both layouts, and how do you assert that?

**(category: Acceptance Criteria Testability)**

**User answers:**

> Every caller that today reads slice content from spec.md must
> transparently read from `slice-NN-*.md` if the slice fragment
> resolves there. Test: for each caller, write a `MixedLayout<Caller>Tests`
> class with at least one fixture where the slice lives in a file
> and one where it lives inside spec.md. Both must produce identical
> results.

### Q3: If a slice file is missing or malformed, what's the failure mode? Hard error, silent fallback to spec.md, or refuse-with-message?

**(category: Edge Cases & Failure Modes)**

**User answers:**

> Hard error on parse failure (the slice file exists but is malformed).
> Silent fallback only when the slice file doesn't exist (then the
> caller reads from spec.md). The refuse-with-message case applies to
> the migration helper (018-04) when it would overwrite an existing
> slice file — it refuses, doesn't merge.

### Q4: In the body, "spec" sometimes means the directory (`docs/specs/018-slice-per-file/`) and sometimes means the file (`spec.md`). Pick one term for each and lock it.

**(category: Terminology Consistency)**

**User answers:**

> "spec directory" for the directory; "spec.md" for the file. The
> bare word "spec" is fine when context is unambiguous (e.g. "this
> spec ships per-slice files" reads naturally without qualifying
> which artifact).

## Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Outstanding |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Resolved |

Five of six categories closed; **Non-functional Requirements**
stayed Outstanding because the five-question budget was hit after
four questions and the model judged the remaining gap (file I/O
performance for big specs, semver bump for the layout change) as
lower priority than the four answered. Spec author can revisit
NFRs in a follow-up clarify run or in the spec body directly.

## Rendered `## Clarifications` section (appended to spec.md)

This is what the skill writes to `docs/specs/018-slice-per-file/spec.md`:

```markdown
## Clarifications

### Q1: When a project already has slices inside `spec.md`, does the spec 018 refactor require migrating them all to per-slice files, or are both layouts supported indefinitely?
_(category: Scope & Boundaries)_

Both layouts are supported indefinitely. Existing specs keep their
monolithic shape; new specs scaffold per-slice. A migration helper
(slice 018-04) is offered but optional.

### Q2: What's the testable form of "existing callers keep working"? For example, does `review.py find_slice_label` need to find labels in both layouts, and how do you assert that?
_(category: Acceptance Criteria Testability)_

Every caller that today reads slice content from spec.md must
transparently read from `slice-NN-*.md` if the slice fragment
resolves there. Test: for each caller, write a `MixedLayout<Caller>Tests`
class with at least one fixture where the slice lives in a file
and one where it lives inside spec.md. Both must produce identical
results.

### Q3: If a slice file is missing or malformed, what's the failure mode? Hard error, silent fallback to spec.md, or refuse-with-message?
_(category: Edge Cases & Failure Modes)_

Hard error on parse failure (the slice file exists but is malformed).
Silent fallback only when the slice file doesn't exist (then the
caller reads from spec.md). The refuse-with-message case applies to
the migration helper (018-04) when it would overwrite an existing
slice file — it refuses, doesn't merge.

### Q4: In the body, "spec" sometimes means the directory (`docs/specs/018-slice-per-file/`) and sometimes means the file (`spec.md`). Pick one term for each and lock it.
_(category: Terminology Consistency)_

"spec directory" for the directory; "spec.md" for the file. The
bare word "spec" is fine when context is unambiguous (e.g. "this
spec ships per-slice files" reads naturally without qualifying
which artifact).

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Outstanding |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Resolved |
```

## What this run produced

The spec author can now:

1. Update the Decomposition section to enumerate slices explicitly
   (Q1's answer makes 018-04 optional but called-out).
2. Add ACs that name the `MixedLayout<Caller>Tests` invariant
   (Q2's answer is directly testable).
3. Add an Edge Cases subsection to the Overview noting the
   refuse-with-message + hard-error + silent-fallback hierarchy
   (Q3).
4. Sweep the body for "spec" → "spec directory" / "spec.md" /
   bare "spec" per Q4's lock.

The Outstanding NFR category is a known gap for the spec author
to either address inline or accept as a follow-up note in
`refinement-todo.md`. The skill flagged it; the choice is the
author's.

## What the skill did NOT do

- **Did not paraphrase the user's answers.** "Both layouts are supported
  indefinitely" stays verbatim; the skill did not rewrite it to
  "The migration to per-slice files is offered on an opt-in basis
  to preserve backwards compatibility."
- **Did not modify the spec body above `## Clarifications`.** The
  Overview / Why now / Goals / Decomposition sections are
  unchanged. Editing them is the spec author's job, informed by
  the clarifications.
- **Did not transition the slice state.** Promoting DRAFT →
  READY_FOR_REVIEW is `/jig:spec-workflow`'s job; clarify is
  advisory.
- **Did not file ADRs from the answers.** The "Both layouts supported
  indefinitely" decision in Q1 is durable enough to warrant an ADR;
  the spec author should run `/jig:adr-workflow new` separately
  to capture it.
