---
status: RECONCILED
dependencies: []
last_verified: 2026-10-05
claimed_by: sdd-adoption-review
---

## Slice 118-01 -- author-to-review

**Goal:** Authors can make state-dependent behavior and preserved user journeys
explicit, run a reproducible scenario, and give an independent reviewer
checkable observations without adding ceremony to unrelated slices.

**DoR:**
- Existing slice template, clarify taxonomy, and compliance prompt inspected.
- Owner approved the bounded pilot and implementation through jig's ceremony.
- Work stays in this worktree. The owner authorized network prechecks and
  explicitly selected complete local ceremony authorization on 2026-10-05.
  No push, merge, PR, or gate bypass is authorized. The owner separately approved
  a test-process-only bare-fixture setting; persistent Git settings stay unchanged.

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

**Preconditions:** Python 3, Git, repository helpers, and a helper-owned temporary
fixture. The scenario uses no remote access or production credentials.

**Invocation:** Follow the packaged worked example; run targeted source tests
and `python3 scripts/build_host_packages.py --check`.

| Step | AC | Expected observation | Observed | Outcome | Evidence |
|------|----|----------------------|----------|---------|----------|
| 1 | 7 | Real progress CLI reports fixture counts | UC-1 reports `1/2 slices done`; CLI exits 0 | pass | [scenario.json](verification/scenario.json), step 1 |
| 2 | 7 | Fixture bytes unchanged after CLI execution | File paths and bytes compare equal (`unchanged: true`) | pass | [scenario.json](verification/scenario.json), step 2 |
| 3 | 1-6, 8 | Targeted tests exercise authoring and generated prompts | All 347 selected tests pass, including the executed example | pass | [checks](verification/checks.md), [TDD excerpts](verification/tdd.txt) |
| 4 | 9 | All three committed packages match generated source | `build_host_packages.py --check` exits 0 | pass | [checks](verification/checks.md) |
| 5 | 9 | Repository suite and type-check gate pass | Approved fixture-compatible run: 5065 tests, `OK (skipped=8)`, pyright clean, exit 0 | pass | [checks](verification/checks.md) |

**Preserved behavior:** progress stays read-only, legacy slices need no new
fields/sections, and design attestation is unchanged.

**Code revision / dirty-change identity:** Implementation
`7a04ff595769a86bcb51ba3dc5bd96c1969ff971`; runtime sources unchanged at execution.
[scenario.json](verification/scenario.json) records the per-file runtime manifest
and `runtime-sha256:fb26e69aba1c26e826883e041fe9d21f4b2bc006fc4764881e26f4ea36e3c6bc`.
Subsequent edits are ceremony records, not runtime deliverables.

**DoD:**
- [x] Functional ACs pass; the narrow AC8 sequencing deviation is explicitly
      recorded and independently accepted; full test suite green.
- [x] Implementer tests exercise each executable/surface AC meaningfully.
- [x] Original planned behavior witnessed red before implementation and green
      afterward; the late supplemental guard's sequencing exception is recorded,
      without claiming retroactive chronology.
