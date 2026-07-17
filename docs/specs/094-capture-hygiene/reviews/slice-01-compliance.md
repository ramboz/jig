---
slice: 094-01 — machine text is never attributed to the owner
pass: compliance
verdict: pass
reviewer: jig:reviewer subagent (fresh context)
reviewed_at: 2026-07-16T21:16:40Z
prompt_source: review.py implementation
---

Verdict: **pass-with-findings** → recorded as `pass` (no blockers; every finding folded back before REVIEWED).

Reviewed `decision_scan.py`, `decision_scratch.py`, `jig-decision-inflight.sh` against 094-01's ACs.

**Findings folded back (not deferred):**

1. **[major]** `_MACHINE_UNCLOSED` swallowed everything after an unclosed named tag, so owner prose *beginning* with a tag mention was classified machine and silently dropped — contradicting AC #2. **Fixed by deleting `_MACHINE_UNCLOSED` entirely.** The truncated-injection case it guarded was speculative (invented during implementation, no evidence in #108) and bought that speculation at the price of a real recall failure — the exact class #108 is about. Regression test added (`test_prose_opening_with_a_tag_keeps_the_prose`).
2. Test passed for the wrong reason (only the stopword "the" survived, so it could not distinguish "prose preserved" from "one stray article preserved"). **Fixed**: asserts the prose itself now.
3. **[minor as filed, major in effect]** The hook stubbed the *raw* prompt, so a prepended `<system-reminder>` recorded harness text under `who: "user"` (`clip()` truncates at 240 chars). **Fixed**: the hook gates *and* quotes on `typed_by_owner(prompt)`. AC #3 reworded — on the Goal-vs-AC tension the reviewer named, the Goal is authoritative.
4. AC #3 untested with a *prepended* block. **Fixed**: both orderings tested.
5. The re-export had no unit test. **Fixed**: `TypedByOwnerTests` added.
6. The blanket `except Exception: pass` made every "writes nothing" assertion vacuously satisfiable — a dead hook would pass them. **Fixed**: `test_hook_discriminates_rather_than_just_failing` feeds both payload kinds to one session and asserts exactly the typed one survives.
7. `\b` admitted `<command-name-extra>` as a wrapper (`-` is a non-word char). **Fixed**: `(?![-\w])`, with a test.
9. `who == "user"` unasserted on the genuine-prose path. **Fixed**.

**Accepted, not fixed:**

8. `_MACHINE_BLOCK` is quadratic on input with many unpaired openers (~1.1s on a synthetic 95KB opener-spam payload). Not ReDoS — no nested quantifiers. Measured: realistic payloads (50KB pasted log, 50KB prose + reminder) run in 0.0003s. The hook is `async: true, timeout: 5` (hooks.json) so it cannot block a turn, and the input is the owner's own prompt — not an untrusted source. Recorded in the deviation log rather than optimised.

**Reviewer's open question, carried to #108 rather than answered here:** other wrapper families (`<bash-input>`, `<ide_selection>`) sit outside the enumerated set; the reviewer correctly declined to claim they occur without probing the host (ADR-0020).
