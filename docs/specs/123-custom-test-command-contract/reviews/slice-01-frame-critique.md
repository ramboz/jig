---
slice: 123-01 — exit-contract
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-20T21:59:11Z
prompt_source: review.py frame-critique docs/specs/123-custom-test-command-contract/spec.md exit-contract docs/specs/123-custom-test-command-contract/slice-01-exit-contract.md
---

VERDICT: pass

REASONING:
Round 3 (rounds 1 and 2 returned needs-changes; their findings were folded into the slice, spec 123 and ADR-0068 before this round). The frame rests on one assumption: a custom command's exit status alone can carry three states, with 1 as the only trusted red, and every reclassified status fails closed wherever `tdd.py run` is read. The strongest attack (a fail-open read site, or a status that becomes more permissive) did not land: only `bug.py` and `land.py` shell to `tdd.py`, and all read sites refuse or block on exit 2. That exit 1 is also the commonest generic-failure status is real, but ADR-0068 discloses it and its kill criteria cover it.

SPECIFIC ISSUES:
- Primary — "only exit 1 is red" is sound enough and its blast radius acceptable; asserted rather than evidenced on two points (notes, not blockers): no installed-base evidence of how many existing `.jig/test-command` users run `make test` / `cargo test` / count-exit runners (the change fails closed, so being wrong costs friction, not unsoundness); and a crash-class regression test (segfault, abort, OOM) whose honest red is a 134/139/negative status cannot enter `FIXING` without a wrapper mapping the crash to 1.
- Secondary — `tdd.py detect` does not cleanly split exit 2: a `.jig/test-command` that exists but is blank or comment-only is skipped by `detect_runner` while `cmd_run` exits 2 on it, so it reached `land.py` as the doc-only `warn`. Pre-existing, not a regression. Suggested treating file presence as runner intent.
- Note — ADR-0068 is `status: Proposed`; it should be Accepted before this slice closes.

Orchestrator follow-up after this verdict (not seen by the reviewer): the crash-class case is now stated in the slice's edge cases and in `skills/tdd-loop/test-command-recipes.md`; `land.py check_tests` now treats the presence of `.jig/test-command` as a declared runner (test added).
