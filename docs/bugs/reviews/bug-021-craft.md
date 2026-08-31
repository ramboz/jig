---
bug: 021
pass: craft
verdict: pass
reviewer: reviewer subagent (read-only, fresh context)
reviewed_at: 2026-08-31T15:15:46Z
prompt_source: pr-review skill craft pass
---

VERDICT: pass

REASONING:
Well-crafted and tightly scoped: the custom-command branch fails closed (refuse, exit 2) instead of silently widening; the exit-code contract is coherent across all three layers (tdd.py 0/1/2 → bug.py's gates; run_tests.py's `no matching tests` + exit 1 → mapped to 2 via `_selector_missed` through the merged-output stream, since `_run_streaming` uses `stderr=subprocess.STDOUT`); the deliberate red-vs-unresolved split in `build_suite_from_selectors` (import failure = red, unresolved name = missing) is explicitly reasoned and 3.9-safe. Tests are hermetic (tmp dirs, recorder/fake-helper subprocess stand-ins), pin behavior at the real CLI boundary, and assert the load-bearing negative (refused command never spawned; `red_confirmed_at` not stamped). Voice, comment discipline, class naming, fixture idioms, and the py-3.9 floor all check out. `main(argv=None)` stays CLI-compatible; hosts carry the new constant.

SPECIFIC ISSUES:
- skills/tdd-loop/tdd.py:370 — placeholder detection is token-exact; embedded forms like `--filter={test}` are refused when targeting (safe) yet forwarded literally on no-selector runs. Addressed: SKILL.md now says "as its own standalone argument". Nit, not blocking.
- skills/tdd-loop/tdd.py:388 — `_selector_missed("custom", …)` returns False on exit 0, so a command that exits 0 having matched nothing reads green. Known edge, parity with existing vitest/jest handling; now documented in SKILL.md + the record's residual risks.
- scripts/test_run_tests.py:159-161 — `[1]` indexing vs sibling tuple-unpack style. Addressed: unpacked for consistency.

RECONCILIATION NOTES:
- The `no matching tests` / `no test found` prefix set in `_selector_missed` is now part of the custom-command output contract; SKILL.md names the recognized prefixes so downstream custom-command authors emit a recognized line rather than an unrecognized synonym.
- The getattr chain in run_tests.py before `loadTestsFromName` is load-bearing (version-dependent miss behavior — 3.9 raises, newer returns a synthetic red _FailedTest); its comment must survive future refactors or the typo'd-selector-runs-red hazard returns on newer Pythons.
