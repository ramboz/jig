---
status: IN_PROGRESS
skill: explain
---

# Spec 065: Lower the vocabulary barrier (shipped lexicon + on-demand explainers)

## Overview

A first jig user got stuck on their first specs: the artifacts are dense with
opinionated, jargon-heavy vocabulary — **SPIDR**, **ADR**, **vertical slice**,
**reconciliation**, **deviation log**, **DoR / AC / DoD**, **frontmatter**,
"teeth gates", "detect-and-drive" — and almost none of it is explained where the
reader meets it. The glossary and SPIDR primer exist, but nothing *routes* a
confused reader to them at the moment of confusion. The barrier hits hardest the
people jig most wants to help: juniors and devs new to spec-driven work.

The instinct was a scaffold-time "light vs expert" verbosity mode that
auto-graduates after ~20 specs. We rejected that shape for three reasons:

- **Project maturity ≠ reader expertise.** A repo with 30 specs is exactly where
  a *new hire* lands — and spec count says nothing about any human's vocabulary.
  Auto-removing explanations on a counter would yank the lifeline out from under
  the people it's for.
- **"More verbose docs" fights context-cost discipline** ([spec 055](../055-context-cost-discipline/spec.md) /
  [spec 057](../057-thin-orchestrator/spec.md)). Fattening `CLAUDE.md` / the hot
  cache taxes every session forever.
- **The barrier is in the *artifacts*, not the scaffold step.** A one-time flag
  can't help the person reading spec 062 six months later.

So this spec reframes the goal as: **jig explains its own vocabulary,
on demand, at near-zero standing cost.** One canonical definition of each term,
four consumers that read it, all off the always-loaded path.

## Goals

1. **One lexicon, four consumers.** A single canonical, machine-readable
   definition per jig term, so the hook, the explainer skill, generated specs,
   and the glossary never drift in wording.
2. **Surface definitions just-in-time** — when a reader meets a term, not by
   pushing verbosity at everyone up front.
3. **Strong handholding on demand** — a `/jig:explain` skill that translates a
   whole dense spec/ADR into plain language for a junior, pulling in the linked
   ADRs/specs so they don't have to chase references.
4. **Stop the bleed going forward** — new specs self-define their jargon on first
   use, so the dense pile stops growing.
5. **Stay off the hot path.** Nothing here is loaded into `CLAUDE.md` every
   session; the lexicon is read on demand. Respects 055/057.
6. **Stay soft.** Conventions and nudges, not gates — consistent with
   [ADR-0011](../../decisions/adr-0011-spec-gate-model.md)'s deliberateness model.

## Non-goals

- **A scaffold-time "light/expert" verbosity mode.** Rejected above (maturity ≠
  expertise; fights context-cost). No `mode:` field in `scaffold.json`.
- **An auto-graduation counter ("after N specs, switch to expert").** Rejected —
  spec count is not a proxy for the reader's vocabulary.
- **Retrofitting existing dense specs** (062, 058, …) with inline definitions.
  Self-defining generation is **forward-only**; `/jig:explain` covers the back
  catalogue on demand instead.
- **A lint/gate that blocks transitions on undefined acronyms.** Resolved at
  clarify as a soft convention, not a teeth gate (would false-positive on
  legitimately-undefined terms).
- **`/jig:explain` writing its output to disk.** Resolved at clarify: always
  ephemeral (chat-only), zero hot-path cost.

## SPIDR analysis

Axis: a **Data + Interface + Rules** mix — the lexicon is the **Data**
foundation; the hook surfacing and the `/jig:explain` skill are **Interfaces**
onto it; self-defining generation is a **Rule**. Each slice is independently
**vertical** (delivers usable value end-to-end). **Spike rejected** — the
substrate is known: `glossary.md` exists, `jig-memory-scan.sh` exists to extend,
the judgment-skill pattern is proven (`/jig:clarify`, `/jig:pr-review`), and
`_common/` already hosts shared stdlib-only helpers.

| Slice | Delivers | Role |
|---|---|---|
| 065-01 | **Lexicon foundation** — a shipped, structured (JSON) jig lexicon + a `_common/` loader that merges the per-project glossary overlay on top (project wins) | Data |
| 065-02 | **Hook surfacing** — `jig-memory-scan.sh` injects the plain-language def of any lexicon term that appears in a prompt (bounded, one-line) | Interface |
| 065-03 | **`/jig:explain` skill** — term mode (define a term) + artifact mode (junior-grade handholding walkthrough of a spec/ADR, auto-pulling linked refs), ephemeral output | Interface |
| 065-04 | **Self-defining generation** — a soft authoring convention so new specs expand acronyms + link the lexicon on first use; forward-only | Rule |
| 065-05 | **`/jig:explain` passage mode** — a third mode that explains a pasted snippet of jig output (neither a term nor a path), reusing the lexicon scan; turns the dead-end ambiguous-argument branch into a useful explanation | Interface |

## Design notes

- **Lexicon home + overlay precedence (decided — [ADR-0021](../../decisions/adr-0021-lexicon-home-and-overlay.md)).**
  jig ships the canonical lexicon as **structured
  JSON** (`skills/_common/lexicon.json`), keyed by term, each entry carrying
  `short` (one-line), `plain` (a junior-readable paragraph), optional `example`,
  and `see_also` (related term keys). JSON, not YAML — stdlib-only so the
  `python3 -c` hook can parse it with no dependency. Seeded from the existing
  `docs/memory/glossary.md` terms, then expanded into plain language (not
  authored from scratch). The lexicon's shape is guarded by the 065-01
  schema/shape test (required fields + resolvable `see_also`); a **formal JSON
  Schema** for `lexicon.json` is deferred (internal data shape per
  [ADR-0005](../../decisions/adr-0005-contracts-as-judgment-skill.md)) — add only if the
  shape proves worth enforcing beyond the test.
