---
slice: 094-03 — decision vocabulary on the routing surface
pass: compliance
verdict: pass
reviewer: jig:reviewer subagent (fresh context)
reviewed_at: 2026-07-16T21:17:52Z
prompt_source: review.py implementation
---

Verdict: **pass-with-findings** → recorded as `pass` (no blockers). All four ACs met.

Reviewed `skills/memory-sync/SKILL.md` + `evals/cases/memory-sync.json`. (Reviewer had no Bash; routing figures below were derived arithmetically from supplied numbers and the case corpus, not measured by them. The implementer measured them — see the deviation log.)

**On the 97% → 95% "regression" (asked explicitly): it is denominator dilution, not sibling damage.** The corpus went 60 → 62 positives; the rank-1 *count* went **up**, 58 → 59. The two new cases contributed one rank-1 and one rank-2, and every pre-existing rank-1 held. Had a sibling lost rank-1 the figure would be 94%, not 95%. This corrects the implementer's own framing mid-slice ("I lost 3 rank-1s"), which was true of a first draft and not of what shipped.

**On rank 2 for the "cards" case (asked explicitly): a proxy limit, not a goal failure.** `adr-workflow` claims the phrase "record this decision" verbatim; the lightweight-ness of the prompt lives in content words ("cards", "cap", "tall", "laptops") present in neither description, so TF-IDF has nothing to discriminate on. The discriminator that does the real work sits after "Do not use", which `routing_surface()` strips by design (frame-critique 086-01). The engine's own docstring pre-authorises this: forcing a lexical proxy to win every pairwise tie "invites gaming the descriptions rather than improving them". Fixing rank 2 would require keyword-stuffing — the failure mode the harness exists to prevent.

**On over-claiming (asked explicitly): none.** Every scope term is grounded in `lightweight-decisions.md`'s own canon. The description *under*-claims (drops brand/icon swaps), which is the safe direction.

**Findings folded back:**

1. The slice's own citation `SKILL.md:110-116` was invalidated by the change it governs — the description grew 6 lines, so the block moved to 116-128. **Fixed**: both citations now name the block ("the lightweight-decision flow") instead of line numbers that drift.
2. The description filed `docs/decisions/lightweight-decisions.md` under "the memory layer", a label the body explicitly reserves for `docs/memory/` ("the file lives in `docs/decisions/`, not `docs/memory/`") — a category looseness against AC #4's "description and body agree". **Fixed**: the description now sends memory-layer work to the memory layer and decisions to `docs/decisions/…` via `decisions.py`, as two separate sentences. This also fixed a dangling relative clause the craft reviewer flagged, and *lowered* the adr-workflow × memory-sync collision from 0.23 → 0.20.
3. The first new eval case ("Remember this decision…") is a weak pin — it overlaps the description near-verbatim and its load-bearing token ("remember") was already in the *pre-slice* description, so it might not fail on the regression AC #3 exists to catch. The "cards" case is the honest test. **Partly fixed**: that case is now pinned at `top_k: 1`, so it fails on the *rank-1 loss* that is the actual reported symptom rather than merely on a top-3 drop.

**Accepted, not fixed:**

4. `analyze`'s positive ("Are there contradictions or duplication across the decision records and the spec?") sits at rank 3, one place off the hard gate, because the "decision" stem is now denser in memory-sync's positive surface. It was already non-rank-1 before this slice (rank 2), so no rank-1 was lost — but the reviewer's warning stands: *the next* skill to add decision vocabulary will break it. Recorded as a watch-item in the deviation log; cutting the triple phrasing now would trade a real routing gain for a proxy margin.

**Finding 5 (verification, unresolved by the reviewer): resolved — no action.** The reviewer could not run git and asked whether this slice silently restated `skill_routing.py`'s "rank-1 95%" baseline comment. Checked: `git show --stat a63f501` does not touch `scripts/skill_routing.py`; the comment dates to `fbee6a7` (2026-07-08, spec 086). It is stale from corpus growth, predates this slice, and was not touched.
