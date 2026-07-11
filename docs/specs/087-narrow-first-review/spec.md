---
status: DONE
skill:
use_cases: []
---

# Spec 087: Narrow-first review

> Reserved on 2026-07-11 via `workflow.py new`.

## Overview

jig's read-only reviewer subagent (Read/Glob/Grep) is handed prompts that say
*what* to read — the spec, the deliverables, related files — but never *how* to
read them. With no investigation discipline, a general-purpose agent defaults to
the repo-explorer instinct: browse broadly, open whole files, accumulate context.

GitHub reported this exact failure mode for Copilot code review: swapping bespoke
review tools for generic ones made reviews *costlier and lower-hit-rate* purely
because the tool instructions gave the agent the wrong instincts, and that
rewriting the guidance to be reviewer-shaped — anchor to the diff, narrow with
grep/glob before reading, batch discovery before reads, read focused ranges,
retry a failed search with a simpler query — recovered ~20% cost at equal
quality ([source](https://github.blog/ai-and-ml/github-copilot/better-tools-made-copilot-code-review-worse-heres-how-we-actually-improved-it/)).
That efficiency claim is external and unmeasured for jig — the spec does not
promise a measured cost delta (a unit test cannot observe token cost); it makes
the reviewer prompts carry the discipline that produced it. This directly serves
jig's own context-cost thesis (specs [055](../055-context-cost-discipline/spec.md)
/ [057](../057-thin-orchestrator/spec.md): cost ≈ orchestrator context × turns).

**The change.** Add a shared "How to investigate (read efficiently)" block to the
reviewer prompts *and* to the `agents/reviewer.md` agent definition — narrow-first,
deliverable-anchored investigation guidance.

**Scoping is the load-bearing design decision.** The guidance goes to the
code-reviewing passes only — `implementation`, `pr-review`, `bug-review`,
`arch-review`, `code-health` — where the reviewer navigates a code deliverable.
It is deliberately **withheld** from the prose/framing passes — `reconciliation`,
`frame-critique`, `design-review` — where there is no code diff to anchor to and
"grep before read / read focused ranges" would be wrong instincts (a
frame-critique must read the whole spec; an attest-only design pass re-derives
nothing). Applying task-shaped guidance rather than blanket guidance is the
article's actual lesson, and applying it uniformly would repeat the original
mistake in reverse.

## Current state (verified)

Probe-verified by reading the code directly (not assumed):
- The reviewer subagent's toolset is Read/Glob/Grep — `agents/reviewer.md`
  frontmatter, and the `review.py` comment at the richer-skill-detection block.
- The code-review vs. prose-pass split matches the CLI subcommands and their
  builders — `review.py` argparse defines `implementation` / `pr-review` /
  `bug-review` / `arch-review` / `code-health` (code) vs. `reconciliation` /
  `frame-critique` / `design-review` (prose/framing); all eight builders open
  with the shared `_PREAMBLE`.
- `agents/reviewer.md` and `review.py` are mirrored into `hosts/claude/` and
  `hosts/codex/plugins/jig/` by `scripts/build_host_packages.py` (a drift test
  enforces it), so source edits require a host-package rebuild.

## Assumptions

None.

## Decomposition

SPIDR — **Rules** axis. The work adds one investigation-discipline rule to the
reviewer prompts. No Spike: the current-state behavior was verified by reading
`review.py` and `agents/reviewer.md` directly; nothing is unknown. There is no
sensible Path/Interface/Data split — the guidance is one coherent block applied
across the code-review passes. It collapses to a single vertical slice that
delivers end-to-end value: every code-review prompt jig emits, plus the standing
reviewer agent definition, carries the discipline, exercised by tests.

## Slices

- [087-01 — investigation guidance in code-review prompts + reviewer agent](slice-01-investigation-guidance.md)
