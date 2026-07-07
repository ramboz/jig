---
status: Proposed
dependencies: []
last_verified: 2026-07-06
frame_review: true
---

# ADR-0035: Active Plan-mode driving for the plan phase (extends ADR-0027)

## Status

Proposed (2026-07-06)

## Context

[ADR-0027](adr-0027-host-native-phase-modes.md) adopted **mode-aware, not
mode-dependent**: host planning/implementation modes are *advisory* affordances,
never lifecycle state or gate inputs. [Spec 074](../specs/074-host-native-phase-modes/spec.md)
shipped that in full (all slices DONE) — portable phase vocabulary in
`docs/workflow.md` + `docs/prompts.md`, per-phase host-mode **hints** in
`workflow.py session-plan`, and host-native primer substitutions
(`phase_mode_substitutions()` in `scaffold.py`) for both Claude and Codex. The
capability is universal, not scoped to any adopter cohort.

The limit ADR-0027 chose deliberately: everything is **advisory** — jig
*suggests* Plan mode and prints "(advisory only)", but never drives the host into
it and never leverages the host's plan primitive concretely. An advisory hint is
easy to ignore, so "route work through Plan mode" is delivered as guidance rather
than rhythm. This ADR pushes exactly one rung deeper — from *suggest* to
*actively drive* — for the **plan phase only**, while preserving ADR-0027's
invariant intact.

Boundaries fixed by prior discussion (2026-07-06):

