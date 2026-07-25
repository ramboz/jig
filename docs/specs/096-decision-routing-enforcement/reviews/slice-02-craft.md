---
slice: 096-02 — update-subcommand
pass: craft
verdict: pass
reviewer: jig:reviewer (independent, read-only)
reviewed_at: 2026-07-24T23:45:21Z
prompt_source: review.py pr-review (spec 096, all slices)
---

Independent craft review of spec 096, run read-only over the four commits
without access to the implementation conversation.

**Verdict: FAIL on the first pass — two load-bearing defects. Both reproduced
before fixing, both fixed, both now regression-tested.**

1. **`promote` was broken in every push mode except `--no-push`.** It took
   `adr.py new`'s LAST stdout line as the created ADR's path, but adr.py prints
   the path and then keeps printing (`reserved … on origin/main` on push, the PR
   URL on `--pr`). So the default mode and `--pr` created, committed and PUSHED
   the ADR, then aborted — the exact half-promoted state the ordering exists to
   prevent. Hidden because every e2e test passed `--no-push` and the one
   push-mode test asserted a failure. FIXED: resolve by slug/filename;
   `PromoteDefaultPushModeTests` runs a real default-mode promotion against a
   real bare origin and asserts the ADR landed there. Verified the new test fails
   against the old code.

2. **`_real_entries` had no lower bound on the `## Entries` section**, so the
   last entry's `**Scope:**` absorbed any following `## ` section — and since
   update/promote rewrite exactly that span, the section was DELETED. Reproduced
   (`## Archive` silently removed) before fixing. FIXED: bounded at the next H2,
   and the section start anchored on a real heading line rather than a substring
   find. `EntriesSectionBoundTests` covers parse/update/promote/lint.

3. **A line-initial `### ` in a field value orphaned its entry** — split in two,
   neither half parsed, invisible to update/promote/lint with no error. The
   existing test used INLINE `### `, which the pattern can never match, so it
   asserted a guarantee it did not exercise. FIXED: refused at `render_entry`
   (the shared emitter); the inline test kept and renamed, a real line-initial
   test added.

4. **Marker false positives on exactly the classes the rubric routes here** —
   bare `protocol`, `schema`, `dependency`, `migration`, `replaces` flagged a
   mailto link, a Figma colour schema, an icon swap, an empty-state string. All
   verified, then narrowed: BOUNDARY now holds only qualified phrases (it flags
   with no second signal, so one over-broad member condemns a class), and
   `replaces` is qualified. All seven false positives clear; the three must-flag
   cases still flag.

5. **Weak/vacuous tests** — the locator absence test, the gate-machinery
   assertion, AC1's phrase check, AC5's `assertIn("1", out)`. FIXED; the two
   structural invariants (evaluator call site, self-containment imports) are now
   AST-based and mutation-tested.

6. **Post-`adr.py`-success `OSError` escaped as a traceback.** FIXED: caught and
   reported, naming the possibly-orphaned ADR.

7. **A docstring contradicted the code** on whether entry spans include the
   blank-line separator. Corrected.

Noted as good and deliberately not churned: the ADR-0039 boundary is genuinely
respected and structurally guarded; the e2e tests use real git and real
subprocesses rather than mocks; fixtures are built through `render_entry` and the
false-positive corpus is read from the real shipped file; the code is Python
3.9-clean throughout.
