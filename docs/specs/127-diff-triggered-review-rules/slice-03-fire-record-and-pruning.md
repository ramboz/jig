---
status: DRAFT
dependencies: [adr-0072, 127-01]
last_verified: 2026-11-21
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 127-03 — fire-record-and-pruning

**Goal:** every craft and `bug-review` verdict records which rules the reviewer
was shown. `memory-sync`'s routine reports, per rule, how often it was shown
and how often it produced a finding, and proposes removing the rules that no
longer earn their place. Nothing is removed without a reviewed edit.

**Decision:** [ADR-0072](../../decisions/adr-0072-diff-triggered-review-rules.md)
§6; extends the [ADR-0014](../../decisions/adr-0014-review-evidence-model.md)
§2 verdict schema with one optional field.

**DoR:**
- ⬜ 127-01 is DONE (selection function, `[rule:<id>]` tag instruction).
- ✅ `record-review` already stamps an optional frontmatter line
  (`substrate:`, `review.py:2061-2072`). Slice records live at
  `<spec>/reviews/slice-NN-<pass>.md`; bug records live at
  `<docs>/bugs/reviews/bug-NNN-<pass>.md`
  (`skills/_common/review_evidence.py:245-258`, `:807-820`).
- ✅ Findings already carry bracket tags that the shared parser reads
  (`_TAGGED_ENTRY_RE`, `review_evidence.py:487`).
- ⬜ Check whether spec 124-02 (prompt-time `reviewed_commit` + deliverables
  digest) has landed; AC1 rides its capture if so.

**Acceptance Criteria:**

1. **Verdicts record the rules shown.** `record-review` for `--pass craft` on a
   slice, and for `--bug … --pass bug-review`, recomputes the 127-01 selection
   and stamps one of:
   - `review_rules: <id>, <id>` — the rules shown, in prompt order;
   - `review_rules: none` — selection ran and nothing matched;
   - `review_rules: unavailable (<reason>)` — selection could not run (127-01
     AC3: no base resolves, or not a git repository).

   When the cap cut rules, it also stamps `review_rules_overflow: <id>, …`.
   If spec 124-02's prompt-time capture exists when this slice is built, the
   ids are captured there when the prompt is built and stamped from it,
   instead of being recomputed. Other passes get no field. Records without the field still parse and still
   clear the gate exactly as today (`verdict_clears` unchanged).
2. **The report counts shown and cited.** `memory.py rules-report` reads the
   working-tree `review-rules.md` and every slice and bug verdict record. For
   each active rule it prints: `Added`, distinct occurrences, times shown, times
   cited (a `[rule:<id>]` tag on a `SPECIFIC ISSUES` entry of a record that
   showed it), and the last date shown (from `reviewed_at`). It also prints the
   promotable candidates from 127-02's listing.
3. **It proposes removals with a reason.** The report lists a rule as a removal
   proposal when any of these holds:
   - it was not shown in any record dated more than `--window` days (default
     90) after its `Added` date;
   - it was shown 5 or more times and cited 0 times;
   - none of its `Paths` globs matches a file in `git ls-files`;
   - a provenance `bug NNN` record, or a `learning "…"` heading, no longer
     exists.

   Each proposal names the rule and the reason. The command exits `0`; it is
   advisory.
4. **The routine surfaces it; a person removes.** `memory-sync/SKILL.md`'s
   session-end consolidation runs `rules-report` when `review-rules.md` has at
   least one rule, and passes removal proposals and promotable candidates to
   the user. Removing a rule is a normal edit to the protected file, reviewed
   in a PR (git history is the audit trail). No command deletes a rule.
5. **It does not grow into the gated rollup.** `rules-report` counts rule ids
   only. It does not bucket findings by `[spec]`/`[impl]` or by `/jig:analyze`
   category, which is the rollup the refinement-todo entry "Instrument the
   review→learnings→clarify loop before building it" still gates. The skill
   text says so.

**Edge cases to cover explicitly:**
- A record that cites `[rule:x]` but did not show `x` (a reviewer slip): not
  counted as a citation; the report notes the mismatch once.
- A rule added after some records were written: only records dated on or
  after `Added` count toward "shown".
- An overflow rule is not counted as shown.
- A re-recorded verdict (ADR-0014 §4 overwrite) counts once, by its current
  file.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: if this slice closes the spec,
      compress the Active-specs entry; otherwise leave it.

**Anti-horizontal-phasing check:** after this slice, the end-of-session
`memory-sync` run tells the developer which review rules have gone quiet or
never find anything, with a reason for each. The rules file stays small
without anyone auditing it by hand.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TBD — not yet implemented (recorded, not built)._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/specs/README.md` | `updated` | _TBD — regenerate by `workflow.py status-board` at close._ |
| `skills/independent-review/SKILL.md` | `updated` | _TBD — the `review_rules:` field in the verdict schema description._ |
| `skills/memory-sync/SKILL.md` | `updated` | _TBD — AC4 / AC5._ |
| `docs/refinement-todo.md` | `no-op` | _TBD — confirm the review→learnings→clarify entry's count and trigger are untouched (AC5)._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TBD at close._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TBD at close; if this slice closes spec 127, add a one-line Key-terms index entry._ |
