---
status: READY_FOR_REVIEW
dependencies: []
last_verified:
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
- [ ] All ACs pass; full suite green (no regressions).
- [ ] Coverage via **synthetic transcript fixtures** (a temp
      `~/.claude/projects`-shaped tree): attribution to the right spec; the
      four token sums; the no-`ccusage` degradation path; read-only/no-mutation.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if decisions were deferred.

**Anti-horizontal-phasing check:** After this slice a developer runs one
command and sees a real per-spec token + $ number — end-to-end value, even
before subagent accounting and exact attribution land.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the helper
      name + the on-demand (no-hook) design + ccusage-integration shape.
- [ ] CLAUDE.md hygiene per spec 025-01 rule; add the helper's row to the
      Skills/Scripts table if it introduces a new entry point.
