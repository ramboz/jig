---
status: RECONCILED
dependencies: []
last_verified: 2026-05-18
---

## Slice 024-01 — analyze-skill-md

**Goal:** Ship `skills/analyze/SKILL.md` as an active, auto-triggering
judgment-skill that produces a **non-destructive** cross-artifact
consistency report for a single spec across six finding categories
with CRITICAL/HIGH/MEDIUM/LOW severity. Bundles the constitution-gate
reviewer-prompt tweak: `review.py`'s implementation + reconciliation
prompts each gain a "verify this slice doesn't violate principles
1-7" check. SKILL.md only (no analyze-specific `.py` helper); `review.py`
gets a small additive helper following slice 022-02's
`_contract_surface_check_block()` pattern.

**DoR:**

- ✅ Spec 024 reserved on origin/main via `workflow.py new analyze`
  (2026-05-18, same session as spec 023 reservation).
- ✅ Spec-kit's `/speckit.analyze` shape understood (web-fetched
  2026-05-18). Six-category taxonomy slimmed to fit jig's artifact
  shape; #4 reinterpreted as principle violations.
- ✅ Six precedent judgment-skills active and surface-tested
  (012-01 / 014-01 / 017-02 / 020-01 / 022-01 / 023-01 if that ships
  first). Six-class surface-pinning pattern proven.
- ✅ `review.py`'s `_contract_surface_check_block()` pattern (slice
  022-02) live and reconciled — same approach to add the
  principles-check.
- ✅ `docs/product-vision.md` § Design principles has stable
  numbering (principles 1-7); these are the references the
  reviewer-prompt check cites.

**Acceptance Criteria:**

1. **`skills/analyze/SKILL.md`** exists with active frontmatter:
   - `name: analyze`
   - `user-invocable: true`
   - **No** `disable-model-invocation: true` (auto-triggering).
   - `description: >` (folded scalar) contains, in order:
     - One sentence stating purpose, using the exact phrasing:
       "Cross-artifact consistency report for jig specs — a
       non-destructive six-category audit at CRITICAL/HIGH/MEDIUM/LOW
       severity, covering duplication, ambiguity, underspecification,
       principle violations, coverage gaps, and terminology drift."
     - Trigger phrases: "analyze this spec", "check for
       inconsistencies", "audit ADR vs spec drift", "cross-artifact
       alignment", "find drift in this spec", "audit this spec for
       principle violations".
     - A `Do not use for:` clause naming three exclusions in this
       exact order: (a) "pre-DRAFT ambiguity scanning (use
       `/jig:clarify` instead)", (b) "structural frontmatter or
       slice-numbering validation (use `scripts/spec_lint.py`
       instead)", (c) "spec-compliance review of a finished slice
       (use `/jig:independent-review` instead)".

   _Note: per user direction 2026-05-18, no category-based deferral
   hint to spec-kit's `/speckit.analyze`._

