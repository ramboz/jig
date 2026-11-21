---
status: DONE
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
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [x] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
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

1. **Polarity changed after the frame critique.** The first draft kept every
   non-zero status other than 2 as red ("backward compatibility"). The ADR's
   round-1 frame critique showed that fails open on the conventional
   could-not-run statuses (126/127, signals) every shell wrapper produces, so
   the rule became "only 1 is red" (ADR-0068 §2, Option F rejected). AC1/AC2
   test 2, 3, 101 and 127.
2. **`slice-land` brought in scope (frame critique, round 1).** `land.py
   check_tests` mapped every `tdd.py run` exit 2 to the non-blocking doc-only
   `warn`; the new contract would have opened the land gate. Added the
   `could_not_run` status (spec D4), `tests_block()`, a blocker line and a
   loud readiness row. The row quotes `tdd.py`'s last stderr line. That
   detail is carried in a module-level `_could_not_run_detail` set by
   `check_tests`, so its `(status, exit_code)` return (unpacked by callers
   and tests) is unchanged; the craft review called this hidden state and
   suggested a wider return. Kept, with the trade-off in a code comment.
3. **`tdd.py`'s own failure paths (frame critique, round 2).** AC6a added: an
   unparsable `.jig/test-command`, undecodable command output
   (`errors="replace"`) and an uncaught exception in the helper now exit 2;
   the catch-all used to return 1, which `bug.py` would read as red.
4. **A blank `.jig/test-command` counts as a declared runner in `land.py`**
   (frame critique, round 3). `tdd.py detect` skips a blank or comment-only
   file while `run` exits 2 on it, so it reached `land.py` as the doc-only
   warning. `land.py` now treats the file's presence as runner intent, so it
   and `detect` classify that file differently. The row says "detected or
   declared".
5. **Not changed, by decision:** the `REVIEWED` green check still routes any
   non-zero exit, including an environment error, back to `DIAGNOSING`
   (bug 043, ADR-0016 back-edge pinned by a bug 021 test); the built-in
   runner paths still read a load failure as red (bug 042). Both were found
   here and filed, per the owner's instruction not to fix them in this spec.
6. **The "fix" advice in the message.** The draft ADR suggested
   `sh -c "make test || exit 1"`. The frame critique showed that turns a build
   failure back into red. The contract line now says exit 1 must mean a test
   ran and failed, and a test asserts it carries no `||` advice.
7. **Review findings folded in after the implementation reviews.** Compliance
   round 1 (`needs-changes`): the servo-silence test could pass without the
   feature (now uses the servo-marker fixture), no `prepare()`-level verdict
   test (added `test_prepare_could_not_run_is_not_go`), a stale docstring
   (fixed), the row wording (reworded), an unquoted interpreter path in a
   fixture (quoted). Each new test was mutation-checked: removing
   `could_not_run` from the servo silent tuple, or reverting `has_blocker` to
   `test_status == "red"`, turns it red. Craft (`pass`) nits: the AC label in
   a comment and the same docstring, both fixed; the redundant
   `except (FileNotFoundError, OSError)` is pre-existing and left alone.
8. **Compliance round 2 (`needs-changes`).** The pytest-module-missing edge
   case had no test; added
   `test_pytest_detected_but_module_missing_is_could_not_run` (a shadowing
   `pytest.py` that raises `ImportError`, so it holds on machines with
   pytest installed). Recorded per its notes: `_run_streaming`'s
   `errors="replace"` also covers targeted runs of the built-in runners, not
   only custom commands; the `OSError` catch on the custom launch paths is
   pre-existing.
9. **Behaviour change for existing projects (spec D4).** A detected runner
   that exits 2 now blocks `slice-land` where it used to be the doc-only
   warning. Built-in cases included: the pytest module missing (for example
   a unittest-only repository with `test_*.py` files, which `tdd.py`
   detects as pytest) and a runner binary missing. The row quotes the
   reason; the ways out are installing the runner or a `.jig/test-command`.
   Called out in the PR body.
   Compliance round 3 passed; per its notes the blocker line now also says
   "detected or declared", and AC5's no-`{test}` refusal is covered by the
   existing bug 021 test (`test_selector_without_placeholder_is_refused_exit_2`),
   not a new Spec123 test.
10. **Red before green.** The 123-01 tests in `test_tdd.py` and `test_bug.py`
   were written first and failed (6 tdd failures/errors, 1 bug failure)
   before `_custom_exit` existed; the land tests failed (2 failures, 2 errors)
   before `could_not_run` existed. Mutation check: making `_custom_exit`
   return 1 for any other status turns 19 Spec123 assertions red.

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Checked: the front door names `tdd-loop` but states no runner list or exit contract. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/architecture.md` | `no-op` | Checked: lists `tdd.py` / `land.py` as helpers only; no exit contract or runner list to correct. Module boundaries unchanged. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | `CLAUDE.md` is left alone to keep the primer byte budget (spec 122-03 precedent); the per-slice invariants go to the status-board Notes column. The scaffold template change belongs to slice 123-02. |
| `docs/inbox.md` | `no-op` | Checked: no parked item about runners or the test command. |
| `docs/memory/**` | `no-op` | Checked: the glossary has no runner-list entry. The durable facts live in ADR-0068 and the tdd-loop SKILL.md. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0068 added and accepted; index regenerated by `adr.py index`, `check-index` clean. |
| `docs/bugs/**` | `updated` | Bugs 042 (built-in runners read a load failure as red) and 043 (`REVIEWED` reopens on an environment error) filed; board regenerated, `check-board` clean. |
| Generated host packages (`hosts/**`) | `updated` | Rebuilt by `scripts/build_host_packages.py`; `--check` clean. |
| `docs/product-vision.md` | `no-op` | Changed by 123-02 (the out-of-scope line), not by this slice. |
| `docs/refinement-todo.md` | `no-op` | No decision deferred by this slice; the JUnit-XML reader entry belongs to 123-02. |
| `skills/slice-land/SKILL.md` / `land.py` module docstring | `updated` | Test-check warnings section and readiness-check list describe the `could_not_run` blocker. |
| Additional live prose | `no-op` | `skills/bug-fix/SKILL.md` already said exit 2 fails closed at `FIXING`; its no-runner text belongs to 123-02. |
| `skills/tdd-loop/SKILL.md` | `updated` | AC9: exit-code list and the custom-command contract gotcha. The same file's policy text belongs to 123-02 (see its sweep). |
| Tests: `skills/tdd-loop/test_tdd.py`, `skills/slice-land/test_land.py`, `skills/bug-fix/test_bug.py` | `updated` | The exit-contract, land-gate and `FIXING`-gate tests (deviation items 7, 8 and 10). |
| Files in `87610a93..HEAD` not changed by spec 123 | `no-op` | None: `git diff --name-only 87610a93...HEAD` lists only spec 123 files, ADR-0068, bugs 042/043, the boards and the generated `hosts/` copies. Files a reviewer sees against a stale local `main` (spec 122, bug 041, `CHANGELOG.md`, manifests, `agents/reviewer.md`, `docs/conventions.md`) are base drift; `docs/conventions.md` is not modified. |
