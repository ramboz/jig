---
status: DRAFT
dependencies: []
last_verified:
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
# design_review: true  # set true when this slice's fidelity must be a HARD
#                      # gate: extract the mockup's design values (colours,
#                      # spacing, sizes, layout rules) into this slice's ACs,
#                      # then wire a servo `design-eval` as the done-condition
#                      # (attest-only at REVIEWED; ADR-0014, ADR-0022,
#                      # ADR-0049).
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 114-01 — severity-tags-and-review-rendering

**Goal:** Every rule in `docs/conventions.md` carries an id, a severity and a
promotion state, and the review passes render them so a verdict cites the rule
it found against and withholds `pass` only for an unmet enforced MUST.

**DoR:**
- ✅ [ADR-0062](../../decisions/adr-0062-convention-rule-severity-and-promotion.md) Accepted.
- ✅ Owner has approved the initial severity/state assignment for the existing
  rules (a `JIG_CONVENTIONS_APPROVED=1` edit under spec 102) — the slice
  renders that assignment, it does not choose it.
- ✅ Probed the reviewer-prompt block composition in `review.py` and the
  verdict frontmatter the evidence gate reads, so the rendering slots in
  beside `_principles_check_block` without a new gate.

**Acceptance Criteria:**

1. **Tagged rule shape.** Each `**Rule:**` block in `docs/conventions.md` and
   in `templates/docs/conventions.md.template` carries `**Id:**` (a stable
   `<section>.<slug>`), `**Severity:** MUST|SHOULD`, and
   `**State:** advisory|enforced`. Observable: a parser in `_common/` returns
   the rule list with those fields for both files; a block missing any field
   is reported by id/section.
2. **Review passes render by state.** The compliance and craft prompts built by
   `review.py` include the enforced rules as blocking checks and the advisory
   rules as report-only checks, each with its id. Observable: prompt fixture
   text contains both groups, correctly partitioned, within the per-block size
   hygiene precedent (or the slice records the measured size and why it is
   acceptable).
3. **Verdict semantics.** A recorded review verdict lists the rule ids found
   against; `verdict: pass` is withheld only when an `enforced` + `MUST` id is
   among them. Observable: a verdict fixture with an advisory finding still
   passes the evidence gate; one with an enforced-MUST finding is refused by
   `transition` with the rule id named.
4. **Id-citation fixture.** A reviewer given a synthetic breach of a known rule
   cites that rule's id (the load-bearing assumption in ADR-0062). Observable: a
   fixture in the test suite; if it cannot be made deterministic, the slice
   records the manual dogfood result in its deviation log.
5. **Principles untouched.** `_principles_check_block` and
   `docs/product-vision.md` are unchanged. Observable: existing tests pass
   without edits.

**Anti-horizontal-phasing check:** After this slice a reviewer verdict says
which convention was breached and whether that blocks; a `pass` with advisory
findings is legible and a `needs-changes` is auditable to a rule.

### For `kind: spike` slices

When the slice's frontmatter has `kind: spike`, the body carries four
extra labelled blocks alongside the standard Goal / DoR / AC / DoD
scaffolding. Spike slices are timeboxed investigation, not feature
work — they reduce an unknown before committing to a design.

```markdown
**Question:** _One sentence stating the open question. Set at DRAFT._

**Time-box:** _Explicit budget — e.g., "1 day", "4 hours". Set at DRAFT._

**Findings:** _Bullet evidence collected during the spike. Filled
during IN_PROGRESS._

**Outcome:** _One of: `ADR-NNNN created` / `spec NNN-NN unblocked` /
`abandoned (reason)`. Multiple outcomes separated by `;`
(e.g., `ADR-0007 created; spec 030-02 unblocked`). Set at DONE._
```

`spec_lint.py` validates the `kind:` enum (allowed values: `spike`,
`feature`) and soft-warns when a `kind: spike` slice is missing any of
the four labels. Mid-flight spikes legitimately have empty Findings /
Outcome, so this is a warning, not a hard error.

See `skills/spec-workflow/SKILL.md` (Spike slices subsection) and
`docs/spec-workflow/spidr-primer.md` for the always-nested rule (spike
slices live inside a real spec, never as standalone `docs/spikes/`
artifacts) and the abandoned-outcome manual-reshape failure mode.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry — drop facts derivable from the
      spec dir + status board, migrate load-bearing per-slice
      invariants to the status board Notes column, keep at most a
      one-liner only for cross-cutting facts. If the spec is still
      in flight (other slices DRAFT / READY / IN_PROGRESS), leave
      the entry. If this slice introduces a new skill, add or
      update its row in the Skills table.

**Anti-horizontal-phasing check:** _TODO: in one sentence, describe
the end-to-end observable value a user gets after this slice lands.
If the answer is "intermediate state for the next slice," the slice
is mis-shaped — re-split._

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO: why this slice did not affect the project front door, or summarize the update._ |
| `docs/specs/README.md` | `updated` | _TODO: regenerated by `workflow.py status-board`, or explain why deferred._ |
| `docs/product-vision.md` | `no-op` | _TODO: checked for behavior / scope drift._ |
| `docs/architecture.md` | `no-op` | _TODO: checked for module-boundary / public-contract drift._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: primer hygiene checked; note compression or template updates if any._ |
| `docs/inbox.md` | `no-op` | _TODO: checked for items resolved by this slice._ |
| `docs/refinement-todo.md` | `no-op` | _TODO: checked for resolved items or new deferred decisions._ |
| `docs/memory/**` | `no-op` | _TODO: note memory-sync result or why nothing was worth capturing._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO: use `updated` when the slice touched ADRs; otherwise mark checked._ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO: name owner or trigger when real cleanup remains; otherwise replace with `no-op`._ |
