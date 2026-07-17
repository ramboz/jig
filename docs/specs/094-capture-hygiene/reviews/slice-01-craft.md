---
slice: 094-01 — machine text is never attributed to the owner
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (fresh context)
reviewed_at: 2026-07-16T21:16:40Z
prompt_source: review.py pr-review
---

Verdict: **pass-with-findings** → recorded as `pass` (no blockers; findings folded back before REVIEWED).

Craft pass over `decision_scan.py`, `decision_scratch.py`, `jig-decision-inflight.sh`.

**Findings folded back:**

1. **[major]** Mixed payloads stubbed the raw prompt rather than the stripped text, quoting harness markup under `who: "user"` — the #108 defect surviving through the AC #3 hole. Converged independently with the compliance reviewer's finding 3. **Fixed**: the hook quotes `typed_by_owner`.
2. `_MACHINE_TAG`'s comment misdescribed the constant (given the ordering it could only strip orphan closers) and duplicated a neighbouring comment. **Fixed** — largely moot once `_MACHINE_UNCLOSED` was deleted; the comments now state the ordering constraint that makes paired-then-unpaired stripping work.
3. `not _MACHINE_TAG.search(raw)` was redundant for correctness, and the docstring oversold it as a two-part rule. **Fixed**: `is_machine_text` deleted; `strip_machine_text` is the single primitive, now used in production rather than only by a predicate — which also closes the reviewer's related note that `strip_machine_text` had no production caller.
4. AC #2's guarantee was position-dependent; the fixture passed only because "the " preceded the tag. **Fixed** — see compliance finding 1.
5. The `is_machine` → `is_machine_text` alias was a pure rename that cost grep discoverability, and was untested at this level. **Partly kept, partly changed**: the re-export stays (it mirrors the established `is_override` → `is_user_override` precedent, and `decision_scratch` is the hook's only import surface — AC #4), but it is renamed `typed_by_owner`, so it is no longer a pure rename: it names what the caller wants (the owner's text) rather than restating the callee. Now unit-tested.
6. `extract_askuserquestion_answer`'s docstring ran ~10 lines of change-history narration — "deviation-log material, not a constraint the next reader needs", with the call site's two-line comment named as the right density. **Fixed**: trimmed to the three things the code cannot say (the `""`-is-a-contract coupling to `append_stub`'s blank-quote guard, response-only by construction, and don't re-add the parameter).

**Strengths the reviewer named:** embedding a Tier-2 marker inside every harness fixture, so the wrapper tests cannot pass vacuously on the `is_override` gate; the `_MACHINE_TAGS` comment explaining the constraint rather than narrating the regex.
