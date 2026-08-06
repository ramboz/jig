---
bug: 031
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent
reviewed_at: 2026-08-05T04:29:55Z
prompt_source: review.py bug-review
---

VERDICT: pass

REASONING:
The fix addresses the documented root cause (orient never refreshes remote-tracking refs nor reports commits-behind on the interactive path) rather than masking a symptom. It adds a `fetch=False` param defaulting to the byte-identical hot path — the SessionStart hook (`jig-project-orient.sh`, timeout=4) passes no `--fetch`, so the 4s path is untouched. The bounded fail-soft fetch (5s), the fetch-failure fall-through to "could not reach origin", the post-fetch deadline reset, and every named edge case (detached HEAD count still valid, local-only silence, non-git silence, zero-behind-with-failed-fetch → unreachable, plural/singular noun, ref-name sanitization via `_sanitize_orient_ref`) are handled correctly and pinned by tests. The named regression test calls `orient(..., fetch=True)`, which raises `unexpected keyword argument 'fetch'` before the fix — a genuine red — and passes after.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- `green_confirmed_at` is empty while the record is in FIXING; the REVIEWED transition populates it before advancing, resolving the apparent contradiction with the Proof section.
- `_freshness_summary` resolves the base against the default branch (`origin/main`), not the branch's own `@{upstream}` — intentional parity with `_in_flight_summary`/`_in_flight_base` (orient's "status board describes the default branch" model). Noted in the deviation log so a future reader does not mistake it for an oversight.
