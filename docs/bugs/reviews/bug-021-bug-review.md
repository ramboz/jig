---
bug: 021
pass: bug-review
verdict: pass
reviewer: reviewer subagent (read-only, fresh context)
reviewed_at: 2026-08-31T15:14:40Z
prompt_source: review.py bug-review builder
---

VERDICT: pass

REASONING:
The fix addresses the documented root cause, not the symptom: selector capability for a custom command is now a declared, refusable contract (tdd.py:366-398 — fail-closed exit 2 before spawning when `{test}` is absent, `_selector_missed("custom", ...)` parity for unresolved selectors), and bug.py's gates surface tdd.py's own report instead of a bare exit code (bug.py:810-819, 935-949, 970-985). All three regression classes are demonstrably red pre-fix (the refusal/substitution/drop assertions and `build_suite_from_selectors` cannot pass against the old code), and the record honestly discloses that the pre-fix red was necessarily whole-suite. Blast radius is genuinely closed: independently confirmed bug.py:802 is the only production caller passing `--test`, land.py:327 passes no selector (the `{test}` token strip keeps whole-suite paths working), health.py reads only `.jig/lint-command`, run_tests.py is not shipped to hosts, and both host copies of tdd.py/bug.py carry the new code. The voluntary closure inventory meets the ADR-0052 standard — recorded terms, `git log -S` history with commits, explicit reuse decision, per-site disposition.

SPECIFIC ISSUES:
- docs/bugs/021-custom-test-command-drops-selector.md Proof — claimed the green stamp one step ahead of its evidence (frontmatter still FIXING at review time). Self-correcting at the real REVIEWED transition; implementer reworded to name the mechanism instead.
- skills/tdd-loop/tdd.py:278 — `_selector_missed("custom", 0, output)` returns False: a custom command exiting 0 while reporting "no matching tests" reads green; SKILL.md stated the mapping without the non-zero qualifier. Doc nit — implementer added the qualifier.
- skills/bug-fix/bug.py:937-941 — exit-2 arm still labels a targeting refusal "environment error"; appended detail disambiguates, cosmetic only (message phrase pinned by existing test contract).

RECONCILIATION NOTES:
- Green-stamp gap reworded in Proof; green witnessed and stamped at the actual REVIEWED transition after this review was recorded.
- Residual accepted risks recorded in the bug record: literal `{test}` reaches run_tests.py when a human runs the command verbatim (fails safe: "no matching tests: {test}", exit 1); the placeholder must be a standalone shlex token (embedded forms like `--sel={test}` are not recognized and produce the refusal, which fails safe); a custom command exiting 0 on a selector miss is not detected (parity with auto-detect runners).
- REVIEWED's green gate in this repo now runs only the named test and skips pyright (whole-suite green + pyright + board integrity move to land/CI) — intended per the record; narrows what the REVIEWED transition itself attests.
