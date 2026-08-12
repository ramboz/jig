---
status: DRAFT
dependencies: [110-01]
last_verified:
frame_review: true
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 110-03 — put the "no" on the tooling; tone-pass the review bodies

**Goal:** Where orchestrator-facing SKILL prose narrates a refusal as the
*agent's* job ("you refuse to advance…"), rewrite it so the `.py` helper / exit
code is the gatekeeper and the agent stays collaborative — and soften only the
orchestrator-read parts of the review-heavy skill bodies, leaving the generated
subagent prompts as sharp as the review needs.

**DoR:**
- ✅ 110-01 landed (the boundary this pass enforces in-prose).
- ✅ Enumeration + classification of the gate helpers (A2 probe): each narrated
  refusal is classified hard-gate vs deliberateness/prose-only before rewording.

**Assumptions:** rests on **A2** (qualified — *most* refusals are exit-code
gates, but jig also uses deliberateness/prose-only gates where the prose *is* the
enforcement) and **A1**; `frame_review: true`.

**Role & scope (per [ADR-0055](../../decisions/adr-0055-adversarial-register-quarantine.md)):**
source reduction — but its value is **(ii)-contingent**, like 110-04's: de-toning
the review bodies only reduces a leak *source* if the register actually enters by
*reading* those bodies (mechanism (ii)). Under (iii) (intrinsic cautiousness),
de-toning is counter-priming of unproven strength, not source removal. Its
**honesty fix** (tool-owned refusals not fictionalized; AC1/AC2) holds regardless.

**Acceptance Criteria:**

1. **Each narrated refusal is classified before rewording.** The A2 probe
   enumerates orchestrator-facing SKILL prose that casts the *agent* as the one
   who "refuses/blocks" AND classifies each as **hard-gate** (a backing `.py`
   exit code) vs **deliberateness/prose-only** (the agent's compliance is the
   enforcement — e.g. `jig-spec-gate.sh`, `contracts`, `clarify`). The sweep is
   complete, not sampled.
2. **Relocate only where a backing exit code exists.** For hard-gate refusals,
   rewrite so the helper's exit code is the gatekeeper and the agent relays and
   routes. For **deliberateness/prose-only** refusals, **keep the agent-owned
   refusal** (or file a gate-gap note) — never re-narrate a nudge as "the tool
   refuses". No enforcement is dropped and none is fictionalized.
3. **Tone pass on the orchestrator-read parts** of `independent-review`,
   `spec-workflow`, and `bug-fix` SKILL.md: the register the orchestrator reads
   is collaborative; the *generated subagent prompt strings* are untouched and
   remain sharp (verified by diff — no change inside the prompt builders).
   (Frame-critique confirmed this separability: the sharp strings live in
   `review.py`'s prompt builder, outside the orchestrator's read path.)
4. **Preserve the invoke-the-gate obligation.** jig gates are **in-helper-only
   and invocation-conditional** — a `workflow.py transition` / `bug.py` refusal
   fires *only when the orchestrator runs the helper* (the off-path-bypass
   invariant). So relocating the *refusal decision* onto the tool must **not**
   drop the agent's obligation to *invoke* it: each reworded site still carries an
   explicit "run/invoke `<helper>`" imperative. Softening "you refuse to advance"
   into a bare "relay and route" that no longer compels invocation would let an
   ungated advance slip through — a bypass CI cannot see. Verified by
   **inspection** of the reworded prose, not by the suite.
5. **No gate behaviour changes.** Hard-gate exit codes still fire *when invoked*
   (suite green); deliberateness/prose-only refusals keep agent-owned
   enforcement (AC2); and the invoke-obligation is preserved (AC4). The suite
   proves exit-code behaviour *given invocation* — it **cannot** observe whether a
   re-toned orchestrator still invokes, which is why AC4 is an inspection check,
   not a suite claim.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] The A2 classification (each narrated refusal → hard-gate vs
      deliberateness/prose-only) is recorded in the deviation log.
- [ ] Each relocated refusal site is shown, by inspection, to retain an explicit
      invoke-the-gate imperative (AC4).
- [ ] Reviewed by `reviewer` subagent (compliance + craft; frame-critique fires).
- [ ] Deviation log + reconciliation sweep produced.
- [ ] Reconciliation review passed.

**Anti-horizontal-phasing check:** after this slice, the orchestrator-read parts
of the review-heavy skills are collaborative and their refusals are honestly
attributed (tool-owned where a gate exists, agent-owned where enforcement is
prose-only, invoke-obligation intact) — an observable change in what the
orchestrator reads. Its source-reduction *efficacy* is (ii)-contingent (see Role
& scope); the honesty fix and the preserved invocation obligation hold
regardless.

### Deviation log (after reconciliation)

_TODO at reconciliation._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/specs/README.md` | `updated` | _TODO: regenerated by `workflow.py status-board`._ |
| `skills/independent-review/SKILL.md` | `updated` | _TODO: orchestrator-read tone pass (prompt builders untouched)._ |
| `skills/spec-workflow/SKILL.md` | `updated` | _TODO: refusal-narration relocation + tone._ |
| `skills/bug-fix/SKILL.md` | `updated` | _TODO: refusal-narration relocation + tone._ |
| `hosts/**` mirrors | `updated` | _TODO: rebuilt via `build_host_packages.py` (SKILL.md edits drift the mirrors)._ |
| `docs/memory/**` | `no-op` | _TODO: memory-sync result._ |
