---
status: DRAFT
skill: analyze
tier: 1
---

# Spec 024: analyze skill (cross-artifact consistency report + constitution-gate)

## Overview

The 2026-05-18 spec-kit gap analysis surfaced three real gaps in jig's
spec lifecycle:

1. **Clarify** — pre-spec ambiguity scan. → [spec 023-clarify](../023-clarify/spec.md).
2. **Analyze** — cross-artifact consistency report. → this spec.
3. **Constitution-gate** — principle-violation check on every slice
   review. → folds into this spec as one of analyze's six finding
   categories + a small reviewer-prompt AC.

GitHub's [spec-kit](https://github.com/github/spec-kit) ships
`/speckit.analyze` as a **non-destructive** cross-artifact consistency
report covering six finding categories at severity levels CRITICAL /
HIGH / MEDIUM / LOW: duplication, ambiguity, underspecification,
constitution alignment, coverage gaps, and inconsistency. Spec-kit
runs the analysis across `spec.md` + `plan.md` + `tasks.md` plus a
project `memory/constitution.md`.

Jig's analyze ships **slimmed and adapted** to jig's artifact shape:

- **Single-spec input**, not three artifacts — jig collapses spec/plan/tasks
  into one `spec.md` (with sibling `slice-NN-*.md` files per
  spec 018) and writes hard-decision rationale to ADRs at
  `docs/decisions/adr-NNNN-*.md`.
- **Six finding categories** mirroring spec-kit's, with category
  #4 (Constitution Alignment) reinterpreted as **principle
  violations** against `docs/product-vision.md`'s `## Design
  principles` section. No new "constitution.md" artifact needed —
  jig already has the principles, just not enforced.
- **Reporter only, no writes.** Output goes to stdout, same model as
  `/jig:pr-review` and `/jig:arch-review`. Spec-kit's "do not modify
  any files" stance kept verbatim.
- **CLARIFY-aware.** One finding sub-category checks whether the
  spec went through `/jig:clarify` and whether the resulting
  `## Clarifications` were addressed in ACs.

