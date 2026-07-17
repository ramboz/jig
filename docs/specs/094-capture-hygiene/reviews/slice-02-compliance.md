---
slice: 094-02 — a dismissed dialog produces no stub
pass: compliance
verdict: pass
reviewer: jig:reviewer subagent (fresh context)
reviewed_at: 2026-07-16T21:17:12Z
prompt_source: review.py implementation
---

Verdict: **pass-with-findings** → recorded as `pass` (no blockers).

Reviewed `decision_scratch.py` + `jig-decision-inflight.sh` against 094-02's ACs.

**On the breaking-change question (asked explicitly):** the reviewer checked every caller — source hook plus both host mirrors — all pass one argument, and both mirrors of the lib are in sync. No test mirrors exist under `hosts/`. A downstream install ships hook + lib together, and even a hypothetical stale two-arg caller fails open through the wrapper's blanket `except`. **No breaking change.**

**On whether the fix is complete (asked explicitly):** complete *for the evidenced defect*. #108's captured quote was question + option labels, which exist only in `tool_input` — itself the proof that the dismissed response yielded zero string leaves on that host. But see finding 1 for the residual.

**Findings folded back:**

1. `_collect_strings` walks the whole response, so a dismissed response carrying *any* string (`status: "dismissed"`, a `tool_use_error`, an echoed question) would still be stubbed `who: "user"` at Tier 1 — the same defect class, reached by a different payload shape. The slice bounds this out deliberately (the shape is not probeable from this repo; pattern-matching it would be the unverified assumption ADR-0020 forbids), and the reviewer agreed with that call — but noted the DoD requires a deferred decision to be *tracked*, and it was living only in a slice file that closes. **Fixed**: `docs/refinement-todo.md` gains "Narrow AskUserQuestion extraction to the answer key (094-02)" with a resolution trigger tied to the same 083-08 unknown that blocks the neighbouring per-answer split.
2. `docs/refinement-todo.md:54` was stale on two counts: it described the function as reading the whole PostToolUse payload (now response-only), and justified its deferral with the very "noisy stub is cheap" premise this slice reverses. **Fixed**: corrected inline (ADR-0010 — spec 083 is IN_PROGRESS, so live prose is corrected in place, not amended). The sweep's pre-filled `no-op` for that file flipped to `updated`.
4. AC #3's "at Tier 1" was not tied to an answered dialog through the hook path — tier coverage came only from a hand-built stub dict. **Fixed**: the hook test now round-trips its stub through `stubs_to_candidates` and asserts tier 1, plus asserts the question text is absent from an answered dialog's quote.

**Accepted, not fixed:**

3. The unit tests do not by themselves witness the reversal — with `tool_input` simply gone, `extract_askuserquestion_answer({}) == ""` would likely have passed pre-slice too. This is structural: once the parameter is deleted, no unit test *can* pass a question to be ignored. The witness is `test_dismissed_askuserquestion_writes_nothing`, which supplies #108's real payload (question + "Enforcement / Hard block" options) end-to-end and asserts an empty log. The reviewer judged coverage adequate in aggregate and noted the implementer names the limitation honestly in the test comment.

**Reviewer confirmed:** spec 083-07's closed record needs no ADR-0010 `## Amendments` block — its AC #3 ("Ephemera produce no stub") is *better* satisfied now.
