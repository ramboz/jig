---
status: DRAFT
dependencies: [122-01, 122-02]
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

## Slice 129-02 — three-rounds-then-a-person

**Goal:** when any review pass on a slice is still not passing on its third
round, jig stops the slice for a person with the same STOP notice, inbox entry
and `blocked_by:` treatment an arch escalation gets, instead of letting the
agent keep re-running it.

**Decision:** spec 122 D2 ("No new lifecycle state, no new command") and D3
(carry-over stays arch-only), extended to a round count; ADR-0014 §2 gains one
optional record field. See spec 129, "Which decision each slice extends".

**DoR:**
- ✅ 122-01's surfaces exist: the `STOP` notice in `record_review`
  (`skills/independent-review/review.py:2082-2091`), the shared "a person
  decides" message `escalation_guidance`
  (`skills/_common/review_evidence.py:551`), and the gate diagnostic that uses
  it (`review_evidence.py:697-707`).
- ✅ `record_review` overwrites in place (ADR-0014 §4) after building the
  frontmatter (`review.py:2064-2081`), so it can read the previous record for
  the same `(slice, pass)` before writing.
- ⬜ The owner says whether the new `round:` field wants an ADR-0014
  `## Amendments` note. Spec 096-05 added `substrate:` without one; bug 039
  added `review_reopened_at` with one. Either way the clearing rule (§3) is
  untouched. Amending a record needs explicit owner approval (spec 102).

**Acceptance Criteria:**

1. **`record-review` counts rounds.** For a slice-keyed record, the written
   frontmatter carries `round: N`. N is 1 when there is no previous record for
   that `(slice, pass)` or the previous verdict is `pass`; otherwise it is the
   previous `round` plus 1, where a previous record with no `round:` counts as
   round 1. `--adr` and `--bug` records are written exactly as today.
2. **Every third round stops.** Recording a non-`pass` verdict whose round is
   a multiple of 3 (3, 6, …), for any pass in `PASSES`
   (`review_evidence.py:68-69`), writes the record as today, exits 0, and then
   prints a `STOP` notice naming the pass, the round, the record's path, and
   the two follow-ups: one `memory.py add-inbox` entry, and `blocked_by:` with
   a `**Blocked:**` line on the slice. Any other recording prints only what it
   prints today.
3. **The gate says a person decides.** When a required record is non-`pass`
   and its round is a multiple of 3, `validate_evidence` (so `check-reviews`
   and `workflow.py transition`) still refuses, but its diagnostic says a
   person decides — the `escalation_guidance` wording — instead of "re-run the
   review". Clearing is still `verdict: pass` alone (ADR-0014 §3).
4. **Escalations keep their notice.** An arch record with `[blocker]
   ESCALATE:` entries keeps 122-01's notice and diagnostic at any round. When
   an escalation and the round cap apply to the same recording, one `STOP`
   notice names both reasons.
5. **Inside spec 122's D2 and D3.** No new lifecycle state, command or flag.
   The compliance, craft, code-health, design-review, reconciliation and
   frame-critique prompts are byte-identical to today's. The arch prompt's
   round line (122-02) is unchanged; if the reviewer's `round:` line in
   `REASONING` disagrees with the frontmatter, the frontmatter decides the
   stop.
6. **Docs.** spec-workflow SKILL.md "Recovering from a failed review"
   (`skills/spec-workflow/SKILL.md:635`), independent-review SKILL.md's
   recording section, `docs/workflow.md` and
   `templates/docs/workflow.md.template` say: three rounds, then a person; to
   resume, a person decides, `blocked_by:` is cleared, and the next three
   rounds run before the next stop. Host packages are rebuilt.

**Edge cases to cover explicitly:**
- `fail`, `needs-changes`, `fail` on one pass → round 3 → stop.
- `fail`, `pass`, `fail` → round 1 after the `pass`; no stop.
- A `pass` at round 3 → clears; no notice.
- A previous record hand-deleted → the count restarts at 1 (accepted; the
  count lives in the record, which git history keeps).
- A reopened slice (bug 039 back-edge) whose last verdict was `pass` → round 1.
- Rounds are counted per pass: craft at round 3 does not stop compliance.

### Behavioral rules (optional)

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | `record-review` | Orchestrator | Non-`pass`, round 1–2 (or 4–5 …) | Recorded; today's output | Normal fix-and-re-run loop | 1, 2 |
| BR-2 | `record-review` | Orchestrator | Non-`pass`, round a multiple of 3 | Recorded; `STOP` notice | "Still failing after three rounds … brings in a human" | 2 |
| BR-3 | `transition → REVIEWED` | Orchestrator | Required record non-`pass` at round a multiple of 3 | Refused; "a person decides" | Point at the person, not another re-run | 3 |
| BR-4 | `record-review` | Orchestrator | `pass` at any round | Clears; counter resets next time | Only `pass` clears (ADR-0014 §3) | 1, 3 |

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
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the
      spec).

**Anti-horizontal-phasing check:** after this slice, an unattended run that
records a third failing craft (or compliance, or any other) verdict on a slice
gets a `STOP` notice and a gate message that sends the slice to a person,
without any new tooling on the user's side.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO: likely `updated` — the record's new field._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO: "Warn when an escalated arch record is overwritten" — trigger unchanged._ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
