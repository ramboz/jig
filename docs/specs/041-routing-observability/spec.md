---
status: DONE
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 041: Skill-routing observability — trace which skill actually fired

## Overview

Specs 012 (pr-review), 014 (arch-review), 022 (contracts), and 031
(multi-perspective review) all rely on **category-based deferral via
SKILL.md description prose**: jig ships a baseline skill whose
description includes "Defers to any other installed skill whose
description identifies it as handling X." Claude Code's skill router
is supposed to prefer the more-specific user-installed skill.

Spec 031 Open question #1 named two paths: (a) prose-only dispatch and
(b) filesystem-detect installed skills. Shipped (a) with "fall back to
(b) only if (a) misroutes."

**Path (a) is unobservable.** `jig-telemetry.sh` fires on `PreToolUse/Task`
only (line 3 + `hooks/hooks.json`). It does not log skill routing
decisions. The Claude Code skill router is internal; jig cannot
introspect which SKILL.md it picked.

Two refinement-todo entries already capture this gap:

- "Skill telemetry granularity" — telemetry is imprecise.
- "Skill-routing observability" — no visibility into which skills fire
  when, whether deferral hints work. Resolution trigger: "first
  observable routing mismatch" — which is **unobservable by
  construction** if you can't see which skill fired.

This spec replaces the unobservable trigger with a measurable one by
adding the trace.

## Reconciliation note (2026-06-01 partial → 2026-06-02 completed)

A `PreToolUse`/`Skill` observability hook shipped ahead of this spec's
formal slice transitions. Deviations from the drafted plan, recorded here
because spec 041 was still DRAFT when they shipped (inline correction per
ADR-0010):

- **Approach (Goal 1):** the routing trace shipped as a **new**
  `hooks/scripts/jig-skill-trace.sh` on `PreToolUse`/`Skill`, NOT as an
  extension of `jig-telemetry.sh` on `UserPromptSubmit` — crossing the
  "No new hook events" non-goal. Rationale: `PreToolUse`/`Skill` carries
  `tool_input.skill_name` and captures *implicit* (auto-triggered) routing
  — the actual question — which `UserPromptSubmit` cannot (this spec's own
  Q1, now verified). The hook shares `.claude/skill-usage.jsonl`; readers
  must filter `event == 'skill_invoked'` (Task-spawn entries lack
  `skill_name`).
- **Scope boundary:** the file-read dispatch added to `review.py`
  (`detect_richer_skill()`) belongs to the *separate* craft-pass dispatch
  fix, NOT this spec. 041's "No filesystem detection in review.py" non-goal
  was about detection-for-observability and still holds for 041's scope.
- **Closed (2026-06-02):** Goal 2 landed as slice 041-02 —
  `workflow.py routing-stats [--days N]`, a category-split histogram
  (jig baseline vs. richer/"other" per category) read from
  `.claude/skill-usage.jsonl`; reviewed (compliance + craft both `pass`)
  and reconciled. The three deliverables that shipped ahead of slicing are
  now formalized as `slice-01-routing-trace-hook` (the hook),
  `slice-02-routing-stats-helper` (the histogram), and
  `slice-03-deferral-verification-doc` (the verification recipe at
  `docs/skill-routing-verification.md`), all DONE. Both refinement-todo
  entries ("Skill telemetry granularity" + "Skill-routing observability")
  are struck. The three open questions are resolved: **Q1** → implicit
  routing needs `PreToolUse`/`Skill` (not `UserPromptSubmit`); **Q2** →
  category-split including the non-jig "other" column (deferral is invisible
  otherwise); **Q3** → both refinement-todo entries folded together.

## Why now

- **The trigger is unobservable today.** Both refinement-todo entries
  have been parked behind triggers that can't fire without the
  measurement this spec provides.
- **Closes two parked decisions in one spec.** "Skill telemetry
  granularity" + "Skill-routing observability" resolve together
  when this lands.
- **Cheap first cut.** Extending `jig-telemetry.sh` to fire on
  `UserPromptSubmit` and log the prompt prefix + detected slash
  command is a handful of lines.

## Goals

