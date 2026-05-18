---
status: DRAFT
skill: clarify
tier: 1
---

# Spec 023: clarify skill (judgment-style, pre-spec ambiguity scan)

## Overview

A gap analysis against GitHub's [spec-kit](https://github.com/github/spec-kit)
surfaced that jig has **no formal clarification pass** before a spec
transitions `DRAFT → READY_FOR_REVIEW`. Spec-kit's `/speckit.clarify`
runs a structured nine-category coverage scan and asks up to five
prioritized questions, appending each Q/A pair to a `## Clarifications`
section in the spec. Jig today trusts the spec author to bring clarity,
and SPIDR-splitting (per `/jig:spec-workflow`) assumes that clarity
already exists.

Spec 023 introduces a new `clarify` skill (judgment-only, no `.py`
helper — same archetype as `pr-review` / `arch-review` /
`vision-elicitation` / `slice-to-spec` / `contracts`) that runs an
interactive ambiguity scan against a DRAFT spec, asks up to five
prioritized questions across **six categories aligned with jig's
slice template**, and appends a `## Clarifications` section as
answers arrive. Designed to slot between `workflow.py new <slug>`
(stub reservation) and the `READY_FOR_REVIEW` transition (spec body
ready for first review).

The user explicitly chose **not** to ship a category-based deferral
hint to spec-kit's richer `/speckit.clarify` — see the close-out
conversation on 2026-05-18 in the merge commit. Jig's clarify ships
as a standalone baseline, not as a router-deferral surface. If a
power user wants spec-kit's depth, they install spec-kit and invoke
`/speckit.clarify` explicitly; jig's `/jig:clarify` continues to
serve as the in-repo workflow's lightweight scan.

## Why now

- **Direct gap from the spec-kit comparison (2026-05-18).** The
  comparison surfaced three real gaps (clarify, analyze,
  constitution-gate) — see also [spec 024-analyze](../024-analyze/spec.md)
  for the second of the three. Constitution-gate folds into 024 as a
  reviewer-prompt AC; clarify gets its own spec because the
  six-category taxonomy + Q/A loop is the meatiest piece.
