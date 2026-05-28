---
status: RECONCILED
dependencies: [036-01]
last_verified: 2026-05-28
---

## Slice 036-02 — sweep-and-reconciliation-hook

**Goal:** Apply the policy from ADR-NNNN (landed in slice 036-01) to
the four sweep-able drift instances named in spec 036's "Current state"
table (drifts #1–#4; drift #5 deferred to spec 038 per spec 036's
coordination note), and add a one-line entry to
`skills/spec-workflow/SKILL.md`'s reconciliation checklist that points
to the policy ADR. End-to-end value: every known-drifted artifact is
either corrected or carries an amendment per policy, and future
reconcilers have a named rule to follow when they encounter a new
drift.

**DoR:**

- ✅ Slice 036-01 is DONE; ADR-NNNN is `Accepted` and indexed.
- ✅ The policy ADR's Decision section picks Option A (immutable +
  new ADR/inbox) or Option B (`## Amendments` section) — the chosen
  option determines the *form* of each sweep edit below.
- ✅ The four sweep targets are still live (re-verified at slice
  start; spec 036's 2026-05-26 verification establishes the
  baseline).
- ✅ Drift #5 (README.md Tier-0 count) remains deferred to spec
  038's scope to avoid double-editing.

**Acceptance Criteria:**

1. **Drift #1 corrected per policy** —
   `docs/specs/016-scaffold-mode/spec.md` lines 72, 412, 445, 471.
   Claim "the same five jig hooks" / "all five hook scripts"
   reconciled with the seven-hooks reality (six → seven sweep in
   slice 005-03). Form follows ADR-NNNN: in-body edit + ADR/inbox
   note (Option A) or `## Amendments` entry on spec 016 (Option B).

2. **Drift #2 corrected per policy** — `skills/pr-review/SKILL.md`
   line 14. Claim "jig does not ship an arch-review skill today"
   reconciled with the reality that arch-review shipped in spec
   014. Per spec 036's clarification Q2, SKILL.md prose is in
   scope (it influences router behavior). Form follows ADR-NNNN.

3. **Drift #3 corrected per policy** — `skills/memory-sync/SKILL.md`
   lines 13–14. Claim that slices 002-03 and 002-04 are pending
   reconciled with the status-board reality (both DONE). Form
   follows ADR-NNNN.

4. **Drift #4 corrected per policy** — `docs/workflow.md` line 114.
   Claim that spec-workflow, independent-review, and contracts are
   stubs with `disable-model-invocation: true` reconciled with the
   reality that none carry that flag and all auto-trigger. Form
   follows ADR-NNNN.

5. **Drift #5 explicitly deferred** — deviation log records that
   `README.md` lines 35 and 38 (Tier-0 count "5 (not 100+)" /
   "8-12 skills total") were deliberately NOT touched in this
   sweep; spec 038's tier-reconciliation scope handles them.
   No edit to README.md from this slice.

6. **Reconciliation-hook line added to
   `skills/spec-workflow/SKILL.md`.** One line added to the
   reconciliation checklist (or the equivalent post-implementation
   section): "If reconciliation surfaces a prior closed-spec
   inaccuracy, follow the policy in ADR-NNNN." Wording may vary
   but must (a) name the trigger (reconciliation surfaces a prior
   inaccuracy), (b) name the rule (the policy ADR by number), and
   (c) sit in the reconciliation flow, not the implementation flow.

7. **All four sweep edits comply with the chosen ADR form
   identically.** If ADR-NNNN picks Option B, every sweep edit
   uses the same `### YYYY-MM-DD — <summary>` heading shape. If
   Option A, every sweep edit links to the same kind of follow-up
   artifact (new ADR for permanent decisions, inbox entry for
   transient notes). Inconsistency across the four is itself a
   defect.

**DoD:**

- [x] All ACs pass; full test suite green (no regressions). 1397
      tests, 3 skipped (baseline 1378 → 1397; +19 new tests in
      `scripts/test_closed_spec_drift_sweep.py`).
- [x] Implementer test coverage exercises each AC. For prose-only
      edits, "coverage" means the corrected text is asserted (grep
      / regex / fixture diff) rather than the previous claim.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed. (Compliance pass via
      `review.py implementation`: pass. Craft pass via
      `review.py pr-review`: pass — 4 nits + 3 strengths, no
      blockers. Arch pass skipped: slice frontmatter has no
      `arch_review: true`.)
- [x] Deviation log produced under this slice heading. Must include
      AC #5's explicit deferral of drift #5 to spec 038. (See
      deviation-log item 1 below.)
- [x] Reconciliation review passed. (Verdict: pass — all seven
      deviation-log items verified against the implementation
      files; no silent changes, no overstated claims.)
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. (No decisions deferred;
      condition trivially satisfied.)

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column carries a load-bearing invariant: "Policy ADR-NNNN
      governs closed-spec drift; drift #5 → 038."
- [ ] `CLAUDE.md` hygiene per spec 025-01 rule: this slice closes
      spec 036 (036-01 + 036-02 both DONE; no DEFERRED slices).
      **Compress** spec 036's Active-specs entry — drop facts
      derivable from the spec dir + status board, migrate the
      load-bearing invariant ("ADR-NNNN governs closed-spec drift")
      to the status board Notes column, keep at most a one-liner
      for the cross-cutting fact (the ADR is now the canonical rule).
      No new skill row needed in the Skills table (no new skill
      shipped).

