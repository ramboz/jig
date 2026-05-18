---
status: RECONCILED
dependencies: []
last_verified: 2026-05-18
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

- [x] All 10 ACs pass; full test suite green (932 pass + 3 skipped, no
      regressions; 30 new tests in `test_clarify_skill_surface.py`).
- [x] Implementer test coverage exercises each AC with at least one
      fixture; six-class surface-pinning pattern (Frontmatter /
      Description / DescriptionBounds / Body / TaxonomyCoverage /
      WorkedExample) covers AC #1-#6. Bonus `NoPyHelperTests` class
      pins AC #7's no-`.py`-helper invariant.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`. _(Implementation review verdict: `pass`. Four
      non-blocking reconciliation notes folded into §1-§4 below.)_
- [x] Implementation review passed.
- [x] SKILL.md dogfood against this slice's own spec.md (AC #10),
      with output recorded in deviation §5 below.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. _(No new refinement-todo
      deferrals; three observations went to `docs/inbox.md`
      instead — see deviation §7.)_

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

**Implementation review** verdict was `pass` with four non-blocking
reconciliation notes (§1-§4 below). All deliverables shipped per
ACs #1-#7; AC #8/#9 are post-DONE close-out items (handled below);
AC #10 dogfood is captured in §5.

1. **AC #1 "Do not use for" exclusion ordering is not pinned by
   tests.** `DescriptionTests.test_do_not_use_clause_three_exclusions`
   asserts each of the three substrings is present but does not
   assert their relative order. The SKILL.md description (the
   "Do not use for:" intro on line 9 followed by the three
   exclusions on lines 10-13) does present them in the spec-mandated
   order (spec-compliance review → cross-artifact consistency →
   vision-elicitation),
   so the AC is met substantively. A future tightening could add
   an ordering assertion; filed to §7 as a candidate inbox entry
   rather than chasing in this slice.
2. **AC #7's `test_scaffold_install_lists.py` does not exist.**
   The AC text was conditional ("if present"); the existing
   `test_scaffold.py::test_test_signals_install_tier_1` asserts only
   `tier-1/tdd-loop` as a representative tier-1 entry, not the full
   set. So adding `clarify` to `_TIER_SKILLS["tier-1"]` (one-line
   edit at `skills/scaffold-init/scaffold.py:62`) is not regression-
   pinned by any current test. A dedicated "all expected tier-1
   skills land in installed_skills" test would be a sound
   follow-up; recorded to §7 as inbox candidate. Low priority —
   `_TIER_SKILLS` is the single source of truth and a one-line
   typo would surface in scaffold dogfooding.
3. **AC #4 example formatting drift.** AC #4's example block
   (slice-01 lines ~130-147) shows `_(category: <category-name>)_`
   immediately followed by `<verbatim user answer>` with no blank
   line; SKILL.md's `## Output:` section (lines ~268-272) inserts
   a blank line between them, and both worked examples follow the
   blank-line variant. Both readable; the blank-line shape produces
   cleaner Markdown rendering. AC text not amended (would churn the
   surface tests); the SKILL.md and worked-example shape is the
   shipped convention.
