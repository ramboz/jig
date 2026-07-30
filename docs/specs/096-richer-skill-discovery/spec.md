---
status: DRAFT
skill: independent-review
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 096: Richer-skill discovery for extensible review passes

## Overview

Implements [ADR-0039](../../decisions/adr-0039-richer-skill-discovery.md). jig
ships **shallow baselines** for several review skills and is meant to defer to a
richer skill the user installed. Today it doesn't, reliably:

- The read-only review passes resolve by **exact folder name at user scope only**
  (`review.py detect_richer_skill` → `~/.claude/skills/<name>/SKILL.md`), so a
  genuinely richer skill installed under any other name is invisible. This is the
  **reported failure**: a user installed `review-pr-deep` at user scope and the
  workflow craft pass silently used jig's baseline.
- The interactive skills defer via the **Claude skill router**, which does not
  exist on the **Codex** host — so those deferrals are inert there.

This spec makes richer-skill deferral **work by configuration first** (the only
path that guarantees it), then adds a **zero-config discovery layer** on top.

**Extensible set** (these passes defer): `pr-review`, `arch-review`,
`security-review`, `code-health`, `design-review`. `bug-fix`'s craft + security
passes reuse `pr-review` / `security-review` and inherit the behavior.

**Never-defer set** (stay jig-canonical): the strict spec-compliance pass
`independent-review`, the `frame-critique` pass, `bug-fix`'s diagnose +
red→green rigor gates, and all process/orchestration skills.

## Goals

1. **Config-first resolution.** `review.<category>_skill` in `scaffold.json`
   deterministically selects the richer skill for a category, on both hosts,
   honored by all five extensible passes.
2. **Zero-config pickup.** Absent config, candidates are enumerated across all
   scopes on the active host and the orchestrator selects one, passed explicitly
   into `review.py` and resolved to a concrete path for the read-only reviewer.
3. **Observability.** The applied skill (or `none`) and the candidate set the
   orchestrator was shown are recorded in the review evidence artifact, with at
   least one committed consumer.
4. **Codex parity** for the read-only review passes — no router dependency.

## Non-goals

- **No `Skill` tool on the read-only reviewer.** Reaffirmed from spec 053; the
  reviewer stays Read/Glob/Grep and reads a path it was handed.
- **No change to what any baseline contains.** Whether jig's `security-review`
  floor is "too deep" for a shallow default is
  [a separate deferred decision](../../refinement-todo.md) against ADR-0013.
- **No migration for already-scaffolded projects** (ADR-0039 OQ4) — the
  `jig_baseline:` marker ships forward-only.
- **Interactive judgment skills** (`contracts`, `explain`, `orient`, `reframe`,
  `vision-elicitation`) are out of scope here — their Codex parity is ADR-0039 §5
  follow-up work, deliberately lower priority than the review passes.
- **No hard gate on the anomaly.** ADR-0014's evidence gate stays a one-line
  predicate on `verdict:`; this spec records and surfaces, it does not block.

## Assumptions

- **VERIFIED (2026-07-27 spike, ADR-0039 OQ1):** Codex exposes an enumerable
  skill surface at `$HOME/.agents/skills`, repo `.agents/skills`, and
  `/etc/codex/skills`, each holding `SKILL.md` with `name`/`description`
  frontmatter identical in shape to Claude's. Probed live against
  `codex-cli 0.133.0`; one parser covers both hosts.
