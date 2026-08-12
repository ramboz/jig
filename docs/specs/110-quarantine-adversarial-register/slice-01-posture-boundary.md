---
status: RECONCILED
dependencies: []
last_verified: 2026-08-11
frame_review: true
claimed_by: claude/adversarial-review-leak-64bb2d
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 110-01 — posture boundary + keystone ADR

**Goal:** State, where the orchestrator reads it, that adversarial review is a
*named, bounded operation* and that the default posture everywhere else is
collaborative and solution-forward — so a jig-scaffolded session answers what's
asked and proposes routes instead of manufacturing blockers. Record the
quarantine principle as the keystone ADR.

**Role & scope (per [ADR-0055](../../decisions/adr-0055-adversarial-register-quarantine.md)):**
this slice is a **counter-anchor — necessary but not sufficient.** A1 says the
dominant leak is register accumulated from *mid-session reads*, which a lean
standing line cannot outweigh on its own; the behavioural cure is **paired** with
the source-reduction slices (110-03 de-tone at source, 110-04 delegate away).
This slice delivers the *recorded principle* (ADR) and the *collaborative
default* — it does not claim a standalone turn-one behavioural fix.

**DoR:**
- ✅ Issue #199 comments 2–3 read; scaffold-wide register audit available.
- ✅ Owner has confirmed the quarantine principle is the intended direction
  (this spec's DRAFT review) and whether slice 01 authors the ADR.

**Assumptions:** rests on spec-level **A1** (the leak is operational
context-bleed, not always-on priming) — a real, contested load-bearing
assumption, so this slice is `frame_review: true` and draws the (now
grounding-aware) frame-critique pass.

**Acceptance Criteria:**

1. **Keystone ADR recorded.** An accepted ADR states the quarantine principle:
   adversarial review is bounded and isolated; orchestrator-facing surfaces are
   collaborative; the rejected alternative (softening the review prompts
   themselves) and why it's rejected (blunts the review) are named.
2. **Primer carries a posture-boundary line.** `templates/CLAUDE.md.template`
   (and the identical `AGENTS.md.template`) gains one concise standing
   statement: adversarial review is a named operation; outside it, default to
   collaborative, solution-forward help — answer what's asked; don't manufacture
   blockers or lead with why-not. It reads as posture, not a new gate.
3. **Review-heavy SKILL bodies point to the boundary.** The tops of
   `independent-review`, `spec-workflow`, and `bug-fix` SKILL.md carry a short
   pointer to the same boundary (a one-liner + link), so the orchestrator meets
   it exactly when it loads the register-heavy material.
4. **No gate or rigor is weakened.** The statement changes posture only; no
   `.py` gate, exit-code, or generated subagent prompt is altered by this slice
   (verified by diff scope).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] If a lexical-presence test guards the primer/SKILL statement, it is shown
      to fail when the statement is removed (capable of failing, not vacuous).
- [ ] Reviewed by `reviewer` subagent (compliance + craft; frame-critique fires
      pre-review per `frame_review: true`).
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.

**Anti-horizontal-phasing check:** end-to-end value is that the quarantine
principle is *recorded* (an accepted ADR future agents can cite) and the
collaborative default is *stated on the surfaces the orchestrator loads* — a
standing, user-visible default, not intermediate state for a later slice. Its
behavioural *sufficiency* is explicitly paired with 110-03/04 (see Role & scope);
this slice is not claimed to cure the symptom alone.

### Deviation log (after reconciliation)

1. **Orchestrator-implemented (not an implementer subagent).** These four slices
   are judgment-heavy prose edits to jig's own high-blast-radius surfaces, where
   holding subtle boundaries (no gate weakened, invoke-obligations preserved,
   spec-102 carve-out, tone-vs-disposition) matters more than TDD mechanics. The
   orchestrator implemented with the full frame-critique context; the
   load-bearing independence gate — compliance + craft — ran as fresh-context
   reviewer subagents (both `pass`).
2. **Primer line trimmed after craft round-1.** The first draft used a 7-line
   Working-posture body that pushed the primer template over the 70-line
   lean-primer budget (spec 076-01), and the craft pass flagged a [nit] that it
   injected adversarial vocabulary ("skeptical/flaw-hunting/blockers/gatekeeping")
   onto the very surface the spec prizes as near-zero-register. Both fixed:
   collapsed to one lean, lower-register line (rendered template = 70 lines,
   within budget), keeping only the one necessary "adversarial" to name the
   boundary. **Primer headroom is now ~0 — 110-02 must route its
   corpus-reconcile guidance to `workflow.md`, not the primer.**
3. **Host mirrors rebuilt.** Editing `templates/*.template` and the three
   `SKILL.md` bodies drifts the committed `hosts/claude/**` + `hosts/codex/**`
   mirrors; `build_host_packages.py` regenerated them (drift check green). This
   is part of the slice, not stray.
4. **jig's own `CLAUDE.md` primer intentionally NOT edited.** Per A1, the
   always-loaded primer is *not* the leak source (audited lean); the operative
   surfaces are the scaffold *template* (for newly-scaffolded projects) and the
   review-heavy *SKILL pointers* (AC3), which reach jig's own review path. So the
   primer change is template-only by design — consistent with the spec's own
   finding — not an omission.
5. **Nit carried (non-blocking):** `test_working_posture.py`'s template vs SKILL
   test classes assert asymmetric lexical sets (template guards "enforcement
   lives in tooling"; SKILL guards the ADR link + stance phrase). Harmless given
   the surfaces differ in register; left as-is.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` (110-01 status). |
| Primer surfaces: scaffold `CLAUDE.md.template` + `AGENTS.md.template` | `updated` | The lean Working-posture line (AC2). jig's own `CLAUDE.md` intentionally untouched (deviation #4). |
| `skills/{independent-review,spec-workflow,bug-fix}/SKILL.md` | `updated` | Posture pointer + ADR-0055 link at body top (AC3). |
| `scripts/test_working_posture.py` | `updated` (new) | Lexical-presence guard for the primer + SKILL posture statements (DoD item 2 / deviation #5). |
| `hosts/claude/**` + `hosts/codex/**` | `updated` | Rebuilt mirrors (deviation #3); drift check green. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0055 accepted + indexed (`README.md:61`). |
| `docs/architecture.md` | `no-op` | No module-boundary / public-contract change — prose posture only. |
| `docs/memory/**` (for 110-01) | `no-op` | 110-01 adds no domain term beyond ADR-0055 (indexed). NB: `learnings.md` was modified on this branch by the co-landed **bug 033** fix (its "Bug 033" entry), not 110-01 — accounted for under bug 033's own reconciliation, not an omission here. |
| `docs/conventions.md` | `no-op` | Not touched (posture is guidance, not a coding rule). |
