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

**Keystone decision → candidate ADR.** The quarantine principle is a
load-bearing, cross-cutting *authoring* rule for how jig writes its own
surfaces, chosen over the rejected alternative of *softening the review prompts
themselves* (which would blunt the review). By jig's own convention
(load-bearing choice with a rejected alternative), slice 110-01 should record it
as an ADR — proposed title *"Adversarial-register quarantine: orchestrator-facing
surfaces are collaborative; sharp language stays in the discarded subagent
context."* Flagged for the owner at DRAFT review.

## Assumptions

- **A1 (load-bearing, contested).** The conversational-gatekeeping symptom is
  caused by **operational context-bleed** of the adversarial register (reading
  review bodies / corpus / verdicts), *not* by the always-loaded priming.
  *Grounding:* two independent register audits found the always-on surfaces lean
  (this session's scaffold-wide sweep; the reporter's comment 2), and two
  observed instances (issue body + comment 1) show the stance in plain
  conversation with no reviewer involved. *Not experimentally proven:* the
  within-project before/after (jig scaffolded in as the single changed variable)
  is still being read; the early baseline lacked an active review gate, so
  causality is not yet conclusive. **Kill criterion:** if the before/after shows
  no stance shift at the scaffolding line even in register-heavy sessions, the
  premise is wrong and softening the surfaces will not move the symptom — stop
  and re-frame.
- **A2 (grounded).** Softening orchestrator-facing *prose* does not weaken any
  actual gate, because the gates are enforced by `.py` helpers via exit codes
  (e.g. `jig-spec-gate.sh`, the review-evidence gate in `workflow.py
  transition`, `bug.py`'s teeth), out-of-band from the prose the orchestrator
  reads. *Probe at implementation:* enumerate the gate helpers and confirm each
  refusal is a code exit, not a prose instruction, before rewording any "you
  refuse…" narration (slice 110-03).

## Decomposition

**SPIDR — Rules axis, keystone-first.** Each slice changes an
orchestrator-facing surface and delivers standalone behavioural value (the
agent's standing posture is the "user-facing layer" here); none is horizontal
phasing. Sharp language inside the *generated subagent prompts* is out of scope
to change — it is already quarantined and must stay sharp.

- **110-01 — Posture boundary (keystone).** The single explicit statement:
  adversarial review is a *named, bounded operation*; outside it the default
  posture is collaborative and solution-forward — answer what's asked, propose
  routes, don't manufacture blockers. Placed where the orchestrator reads it:
  the scaffolded primer (`templates/CLAUDE.md.template` + `AGENTS.md.template`)
  and a short pointer at the top of the review-heavy SKILL bodies. Records the
  keystone ADR. [lever 2a]
- **110-02 — De-weaponize the corpus premise.** General guidance: recorded
  decisions are context to **reconcile against**, not ammunition to **refuse
  with**; when a user's idea conflicts with a record, surface and explore, don't
  block. Includes the amendment-authorization wording pass
  (`spec-workflow/SKILL.md` amend-lead + its hot-cache `CLAUDE.md` twin: lead
  with reconcile, reframe "surface and stop" as "escalate to owner").
  **Owner-approval-gated** surfaces (conventions-adjacent hot cache, the spec
  102 guardrail) are drafted but not applied without sign-off. [lever 2b]
- **110-03 — Put the "no" on the tooling; tone-pass the review bodies.** Rewrite
  orchestrator-facing SKILL prose that narrates refusal as the *agent's* job
  ("you refuse to advance…") so the helper/exit-code is the gatekeeper and the
  agent stays collaborative; soften only the orchestrator-read parts of the
  review-heavy bodies (`independent-review`, `spec-workflow`, `bug-fix`) —
  the generated subagent prompts stay as sharp as wanted. [levers 2c + 2d]
- **110-04 — Delegate-as-quarantine.** Extend thin-orchestrator
  ([spec 057](../057-thin-orchestrator/spec.md)) / context-cost-discipline
  ([spec 055](../055-context-cost-discipline/spec.md)) guidance to **name the
  second reason** for delegation: delegating file-heavy reading to a subagent
  keeps the review/verdict register out of the orchestrator's context, not only
  tokens. Prioritize the highest-register files (`reviews/*-frame-critique.md`,
  adversarial skill bodies) for delegate-and-summarize. Name the honest tension:
  delegating *all* reading weakens grounding (jig's core value), so "delegate
  the bulk + the adversarial-register files; keep the minimum first-hand reading
  grounding genuinely needs" — and de-toning the source (110-02) is the real fix
  for the reading that must stay first-hand. [lever 3]

**Ordering.** 110-01 is the keystone (states the principle + ADR). 110-02–04 can
proceed in parallel after it; 110-04 references the reconcile framing 110-02
establishes.

## Slices

- [110-01 — posture boundary + keystone ADR](slice-01-posture-boundary.md)
- [110-02 — de-weaponize the corpus premise](slice-02-deweaponize-corpus.md)
- [110-03 — no-on-the-tooling + tone-pass review bodies](slice-03-tooling-owns-no.md)
- [110-04 — delegate-as-quarantine](slice-04-delegate-as-quarantine.md)
