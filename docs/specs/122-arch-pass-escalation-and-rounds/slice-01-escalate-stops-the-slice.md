---
status: DONE
dependencies: []
last_verified: 2026-11-18
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

## Slice 122-01 — escalate-stops-the-slice

**Goal:** when an arch-pass verdict carries a `[blocker]` entry starting with
`ESCALATE:`, the orchestrator stops work on that slice and parks the decision
and its options in `docs/inbox.md` for a person, instead of trying to fix it.

**Decision:** spec 122 D2 — reuse `memory.py add-inbox` and the `blocked_by:`
annotation ([ADR-0057](../../decisions/adr-0057-first-class-blockers-are-annotations.md));
jig's code adds one shared parser and two signals.

**DoR:**
- ✅ `record-review` always stores the envelope body (spec A1).
- ✅ `memory.py add-inbox <text> <target>` appends a dated, locked bullet to
  `<docs>/inbox.md` (`skills/memory-sync/memory.py`, `add_inbox`).
- ✅ `blocked_by:` + `**Blocked:**` is the slice-level "stuck on X" annotation
  and changes no transition (spec A2).

**Assumptions:** None beyond spec A1–A3.

**Acceptance Criteria:**

1. **One shared parser.** `_common/review_evidence.py` exposes
   `escalations(text) -> list[str]`, returning (in order) the decision text
   after `ESCALATE:` for every `SPECIFIC ISSUES` entry tagged `[blocker]` whose
   description starts with `ESCALATE:` — either right after the tags or after an
   anchor and a ` — ` / ` - ` separator. It ignores `[nit]` / `[strength]`
   entries, text outside the `SPECIFIC ISSUES` section (e.g. `RECONCILIATION
   NOTES`), and code-fence lines; it joins indented continuation lines onto
   their entry; it returns `[]` when there is no `SPECIFIC ISSUES` section.
2. **The gate says a person decides.** When the recorded arch verdict is not
   `pass` and its body has at least one escalation, `validate_evidence` (so
   `check-reviews` and `workflow.py transition`) still refuses, and the arch
   diagnostic names each escalated decision and says not to fix or re-run it
   but to park it in the inbox and mark the slice `blocked_by:` — instead of
   "re-run the review and re-record a 'pass'". Every other pass, and an arch
   record with no escalation, keeps today's diagnostic text.
3. **`record-review` prints a stop notice.** Recording `--pass arch` with a
   non-`pass` verdict whose body has escalations writes the record exactly as
   today and exits `0`, then prints a `STOP` notice listing each escalated
   decision and the two follow-ups (inbox entry, `blocked_by:`). Any other
   recording prints only today's `recorded …` line.
4. **The arch prompt states the format.** `review.py arch-review` tells the
   reviewer that a decision only a person can make (a duplicated path, effort
   past plan, a slice tied to no goal line, a hard-to-reverse choice) is
   reported as `VERDICT: fail` with an entry
   `- [blocker][spec] <anchor> — ESCALATE: <decision> (options: A, B)`, and is
   not something the implementer fixes.
5. **The recovery docs cover the case.** `spec-workflow/SKILL.md` ("Recovering
   from a failed review") and `independent-review/SKILL.md` (arch pass +
   recording) describe the escalated case: record the verdict as returned; do
   not fix it or re-run the pass; one `memory.py add-inbox` entry per decision
   with its options and the record's path; set `blocked_by:` and a
   `**Blocked:**` line on the slice; stop work on that slice. Resuming: a person
   decides and records the decision, clears `blocked_by:`, and the arch pass is
   re-run.

**Edge cases to cover explicitly:**
- `[blocker][spec] path:12 — ESCALATE: …` and `[blocker] ESCALATE: …` both parse.
- `[nit] … ESCALATE: …` and an `ESCALATE:` line under `RECONCILIATION NOTES` do
  not parse.
