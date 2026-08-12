---
status: Proposed
dependencies: []
last_verified:
frame_review: true
---

# ADR-0055: Adversarial-register quarantine: orchestrator-facing surfaces are collaborative

## Status

Proposed (2026-08-11)

## Context

jig runs adversarial reviews (frame-critique, the craft/arch passes). Their
register — *hunt the flaw, attack the frame, concede a `pass` only if it
survives your strongest attack* — is correct **inside** those reviews. But in
jig-scaffolded sessions the same stance has been observed leaking into the
orchestrator's **plain conversation**, where nothing is gated: manufacturing
blocking objections, defending recorded decisions against exploratory questions,
and refusing-by-default. The clean case (issue #199, comment 1): a user asked a
pure feasibility question ("is X possible?") and the orchestrator answered with
an unrequested cost/blocking case built out of the project's own records
("collides head-on with three recorded project decisions"); the user had to push
back — "did i ever ask you if this was expensive? no. i asked if it was
possible."

Two independent register audits (issue #199 comment 2; the scaffold-wide sweep
recorded in spec 110) agree the leak is **not** always-on priming — jig's
always-loaded surfaces are lean. It is **operational context bleed**: the
orchestrator reading adversarial material while it works (review skill bodies,
the corpus, `docs/**/reviews/*-frame-critique.md` verdicts, reviewer output),
and because a session's context carries across turns, that register colours the
plain-conversation stretches of the same session.

The reviewer already runs as a fresh-context subagent (rung-1 independence,
ADR-0020): adversarial instructions *inside there don't leak* — the subagent
returns a verdict and its context is discarded. The leak only happens through
the **orchestrator's** always-carried context.

The first half of the response — making the frame-critique reviewer prompt
grounding-aware so it stops false-positive-blocking on grounded assumptions —
shipped as bug 033 (the "contain-at-review" lever). This ADR governs the second
half: containing the leak into ordinary conversation.

## Decision Options Considered

### Option A: Soften the adversarial review prompts themselves
- **Pros:** one edit surface; directly removes the sharp language that leaks.
- **Cons:** blunts the review — ADR-0020 makes frame-critique's adversarial
  depth its whole value and forbids weakening it for cost. Trades away rigor to
  fix a tone leak; wrong lever.

### Option B: Quarantine the register to the isolated reviewer context
- Keep the sharp, skeptical language **inside the generated subagent prompt** (as
  sharp as the review needs — it is discarded and doesn't leak), and make **every
  orchestrator-facing surface collaborative**: the primer, the review-heavy SKILL
  bodies the orchestrator reads, and the way recorded decisions are framed for
  ordinary conversation. Pair it with delegating the highest-register reads to
  subagents so their register never enters the orchestrator's context.
- **Pros:** removes no rigor — rigor stays where it belongs, inside the bounded
  isolated review; fixes the actual channel (operational context bleed).
- **Cons:** touches several surfaces (spec 110's four slices); the causal premise
  (A1) is corroborated but not yet experimentally proven.

## Recommended Decision

**Option B — quarantine the register.** Adversarial review is a **named, bounded
operation**; sharp language stays inside the isolated, discarded reviewer
subagent context. **Every orchestrator-facing surface defaults to collaborative
and solution-forward** — answer what's asked, propose routes, don't manufacture
blockers, and treat recorded decisions as context to *reconcile against*, not
ammunition to *refuse with*. The real gates remain the `.py` helpers' exit
codes; softening prose changes posture, never a gate.

**Two distinctions this decision turns on** (surfaced by the frame-critique of
this ADR and spec 110's slices):

1. **Register-as-tone vs register-as-disposition.** The leak is not merely sharp
   *wording*; the reported instance shows the orchestrator *already reconciled*
   against the records ("cited three recorded decisions") and then weaponized the
   result. The pathology is the **blocking disposition** — carrying "hunt the
   objection / lead with why-not" into a question that asked for none — not a
   failure to engage the corpus. Fixes must target the disposition, not just
   soften words or add "reconcile" prose (a primed orchestrator satisfies "I
   reconciled; it conflicts; here is the blocker").

2. **Source-reduction vs counter-anchor — two lever roles.** Because A1 locates
   the dominant channel in material *read mid-session* (not the lean always-on
   surfaces), the levers are **not** equal:
   - **Source reduction (load-bearing):** de-tone the review bodies at the
     source (spec 110-03) and delegate the highest-register reads so they never
     enter the orchestrator's context (110-04). These attack the diagnosed
     channel.
   - **Counter-anchor (necessary but not sufficient):** the posture-boundary line
     (110-01) and the de-weaponized corpus premise (110-02) set the collaborative
     *default* and reframe the premise. On their own, a lean primer line is
     dwarfed by accumulated adversarial register; their value is real but
     **paired** with source reduction, not standalone. Slice 110-01/02 claim
     principle-setting and default-setting, not a turn-one behavioural cure.

Spec 110 implements this across the four slices with those roles made explicit.
The **hard stops that must stay hard** — e.g. the spec 102 unauthorized-
record-amendment brake — are *not* softened; only ordinary exploratory
conversation defaults collaborative (see Consequences).

## Consequences

**Becomes easier:**
- Ordinary "is X possible?" conversation in jig sessions stays collaborative
  instead of gate-shaped.
- The register that must stay sharp (the review) is clearly separated from the
  register the orchestrator carries.

**Becomes harder:**
- Authors of jig's own surfaces must now hold a boundary: sharp inside the
  generated subagent prompt, collaborative everywhere the orchestrator reads.
- Delegating the corpus/verdict reads to quarantine their register slightly
  fights first-hand grounding (jig's core value); the rule is "delegate the bulk
  + the adversarial-register files; keep the minimum first-hand reading grounding
  genuinely needs," with de-toning the source as the fix for the rest.
- **Delegation quarantines tone, not the blocking conclusion.** Delegating the
  sharp review *bodies* and bulk corpus reads is a clean win — the orchestrator
  never reads the "attack the frame" prose. But a *verdict's* conclusion ("X is
  wrong, here is what breaks") is itself the adversarial payload, and any
  faithful summary relays it — the spec's own leak taxonomy names "reviewer
  output surfaced back up." So 110-04's delegation must return a **neutral,
  decision-focused** summary (the actionable outcome + what to change, not the
  argumentation), and the residual disposition a relayed conclusion still carries
  is addressed by 110-02/03 (de-tone the source, collaborative default), not by
  delegation. This is why 110-04's *register* rationale is a helper, and its
  token-cost rationale (specs 055/057) is the part that always holds.

## Assumptions

- **A1 (load-bearing, contested — mechanism-scoped).** There are **three**
  candidate mechanisms for the conversational-gatekeeping symptom, not two:
  (i) always-on priming; (ii) operational context-bleed of the adversarial
  register (the orchestrator reading review bodies / corpus / frame-critique
  verdicts mid-session); (iii) base-rate model cautiousness *intrinsic* to the
  underlying model, present with or without any jig adversarial content.
  Mechanism (i) is ruled out by two independent register audits (always-on
  surfaces are lean). Between (ii) and (iii) the evidence does **not** yet
  discriminate: the two observed instances establish only that the symptom
  occurs *in jig sessions with no reviewer present*; neither traces the leak
  back to a prior adversarial read, which is the exact causal link (ii)
  requires. **This uncertainty is deliberately survivable by the decision.** The
  posture/tone edits (levers 2a–2d: collaborative default, de-weaponized corpus
  premise, tool-owned refusals) reduce the symptom **regardless of whether (ii)
  or (iii) dominates** — they make the orchestrator-facing surfaces collaborative
  either way. Only the *second reason* named in **110-04**
  (delegate-as-quarantine) depends specifically on (ii); and even 110-04's
  **primary** justification (token cost, specs 055/057) is unaffected by A1, so
  the worst case for a false (ii) is that 110-04 keeps its cost rationale and
  loses only its register rationale — no work is stranded.
- **A2 (partially grounded — with a disconfirming branch).** *Most*
  orchestrator-facing refusals are backed by `.py` exit codes (`bug.py`'s teeth;
  the review-evidence gate in `workflow.py transition`), out-of-band from the
  prose — softening *their* narration changes posture, not enforcement. **But
  not all.** jig deliberately also uses **deliberateness** gates and prose-only
  nudges where the agent's own compliance *is* part of the enforcement
  (`jig-spec-gate.sh` is a deliberateness gate; `contracts` / `clarify` nudge
  without refusing). For those, the prose is load-bearing — re-narrating them as
  "the tool refuses" would either drop the only enforcement or fictionalize a
  hard gate. So 110-03's rule is **conditional**: relocate the "no" onto the
  tooling **only where a backing exit code exists**; where enforcement is
  prose-only, keep the agent-owned refusal (or file a gate gap) — never dress a
  nudge as a hard gate. *Probe (110-03):* enumerate each narrated refusal **and
  classify it** hard-gate vs deliberateness/nudge before rewording.

## Kill criteria

- **Mechanism test for (ii) — the one that gates 110-04's register rationale.**
  Vary adversarial-read volume **within** jig sessions (register-heavy vs
  register-light, *same* scaffold, same model) and compare the conversational
  stance. If both leak equally, mechanism (ii) is false: the register bleed is
  not the driver, and 110-04's register rationale should be dropped (its
  token-cost rationale still stands). This is the discriminating test the
  earlier jig-vs-no-jig framing could not provide.
- **Attribution test (weaker, not a mechanism test).** The within-project
  before/after (jig scaffolded in as the single changed variable) confirms
  *whether jig causes the shift at all*, but holds read-volume roughly constant
  and so **cannot** distinguish (ii) from (iii). If it shows no stance shift at
  the scaffolding line even in register-heavy sessions, the whole premise is
  weak and the decision should be re-framed; a positive result confirms
  attribution only, not the bleed mechanism.

## Open questions

- Whether the delegate-as-quarantine guidance (110-04) needs any enforcement, or
  stays advisory like specs 055/057 (current lean: advisory — consistent with
  those specs being disciplines, not gates).
