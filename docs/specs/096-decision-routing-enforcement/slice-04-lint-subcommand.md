---
status: READY_FOR_IMPLEMENTATION
dependencies: [096-01]
last_verified: 2026-07-22
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-04 — lint-subcommand

**Goal:** `decisions.py lint` sweeps an existing `lightweight-decisions.md` and
reports the entries whose own text disqualifies them from living there. 096-01
and 096-02 guard the write paths; this is the one pass over what is **already on
disk**, written before either gate existed.

**DoR:**
- ✅ 096-01 is DONE and exports the evaluator as an importable pure function
  (096-01 AC8). This slice adds no new rule — it runs the same one over a file
  instead of over CLI arguments.
- ✅ The must-not-flag corpus is jig's own file: one illustrative worked example
  (`lightweight-decisions.md:51-55`) and one `### [Date] — [Short title]` heading
  inside the `## Template` fence (`:33`). A lint that flags either is broken on
  the only corpus jig ships.

**Acceptance Criteria:**

1. **A misfiled entry is reported.** Over a file containing an entry whose text
   trips the two-signal rule, `lint` names the entry (date + title), the matched
   groups and phrases, and the remedy (`decisions.py promote --title …`).
2. **Nothing is written, ever.** `lint` is read-only: the file is byte-identical
   after any run, including runs that report findings. Auto-promotion is out of
   scope for the whole spec, and a linter that edits is not a linter.
3. **Documentation is not linted.** The illustrative worked example and the
   `## Template` fence heading produce **no** findings. Asserted against jig's
   real shipped file, not a fixture.
4. **Exit code carries the verdict.** Exit 0 when clean, non-zero when findings
   exist, so the sweep is usable from a script or a future gate. `--exit-zero`
   reports without failing, for a report-only run.
5. **A clean file says so.** No findings prints an explicit clean line naming the
   file and the entry count scanned — silence is indistinguishable from a broken
   scan.
6. **Absent or foreign files behave like the rest of the helper.** A missing file
   reports "nothing to lint" and exits 0 (there is no misfiling in a file that
   does not exist, and `lint` must not seed one). A file with no `## Entries`
   heading raises the existing `_foreign_format_error`, unchanged.
7. **`--project-dir` and `layout.docs_root` are honoured** — the file is found
   and reported where the layout actually puts it (spec 084), as
   `_display_path` already does.

**Edge cases covered explicitly:**

- An entry that is already a promotion stub (096-03) produces no finding — it has
  been dealt with, and re-reporting it would make the lint's output permanently
  non-empty.
- An entry whose fields are split across multiple lines is scanned whole, not
  first-line-only.
- A file with zero real entries (jig's own, today) exits 0 with the clean line.

**Anti-horizontal-phasing check:** after this slice an operator can point the
helper at any project and get the list of decisions that are in the wrong home,
with the fix command for each — the backlog #121 describes as invisible becomes
enumerable.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [ ] AC3 asserted against the repo's real `docs/decisions/lightweight-decisions.md`,
      so a future edit to the illustrative example that breaks the lint fails CI.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] Host packages regenerated (`scripts/build_host_packages.py`).
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.
