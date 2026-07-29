---
status: IN_PROGRESS
skill: independent-review
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 096: Richer-skill discovery for extensible review passes

## Overview

Implements [ADR-0040](../../decisions/adr-0040-richer-skill-discovery-explicit-candidate-channel.md)
(which supersedes [ADR-0039](../../decisions/adr-0039-richer-skill-discovery.md)
on three points; read both — 0039 for the governing rationale carried forward,
0040 for the three superseding decisions D1–D3). jig ships **shallow baselines**
for several review skills and is meant to defer to a richer skill the user
installed. Today it doesn't, reliably:

- The read-only review passes resolve by **exact folder name at user scope only**
  (`review.py detect_richer_skill` → `~/.claude/skills/<name>/SKILL.md`), so a
  genuinely richer skill installed under any other name is invisible. This is the
  **reported failure**: a user installed `review-pr-deep` at user scope and the
  workflow craft pass silently used jig's baseline.
- The interactive skills defer via the **Claude skill router**, which does not
  exist on the **Codex** host — so those deferrals are inert there.

This spec makes richer-skill deferral **work by configuration first** (the only
path that guarantees it), then adds a **zero-config discovery layer** on top,
built around an **explicit printed candidate channel** (ADR-0040 D3) rather than
the ambient host context ADR-0039 assumed.

**Extensible set** (these passes defer) — **three categories** (ADR-0040 D1):
`pr-review`, `arch-review`, `code-health`. Each has a real `review.py`
prompt-builder *and* is semantically extensible. `bug-fix`'s craft pass reuses
`pr-review` and inherits the config behavior only in its orchestrated review
pass — see the lifecycle-dependence caveat below.

**Named follow-up, not in scope** (ADR-0040 D1 / OQ1): `security-review` (no
`review.py` builder; router-hint deferral) and `bug-fix`'s craft/security passes
(no `review.py pr-review` call). Making an orchestrator-invoked judgment skill
config-honoring without inert prose is a real design question entangled with
[ADR-0013](../../decisions/adr-0013-security-floor-policy.md); it gets its own
ADR before any security-parity work. **This is the honest residual** — security
is the category [ADR-0039 Context §3] named as the user's real concern, and this
spec does not fix it.

**Never-defer set** (stay jig-canonical): the strict spec-compliance pass
`independent-review`, the `frame-critique` pass, **`design-review`** (an
[ADR-0022](../../decisions/adr-0022-pluggable-oracle-boundary.md) attest-only
gate whose own builder refuses richer-skill detection — ADR-0040 D1 moved it
here, correcting an ADR-0039 §1 error), `bug-fix`'s diagnose + red→green rigor
gates, and all process/orchestration skills.

## Goals

1. **Config-first resolution (ADR-0040 D1).** `review.<category>_skill` in
   `scaffold.json` deterministically selects the richer skill for one of the
   **three** categories (`pr_review_skill`, `arch_review_skill`,
   `code_health_skill`), on both hosts, honored by those three extensible passes.
2. **Zero-config pickup over an explicit channel (ADR-0040 D3).** Absent config,
   `review.py candidates <category> <spec> <slice> --pass <pass>` enumerates
   non-baseline candidates, **prints them tiered** (high-confidence with
   descriptions, speculative as names only), **and writes the shown set to a
   sidecar** keyed to `(slice, pass)`. The orchestrator selects from the printed
   list and passes `--richer-skill <name|none>` back; the pick is recorded into
   the same sidecar. This is host-portable by construction — an agent picking
   from text it was shown needs no router and no ambient injection.
3. **Observability via a derived substrate (ADR-0040 D3).** `record-review`
   *derives* a closed `substrate:` vocabulary (`config` / `shown` /
   `non-interactive` / `not-shown` / `n/a`) from observable state (config
   presence + sidecar presence), and records the applied skill (or `none`) plus
   the shown-and-declined set. `record-review` is the honest-actor chokepoint;
   `substrate:` is recorded, never gated on (ADR-0014 §3 unchanged).
4. **Codex parity for the read-only review passes.** The printed candidate list
   is the same mechanism on both hosts, so no router dependency — and ADR-0039's
   OQ6 (host-injected skill metadata) stops gating anything (ADR-0040 D3).

