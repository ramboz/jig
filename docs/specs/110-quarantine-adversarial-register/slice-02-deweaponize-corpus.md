---
status: DONE
dependencies: [110-01]
last_verified: 2026-08-11
frame_review: true
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 110-02 — de-weaponize the corpus premise

**Goal:** Reframe, in the orchestrator-facing guidance, the *disposition* with
which recorded decisions are used in ordinary conversation: a recorded decision
is context to **reconcile against**, not ammunition to **refuse with**. The
target is the blocking *intent*, not engagement — the reported instance already
reconciled ("cited three recorded decisions") and then weaponized the result, so
"add reconcile prose" is not enough: the guidance must say *don't carry a
blocking intent into a question that asked for none — surface and explore.*

**Role & scope (per [ADR-0055](../../decisions/adr-0055-adversarial-register-quarantine.md)):**
**counter-anchor — necessary but not sufficient**, paired with the
source-reduction slices (110-03/04). And the **hard stops stay hard**: the
collaborative default is for ordinary exploratory conversation; it does **not**
touch the spec 102 unauthorized-record-amendment brake.

**DoR:**
- ✅ 110-01 landed (the posture boundary this reframing specializes).
- ✅ Owner decision on the amendment-authorization wording pass (touches
  conventions-adjacent hot cache + the spec 102 guardrail — owner-approval-gated).

**Assumptions:** rests on **A1**; `frame_review: true`.

**Acceptance Criteria:**

1. **Reconcile-not-refuse guidance exists** in a general orchestrator-facing
   surface (primer and/or `workflow.md`), targeting the *disposition*: recorded
   decisions are context to reconcile against; on a conflict with a user's idea,
   surface and explore, don't carry a blocking intent — reconciling-then-blocking
   is the failure mode, so the guidance names it explicitly. Cross-links the
   `reframe` skill, which already names this as jig's structural blind spot.
2. **The spec 102 amendment guardrail is explicitly carved OUT of the
   collaborative reframe — its lead is left unchanged.** Frame-critique
   established that spec 102 is a **prose-only advisory brake** (its coded hook is
   deferred as unable to cover the case, per `docs/specs/102-.../spec.md:60-62`),
   so by this spec's own **A2** the prose *is* the enforcement and must not be
   softened. Therefore the amend-lead ("surface the conflict and stop") is **not
   reworded** — not "reconcile-first", not "escalate". AC1's general
   collaborative default names this as an explicit exception so it never reaches
   the one place that must stay hard. (The earlier "amendment wording pass" idea
   is dropped by this slice as unsafe — a finding surfaced by the ceremony, worth
   the owner's attention.)
3. **Owner-approval-gated surfaces are not applied without sign-off.** Any touch
   to owner-approval-gated surfaces (the primer hot-cache reconcile guidance;
   `docs/conventions.md`) is presented for explicit approval, not written
   unilaterally.
4. **No guardrail weakened — verified by diff, not by a suite.** The spec 102
   amend-lead prose is unchanged (diff shows no edit); its drift-test still
   asserts the load-bearing clauses. AC4 makes **no** "verified by behaviour"
   claim — a prose-only brake has no exit-code oracle a suite could check.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Diff confirms the spec 102 amend-lead prose is unchanged; its existing
      drift-test still passes (load-bearing clauses present).
- [ ] Reviewed by `reviewer` subagent (compliance + craft; frame-critique fires).
- [ ] Deviation log + reconciliation sweep produced.
- [x] Reconciliation review passed.

**Anti-horizontal-phasing check:** end-to-end value is that the orchestrator-
facing guidance now frames the corpus as ground-to-reconcile-against (not
ammunition) and names the reconcile-then-block failure mode — a standing,
user-visible reframe on the surfaces sessions load. As a counter-anchor its
behavioural sufficiency is paired with 110-03/04 (see Role & scope); it is not
claimed to move the stance alone.

### Deviation log (after reconciliation)

1. **Guidance placed in `docs/workflow.md`, not the primer.** AC1 offered "primer
   and/or `workflow.md`"; the primer was chosen against for two reasons — 110-01
   left it at ~0 lean-budget headroom, and the primer hot cache is
   owner-approval-gated. `docs/workflow.md` is the un-gated, always-relevant home,
   so a new "Working posture — recorded decisions are context, not ammunition"
   section landed there. No primer surface was touched.
2. **The originally-scoped "amendment wording pass" was dropped as unsafe.** The
   frame-critique established that spec 102 is a **prose-only advisory brake** (no
   coded backstop), so its prose *is* the enforcement and softening its lead would
   violate this spec's own A2. The amend-lead ("surface the conflict and stop") is
   left **verbatim**; the collaborative default is carved to exclude it (AC2). A
   guard test asserts the lead + its load-bearing clauses are unchanged.
3. **Shared guard file.** `scripts/test_working_posture.py` gained
   `CorpusReconcileGuidanceTests` (110-02) alongside 110-01's and 110-03's
   classes — the file is the shared posture-guard home across this spec's slices
   (noted for scope clarity; the craft pass flagged the cross-slice presence).

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` (110-02 status). |
| `docs/workflow.md` | `updated` | New "Working posture — recorded decisions are context, not ammunition" section (AC1). |
| `scripts/test_working_posture.py` | `updated` | New `CorpusReconcileGuidanceTests` (guidance present + spec-102 lead unchanged). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / templates | `no-op` | Not touched — guidance went to `workflow.md` (deviation #1); primer owner-approval-gated + no headroom. |
| `skills/spec-workflow/SKILL.md` (spec 102 amend-lead) | `no-op` | Prose-only brake carved out of the reframe — lead unchanged (AC2, deviation #2). |
| `docs/conventions.md` | `no-op` | Not touched by this slice. |
| `docs/memory/**` | `no-op` | No new domain term; nothing to sync. |