- **Sequencing matters: clarify before analyze.** Clarify writes to
  `## Clarifications` during DRAFT. Analyze (spec 024) reads the same
  section as one of its six finding categories ("underspecification:
  has the spec gone through clarify, and were the resulting
  clarifications addressed in the ACs?"). Shipping clarify first
  means analyze can immediately exercise it.
- **The judgment-skill archetype is well-established.** Five
  precedents (012-pr-review, 014-arch-review, 017-vision-elicitation,
  020-migrate-slice-to-spec, 022-contracts) all SKILL.md-only, all
  with surface-pinning tests + worked-example siblings. Slice 023-01
  is the sixth and adds no new mechanics.
- **Tier 1 stays at five active skills.** With this spec landing
  alongside 024, Tier 1 grows from five (`adr-workflow`, `tdd-loop`,
  `slice-land`, `pr-review`, `arch-review`) to seven. `contracts` is
  also Tier 1 per spec 022, making the running count nine after both
  this spec and 024 land. The "five Tier 1" count in product-vision.md
  needs an update during reconciliation.

## Goals

1. **A new active skill `skills/clarify/SKILL.md`** (judgment-only,
   auto-triggering) that conducts an ambiguity scan against a DRAFT
   spec.
2. **Six-category taxonomy** aligned with jig's slice template, not
   spec-kit's nine — drop "Domain & Data Model" and "Interaction &
   UX Flow" (which assume slots jig's slice template doesn't have)
   and fold the substance of those categories into "scope &
   boundaries" where it applies.
3. **Up to five prioritized questions per session**, asked
   sequentially with recommended-default options where applicable.
   The skill does not loop indefinitely.
4. **Writes `## Clarifications` section into the target `spec.md`**
   (or the relevant `slice-NN-*.md` if the user names a specific
   slice). Same write-into-spec archetype as `/jig:vision-elicitation`,
   which writes into `product-vision.md` and `architecture.md`.
5. **Two worked-example siblings**: one against a jig spec that has
   real ambiguity (TBD — pick during implementation; candidate is
   an early version of spec 018-slice-per-file or spec 022-contracts),
   one against a non-jig hypothetical spec to prove the taxonomy
   generalizes.
6. **Surface-pinning tests** mirroring `pr-review` / `arch-review`
   six-class pattern (Frontmatter / Description / DescriptionBounds
   / Body / TaxonomyCoverage / WorkedExample).
7. **Advisory only, not a state-machine gate.** Clarify is recommended
   before `DRAFT → READY_FOR_REVIEW` but `/jig:spec-workflow`'s
   `transition` does not refuse the transition if `## Clarifications`
   is absent. Same advisory shape as `/jig:pr-review` — calling it is
   a workflow choice, not an enforced step.

## Non-goals

- **No category-based deferral hint to spec-kit.** Per user direction
  on 2026-05-18, jig's clarify stands on its own. Power users who
  want spec-kit's `/speckit.clarify` install spec-kit and invoke it
  explicitly under `/speckit.*`.
- **No automatic invocation on `workflow.py new`.** Reservation
  writes a stub; clarify is the next step the user runs (or
  doesn't). Auto-triggering happens via the SKILL.md description
  matching user messages, not via hook-driven invocation.
- **No interpretation of the user's answers.** Same boundary as
  `/jig:vision-elicitation`: the skill formats answers into the
  `## Clarifications` section verbatim; it does not paraphrase,
  expand, or "improve" them.
- **No cross-spec clarify pass.** Each invocation targets one spec
  (or one slice within one spec). Auditing all of `docs/specs/` for
  drift is the territory of `/jig:analyze` (spec 024), not clarify.
- **No `.py` helper.** All determinism the skill needs (reading
  spec.md, locating section bounds, appending text) Claude can run
  inline using Read + Edit. If a friction signal emerges three
  times, slice 023-02 can add a helper — same trigger discipline as
  `/jig:pr-review`'s deferred gather helper (012-02).
- **Slice-level clarify within a single invocation is out of scope.**
  The MVP targets one document at a time: either `spec.md`
  (overview-level scope) or one `slice-NN-*.md` (slice-level ACs).
  Mixed sessions ("clarify the spec AND each slice") would need
  the helper a future 023-02 might ship.

## Decomposition

One active slice. SPIDR-split:

| Technique | Question | Outline |
|---|---|---|
| **S** — Spike | Do we need a spike on "how do we elicit clarifications without LLMing past the user's answers"? | **No.** Pattern is well-trodden by vision-elicitation (017-02), spec-kit's `/speckit.clarify`, and the lean-canvas style of product discovery. |
| **P** — Path | Single-skill judgment vs skill + `.py` helper for section surgery? | **Judgment-only.** Same call as 012-01, 014-01, 017-02, 020-01, 022-01. If section-surgery friction recurs three times, 023-02 lands a helper (deferred). |
| **I** — Interface | Auto-trigger via SKILL.md description match, or explicit `/jig:clarify <spec>` only? | **Both.** Auto-trigger when the user says "clarify this spec / find unknowns / is this spec ready for review", explicit invocation as the documented entry point. No `disable-model-invocation` flag. |
| **D** — Data | What does the skill consume? Where does it write? | **Consumes:** the target `spec.md` (or `slice-NN-*.md`). **Writes:** appends a `## Clarifications` section under the existing body. **Stop condition:** all six categories scanned + up to five questions asked + summary table rendered. |
| **R** — Rules | What governs the question-asking loop? | **Six-category coverage** scanned internally → **prioritized question selection** (Critical > High > Medium severity) → **stop after five questions** OR when the model judges all gaps resolved → **summary table** named per category (Resolved / Deferred / Clear / Outstanding). |

### Slices

- [023-01 — clarify-skill-md](slice-01-clarify-skill-md.md) — DRAFT

## Out of scope for spec 023 (any slice)

- **Slice-level clarify in a single session.** MVP is one doc at a
  time. Slice-level loops require the helper that 023-02 may add.
- **Auto-invocation on transition.** Clarify stays advisory. No
  `workflow.py transition DRAFT → READY_FOR_REVIEW` integration.
- **Cross-spec drift audit.** Belongs to spec 024-analyze.
- **Constitution-gate (principle-violations) check.** Belongs to
  spec 024-analyze (one of its six finding categories).
- **Deferral hint routing to spec-kit's `/speckit.clarify`.**
  Explicit user direction (2026-05-18) — not shipping the deferral
  pattern for this skill.

## Open questions

- **Worked-example #1 spec choice.** Picking a real DRAFT-state jig
  spec (or a snapshot of one) for the worked example tests the
  taxonomy against actual jig vocabulary. Lean: spec 018-slice-per-file
  in its DRAFT state had real cross-layer ambiguity (parser dual-read
  vs new helpers — closed in slice 018-01's reviewer pass). A
  reconstructed-DRAFT snapshot is the worked example.
- **Worked-example #2 shape.** Non-jig hypothetical to prove the
  taxonomy generalizes. Lean: a small consumer-product spec (e.g.,
  "add OAuth login to a SaaS app") — same shape as 017's
  worked-example-yarnfinder.md and 012's diff-fragment example.
- **Severity nomenclature.** Spec-kit uses Critical/High/Medium/Low
  in its `/speckit.analyze`, but `/speckit.clarify` uses internal
  Clear/Partial/Missing. Lean: adopt spec-kit's Clear/Partial/Missing
  for the internal coverage map (per category), and a simple
  "questions asked: 1-5" count externally. No severity on the
  questions themselves — the model picks the top five by judgment.

## References

- **Originating conversation:** 2026-05-18 spec-kit gap analysis
  (user-driven; this spec + spec 024 are the two specs that came out
  of it).
- **Skill-only-no-helper precedent:** specs 012-01 (pr-review),
  014-01 (arch-review), 017-02 (vision-elicitation-skill-core),
  020-01 (migrate-slice-to-spec), 022-01 (contracts-skill-md).
- **Write-into-doc precedent:** `/jig:vision-elicitation` writes
  `product-vision.md` + section slots in `architecture.md`;
  clarify writes a single `## Clarifications` section into `spec.md`.
- **Spec-kit's `/speckit.clarify`:** the nine-category source we
  slimmed to six. Spec-kit's full taxonomy: Functional Scope / Domain
  & Data Model / Interaction & UX Flow / Non-Functional Quality /
  Integration & External Dependencies / Edge Cases & Failure
  Handling / Constraints & Tradeoffs / Terminology & Consistency /
  Completion Signals. Jig's six: Scope & Boundaries / Acceptance
  Criteria Testability / Dependencies & Blockers / NFRs / Edge
  Cases & Failure Modes / Terminology Consistency.
