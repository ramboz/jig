# Research: Spec-Driven Development and SPIDR

> Reference notes from the design phase. Pull into context only when relevant.

## Why spec-driven?

LLMs are exceptional at pattern completion, not mind reading. A vague prompt forces the model to guess at unstated requirements; some guesses will be wrong, and you won't discover which until deep into implementation. A clear specification up front gives the agent more clarity, improving efficacy.

cc-sdd's framing is the sharpest: **"Specs are contracts between parts of the system, not master command documents handed to the agent. Code remains the source of truth. Specs make the boundaries between parts of the code explicit so humans and agents can work in parallel without constant synchronization."**

This is much better than "spec = exhaustive requirements doc." Specs as **contracts at the right granularity** is the framing we adopt.

## SPIDR — Mike Cohn's five story-splitting techniques

Cohn analyzed 1000+ user stories and grouped the splitting patterns into five techniques, forming the acronym SPIDR.

### S — Spike (last resort, not first)

A **research/learning activity**. Used when the team needs to acquire knowledge before they can split the story properly. Example: "Should we use commercial captioning software or build our own?" → spike to evaluate before committing.

**Important nuance:** Spike is the *last resort* of the five techniques, not the first. AI-native dev often inverts this — agents reach for "let me research this" too quickly. **Our `spec-workflow` skill enforces the correct ordering:** try Rules, Data, Interface, Path first; Spike only when none apply.

### P — Path

Split by alternative paths through the story. Happy path first; edge cases and alternative flows in later slices.

Example: "User uploads video" → first slice is the happy path (valid file, network works, single user). Second slice handles errors. Third handles concurrent uploads.

### I — Interface

Split by UI / platform / channel. Minimal UI first, polish later. Or one platform first (iOS), others later (Android, web).

Example: "User can search products" → first slice is a plain HTML form with text results. Second slice adds filters. Third adds suggestions.

### D — Data

Split by data subset or format. Process less data in the first slice.

Example: "Support video uploads in any format" → first slice supports MP4 only. Later slices add the other 15 formats. Or: "Bank account balance can be any value" → first slice forbids negative balances; second slice handles overdrafts.

### R — Rules

Split by business rules. Simple rules first, edge cases later.

Example: "Tax calculation supports all US states" → first slice handles flat-rate states. Second slice handles tiered. Third handles states with city/county overrides.

## The vertical slicing principle

The thing SPIDR is really enforcing is **vertical slicing** — each slice crosses all layers (DB + service + UI) and delivers value end-to-end.

**AI's default failure mode is horizontal phasing:** "DB phase, then API phase, then frontend phase." This delays end-to-end feedback and creates large rework when integration reveals problems.

**Our `spec-workflow` skill has an explicit anti-horizontal-phasing guardrail.** A check that runs after split: if any slice doesn't touch the user-facing layer, that's a smell. Either it's a spike (allowed, but explicit) or the split needs reworking.

## Spec lifecycle states

```text
DRAFT
  ↓ (spec written, ready for review)
READY_FOR_REVIEW
  ↓ (independent reviewer pass on spec)
READY_FOR_IMPLEMENTATION
  ↓ (implementer picks up slice)
IN_PROGRESS
  ↓ (implementer done, deliverable on disk)
REVIEWED
  ↓ (independent reviewer pass on implementation)
RECONCILED
  ↓ (docs updated, deviation log produced, reconciliation review pass)
DONE
```

Each transition is a deterministic checkpoint. Hooks enforce the gates between states.

## References we mined

### GitHub Spec Kit

Phases: Specify → Plan → Tasks → Implementation. Each phase produces markdown artifacts.

Useful patterns we adopt:

- `constitution.md` for project principles (we call it `conventions.md`).
- Task breakdown organized by user story.
- Tasks marked `[P]` for parallel execution.
- Dependency management built into task ordering.

Less useful:

- The four-phase workflow is rigid. We prefer a state machine over a phase sequence.
- Spec Kit's commands are explicit (`/speckit.specify`, `/speckit.plan`) — opposite of our auto-trigger preference.

### cc-sdd

Closest reference to our v1. Key design choices we adopt:

- `/kiro-discovery` as entry point: routes new work into "extend existing spec / implement directly / create new spec / decompose into multiple specs." We adopt the discovery routing pattern in our `scaffold-init` wizard.
- Specs as contracts framing.
- Phase gates with human approval.
- Per-task fresh implementer + independent reviewer + auto-debug pass.
- 17 skills per install with progressive disclosure.

Less useful:

- 17 skills is at the upper bound of cognitive load. Our 8-12 is on the right side of this.
- Multi-harness support (Cursor, Codex, Copilot, etc.) — we defer to v2.

### Pimzino/claude-code-spec-workflow

Requirements → Design → Tasks → Implementation; plus a streamlined Report → Analyze → Fix → Verify for bug fixes. Useful for the bug-fix split — we may add a `bug-workflow` skill in Tier 1.

## Definition of Done per slice

Every spec slice has explicit acceptance criteria. Template:

```markdown
## Definition of Done

- [ ] All listed acceptance criteria pass
- [ ] Tests written and green (TDD discipline)
- [ ] Code reviewed by independent reviewer agent
- [ ] Contract tests pass (if module boundary touched)
- [ ] Deviation log produced (if any deviations)
- [ ] Reconciliation review pass
- [ ] No outstanding TODOs in modified files
```

This is what the Stop hook checks before allowing completion.

## Source signals

- Mike Cohn on SPIDR: <https://www.mountaingoatsoftware.com/blog/five-simple-but-powerful-ways-to-split-user-stories>
- GitHub Spec Kit: <https://github.com/github/spec-kit>
- cc-sdd: <https://github.com/gotalab/cc-sdd>
- Pimzino spec workflow: <https://github.com/Pimzino/claude-code-spec-workflow>
- Spec-driven dev (GitHub blog): <https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/>
