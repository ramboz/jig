---
slice: 072-01 — present-infra-hint
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (read-only)
reviewed_at: 2026-06-15T17:13:41Z
prompt_source: review.py pr-review 072-01
---

VERDICT: pass

REASONING:
The servo advisory is implemented cleanly as four small, single-purpose helpers (`_servo_present`, `_servo_hint_opted_out`, `_latest_paused_run`, `render_servo_advisory`) appended after `has_blocker` is computed, so the never-gating invariant is structural rather than asserted after the fact. Naming, docstrings, constant-extraction, and the loose type-annotation style match the surrounding `land.py` idiom. Error handling is sound (filesystem probes no-raise on missing paths; the `relative_to` ValueError is caught). The test class is thorough — asserts behavior (not just code paths), pins the most-recent-run tie-break by `mtime`, proves the no-subprocess claim by making `subprocess.run` raise, and verifies present-vs-absent output is purely additive. No blockers.

SPECIFIC ISSUES:
- [strength] land.py:604-612 — advisory appended strictly after `has_blocker` is computed → AC4 (never-gating) is a structural property; matching test (test_land.py:2224) asserts present output == absent output + appended section.
- [strength] test_land.py:2246-2266 — no-subprocess assertion patches `subprocess.run` to raise on any call and still drives a full render incl. the paused-run path.
- [strength] test_land.py:2098-2107 — setUp uses a spec whose path/content contain no "servo" substring, making the AC2 case-insensitive assertion meaningful rather than vacuous.
- [strength] land.py:514-522 — `relative_to` wrapped in try/except ValueError with absolute-path fallback (handles a symlinked `.servo/`).
- [nit] land.py:481 — `_latest_paused_run` annotated `-> Path` but returns `None` when no runs; matches the module's existing loose-annotation convention (`_check_github_remote(cwd: Path = None)`, no `Optional` imported). `Optional[Path]` would be marginally more honest. Defer.
- [nit] land.py:463-465 — `_SERVO_PRESENCE_SIGNALS` (flat filename tuple) vs `_SERVO_HINT_OPT_OUT` (positionally-indexed path-segment tuple) use subtly different shapes; inline `target / ".jig" / "no-servo-hint"` would read more directly. Cosmetic.
- [nit] test_land.py:2208-2209 — `import os as _os` / `import time as _time` inside the test method; `os` already imported module-wide. Trivial.

RECONCILIATION NOTES:
No blockers; nothing blocks the REVIEWED transition. For the deviation log: (1) `_latest_paused_run` returns `None` under a `-> Path` annotation, following the file's existing un-typed-Optional convention (a deliberate consistency choice); (2) the two servo module-level constants use different tuple shapes — a future tidy-up if `land.py` adopts `Optional`/path-helper conventions repo-wide.
