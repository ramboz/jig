---
status: DONE
skill: independent-review
tier: (none — dev infrastructure)
---

# Spec 053: craft/arch-pass skill dispatch — file-read, not router

## Overview

Spec 031 wired the post-implementation **craft** (`pr-review`) and **arch**
(`arch-review`) passes into the spec-workflow, intending each to defer to a
richer user-installed skill (`~/.claude/skills/<name>/`) when present. Its
**Open question #1** named two dispatch paths — (a) prose instructs the
orchestrator/router to resolve precedence; (b) `review.py` filesystem-detects
the installed skill — and shipped (a) with "fall back to (b) only if (a)
misroutes."

**(a) misroutes — structurally.** The craft/arch passes spawn a read-only
`reviewer` subagent (`agents/reviewer.md`, tools: Read/Glob/Grep) which has
**no `Skill` tool**, so it cannot reach Claude's skill router at all. The
prose "apply the most-specific SKILL.md the router resolves to" was therefore
inert: the reviewer silently followed jig's inlined baseline buckets and never
applied a richer user skill. A live probe (a real `reviewer`-shaped subagent
handed the actual craft prompt) confirmed it: *"there is no mechanism available
to me to invoke a skill … the capability does not exist in my tool set"* — but
it **could** `Read` `~/.claude/skills/pr-review/SKILL.md`.

This spec promotes spec 031's deferred **option (b)**: `review.py`
deterministically detects a user-installed skill on disk and points the
read-only reviewer at that concrete path to **read-and-apply**, with graceful
fallback to jig's baseline buckets.

> **Retroactive record.** This spec was written *after* the work was
> implemented, dogfood-reviewed, and landed (commit `734e424`). See the
> slice's deviation log for why, and for the full review trail.

## Why now

- **Originating question (2026-06-01).** A user asked "how can I *guarantee*
  the deferral to my richer pr-review / arch-review actually works during the
  workflow?" Diagnosis + a live probe showed the workflow craft/arch pass never
  reached the richer skill — confirming a long-standing suspicion.
- **Closes spec 031 Open question #1.** (a) was shown to misroute on the
  no-`Skill`-tool subagent path; (b) is now the dispatch mechanism.
- **Small, deterministic, well-bounded.** One detection helper + a two-branch
  prompt, no new agent and no new capability handed to the read-only reviewer.

## Goals

1. **Deterministic richer-skill detection.** `review.py detect_richer_skill(name)`
   returns the path to a user-scope `~/.claude/skills/<name>/SKILL.md` when
   present, else `None`. Conservative on every error (never raises); honors
   `$HOME` (hermetically testable).
2. **File-read dispatch in both prompt builders.** `build_pr_review_prompt` /
   `build_arch_review_prompt` branch on detection: when a richer skill is found
   the prompt names its concrete path and instructs the reviewer to read-and-
   apply it (superseding the baseline); when absent it inlines jig's baseline
   buckets. Both branches normalize findings into the shared
   VERDICT / REASONING / SPECIFIC ISSUES / RECONCILIATION NOTES envelope.
3. **Honesty fix.** Correct the now-inaccurate "Claude's skill router resolves"
   prose describing the *reviewer/craft-pass* path (workflow.md,
   spec-workflow/SKILL.md, both skill Gotchas, review.py docstrings) — while
   preserving the accurate description of *interactive* routing (Path A).

## Non-goals

- **No new agent / no `Skill` tool on the reviewer.** Keeping the craft/arch
  reviewer read-only (and reaching the skill via file-read) is the minimal fix;
  granting it a `Skill` tool was the considered alternative and rejected.
- **No project-scope detection.** A project-scope `.claude/skills/<name>/` may
  be jig's own `scaffold-init` baseline copy, indistinguishable by path from a
  genuinely richer project skill. User-scope only; project-scope deferred (see
  `docs/refinement-todo.md`).
- **No routing observability here.** The `PreToolUse`/`Skill` trace hook that
  landed in the same commit belongs to spec [041](../041-routing-observability/spec.md)
  (reconciled there inline). This spec is dispatch only.
- **No re-engineering of `jig:pr-review` / `jig:arch-review`.** They remain
  judgment skills; the baseline buckets are unchanged.

## Decomposition

Single vertical slice — one detection helper + the two-branch prompt change +
the prose honesty fix all deliver one observable behavior (the workflow craft/
arch pass applies the richer user skill).

| Technique | Resolution |
|---|---|
| **S** — Spike | The live probe answered the only unknown (does the read-only reviewer have a `Skill` tool? can it `Read` `~/.claude`?). Folded into implementation, not a separate slice. |
| **P/I/D/R** | Single path: detection in `review.py`, consumed by both prompt builders; prose corrected in the operational docs. No staging needed. |

### Slices

- [053-01 — file-read-dispatch](slice-01-file-read-dispatch.md) — DONE — `detect_richer_skill()` + two-branch craft/arch prompts + prose honesty fix

## References

- **Originating conversation:** 2026-06-01 — "How can I guarantee that the
  skills delegation to richer local versions work (pr & arch review)? … Can you
  do a deterministic test somehow to verify?"
- **Spec [031](../031-multi-perspective-review/spec.md):** wired the craft/arch
  passes and named the (a)/(b) dispatch open question this spec resolves.
- **Spec [041](../041-routing-observability/spec.md):** routing observability;
  the `jig-skill-trace.sh` hook co-landed in `734e424` is reconciled there.
- **Landing commit:** `734e424` (`fix(review): route craft/arch pass to richer
  user skill via file-read dispatch`).
