---
adr: 0039
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (independent, read-only)
reviewed_at: 2026-07-24T23:43:48Z
prompt_source: review.py frame-critique docs/decisions/adr-0042-decision-routing-gate.md
---

Adversarial frame-critique of ADR-0042, run before accept (ADR-0020 OQ2).

**Initial verdict: needs-changes.** The reviewer found the ADR's load-bearing
assumption was never stated: *that memory-sync's guidance is in the acting
agent's context at the moment a recorded decision is revised.* The draft claimed
"Assumptions: None unverified" while resting on exactly that.

The attack that landed: jig already shipped four judgement prompts quoting
`ADR_TRIGGER` before #121, and #121 happened anyway — so citing that pattern as
precedent cites the mechanism whose miss produced the ticket. ADR-0031
explicitly declines to claim a judgement prompt lifts attention; ADR-0042 rested
on the claim ADR-0031 refused to make. Compounding it, the guidance had landed
in the skill *body* while the always-loaded *description* never mentioned
revising a record and routed load-bearing decisions to `adr-workflow`, which
cannot promote a lightweight entry — so the guidance was unreachable on the very
trajectory #121 describes. The maintainer's ask on #121 was literally "a better
skill description".

**Changes made in response** (all before accept):

1. `memory-sync`'s **description** now covers revising/updating/correcting a
   recorded decision and names promotion as the remedy — the always-loaded
   surface, not just the body. Guarded by two new routing-eval cases; the full
   eval stays green (64/64 positive, 44/44 negative) and the
   adr-workflow × memory-sync collision sits at 0.24, far under the 0.50 warn.
2. Both reconcile checklists (`docs/workflow.md`, `spec-workflow/SKILL.md`) gain
   the revision clause, so spec sessions carry it too.
3. Assumptions section rewritten: the behavioural assumption is named as
   load-bearing and unverified, with the counter-evidence recorded beside it.
4. The precedent argument is demoted from a Pro to an acknowledged risk.
5. Stated plainly that **Option B would not have caught #121 alone either** —
   the revision was a hand-edit outside the helper — so Option A's
   disqualification is not asymmetric.
6. Kill criteria rewritten to be observable, and the honest risk named as false
   NEGATIVES (ADR-0031: lexical scans miss load-bearing cases precisely because
   they carry no stock phrase; 100-04 narrowed further in that direction). This
   downgrades "mitigated by the advisory lint" explicitly.
7. The brittle-signal argument is scoped so it does not generalise against
   ADR-0011's deliberateness-gate model as a whole.
8. Stale write-gate framing corrected in `spec.md`.

The frame survives with the assumption named, the counter-evidence recorded, and
the prompt moved to a surface that actually loads. It is not claimed to be
enforcement.
