---
status: READY_FOR_IMPLEMENTATION
dependencies: [096-01, 096-02]
last_verified: 2026-07-22
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-03 — promote-subcommand

**Goal:** `decisions.py promote --title "<existing>"` moves a misfiled entry to
an Architectural Decision Record (ADR) via `adr.py new`, seeds that ADR from the
entry's own fields, and replaces the entry with a stub that links forward. The
correction stops being a manual job, which is what makes 096-01's and 096-02's
flags actionable rather than merely informative.

**DoR:**
- ✅ 096-01 and 096-02 are DONE — the gate that surfaces the problem exists, and
  096-02's refusal message already names this subcommand as the remedy.
- ✅ `adr.py new <slug>` scaffolds an ADR and allocates its number, with
  `--no-push` / `--pr` / `--project-dir` (probed via `--help`). This slice calls
  that path rather than writing a second ADR writer.
- ✅ Nothing links a lightweight entry to an ADR today: `adr.py` has no
  lightweight-record awareness, `render_entry` (`decisions.py:218`) emits no
  back-reference field, and `docs/decisions/README.md:47-53` is hand-written
  prose outside the regenerated Index.

**Acceptance Criteria:**

1. **Promotion creates the ADR through `adr.py`.** `promote --title "<existing>"`
   invokes `adr.py new` — not a hand-rolled ADR writer — so numbering, the
   template, and the reservation path stay single-sourced. The slug defaults to a
   kebab-cased form of the entry title and is overridable with `--slug`.
2. **The ADR is seeded from the entry's own fields.** The entry's Decision,
   Context, and Scope land in the corresponding ADR sections rather than leaving
   an empty template for someone to retype — the fields already exist, and
   retyping is where content gets dropped.
3. **The entry is replaced by a forward-linking stub, not deleted.** The original
   `### <date> — <title>` heading stays addressable and its body becomes a
   pointer to the new ADR. A reader who follows an old reference to the entry
   must land on the record, not on a gap. Deleting it would break every existing
   link and erase the fact that the decision was once filed here.
4. **The ADR back-links to the entry it came from**, naming the original date, so
   the promotion is legible from both ends.
5. **Reservation flags pass through.** `--no-push` and `--pr` reach `adr.py new`
   unchanged, so promotion works on a feature branch without pushing to
   `origin/main`.
6. **Failure is atomic.** If `adr.py new` fails for any reason (unreachable
   template, reservation refused, network), `lightweight-decisions.md` is left
   **byte-identical** and the error is reported. A promotion that stubs the entry
   and then fails to create its target destroys the record.
7. **A missing or ambiguous `--title` refuses**, with the same matching rules and
   messages as 096-02 (AC6–AC8) — one title-matching contract across the helper.
8. **An already-promoted entry refuses.** Re-running `promote` on a stub exits
   non-zero naming the ADR it already points to, rather than creating a second
   ADR for one decision.
9. **The illustrative example and the `## Template` fence are not promotable** —
   same exclusion as 096-02 AC9.

**Edge cases covered explicitly:**

- A title that kebab-cases to a slug `adr.py` rejects (empty, leading digit,
  double hyphen) — refuse with the rule, do not silently mangle.
- An entry with an empty `**Context:**` or `**Scope:**` (both optional at write
  time) promotes with those ADR sections left as the template's own placeholder,
  not as the literal empty string.
- Promotion under `layout.docs_root: "."` (spec 084) writes both files where the
  layout actually puts them, not at the hardcoded default.

**Anti-horizontal-phasing check:** after this slice a flagged entry can be
corrected with one command, end-to-end — ADR created, entry stubbed, both linked
— rather than the flag naming a job the operator still has to do by hand.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [ ] AC6 (atomicity) is proven by an induced `adr.py` failure, not by
      inspection.
- [ ] 096-02's refusal message is updated to name `promote` concretely (096-02
      AC4 deferred the final wording here).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] Host packages regenerated (`scripts/build_host_packages.py`).
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.