This spec also bundles a **reviewer-prompt principles-check tweak**
as AC #6 — a 5-line change to `review.py`'s prompt builders that
adds a "verify this slice doesn't violate principles 1-7 from
product-vision.md § Design principles" line to every implementation
+ reconciliation review. That's the constitution-gate piece. Cheap
enough that a standalone spec isn't worth it; pairing it with
analyze keeps the conceptual unit ("how does jig enforce its own
governance?") in one place.

The user explicitly chose **not** to ship a category-based deferral
hint to spec-kit's richer `/speckit.analyze` (2026-05-18 conversation).
Jig's analyze ships as a standalone baseline.

**Terminology.** This spec uses two terms for the same underlying
concept (slice-level enforcement of `docs/product-vision.md` §
Design principles) at two surfaces:

- **Principle violations** — the analyze **finding category name**
  (Goals #2; surfaced by `/jig:analyze` when scanning a spec).
- **Constitution-gate** — the colloquial label for the
  **reviewer-prompt enforcement piece** (AC #6;
  `_principles_check_block()` in `review.py`). Borrowed from
  spec-kit's "constitution.md" pattern as a familiar cross-tool
  cue, even though jig has no separate constitution artifact.

Same concept, two enforcement surfaces: detection (analyze) and
slice-review gate (`review.py`).

## Why now

- **Direct gap from the spec-kit comparison (2026-05-18).** Second of
  three gaps; pairs with [spec 023-clarify](../023-clarify/spec.md).
- **Complements `spec_lint.py`** — `scripts/spec_lint.py` is
  structural (frontmatter shape, slice numbering). Analyze is
  **semantic** (ADR ↔ spec ↔ architecture drift, ACs without tests,
  principle violations). Two layers of safety; no overlap.
- **Reuses the prompt-builder integration pattern from spec 022.**
  Slice 022-02 added `_contract_surface_check_block()` and conditional
  prompt injection in `review.py`. Slice 024-01's reviewer-prompt
  principles-check AC follows the same pattern — same module, same
  shape, same test idioms.
- **Sequencing: clarify first, analyze second.** Analyze checks for
  the presence of `## Clarifications` as one of its findings; if
  clarify isn't shipped first, that sub-finding has nothing to detect.
  Doesn't strictly block, but clarify ships logically earlier.

## Goals

1. **A new active skill `skills/analyze/SKILL.md`** (judgment-only,
   auto-triggering) that produces a **non-destructive** cross-artifact
   consistency report for a single spec.
2. **Six finding categories with severity** (CRITICAL / HIGH /
   MEDIUM / LOW):
   - **Duplication** — near-duplicate requirements / ACs within a
     spec.
   - **Ambiguity** — vague terms ("fast", "scalable", "TBD",
     "configurable") and unresolved placeholders.
   - **Underspecification** — ACs without measurable outcomes;
     slices without dependencies declared; clarifications missing
     when the spec is non-trivial.
   - **Principle violations** — spec contradicts one or more of
     the seven principles in `docs/product-vision.md` §
     Design principles. **This is the constitution-gate sub-piece.**
   - **Coverage gaps** — ACs without corresponding tests in the
     repo (or no test plan documented); slices that claim a hard
     decision without an ADR back-link.
   - **Terminology drift** — glossary terms used inconsistently;
     ADR-NNNN references that don't resolve to an accepted ADR;
     dependency references that name slices in non-existent specs.
3. **Output: stdout markdown report**, same shape spec-kit uses but
   slimmed: findings table (sorted by severity) → coverage summary
   (categories scanned, count per severity) → actionable next steps.
   No file writes. Maximum 50 findings per run.
4. **Two worked-example siblings** at `skills/analyze/`:
   one against a real jig spec that has known drift (e.g., spec
   017 where `docs/architecture.md` slot prose evolved during
   017-01 reshape but glossary terms migrated later), one against
   a non-jig hypothetical with deliberate drift.
5. **Surface-pinning tests** mirroring the six-class pattern:
   Frontmatter / Description / DescriptionBounds / Body /
   FindingCategoryTests (all six categories named) / WorkedExample.
6. **Reviewer-prompt principles-check** (the constitution-gate
   piece) — `review.py`'s `build_implementation_prompt` and
   `build_reconciliation_prompt` each append a "verify this slice
   doesn't violate principles 1-7 from product-vision.md §
   Design principles" line. Pattern: same conditional-insert
   helper as `_contract_surface_check_block()` from slice 022-02,
   but for principle violations.

## Non-goals

- **No category-based deferral hint to spec-kit.** Per user direction
  on 2026-05-18.
- **No cross-spec audit in the MVP.** Each invocation targets one
  spec. Auditing all of `docs/specs/` for drift (e.g., "spec 010's
  ADR-0003 reference resolves to an ADR that's been superseded") is
  the territory of a future slice 024-02 if signal emerges.
- **No automatic invocation on transitions.** Same advisory stance
  as clarify and pr-review. `workflow.py transition` does not call
  analyze.
- **No file mutations.** Stdout reporter only. Spec-kit's "do not
  modify any files" stance carries over.
- **No principles enforcement beyond category #4.** The principles-
  check is a finding category, not a hard refusal. Same advisory
  shape as the rest of analyze.
- **No `.py` helper for analyze itself.** The reviewer-prompt
  principles-check is a code change in `review.py` (existing
  helper), but analyze the skill ships SKILL.md-only. If
  determinism friction surfaces three times, a future 024-03
  could add `analyze.py gather`.

## Decomposition

One active slice. SPIDR-split:

| Technique | Question | Outline |
|---|---|---|
| **S** — Spike | Spike on "how do we surface ADR/spec/arch drift without false positives"? | **No spike needed.** Six finding categories are well-defined by spec-kit; we slim them to fit jig's artifacts. The principle-violation check is bounded (read product-vision.md, score the spec against seven numbered principles). |
| **P** — Path | Skill-only judgment vs skill + `.py` helper for finding aggregation? | **Skill-only.** Same call as 023-01. Severity scoring + finding table rendering Claude can do inline. If signal emerges three times that the model misses systematic drift, slice 024-03 (deferred) lands a helper. |
| **I** — Interface | Auto-trigger via SKILL.md description match, or explicit-only? | **Both.** Trigger phrases: "analyze this spec", "check for inconsistencies", "audit ADR vs spec drift", "cross-artifact alignment". |
| **D** — Data | What does the skill consume? Where does it write? | **Consumes:** one `spec.md` + all sibling `slice-NN-*.md` files + `docs/product-vision.md` (for principles) + `docs/decisions/*.md` (for ADR resolution) + `docs/memory/glossary.md` (for terminology consistency) + `docs/architecture.md` (for architecture-drift checks). **Writes:** nothing. Output to stdout. |
| **R** — Rules | What governs the finding-emission loop? | **Six categories scanned in order**; each finding gets a severity (judged by the model); findings sorted by severity in the output; max 50 findings; if a category has zero findings, render "(none)" so the category list stays scannable. |

### Slices

- [024-01 — analyze-skill-md](slice-01-analyze-skill-md.md) — DRAFT

## Out of scope for spec 024 (any slice)

- **Cross-spec drift audit** (audit all of `docs/specs/`). Deferred
  to a future 024-02 if a real signal emerges.
- **Automated finding remediation** ("fix the findings for me").
  Reporter only. Same stance as `/jig:pr-review`.
- **CI integration** (run analyze on every PR). Out of scope; the
  skill is a session tool, not a CI gate. CI integration could
  follow if pattern proves out, but not in this spec.
- **Custom severity thresholds.** Spec-kit's CRITICAL/HIGH/MEDIUM/LOW
  is fixed in the MVP; no `--min-severity LOW` flag.
- **Deferral hint routing to spec-kit's `/speckit.analyze`.** Explicit
  user direction (2026-05-18).

## Open questions

- **Worked-example #1 jig spec choice.** Picking a real jig spec
  with known drift demonstrates the taxonomy's signal-to-noise. Lean:
  spec 017 (vision-elicitation) during its mid-reshape window
  produced 7 staleness incidents that analyze would have caught — a
  reconstructed snapshot at that point is the candidate. Alternative:
  a synthetic spec with planted drift, lower realism but easier to
  audit. Pick during implementation.
- **Coverage gap depth.** Should analyze read the test files
  (`grep -r` against `test_*.py`) to verify AC → test mapping, or
  rely on the spec's stated test plan? Lean: rely on the stated
  plan; reading source code expands the read-set unboundedly.
- **Principle-violation severity assignment.** Are all seven
  principles equal in weight? Lean: principles 1-3 (Hooks/skills,
  context economy, three subagents) → HIGH; principles 4-7
  (dogfooding, deferral, no-shims, scaffolding-not-renting) →
  MEDIUM. Pick during implementation with the worked example.

## References

- **Originating conversation:** 2026-05-18 spec-kit gap analysis;
  same conversation that authored [spec 023-clarify](../023-clarify/spec.md).
- **Spec-kit's `/speckit.analyze`:** six-category source, full
  taxonomy: Duplication / Ambiguity / Underspecification /
  Constitution Alignment / Coverage Gaps / Inconsistency. Jig's
  adaptation: same six, with #4 → Principle Violations (against
  product-vision.md design principles) and the other five slimmed
  to jig's artifact shape.
- **Skill-only-no-helper precedent:** specs 012-01 (pr-review),
  014-01 (arch-review), 017-02 (vision-elicitation), 020-01
  (slice-to-spec), 022-01 (contracts), 023-01 (clarify).
- **Reviewer-prompt conditional-insert pattern:** slice 022-02
  introduced `_contract_surface_check_block()` in
  `skills/independent-review/review.py`. Slice 024-01's
  principles-check follows the same pattern.
- **Companion spec:** [spec 023-clarify](../023-clarify/spec.md).
  Sequencing recommended: clarify lands first, analyze second
  (so analyze's "did this spec go through clarify?" sub-finding
  has signal to detect).
