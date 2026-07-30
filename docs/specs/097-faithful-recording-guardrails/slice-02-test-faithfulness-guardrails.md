---
status: DONE
dependencies: []
last_verified: 2026-07-24
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 097-02 — test-faithfulness guardrails

**Goal:** A test that stays green when its feature is removed becomes catchable at
the two cheapest points — the author's Definition of Done and the reviewer's
prompt — so the vacuous-test failure (issue #124 instance 2) is front-loaded
instead of surfacing late across multiple review rounds.

**DoR:**
- ✅ Maintainer approved questions 3 and 4.
- ✅ Target surfaces identified: DoD in `templates/docs/specs/slice-template.md`;
  `build_implementation_prompt` + `build_pr_review_prompt` in
  `skills/independent-review/review.py`.
- ✅ Host-mirror regeneration path known (`scripts/build_host_packages.py`).

**Acceptance Criteria:**

1. **The DoD template asks for mutation evidence (question 3).** The DoD block in
   `templates/docs/specs/slice-template.md` gains a checklist item requiring that
   each new test has been shown to fail when its feature is removed — i.e. the
   test is capable of failing, not vacuously green.
2. **The reviewer prompt asks the vacuous-test question directly (question 4).**
   Both `build_implementation_prompt` and `build_pr_review_prompt` in `review.py`
   emit a line that has the reviewer ask, of the slice's tests, whether each would
   still pass if the feature under test were deleted — flagging any that would.
3. **The prompt lines are covered by a capable test.** `test_review.py` asserts
   the vacuous-test question is present in both prompts, and the assertion is
   shown to fail when the prompt line is removed (dogfooding this slice's own
   guardrail).
4. **The host mirrors match source.** The `hosts/claude/` and
   `hosts/codex/plugins/jig/` mirrors of the slice template and `review.py` are
   regenerated so `python3 scripts/build_host_packages.py --check` passes.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). — 3503 tests,
      `OK (skipped=4)` on Python 3.9, re-run after the rebase onto `main`
      (see deviation-log item 6).
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed in the slice are covered explicitly. — prompt-line tests
      for both builders, plus a DoD-line presence test (added in reconciliation).
