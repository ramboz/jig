---
slice: 094-01 — machine text is never attributed to the owner
pass: reconciliation
verdict: pass
reviewer: jig:reviewer subagent (fresh context)
reviewed_at: 2026-07-16T21:31:24Z
prompt_source: review.py reconciliation
---

Verdict: **pass-with-findings** → recorded as `pass`. One reconciliation review covering all three slices of spec 094. Every finding is folded back; none deferred.

The pass judged whether the deviation logs are honest, not whether the code is good (that was the implementation review). It found three claims that did not survive checking — all three are now fixed.

**Findings folded back:**

1. **[medium] A "corrected inline" fix that was only half-applied.** 094-02 §5 claimed `refinement-todo.md:54` had been corrected on two counts; only the premise half was. The entry still described `extract_askuserquestion_answer` as reading "the PostToolUse payload" when it is now response-only — with the adjacent new entry getting it right, which made the omission plainer. **Fixed**: the entry now says `tool_response`.

2. **[medium] An undisclosed AC edit, described as a disclosure.** 094-01 §2 asserted that AC #4's word "predicate" was stale — but AC #4 no longer contained the word, because it had been silently edited from "The predicate lives" to "The rule lives". Meanwhile the genuinely stale word survived, uncorrected, in the Scope boundary. **Fixed**: the AC #4 edit is now disclosed with the original quoted verbatim, and the Scope-boundary prose is corrected.

3. **[medium] Template boilerplate falsified by the log's own content.** "The original spec is preserved above" was untrue once AC #3 was edited in place — the reader had to take the log's paraphrase on trust with no auditable delta. **Fixed**: the deviation log now states exactly which sections are as-drafted and which were edited, and quotes both original ACs verbatim.

4. **[low-medium] A sweep rationale that answered the wrong question.** All three sweeps marked primer surfaces `no-op` on a rationale about *compression*, while `CLAUDE.md:13` / `AGENTS.md:13` never mention spec 094 at all — the reviewer noted 025-01 asks whether an entry should *exist*, not only whether it should be compressed. **Fixed**: the rationale now answers the question actually posed — 094 opens and closes inside one change set, so it has no in-flight window to advertise, and its load-bearing invariant migrates to the status-board Notes column, which is where 025-01 sends it.

5. **[low] Status board stale** (rendered `IN_PROGRESS` while the slices read `REVIEWED`). **Fixed**: regenerated at close-out, which is when that item is due.

6. **[medium — process] The headline routing numbers had never been measured by anyone but their author.** All three 094-03 reviewers ran without Bash and said so; the reconciliation reviewer could not run them either, and asked that the commands actually be run before RECONCILED → DONE. **Done**, on the final tree, with output pasted into 094-03's deviation log §11: 62/62 positives, rank-1 59/62 = 95%, 44/44 negatives, collision 0.20, reported phrasing rank 1/1, 3339 tests OK, hosts in sync, pinned ruff clean. Every figure held. The reviewer's static cross-checks (62 positives / 44 negatives counted from the case files, `top_k` values, untouched `MIN_RANK1_RATE`, mirror parity, the stale-baseline comment) independently agree.

7. **[low] Two siblings applying different bars to a residual.** 094-01 §7's perf limit got no refinement-todo entry while 094-02's residual was made to take one. **Fixed by making the reasoning explicit** rather than by changing the outcome: §7 is a *closed* decision (not to optimise, on measurements, with the hook's async/5s registration making it unreachable in practice) — nothing later would resolve it, so it has no trigger and does not belong in a deferred list. 094-02's residual does have a trigger (083-08's payload shape) and is now tracked.

**What the reviewer affirmed:** the AC #3 rewrite moved in the honest direction — the AC was tightened to match a Goal that was never touched, after two independent reviewers found the hook still quoting raw harness text, and the code was then changed to clear the higher bar. That is spec-tightening, not retrofitting the spec to the code. The reviewer also noted the logs self-incriminate where it counts (094-01 §3 admitting an invented guard caused a real recall defect; 094-02 §3 admitting the unit tests cannot witness the reversal; 094-03 §2 recording that my own in-flight "I lost 3 rank-1s" framing was wrong and described a discarded draft), and that 094-03's out-of-deliverable work is disclosed and bounded by its own named hazard.