## Non-goals

- **No `Skill` tool on the read-only reviewer.** Reaffirmed from spec 053; the
  reviewer stays Read/Glob/Grep and reads a path it was handed.
- **No change to what any baseline contains.** Whether jig's `security-review`
  floor is "too deep" for a shallow default is
  [a separate deferred decision](../../refinement-todo.md) against ADR-0013.
- **`security-review` + `bug-fix` config-honoring is deferred** (ADR-0040 D1 /
  OQ1) — a named follow-up with its own ADR, not this spec.
- **`design-review` is out of scope as an extensible pass** — it is in the
  never-defer set (ADR-0040 D1). No `review.design_review_skill` key ships.
- **No forward-only frontmatter marker for project-scope exclusion** (ADR-0040
  D2). Exclusion uses the existing `jig-` path prefix / "unprefixed ⇒ no
  SKILL.md" invariant. A `jig_baseline:` marker is retained *only* at
  plugin/admin scope, and even that is gated on OQ4 (rule out a plugin-dir test
  first). ADR-0039 OQ4 (no migration) is thereby mooted, not resolved.
- **No hard gate on the anomaly.** ADR-0014's evidence gate stays a one-line
  predicate on `verdict:`; this spec records and surfaces, it does not block.

## Assumptions

- **VERIFIED (2026-07-27..28, direct read of this tree):** `review.py` has
  builders only for pr/arch/code-health/design and **no** security builder;
  `scaffold.py:742` prefixes every user-facing scaffolded skill `jig-` while the
  two unprefixed writers (`:726`, `:1485-1489`) omit `SKILL.md`; `migrate.py:287`
  ships the `jig-` discriminator; `design-review`'s builder refuses richer-skill
  detection. These ground ADR-0040 D1 + D2.
- **VERIFIED (2026-07-27 spike, ADR-0039 OQ1, carried forward):** Codex exposes
  an enumerable skill surface at `$HOME/.agents/skills`, repo `.agents/skills`,
  and `/etc/codex/skills`, each holding `SKILL.md` with `name`/`description`
  frontmatter identical in shape to Claude's. One parser covers both hosts.
- **VERIFIED (2026-07-27 spike):** naive substring matching over descriptions
  misclassifies — `morning-github` was nominated as a `pr-review` candidate and
  won a lexical tiebreak. Precision governs the **tiering** (which candidates are
  high-confidence) and the anomaly's false-positive rate — never the pick
  (ADR-0040 D3); see slice 096-03.
- **RETIRED (ADR-0040 D3):** ADR-0039's OQ6 (that the Codex orchestrator receives
  skill `name`/`description` in ambient context) is no longer load-bearing — the
  explicit printed list is shown on both hosts because the calibration
  requirement demands it anyway. The residual, **probed by 096-04 before 096-03
  ships**, is jig-side: does an orchestrator reliably run the
  `candidates → pick → --richer-skill` sequence against jig's own prose? This is
  the most likely failure mode of the whole design (ADR-0040 Assumptions).
- **VERIFIED (2026-07-28, 096-02 AC6 live probe):** the read-only reviewer
  (`jig:reviewer`, Read/Glob/Grep) CAN `Read` a SKILL.md at project scope AND at
  an absolute admin/plugin path outside the project — both reads succeeded and
  returned the fixture's `description`. So the multi-scope resolver's paths are
  usable by the reviewer; no scope needs to be withheld. (Spec 053 had confirmed
  only `~/.claude` user scope; this extends it to project + admin/plugin.)

## Decomposition

SPIDR: **Rules** is the primary axis. The resolution precedence chain is a
rule-stack, and each slice adds one rule while keeping the pass end-to-end
functional — simple rule first (config), edge rules later (enumeration,
selection, anomaly). Every non-spike slice touches the user-facing surface (a
review pass actually applying a different rubric), so none is horizontal phasing.