- [x] Each new test has been shown to fail when its feature is removed — the test
      is capable of failing, not vacuously green (issue #124 instance 2). —
      mutation-checked: removing each prompt bullet reddens the prompt tests;
      removing the DoD line reddens the DoD-presence test.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed. — compliance `pass`, craft `pass`.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed. — round 1 returned needs-changes (sweep
      overstated the primer-surface and status-board dispositions); sweep
      corrected; round 2 `pass`.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred during
      implementation. — none deferred; no-op.

**Notes:** Keep each prompt addition short — `review.py`'s prompt blocks are held
under explicit size budgets (see `_principles_check_block` / `_practices_check_block`
docstrings). The DoD line and the prompt line are the author-side and
reviewer-side halves of the same check; they ship together so neither asserts a
catch-point the other lacks. The DoD template edit is the same wording added to
this spec's own slice DoDs — a deliberate dogfood.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **No deviation from the planned shape.** All four ACs implemented as
   specified: a DoD mutation-evidence line in `slice-template.md`, a
   `Vacuous-test check` bullet in both `build_implementation_prompt` and
   `build_pr_review_prompt`, a whitespace-normalized anchor test, and
   regenerated host mirrors.
2. **Test robustness (chosen, not deviated).** The prompt-line test asserts its
   anchor against whitespace-normalized text so source line-wrapping cannot
   silently make the assertion vacuous — caught during implementation when the
   first assertion failed purely on a mid-phrase line-wrap.
3. **Reviewer finding folded in (craft nit).** The craft pass noted the DoD
   mutation-evidence line shipped without a presence test — "mildly ironic for a
   test-faithfulness slice." Added `test_slice_template_dod_asks_for_mutation_evidence`
   in `test_workflow.py`, scoped to the DoD block (not a whole-file token match),
   and mutation-verified.
4. **Bug-review prompt deliberately untouched.** The vacuous-test bullet was not
   added to `build_bug_review_prompt`: that prompt already carries an equivalent
   "regression test fails without the fix" check. Scoping to the two named
   prompts is intentional, not an omission (per the craft reviewer).
5. **DoD parenthetical differs by design.** The template's DoD line ends
   "(mutate the feature, watch the test go red, restore)" — a more actionable
   instruction — while this spec's own slice DoDs cite "(issue #124 instance 2)".
   Same substance, tailored trailing clause.
6. **Post-review corrections from PR review of [#135](https://github.com/ramboz/jig/pull/135)
   (recorded, not silently swapped).** Three changes landed after the recorded
   review passes; none touches an AC or a shipped guardrail's wording:
   (a) rebased onto `main` (spec 096 had landed) and regenerated
   `docs/specs/README.md` with `workflow.py status-board` rather than
   hand-merging the generated table; (b) the status-board Notes column now
   carries this spec's two "don't re-argue" invariants for both slices — the
   `Accepted`-only scoping (question 2 was declined) and the deliberate absence
   from `build_bug_review_prompt` — which the 097-02 sweep had left with no
   durable home once `CLAUDE.md` was correctly a `no-op`; (c) the DoD
   test-suite-count evidence above was **3502**, the count before this slice's
   own reconciliation added the DoD-presence test. Corrected to the re-run
   figure (3503, `OK (skipped=4)`, Python 3.9) rather than left stale — the
   number was understated, not the greenness.
7. **Prompt-line tests relocated (post-review, mutation re-verified).** The two
   vacuous-test assertions were a standalone `VacuousTestPromptTests` class that
   re-declared setup, teardown, module-import and temp-repo helpers already
   present four times over in `test_review.py`. They now live in the existing
   `ImplementationPromptTests` and `PrReviewPromptTests` classes (which build
   the same two prompts through the CLI), with the anchor and the
   whitespace-normalizer hoisted to module level as `VACUOUS_TEST_ANCHOR` /
   `normalize_ws`. Behaviour-preserving and re-mutation-checked after the move:
   removing the bullet from one builder reddens **only** that builder's test, so
   the two are not covering for each other. Structural change only — it landed
   after the recorded compliance/craft passes, so this note plus the re-run
   mutation evidence stands in for a fresh review round.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door unaffected. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` at close-out (after the rebase onto `main`), and the Notes column filled for both 097 rows — see deviation-log item 6. Regen verified idempotent, so the Notes survive the next one. |
| `docs/product-vision.md` | `no-op` | No behaviour / scope drift. |
| `docs/architecture.md` | `no-op` | No module-boundary / public-contract change — additive prompt/doc text, no logic. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | Only the scaffold `templates/docs/specs/slice-template.md` DoD gained the mutation-evidence line (host mirror regenerated). `CLAUDE.md` / `AGENTS.md`: `no-op` — spec 097 was implemented end-to-end on one branch and never had an Active-specs entry, so there is nothing to compress. |
| `skills/independent-review/review.py` + host mirrors | `updated` | Vacuous-test bullet added to both prompt builders; mirrors regenerated, drift-guard green. |
| `docs/inbox.md` | `no-op` | No items resolved by this slice. |
| `docs/refinement-todo.md` | `no-op` | No resolved items; no new deferrals. The craft reviewers' "review→learnings→clarify loop" note is a pre-existing tracked item, unchanged. |
| `docs/memory/**` | `no-op` | No new domain term or learning worth persisting. |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR — maintainer's decision, recorded in the spec. |

**Anti-horizontal-phasing check:** After this slice lands, a slice author is asked
to prove each test can fail, and both review passes ask the reviewer directly
whether a test would survive deleting its feature — the vacuous-test failure is
catchable at both cheap points, end-to-end.