- **Project overlay (decided: project wins).** The loader (`_common/lexicon.py`)
  merges the shipped lexicon with the consuming project's
  `docs/memory/glossary.md`. The parse target is the glossary's **documented
  canonical format** — `glossary.md.template` states it explicitly: *"Format:
  `## TERM`, followed by definition prose."* So the loader reads each **`## Term`
  (H2) heading** + its first paragraph as an overlay entry that **overrides** the
  shipped definition for that term. (The earlier draft said `### Term` / H3 — a
  bug: the live glossary and the template both use H2, so an H3 parser would
  match nothing.) This keeps **one** human-facing project artifact (the glossary
  devs already edit) rather than a second per-project file. The prose parse is
  heuristic (H2 heading → term, first paragraph → short def); fail-soft (a
  glossary that doesn't match the format degrades to shipped-only, never raises).
- **Off the hot path.** The lexicon is read on demand by the hook and the skill;
  it is **not** injected into `CLAUDE.md` or any always-loaded doc. The hook
  surfacing (065-02) is bounded — matched terms only, one line each, capped —
  so per-prompt context growth stays negligible (the 055/057 constraint).
- **Retrofit to existing projects.** The new assets live inside trees that
  `migrate copy-machinery` / `scaffold-init` already copy (`skills/_common/`,
  `hooks/scripts/`, the doc templates). The shipped `lexicon.json` + `lexicon.py`
  travel as machinery; existing projects pick them up on their next
  `copy-machinery` / tier upgrade — no new copy path, no re-scaffold. (No
  separate slice; asserted in 065-01/02/04 ACs.)
- **`/jig:explain` is a judgment skill, no `.py`** (like `/jig:clarify`). Its
  testable surface is structural — SKILL.md present, manifest-registered,
  CLAUDE.md skills-table row, no helper, deferral language present; the
  plain-language *quality* is judgment, exercised by the skill prompt, not a unit
  test (the AC-testability gap flagged at clarify, accepted for a judgment skill).
- **Honesty.** This is a best-effort comprehension floor, not a guarantee the
  reader will understand everything — the same framing as the security floor
  ([ADR-0013](../../decisions/adr-0013-security-floor-policy.md)) and the soft
  context mechanisms (055/057). jig surfaces and explains; it doesn't certify
  understanding.

## Slices

- `slice-01-lexicon-foundation.md` — shipped structured lexicon + `_common/` loader with project-glossary overlay (Data foundation; gates the rest)
- `slice-02-memory-scan-lexicon.md` — `jig-memory-scan.sh` surfaces plain-language defs for lexicon terms in a prompt (Interface; bounded, fail-open)
- `slice-03-explain-skill.md` — `/jig:explain` term + artifact modes, ephemeral, defers to richer installed skill (Interface)
- `slice-04-self-defining-generation.md` — soft authoring convention: new specs expand + link jargon on first use (Rule; forward-only)
- `slice-05-passage-mode.md` — `/jig:explain` third mode: explain a pasted snippet of jig output (neither term nor path); reuses the lexicon scan, replaces the dead-end ambiguous-argument branch (Interface; added post-065-03 per usage)

## Open questions

_All four resolved at clarify (2026-06-06) — see ## Clarifications below._

## Clarifications

### Q1: What format should the shipped lexicon take?
_(category: Scope & Boundaries / Terminology Consistency)_

**Structured data (JSON).** Keyed by term with short-def / plain-language def /
example / see-also. One schema all four consumers parse; easy to test and
validate. (JSON specifically — stdlib-only so the `python3 -c` hook can read it.)

### Q2: When a project's glossary defines a term that is also in the shipped lexicon, what wins?
_(category: Edge Cases & Failure Modes)_

**Project overlay wins.** The per-project `docs/memory/glossary.md` overrides the
shipped lexicon for that term; the shipped definition is the fallback. Projects
can specialize jig's vocabulary to their domain.

### Q3: Should `/jig:explain` ever write its explanation to disk?
_(category: Scope & Boundaries / Non-functional Requirements)_

**Always ephemeral.** Chat-only, never writes. Simplest and zero context-cost
risk; keeps the hot path clean (055/057).

### Q4: How strongly should the self-defining generation policy be enforced?
_(category: Scope & Boundaries / Acceptance Criteria Testability)_

**Soft convention / agent policy.** A documented generation policy + convention
(sibling of the soft 055/057 mechanisms): the authoring agent expands acronyms
and links the lexicon on first use. Forward-only, not retrofitted to existing
dense specs. No gate.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Partial — `/jig:explain` quality is judgment, not unit-testable; structural surface is covered (065-03) |
| Dependencies & Blockers | Clear — 065-01 gates 02/03/04 |
| Non-functional Requirements | Resolved — off-hot-path; hook surfacing bounded |
| Edge Cases & Failure Modes | Resolved — overlay collision (project wins), missing/malformed glossary (fail-soft), term-not-in-lexicon (flagged) |
| Terminology Consistency | Resolved — **lexicon** = shipped jig vocabulary; **glossary** = per-project overlay; two distinct things, no blurring |
