---
status: IN_PROGRESS
dependencies: []
last_verified: 2026-11-17
kind: feature
arch_review: true
claimed_by: claude/arch-pass-escalate-rounds
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

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the spec).

**Anti-horizontal-phasing check:** after this slice, an arch reviewer that
escalates a decision makes an autonomous run stop on that slice with the
decision waiting in `docs/inbox.md`, instead of the agent deciding it.
