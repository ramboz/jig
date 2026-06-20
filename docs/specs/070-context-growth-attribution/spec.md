---
status: DONE
skill: context-cost-discipline
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 070: Context-growth attribution

> Reserved on 2026-06-12 via `workflow.py new`. Body to be drafted in a feature branch.

## Overview

jig already knows that `cache_read` dominates token consumption, but the
current reports mostly answer **how much** context was reread, not **why** the
orchestrator context grew. The next useful optimization loop needs attribution
for the two most plausible context-growth sources we just identified:

- **Large or duplicate orchestrator `Read` calls.** Spec 055's read-lean hook
  already nudges on duplicate reads and large whole-file reads, but the event is
  ephemeral. We cannot later ask "which files caused growth on this spec?" or
  "did large reads predict peak cache-read?"
- **Hook-injected `additionalContext`.** Several hooks inject soft guidance
  (`jig-context-check`, `jig-memory-scan`, `jig-post-edit-verify`,
  `jig-task-capture`, `jig-boundary-change-warn`). They are useful, but repeated
  injected text is still context the orchestrator rereads. Today we do not log
  how many bytes/tokens each hook injects.

This spec adds lightweight, fail-open telemetry and a report surface that ties
those context-growth sources back to sessions/specs. The goal is not to block
work. The goal is to make the next cost-reduction decision data-driven: if big
whole-file reads dominate, tighten read discipline; if hook injections are
noise, trim the noisy hook; if neither is material, look elsewhere.

## Assumptions

- Hook payloads continue to include `session_id`, `hook_event_name`, and
  `tool_input` for the tool events this spec instruments. Current tests already
  fabricate those fields for the read and telemetry hooks.
- `CLAUDE_PROJECT_DIR` points at the project root in scaffolded installs, so a
  hook can read `.jig/spec-ref` there when a slice is in progress. If absent,
  events remain useful at session/hook level and render as unattributed to a
  spec.
- Byte length is a good enough proxy for injected-context size. Reports should
  show bytes plus estimated tokens using the existing context-fill ratio; exact
  tokenizer parity is out of scope.

## Decomposition

**SPIDR axis: Data.** The unknown is not how to build the mechanism - existing
hooks and `usage.py` are the substrates - but which data source is worth
attributing first. Split by context-growth source:

1. **Read events.** Capture large/duplicate `Read` nudges and report them by
   spec/session/path.
2. **Hook injections.** Capture `additionalContext` emissions and report them by
   hook/spec/session.

**Spike rejected.** The current code paths are verified: `jig-context-check.sh`
already branches on `PreToolUse(Read)` and delegates to
`lib/context_fill.py`; the hooks listed above already emit
`additionalContext`; `usage.py` already reads transcript/session data and has a
marker-required attribution mode.

## Slices

- [070-01 — read-event attribution](slice-01-read-event-attribution.md)
- [070-02 — hook-injection attribution](slice-02-hook-injection-attribution.md)

## Current state verified 2026-06-12

- `hooks/scripts/jig-context-check.sh` handles `PreToolUse` for `Read` and
  calls `read_nudge_for_turn`; it emits a soft `additionalContext` nudge and
  never blocks.
- `hooks/scripts/lib/context_fill.py` has `evaluate_read`, duplicate-read
  detection, large whole-file detection, and `JIG_READ_LEAN_BYTES` with a
  64 KiB default.
- `hooks/scripts/jig-memory-scan.sh`, `jig-post-edit-verify.sh`,
  `jig-task-capture.sh`, `jig-boundary-change-warn.sh`, and
  `jig-context-check.sh` can emit `additionalContext`.
- `scripts/usage.py` can already report token totals, top specs, turn counts,
  peak cache-read, compaction-threshold what-ifs, and marker-required
  attribution. It does not yet ingest hook/read context-growth telemetry.

## Non-goals

- No hard blocking of `Read`, `Edit`, `Write`, or prompt submission. This spec
  preserves ADR-0011's nudge-not-gate posture.
- No automatic `/compact` or session handoff.
- No exact tokenizer integration. Estimated tokens from bytes are sufficient
  for ranking context-growth sources.
- No pricing model changes. `ccusage` remains the pricing authority for dollar
  estimates; this spec adds attribution signals, not cost rates.
- No full prompt/transcript content capture. Logs must store metadata and short
  snippets only, never whole injected messages or file contents.
