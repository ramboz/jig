# Worked example: analyze against spec 017-vision-elicitation mid-reshape

> **Purpose.** Demonstrates the six-category cross-artifact audit
> against a reconstructed snapshot of [spec 017-vision-elicitation](../../docs/specs/017-vision-elicitation/spec.md)
> at its mid-reshape moment — between AC #4's original three-stanza
> framing and the post-reshape four-elicitation-slot framing. The
> reshape produced **seven distinct staleness incidents** (per the
> CLAUDE.md hot-cache entry for spec 017), each of which analyze would
> have caught had the skill existed at the time. This worked example
> reconstructs the finding report analyze would have emitted.
>
> Six findings spanning **five of the six categories** (Duplication,
> Ambiguity, Underspecification, Principle Violations, Coverage Gaps,
> Terminology Drift) demonstrate that the taxonomy lights up cleanly
> on a real-world drift case from jig's own history.

## Input excerpt: reconstructed mid-reshape spec 017

The spec at this moment (between original AC #4 and the wholesale
reshape) had these surfaces in tension:

- `docs/specs/017-vision-elicitation/spec.md` — original AC #4 named
  three stanzas (What this project does / Tech stack / Module
  boundaries) and the slice scaffolded markers in those three slots.
- `templates/docs/architecture.md.template` — already-shipped template
  carried the three-stanza framing.