**Anti-horizontal-phasing check:** End-to-end value: every reader of
spec 016, pr-review/SKILL.md, memory-sync/SKILL.md, and
docs/workflow.md sees accurate prose (or an amendment annotated per
policy); every future reconciler sees the one-line hook pointing to
the policy ADR. The slice ships the rule in action; the user-visible
deliverable is "drifted artifacts no longer mislead."

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**1. AC #5 — drift #5 explicitly deferred to spec 038.** Per slice
AC #5, `README.md` lines 35 and 38 ("5 Tier 0 skills (not 100+)" /
"8-12 skills total") were deliberately NOT touched in this sweep.
Drift #5 is owned by spec 038 (tier-reconciliation) to avoid
double-editing the README's Tier-0 line. `scripts/test_closed_spec_drift_sweep.py`
carries a negative-assertion test (`test_readme_not_amended`) that
asserts `README.md` does NOT contain a `## Amendments` section,
making the deferral mechanically enforced for the duration of this
slice.

**2. Scope extension — two-link amendment in drift #1.** The
amendment block on `docs/specs/016-scaffold-mode/spec.md` cites two
causal links (slice 005-03 for six → seven, spec 027 for the prior
five → six step) rather than only slice 005-03. AC #1 strictly
required reconciling the seven-hooks reality; the second link
surfaces full provenance without bloat. The compliance pass flagged
this as a deliberate scope extension worth noting; the craft pass
flagged it as a `[strength]` worth mirroring in future amendments.

**3. Reconciliation-hook gate body slightly longer than siblings
(`[nit]` from craft pass).** The new `**Closed-spec drift**` gate in
`skills/spec-workflow/SKILL.md` spans 6 lines (trigger + ADR link +
default + decision-content carve-out). Sibling gates are 2–3 lines.
Kept as-is: the carve-out line is the load-bearing distinction
between "append amendment" and "write new ADR" — the ADR link does
carry the detail, but inlining the carve-out keeps the gate
actionable without a click-through. Logged here per the block rule;
not blocking.

**4. Test-craft nits (`[nit]` × 3 from craft pass).** Three
test-shape observations on `scripts/test_closed_spec_drift_sweep.py`,
all logged here as deviation-log items, none blocking the REVIEWED
transition:
   - **Literal date assertion in 4 places.** The string `"2026-05-27"`
     is asserted in four per-drift tests. If a future amendment to
     any of the four artifacts is dated differently, the assertions
     rot. Mitigation already present: the `DATE_HEADING_RE` cross-
     artifact test validates ISO shape, which catches the structural
     invariant. Resolution trigger: first test rot on this slice's
     four artifacts.
   - **OR-soup in drift #4 test (lines 154–158).** The
     `"auto-trigger" or "user-invocable" or "no longer" or "do not
     carry"` chain reads as a coverage hedge. Current amendment uses
     all four phrases; the test will not rot under any expected
     edit. Resolution trigger: first test failure traceable to a
     real amendment edit that drops all four phrases simultaneously.
   - **README absence test (lines 165–172).** Asserts no
     `## Amendments` heading in `README.md`. If a future unrelated
     change adds an `## Amendments` to README for any reason, this
     test fails in a confusing way. Acceptable as written for this
     slice — the test is the AC #5 enforcement mechanism. Spec 038
     will add the README Tier-0 amendment and update this test in
     the same slice; document is the trigger.

**5. Strengths flagged for repetition (`[strength]` × 3 from craft
pass).** Patterns worth mirroring in future amendment / sweep slices,
captured here for future reviewers:
   - **Two-link amendment shape** (drift #1 in spec 016): causal
     slice plus related historical step. Surfaces full provenance.
     Future amendments touching a fact that has multiple causal
     steps should adopt this pattern.
   - **`subTest` per file for cross-artifact invariants** (test_closed_spec_drift_sweep.py
     `FormConsistencyAcrossArtifacts`, lines 212–231). Each failure
     identifies which file broke the shape. Reusable for any future
     "same-shape-across-N-files" gate.
   - **Structural gate-ordering test** (test_closed_spec_drift_sweep.py
     lines 194–209, `drift_pos < commit_pos`). Asserts structural
     position rather than literal wording — won't rot when the gate
     prose is polished, but will catch a misplaced gate.

**6. Inbox status.** Inbox already carries the ADR-0008 watch-item
(`[2026-05-28] ADR-0008 watch-item — spec_lint.py … in-body edit
without matching ## Amendments entry`). No new inbox items from
this slice. The 2026-05-26 external-review cluster entry's
coordination note ("036 amendment convention shapes 038/039/040
edits") is realized by this slice — those three downstream specs
now have a worked example to mirror.

**7. Items NOT actioned.**
   - `docs/conventions.md` was not edited. The closed-spec drift rule
     is captured in ADR-0008 and referenced by the new
     reconciliation-checklist gate; no rule-text change to
     `conventions.md` is in scope.
   - No new `TODO` / `FIXME` introduced; no refinement-todo entry
     needed.
