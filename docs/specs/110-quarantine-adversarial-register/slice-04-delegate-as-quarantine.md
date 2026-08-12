---
status: REVIEWED
dependencies: [110-01, 110-02]
last_verified:
frame_review: true
claimed_by: claude/adversarial-review-leak-64bb2d
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 110-04 — delegate-as-quarantine

**Goal:** Give thin-orchestrator / context-cost-discipline a *second reason* to
delegate file-heavy reading: delegating the sharp review *bodies* and bulk
corpus reads keeps that register out of the orchestrator's carried context — not
only its token bill. Handle *verdicts* carefully (their conclusion is itself the
adversarial payload — see the relay caveat), and name the honest grounding
trade-off so the guidance doesn't over-rotate into "delegate everything."

**Role & scope (per [ADR-0055](../../decisions/adr-0055-adversarial-register-quarantine.md)):**
source reduction (load-bearing), but the *register* reason is **contingent on
A1(ii)** (the bleed mechanism). Its **token-cost** rationale (specs 055/057)
holds regardless — so even if the mechanism test (A1 kill criterion) falsifies
(ii), this slice keeps its cost rationale and only drops the register reason. No
work stranded.

**DoR:**
- ✅ 110-01 (boundary) and 110-02 (reconcile framing) landed — 110-04 references
  the reconcile framing for the reading that must stay first-hand.

**Assumptions:** rests on **A1** — specifically the contingent mechanism A1(ii)
for its register rationale; `frame_review: true`.

**Acceptance Criteria:**

1. **Second reason named — with the relay caveat.** The thin-orchestrator (spec
   057) / context-cost-discipline (spec 055) guidance states that delegating the
   sharp review *bodies* and bulk corpus reads keeps their register out of the
   orchestrator's context (a clean win — the orchestrator never reads the "attack
   the frame" prose). **But** a *verdict's* conclusion ("X is wrong, here is what
   breaks") is itself the adversarial payload, and the spec's own leak taxonomy
   names "reviewer output surfaced back up" — so the guidance requires the
   subagent to return a **neutral, decision-focused** summary (the actionable
   outcome + what to change, not the argumentation). Delegation quarantines tone
   and the unread body, **not** a relayed blocking conclusion; that residual is
   handled by 110-02/03 (de-tone + collaborative default), stated as such.
2. **Highest-register files prioritized** for delegate-and-summarize:
   `docs/**/reviews/*-frame-critique.md` verdicts and the adversarial skill
   bodies are called out as both the costliest to hold and the most leak-prone —
   read by a subagent and returned as a neutral decision-summary, never pulled in
   wholesale.
3. **Grounding tension named, not hand-waved.** The guidance states that
   delegating *all* reading weakens grounding (jig's core value), so the rule is
   "delegate the bulk + the adversarial-register files; keep the minimum
   first-hand reading grounding genuinely needs" — and points at 110-02
   (de-toning the source) as the fix for the reading that must stay first-hand.
4. **No delegation is made mandatory.** The change is guidance/rationale only; no
   gate forces delegation (consistent with specs 055/057 being disciplines, not
   gates).

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Reviewed by `reviewer` subagent (compliance + craft; frame-critique fires).
- [ ] Deviation log + reconciliation sweep produced.
- [ ] Reconciliation review passed.

**Anti-horizontal-phasing check:** after this slice, an orchestrator following
thin-orchestrator guidance delegates the register-heavy reads for a stated
second reason — observable as which files it reads first-hand vs delegates.

### Deviation log (after reconciliation)

1. **Guidance placed in `docs/workflow.md`, not the spec 057/055 records.** The
   operative, orchestrator-read home for thin-orchestrator / context-cost
   guidance is `docs/workflow.md`'s "Context-cost discipline" section; specs
   057/055 are **closed (DONE) records** whose editing would fall under the
   ADR-0010 amendment policy. So the second reason landed as a new subsection
   ("A second reason — quarantine the adversarial register") directly under the
   existing "### Delegate file-heavy reading" rule — the live prose the
   orchestrator actually reads — not the closed records.
2. **Honest scope, per the frame-critique.** The subsection states all three
   hedges the frame-critique required: the **relay caveat** (a verdict's
   conclusion is the payload → return a neutral, decision-focused summary; the
   residual is handled by the collaborative default / de-toned source, not by
   delegation), the **grounding tension** ("delegate the bulk + the
   adversarial-register files; keep the minimum first-hand reading grounding
   needs" — don't over-rotate), and the **contingency** (the register reason
   rests on A1(ii); the token-cost reason holds unconditionally).
3. **No delegation made mandatory (AC4).** The change is guidance/rationale; no
   gate forces delegation — consistent with specs 055/057 being disciplines, not
   gates. Guard test `DelegateAsQuarantineTests` asserts the guidance is present.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` (110-04 status). |
| `docs/workflow.md` | `updated` | New "A second reason — quarantine the adversarial register" subsection under Delegate file-heavy reading (AC1–AC4). |
| `scripts/test_working_posture.py` | `updated` | New `DelegateAsQuarantineTests` guard. |
| `docs/specs/057-thin-orchestrator/**` | `no-op` | Closed (DONE) record — operative guidance lives in `workflow.md`, not the record (deviation #1). |
| `docs/specs/055-context-cost-discipline/**` | `no-op` | Closed record; cross-linked only, not edited. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` | `no-op` | Not touched — delegation guidance is workflow.md's home, not the lean primer. |
| `docs/memory/**` | `no-op` | No new domain term; nothing to sync. |
