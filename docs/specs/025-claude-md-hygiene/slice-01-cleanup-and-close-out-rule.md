---
status: DONE
dependencies: []
last_verified: 2026-05-18
---

## Slice 025-01 — cleanup-and-close-out-rule

**Goal:** Apply the new "compress on close-out" rule to today's
CLAUDE.md, and codify the rule in the slice template + the
spec-workflow reconciliation checklist so it holds going forward.
End-to-end value in one slice: future contributors open CLAUDE.md
and see active work + load-bearing invariants, not implementation
history; the close-out checklist mechanically prevents regrowth.

**DoR:**

- ✅ Status board (`docs/specs/README.md`) maintained by
  `workflow.py status-board`; Notes column documented as
  curate-preserving across regen.
- ✅ Slice template has a `### Close-out (post-DONE)` section
  (slice 009-01), so the rule has a place to live.
- ✅ Reconciliation checklist exists in
  `skills/spec-workflow/SKILL.md` § "## Reconciliation checklist"
  and is the documented gate before `REVIEWED → RECONCILED`.
- ✅ User confirmed the framing 2026-05-18 ("accumulate in status
  board, compress in CLAUDE.md on close-out").

**Acceptance Criteria:**

1. **`CLAUDE.md` "Active specs" section** contains only specs with at
   least one slice in DRAFT / READY_FOR_REVIEW /
   READY_FOR_IMPLEMENTATION / IN_PROGRESS. After this slice lands, the
   section contains only spec 025 itself (DRAFT during implementation,
   then compressed when 025-01 itself transitions to DONE per AC #9).

2. **Load-bearing invariants from closed-spec CLAUDE.md entries are
   migrated** per a three-way rule, applied per-entry:
   - **(a) drop** if the fact is derivable from the spec dir + status
     board (e.g., test counts, reviewer-feedback narrative, deviation
     §-cross-refs);
   - **(b) migrate to status board Notes** if the fact is load-bearing
     for that specific slice (e.g., "first slice to use the
     `JIG_CONVENTIONS_APPROVED=1` escape — 017-01");
   - **(c) keep in CLAUDE.md as a one-liner** if the fact is
     cross-cutting and needed by future work without reading any
     spec dir (e.g., "ADRs live at `docs/decisions/adr-NNNN-<slug>.md`").
   The deviation log records one line per migration, naming the
   destination.

3. **CLAUDE.md "Current sprint focus" section** is rewritten to
   reflect what's actually active, or removed entirely if nothing is.
   The "Prior context (preserved for reference)" stanza is removed
   (git log is the canonical history; sprint-focus is not history).

4. **CLAUDE.md "Skills in this repo" table rows** are slimmed to
   1-2 lines each. Each row carries: name + one-line purpose + key
   active-trigger or invariant. No slice-by-slice "N tests / Y
   fixtures landed / reviewer caught Z" detail (that lives in the
   spec dirs).

5. **CLAUDE.md ADR stanzas** (ADR-0001 / ADR-0002 / ADR-0004 /
   ADR-0005) are removed from the Active-specs section. Cross-cutting
   load-bearing invariants from them (e.g., "ADRs live at
   `docs/decisions/adr-NNNN-<slug>.md`" from ADR-0004) get promoted
   into the existing `## Constraints for agents working on this repo`
   section as bullets — **not** a new "Key invariants" subsection
   (per spec.md Clarifications Q3). The `Key documents` table gains
   a `docs/decisions/` row so the index is discoverable. The ADR
   docs themselves remain untouched.

6. **`templates/docs/specs/slice-template.md` close-out section**
   is reframed. Today it reads:
   ```
   - [ ] `CLAUDE.md` updates: hot-cache entry for this spec/slice;
         Skills table promoted if applicable.
   ```
   New shape names compression-on-completion as the default, with
   skill-promotion-to-Skills-table only when the slice introduces
   a new skill. Suggested wording (the implementer may refine):
   ```
   - [ ] `CLAUDE.md` hygiene per slice 025-01 rule: if this slice
         closes the spec (all non-deferred slices DONE), compress
         the spec's "Active specs" entry — drop if derivable from
         the spec dir + status board, migrate load-bearing
         invariants to the status board Notes column, or keep a
         one-liner only for cross-cutting facts. If this slice
         introduces a new skill, add/update its row in the Skills
         table.
   ```

7. **`skills/spec-workflow/SKILL.md` reconciliation checklist** gains
   a "CLAUDE.md hygiene" gate, inserted between "Inbox triage" and
   "Memory-sync" (next to the other doc-touching gates). Suggested
   wording:
   ```
   - [ ] **CLAUDE.md hygiene** — if this slice closes the spec
         (all non-deferred slices DONE), apply the compress-on-
         close-out rule per the slice template's Close-out
         section. The Active-specs section should only carry
         in-flight work; load-bearing invariants migrate to the
         status board Notes column.
   ```

8. **No load-bearing fact is silently dropped.** The deviation log
   has a "## Compression decisions" subsection enumerating, per
   closed-spec CLAUDE.md entry, the disposition (drop / migrate to
   Notes / keep one-liner). Reviewer can audit each row by reading
   the diff alone.

9. **Self-dogfood.** When slice 025-01 itself transitions
   `RECONCILED → DONE`, its own CLAUDE.md entry gets compressed
   per the new rule. Since 025-01 closes spec 025 (025-02 is
   DEFERRED, not blocking), the rule prescribes compressing the
   entry to a one-liner (or removing if nothing load-bearing
   remains). The dogfood verifies the rule produces sensible
   behavior on its own surface.

10. **No new tests required.** This slice is content cleanup +
    template surgery; no helper code changes. The full test suite
    still runs green (no regressions). If the implementer chooses
    to add a regression test pinning the template's close-out
    wording (e.g., a `test_slice_template_close_out_names_compression`
    in an existing test file), that's optional surface coverage,
    not a DoD blocker.

**DoD:**

> **Anti-pre-tick reminder.** Only two boxes are auto-ticked by
> `workflow.py transition` (per slice 003-04): "Implementation review
> passed" on IN_PROGRESS → REVIEWED, and "Reconciliation review passed"
> on REVIEWED → RECONCILED. Every other box below must be ticked
> **after** the corresponding evidence exists.

- [x] All 10 ACs pass; full test suite green (988 pass + 3 skipped,
      no regressions).
- [x] Implementer test coverage: AC #10 declares no new tests
      required; no optional surface coverage added (would have been
      a `test_slice_template_close_out_names_compression` regression
      pin, deemed not worth the surface).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py implementation`; subagent type resolved to
      `general-purpose` (jig not registered as plugin in this
      session). Verdict: **pass** with 3 minor SPECIFIC ISSUES + 3
      RECONCILIATION NOTES — folded into deviation §7.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading, including
      the "## Compression decisions" subsection per AC #8.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. _(Two items closed: Scaffold.json
      manifest format RESOLVED; jig-memory-scan firing-rate trigger
      updated to "never bites in practice" — see deviation §4.)_

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`;
      Notes column curated per AC #2's migrations (009-01 got the
      `check_dod` close-out invariant; 025-01 got the compress-on-
      close-out rule summary).
- [x] `CLAUDE.md` self-dogfood per AC #9: spec 025's own entry
      compressed under the new rule. **Outcome:** dropped entirely
      (disposition (a) per the three-way rule — the spec's invariant
      is fully captured by the slice template close-out section + the
      SKILL.md reconciliation gate + the Constraints-section pointer +
      the status board Notes column; CLAUDE.md adds nothing the next
      contributor can't derive). Active-specs section now reads
      `_(none currently in flight)_` with a pointer to the status
      board. **Dogfood verdict: the rule produces sensible behavior
      on its own surface.** The compressed CLAUDE.md is the
      authoritative answer to "what does the rule prescribe for a
      spec whose only contribution is the rule itself?" — drop the
      entry; the rule lives where the work happens.

**Anti-horizontal-phasing check:** A future contributor opening
CLAUDE.md sees only active work + load-bearing invariants, not
implementation history. The slice template's close-out checklist
mechanically enforces compression on next close-out. End-to-end
observable; one slice; no shimmy.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Canonical term picked at implementation time (Terminology Q4
   declined-to-ask in clarify pass).** Three variants appeared in
   draft: "compress-on-close-out", "compress on close-out",
   "CLAUDE.md hygiene". Implementer chose **"CLAUDE.md hygiene"**
   as the **gate name** (for the reconciliation-checklist bullet
   and the slice-template close-out reference); **"compress"** as
   the **verb** in the rule body; and left "compress-on-close-out"
   as the spec's umbrella concept in the overview. Three-tier
   vocabulary captures three audiences (reviewer at the gate,
   slice author at the close-out checkbox, future contributor
   reading the spec). The Terminology category in the
   Clarifications coverage table accordingly stays Partial.

2. **Skills table: `/jig:vision-elicitation` was missing from
   pre-sweep CLAUDE.md** — discovered mid-implementation by
   cross-checking against `_TIER_SKILLS` in
   `skills/scaffold-init/scaffold.py`. The original CLAUDE.md
   never carried a vision-elicitation row even though the skill
   has been active since spec 017-02. Added in this slice as a
   row between scaffold-init and memory-sync (the greenfield-setup
   grouping). Pre-existing gap; not introduced by this slice.

3. **AC #7 reconciliation-checklist insertion point.** AC #7
   named the position "between Inbox triage and Memory-sync."
   Implemented exactly there in
   `skills/spec-workflow/SKILL.md`. Bullet phrasing matches the
   slice's suggested wording with one addition: the `(which
   workflow.py status-board preserves across regen)`
   parenthetical, so the implementer at the gate doesn't have to
   remember that fact.

4. **Adjacent cleanup (out-of-scope-but-related).** As part of
   the same session, four `docs/refinement-todo.md` /
   `docs/inbox.md` items were triaged: (a) refinement-todo
   "Scaffold.json manifest format" RESOLVED (slice 001-01 +
   ADR-0007); (b) refinement-todo "jig-memory-scan firing-rate
   measurement" trigger window elapsed — status updated to
   "never bites in practice, re-open on noise"; (c) inbox
   2026-05-11 "Slice landing step" RESOLVED by spec 007;
   (d) inbox 2026-05-12 "Multi-persona reviewer expansion"
   option (a) RESOLVED by specs 012 + 014. Tangential to
   AC #1-#10 but matches the spec's spirit (compress accumulated
   doc debt). Scope-creep concern: if the reviewer flags it,
   splitting to a sibling `chore(docs):` commit (matching the
   `chore(tests): address four 2026-05-18 inbox quick wins`
   precedent) is the documented escape.

5. **AC #2's three-way migration rule applied with light Notes
   migration.** Per Q2's "implementer judgment" answer: only one
   slice received a new Notes column entry (009-01, `check_dod`
   close-out recognition — the fact future template editors
   need). Every other closed spec's load-bearing facts are
   either (a) covered by the new slimmed Skills table row,
   (b) covered by the existing status-board Notes column (which
   many slices already had non-empty Notes), or (c) dropped as
   derivable from the spec dir. Full enumeration in the
   "## Compression decisions" subsection below.

6. **No new ADR.** SPIDR-table prediction held — the rule
   change is codified in the slice template + SKILL.md
   reconciliation checklist, not in a new ADR. ADR threshold
   remains "hard-to-reverse architectural decision"; a process
   rule is reversible (revert the template + SKILL.md).

7. **Implementation reviewer findings folded in.** Verdict:
   **pass** with three minor SPECIFIC ISSUES and three
   RECONCILIATION NOTES.
   - SPECIFIC ISSUE #1 (line-count drift): "shrank from 112
     lines to ~84 lines (~25%)" was inaccurate — the reviewer
     measured 111 → 86 (~22%). Fixed inline in the "Net effect"
     paragraph above.
   - SPECIFIC ISSUE #2 (test claim not independently verified):
     reviewer noted the "988 pass + 3 skipped" claim is the
     implementer's only; AC #10 explicitly waives new tests, so
     the box is content-only-cleanup-tickable. Accepted as
     non-blocking; the implementer's `python3 scripts/run_tests.py`
     output is reproducible by the reconciliation reviewer if
     needed.
   - SPECIFIC ISSUE #3 (CLAUDE.md:27 entry will need
     compression at close-out): reviewer noted the irony — the
     spec-025 Active-specs entry uses inline narrative form and
     will itself need compression per AC #9. **By design** per
     Q1; flagged for awareness, not blocking.
   - RECONCILIATION NOTE: numerical fix applied above.
   - RECONCILIATION NOTE: which commit path is taken (single
     `feat(docs)` vs split `chore(docs)` per the deviation-§4
     escape hatch) will be documented in the commit message at
     land time. The default is a single `feat(docs): ` commit
     covering all of spec 025's content; if the reviewer of the
     close-out commit flags the inbox/refinement-todo
     adjacent-cleanup as scope-creep, the implementer splits.
   - RECONCILIATION NOTE: close-out commit message should call
     out that the rule's first test case is itself — the
     post-DONE self-dogfood (compressing spec 025's own
     Active-specs entry under the rule) is the load-bearing
     validation that the rule produces sensible behavior on the
     surface that motivated it.

8. **Reconciliation reviewer findings folded in.** Verdict:
   **pass** with **zero SPECIFIC ISSUES** and three
   RECONCILIATION NOTES (all minor):
   - **Cosmetic drive-bys not enumerated.** While rewriting
     CLAUDE.md I also: added blank-line separators after the
     three `###` subheadings (`Project codenames / active
     work`, `Key terms`, `Deferred decisions`); converted three
     bare-text path references to markdown links
     (`docs/conventions.md`, `templates/CLAUDE.md.template`,
     `docs/memory/glossary.md`, etc.); added a new `Key terms`
     line — `**Status board** = [docs/specs/README.md] ...`.
     These improvements were not enumerated in §1-§7 or the
     "Doc updates from this slice" bullet list. Recording here
     for traceability: drive-bys were stylistic / link-adding
     only; no semantic changes.
   - **Test count claim unverified at reconciliation either.**
     The "988 pass + 3 skipped" DoD claim was the
     implementer's; neither reviewer re-ran the suite. Per
     AC #10's "no new tests required" framing this is
     acceptable but worth noting that the test-suite claim
     hasn't been independently re-verified across either
     review pass.
   - **Mild redundancy.** The new `**Status board** = ...`
     Key-terms entry in CLAUDE.md (line 23) overlaps slightly
     with the spec-018 Constraints bullet (slice-file layout).
     Both are true; the Status-board entry frames it as a
     vocabulary term, the Constraints entry as an authoring
     rule. Non-blocking; left as-is.

## Compression decisions

Per AC #8, every closed-spec entry's disposition is enumerated
here. Three dispositions: **drop** (derivable from spec dir +
status board + Skills table), **Notes** (migrated to status
board Notes column for that slice), **constraint** (promoted to
the `## Constraints for agents` section of CLAUDE.md).

| Source entry | Disposition | Where it went |
|---|---|---|
| 001-scaffold-init: complete | drop | Skills table `/jig:scaffold-init` row covers current behavior |
| ADR-0001 (scaffold-stable) accepted | drop | `docs/decisions/` now in Key documents; ADR-0001 stays canonical there |
| ADR-0002 (contracts stays deferred) superseded by ADR-0005 | drop | ADR-0005 is canonical; supersession is in the ADR doc itself |
| ADR-0005 (contracts as judgment-skill) accepted | drop | Skills table `/jig:contracts` row mentions ADR-0005; superseded-by tracked in ADR docs |
| 002-memory-layer: complete | drop | Skills table `/jig:memory-sync` row covers behavior |
| 003-spec-workflow-promotion (003-01/03/04 DONE) | drop | Skills table row mentions `new` / `transition` auto-tick / `status-board` / `stale`; status-board Notes already detail per-slice facts |
| 004-independent-review-promotion (004-01 DONE) | drop | Skills table row covers `review.py` + `subagent-type` |
| 005-adr-workflow (005-01 DONE) | drop | Skills table row + `docs/decisions/` pointer |
| ADR-0004 (decisions-folder-naming) accepted | **constraint** | Added bullet to Constraints section: "ADRs live at `docs/decisions/adr-NNNN-<slug>.md` (per ADR-0004)" |
| 006-tdd-loop (006-01/04/05 DONE) | drop | Skills table row covers exit codes + `.jig/test-command` override |
| 007-slice-land (007-01/02/03 DONE) | drop | Skills table row covers prepare + execute modes + close-out recognition + `--no-deviation-log` |
| 008-migrate-existing-project (008-01/02/03/05 DONE) | drop | Skills table row covers subcommands |
| 009-dod-close-out-separation (009-01 DONE) | **Notes** | Status board Notes for 009-01 now reads: "`check_dod` recognizes `### Close-out (post-DONE)` subsection and excludes its checkboxes from the count; consumed by template + spec 025-01" |
| 011-plugin-self-install (011-01/02 DONE) | drop | Skills table `/jig:independent-review` row mentions `subagent-type` fallback; install runbook lives in CONTRIBUTING.md |
| 012-pr-review (012-01 DONE) | drop | Skills table row + deferral language |
| 013-release-pipeline (013-01..04 DONE) | drop | Install paths live in README + CONTRIBUTING.md |
| 016-scaffold-mode (016-01/02/03 DONE) | drop | Skills table `/jig:scaffold-init` row mentions `--plugin-only` opt-out and default-on copy behavior |
| 017-vision-elicitation (017-01/02/03 DONE) | drop | Skills table row added (was missing from original CLAUDE.md — see §2 above) |
| 018-slice-per-file (all 4 DONE) | **constraint** | Added bullet to Constraints section: "Spec slices live in sibling files: `docs/specs/NNN-<slug>/slice-NN-<short>.md` (per spec 018)" |
| 019-land-deviation-log-tolerance (019-01 DONE) | drop | Skills table `/jig:slice-land` row mentions `--no-deviation-log` |
| 020-migrate-slice-to-spec (020-01 DONE) | drop | Skills table `/jig:migrate` row mentions agentic slice-to-spec workflow |
| 021-migrate-copy-machinery (021-01 DONE) | drop | Skills table `/jig:migrate` row mentions `copy-machinery` |
| 022-contracts (022-01/02 DONE) | drop | Skills table `/jig:contracts` row covers behavior + ADR-0005 ref |
| 023-clarify (023-01 DONE) | drop | Skills table row covers six-category taxonomy + no-deferral-hint stance |
| 024-analyze (024-01 DONE) | drop | Skills table row covers finding categories + constitution-gate bundle |
| Current sprint focus (3 stanzas) | drop | Sprint-focus is not history. Only spec 025 is currently in flight, and its Active-specs one-liner above covers it. |
| "Prior context (preserved for reference)" | drop | Pure history paragraph. Belongs in git log, not hot cache. |

**Net effect:** CLAUDE.md shrank from 111 lines to 86 lines
(~22% reduction; reviewer-verified during implementation review);
Active-specs section from 25 entries to 1; Skills table rows
from ~3-30 lines each to ~1-3.

**Doc updates from this slice:**

- `CLAUDE.md` — rewritten. Active-specs 25 → 1; Skills table
  rows slimmed; `/jig:vision-elicitation` row added (was absent);
  `docs/decisions/` row added to Key documents; Sprint-focus +
  ADR stanzas + "Prior context" stanza removed; Constraints
  section gained two bullets (ADR-0004, spec 018) plus a
  pointer to the close-out compression rule.
- `templates/docs/specs/slice-template.md` — Close-out section's
  CLAUDE.md bullet reframed from "add hot-cache entry" to
  "compress / migrate / keep one-liner per spec 025-01 rule."
- `skills/spec-workflow/SKILL.md` — Reconciliation checklist
  gained a "CLAUDE.md hygiene" bullet between "Inbox triage"
  and "Memory-sync."
- `docs/specs/README.md` — status board regenerated; 009-01
  Notes column got the `check_dod` invariant per §5 above;
  spec 025 row added by regen.
- `docs/refinement-todo.md` — two items closed: "Scaffold.json
  manifest format" RESOLVED 2026-05-18; "jig-memory-scan
  firing-rate measurement" trigger updated to "never bites in
  practice."
- `docs/inbox.md` — two items struck through: 2026-05-11 slice
  landing step RESOLVED; 2026-05-12 multi-persona reviewer
  option (a) RESOLVED.
- No code changes, no test changes (988 tests still pass, 3
  skipped, no regressions).
- No new ADR (per §6).