- An entry whose `ESCALATE:` is mid-sentence (not the description's start) does
  not parse.
- An escalation recorded with `verdict: pass` is not acted on (the gate clears
  `pass`; the notice does not fire).
- The envelope wrapped in a ```` ``` ```` fence parses the same as unwrapped.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [x] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the spec).

**Anti-horizontal-phasing check:** after this slice, an arch reviewer that
escalates a decision makes an autonomous run stop on that slice with the
decision waiting in `docs/inbox.md`, instead of the agent deciding it.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

1. **Acts on any non-`pass` arch verdict, not only `fail`.** The spec overview
   frames escalation as `VERDICT: fail`, and the prompt asks for `fail`. The
   gate diagnostic and the `STOP` notice fire for any well-formed non-`pass`
   arch record with an escalation (so `needs-changes` too), as AC2/AC3 word it.
   Deliberate and fail-safe: a person's decision never goes back to the fix
   loop because the reviewer picked the other non-`pass` word. Tested on both
   sides (`EscalationGateDiagnosticTests`, `ArchEscalationRecordNoticeTests`).
2. **Parser wider than AC1.** The first version already accepted
   `## SPECIFIC ISSUES` headings (ADR-0014 §2's example) and an en-dash
   separator. All three review passes then returned `pass`, and the
   compliance and craft reviewers noted record shapes it still missed, some
   already seen in this repo's records. Added after those verdicts and before
   recording them (spec-workflow's "address findings, then record" order; not
   re-reviewed, so the recorded bodies cite the earlier line numbers):
   annotated or bold headings (`SPECIFIC ISSUES (round 2):`,
   `**SPECIFIC ISSUES:**`), an empty anchor (`[blocker] — ESCALATE:`), and a
   bold or lowercase token (`**ESCALATE:**`, `Escalate:`). A missed escalation
   would fall back to "re-run the review" — the failure this slice exists to
   prevent — so the parse leans lenient (spec A3). Also beyond AC1 and
   fail-safe: an `ESCALATE:` entry with no decision text still counts, listed
   as "(decision text missing)".
3. **Code fences are neutral.** Fence lines are skipped and never start or
   end a section. Two stricter rules were tried during review and both dropped
   escalations: ending the section on any fence lost an escalation after a code
   snippet (third reconciliation review), and ending it on the close of a
   wrapping fence lost one after a snippet inside a wrapped envelope (fourth
   reconciliation review). Telling a wrapping fence from a snippet fence is
   guesswork, so the parser does not try: the only cost is that a `[blocker]
   ESCALATE:` bullet written after a wrapped envelope with no `RECONCILIATION
   NOTES` would also be read, which errs toward stopping. The skip keeps fence
   markers out of an entry's decision text
   (`test_fence_lines_stay_out_of_the_decision_text` goes red without it,
   mutation-checked); `test_fence_inside_the_section_keeps_later_escalations`
   and `test_wrapped_envelope_with_inner_snippet_keeps_escalations` pin the
   two cases that broke the stricter rules.
4. **`VerdictRecord.well_formed` instead of string matching.** The first
   version told a well-formed non-`pass` record from a malformed one by
   comparing `problems` with a rebuilt message string (craft and arch nit).
   `parse_verdict_file` now sets a `well_formed` flag; `escalated_decisions`
   reads it. `clears` is computed exactly as before.
5. **Prompt says `<anchor>`, not `<file:line>`.** Spec-level escalations (no
   goal line, effort past plan) have no natural `file:line`; the arch prompt
   and spec-workflow SKILL.md now say `<anchor>` — "a file:line or the spec
   line the decision rests on" — matching AC4.
6. **Guard tests that passed before the feature.** Six tests were green before
   the implementation because they pin unchanged behaviour:
   `test_other_recordings_print_only_the_recorded_line` (no notice for craft,
   for `pass`, or without an escalation), `test_craft_prompt_does_not_offer_escalation`,
   and four `EscalationGateDiagnosticTests` guards —
   `test_arch_fail_without_escalation_keeps_todays_diagnostic`,
   `test_escalation_in_a_pass_record_clears`,
   `test_craft_escalation_keeps_todays_diagnostic` and
   `test_malformed_escalated_record_keeps_generic_diagnostics`. They fail if the
   notice, the prompt section or the "a person must decide" diagnostic stops
   being limited to well-formed, non-`pass` arch records that carry an
   escalation. The tests that assert the new behaviour were red before the
   implementation.
7. **No end-to-end `transition` test.** AC2 is covered through
   `validate_evidence`; `check-reviews` and `workflow.py transition` print its
   diagnostics unchanged (`workflow.py` gate path), so no new CLI fixture was
   added.
8. **Verification.** Full suite (`scripts/run_tests.py`): 5,208 tests green
   (8 skipped). Its pyright gate then flagged one error: it could not narrow
   `verdict_val` through the new `well_formed` flag. Fixed by keeping the
   explicit `verdict_val is not None` guard in `clears`; pyright is clean on
   both changed modules. An en-dash separator test and a "(decision text
   missing)" test were added after the reconciliation reviews noted the
   behaviour had none. Two craft nits were addressed after the craft verdict,
   so its recorded body predates them: the message's repeated wording
   ("escalated — N decision(s) a person must decide"), and the `needs-changes`
   case of the STOP notice, now pinned by
   `test_escalated_arch_needs_changes_also_prints_stop_notice`.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| Slice deliverables: `skills/_common/review_evidence.py` + `test_review_evidence.py`, `skills/independent-review/review.py` + `test_review.py` + `SKILL.md`, `skills/spec-workflow/SKILL.md`, this slice file | `updated` | The implementation, tests and skill docs this slice delivers; see the ACs and the deviation log above. |
