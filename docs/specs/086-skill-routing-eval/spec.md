---
status: DONE
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 086: Skill-routing eval

> Reserved on 2026-07-08 via `workflow.py new`. Retro-spec: a working
> prototype was built first (this session) and is being formalized through the
> lifecycle — the review + reconciliation gates evaluate the as-built code
> against these acceptance criteria. The deviation logs record that ordering.

## Overview

jig routes work to skills entirely through each skill's `SKILL.md`
`description:` — the host surfaces every description each session and the model
picks (spec 076 / EngTip #23). That routing surface has **no automated guard**:
two descriptions can drift toward each other until the model cannot tell them
apart, and a description can lose the vocabulary users actually say until the
right skill stops ranking for a realistic prompt. Every SKILL.md craft-pass
edit (e.g. commit `1d5bf7c`) risks both, silently.

This spec adds the deterministic, CI-safe **Tier-2 routing eval** the reference
collection ([addyosmani/agent-skills](https://github.com/addyosmani/agent-skills),
schema from Anthropic's skill-creator) pioneered, adapted to jig's idiom
(`unittest` discovered by `run_tests.py`, zero-dependency, Python 3.9 floor,
floor-ratcheted gates like the rest of jig's CI). It is a **stemmed TF-IDF
cosine** over the descriptions' *positive routing surface* — a *lexical
approximation* of routing. It is a regression **canary, not ground truth**: it
pins two properties of the *current* descriptions + case set and fails a later
edit that **regresses** them —

- **collision** — two descriptions grow similar enough (on their positive
  surface) that routing between them is at risk;
- **case regression** — a description edit drops vocabulary a **pinned trigger
  case** encodes, so its owner stops ranking within `top_k`.

**Scope, honestly (frame-critique 086-01):** the case-regression guard protects
the *author-authored* prompt set — **not** the full space of "vocabulary real
users say." A craft-pass edit (e.g. commit `1d5bf7c`) that strips a word real
users say but that no case encodes still passes green; closing that gap needs
the deferred semantic (Tier-3) eval and real-usage-sourced prompts (see
`## Assumptions`, slice 01, and `docs/refinement-todo.md`). What the eval
reliably catches **today** is *regression against the pinned baseline*, in jig's
existing gate culture (`spec_lint.py`, `validate_manifests.py`, host-package
drift).

## Assumptions

_None at the spec level. The one unverified, load-bearing premise (a lexical proxy yields useful regression signal for a semantic router) is not spec-wide — it bears weight only on the harness, so it is scoped to slice 086-01's `## Assumptions`. Slice 02's edits add real user vocabulary that helps the semantic router regardless of the proxy, and slice 03 is pure integration; neither rests on the premise. This italic note is a framing pointer, not a surfaced assumption._

## Decomposition

SPIDR split on **Rules + Interface** — Spike is not needed (the prototype
already probed feasibility; there is no open research question). Every slice is
vertical: it delivers a runnable, observable capability, not an intermediate
layer.

- **R — the guard rules.** Slice 01 ships the two rules the harness enforces
  (description-collision and trigger-routing) as one cohesive capability: they
  share a single TF-IDF vector space and are exercised by one report + one
  CI-gating test, so splitting the engine from its two rules would be horizontal
  phasing (an engine with no observable output).
- **D/R — act on the findings.** Slice 02 applies the eval's output: sharpen the
  descriptions it flags and regenerate the host packages. Depends on 01.
- **I — integration.** Slice 03 registers the eval as a named gate in
  `ci_check.py` so it is legible alongside the other gates. Depends on 01.

Slices 02 and 03 both depend on 01 but are independent of each other.

## Slices

- [086-01 — routing-eval harness (collision + trigger + ratchet)](slice-01-harness.md)
- [086-02 — sharpen eval-flagged descriptions](slice-02-sharpen-descriptions.md)
- [086-03 — register the eval as a named ci_check gate](slice-03-ci-gate.md)
