---
status: IN_PROGRESS
dependencies: []
last_verified:
claimed_by: sdd-adoption-review
---

## Slice 118-01 -- author-to-review

**Goal:** Authors can make state-dependent behavior and preserved user journeys
explicit, run a reproducible scenario, and give an independent reviewer
checkable observations without adding ceremony to unrelated slices.

**DoR:**
- Existing slice template, clarify taxonomy, and compliance prompt inspected.
- Owner approved the bounded pilot and implementation through jig's ceremony.
- Work stays in this worktree; Git network transports are disabled for lifecycle
  commands because remote access was not authorized.

**Acceptance Criteria:**

1. **Optional rules shape.** The slice template offers a behavioral rules table
   with stable rule ID, operation/control, actor, state/precondition, outcome
   (allowed/blocked/hidden or concrete response), rationale, and owning AC.
   Guidance scopes it to stateful/role-dependent behavior and permits omitting
   it or linking an existing contract; no frontmatter field or gate is added.
2. **Traceability, not competing authority.** Authoring and template guidance
   state that IDs do not encode precedence, conflicting rules/ACs are surfaced
   for explicit resolution, and a demo cannot silently override the owning ACs.
   External sources, when used, carry an authority and revision reference.
3. **Scenario shape.** The template offers an optional verification scenario:
   preconditions/environment/fixtures, reproducible invocation or tool steps,
   AC-linked expected observations, and existing behavior to preserve.
   It accommodates CLI, service, and UI projects without requiring a new runner.
4. **Honest evidence.** The template and authoring guidance ask for actual
   per-step observations and pass/fail/not-run/environment-error outcomes,
   evidence references, and the exercised code revision plus dirty-change
   identity when relevant. Not-run/environment-error is not a pass; required
   verification cannot be declared complete without adequate evidence.
5. **Reachable clarification.** `clarify`'s existing six-category scan checks
   role/state-dependent outcomes, negative/preservation paths, reference
   authority conflicts, and scenario environment/testability where applicable.
   It keeps the existing question cap and taxonomy, does not demand optional
   tables from every spec, and adds no new skill.
6. **Bounded compliance review.** The generated implementation-review prompt
   checks supplied rules and scenarios for AC alignment, preserved behavior,
   observed outcomes, revision applicability, and honest unavailable-environment
   reporting. Missing optional sections alone are not blockers. Its new
   guidance is at most 1,400 characters; craft, frame, reconciliation, and
   design-review prompts do not inherit this new block.
7. **Worked example and dogfood.** A packaged jig-native worked example links
   rules and scenario steps to ACs, runs the actual `workflow.py progress` CLI
   on an isolated fixture, and checks both a positive outcome and preserved
   read-only behavior. This slice records its actual step outcomes. The example
   does not fabricate reviewer verdicts or claim to exercise live host hooks.
8. **Preserve existing rails.** Existing slices without the optional sections
   still build review prompts and follow unchanged lifecycle evidence rules.
   Existing `design_review` attestation remains unmodified. Tests exercise the
   new template/skill surfaces, generated compliance prompt, and unchanged
   non-compliance prompts; new tests are witnessed red before implementation.
9. **Ship every host and document proportionally.** Update directly related
   workflow documentation and regenerate all three host packages. Package drift
   check, spec lint, targeted tests, and the repository suite pass. Neither
   conventions nor accepted/closed records are rewritten.

### Behavioral rules

| Rule | Operation | Actor | State/precondition | Outcome | Rationale | AC |
|------|-----------|-------|--------------------|---------|-----------|----|
| BR-1 | Author rules | Slice author | State/role-dependent outcomes | Optional table or existing contract link | Expose implicit behavior | 1, 2 |
| BR-2 | Review scenario | Compliance reviewer | Required runtime evidence is missing or environment unavailable | No verified-pass claim for that AC | Execution must be observed | 4, 6 |
| BR-3 | Review ordinary slice | Compliance reviewer | Optional sections absent | No blocker solely for absence | Keep proportional ceremony | 6, 8 |

### Verification scenario

**Preconditions:** Python 3, repository helpers, isolated fixture under the
session artifacts directory, no remote access or production credentials.