| Review evidence `reviews/slice-01-{compliance,craft,arch,reconciliation}.md` | `updated` | Gate records written by `record-review`; the compliance, craft and arch bodies predate the post-review parser changes (deviation 2). |
| `README.md` | `no-op` | Front door does not describe review-pass recovery. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` (spec 122 rows). |
| `docs/product-vision.md` | `no-op` | No scope change; UC-4/UC-7 unchanged. |
| `docs/architecture.md` | `updated` | New "Arch-pass escalation (spec 122)" paragraph: the gate reads the record body for its *message* only, clearing stays `verdict: pass` (arch-review nit). Replaced the stale `review_evidence.py:523,586` / `review.py:1973` line anchors with symbol names, which this slice's insertions had shifted. |
| `docs/workflow.md` | `updated` | "Recovering from a failed review" names the escalated-arch exception (arch-review nit). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` | `no-op` | Spec still in flight; no new term worth a hot-cache line yet. |
| Scaffold template `templates/docs/workflow.md.template` | `updated` | Its "Recovering from a failed review" line now names the escalated-arch exception, so scaffolded projects match the gate and the `STOP` notice (second reconciliation review). Host copies rebuilt. Its block-rule line ("`[nit]`-tagged ones become reconciliation-log items") states no `needs-changes` rule and stays as is. |
| `docs/inbox.md` | `no-op` | No parked item is resolved by this slice. |
| `docs/refinement-todo.md` | `updated` | Deferred "warn when an escalated arch record is overwritten" with a resolution trigger (arch reviewer's open question). |
| `docs/memory/**` | `no-op` | Nothing beyond the deviation log worth a learning yet; revisit at spec close. |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR change; ADR-0014 §3 and ADR-0057 are applied, not amended. |
| Generated host packages (`hosts/**`) | `updated` | Rebuilt with `build_host_packages.py`; `--check` clean. |
| Files in `main...HEAD` from the branch base | `no-op` | Deliberate exclusion: local `main` (`35826fb`) is behind this branch's base `origin/main` (`76aa587`, 2.17.1), so a `main...HEAD` diff also lists bug 041 (including
`scripts/test_skill_routing.py`), orient, evals, `CHANGELOG.md`, plugin manifests, release-please files, `docs/inbox.md` and `docs/memory/learnings.md`. None comes from this slice; the `docs/inbox.md` and `docs/memory/**` rows above refer to this slice's own changes. Slice-02/03 files come from the draft commit. |
| `docs/specs/122-arch-pass-escalation-and-rounds/spec.md` | `updated` | Drafted with the spec; its `status:` is a mechanical rollup written by this slice's own transitions (`workflow.py` `_write_spec_rollup`). |
| Line anchors in ADR-0066 (`:24`) and spec 120 `spec.md` (`:25`) | `no-op` | Both cite `review_evidence.py:523–529,586–595`, which this slice's insertions shifted. They are accepted/closed records; ADR-0010 leaves them as written. The live copy in `docs/architecture.md` now uses symbol names. |
