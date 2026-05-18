---
status: DRAFT
dependencies: []
last_verified:
---

## Slice 023-01 — clarify-skill-md

**Goal:** Ship `skills/clarify/SKILL.md` as an active, auto-triggering
judgment-skill that scans a DRAFT spec across **six categories**, asks
**up to five prioritized questions**, and appends a `## Clarifications`
section with the user's verbatim answers + a coverage summary table.
SKILL.md only — no `.py` helper. Same archetype as `pr-review` (012-01),
`arch-review` (014-01), `vision-elicitation` (017-02), `slice-to-spec`
(020-01), `contracts` (022-01).

**DoR:**

- ✅ Spec 023 reserved on origin/main via `workflow.py new clarify`
  (2026-05-18 — first live-remote dogfood of slice 003-03; closed
  CLAUDE.md hot-cache close-out item #3).
- ✅ Five precedent judgment-skills active and surface-tested (012,
  014, 017-02, 020, 022). Six-class surface-pinning pattern proven.
- ✅ Spec-kit's `/speckit.clarify` shape understood (web-fetched
  2026-05-18). Nine-category source slimmed to six aligned with
  jig's slice template.
- ✅ Vision-elicitation precedent for writing into an existing doc
  is live and reconciled (017-02 / 017-03). The `## Clarifications`
  append shape mirrors vision-elicitation's section-marker writes.

**Acceptance Criteria:**

1. **`skills/clarify/SKILL.md`** exists with active frontmatter:
   - `name: clarify`
   - `user-invocable: true`
   - **No** `disable-model-invocation: true` (auto-triggering).
   - `description: >` (folded scalar) contains, in order:
     - One sentence stating purpose, using the exact phrasing:
       "Lightweight spec clarification scan for jig projects —
       a six-category ambiguity audit that asks up to five prioritized
       questions and appends them to the spec's `## Clarifications`
       section."
     - Trigger phrases the router should match on: "clarify this spec",
       "audit this spec for ambiguities", "is this spec ready for
       review", "find unknowns in this scope", "scan for unanswered
       questions", "what's missing from this spec".
     - A `Do not use for:` clause naming three exclusions, in this
       exact order, with this exact phrasing: (a) "spec-compliance
       review of a finished slice (use `/jig:independent-review`
       instead)", (b) "cross-artifact consistency analysis or
       drift detection (use `/jig:analyze` instead)", (c)
       "project-vision or architecture elicitation (use
       `/jig:vision-elicitation` instead)".

   _Note: per user direction on 2026-05-18 the description does
   **not** include a category-based deferral hint to spec-kit's
   `/speckit.clarify`. Jig's clarify ships as a standalone baseline,
   not a deferral surface._