| Technique | Resolution |
|---|---|
| **R — Rules** | **Chosen.** Precedence rules from ADR-0040, one per slice: config (01), then path-prefix exclusion + name→path resolution (02), then the prose-compliance spike (04), then the explicit candidate channel + selection (03), then the substrate record + consumers (05). |
| **S — Spike** | Used once, deliberately: 096-04 settles the jig-side prose-compliance premise (ADR-0040 Assumptions), the design's most likely failure mode. **Re-sequenced ahead of 096-03** so it gates the selection machinery rather than following it. |
| **P — Path** | Rejected as primary: the happy/edge split here maps onto the same rule-stack, so it would duplicate R. |
| **I — Interface** | Rejected as primary: per-host splitting would strand Codex behind a separate slice; each rule slice is host-portable by construction (filesystem + frontmatter + a printed list), so no host-specific slice is needed. |
| **D — Data** | N/A — no data subset to stage. |

**Why config first (ADR-0040 D1, carried from ADR-0039 §6).** Slice 096-01 alone
closes the reported bug, deterministically, on both hosts, with no enumeration
and no marker. It is the layer that can actually be *guaranteed*, and the
destination every kill criterion falls back to — so it must exist before the
layers that fall back to it. If the zero-config layer is later abandoned, 096-01
remains a working feature rather than a half-built one.

**Why the spike moved ahead of the machinery (ADR-0040 D3).** The prose-compliance
risk — whether the orchestrator runs the `candidates` step at all — is the
design's self-declared most likely failure mode. Probing it *before* 096-03 ships
means the machinery is built only if the premise it rests on holds; the probe is
stub-based (a fake `candidates` script + the real SKILL.md recipe) and so does
not depend on 096-03. On a FAIL, the fallback is config-only (096-01), a shipped
working state.

### Slices

- [096-01 — config-precedence](slice-01-config-precedence.md) — DRAFT — `review.<category>_skill` in scaffold.json for the **three** extensible categories, honored by their passes, both hosts
- [096-02 — baseline-marker-and-resolve](slice-02-baseline-marker-and-resolve.md) — DRAFT — `jig-` path-prefix / "unprefixed ⇒ no SKILL.md" exclusion + deterministic name→path resolution across scopes (reviewer-read probe included)
- [096-04 — orchestrator-selection-compliance](slice-04-codex-orchestrator-visibility.md) — DRAFT — **spike (re-sequenced ahead of 03):** does an orchestrator reliably run `candidates → pick → --richer-skill` against jig's prose? (gates the zero-config machinery)
- [096-03 — enumerate-and-select](slice-03-enumerate-and-select.md) — DRAFT — the explicit candidate channel: tiered `candidates` + sidecar + `--richer-skill` selection, Claude
- [096-05 — anomaly-record-and-consumers](slice-05-anomaly-record-and-consumers.md) — DRAFT — derived `substrate:` record + `check-reviews` / status-board consumers

## References

- **[ADR-0040](../../decisions/adr-0040-richer-skill-discovery-explicit-candidate-channel.md)** — the governing decision (Accepted 2026-07-28; supersedes ADR-0039 on D1–D3; reached `pass` on its sixth frame-critique revision, all recorded).
- **[ADR-0039](../../decisions/adr-0039-richer-skill-discovery.md)** — superseded, but its problem framing, config-first precedence chain, never-defer set, read-only-reviewer constraint, and auditability posture are carried forward as the governing rationale.
- **Spec [053](../053-craft-pass-skill-dispatch/spec.md)** — introduced the file-read dispatch this spec generalizes; its exact-name / user-scope-only resolution is superseded here.
- **[ADR-0022](../../decisions/adr-0022-pluggable-oracle-boundary.md)** — the attest-only boundary that keeps `design-review` in the never-defer set.
- **[ADR-0014](../../decisions/adr-0014-review-evidence-model.md)** — the review-evidence gate the substrate record must not silently amend.
- **[ADR-0013](../../decisions/adr-0013-security-floor-policy.md)** — baseline security depth; the "shallow by default" tension + security config-honoring (OQ1) are tracked separately in [refinement-todo](../../refinement-todo.md).
- **Originating report (2026-07-27):** a richer `review-pr-deep` installed at user scope was silently ignored by the workflow craft pass.