4. **Surface tests are not code-block-aware.** The `_h2_positions`
   and `_h3_blocks` regex helpers in `test_clarify_skill_surface.py`
   match `## Clarifications` / `### Qn` lines that appear inside the
   fenced ```markdown blocks at SKILL.md lines ~266 / 268 / 273. This
   does not produce false positives or negatives for any current
   assertion (none of the affected lines contain the six category
   names; `test_sections_in_order` uses a fixed substring list that
   doesn't enumerate "clarifications"). A future H2-named-by-example
   inside a code block could trip something; non-blocking but
   recorded for awareness. Same robustness concern would apply to
   the other judgment-skills' surface tests if anyone adds prose
   examples inside their bodies.

5. **AC #10 dogfood — clarify applied to spec 023-clarify itself
   (this slice's own spec).** Six-category coverage scan + 3
   prioritized questions, applied retrospectively to
   `docs/specs/023-clarify/spec.md` + `slice-01-clarify-skill-md.md`
   as a prompt-to-self.

   **Coverage scan:**
   | Category | Status |
   |---|---|
   | Scope & Boundaries | Clear (Tier 1 placement, judgment-skill archetype, six categories all explicit). |
   | Acceptance Criteria Testability | Clear (10 ACs with exact-phrasing mandates, case-insensitive heading match, named test classes). |
   | Dependencies & Blockers | Clear (frontmatter `dependencies: []`; DoR lists 5 precedent skills DONE; reservation done). |
   | Non-functional Requirements | Resolved (via Q1). |
   | Edge Cases & Failure Modes | Resolved (Q3) / Outstanding (Q2 — empty-body refusal not specified). |
   | Terminology Consistency | Clear (no internal contradictions; minor lowercase/capitalize variance between "scope" in non-goals and "Scope & Boundaries" in taxonomy is acceptable English-vs-proper-noun usage). |

   **Q1: Should the spec explicitly call out NFRs as N/A for
   judgment-skills, or is the absence (as in 022/020) the
   convention?** _(category: Non-functional Requirements)_
   _Answer:_ Convention from spec 022-01 and 020-01 is that
   judgment-skills (SKILL.md only, no runtime code) implicitly have
   N/A NFRs. The skill is prompt content invoked through the LLM,
   not a process that has perf budgets or security boundaries. Not
   worth an explicit call-out in spec body. **Resolved.**

   **Q2: What should happen when clarify is invoked against a spec
   stub that has no body beyond the reservation header (e.g., a
   freshly-reserved spec right after `workflow.py new`)?**
   _(category: Edge Cases & Failure Modes)_
   _Answer:_ The shipped SKILL.md does not specify this. In
   practice, the model would either ask "what's this spec about?"
   as Q1 (effectively the first elicitation question — sensible)
   or report all six categories as "Missing" (less helpful). A
   future enhancement could refuse with "spec body too thin to
   scan — add an Overview first". **Outstanding** — filed to
   `docs/inbox.md` as a known limitation.

   **Q3: How should the skill handle user empty / "I don't know"
   answers — record verbatim, prompt for clarification, or mark
   the question Outstanding?** _(category: Edge Cases & Failure
   Modes)_
   _Answer:_ Per AC #4, answers are recorded verbatim — including
   empty strings or "I don't know". The Coverage Summary status
   for that category becomes "Outstanding". The shipped SKILL.md
   handles this implicitly through the verbatim-answer rule; no
   spec change needed. **Resolved.**

   **Dogfood verdict:** The SKILL.md prose produces useful
   output. The coverage scan correctly identified one Outstanding
   gap (empty-body refusal) that's worth tracking; the other five
   categories are honestly Clear. End-to-end honest validation
   passes — the spec for clarify produces clarifications that
   sharpen the spec for clarify. Recursion intentional.

6. **Judgment calls captured by the implementer:**
   - **Worked-example #1 spec choice:** spec 018-slice-per-file
     in a reconstructed early-DRAFT shape (before slice 018-01 nailed
     down the dual-read contract). Picked over 022-contracts because
     018's pre-resolution shape produced cleaner Partial/Missing
     coverage across more categories — closer to a realistic
     ambiguity scan.
   - **Severity nomenclature:** adopted the five-status taxonomy
     (Clear / Partial / Resolved / Outstanding / Skipped) literally
     from the spec body. Each defined in SKILL.md's `## Output`
     section.
   - **TaxonomyCoverageTests bullet count:** implemented as
     `re.findall(r"(?m)^[-*]\s+\S", block)` to count bullet lines
     after each H3 heading, bounded at the next H2/H3 — robust to
     both `-` and `*` markers.
   - **Bonus `NoPyHelperTests` class** added to lock the AC #7
     "no `.py` helper" invariant deterministically (one test
     asserts `skills/clarify/` contains no `*.py` file other than
     `test_*.py`). Not in the spec's six-class enumeration; treated
     as additive surface coverage.

7. **Follow-ups filed to `docs/inbox.md`** during reconciliation:
   - `clarify/edge-case/empty-body:` Q2 above — clarify against an
     ultra-thin spec stub has undefined behavior. Future hardening
     could refuse with a structured error.
   - `clarify/test/exclusion-ordering:` AC #1's three "Do not use
     for" exclusions are ordered in SKILL.md but not pinned by tests
     (§1 above). Tightening could add an ordering assertion.
   - `scaffold/test/install-list-tier-1-full-set:` AC #7's referenced
     `test_scaffold_install_lists.py` does not exist; the `tier-1`
     full-set lockdown is a sound follow-up (§2 above). Would
     benefit all tiers, not just Tier 1; filed under the broader
     `scaffold/test/` tag prefix to match.
   - `judgment-skills/test/code-block-aware-h2-h3:` recommended by
     the reconciliation reviewer as a follow-up to §4. The
     `_h2_positions` / `_h3_blocks` regex helpers in
     `test_clarify_skill_surface.py` are not code-block-aware;
     the same pattern is shared with `test_pr_review_skill_surface.py`,
     `test_arch_review_skill_surface.py`, `test_vision_elicitation_skill_surface.py`,
     `test_slice_to_spec_skill_surface.py`, and
     `test_contracts_skill_surface.py`. A future contributor adding
     category-named H3s inside a fenced ```markdown block (e.g.
     `### Scope & Boundaries` as an example in clarify, or a sample
     `### Blockers` inside pr-review's worked example) could trip
     false matches. Cross-skill follow-up.

**Doc updates from this slice:**

- `skills/clarify/SKILL.md` — net-new (~378 lines). Active
  frontmatter; eight required H2 sections; six-category H3
  taxonomy with 3+ "what to check" bullets per category; explicit
  `## Output` spec; gotchas covering (a)-(d) per AC #2.
- `skills/clarify/test_clarify_skill_surface.py` — net-new (~487
  lines). 30 tests across 7 classes (six required + bonus
  `NoPyHelperTests`).
- `skills/clarify/worked-example-jig.md` — net-new (~221 lines).
  Reconstructed early-DRAFT scan of spec 018-slice-per-file.
- `skills/clarify/worked-example-saas.md` — net-new (~222 lines).
  Non-jig OAuth/SaaS hypothetical with deliberate ambiguity.
- `skills/scaffold-init/scaffold.py` — +1 line: `"clarify"` under
  `_TIER_SKILLS["tier-1"]` (line 62).
- `docs/inbox.md` — three entries per §7 above.
- No new ADR required.
- No `architecture.md` changes.
