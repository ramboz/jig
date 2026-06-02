---
status: READY_FOR_REVIEW
dependencies: [055-01]
last_verified:
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
- [ ] All ACs pass; full test suite green.
- [ ] Coverage via **synthetic fixtures** (Clarification Q4): single read ⇒
      silent; duplicate read of same path ⇒ exactly one nudge; distinct paths
      ⇒ silent; never blocks.
- [ ] A scaffold-mode test asserts the `PreToolUse` hook lands in the
      generated `settings.json`.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if decisions were deferred.

**Anti-horizontal-phasing check:** After this slice the developer — in the jig
repo or a scaffolded project — is steered away from the biggest single context
source (repeated and oversized file reads) via an observable nudge.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the dedupe
      mechanism / env vars.
- [ ] CLAUDE.md hygiene per spec 025-01 rule.
