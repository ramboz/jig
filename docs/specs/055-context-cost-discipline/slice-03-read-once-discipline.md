---
status: DONE
dependencies: [055-01]
last_verified: 2026-06-01
---

## Slice 055-03 — Read-once / read-lean discipline

**Goal:** Steer developers away from the two most common Read-side context
wasters — re-reading a file already in context, and whole-file reads where a
range suffices — via a soft nudge plus standing guidance. Read is the single
largest context source (≈ 26%; e.g. `spec.md` was re-read 42× in the $540
session).

**DoR:**
- ✅ 055-01 landed (discipline section to extend).
- ✅ Mechanism decided: a `PreToolUse` (matcher: Read) nudge, tested via
  synthetic fixtures, scaffolded into target projects (Clarifications Q1/Q4).

**Acceptance Criteria:**

1. The `docs/workflow.md` "Context-cost discipline" section gains the
   read-once / read-lean rule: don't re-Read what's already in context; prefer
   Grep-to-locate plus ranged Read over whole-file scans.
2. A soft `PreToolUse` hook (matcher: `Read`) nudges when the **same file path
   is Read more than once** in a session (configurable; at most once per
   path), recommending reuse of the in-context copy. Non-blocking (exits 0);
   per-session read-path state kept alongside 055-02's state file.
3. (Optional, same mechanism) a nudge on a whole-file Read above a size
   threshold suggesting `offset` / `limit`. (Size threshold left to fine-tune
   at planning — see spec Open questions.)
4. The rule cites the observed motivating pattern (the 42× `spec.md`
   re-read) so the guidance carries its evidence.
5. **The `PreToolUse` hook is wired into both the plugin's hook config and
   scaffold-init's generated `settings.json`** (Clarification Q1), so
   scaffolded target projects receive the nudge.

**DoD:**
- [x] All ACs pass; full test suite green. 1743 tests, OK (3 skipped).
- [x] Coverage via **synthetic fixtures** (Clarification Q4): single read ⇒
      silent; duplicate read of same path ⇒ exactly one nudge; distinct paths
      ⇒ silent; never blocks.
- [x] A scaffold-mode test asserts the `PreToolUse` hook lands in the
      generated `settings.json`.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed (2 nits → 1 fixed, 1 logged; none blocking).
- [x] Deviation log produced.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if decisions were deferred (n/a — read-lean threshold resolved inline, no deferrals).

**Anti-horizontal-phasing check:** After this slice the developer — in the jig
repo or a scaffolded project — is steered away from the biggest single context
source (repeated and oversized file reads) via an observable nudge.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the dedupe
      mechanism + `JIG_READ_LEAN_BYTES`.
- [x] CLAUDE.md hygiene per spec 025-01 rule (n/a — 055-03 does not close the
      spec; 055-04 remains).

### Deviation log (after reconciliation)

The spec above is preserved. Implementation notes:

1. **What shipped.** Implemented via the `jig:implementer` subagent (strict
   TDD). A new `PreToolUse` branch in `jig-context-check.sh` (gated on
   `tool_name == 'Read'`) delegates to pure functions in
   `hooks/scripts/lib/context_fill.py` (`evaluate_read`, `read_nudge_for_turn`,
   `duplicate_read_nudge_text`, `large_read_nudge_text`). It nudges on (a) a
   duplicate Read of the same path — at most once per path per session — and
   (b) a whole-file Read of a file above `JIG_READ_LEAN_BYTES` (default
   **64 KiB**), exempting ranged (`offset`/`limit`) reads. Per-session path
   state lives under `$TMPDIR` with a distinct `jig-read-paths-` prefix (vs the
   growth nudge's `jig-context-growth-`). The "Read once, read lean" rule
   (citing the 42× `spec.md` re-read) was added to the `docs/workflow.md`
   Context-cost discipline section. Registered under `PreToolUse` / matcher
   `Read` in `hooks.json`; auto-propagates to scaffold via
   `_build_jig_hook_entries`. Suite green: 1743 tests, OK
   (3 skipped) — 1739 implementation baseline; reconciliation replaced the lone
   positivity check with 5 value/fallback tests (net +4).

2. **Dogfooding note.** Implementation (~112K tokens) + all three review passes
   ran in isolated subagents; the orchestrator kept only summaries.

3. **Design resolution (spec Open question).** The "read-lean size threshold"
   open question is RESOLVED: **64 KiB** (`DEFAULT_READ_LEAN_BYTES`),
   overridable via `JIG_READ_LEAN_BYTES` (~16K tokens at RATIO=4 — large enough
   to skip routine source reads). Recorded in the status-board Notes per
   Close-out.

4. **Review findings folded in** (compliance + craft both `pass`; evidence in
   `reviews/slice-03-{compliance,craft}.md`):
   - *Fixed (craft nit)* — added unit tests pinning the 64 KiB default and
     exercising the `JIG_READ_LEAN_BYTES` out-of-range / non-numeric fallback
     directly (`_resolve_read_lean_bytes`), matching the robustness coverage the
     sibling env knobs already had.

5. **Findings logged, not changed** (non-blocking, accepted-by-design):
   - The per-session `seen`-path list grows unbounded within a session and is
     re-serialized on every Read (O(paths) × O(reads)) — tiny in absolute
     terms, a natural consequence of the `PreToolUse(Read)` mechanism, and
     consistent with the growth nudge's "left to the OS tmp-reaper" stance.
   - Intentional, tested interaction: a large file's first read fires the
     *large* nudge without consuming the per-path duplicate budget, so a later
     re-read still earns the (priority) *duplicate* nudge.

6. **Plan adherence / impact.** Followed the planned shape (pure function +
   thin shell shim, mirroring 055-02). No conventions impact. Architecture: a
   new `PreToolUse` matcher on the existing context-fill hook — no
   module-boundary or public-contract change, so no ADR. Inbox: nothing to
   park.
