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

## Slice 115-02 — fix-evidence-separation-rule

**Goal:** The ADR-0063 invariant — separate fix ref, failure stays red until
a human merges, green is new evidence on the fix revision, evidence-modifying
fixes are flagged — is stated where adopters and the bug-fix skill read it.

**DoR:**
- ✅ [ADR-0063](../../decisions/adr-0063-agent-fix-evidence-separation.md) Accepted.
- ✅ Probed `skills/bug-fix/SKILL.md`'s FIXING / REVIEWED / VERIFIED wording
  and `bug.py`'s evidence-pointer check, so the new wording lands in the
  existing sections rather than a parallel one.
- ✅ Probed whether an evidence-modifying diff is detectable (regression-test
  path from the bug record + skip/xfail/disable markers) — result recorded in
  this slice's DoR before AC 4 is committed to as a nudge vs guidance.

**Acceptance Criteria:**

1. **Governance rule stated.** `render_governance_doc` emits a
   `## Agent-proposed fixes` section with the four clauses of ADR-0063 in
   adopter-facing language. Observable: governance scaffold test asserts the
   section and the four clauses.
2. **bug-fix wording.** `skills/bug-fix/SKILL.md` names the fix ref
   (`fix/<bug-id>`), the append-only rule for attempt evidence, and that a
   re-run of the failing revision that passes is recorded as a flake signal,
   not a fix. Observable: the skill-surface test covers the new phrases; host
   packages regenerated (`build_host_packages.py`) and drift guard green.
3. **Spec 105 cross-link.** Spec 105's freeze-on-quarantine semantics cite
   ADR-0063 clause 1 as the same append-only rule, via an `## Amendments`-free
   inline link (spec 105 is still DRAFT, so live-prose correction is allowed).
   Observable: the link exists and `spec_lint.py --all` is green.
4. **Evidence-modifying flag.** If the DoR probe found detection reliable, the
   bug-fix `→ REVIEWED` transition emits a `jig hint:` naming the regression
   test path when the fix diff touches it or adds a skip marker, pointing at
   the owner-review path; otherwise the rule ships as reviewer guidance in the
   `bug-review` prompt and the deviation log records why. Observable: a
   fixture per branch of that choice.

**Anti-horizontal-phasing check:** After this slice the next bug fix, attended
or not, is judged against an intact failure record, and a test-edit "fix" is
named as such before it lands.

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