**Invocation:** Follow the packaged worked example; run targeted source tests
and `python3 scripts/build_host_packages.py --check`.

| Step | AC | Expected observation | Observed | Outcome | Evidence |
|------|----|----------------------|----------|---------|----------|
| 1 | 7 | Real progress CLI reports fixture counts | Pending | not-run | Pending |
| 2 | 7 | Fixture bytes unchanged after CLI execution | Pending | not-run | Pending |
| 3 | 1-6, 8 | Targeted tests exercise authoring and generated prompts | Pending | not-run | Pending |
| 4 | 9 | All three committed packages match generated source | Pending | not-run | Pending |

**Preserved behavior:** progress stays read-only, legacy slices need no new
fields/sections, and design attestation is unchanged.

**Code revision / dirty-change identity:** Record the implementation commit and
any subsequent diff with the observations before closing this slice.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer tests exercise each executable/surface AC meaningfully.
- [ ] New tests witnessed red before implementation and green afterward.
- [ ] Reviewed by a fresh read-only reviewer using `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] Deferred decisions assessed; any real follow-up recorded proportionally.

### Close-out (post-DONE)

- [ ] Status board regenerated and checked.
- [ ] Primer surfaces checked; no active-spec residue for this completed pilot.

**Anti-horizontal-phasing check:** A spec author gets a complete optional
contract-to-runtime-evidence-to-independent-review path in one slice.

### Deviation log (after reconciliation)

Implementation notes so far; reconciliation is not complete:

1. **Execution ownership.** The implementer agent refused the initial
   IN_PROGRESS handoff because its contract requires READY_FOR_IMPLEMENTATION.
   The parent returned the untouched slice to readiness, confirmed it, then
   performed the implementation with witnessed red/green tests. The sync agent
   could not accept a follow-up message; no duplicate implementer was launched.
2. **Validation so far.** The first rules loop witnessed three failures and
   then three passes. The scenario loop witnessed seven failures (after fixing
   an invalid reconciliation-test invocation) and then a combined 346-test
   pass. The latest permitted source/prompt-only selection also passed 346
   tests, explicitly excluding scenario execution. All three packages were
   regenerated; their drift check, this spec's lint, and whitespace checks
   passed. These are partial checks, not a full-suite result.
3. **Review refinements.** The worked example now fingerprints `_common`
   runtime sources as well as `workflow.py`, rather than missing dirty
   dependency edits. The example explicitly requires the Git executable (not
   a Git checkout), and its executable test independently recomputes the
   expected manifest and digest. The latest scenario test has not been run:
   its execution remains blocked.
4. **Permission boundary.** Remote fetching, a manual readiness-review file,
   direct scenario execution/evidence, and a Git file-protocol override were
   denied. No override was applied. Local lifecycle transitions ran with all
   Git transports blocked, reporting unavailable remote freshness honestly.
   The number is provisional; no push, PR, merge, or remote reservation occurred.
5. **Closure remains blocked.** The full suite was stopped to honor the denied
   scenario execution. Per-step observations above remain not-run and no
   gated review verdicts are recorded. The existing evidence gates stay armed;
   IN_PROGRESS is intentional until authorized verification and reconciliation.

### Reconciliation sweep

Provisional sweep; not a reconciliation verdict:

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| Source template and authoring/clarify/compliance surfaces | updated | Optional rule/scenario guidance and compliance-only review nudge; no new gate or schema. |
| `docs/workflow.md` and workflow template | updated | Proportional usage documented; source package guidance names all three hosts. |
| `hosts/` | updated | Generated from canonical source, never hand-edited. |
| `docs/specs/README.md` | updated | Regenerated for this open local slice; must be checked again before integration. |
| Vision, architecture, conventions, accepted ADRs, closed specs | no-op | No product/module-boundary change or record amendment; conventions were not edited. |
| Primer surfaces | no-op | No new skill or active-spec entry introduced; closure has no new primer residue to remove. |
| Memory, inbox, refinement queue | no-op | No settled new decision or unrelated follow-up recorded; memory status checks were outside the requested scope. |
| Runtime evidence and gated review records | deferred | Owner authorization is required after the denied writes/execution; no pass is inferred. |
