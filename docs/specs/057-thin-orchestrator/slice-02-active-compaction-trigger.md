---
status: DONE
dependencies: [055-02]
last_verified: 2026-06-03
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
- [x] All ACs pass; full test suite green (no regressions).
- [x] Coverage: crossing the compaction band emits the actionable message once;
      staying above it does not re-fire; dropping below then re-crossing
      re-fires; the warn bands are unaffected; malformed/missing transcript
      degrades silently; the message names a concrete carry-over.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (None deferred.)

**Anti-horizontal-phasing check:** After this slice a long session is actually
told to compact — with *how* (compact or hand off, and what to carry) — instead
of merely warned it's large.

### Deviation log

**Chosen default band — `JIG_CONTEXT_COMPACT_PCT = 0.75`.** Per spec Decisions
§Q3 ("Prompt-only, ~75% default"). 0.75 lands **between** the existing fixed
055-02 escalation bands (0.60 and 0.80), so it is unambiguously above the warn
bands (AC #2) while still firing well before the window is exhausted. The knob
mirrors the other PCT knobs exactly: a fraction in (0, 1], with the same
out-of-range / non-numeric silent fallback (`_resolve_compact_threshold()`).

**Reuse approach (AC #3 — no duplicate state).** Rather than a parallel state
machine, the compaction band is **injected into the existing band set**
(`_growth_bands()` now also adds the compaction threshold). The 055-02
once-per-band + re-arm-on-drop machinery (`evaluate_growth`) is therefore reused
verbatim. The **only** new branch is message *selection* in
`growth_nudge_for_turn`: when the fired band is at/above the compaction
threshold, it returns `compaction_nudge_text()` instead of `growth_nudge_text()`.
This keeps a single state file, a single band evaluation, and no duplicated
warn-message code. Side effect (intentional, consistent with the 055-02 design):
because the 0.75 band is a real band, a session can now receive up to four
distinct nudges as it climbs (40 / 60 / 75 / 80) — the 0.75 one being the
compaction message, the others the warn message. This matches the escalation
intent and the once-per-band contract.

**Actionable message shape.** `compaction_nudge_text()` opens with
"Active-compaction nudge: ..." (distinct prefix from the warn message's
"Context-growth nudge: ..."), states the peak-context cost framing, then gives
the concrete next step — "run /compact … OR hand off to a fresh session" — and
an explicit carry-over checklist: "the spec path, the current slice, and any
open threads / decisions in flight." It reiterates jig recommends, does not run
`/compact` (ADR-0011), and points at the `docs/workflow.md` "Context-cost
discipline" section.

**`verify_install.py` (AC #5).** scaffold-init copies `hooks/scripts/lib/*.py`
and the `.sh` files verbatim, so the trigger flows with **no scaffold/copy-
machinery change** (confirmed — `_copy_hooks_and_register` copies the whole lib
dir). The new scaffold-mode check `check_scaffold_compaction_trigger` asserts the
copied `lib/context_fill.py` carries the `JIG_CONTEXT_COMPACT_PCT` marker (a
*behavior* assertion, not just file presence), registered as
`"compaction-trigger"` in `_SCAFFOLD_CHECKS`. The shared test fixture
(`_make_fake_scaffold_root`) was extended to write the `lib/context_fill.py`
stub with the marker so the full-fixture pass still holds.

**No deviations from the ACs.** All five ACs implemented as written; the DoD
coverage items (crossing fires once, staying above does not re-fire, drop +
re-cross re-fires, warn bands unaffected, malformed/missing transcript silent,
message names a concrete carry-over) are each covered by a test in
`test_context_fill.py` and `test_jig_context_check.py`. No decisions were
deferred → no `docs/refinement-todo.md` change needed.

**Test command (all green):**
```
python3 hooks/scripts/lib/test_context_fill.py    # 93 tests OK
python3 hooks/scripts/test_jig_context_check.py   # 44 tests OK
python3 scripts/test_verify_install.py            # 70 tests OK
```

**Post-review reconciliation note (craft nits).** The craft pass raised two
non-blocking nits: (1) `_growth_bands()` now owns the compaction band too — its
docstring already frames it as the umbrella warn+compaction band-set, so no
change was needed; (2) a pathological config setting `JIG_CONTEXT_COMPACT_PCT`
*below* the warn band would invert the warn-then-compact escalation. Addressed
in reconcile by a docstring note on `_resolve_compact_threshold()` documenting
that the knob is expected **above** the warn bands (the inverted config still
works — sorted band set — but is outside the supported envelope). No logic or
test change; the touched suite re-ran green.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the
      `JIG_CONTEXT_COMPACT_PCT` knob + that it extends the 055-02 hook.
- [x] `CLAUDE.md` hygiene per spec 025-01 (covered by the shared spec-057
      "Thin-orchestrator discipline" Key-terms entry; Active-specs was "(none)").
