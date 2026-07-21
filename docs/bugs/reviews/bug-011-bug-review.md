---
bug: 011
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-16T21:29:05Z
prompt_source: skills/independent-review/SKILL.md (bug-review pass, bug 011)
---

Independent bug-review pass — **pass** on the fix. Per ADR-0014 §4 this file holds the
*operative* verdict; the earlier `needs-changes` rounds live in git history.

## Verdict basis

Round 4 returned pass on the tree as it then stood. A final pass re-verified the tree after the
`origin/main` merge and concluded: "The **fix is correct and complete**, and survives the merge
cleanly. Both recorded-corpus paths flag instead of drop… containment has a single home in
`is_contained()` that all three call sites route through, so the mirror that propagated the
original defect cannot drift again. #115's `skills/memory-sync/decisions.py` is inert here…
`hosts/` mirrors source at byte-identical line numbers for both claude and codex… Both residuals
are parked together at `refinement-todo.md:245-248`; ADR-0010 amendments are intact."

That final pass returned `needs-changes` on one ground only: **these two evidence files were
frozen at `needs-changes`**, which blocks REVIEWED by design — and it correctly identified that
freezing them misread ADR-0014 §4, which makes verdict files *live operational artifacts*
corrected inline with git history as the audit trail. Overwriting in place with the operative
verdict is the sanctioned move, and resolves that ground. No substantive finding on the fix
remained open.

## What the rounds found and fixed

1. **Dead comments and a broken discovery trail** — the `decision_scan.dedup` cross-references
   mattered beyond ordinary dangling refs: the "mirrors dedup's containment rule" docstring is
   what *proved* the stub path carried the same defect. Breaking the trail is how the next
   mirrored defect hides. Now a single shared rule makes the mirror structural.
2. **Spec 083 drift** — live prose and the AC5s of two closed slices described the behaviour this
   fix inverts, and open slice 083-08 would have validated against a stale AC5. Corrected per
   ADR-0010: inline for live prose, `## Amendments` for closed records.
3. **The record overclaimed** "nothing is ever dropped, so the class cannot recur" —
   `dedup_scan_against_stubs` still drops, so a Tier-3 *agent* reversal of an in-flight stub is
   still suppressed (agent prose never produces a stub of its own). Claim scoped; residual parked.
4. **A lifecycle claim went stale** — `clear_scratch` is now unreachable for a populated log, so
   a scratch log outlives its session while the module called it "ephemeral". Corrected; parked.
5. **A worked example didn't compute** (0.5, not 0.75 — the short stub with the long stub's
   arithmetic). The residual was real; the transcription was wrong.
6. **A fail-open regression** — the refactor dropped `or []` in a module contracting fail-open
   throughout. Restored and pinned by a test.
7. **Claims outrunning evidence, twice** — the `hosts/` drift-green claim and a "green witnessed"
   bullet pointing at an empty frontmatter field. Both corrected.

Behaviour-preservation of the `is_contained()` extraction was disputed in the review brief and
**resolved in the fix's favour**: the `_DUPLICATE_MIN_TOKENS` floor already existed in
`dedup_scan_against_stubs` (a slice 083-07 craft nit), so nothing changed. Recorded in `## Proof`
so it is not re-litigated.