- **The invariant is non-negotiable and carries over unchanged:** artifacts stay
  canonical; host mode/plan state *never* satisfies or bypasses a jig gate. This
  is a change to *how actively jig uses the affordance*, not a step toward
  mode-as-evidence (ADR-0027's rejected Option A / kill-criterion #2).
- **Granularity is settled: slice → plan is primary.** A slice is the natural
  size of one Plan-mode session (shape the approach, confirm unknowns, decide the
  next action, then implement) — just-in-time, matching the
  [spec 057](../specs/057-thin-orchestrator/spec.md) thin-orchestrator rhythm and
  jig's vertical-slice model. Mapping a whole spec to a single plan was rejected:
  it means planning a multi-slice feature up front — the waterfall-shaped big plan
  vertical slicing exists to avoid. The **spec-level SPIDR decomposition** is a
  legitimate *second, coarser* Plan-mode moment (a breakdown plan, once per spec,
  at authoring), not a per-spec identity.
- **No task/todo-primitive mapping.** Considered and pulled back: the host
  task/todo primitive is an *ephemeral, session-scoped* checklist, while slices
  are *durable, cross-session* units — mapping slices onto it mismatches altitude
  and duplicates the status board (jig's existing durable slice view). This ADR
  stays at the plan level.

This ADR **extends and partially supersedes ADR-0027** — it changes *only* the
plan-phase disposition (advisory → active driving). ADR-0027's invariant and its
advisory posture for `implement / review / reconcile / land` remain in force. It
is the deeper-integration companion to [ADR-0034](adr-0034-lower-interaction-altitude.md)
(interaction altitude), which explicitly disclaims owning Plan-mode routing.

**Feasibility is genuinely uncertain and load-bearing.** ADR-0027 flagged host
modes as *product surfaces* to re-verify. "Driving" (vs. suggesting) may not be
fully programmatic: a skill can propose a plan and call `ExitPlanMode`, but
*forcing* the client into plan mode likely is not possible, and Codex differs
from Claude. How far this ADR can actually reach is capped by a spike, not
decided by fiat.

## Decision Options Considered

### Option A: Stay advisory (ADR-0027 status quo)
- **Pros:** zero added host-coupling; portable; simplest; already shipped.
- **Cons:** the hint is trivially ignored, so the plan-then-build rhythm is
  delivered as guidance, not practice; does not satisfy the "route work through
  Plan mode" intent when the hint goes unheeded. **Rejected** as insufficient for
  the stated goal.

### Option B: Active Plan-mode driving for the plan phase (this ADR)
jig actively drives the plan phase into the host planning surface and lands the
plan into canonical artifacts; all else stays advisory; nothing becomes a gate.
- **Pros:** delivers the rhythm rather than nudging toward it; scoped to one
  phase; preserves the ADR-0027 invariant and single-source-of-truth; extends
  spec 074's existing machinery.
- **Cons:** takes on real host-coupling (a product surface, not a jig contract);
  reach is feasibility-capped; must actively guard against the duplicate-planning-
  surface risk ADR-0027 kill-criterion #2 names.

### Option C: Full mode-dependent + task-mapping (ADR-0027's rejected Option A)
Host mode/plan/task state becomes lifecycle evidence; slices map to task
primitives; two-way sync.
- **Cons:** recreates the drift jig exists to prevent; non-portable; a second
  source of truth. The user pulled back from task-mapping explicitly.
  **Rejected** (and off-limits by ADR-0027's kill criteria).

## Recommended Decision

**Adopt Option B.** Change only the plan-phase disposition from advisory to
active driving; everything else in ADR-0027 stands.

1. **Two drive points, plan-level only:**
   - **Slice → plan (primary, recurring).** When a slice is picked up, jig's plan
     phase actively uses the host planning surface to shape the approach / confirm
     unknowns / decide the next action; the plan **lands in the slice** (approach
     notes / confirmed DoD), then the slice goes `IN_PROGRESS`.
   - **Spec → decomposition plan (secondary, once per spec).** SPIDR splitting at
     authoring is done in the planning surface; output lands in `spec.md` + the
     slice files.

2. **No task/todo-primitive mapping.** If it is ever revisited, the recorded
   shape is **current-slice ACs → session todos, one-way** (never slices → tasks,
   never two-way) — deferred, demand-gated. Not built here.

3. **Reach is feasibility-capped and degrades gracefully**, best-effort down a
   ladder: *drive the host into plan mode* → else *operate plan-first and use
   `ExitPlanMode` to surface and land the plan* → else *advisory* (ADR-0027 status
   quo). A **required spike** (precondition, below) fixes the achievable rung per
   host (Claude Code + Codex) before any build.

4. **Invariant preserved (from ADR-0027):** host mode/plan state never satisfies
   or bypasses a transition, review-evidence, or dependency gate; the spec, slice
   frontmatter, review evidence, and status board remain the sole durable record;
   the host planning surface is a driver, **never a second planning ledger.**

5. **Home:** extend spec 074's already-shipped host-adapter rendering /
   `phase_mode_substitutions()` machinery rather than a greenfield surface.

**Precondition — feasibility spike (blocks acceptance).** Before this ADR is
accepted or any slice is built, spike what is *programmatically drivable* in
Claude Code and Codex: can a skill enter plan mode, or only propose-a-plan +
`ExitPlanMode`? What is the `ExitPlanMode` contract? What is the graceful
fallback when the primitive is absent or changed? The spike output sets the
ADR's real ceiling; if driving proves impossible on both hosts, this ADR reduces
to Option A and is withdrawn.

## Consequences

**Becomes easier:**
- The plan-then-build rhythm becomes practice, not a skippable hint — the spec
  057 thin-orchestrator win lands per slice, for all users.
- Extends existing, shipped machinery (spec 074) rather than adding a parallel
  surface.

**Becomes harder:**
- jig takes on deeper coupling to a host **product surface** it does not own;
  more exposure to host changes (mitigated by the graceful-degradation ladder).
- Active driving amplifies the duplicate-planning-surface risk; the "plan lands
  in the artifact, host surface is never a ledger" rule (§4) is the load-bearing
  mitigation and must be enforced, not assumed.
- The plan phase's UX now differs by host; adapter prose + tests must track two
  moving surfaces.

## Assumptions

- **Active driving is programmatically possible (or meaningfully approximable) on
  the hosts.** Explicitly *unverified* — the spike tests it; the decision is
  gated on it, not asserting it.
- **Active driving is materially better than advisory** — i.e. the advisory hint
  is being ignored often enough that driving changes behavior. Plausible but not
  measured; a frame-critique should attack this (if advisory already suffices,
  Option B buys host-coupling for little gain). ADR-0027 kill-criterion #2 is the
  backstop.
- **The plan-lands-in-the-artifact rule actually prevents the second-ledger
  failure** in practice, not just on paper.
- The host plan primitives are stable enough to justify deeper dependence than
  ADR-0027 assumed (a real step up in exposure).

## Kill criteria

- If the spike shows the primitives aren't drivable on either host, reduce to
  Option A (advisory); ADR-0027 stands and this ADR is withdrawn.
- If active driving produces the duplicate-surface / chat-as-source-of-truth
  confusion ADR-0027 warned of, revert the plan phase to advisory.
- If host changes to the plan primitive repeatedly break jig's driving, drop to
  prose-only advisory (ADR-0027 kill-criterion, inherited).

## Open questions

- Exact per-host mechanism and fallback rung (spike output).
- What "the plan lands in the slice" is concretely — an approach-notes section, a
  DoD confirmation step, or a deviation-log seed?
- Does spec-level SPIDR driving warrant the same active treatment, or stay
  advisory given its low frequency?
- Interaction with the read-only reviewer passes — `review` stays advisory
  (ADR-0027 OQ#3 unresolved); confirm no coupling leaks in.
