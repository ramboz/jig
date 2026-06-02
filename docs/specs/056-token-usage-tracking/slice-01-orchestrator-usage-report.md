---
status: DONE
dependencies: []
last_verified: 2026-06-02
---

## Slice 056-01 — On-demand per-spec orchestrator usage report (MVP)

**Goal:** A developer can run a helper command for a spec and get the
orchestrator token breakdown (input / output / `cache_read` / `cache_create`)
plus a `ccusage`-based $ estimate — reading local transcripts directly, no
capture hook or ledger.

**DoR:**
- ✅ Helper home decided (spec Open question — `scripts/usage.py` vs a skill).
- ✅ ccusage-integration shape decided (rate-application vs `ccusage --json`).

**Acceptance Criteria:**

1. A helper (e.g. `scripts/usage.py`) exposes `report <spec>` (number or slug)
   that locates the spec's transcript sessions under `~/.claude/projects/` by
   worktree `cwd` + spec-path mentions in the transcript.
2. It sums **orchestrator** `message.usage` across those sessions —
   `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
   `cache_creation_input_tokens` — and a total.
3. It produces a **$ estimate via `ccusage`** (apply ccusage's per-model
   effective rates to the attributed token totals; never hard-coded pricing).
   It **degrades gracefully** with a clear message when `npx`/`ccusage` is
   unavailable (token counts still print; $ shows "unavailable").
4. Output is a compact per-spec summary (tokens by category + est $ + session
   count + models seen), **stdout-only and read-only** (no file mutation, no
   network beyond the optional ccusage call).
5. Honest framing in the output: $ is an estimate (notional under subscription
   billing), and this MVP counts orchestrator usage only (subagents arrive in
   056-02).

**DoD:**
- [x] All ACs pass; full suite green (no regressions). 1895 tests, OK (3 skipped).
- [x] Coverage via **synthetic transcript fixtures** (a temp
      `~/.claude/projects`-shaped tree): attribution to the right spec; the
      four token sums; the no-`ccusage` degradation path; read-only/no-mutation.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed (2 review issues fixed: ccusage timeout + coverage; none blocking).
- [x] Deviation log produced.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if decisions were deferred (n/a — the 056-02 design correction is captured in slice-02's note + the deviation log, not a deferred decision).

**Anti-horizontal-phasing check:** After this slice a developer runs one
command and sees a real per-spec token + $ number — end-to-end value, even
before subagent accounting and exact attribution land.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the helper
      name + the on-demand (no-hook) design + ccusage-integration shape.
- [x] CLAUDE.md hygiene per spec 025-01 rule (n/a — spec 056 still in-flight
      [056-02/03 remain], so the Active-specs entry stays; `usage.py` is a
      standalone script, not a skill, so no Skills-table row).

### Deviation log (after reconciliation)

The spec above is preserved. Implementation notes:

1. **What shipped.** `scripts/usage.py` (standalone tool, per the clarify
   decision) with `report <spec>`: finds the spec's transcript sessions under
   `~/.claude/projects/` by encoded-cwd prefix (spanning worktrees;
   `--projects-dir` override), attributes by dominant spec-path mention, sums
   orchestrator `message.usage` (4 fields + total), and prices via ccusage's
   per-model effective rate applied to those sums (graceful degradation when
   ccusage is unavailable). stdout-only, read-only, never throws.
   `scripts/test_usage.py` covers attribution (incl. via tool-call content),
   the sums, degradation, read-only, worktree-spanning discovery. Suite green:
   1895 tests (1888 baseline + 7 reconciliation tests), 3 skipped.

2. **Dogfooding note.** Implementation + both review passes ran in isolated
   subagents; the orchestrator kept summaries. (This slice *is* the tool that
   will measure that.)

3. **Review findings folded in** (compliance + craft both `pass`; evidence in
   `reviews/slice-01-{compliance,craft}.md`):
   - *Fixed (compliance medium)* — added `timeout=` to `run_ccusage_npx` so a
     stalled `npx` fetch degrades to "$ unavailable" instead of hanging
     (`subprocess.TimeoutExpired` flows through the existing degradation path),
     plus a test.
   - *Fixed (coverage nits)* — tests for: attribution via a spec path inside a
     `tool_use` input / `tool_result`; the `apply_rates` partial-rate branch
     (two-model fixture); `--ccusage-json` missing/garbage-file degradation.

4. **Significant finding — corrects a prior assumption (and 056-02's design).**
   The craft review verified, and the orchestrator independently confirmed,
   that **subagent turns are fully logged per-turn in nested
   `<session>/subagents/agent-*.jsonl` files** (333 in jig; `isSidechain:true`,
   real `usage`). The earlier "subagent usage is final-turn-only in
   `toolUseResult` / needs a peak×turns proxy" conclusion (this session's
   by-hand analysis; spec 056 Overview finding #2; 056-02's approach; the
   factor-0.7 clarify decision) was a **glob-depth artifact** (scanned one
   level deep, missed the nested dirs). 056-01 correctly stays
   orchestrator-only (non-recursive glob excludes the nested dirs). **056-02
   should sum the nested transcripts directly** — a ⚠️ correction note was
   appended to `slice-02`, and the memory record was corrected. The ~90/8
   orchestrator/subagent split is likely understated for subagents; 056-02 will
   produce the measured number.

5. **Incident — collateral repo damage during the fix-pass (recovered).** The
   reconciliation fix-implementer ran `git stash push` (a no-op on the
   untracked 056-01 files) then `git stash pop`, which applied an **unrelated,
   pre-existing shared stash** (worktrees share the stash list) — a
   `032-atomic-writes` WIP from branch `claude/funny-goldberg-828e9e` — into the
   tree, leaving conflict markers in 5 out-of-scope files (`032` spec + slice,
   `scaffold.py`, `land.py`, `memory.py`). The sandbox correctly blocked the
   subagent from git-discarding them. The orchestrator verified `stash@{0}` was
   still intact (no WIP lost), restored all 5 files to HEAD, and left the stash
   in the list for its owner (`git stash apply stash@{0}`). **Lesson:**
   subagents must not use `git stash` in a shared-`.git` worktree setup — `pop`
   can apply a sibling branch's stash. (Captured in `docs/memory/learnings.md`.)

6. **Plan adherence / impact.** Followed the planned shape (standalone
   `scripts/usage.py`, on-demand, ccusage-priced). Added `--main-root` /
   `--ccusage-json` seams beyond the literal ACs for testability/offline —
   noted. Attribution is the MVP content heuristic (056-03 adds the exact
   `.jig/spec-ref` marker). No conventions/architecture impact; no ADR.
