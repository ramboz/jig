---
status: DONE
dependencies: [100-03]
last_verified: 2026-07-24
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 100-04 — lint-subcommand

**Goal:** `decisions.py lint` sweeps an existing `lightweight-decisions.md` and
**reports** — never edits — the entries whose own text reads as ADR-worthy. This
is the one pass over what is **already on disk**, and the single place a lexical
evaluator is allowed to live: an advisory, report-only surface where a brittle
signal is low-stakes ([ADR-0042](../../decisions/adr-0042-decision-routing-gate.md)).
The write-time judgement is the assistant's (100-01); the lint is the backstop
for records the guidance never saw.

**DoR:**
- ✅ [ADR-0042](../../decisions/adr-0042-decision-routing-gate.md) confines the
  lexical evaluator to this advisory surface — it must not gate or edit anything.
- ✅ This slice owns the evaluator: a pure `evaluate_routing_signals` / marker
  table derived from `ADR_TRIGGER`'s two criteria (`BOUNDARY` alone, or
  `ALTERNATIVES ∧ LOAD_BEARING`). One evaluator, so the lint cannot drift from
  the rule it approximates.
- ✅ The must-not-flag corpus is jig's own file: one illustrative worked example
  (`lightweight-decisions.md:51-55`) and one `### [Date] — [Short title]` heading
  inside the `## Template` fence (`:33`). A lint that flags either is broken on
  the only corpus jig ships. (The evaluator prototype refused an ordinary "user
  interface" copy decision until narrowed — the brittleness ADR-0042 cites, and
  the reason this stays advisory-only.)

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

- An entry that is already a promotion stub (100-03) produces no finding — it has
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
- [x] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [x] AC3 asserted against the repo's real `docs/decisions/lightweight-decisions.md`,
      so a future edit to the illustrative example that breaks the lint fails CI.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] Host packages regenerated (`scripts/build_host_packages.py`).
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.
      _(No deferred DECISIONS — the three deferred follow-ups are scoped work,
      not open questions, so they went to `docs/inbox.md` per the routing
      rubric: refinement-todo is for decisions with a resolution trigger.)_

### Reconciliation sweep

| Artifact | Disposition | Why |
|---|---|---|
| `skills/memory-sync/decisions.py` | **rewrite** | `lint` (read-only), and the marker table narrowed after the craft review found five real false positives. |
| `skills/memory-sync/test_decisions.py` | **rewrite** | Lint ACs against jig's real shipped file, negative fixtures for the narrowed markers, and AST-based guards pinning the evaluator's single call site. |
| `docs/memory/glossary.md` | **new** | **advisory lint** — records that the honest risk is false NEGATIVES (ADR-0031), so "mitigated by the lint" is not over-read. |
| `docs/inbox.md` | **new** | The scaffold template's helper block still documents only `add-lightweight`. |
| `hosts/**` | **regenerate** | Helper mirror. |

See the spec-level `## Reconciliation sweep` for the full cross-slice table.

### Deviation log

The original slice text is preserved above. Implementation notes:

**§1 — the marker table was narrowed after the craft review found real false
positives.** ADR-0042 accepts that this signal is fallible and states a kill
criterion for it; the review supplied the concrete cases, each verified before
changing anything:

| Decision (all belong in the lightweight home) | Fired on |
|---|---|
| "Link the support address with the `mailto:` protocol instead of a contact form" | `BOUNDARY: protocol` |
| "Name the colour tokens after the Figma colour schema" | `BOUNDARY: schema` |
| "Use the outline bell icon rather than the filled one … lands with the icon-set migration" | `LOAD_BEARING: migration` |
| "Say 'Nothing here yet' instead of 'No data' … no new dependency" | `LOAD_BEARING: dependency` |
| "Replace the custom share icon with the platform glyph" | `LOAD_BEARING: replaces` |

The third is a brand/icon swap — the *first* example in `lightweight-decisions.md`'s
own opening line. Changes made:

- `BOUNDARY` now holds **only qualified phrases** — bare `protocol` and `schema`
  removed, `wire protocol` and `database schema` kept. This group flags with no
  second signal, so one over-broad member condemns a whole class on its own; the
  invariant is now stated at the table.
- `LOAD_BEARING` lost bare `dependency` and `migration`, and `replac(es|ing)` is
  qualified to a following implementation/library/module/path/layer noun. In
  practice `ALTERNATIVES` is near-universal prose ("X instead of Y" is how anyone
  describes any choice), so a `LOAD_BEARING` member is close to flagging alone.

Re-verified after narrowing: all seven false positives clear, and the three
must-flag cases (the #121 case, a bare boundary change, a database-schema change)
still flag. Negative fixtures added alongside `_UI_COPY_WITH_INTERFACE`.

**§2 — the lint inherits 100-02's section bound.** An unbounded `## Entries`
section fed trailing prose to the evaluator, so a project with a section below
its entries could raise findings against text that is not a decision at all.
Fixed in 100-02 (see its deviation log §1); asserted here by
`EntriesSectionBoundTests::test_lint_does_not_scan_the_following_section`.

**§3 — two assertions were weaker than their ACs.** AC1 requires the report to
name the matched *phrases*, but the test asserted only the group names, which
appear in the summary line regardless — dropping the phrase list would not have
failed anything. AC5's "entry count" was asserted with `assertIn("1", out)`, a
single character that matches almost any output. Both tightened.

**§4 — advisory framing is in the output, not just the docs.** The report ends
with a line stating that it matches wording rather than meaning and that each
finding needs judging. ADR-0042 makes the advisory status load-bearing; a
reader who only ever sees stdout would otherwise not learn it.