- **VERIFIED (2026-07-27 spike):** naive substring matching over descriptions
  misclassifies — `morning-github` (a briefing skill mentioning "stage draft PR
  reviews") was nominated as a `pr-review` candidate and won a lexical tiebreak.
  Precision therefore cannot come from the nominator; see slice 096-03.
- **SECOND-HAND, NOT VERIFIED (ADR-0039 OQ6):** that the **Codex orchestrator**
  receives skill `name`/`description` in its context and can select among them.
  Per OpenAI documentation as relayed by the user (2026-07-27); local
  verification was attempted and failed to confirm or refute (`codex-cli 0.133.0`
  exposes no `skills` subcommand). **This gates slice 096-04 only** — it is the
  premise the zero-config path rests on for Codex, and 096-04 is a spike that
  settles it before any Codex selection code is written. Slices 096-01..03 do not
  depend on it.
- **ASSUMED (cheap to verify in 096-02):** the read-only reviewer can `Read` a
  SKILL.md at project and admin scope. Spec 053's live probe confirmed only
  `~/.claude` (user scope).

## Decomposition

SPIDR: **Rules** is the primary axis. The resolution precedence chain is a
rule-stack, and each slice adds one rule while keeping the pass end-to-end
functional — simple rule first (config), edge rules later (enumeration,
selection, anomaly). Every slice touches the user-facing surface (a review pass
actually applying a different rubric), so none is horizontal phasing.

| Technique | Resolution |
|---|---|
| **R — Rules** | **Chosen.** Precedence rules 1→5 from ADR-0039 §3, one per slice: config (01), then baseline-exclusion + path resolution (02), then enumeration + orchestrator selection (03), then the anomaly record + consumers (05). |
| **S — Spike** | Used once, deliberately: 096-04 settles OQ6 (Codex orchestrator skill-visibility), the one unverified premise. Sequenced *before* Codex selection code, not as a prelude to everything. |
| **P — Path** | Rejected as primary: the happy/edge split here maps onto the same rule-stack, so it would duplicate R. |
| **I — Interface** | Rejected as primary: per-host splitting would strand Codex behind a wholly separate slice; instead each rule slice is host-portable by construction (pure filesystem + frontmatter), and only the *selection* path needs the 096-04 spike. |
| **D — Data** | N/A — no data subset to stage. |

**Why config first (ADR-0039 §6).** Slice 096-01 alone closes the reported bug,
deterministically, on both hosts, with no marker and no enumeration. It is the
layer that can actually be *guaranteed*, and the destination every ADR-0039 kill
criterion falls back to — so it must exist before the layers that fall back to
it. If the zero-config layer is later abandoned, 096-01 remains a working
feature rather than a half-built one.

### Slices

- [096-01 — config-precedence](slice-01-config-precedence.md) — DRAFT — `review.<category>_skill` in scaffold.json, honored by all five extensible passes, both hosts
- [096-02 — baseline-marker-and-resolve](slice-02-baseline-marker-and-resolve.md) — DRAFT — `jig_baseline: true` on shipped baselines + deterministic name→path resolution across scopes
- [096-03 — enumerate-and-select](slice-03-enumerate-and-select.md) — DRAFT — candidate enumeration (recall-only) + `--richer-skill` orchestrator selection, Claude
- [096-04 — codex-orchestrator-visibility](slice-04-codex-orchestrator-visibility.md) — DRAFT — spike: does the Codex orchestrator see skill descriptions? (gates Codex zero-config)
- [096-05 — anomaly-record-and-consumers](slice-05-anomaly-record-and-consumers.md) — DRAFT — calibrated unapplied-candidates record + `check-reviews` warning + status-board count

## References

- **[ADR-0039](../../decisions/adr-0039-richer-skill-discovery.md)** — the governing decision (Accepted 2026-07-27, with a recorded override and a recorded `needs-changes` frame-critique; read both before implementing).
- **Spec [053](../053-craft-pass-skill-dispatch/spec.md)** — introduced the file-read dispatch this spec generalizes; its exact-name / user-scope-only resolution is superseded here.
- **[ADR-0014](../../decisions/adr-0014-review-evidence-model.md)** — the review-evidence gate the anomaly record must not silently amend.
- **[ADR-0013](../../decisions/adr-0013-security-floor-policy.md)** — baseline security depth; the "shallow by default" tension is tracked separately in [refinement-todo](../../refinement-todo.md).
- **Originating report (2026-07-27):** a richer `review-pr-deep` installed at user scope was silently ignored by the workflow craft pass.