- [x] Reviewed by fresh read-only reviewers using `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] Deferred decisions assessed; no new load-bearing decision or separate
      feature was deferred by this bounded pilot.

### Close-out (post-DONE)

- [ ] Status board regenerated and checked.
- [ ] Primer surfaces checked; no active-spec residue for this completed pilot.

**Anti-horizontal-phasing check:** A spec author gets a complete optional
contract-to-runtime-evidence-to-independent-review path in one slice.

### Deviation log (after reconciliation)

Implementation and review history:

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
   expected manifest and digest. At the first pause the updated scenario test
   had not run; it subsequently passed in the authorized 347-test selection.
4. **Permission boundary.** Remote fetching, a manual readiness-review file,
   direct scenario execution/evidence, and a Git file-protocol override were
   denied. No override was applied. Local lifecycle transitions ran with all
   Git transports blocked, reporting unavailable remote freshness honestly.
   The number is provisional; no push, PR, merge, or remote reservation occurred.
5. **First paused close-out.** The full suite was stopped to honor the denied
   scenario execution. Per-step observations above remain not-run and no
   gated review verdicts are recorded. The existing evidence gates stay armed;
   IN_PROGRESS was retained until authorized verification and reconciliation.
6. **Authorized resumption (2026-10-05).** The owner explicitly selected complete
   local ceremony authorization. Fresh remote prechecks succeeded; `origin/main`
   had zero commits absent from this branch. The actual CLI and preservation
   scenario now have passing recorded outcomes, and all 347 targeted tests pass.
   Package drift, spec lint, and board audit passed. The full suite executed
   5065 tests in 501.756s with 5 failures, 26 errors, and 8 skips; pyright passed.
   A temporary bare-repository probe reproduced the inherited command-line
   `safe.bareRepository=explicit` restriction (`git config` exits 128).
   That initial run's result remains recorded, not erased.
7. **Recovered validation.** The owner then approved the test-process-only
   `safe.bareRepository=all` setting with "Do it". The runner appended only that
   entry to its copied environment; no persistent setting or file-protocol
   policy changed, and the parent still reports `explicit`. All 56 previously
   failing fixture selectors passed, followed by the complete 5065-test suite
   (`OK`, 8 skipped) and clean pyright. After permissions were relaxed, an
   isolated copied-runtime sensitivity check also passed: a dependency edit
   changed the identity, while a constant-digest mutant was rejected by the
   existing assertion. Repository source was untouched.
8. **AC8 sequencing exception.** The supplemental runtime-manifest guard was
   added after its implementation, unlike the original planned behavior's
   red/green loops. The orchestrator accepts this as a narrow, recorded process
   deviation for independent review/reconciliation, backed by actual independent
   assertions and mutant rejection. No pre-implementation chronology is claimed
   for it, no original AC is rewritten, and no functional requirement or future
   test-first policy is weakened.
9. **Compliance recovery.** The fresh reviewer initially recorded needs-changes
   for the full-suite failure and the late test chronology. The initial verdict
   is preserved in `verification/compliance-initial.md`. After the passing full
   suite, independent mutant evidence, and explicit deviation disposition, the
   same reviewer accepted the narrow historical process exception and returned
   pass, without claiming test-first chronology for the late guard.
10. **Craft review.** A fresh craft reviewer returned pass with no blockers.
    Its claimed manifest omission was checked against the actual JSON: all
    three named modules are present, and an independent audit matches all 19
    runtime files and the aggregate identity. No refresh is needed. The
    section-localization observation is accepted as nonblocking: current
    authoring steps remain on the correct hot path, and no required behavior or
    test is removed. Real CLI preservation and independent digest assertions
    are retained as strengths.
11. **Scope and leanness.** No new gate, runner, skill, schema, authentication
    mechanism, architectural boundary, or persistent Git setting was added.
    Conventions, accepted ADRs, closed records, and existing design attestation
    remain untouched. Memory-sync judgment identified no additional settled
    domain decision worth persisting; no unrelated memory inventory was run.
12. **Reconciliation sweep recovery.** The independent reconciliation reviewer
    requested explicit dispositions for this spec's records, the canonical test
    and worked example, the root README, and the ADR index. The grouped sweep
    below now names each canonical artifact and gives a checked rationale;
    no implementation expansion or unrelated document correction was needed.
    A fresh, focused recovery reviewer returned pass with the accounting issue
    resolved. The original non-clearing verdict is preserved in
    `verification/reconciliation-initial.md`; the recovery verdict is recorded
    via the helper before any terminal state is entered.

### Reconciliation sweep

Checked dispositions before the independent reconciliation review:

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `templates/docs/specs/slice-template.md`; `skills/spec-workflow/SKILL.md`; `skills/clarify/SKILL.md`; `skills/independent-review/review.py` | updated | Optional rule/scenario guidance and compliance-only review nudge; no new gate or schema. |
| `skills/spec-workflow/test_behavioral_verification.py`; `skills/spec-workflow/worked-example-behavioral-verification.md` | updated | New canonical regression coverage and executable example shipped; current bytes match the tested implementation revision. |
| `docs/specs/118-behavioral-verification-pilot/{spec.md,plan.md,tasks.md,slice-01-author-to-review.md}` | updated | The new spec/plan define the bounded pilot; tasks and slice record track observed implementation, validation, exceptions, and lifecycle progress without rewriting the ACs. |
| `docs/workflow.md`; `templates/docs/workflow.md.template` | updated | Proportional usage documented; source package guidance names all three hosts. |
| Root `README.md` | no-op | Front-door workflow and existing skill/install surface remain accurate for this optional extension; no new skill, tier, installation path, or required artifact was introduced. Unrelated old wording is outside this slice. |
| `hosts/` | updated | Generated from canonical source, never hand-edited. |
| `docs/specs/README.md` | updated | Regenerated from the open slice record; regenerate and audit again after gated closure. |
| Vision, architecture, conventions, accepted ADRs, closed specs | no-op | No product/module-boundary change or record amendment; conventions were not edited. |
| `docs/decisions/README.md` (ADR index) | no-op | No new or superseding ADR was created; the pilot adds no load-bearing architecture choice requiring an index entry. |
| Primer surfaces | no-op | No new skill or active-spec entry introduced; closure has no new primer residue to remove. |
| Memory, inbox, refinement queue | no-op | No settled new decision or unrelated follow-up recorded; memory status checks were outside the requested scope. |
| This spec's `verification/` records | updated | Actual CLI outcomes, runtime manifest, TDD excerpts, passing full-suite result, original environment failure, and isolated mutant observations recorded honestly. |
| This spec's `reviews/` records | updated | Genuine compliance, craft, and reconciliation recovery verdicts recorded via the helper; original non-clearing snapshots retained in `verification/`. |
| Gated terminal transition and post-DONE checks | deferred | Follow the independently cleared reconciliation with real RECONCILED/DONE transitions, board audit, and local commits; these future actions are not pre-ticked. |
