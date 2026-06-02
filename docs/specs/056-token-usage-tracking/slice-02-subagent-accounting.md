---
status: DONE
dependencies: [056-01]
last_verified: 2026-06-02
---

## Slice 056-02 — Subagent accounting (nested transcripts) + orchestrator/subagent split

> **Design note (revised 2026-06-02, from the 056-01 review).** The original
> approach here was a lossy `toolUseResult` "peak×turns proxy" (clarify Q3
> factor 0.7). That is **superseded**: subagent turns are **fully logged
> per-turn** in nested `<session-uuid>/subagents/agent-*.jsonl` files
> (`isSidechain: true`, real `message.usage`, subagent type in
> `attributionAgent`). This slice **sums those directly** — measured, not
> estimated.

**Goal:** Extend `usage.py report` to include delegated-subagent usage by reading
the nested subagent transcripts, and split the report into **orchestrator**
(measured, flat session files — 056-01) vs **subagent** (measured, nested files)
so the true per-spec cost shape is visible.

**DoR:**
- ✅ 056-01 landed (the report + attribution + ccusage pricing it extends).
- ✅ Nested-transcript layout confirmed:
  `~/.claude/projects/<encoded-cwd>/<session-uuid>/subagents/agent-*.jsonl`,
  `isSidechain: true`, per-turn `message.usage`, subagent type in
  `attributionAgent`.

**Acceptance Criteria:**

1. For each session attributed to the spec (056-01's logic), `usage.py` reads
   that session's nested `<session-uuid>/subagents/agent-*.jsonl` transcripts and
   sums their per-turn `message.usage` (input / output / `cache_read` /
   `cache_create`).
2. The report **splits orchestrator (flat sessions) vs subagent (nested)** token
   + $ totals — **both measured** (no proxy, no estimate label) — plus a combined
   total = the true per-spec cost.
3. Subagent totals are **broken down by subagent type** (from each nested
   record's `attributionAgent`, e.g. `jig:reviewer` / `jig:implementer` /
   `general-purpose` / `Explore`).
4. $ uses the same ccusage per-model effective-rate approach as 056-01, applied
   to the orchestrator + subagent token totals; graceful degradation unchanged.
5. A session with no subagents contributes a subagent total of 0 (no nested dir
   → silent, never throws); malformed/missing nested files are skipped.

**DoD:**
- [x] All ACs pass; full suite green (no regressions).
- [x] Coverage via **synthetic fixtures** with nested `subagents/*.jsonl`: the
      subagent per-turn sum; the orchestrator-vs-subagent split; the
      per-`attributionAgent` breakdown; the combined total; a no-subagents
      session (subagent total 0); a malformed/missing nested file (skipped,
      never throws).
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Deviation log produced.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if decisions were deferred.

**Anti-horizontal-phasing check:** After this slice the per-spec report shows the
true **measured** orchestrator-vs-subagent cost shape — closing the measurement
gap the 055-motivating analysis exposed (and correcting its proxy estimate).

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the
      nested-transcript approach + the per-`attributionAgent` breakdown.
- [x] CLAUDE.md hygiene per spec 025-01 rule (n/a — spec 056 still in-flight
      [056-03 remains], so the Active-specs entry stays; `usage.py` is a
      standalone script, not a skill, so no Skills-table row).

### Deviation log (after reconciliation)

The spec above is preserved (this slice was **redesigned at READY_FOR_REVIEW** —
`toolUseResult` proxy → measured-from-nested-transcripts; see the Design note at
the top). Implementation notes:

1. **What shipped.** `usage.py` gains `find_subagent_files` + `sum_subagent_usage`
   (per-turn `message.usage` bucketed by `attributionAgent`) + `_merge_per_model`;
   `build_report` reads each attributed session's nested
   `<session>/subagents/agent-*.jsonl`, and `render` emits a 3-block report
   (orchestrator / subagent / combined, **all measured**) with the same ccusage
   pricing across all three. No-subagent → measured $0.0; malformed/missing
   nested → skipped, never throws. 056-01's orchestrator-only sums are unchanged
   (non-recursive glob + regression test). Suite green: 1906 tests, OK (3
   skipped); +11 056-02 tests (49 in `test_usage.py`).

2. **Dogfooding note.** Implemented + reviewed via isolated subagents. The
   implementer correctly **avoided `git stash`** (per the 056-01 learnings
   gotcha) — no recurrence of the shared-stash incident.

3. **Review findings folded in** (compliance + craft both `pass`; evidence in
   `reviews/slice-02-{compliance,craft}.md`):
   - *Fixed* — swept the stale `toolUseResult` proxy framing from `spec.md`
     (Goal #2, Non-goals, Design-notes, the Decisions "factor 0.7" entry, the
     slice-list line; Clarify Q3 marked superseded) — both reviewers flagged it,
     and per the closed-spec drift policy live spec prose is corrected inline.
   - *Fixed* — updated the stale module docstrings (`test_usage.py`
     "orchestrator-only" → orchestrator+subagent; `usage.py` "Cost via ccusage"
     singular "$ line" → all three dimensions).
   - *Fixed (reconciliation pass)* — the recon reviewer caught one leftover
     "orchestrator_only" name: renamed the test
     `test_output_notes_estimate_and_orchestrator_only` →
     `…_orchestrator_and_subagent` (its body already asserted `subagent`) and
     refreshed its now-stale "land later (056-02)" comment. Suite still 49 OK.

4. **Findings logged, not changed** (non-blocking nits):
   - `test_subagent_record_missing_usage_skipped` tolerates the `Explore` bucket
     absent-or-zero (craft reviewer suggested tightening to one branch);
     behavior is correct + tested, the assertion is just loose.
   - No test for "subagents present + ccusage no matching rate → subagent cost
     None" (the orchestrator variant is tested; the path is shared).

5. **Out-of-scope finding (flagged via a spawned task) — security-floor tuning.**
   The `jig-secret-scan.sh` PreToolUse hook (spec 052) **false-positives** on
   benign `*_tokens: int = 0` dataclass annotations (its
   secret-named-`.env`-assignment heuristic matches `…token… : <value>`). The
   implementer used the documented `JIG_SECRET_SCAN_APPROVED=1` escape hatch for
   one such edit. Spun off as a separate task (out of 056's scope).

6. **Plan adherence / impact.** Followed the revised (measured-from-nested)
   design. No conventions/architecture impact; no ADR. The ~90/8
   orchestrator/subagent split from the earlier by-hand analysis can now be
   **re-measured** with `usage.py` (the subagent dimension is real, not
   estimated).
