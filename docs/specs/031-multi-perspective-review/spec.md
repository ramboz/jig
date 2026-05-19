---
status: IN_PROGRESS
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 031: multi-perspective review in the spec-workflow

## Overview

Every spec slice goes through one review pass today — `jig:independent-review`,
a spec-compliance check (does the implementation meet the ACs?). That's the
*contract* review. There are two other review lenses that should also fire on
the same deliverable:

- **Craft / PR review** — is the code well-structured, idiomatic, free of
  nits? Jig ships `jig:pr-review` (baseline) which already defers to a richer
  user-installed `pr-review` if one is present, but **the workflow never
  triggers it**. Today the user has to remember to invoke it manually.
- **Architecture review** — does the change preserve module boundaries and
  public contracts? Jig ships `jig:arch-review` (baseline) with the same
  deferral pattern, but again, **the workflow never triggers it**.

This spec wires both into the post-implementation flow. `pr-review` runs on
every slice (it's a craft check — always relevant). `arch-review` runs
on demand, gated by a declarative frontmatter flag on the slice (most slices
don't change architecture; gating prevents pointless arch reviews).

The deferral mechanism for both already exists in the skill descriptions
(see [012-01](../012-pr-review/slice-01-pr-review-skill.md) and
[014-01](../014-arch-review/slice-01-arch-review-skill.md)). The
spec-workflow just needs to invoke the right skill at the right time.

## Why now

- **The user just asked.** Mid-session today (2026-05-18), spec 030
  reconciliation surfaced that `jig:independent-review` was the only review
  pass that ran on slice 030-01 — the user observed that their richer
  installed `pr-review` skill would have been a better fit for the craft
  concerns and that arch-review never fired either.
- **The wiring is small.** Both `jig:pr-review` and `jig:arch-review`
  already exist and already defer to richer installed skills. The work is
  almost entirely in `skills/spec-workflow/` (SKILL.md prose + review.py
  prompt builders) plus the slice-frontmatter flag for arch-review.
- **No new skills.** This spec is plumbing, not new functionality. Both
  review skills exist; we're just calling them at the right time.
- **The pattern generalizes.** Once two passes are wired alongside the
  compliance pass, a third (e.g., security-lens per inbox 2026-05-12) is
  the same shape.

## Goals

1. **Post-implementation pr-review pass.** After the implementer finishes
   a slice (slice transitions IN_PROGRESS → REVIEWED is the gate),
   `spec-workflow` instructs the orchestrator to also run a `pr-review`
   pass against the deliverable. The pass routes to the most-specific
   installed `pr-review` skill (user's > `jig:pr-review`). Output:
   scope / blockers / nits / strengths.

2. **On-demand arch-review pass.** Slices gain a frontmatter field —
   `arch_review:` (boolean) — defaulting to `false`. When set to `true`
   on a slice, the post-implementation flow ALSO runs an `arch-review`
   pass. Routes to the most-specific installed `arch-review` skill
   (user's > `jig:arch-review`). Output: summary / strengths / concerns /
   open questions.

3. **Verdict-shaped output for lifecycle gating.** Both passes return
   structured verdicts that the workflow can consume to drive the
   IN_PROGRESS → REVIEWED transition. This means **either** (a) the
   pr-review/arch-review SKILL.md outputs are reshaped to match the
   `jig:independent-review` VERDICT / REASONING / SPECIFIC ISSUES
   contract, OR (b) `review.py` gains prompt builders that wrap the
   underlying skill's concerns in the verdict envelope. **Lean (b).**
   The skill stays free-form for direct invocation; only the
   workflow-invoked path is verdict-shaped.

4. **Failing the craft pass blocks REVIEWED.** Same gate semantics as
   the compliance pass — a `fail` verdict from pr-review keeps the slice
   at IN_PROGRESS. The implementer addresses findings and re-runs.
   (Open question: do nits block? Lean: only `blockers` block; nits
   become reconciliation-log entries.)

5. **Skill-deferral resolver.** `review.py` (or a small helper) detects
   which installed skill should handle a given pass. Precedence rule:
   user-scope skill (`~/.claude/skills/<name>/`) > project-scope
   (`.claude/skills/<name>/`) > jig-bundled (`jig:<name>`) >
   `general-purpose` fallback. Same pattern jig already uses elsewhere.

6. **SKILL.md updated.** `skills/spec-workflow/SKILL.md` § "After
   implementation" describes the three review passes (compliance,
   craft, optional arch) and the order in which the orchestrator
   should fire them.

## Non-goals

- **No new review skills.** We don't ship a "security-lens" pass or any
  other persona here. The inbox 2026-05-12 security-lens entry plugs
  into this scaffolding once it crystallizes.
- **No re-engineering of `jig:pr-review` or `jig:arch-review`.** Both
  stay as judgment-skills. We invoke them; we don't rewrite them.
- **No reconciliation-pass wiring for craft/arch reviews.** The
  reconciliation pass remains a `jig:independent-review` pass against
  the deviation log. Multi-perspective is post-impl only.
- **No `arch_review:` auto-detection.** The flag is declarative — slice
  author or implementer sets it explicitly. We don't try to infer
  "this slice touches architecture" from file patterns.
- **No CLAUDE.md hygiene changes.** Spec 025 owns that.
- **No ADR (probably).** Skill-deferral resolver is a localized
  pattern, not a hard-to-reverse decision. Revisit if the resolver
  shape turns out wrong.

## Decomposition

Two slices. The first lays the pattern (post-impl multi-pass wiring +
pr-review pass + skill-deferral resolver). The second extends with the
arch-review on-demand trigger, reusing slice 1's plumbing.

| Technique | Question | Outline |
|---|---|---|
| **S** — Spike | Spike on "how does Claude's skill-routing layer resolve user > project > plugin precedence?" Or "what does Claude do when two skills match the same auto-trigger phrase?" | **Possibly.** Today jig's skills self-describe their deferral via SKILL.md prose ("Defers to any other installed skill whose description identifies it as ..."). Whether that's enough OR whether `review.py` needs to do filesystem detection is the open question. Lean: try the prose-only path first (let Claude resolve), spike only if the prose-only path mis-fires. |
| **P** — Path | Wire both passes at once, or staged? | **Staged.** Slice 031-01 = pr-review (always-on, simple trigger). Slice 031-02 = arch-review (on-demand, frontmatter-gated, builds on 031-01's pattern). |
| **I** — Interface | Where do the new passes hook in — SKILL.md prose, `review.py` builders, or a new orchestrator helper? | **SKILL.md + `review.py`.** SKILL.md adds the orchestrator instructions; `review.py` gains `pr-review` and `arch-review` prompt-builder modes. The orchestrator (parent Claude) does the dispatch by reading SKILL.md. No new helper script. |
| **D** — Data | What's the input shape for each pass? What's the verdict shape? | Input for both: spec path + slice fragment + deliverable file paths (same as `jig:independent-review`'s mode signature). Verdict shape: same canonical VERDICT / REASONING / SPECIFIC ISSUES / RECONCILIATION NOTES format — the prompt builder wraps the underlying skill's concerns inside this envelope. |
| **R** — Rules | What governs the order of passes? What blocks the IN_PROGRESS → REVIEWED transition? | Order: compliance first (sharp pass/fail), then craft (most slices have nits), then arch (only when flagged). Block rule: any pass returning `fail` blocks. `needs-changes` blocks for compliance, surfaces as reconciliation notes for craft / arch. `pass` from all required passes (compliance always, craft always, arch when flagged) is the gate. |

### Slices

- [031-01 — pr-review-pass](slice-01-pr-review-pass.md) — DRAFT — post-implementation craft pass via `pr-review` skill
- [031-02 — arch-review-trigger](slice-02-arch-review-trigger.md) — DRAFT — on-demand arch pass gated by slice frontmatter

## Out of scope for spec 031 (any slice)

- **Security-lens pass** (inbox 2026-05-12) — separate concern; this
  spec doesn't ship the security lens. The plumbing from 031-01 +
  031-02 should make security-lens an easy follow-on if/when the
  parent decision settles.
- **Reconciliation-pass multi-perspective.** Reconciliation review is
  about deviation-log fidelity, not craft/arch. Stays single-pass.
- **Auto-detection of `arch_review:` triggers.** A future slice could
  scan slice deliverables for architectural impact (e.g., touched
  files include `docs/architecture.md` or any `**/contracts/**`). Not
  in this spec.
- **Replacing `jig:independent-review`.** The compliance pass stays
  intact and primary. Craft + arch are *additional*, not substitute.

## Open questions

- **Skill-routing dispatch.** Two implementation paths:
  (a) SKILL.md instructs the orchestrator to invoke the skill by name
  (`Skill("pr-review", ...)`) — Claude's routing handles user > plugin
  precedence. Simplest.
  (b) `review.py` filesystem-detects installed skills and returns the
  highest-precedence one — orchestrator uses that. More deterministic
  but reinvents the routing layer.
  **Lean: (a)**. Try first. Fall back to (b) only if (a) misroutes.
- **Nits as blockers.** Reviewer output today includes
  `SPECIFIC ISSUES`. For pr-review's craft findings, does every
  `SPECIFIC ISSUES` entry block, or only `blockers`-tagged entries?
  Lean: tag entries `blocker | nit | strength`; only `blocker` gates
  the transition. Nits become reconciliation-log items.
- **Combined verdict.** Three pass results (compliance, craft, arch)
  → one transition decision. Combine rule: AND across required
  passes. A `fail` anywhere = block. `needs-changes` from craft =
  proceed to REVIEWED, surface as reconciliation note.

## References

- **Originating conversation:** 2026-05-18 — user asked "any reason
  the jig independent reviewer was used over the more specialized
  pr-review skill I have? ideally we wanted to defer to that one
  instead by default when the workflow and router see it" and "I
  also need an arch-review to be triggered as part of the workflow
  as needed."
- **Slice 012-01 — pr-review-skill:** established `jig:pr-review`
  with the deferral pattern. This spec consumes that skill.
- **Slice 014-01 — arch-review-skill:** established `jig:arch-review`
  with the same pattern. This spec consumes that skill.
- **Slice 004-01 — review-helper:** established `review.py`'s prompt-
  builder pattern. The new pr-review / arch-review modes extend it.
- **Slice 003-04 — auto-tick-review-passed-on-transition:** REVIEWED
  transition auto-ticks "Implementation review passed." With multi-
  perspective, this needs to mean "all required passes passed" —
  potentially a structural touchpoint.
- **Inbox 2026-05-12 (security-lens-integration):** identifies the
  generalization. Security-lens is one persona; pr-review + arch-
  review are two more. Same plumbing.
- **Inbox 2026-05-12 (multi-persona-reviewer):** the parent question.
  Option (a) shipped via specs 012 + 014. Spec 031 is the wiring that
  makes option (a) actually fire automatically.
