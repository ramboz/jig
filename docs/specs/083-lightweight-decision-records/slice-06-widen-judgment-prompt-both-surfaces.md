---
status: DONE
dependencies: [083-05, adr-0031]
last_verified: 2026-06-26
frame_review: true  # spec-level ## Assumptions are real (064-04 deriver);
#                   # covered by the ADR-0031 frame-critique pass (shared design).
---

## Slice 083-06 — Widen the load-bearing-decision judgment prompt in BOTH session-end surfaces

**Goal:** Own the load-bearing-decision case (not the 083-04 scan). Add the
**same** canonical judgment clause —
[ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md)'s
trigger sentence — to **both** session-end judgment surfaces so there is no
out-of-spec gap: the reconciliation checklist (in-spec slices) and the
session-end memory-sync prompt (out-of-spec work, which has no reconciliation
phase and is the spec's founding case). Both are judgment prompts — no trigger
phrase needed — so they catch the discursive ADR-worthy decisions the regex scan
structurally cannot.

**DoR:**
- ✅ [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md)
  Accepted (the canonical-source policy this slice applies).
- ✅ 083-05 landed the rubric quote + `ADR_TRIGGER` constant + the drift test.
- ✅ Surfaces grounded: `docs/workflow.md` + `skills/spec-workflow/SKILL.md` carry
  the reconciliation checklist; `skills/memory-sync/SKILL.md` carries the 083-03
  enumerated-surface session-end prompt to widen with the escape hatch.

**Acceptance Criteria:**

1. **Reconciliation checklist widened (two sites).** The reconcile checklist in
   both `docs/workflow.md` and `skills/spec-workflow/SKILL.md` asks the
   load-bearing-decision question, quoting the **exact** `ADR_TRIGGER` sentence —
   firing for in-spec slices even when no module boundary changed.
2. **Memory-sync prompt widened with the escape hatch.** `skills/memory-sync/SKILL.md`
   adds the **same** `ADR_TRIGGER` sentence as a judgment escape hatch to the
   083-03 condition, so the session-end prompt fires on **any** load-bearing
   decision a future agent would need to know to avoid undoing — not only the
   enumerated surface list. This is the only judgment owner for out-of-spec
   load-bearing decisions.
3. **Single-source drift guard green.** With both surfaces edited,
   `test_decisions.py`'s four-site assertion (rubric + two reconcile checklists +
   memory-sync prompt) passes verbatim against `ADR_TRIGGER`. Drift in any site
   fails CI.
4. **Host parity.** Host-packaged copies of the edited skills match source
   (`build_host_packages.py --check` green).

**DoD:**
- [x] All ACs pass; full suite green; `uvx ruff check .` clean.
- [x] ADR-0031 transitioned Proposed → Accepted (frame-critique recorded).
- [x] Reviewed by `reviewer` subagent (frame-critique + compliance + craft).
- [x] Deviation log + reconciliation sweep under this slice heading.
- [x] Primer / status board updated; spec 083 Active-specs entry NOT compressed
      (083-07/083-08 remain — this does not close Phase 2).

### Deviation log

- **ADR-0031 reframed after frame-critique round 1 (needs-changes).** The
  adversarial frame-critique flagged that the ADR conflated policy *consistency*
  (what single-sourcing delivers) with capture-rate *improvement* (unevidenced —
  the memory-sync escape hatch is the same session-end attention prompt the spec
  already concedes can't fix recall-dependence). Resolved by adding a "Scope of
  the claim — consistency, not capture" section, correcting `## Assumptions` from
  the false "None load-bearing" to an explicit not-claimed-here declaration,
  stating the drift test's deliberately *lexical* scope (semantic drift is the
  reconciliation reviewer's job), and adding a capture-eval kill criterion.
  Round 2: **pass**.
- **Compliance sequencing finding resolved.** Slice DoR/DoD require ADR-0031
  Accepted; it was authored Proposed (frame-critique gates ADR accept). Accepted
  2026-06-26 once the frame-critique cleared — resolving the compliance pass's
  sole needs-changes.
- **Cross-reference preambles standardized (craft nit).** Each surface's
  "quoted identically in [list]" preamble enumerated a *different* subset of the
  other sites (itself unsynced, un-drift-tested prose). Standardized all three to
  "single-sourced from ADR-0031, drift-tested verbatim across all four surfaces."
- **Active-specs entry deliberately NOT compressed.** Spec 025 compress-on-close
  applies only when a spec closes; 083-07 (ACTIVE) + 083-08 (Codex HANDOFF)
  remain, so spec 083 stays open and the primer entry is unchanged.

### Reconciliation sweep

- `docs/workflow.md` (reconcile checklist) — **updated** (canonical clause added).
- `skills/spec-workflow/SKILL.md` (reconcile checklist) — **updated**.
- `skills/memory-sync/SKILL.md` (session-end prompt escape hatch) — **updated**.
- [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md) —
  **updated** (reframed + Accepted).
- `hosts/claude/**`, `hosts/codex/**` — **updated** (rebuilt; `--check` green).
- `docs/specs/README.md` status board — **deferred** to close-out regen.
- `CLAUDE.md` / `AGENTS.md` primer — **no-op** (spec 083 still active; the
  load-bearing-decision policy lives in ADR-0031 + the four surfaces, not the
  primer index).
- `docs/architecture.md` — **no-op** (no module boundary / contract change; this
  is a lifecycle-policy doc edit, recorded via ADR-0031).