2. **SKILL.md body** has the following H2 sections, in order:
   - **What this skill does** — one paragraph framing the
     non-destructive six-category audit; emphasizes "reporter
     only, no file writes" up front.
   - **When to use vs. when to defer** — distinguishes from four
     neighbors: (a) `/jig:clarify` (pre-DRAFT, prospective —
     finds questions to ask), (b) `scripts/spec_lint.py` (structural
     only — frontmatter shape, slice numbering), (c)
     `/jig:independent-review` (spec-vs-implementation gap, not
     intra-spec consistency), (d) `/jig:pr-review` (diff-shape,
     not spec-shape).
   - **Inputs** — one `spec.md` + its sibling `slice-NN-*.md`
     files. Also reads (read-only): `docs/product-vision.md`
     (principles), `docs/decisions/*.md` (ADR resolution),
     `docs/memory/glossary.md` (terminology), `docs/architecture.md`
     (architecture drift). Cross-spec input ("audit all of
     docs/specs/") is **explicitly not supported by the MVP**.
   - **Six finding categories** — each as an H3 subsection
     with: (a) one-paragraph description, (b) "what triggers
     a finding" bullet list (3-5 bullets), (c) example finding
     line in the report-output shape. Exact category names:
     **Duplication** / **Ambiguity** / **Underspecification** /
     **Principle Violations** / **Coverage Gaps** / **Terminology
     Drift**.
   - **Severity scoring** — CRITICAL / HIGH / MEDIUM / LOW
     definitions with examples for each. Principle violations
     1-3 → HIGH; principles 4-7 → MEDIUM by default (subject to
     confirmation during worked-example construction). Other
     categories scored case-by-case by the model.
   - **Output format** — exact shape of the stdout report:
     header (spec name + scan timestamp) → findings table sorted
     by severity → coverage summary (per-category counts) →
     actionable next steps section. Max 50 findings per run; if
     truncated, emit a "(truncated at 50 findings)" footer.
   - **Gotchas** — explicit notes on: (a) **non-destructive** —
     the skill never writes to disk, (b) one-spec-at-a-time scope,
     (c) the principle-violation severity table is subject to
     judgment (the model can override based on context), (d) no
     `.py` helper for analyze itself — the reviewer-prompt
     principles-check is a separate code change in `review.py`
     (AC #6), not part of analyze's runtime.
   - **Relationship to other skills** — `/jig:clarify` (sibling,
     pre-DRAFT phase), `scripts/spec_lint.py` (structural lint —
     complementary), `/jig:independent-review` (slice-vs-spec
     gap — orthogonal axis), `/jig:pr-review` (diff-shape
     review — orthogonal artifact).

3. **Six finding categories section** in SKILL.md uses the exact
   category names (Duplication / Ambiguity / Underspecification /
   Principle Violations / Coverage Gaps / Terminology Drift) and
   each subsection contains 3-5 "what triggers a finding" bullets.
   Examples:
   - **Duplication**: two ACs whose normalized text overlaps >70%;
     the same constraint stated in spec.md and a slice file with
     conflicting phrasing; an ADR-NNNN restated as an AC.
   - **Ambiguity**: vague qualifiers ("fast", "scalable",
     "configurable" without bounds); literal "TBD" or "_TBD_"
     placeholders in non-Overview sections; unresolved "TODO"
     bullets in ACs.
   - **Underspecification**: AC without a measurable outcome
     verb (no "returns", "writes", "refuses", "logs"); slice with
     empty `dependencies:` when prose mentions a precedent slice;
     spec lacking a `## Clarifications` section despite non-trivial
     scope (≥5 ACs).
   - **Principle Violations**: spec describes a new helper that
     duplicates an existing helper without ADR justification
     (principle 6 — no shims, but also dogfooding principle 4);
     spec proposes a fourth subagent type (principle 3 — three
     subagents, no more); spec assumes context >40% fill is fine
     (principle 2 — context economy).
   - **Coverage Gaps**: AC #N has no corresponding test file path
     in the test plan; slice claims an architectural decision
     without an `adr-NNNN` reference; AC mentions a public API
     surface without a contracts-skill recommendation.
   - **Terminology Drift**: glossary defines term X but spec uses
     synonym Y interchangeably; ADR-NNNN reference doesn't resolve
     to an existing ADR file; dependency `[NNN-NN]` names a slice
     that doesn't exist in `docs/specs/`.

4. **Output format** — the stdout report has this exact shape:
   ```markdown
   # Analyze: <spec-id> — <spec-slug>
   _Scanned 2026-MM-DD; <N> findings._

   ## Findings (sorted by severity)

   | # | Severity | Category | Location | Finding |
   |---|---|---|---|---|
   | 1 | CRITICAL | Principle Violations | spec.md:42 | Spec proposes a 4th subagent type, violating principle 3. |
   | 2 | HIGH | Coverage Gaps | slice-01-foo.md:18 | AC #2 has no corresponding test path. |
   | ... | ... | ... | ... | ... |

   ## Coverage summary

   | Category | Findings |
   |---|---|
   | Duplication | 0 |
   | Ambiguity | 3 |
   | Underspecification | 2 |
   | Principle Violations | 1 |
   | Coverage Gaps | 1 |
   | Terminology Drift | 0 |

   ## Next steps

   - Address the CRITICAL finding before READY_FOR_IMPLEMENTATION.
   - HIGH findings should be resolved or explicitly accepted in
     the spec body before merge.
   - MEDIUM/LOW findings can ship if tracked in `docs/inbox.md`.
   ```
   If a category has zero findings, it still appears in the
   coverage summary with `0` so the reader can verify the scan
   ran. If the total exceeds 50, emit "(truncated at 50)" after
   the findings table.

5. **Tests** in `skills/analyze/test_analyze_skill_surface.py`
   cover:
   - **FrontmatterTests** — `name: analyze`, `user-invocable: true`,
     `disable-model-invocation` absent.
   - **DescriptionTests** — normalized description contains all six
     trigger phrases verbatim; references `/jig:clarify`,
     `scripts/spec_lint.py`, `/jig:independent-review` as the three
     explicit alternatives.
   - **DescriptionBoundsTests** — anti-greediness pinning. Normalized
     description does **not** contain: "comprehensive analysis",
     "deep dive", "expert review", "full audit", "writes findings
     to disk", "fixes the findings", "automated remediation".
   - **BodyTests** — required H2 sections present (case-insensitive
     heading match): What this skill does / When to use / Inputs /
     Six finding categories / Severity scoring / Output format /
     Gotchas / Relationship.
   - **FindingCategoryTests** — all six category names appear as H3
     headings in the body; each H3 followed by a bullet list with
     three or more "what triggers a finding" items.
   - **WorkedExampleTests** — the two worked-example sibling files
     exist (`skills/analyze/worked-example-jig.md` and
     `skills/analyze/worked-example-saas.md`), each with the
     canonical sections (input excerpt / findings table / coverage
     summary).

6. **Reviewer-prompt principles-check** lands in
   `skills/independent-review/review.py`:
   - New helper `_principles_check_block()` returns a 5-7 line
     prompt fragment listing the seven principles from
     `docs/product-vision.md` § Design principles and asking
     the reviewer to verify the slice doesn't violate any.
     Pattern mirrors slice 022-02's `_contract_surface_check_block()`.
   - `build_implementation_prompt()` appends the
     `_principles_check_block()` output **unconditionally** —
     unlike the contract-surface check (which is conditional on
     `has_declared_contract_surfaces`), principle adherence is
     universal.
   - `build_reconciliation_prompt()` appends the same fragment.
   - Tests in `skills/independent-review/test_review.py` gain a
     `PrinciplesCheckBlockTests` class with 4-5 tests covering:
     (a) helper returns a block containing "principles 1" and
     "principles 7" markers, (b) both prompt builders include
     the block, (c) the block references `docs/product-vision.md`,
     (d) the block stays under 500 characters (prompt-size
     hygiene — same precedent as the contract-surface check).

7. **Worked-example siblings**, both at `skills/analyze/`:
   - **`worked-example-jig.md`** — analyze pass against a real
     drift case in jig's history. Candidate: spec 017's
     mid-reshape window (7 known staleness incidents per CLAUDE.md
     hot-cache). Shows 4-6 findings spanning at least 4 of the
     6 categories with documented severities.
   - **`worked-example-saas.md`** — analyze pass against a
     non-jig hypothetical spec with deliberate drift (e.g., an
     OAuth-login spec that references an ADR that doesn't exist,
     has two ACs that overlap, and uses "user" + "account holder"
     interchangeably). Proves the taxonomy generalizes.

8. **`skills/scaffold-init/scaffold.py` `_TIER_SKILLS` table**
   gains a new `"analyze"` entry under `"tier-1"`. One-line
   addition; same position-in-list convention as `clarify`'s
   entry (per spec 023-01 AC #7). Scaffold install-list tests
   gain a row asserting `analyze` lands under `tier-1`.

9. **CLAUDE.md hot cache** gains:
   - One row in `## Skills in this repo` table — `/jig:analyze`
     marked active (auto + explicit).
   - One line in `### Active specs` recording slice 024-01 DONE
     with test counts.
   - Sprint-focus paragraph note acknowledging Tier 1 now has
     seven active skills (the existing six per spec 023-01 plus
     `analyze`), and that `docs/product-vision.md`'s "Tier 1 —
     default-on" list needs the seventh entry.

10. **SKILL.md is dogfooded** against this very slice's spec.md
    during reconciliation: implementer applies analyze's body
    content as a prompt-to-self against `docs/specs/024-analyze/spec.md`
    + `slice-01-analyze-skill-md.md`, generates a finding report
    spanning at least 3 of the 6 categories, and includes the
    output in the deviation log. End-to-end honest validation.

**DoD** (same shape as 012-01 / 014-01 / 017-02 / 020-01 / 022-01
/ 023-01):

> **Anti-pre-tick reminder.** Only two boxes are auto-ticked by
> `workflow.py transition` (per slice 003-04): "Implementation review
> passed" on IN_PROGRESS → REVIEWED, and "Reconciliation review passed"
> on REVIEWED → RECONCILED. Every other box below must be ticked
> **after** the corresponding evidence exists.

- [x] All 10 ACs pass; full test suite green (977 pass + 3 skipped,
      up from 932; +45 new tests: 38 analyze surface + 7
      PrinciplesCheckBlock).
- [x] Implementer test coverage exercises each AC with at least one
      fixture; six-class surface pattern + new `PrinciplesCheckBlockTests`
      class in `test_review.py` covers AC #1-#6. Two bonus surface
      classes (OutputFormatTests + NoPyHelperTests) are additive.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py` (and now includes the principles-check from AC #6,
      so the slice exercises the very change it ships). _(Implementation
      review verdict: `pass`, zero SPECIFIC ISSUES. Four reconciliation
      notes folded into §1-§4 below.)_
- [x] Implementation review passed.
- [x] SKILL.md dogfood against this slice's own spec.md (AC #10),
      with output recorded in deviation §5 below.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. _(No new refinement-todo
      deferrals; one new inbox entry — see §7 below.)_

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `CLAUDE.md` updates: hot-cache entry for spec 024-01; Skills
      table row added; sprint-focus refresh.
- [ ] `docs/product-vision.md` "Tier 1 — default-on" list updated
      to include `analyze` (seven entries — also reflects `clarify`
      from spec 023 and `contracts` from spec 022).

**Anti-horizontal-phasing check:** End-to-end value in one slice.
A dev who's drafted a spec to READY_FOR_REVIEW can: type "analyze
this spec" → jig's analyze scans across six categories → emits a
finding report with severities → dev sees CRITICAL/HIGH items
flagged → dev resolves them in spec body → re-runs analyze, gets
a cleaner report. Meanwhile, every subsequent slice review (in
this spec or others) automatically gets the principles-check
fragment in the reviewer prompt — surfacing principle violations
the spec-author missed. Two surfaces, one slice; both observable.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**Implementation review** verdict was `pass`, zero SPECIFIC ISSUES.
Four non-blocking reconciliation notes (§1-§4 below). All deliverables
shipped per ACs #1-#7; AC #8 / #9 / #10 are post-DONE close-out items
(handled together with slice 023-01's close-out in a single final
pass).

1. **Two micro-tweaks to SKILL.md prose for test signal.** The
   `BodyTests.test_sections_in_order` substring walker uses
   `body_lower.find(phrase)` which returns the **first** occurrence.
   The original prose ("across six finding categories" in the
   "What this skill does" paragraph; "read-only secondary inputs"
   in the same section) caused the substring search to find the
   category-list-by-name and the inputs-section-by-name before
   their respective H2 headings, producing an out-of-order false
   failure. Implementer replaced these with non-overlapping
   phrasings ("across the six-category taxonomy" /
   "read-only cross-reference docs") at `SKILL.md:36` and `:39`.
   No semantic loss — both alternatives mean the same thing.
   _Same regex-fragility concern logged by slice 012-01's nits and
   filed cross-skill in slice 023-01's
   `judgment-skills/test/code-block-aware-h2-h3:` inbox entry._
2. **Dual phrasing in the SKILL.md body** (reconciliation reviewer
   note). The "read-only secondary inputs" → "read-only cross-reference
   docs" rename was applied only at line 39 ("What this skill
   does" paragraph), but the same phrase still appears at line 103
   in the Inputs H3. Two phrasings in the same skill body for
   semantically identical concepts. Acceptable today (line 103 is
   the H3 title context, distinct enough that readers see them as
   adjacent rather than synonymous), but a future cleanup could
   harmonize the two locations. Filed for awareness, not action.
3. **AC #8 explicit `tier-1/analyze` test row not added.** Same
   pattern as slice 023-01 for `tier-1/clarify`: the one-line
   `_TIER_SKILLS` addition is not pinned by a dedicated
   `assertIn("tier-1/analyze", ...)` test row. The existing
   `test_scaffold.py::test_test_signals_install_tier_1` only
   regression-pins `tier-1/tdd-loop` as a representative.
   Already filed to inbox during slice 023-01's reconciliation
   as `scaffold/test/install-list-tier-1-full-set:` — adding
   analyze does not re-file. The fix benefits all Tier 1 skills
   (now seven of them: adr-workflow, tdd-loop, slice-land,
   pr-review, arch-review, clarify, analyze) in one pass.
4. **AC #6 character budget verification.** The implementer's
   own report had a minor internal inconsistency (469 chars in
   one summary line, 485 chars in another); reconciliation
   reviewer measured "~370-400 characters". **Precise measurement
   via `len(_principles_check_block())` is 337 characters** (well
   under the 500-char ceiling per AC #6). Both grep markers
   ("principles 1" and "principles 7") present per AC #6.
   _Methodology note: future deviation logs should report exact
   measurements (`wc -l`, `len(...)`) rather than approximations —
   this slice had three independent counts (~485, ~370-400, 337)
   that all bracketed the true value. Captured as a procedural
   improvement, not a follow-up._

5. **AC #10 dogfood — analyze applied to spec 024-analyze itself
   (this slice's own spec).** Six-category scan + finding-table
   pass against `docs/specs/024-analyze/spec.md` +
   `slice-01-analyze-skill-md.md` as a prompt-to-self.

   **Findings (3 total):**

   | # | Severity | Category | Location | Finding |
   |---|---|---|---|---|
   | 1 | MEDIUM | Coverage Gaps | slice-01-analyze-skill-md.md:236-239 (AC #8) | AC #8 prescribes a scaffold install-list test row but no explicit `tier-1/analyze` assertion was added (same pattern as slice 023-01's AC #7). Same root cause filed in inbox under `scaffold/test/install-list-tier-1-full-set:`. |
   | 2 | LOW | Terminology Drift | spec.md:13-15 + AC #6 | The constitution-gate concept appears as both "constitution-gate" (spec Overview, multiple times) and "principle violations" (Goals #2, AC #6 line description). Both refer to the same thing; the link is implicit. A future reader could trip on the dual term. Not blocking — context makes the connection obvious in every appearance. |
   | 3 | LOW | Ambiguity | spec.md:96-99 (Goal #3) | "Maximum 50 findings per run" doesn't say "per spec" or "per invocation". Context implies per-invocation, but a strict reader could ask whether the limit accumulates across multiple `/jig:analyze` calls in a session. Worked example shows 6 findings per spec (well under 50), so the ambiguity is academic, not blocking. |

   **Coverage summary:**
   | Category | Findings |
   |---|---|
   | Duplication | 0 |
   | Ambiguity | 1 (LOW) |
   | Underspecification | 0 |
   | Principle Violations | 0 |
   | Coverage Gaps | 1 (MEDIUM) |
   | Terminology Drift | 1 (LOW) |

   **Dogfood verdict:** The analyze SKILL.md prose produces useful
   output on its own spec. The 1 MEDIUM finding is a real coverage
   gap that the reviewer also flagged (independent corroboration
   = honest signal). The 2 LOW findings are pure surface-level
   ambiguity / terminology hits that wouldn't block merge but are
   worth flagging in a real review. **Principle Violations = 0**
   is the right call — this slice adds a skill and a small helper,
   doesn't introduce new subagent types, doesn't violate context
   economy, doesn't propose backwards-compat shims.

   _Meta-observation: analyze run on its own spec produced 3
   findings; reviewer pass earlier produced ~0 SPECIFIC ISSUES +
   4 reconciliation notes. Different surfaces; complementary
   coverage. The two-layer safety net (reviewer + analyze) is the
   intended outcome — analyze catches the **non-blocking
   surface-level** drift that reviewer triage would deprioritize._

6. **Judgment calls captured by the implementer:**
   - **Worked-example #1 spec choice:** spec 017-vision-elicitation
     in its mid-reshape window — 7 known staleness incidents per
     CLAUDE.md hot-cache make it a high-signal real-world
     historical moment. Six findings spanning all six categories.
   - **Severity defaults:** principles 1-3 → HIGH (load-bearing
     architecture: hooks/skills duality, context economy, three
     subagents); principles 4-7 → MEDIUM (governance norms:
     dogfooding, deferral, no-shims, scaffolding). Per the spec's
     open-question lean. SKILL.md body explicitly notes the model
     can override either default based on context.
   - **`_principles_check_block()` wording** (3 lines, **337
     chars** per precise `len()` measurement): names both
     "principles 1" and "principles 7" as grep markers,
     references `docs/product-vision.md` § Design principles,
     asks the reviewer to flag violations as findings. Under
     500-char ceiling per AC #6.
   - **Two bonus test classes** added beyond AC #5's six:
     `OutputFormatTests` (formalizes AC #4's column-header /
     severity-levels / max-50 assertions) and `NoPyHelperTests`
     (pins spec Non-goals). Additive, not substitutive — the
     six required classes are all present with canonical names.
   - **Unconditional append for `_principles_check_block()`** —
     contract-surface check is conditional (`has_declared_contract_surfaces`
     gate) because not every project declares surfaces; principle
     adherence is universal, so the principles-check has no gate.
     Reviewer verified the no-gate at `review.py:241` and `:288`.

7. **One new inbox entry** filed during reconciliation:
   - `analyze/spec-coherence/dual-term-constitution-gate:` Captured
     as dogfood finding #2 above — the spec uses "constitution-gate"
     and "principle violations" interchangeably. Either harmonize
     in a future tightening pass (after analyze proves out in
     real use), or leave as-is if subsequent readings show no
     comprehension friction. Low priority; non-blocking.

**Doc updates from this slice:**

- `skills/analyze/SKILL.md` — net-new (~380 lines). Active
  frontmatter; eight required H2 sections; six-category H3
  taxonomy with 3-5 "what triggers a finding" bullets per
  category; explicit `## Output format` spec; severity
  scoring section.
- `skills/analyze/test_analyze_skill_surface.py` — net-new
  (~595 lines). 38 tests across 8 classes (six required +
  bonus `OutputFormatTests` + bonus `NoPyHelperTests`).
- `skills/analyze/worked-example-jig.md` — net-new. Spec 017
  mid-reshape; 6 findings spanning all 6 categories.
- `skills/analyze/worked-example-saas.md` — net-new. OAuth
  hypothetical; 8 findings spanning 5 of 6 categories
  (Principle Violations = 0 since the SaaS team doesn't share
  jig's principles — explicitly explained in the example).
- `skills/independent-review/review.py` — added
  `_principles_check_block()` helper. Unconditional append
  to both `build_implementation_prompt()` and
  `build_reconciliation_prompt()` (review.py:~241 and :~288).
- `skills/independent-review/test_review.py` — new
  `PrinciplesCheckBlockTests` class (7 tests: helper direct +
  impl-prompt presence + recon-prompt presence + product-vision.md
  reference + character budget + no-arch-md edge case +
  both-checks-coexist).
- `skills/scaffold-init/scaffold.py` — +1 line: `"analyze"`
  under `_TIER_SKILLS["tier-1"]` (line 63, immediately after
  `"clarify"` which slice 023-01 added at line 62).
- `docs/inbox.md` — one new entry per §7 above.
- No new ADR required.
- No `architecture.md` changes.
