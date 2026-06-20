---
status: Proposed
dependencies: [033-05, 057-01]
last_verified: 2026-06-17
frame_review: true
---

# ADR-0027: Host-native phase modes are advisory workflow affordances

## Status

Proposed (2026-06-17)

## Context

Jig already has a durable workflow model: specs, slices, review evidence,
state transitions, deviation logs, and ADRs. A discussion on 2026-06-17 raised
whether jig should lean more deliberately on native LLM host modes, especially
the planning and implementation phases exposed by Codex and Claude Code.

The idea fits several existing jig threads:

- [Spec 033](../specs/033-host-adapter-portability/spec.md) already frames
  Codex and Claude as host adapters over one workflow model, with
  host-native rendered files and no universal runtime import layer.
- [Spec 057](../specs/057-thin-orchestrator/spec.md) showed that the
  orchestrator should plan delegation up front and then dispatch/integrate
  compactly. Native Plan mode is a natural host UX for that front-loaded
  planning surface.
- Jig's review-evidence model ([ADR-0014](adr-0014-review-evidence-model.md))
  and gate model ([ADR-0011](adr-0011-spec-gate-model.md)) deliberately keep
  lifecycle truth in versioned artifacts and deterministic helpers rather than
  ephemeral chat state.

The tension: native modes can improve the human/agent rhythm, but they are
host-specific, UI-shaped, and not durable evidence. A mode-aware jig could feel
much better to use; a mode-dependent jig would recreate the drift jig exists
to prevent.

## Decision Options Considered

### Option A: Replace jig lifecycle phases with host modes
- **Pros:** Maximum use of the host UX; fewer jig-specific words for users to
  learn; planning and editing phases become visually obvious in the tool.
- **Cons:** Host modes are not portable across Claude and Codex, are not
  versioned in the repo, and are not reliable review or transition evidence.
  This would create a second source of truth beside specs and slices.

### Option B: Ignore host modes entirely
- **Pros:** Keeps jig fully artifact-first and avoids dependence on moving
  host features.
- **Cons:** Leaves a useful host affordance on the floor. It also misses the
  alignment between Plan mode and jig's own thin-orchestrator/session-plan
  discipline.

### Option C: Make jig mode-aware but not mode-dependent
- **Pros:** Uses native modes where they help: clarify, decompose, present the
  session plan, execute a slice, review, and land. Keeps all lifecycle truth in
  specs, slices, ADRs, and review artifacts. Fits spec 033's host-adapter
  boundary.
- **Cons:** Adds adapter prose and possible branching UX. If overdone, it can
  still create "chat plan vs. spec plan" drift unless the spec remains the
  canonical record.

## Recommended Decision

Adopt **Option C: mode-aware, not mode-dependent**.

Jig should treat host-native planning / implementation modes as advisory
workflow affordances rendered by host adapters, not as lifecycle state and not
as gate inputs.

Concretely:

1. **Artifacts stay canonical.** Specs, slice frontmatter, review evidence,
   ADRs, and generated status boards remain the only durable workflow truth.
   A chat-mode transition never satisfies or bypasses a jig transition gate.
2. **Host adapters may render phase hints.** Claude and Codex adapters may
   say "use Plan mode for this phase" or "switch to implementation/editing
   mode for this phase" in prompt cookbooks, generated primers, skill text, or
   `workflow.py session-plan` output.
3. **The host-neutral vocabulary is small.** The portable phases are:
   `plan`, `implement`, `review`, `reconcile`, and `land`. Adapters map those
   to host-native concepts when available and degrade to plain prose when not.
4. **Plan output must land in artifacts.** A useful native-mode plan becomes a
   spec, slice, ADR, task list, or deviation log before jig relies on it. The
   accepted plan is not "the chat said so"; it is "the artifact was updated."
5. **No hard gate depends on mode state.** Jig does not require proof that
   Codex Plan mode or Claude Plan mode was active. Host modes are a UX and
   safety layer inside the interaction, not evidence for ADR-0014 gates.

The first implementation home is a parked spec,
[Spec 074](../specs/074-host-native-phase-modes/spec.md), not a retrofit into
the current Claude-only flow. The trigger is the next real host-portability
or Codex adapter push, or repeated user friction showing that jig's current
prompt cookbook hides the intended plan-then-implement rhythm.

## Consequences

**Becomes easier:**
- Codex and Claude users get a clearer rhythm: plan the work, commit the plan
  into specs/slices, then implement against the accepted artifact.
- `workflow.py session-plan` can become the bridge between jig's durable model
  and the host's native planning surface.
- Jig can improve UX without weakening the review-evidence and transition
  gates.

**Becomes harder:**
- Host adapters need to carry mode mapping prose and tests so Claude and Codex
  do not drift.
- Users may still confuse an accepted chat plan with an accepted spec unless
  the docs are explicit that artifacts are the ledger.
- Exact host-mode semantics must be re-verified before implementation, because
  they are product surfaces rather than jig-owned contracts.

## Assumptions

- Current jig docs already establish the relevant ground: spec 033 owns the
  host-adapter boundary, spec 057 owns thin-orchestrator planning, and
  ADR-0014/ADR-0011 own the evidence/gate model. Verified by reading those
  artifacts on 2026-06-17.
- The exact Codex and Claude host-mode contracts are intentionally **not**
  treated as verified here. They must be re-checked against official/current
  host behavior when Spec 074 is picked up.

## Kill criteria

- If host modes become machine-readable, stable, and portable enough to serve
  as evidence, reconsider whether some advisory hints should become optional
  checks. The default should still be artifact-first.
- If mode hints create duplicate planning surfaces or confuse users into
  treating chat as the source of truth, remove the hints and keep the workflow
  purely artifact-driven.
- If Codex or Claude removes or substantially changes the relevant mode
  surfaces before implementation, keep the adapter text prose-only.

## Open questions

- Should `workflow.py session-plan` grow an optional host-mode column, or
  should mode hints live only in rendered host primers and prompt cookbooks?
- Should the Codex adapter expose these hints differently from the Claude
  adapter, given different UX and tool-permission surfaces?
- Should `review` be modeled as a separate phase hint, or is it simply
  `plan` plus read-only tool capability?
- Should accepted native-mode plans ever be copied into a generated
  `plan.md`, or should specs and slices remain the only durable planning
  artifacts?
