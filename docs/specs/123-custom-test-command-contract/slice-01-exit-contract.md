---
status: IN_PROGRESS
dependencies: []
last_verified: 2026-11-20
kind: feature
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
# design_review: true  # set true when this slice's fidelity must be a HARD
#                      # gate: extract the mockup's design values (colours,
#                      # spacing, sizes, layout rules) into this slice's ACs,
#                      # then wire a servo `design-eval` as the done-condition
#                      # (attest-only at REVIEWED; ADR-0014, ADR-0022,
#                      # ADR-0049).
claimed_by: claude/xenodochial-tu-c3ef9e
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 123-01 — exit-contract

**Goal:** for a custom test command (`.jig/test-command`), only exit 1 is read as a failing test; every other non-zero exit is reported by `tdd.py run` as an environment error (exit 2). A project wrapper can then refuse to vouch for a run, and neither the bug-fix `FIXING` gate nor `slice-land` treats "could not run" as a result. (Whether a command's exit 1 is honest stays the command's responsibility; the `REVIEWED` green check is bug 043.)

**Decision:** [ADR-0068](../../decisions/adr-0068-no-per-framework-runner-adapters.md) §2; spec 123 D1 and D4.

**DoR:**
- ✅ ADR-0068 drafted with the contract and the backward-compatibility consequence.
- ✅ `cmd_run`'s two custom branches read (`skills/tdd-loop/tdd.py`, `return 0 if returncode == 0 else 1` in both).
- ✅ `bug.py`'s `FIXING` gate already refuses a `tdd.py` exit 2 with "not evidence of red" and quotes the last stderr line (`_tdd_failure_detail`).
- ✅ `tdd.py`'s other consumer read: `skills/slice-land/land.py` `check_tests` runs `tdd.py run <target>` (whole suite) and maps exit 2 to the non-blocking `warn`; only `red` blocks (`has_blocker`). Found by this slice's frame critique.

**Assumptions:** None beyond the spec's.

**Acceptance Criteria:**

1. **Selector branch.** With a `.jig/test-command` that contains `{test}`, `tdd.py run <target> --test <selector>` exits 2 when the command exits 2, 3, 101 or 127.
2. **Whole-suite branch.** The same statuses give exit 2 from `tdd.py run <target>` (no selector).
3. **The message names the contract.** In both branches the last stderr line is a single line of at most 300 characters that names the status the command exited with, names `.jig/test-command`, says it is an environment error and not a failing test, and says that exit 1 must mean a test ran and failed. It does not advise a blanket `|| exit 1`.
4. **0 and 1 are unchanged.** Exit 0 → 0 and exit 1 → 1 in both branches.
5. **Earlier refusals are unchanged.** A selector against a command with no `{test}` token still exits 2 with the bug 021 message; an exit 1 with a recognized no-match line still exits 2 with `unresolved selector`.
6. **The bug-fix gate does not accept it.** `bug.py transition <id> FIXING` on a project whose custom command exits 2 fails with the "not evidence of red" error, the error quotes the `tdd.py` contract line, the record's status stays `ROOT_CAUSED`, and `red_confirmed_at` is not stamped. A custom command that exits 1 still enters `FIXING`. Both run the real `tdd.py`, not a stub helper.
6a. **`tdd.py` does not answer 1 for its own failures.** An unparsable `.jig/test-command` (unbalanced quote) exits 2 with a message naming the file, in both branches; command output that is not valid UTF-8 does not crash a targeted run; an uncaught exception inside `tdd.py` exits 2, not 1.
7. **`slice-land` blocks on "could not run".** `land.py check_tests` returns a status distinct from `warn`, `red` and `not_run` when `tdd.py run` exits 2 **and** `tdd.py detect` finds a runner. The readiness report renders it as tests that could not be run and not as a pass, without the doc-only wording, and it is a blocker (the verdict is not GO). The row quotes `tdd.py`'s last stderr line, so the reason and the pointer to `.jig/test-command` reach the operator. The servo suggestion stays silent for this status, as it does for `warn` and `not_run`. Checked against the real `tdd.py` with a custom command that exits 2.
8. **The doc-only warning is unchanged where it is true.** With no runner detected, `check_tests` still returns `warn`, the row keeps its wording, and it does not block.
9. **The contract is documented** in `skills/tdd-loop/SKILL.md` (the custom-command gotcha and the exit-code list) and the land gate's new row in `skills/slice-land/SKILL.md`.

**Edge cases to cover explicitly:**
- A command that exits 2 **and** prints a no-match line: exit 2 either way; the contract line is reported (the exit code is checked first).
- A command killed by a signal (negative return code) is an environment error. (A regression test whose honest red *is* a crash needs a wrapper that maps that crash to 1; the recipes document says so.)
- A `.jig/test-command` that exists but is blank or all comments is skipped by `tdd.py detect` while `tdd.py run` exits 2 on it; `slice-land` treats the file's presence as a declared runner, so this is "could not run", not the doc-only warning.
- The `REVIEWED` green check is a third read site and is **not** changed: any non-zero exit, including an environment error, still routes the bug back to `DIAGNOSING` and makes recorded verdicts stale. That is wrong for an environment error and is tracked as [bug 043](../../bugs/043-reviewed-gate-env-error-reopens-bug.md); it is bug-lifecycle behaviour (ADR-0016) pinned by a bug 021 test, so it gets its own diagnosis.
- A project detected as pytest whose pytest module is missing (for example a unittest-only project with `test_*.py` files) moves from the doc-only warning to a land blocker. The row quotes `tdd.py`'s reason ("pytest module is not installed"); the ways out are installing pytest or a `.jig/test-command`.
- Built-in runners that already exit 2 with a runner present (for example the pytest module missing) now block `slice-land` too; that is intended (spec D4).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

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

**Anti-horizontal-phasing check:** after this slice a project's wrapper script can exit 2, the `FIXING` gate refuses to treat the run as a failing test, and `slice-land` refuses to land on it.

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