- `docs/architecture.md` (jig's own) — recently slimmed; the literal
  three-stanza framing had drifted; it now carried Repository
  structure / Tech stack / Module boundaries / Data model as
  elicitation slots, plus two non-marker sections.
- `templates/docs/architecture.md.template` versus jig's own
  architecture.md: the template had the OLD shape, jig's own
  architecture.md had the NEW shape, the spec's AC referred to the
  OLD shape.

```markdown
---
status: DRAFT
skill: vision-elicitation
tier: 0
---

# Spec 017: vision-elicitation

## Goals

1. A `vision-elicitation` skill that fills `docs/product-vision.md`
   slots and `docs/architecture.md` slots through an interactive
   question loop.

## Decomposition

### Slice 017-01 — template-slots-and-conventions

**AC #4**: `templates/docs/architecture.md.template` ships with three
elicitation slots: `## What this project does`, `## Tech stack`,
`## Module boundaries`. Each slot carries an
`<!-- elicited: ... / status: deferred -->` marker the wizard fills
on first run.

**AC #5**: The wizard scaffolds the three markers correctly. Tests
verify the marker count in scaffolded output.

### Slice 017-02 — skill-core

**AC #3**: The skill's `questions.md` covers all elicitation slots
from `templates/docs/architecture.md.template`. The fast-mode default
asks one question per slot.
```

While this DRAFT was open, the spec author landed a slimming pass on
jig's own `docs/architecture.md` — replacing the three stanzas with
four slots (Repository structure / Tech stack / Module boundaries /
Data model) plus two non-marker sections. The spec body wasn't
updated to match.

## Findings (sorted by severity)

| # | Severity | Category | Location | Finding |
|---|---|---|---|---|
| 1 | CRITICAL | Underspecification | spec.md:AC#4 | AC #4 references three stanzas ("What this project does / Tech stack / Module boundaries"), but jig's own `docs/architecture.md` was just reshaped to four slots (Repository structure / Tech stack / Module boundaries / Data model). The spec describes a deliverable that contradicts the worked-example artifact it should mirror. Block on this before any test gets written. |
| 2 | HIGH | Terminology Drift | spec.md:AC#4 vs `docs/architecture.md` | "What this project does" appears in the spec as an elicitation slot but in jig's own architecture.md the equivalent content lives in a top-of-doc product-vision pointer (no stanza). The spec uses a slot name the project no longer has. |
| 3 | HIGH | Duplication | spec.md:AC#5 vs spec.md:Slice 017-02 AC#3 | AC #5 ("wizard scaffolds the three markers correctly") and Slice 017-02 AC #3 ("questions.md covers all elicitation slots from the template") rely on the same three-stanza count. Both ACs will need to be updated in lockstep when the count changes from 3 → 4. The two ACs duplicate the "three markers" constraint with conflicting downstream consequences. |
| 4 | HIGH | Coverage Gaps | spec.md:AC#5 | AC #5 names "tests verify the marker count" but no test path is named (`tests/scaffold_init/test_scaffold.py::TestMarkerCount`?). The marker-count test is the load-bearing regression pin for the slot count; without a named test path it's untracked. |
| 5 | MEDIUM | Principle Violations | spec.md:Decomposition | The reshape that drifted the spec out of date was a mid-implementation flip; the spec body wasn't kept honest. Principle 4 (dogfood the workflow we build): the spec should describe what it actually ships, not what it shipped a session ago. |
| 6 | MEDIUM | Ambiguity | spec.md:Goals | "Fills slots through an interactive question loop" — no bound on the number of questions; no bound on session length. The spec leaves it open whether the loop is single-pass or iterative-refine. (Resolved later by AC #1's "fast mode / deep mode" split, but at this snapshot the goal text is ambiguous.) |

## Coverage summary

| Category | Findings |
|---|---|
| Duplication | 1 |
| Ambiguity | 1 |
| Underspecification | 1 |
| Principle Violations | 1 |
| Coverage Gaps | 1 |
| Terminology Drift | 1 |

All six categories light up on this snapshot — the mid-reshape moment
is genuinely cross-axis-drifty.

## Next steps

- Address the CRITICAL finding (Finding #1) before any further work:
  the spec describes a deliverable that no longer matches the
  worked-example artifact. Either revert the architecture.md reshape
  or amend the spec's AC #4 to the new four-slot shape. Without
  resolving this, implementer-subagent work will start from a
  contradicted spec.
- HIGH findings (#2, #3, #4) should be resolved before merge — they
  describe drift that ships if left untouched. Finding #3 in
  particular needs both ACs updated in lockstep, not just one.
- MEDIUM findings (#5, #6) can ship if explicitly accepted in the
  spec body or tracked in `docs/inbox.md`. Finding #6 was implicitly
  resolved when AC #1 grew the fast-mode / deep-mode split; logging
  it confirms the resolution was deliberate.

## What this run produced

The spec author at the time can now:

1. Pick the canonical four-slot framing (Repository structure / Tech
   stack / Module boundaries / Data model), update AC #4 in the
   spec, AND update `templates/docs/architecture.md.template` in the
   same change-set so future scaffolds get the new framing.
2. Update Slice 017-02 AC #3 to reference the canonical slot list
   (resolves Finding #3).
3. Add a named test path to AC #5 (e.g.,
   `skills/scaffold-init/test_scaffold.py::TestArchitectureMarkers::test_four_markers`)
   — resolves Finding #4 by giving the AC a verification surface.
4. Add a deviation-log entry noting the mid-reshape pivot and why
   the spec body was updated to match (closes Finding #5).
5. Sweep the spec body for any other stale references to "three
   stanzas" or "What this project does" as a deliverable section
   name (closes Finding #2).

## What this run shows about the taxonomy

This historical snapshot is genuinely valuable for analyze's design:
the seven staleness incidents that hit spec 017 over its lifetime
were all variants of these six categories. None of them surfaced as
"is the syntax valid?" (that's `scripts/spec_lint.py`'s job); all of
them surfaced as "are these artifacts consistent with each other?"
(that's analyze's job).

The reshape-induced drift pattern is recurring in jig's history —
spec 012-01, 015-01, 022-01 all hit milder variants. Analyze
catches them cleanly.

## What the skill did NOT do

- **Did not modify the spec.** Even Finding #1 (CRITICAL) didn't
  trigger an edit. The skill's job is to surface; resolution is the
  spec author's.
- **Did not file an ADR.** Finding #5 hints that a principle-4 audit
  rule might be worth an ADR (e.g., "if you reshape the
  worked-example artifact, you MUST update every spec body that
  references it in the same session"), but the skill doesn't write
  ADRs.
- **Did not transition the slice state.** A CRITICAL finding might
  warrant rolling the spec back from READY_FOR_REVIEW to DRAFT, but
  that's `/jig:spec-workflow`'s job.
- **Did not re-rate the principle-violation severity.** The default
  table puts principle 4 (dogfooding) at MEDIUM; the model agreed
  in this case. A more egregious dogfood violation (e.g., shipping a
  skill that never gets tested against jig's own specs) would get
  bumped to HIGH.