2. **SKILL.md body** has the following H2 sections, in order:
   - **What this skill does** — one paragraph framing the
     lightweight ambiguity scan; references the six-category
     taxonomy and the five-question budget.
   - **When to use vs. when to defer** — distinguishes from
     four neighbors: (a) `/jig:spec-workflow` (which transitions
     state but doesn't elicit clarifications), (b) `/jig:analyze`
     (cross-artifact, post-DRAFT — different shape), (c)
     `/jig:vision-elicitation` (project-level vision/architecture,
     not spec-level ACs), (d) `/jig:independent-review` (reviews
     against a written spec — assumes clarity already exists).
     The section explicitly says when to reach for each.
   - **Inputs** — one of: (a) a single `spec.md` (overview-level
     scan), (b) one `slice-NN-*.md` (slice-level scan). Mixed-mode
     ("scan everything") is **explicitly not supported by the MVP**;
     belongs to a future slice 023-02 if friction surfaces.
   - **Six-category taxonomy** — the six categories, each as an H3
     subsection, with one paragraph explaining what to check + one
     "what to check" bullet list (3-5 bullets per category).
     Exact category names: **Scope & Boundaries** /
     **Acceptance Criteria Testability** / **Dependencies & Blockers**
     / **Non-functional Requirements** / **Edge Cases & Failure
     Modes** / **Terminology Consistency**.
   - **Question-asking loop** — the algorithm: (1) internal coverage
     scan rates each category Clear/Partial/Missing, (2) up to five
     prioritized questions chosen by the model (Partial/Missing >
     Clear), (3) ask one at a time, recording the answer verbatim,
     (4) stop conditions (any of): five questions asked, all six
     categories resolved or skipped, user types "stop" / "skip
     remaining".
   - **Output: the `## Clarifications` section** — exact shape
     of what gets appended to the spec. Required: H2 heading
     `## Clarifications`, per-entry shape with question + verbatim
     answer + category tag, final coverage summary table mapping
     each category → status (Clear / Partial / Resolved / Outstanding
     / Skipped).
   - **Gotchas** — explicit notes on: (a) verbatim-answer rule
     (no paraphrasing — same boundary as vision-elicitation),
     (b) advisory-not-gate (`workflow.py transition DRAFT →
     READY_FOR_REVIEW` does not refuse without clarifications),
     (c) one-doc-at-a-time scope (no cross-slice loops),
     (d) no `.py` helper — all section surgery via Read + Edit.
   - **Relationship to other skills** — `/jig:spec-workflow`
     (sibling, different shape), `/jig:analyze` (post-DRAFT,
     cross-artifact), `/jig:vision-elicitation` (project-scope,
     not spec-scope).

3. **Six-category taxonomy section** in SKILL.md uses the exact
   category names listed in AC #2 (Scope & Boundaries / Acceptance
   Criteria Testability / Dependencies & Blockers / Non-functional
   Requirements / Edge Cases & Failure Modes / Terminology
   Consistency) and each subsection contains a "what to check"
   bullet list with at least three concrete checks. Examples:
   - **Scope & Boundaries**: in-scope deliverable named? non-goals
     listed? boundary with adjacent specs declared?
   - **Acceptance Criteria Testability**: each AC has a measurable
     outcome? observable from outside the helper? AC count
     reasonable (~3-10)?
   - **Dependencies & Blockers**: upstream slices DONE? ADRs
     accepted? fixtures/data available?
   - **Non-functional Requirements**: performance / security /
     observability constraints named? backwards-compat policy
     stated?
   - **Edge Cases & Failure Modes**: refusals enumerated? failure
     paths drawn? race conditions considered?
   - **Terminology Consistency**: glossary terms used consistently?
     conflicting names ("slice" vs "task")?

4. **Output format** — the `## Clarifications` section that gets
   appended to the target doc has this exact shape:
   ```markdown
   ## Clarifications

   ### Q1: <verbatim question>
   _(category: <category-name>)_
   <verbatim user answer>

   ### Q2: <verbatim question>
   ...

   ### Coverage summary

   | Category | Status |
   |---|---|
   | Scope & Boundaries | Clear / Partial / Resolved / Outstanding / Skipped |
   | Acceptance Criteria Testability | ... |
   | ... | ... |
   ```
   Append-only — the skill does not modify any existing section in
   the spec body above. If `## Clarifications` already exists (re-run
   case), the new entries append to the existing section, not start
   a new one. Q numbers continue from the highest existing.

5. **Tests** in `skills/clarify/test_clarify_skill_surface.py`
   (file name pattern aligned to CONTRIBUTING.md's
   `test_<skill_name>_skill_surface.py` convention — per recent
   ADR-related cleanup in f9f51c2) cover:
   - **FrontmatterTests** — `name: clarify`, `user-invocable: true`,
     `disable-model-invocation` absent.
   - **DescriptionTests** — normalized description (per
     `" ".join(text.lower().split())`) contains:
     - All six trigger phrases listed in AC #1, verbatim.
     - The `Do not use for:` clause names "spec-compliance review",
       "cross-artifact consistency", and "project-vision".
     - References `/jig:independent-review`, `/jig:analyze`, and
       `/jig:vision-elicitation` as the explicit alternatives.
   - **DescriptionBoundsTests** — anti-greediness pinning. The
     normalized description does **not** contain: "comprehensive
     review", "deep analysis", "expert-level", "full audit",
     "specification author", "writes the spec for you",
     "interprets your requirements". Same pattern as 012-01's
     `DescriptionBoundsTests`.
   - **BodyTests** — required H2 sections present (case-insensitive
     heading match): What this skill does / When to use / Inputs /
     Six-category taxonomy / Question-asking loop / Output / Gotchas
     / Relationship.
   - **TaxonomyCoverageTests** — all six category names present
     in the body as H3 headings; each H3 followed by at least one
     bullet list with three or more items.
   - **WorkedExampleTests** — the two worked-example sibling files
     exist (`skills/clarify/worked-example-jig.md` and
     `skills/clarify/worked-example-saas.md`), each with the canonical
     three-section shape (input excerpt / Q/A trace / coverage
     summary).