1. **Add a routing trace.** Per user prompt where a jig skill is a
   candidate, record what was loaded for the response. Extend
   `jig-telemetry.sh` to also fire on `UserPromptSubmit`; log
   timestamp + prompt prefix + detected slash command + any explicit
   `/jig:` invocation. Same `.claude/skill-usage.jsonl` file, two
   event sources.
2. **Surface the trace in a helper.** `workflow.py routing-stats
   [--days N]` reads `.claude/skill-usage.jsonl` and produces a
   categorized histogram of which jig skills fired by category.
   Stdout-only; doesn't write anywhere.
3. **Document the deferral-pattern verification path.** A short
   `docs/skill-routing-verification.md` walks through the manual
   reproduction recipe: how to confirm that an installed user-skill
   takes precedence over jig's baseline.

## Non-goals

- **No introspection of the Claude Code skill router itself.**
  Upstream; jig cannot reach it. The trace records *what jig observed
  happening*, not *why the router chose what it chose*.
- **No filesystem detection in `review.py`** (option (b) from spec
  031). Path (a) stays. This spec adds observability *to* path (a),
  not a replacement.
- **No new hook events.** Use existing `UserPromptSubmit` + `Stop`
  surfaces. The deferred `SubagentStart` event stays deferred per
  the existing refinement-todo entry.
- **No retention/rotation logic** for `.claude/skill-usage.jsonl`.
  It appends; consumers can `head -n 1000` or rotate manually. Add
  rotation if it gets ungainly in real use.
- **No alerting on misrouting.** First cut is *visible* routing,
  not *enforced* routing.

## Current state (verified 2026-05-26)

- `hooks/scripts/jig-telemetry.sh` — fires on `PreToolUse/Task` only
  (line 3 comment). Logs Task tool spawns, not skill routing.
- `hooks/hooks.json` — registers the script under `PreToolUse/Task`
  matcher; no `UserPromptSubmit` registration.
- `docs/refinement-todo.md` — both "Skill telemetry granularity"
  and "Skill-routing observability" entries open, with unobservable
  triggers.

## Decomposition

**Suggested SPIDR axis: I (Interface)** primary — two surfaces (hook
that captures, helper that reads). Each is its own slice. The doc is
independent and could ship first.

### Slices (TBD until clarify runs)

1. **`041-01 routing-trace-hook`** — extend `jig-telemetry.sh` to
   fire on `UserPromptSubmit`. Append an entry per submission with
   timestamp, prompt prefix, detected `/jig:` slash command. Update
   `hooks/hooks.json`. Regression tests under existing telemetry
   tests.
2. **`041-02 routing-stats-helper`** — `workflow.py routing-stats
   [--days N]` reads `.claude/skill-usage.jsonl`, renders a
   categorized histogram. Stdout-only. Useful even before slice 1
   lands (against existing Task-spawn logs).
3. **`041-03 deferral-verification-doc`** *(optional)* —
   `docs/skill-routing-verification.md` walks through the manual
   reproduction recipe for confirming a user-installed skill wins
   over a jig baseline. Independent — could ship first as docs-only.

## Open questions for `/jig:clarify`

- **Q1.** Is the `UserPromptSubmit` event payload rich enough to
  detect *implicit* (auto-trigger) skill choices, or only explicit
  `/jig:` slash commands? Probably explicit-only initially. Implicit
  trace may need `SubagentStart` or a future hook — defer until
  upstream supports it.
- **Q2.** Should the histogram include user-installed non-jig
  skills, or jig only? Lean: jig only initially. The point is "did
  jig's baseline fire, or did the deferral work?"
- **Q3.** Should this spec also fold the existing "Skill telemetry
  granularity" entry, or just "Skill-routing observability"? Lean:
  both, since they share a measurement mechanism.

## Dependencies / coordination

- **None hard.** Can run after spec 036 (drift policy) so any docs
  this spec produces follow the chosen amendment convention.
- **Closes two refinement-todo entries.** Reconciliation should
  strike out both ("Skill telemetry granularity" + "Skill-routing
  observability") simultaneously.

## References

- Historical external review input was folded into this spec; the standalone
  source brief was retired.
- `docs/refinement-todo.md` — "Skill telemetry granularity" and
  "Skill-routing observability" entries.
- Verification 2026-05-26: telemetry hook still PreToolUse/Task
  only; both refinement-todo entries still open.
