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

## Slice 127-02 — bug-candidates-and-promotion

**Goal:** closing a bug can record a rule candidate beside its learning — a
trigger a diff can match and one check. `memory-sync` lists candidates with
their occurrence counts and turns a candidate into an active rule once it has
two occurrences. The reviewer takes no part in either step.

**Decision:** [ADR-0072](../../decisions/adr-0072-diff-triggered-review-rules.md)
§3 and §6; spec 127 D1 and D4.

**DoR:**
- ⬜ 127-01 is DONE (file contract, lint, shared parser).
- ✅ The bug record template comes from `_record_text`, whose `## Learning`
  section is emitted at `skills/bug-fix/bug.py:303`.
- ✅ The `→ DONE` checks run in `transition_bug` (`bug.py:1023-1040`): review
  evidence, then the learning check.
- ✅ `memory.py` owns `docs/memory/` (spec A6) and already uses
  `_common.project_layout` (`skills/memory-sync/memory.py:33`).

**Acceptance Criteria:**

1. **The bug template shows the optional block.** A new bug record's
   `## Learning` section carries an HTML comment that shows the optional
   `**Review rule candidate:**` block: `Id`, `Paths` and/or `Diff`, `Check`,
   optional `Seen in:` refs. Existing records are not rewritten. Adding a
   block to a closed record is an amendment that needs owner approval (spec
   A11); historic lessons go through a hand-written active rule instead.
2. **DONE checks the block's shape, not its quality.** When a bug record's
   `## Learning` section has a candidate block, `bug.py transition <id> DONE`
   validates it with the 127-01 parser. The same field rules as `rules-lint`
   apply, except the two-occurrence bar. A malformed block refuses DONE with a
   diagnostic that names the field. A record with no block transitions exactly
   as today. Deleting the block is the escape; no new bypass variable.
3. **`bug.py` writes nothing to `docs/memory/`.** A test pins that the DONE
   path with a candidate block leaves `review-rules.md` and `learnings.md`
   byte-identical.
4. **Candidates are listed with their occurrences.** `memory.py
   rules-candidates` scans `<docs>/bugs/*.md` records in `DONE` and groups
   candidate blocks by id. For each id it prints:
   - its distinct occurrence refs: each bug that carries it, plus their
     `Seen in:` refs;
   - whether it meets the bar of two;
   - whether an active rule with that id already exists;
   - whether the blocks disagree on Paths, Diff or Check.

   It exits `0`; the listing is advisory.
5. **Promotion writes an active rule only at the bar.** `memory.py
   rules-promote <id>` appends an active entry to the working-tree
   `review-rules.md`, with provenance merged from every block with that id and
   `Added` set to today. It refuses, with exit `1` and a reason, when:
   - the id has fewer than two distinct occurrences;
   - the id is already active;
   - the blocks disagree and `--from <bug>` was not given to pick one.

   The written file passes `rules-lint`. The command prints that the change
   lands through a PR reviewed by the file's code owner (127-01 AC8).
6. **The two skills document the steps.**
   - `bug-fix/SKILL.md` step 5 describes the optional block. Use it when the
     miss could be caught from a diff; otherwise leave the lesson as prose.
   - `memory-sync/SKILL.md` describes the promotion step:
     - Judge whether the occurrences are really the same pattern.
     - Merge differently named candidates by hand with `--from`.
     - In the jig repo, when spec 126's recall harness exists, replay the candidate against its
       incidents before proposing it.
     - The reviewer subagent never runs these commands.

**Edge cases to cover explicitly:**
- Two bugs carry the same id with identical fields: one entry whose provenance
  lists both.
- A `Seen in:` ref that repeats the carrying bug's own id is counted once.
- A candidate block inside a fenced code block in `## Learning` is ignored.
- A non-`DONE` bug's block is not listed (it can still fail its DONE check).

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

**Anti-horizontal-phasing check:** after this slice, a developer closing a bug
can leave a diff-readable rule candidate. The second bug with the same pattern
makes it promotable with one `memory-sync` command, and from then on 127-01
asks every matching review about it.

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
| `docs/bugs/README.md` | `no-op` | _TBD — board columns unchanged unless the slice adds one._ |
| `skills/bug-fix/SKILL.md` / `skills/memory-sync/SKILL.md` | `updated` | _TBD — AC6._ |
| `docs/refinement-todo.md` | `no-op` | _TBD — the "Instrument the review→learnings→clarify loop" entry stays deferred; this slice harvests from bug records, not the review corpus._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TBD at close._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TBD at close._ |
