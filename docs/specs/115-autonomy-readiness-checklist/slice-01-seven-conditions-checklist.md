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

## Slice 115-01 — seven-conditions-checklist

**Goal:** An adopter deciding whether a repo may run unattended has a
checklist in the scaffolded `governance.md` (and jig has one for itself) that
names the seven autonomy conditions and says, per condition, what jig covers,
what the executor must supply, and what is nobody's yet.

**DoR:**
- ✅ Seven-conditions wording re-checked against the primary Cloudflare post
  (R-001 flags it as second-hand); the checklist quotes or paraphrases with a
  citation.
- ✅ Probed `render_governance_doc` (`skills/scaffold-init/governance.py`) and
  the governance scaffold tests, so the new section slots in beside the arming
  checklist without changing the protected-paths or identity sections.

**Acceptance Criteria:**

1. **Checklist rendered.** `render_governance_doc` emits a
   `## Autonomy-readiness checklist` section listing the seven conditions as
   checkboxes, each with a one-line "who supplies it" note (jig / executor /
   unassigned). Observable: the scaffold governance test asserts the section
   and all seven items on a fresh scaffold.
2. **Honest coverage.** The note for each condition matches jig's shipped
   surface: identity/capability separation → `governance.py identity-check`;
   learns from experience → the memory layer; reproducible → the
   witnessed red→green test and evidence artifacts; API-operable,
   preview-per-agent, event-triggered, privilege escalation → executor
   (servo or the ADR-0060 orchestrator), marked as not jig's. Observable: a
   reviewer can trace each note to a spec or ADR link in the rendered text.
3. **Self-hosted copy.** `docs/adoption-readiness.md` gains a "Running
   unattended" section with the same checklist and coverage notes, linking
   ADR-0051 / ADR-0060 / ADR-0063. Observable: the section exists; the
   template `templates/docs/adoption-readiness.md.template` is updated or the
   deviation log says why not.
4. **Inert-until-armed preserved.** The rendered doc still states that the
   checklist is a precondition list, not enforcement, in the same register as
   the existing "INERT UNTIL ARMED" section. Observable: the existing test for
   that statement still passes.

**Anti-horizontal-phasing check:** After this slice an adopter can run the
checklist before an unattended run and see exactly which conditions their
executor must still supply.

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
