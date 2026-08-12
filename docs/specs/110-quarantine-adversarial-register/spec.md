---
status: DRAFT
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 110: Quarantine the adversarial register (orchestrator-facing collaborative posture)

> Reserved 2026-08-11. The deferred second half of the frame-critique-leak work
> ([issue #199](https://github.com/ramboz/jig/issues/199), comments 2–3). The
> first half — reviewer-prompt grounding-awareness, the reporter's
> "contain-at-review" lever — shipped as
> [bug 033](../../bugs/033-frame-critique-false-positive-grounded.md) (DONE).
> This spec is levers **2 (quarantine-the-register)** and **3
> (delegate-as-quarantine)**.

## Overview

**Problem.** jig runs adversarial reviews (frame-critique, the craft/arch
passes). That register — *hunt the flaw, attack the frame, concede a `pass`
only if it survives your strongest attack* — belongs inside those reviews. But
it **leaks into the orchestrator's plain-conversation stance**: in
jig-scaffolded sessions the orchestrator has been observed manufacturing
blocking objections where nothing is gated, defending recorded decisions against
exploratory questions, and refusing-by-default. The reporter's second instance
is the clean case: a user asked a *pure feasibility question* ("is X possible,
and how would we do it?"), and the orchestrator opened with *"Why [the idea] is
more expensive than it looks"* and argued it *"collides head-on with three
recorded project decisions"* — an unrequested blocking case built out of the
project's own records. User pushback: *"did i ever ask you if this was
expensive? no. i asked if it was possible."*

**Where it comes from — operational context bleed, not always-on priming.**
Two independent audits (the reporter's, comment 2; and this session's
scaffold-wide register sweep) agree: jig's *always-loaded* surfaces are lean
(the primer template is ~66 lines with a few incidental gate words;
`independent-review`'s skill `description:` scores zero adversarial vocabulary).
The register enters the orchestrator's context when it **reads adversarial
material while working** — the review skill **bodies**, the **corpus** (ADRs,
specs, and especially `docs/**/reviews/*-frame-critique.md` verdicts written in
"attack the frame" register), and **reviewer output** surfaced back up. Because
a session's context carries across turns, that register colours the
*plain-conversation* stretches of the same session.

**The principle — quarantine the register to the isolated reviewer context.**
The reviewer already runs as a fresh-context subagent (rung-1 independence,
[ADR-0020](../../decisions/adr-0020-spec-frame-hardening.md)); adversarial
instructions *inside there don't leak* — the subagent returns a verdict and its
context is discarded. So: **keep the sharp, skeptical language inside the
subagent prompt (as sharp as the review needs) and make every
orchestrator-facing surface collaborative.** This removes **no** rigor — rigor
stays exactly where it belongs, inside the bounded, isolated review operation,
and the real gates are `.py` exit codes, not prose. It only stops the register
from bleeding into ordinary work.

**What "the register" actually is — disposition, not just tone.** The reported
instance is telling: the orchestrator *already reconciled* against the records
("cited three recorded decisions") and *then* weaponized the result into a
blocking case. So the pathology is the **blocking disposition** — carrying
"hunt the objection / lead with why-not" into a question that asked for none —
not merely sharp wording or a failure to engage the corpus. The fixes target the
disposition; adding "reconcile" prose alone would not move it (a primed
orchestrator satisfies it and still blocks). This distinction, and the resulting
split of the four levers into *source-reduction* (load-bearing) vs
*counter-anchor* (necessary but not sufficient), is the frame this spec was
re-grounded onto after its own frame-critique — see the Decomposition and
[ADR-0055](../../decisions/adr-0055-adversarial-register-quarantine.md).

**Keystone decision → candidate ADR.** The quarantine principle is a
load-bearing, cross-cutting *authoring* rule for how jig writes its own
surfaces, chosen over the rejected alternative of *softening the review prompts
themselves* (which would blunt the review). By jig's own convention
(load-bearing choice with a rejected alternative), slice 110-01 should record it
as an ADR — proposed title *"Adversarial-register quarantine: orchestrator-facing
surfaces are collaborative; sharp language stays in the discarded subagent
context."* Flagged for the owner at DRAFT review.

## Assumptions

See [ADR-0055](../../decisions/adr-0055-adversarial-register-quarantine.md) for
the full statement; mirrored here as the spec's load-bearing premises.

- **A1 (load-bearing, contested — mechanism-scoped).** Three candidate
  mechanisms, not two: (i) always-on priming — **ruled out** by two independent
  register audits (surfaces lean); (ii) operational context-bleed of the
  adversarial register read mid-session; (iii) base-rate model cautiousness
  *intrinsic* to the model, present with or without jig content. The evidence
  does **not** yet discriminate (ii) from (iii): the two observed instances show
  the symptom occurs in jig sessions with no reviewer present, but neither traces
  a leak back to a prior adversarial read. **The decision survives this
  uncertainty:** the posture/tone levers (110-01/02/03) reduce the symptom under
  either (ii) or (iii); only 110-04's *register* rationale depends on (ii), and
  even 110-04 keeps its token-cost rationale regardless — no work is stranded.
  **Kill criterion (mechanism test):** vary adversarial-read volume *within* jig
  sessions (register-heavy vs register-light, same scaffold/model); if both leak
  equally, (ii) is false and 110-04's register rationale is dropped (token
  rationale stands). The jig-vs-no-jig before/after tests *attribution* only, not
  the mechanism.
- **A2 (partially grounded — with a disconfirming branch).** *Most*
  orchestrator-facing refusals are backed by `.py` exit codes (`bug.py`'s teeth;
  the review-evidence gate in `workflow.py transition`) — softening their
  narration changes posture, not enforcement. **But jig also uses deliberateness
  gates and prose-only nudges** where the prose *is* the enforcement
  (`jig-spec-gate.sh`; `contracts` / `clarify` nudge without refusing). So
  110-03 relocates the "no" onto the tooling **only where a backing exit code
  exists**; where enforcement is prose-only it keeps the agent-owned refusal (or
  files a gate gap) and never dresses a nudge as a hard gate. *Probe (110-03):*
  enumerate each narrated refusal **and classify** hard-gate vs
  deliberateness/nudge before rewording.

## Decomposition

**SPIDR — Rules axis, keystone-first.** Each slice changes an
orchestrator-facing surface (the agent's standing posture is the "user-facing
layer" here); none is horizontal phasing. Sharp language inside the *generated
subagent prompts* is out of scope to change — it is already quarantined and must
stay sharp.

**Two lever roles (per ADR-0055, from the frame-critique of this spec).** A1
locates the dominant channel in material *read mid-session*, not the lean
always-on surfaces — so the levers are **not** equal, and 01/02 do **not** claim
a standalone turn-one behavioural cure:

- **Source reduction (load-bearing): 110-03 + 110-04** — de-tone the review
  bodies at the source and delegate the highest-register reads so they never
  enter the orchestrator's context.
- **Counter-anchor (necessary but not sufficient): 110-01 + 110-02** — set the
  collaborative default and de-weaponize the premise. Real value, but **paired**
  with source reduction, not standalone (a lean primer line is dwarfed by
  accumulated register).

The pathology targeted throughout is the **blocking disposition** (the reported
instance *reconciled then weaponized*), not sharp tone alone — see ADR-0055
"register-as-tone vs register-as-disposition."

- **110-01 — Posture boundary (keystone).** The explicit statement: adversarial
  review is a *named, bounded operation*; outside it the default posture is
  collaborative and solution-forward — answer what's asked, propose routes,
  don't manufacture blockers. Placed in the primer
  (`templates/CLAUDE.md.template` + `AGENTS.md.template`) + a pointer at the top
  of the review-heavy SKILL bodies. Records the keystone ADR. **Role:**
  principle- and default-setting counter-anchor, paired with 110-03/04 — not a
  turn-one cure. [lever 2a]
- **110-02 — De-weaponize the corpus premise.** Guidance targeting the
  *disposition*: recorded decisions are context to **reconcile against**, not
  ammunition to **refuse with** — and since a primed orchestrator already
  reconciles ("I reconciled; it conflicts; here is the blocker"), the rule is to
  not carry a *blocking intent* into exploratory questions, surface-and-explore
  instead. Includes the amendment-authorization wording pass, **narrowed**:
  lead the amend-guardrail with *reconcile-first* (safe), but **keep its hard
  "stop"** for a genuine unauthorized-record-amendment conflict — the collaborative
  default is for ordinary exploratory conversation, **never** the spec 102 brake.
  **Owner-approval-gated** surfaces drafted, not applied without sign-off.
  **Role:** counter-anchor, paired. [lever 2b]
- **110-03 — Put the "no" on the tooling; tone-pass the review bodies.** Rewrite
  orchestrator-facing SKILL prose that narrates refusal as the *agent's* job so
  the helper/exit-code is the gatekeeper — **but only where a backing exit code
  exists** (A2): for deliberateness/prose-only gates, keep the agent-owned
  refusal or file a gate gap, never fictionalize tool enforcement. Soften only
  the orchestrator-read parts of the review-heavy bodies; the generated subagent
  prompts stay sharp. **Role:** source reduction (load-bearing). [levers 2c + 2d]
- **110-04 — Delegate-as-quarantine.** Extend thin-orchestrator
  ([spec 057](../057-thin-orchestrator/spec.md)) / context-cost-discipline
  ([spec 055](../055-context-cost-discipline/spec.md)) to **name a second
  reason** for delegation. Clean win: delegate the sharp review *bodies* and
  bulk corpus reads (the orchestrator never reads the "attack the frame" prose).
  For *verdicts*, the relay caveat: a verdict's conclusion is itself the
  adversarial payload ("reviewer output surfaced back up" is a named leak
  vector), so the subagent must return a **neutral, decision-focused** summary
  (outcome + what to change, not the argumentation); the residual disposition a
  relayed conclusion carries is handled by 110-02/03, not delegation. Token-cost
  rationale (055/057) always holds; register rationale is contingent on A1(ii).
  Name the grounding tension: "delegate the bulk + the adversarial-register
  files; keep the minimum first-hand reading grounding genuinely needs." **Role:**
  source reduction (load-bearing), register-reason contingent. [lever 3]

**Ordering.** 110-01 is the keystone (states the principle + ADR). 110-02–04
follow; 110-04 references the reconcile framing 110-02 establishes.

## Slices

- [110-01 — posture boundary + keystone ADR](slice-01-posture-boundary.md)
- [110-02 — de-weaponize the corpus premise](slice-02-deweaponize-corpus.md)
- [110-03 — no-on-the-tooling + tone-pass review bodies](slice-03-tooling-owns-no.md)
- [110-04 — delegate-as-quarantine](slice-04-delegate-as-quarantine.md)
