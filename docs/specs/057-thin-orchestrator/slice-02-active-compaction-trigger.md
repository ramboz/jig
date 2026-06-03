---
status: DRAFT
dependencies: [055-02]
last_verified:
---

## Slice 057-02 — Active compaction trigger

**Goal:** Turn 055-02's *warn-only* growth nudge into an **actionable
compaction / handoff prompt** when orchestrator context crosses a high band —
capping **peak context**, the second factor in cost ∝ context × turns
(r = 0.96 with peak context). Today the hook says "you're big"; after this it
says "compact now — here's what to carry over."

**DoR:**
- ✅ 055-02 landed: `jig-context-check.sh` runs on `UserPromptSubmit`, reads the
  transcript-tail `cache_read`, and bands at `JIG_CONTEXT_GROWTH_WARN_PCT`
  (40/60/80) with once-per-band + re-arm-on-drop semantics.

**Acceptance Criteria:**

1. **Actionable compaction message at a high band.** When transcript-tail
   `cache_read` crosses a new high band (knob `JIG_CONTEXT_COMPACT_PCT`,
   defaulting above the warn bands), `jig-context-check.sh` emits a concrete
   next-step: recommend compaction, or a fresh-session handoff with a one-line
   "carry over: spec path, current slice, open threads" hint — not just a size
   warning.
2. **No duplication of the warn bands.** The compaction message fires only at
   the high band and is distinct from the 40/60/80 warn messages; the warn
   behavior is unchanged.
3. **Once-per-band, re-arm-on-drop.** Reuses 055-02's band-state machinery — the
   compaction nudge fires once per crossing and re-arms only after context drops
   below the band (i.e., after an actual compaction).
4. **Soft, fail-open.** `UserPromptSubmit` advisory only; never blocks a prompt;
   degrades silently on any error. jig recommends — it does not run `/compact`
   (ADR-0011: nudge, not enforcement).
5. **Scaffolds + verifies.** The behavior flows to target projects via the same
   path as the other 055 hooks; `verify_install.py` asserts its presence.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Coverage: crossing the compaction band emits the actionable message once;
      staying above it does not re-fire; dropping below then re-crossing
      re-fires; the warn bands are unaffected; malformed/missing transcript
      degrades silently; the message names a concrete carry-over.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice a long session is actually
told to compact — with *how* (compact or hand off, and what to carry) — instead
of merely warned it's large.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the
      `JIG_CONTEXT_COMPACT_PCT` knob + that it extends the 055-02 hook.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (if this slice + 057-01 close the spec,
      compress the Active-specs entry).