6. **Two worked-example siblings**, both at `skills/clarify/`:
   - **`worked-example-jig.md`** — a clarify pass against an
     early-DRAFT snapshot of a real jig spec (lean toward a
     reconstructed `spec 018-slice-per-file` DRAFT or an early
     `spec 022-contracts` DRAFT — pick during implementation).
     Shows the model's coverage scan output, the top 3-5 questions
     asked, the verbatim answers (synthesized for demonstration),
     and the coverage summary table.
   - **`worked-example-saas.md`** — a clarify pass against a
     non-jig hypothetical: a short "add OAuth login to a SaaS app"
     spec with deliberate ambiguity. Proves the taxonomy generalizes
     beyond jig vocabulary. Same three-section shape.

7. **`skills/scaffold-init/scaffold.py` `_TIER_SKILLS` table**
   gets a new `"clarify"` entry under `"tier-1"`. One-line addition
   between existing entries (alphabetical or position-of-spec-landing
   — match precedent). Existing scaffold tests in
   `test_scaffold_install_lists.py` (if present) gain a row asserting
   `clarify` lands under `tier-1` for projects that opt into Tier 1.

8. **CLAUDE.md hot cache** gains:
   - One row in `## Skills in this repo` table — `/jig:clarify`
     marked active (auto + explicit).
   - One line in `### Active specs` recording slice 023-01 DONE
     with test counts.
   - Sprint-focus paragraph note acknowledging that Tier 1 now
     has six active skills (`adr-workflow`, `tdd-loop`,
     `slice-land`, `pr-review`, `arch-review`, **`clarify`**)
     plus `contracts` (the seventh Tier 1 skill, per spec 022)
     and that the "five Tier 1" prose in `docs/product-vision.md`
     needs a refresh in reconciliation.

9. **`docs/specs/README.md`** regenerated by `workflow.py status-board`
   after the slice transitions to DONE; Notes column curated
   to match 012-01 / 022-01 shape: "N tests; lightweight ambiguity
   scan; six-category taxonomy; no `.py` helper".

10. **SKILL.md is dogfooded** against this very slice's spec.md
    during reconciliation: the implementer applies the clarify
    body content as a prompt-to-self against `docs/specs/023-clarify/spec.md`
    + `slice-01-clarify-skill-md.md`, generates 3-5 questions, and
    answers them (or marks Skip) in the deviation log. This is the
    end-to-end honest validation that the SKILL.md prose actually
    produces useful output.

**DoD** (same shape as 012-01 / 014-01 / 017-02 / 020-01 / 022-01):

> **Anti-pre-tick reminder.** Only two boxes are auto-ticked by
> `workflow.py transition` (per slice 003-04): "Implementation review
> passed" on IN_PROGRESS → REVIEWED, and "Reconciliation review passed"
> on REVIEWED → RECONCILED. Every other box below must be ticked
> **after** the corresponding evidence exists.

- [ ] All 10 ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture; six-class surface-pinning pattern (Frontmatter /
      Description / DescriptionBounds / Body / TaxonomyCoverage /
      WorkedExample) covers AC #1-#6.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] SKILL.md dogfood against this slice's own spec.md (AC #10),
      with output recorded in the deviation log.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `CLAUDE.md` updates: hot-cache entry for spec 023-01;
      Skills table row added; sprint-focus refresh.
- [ ] `docs/product-vision.md` "Tier 1 — default-on" list updated
      to include `clarify` (six entries instead of five — also
      reflects `contracts` from spec 022).

**Anti-horizontal-phasing check:** End-to-end value in one slice.
A dev writing a new spec can: `workflow.py new <slug>` → opens
`spec.md` → starts drafting → types "clarify this spec" → jig's
clarify scans the body across six categories → asks up to five
questions → appends `## Clarifications` with verbatim answers →
dev finalizes the spec → transitions to `READY_FOR_REVIEW` with
documented ambiguities resolved. End-to-end observable; one slice.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TBD — numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._
