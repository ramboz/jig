---
status: READY_FOR_IMPLEMENTATION
dependencies: [096-02, 096-03]
last_verified: 2026-07-24
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-01 — routing-judgment-guidance

**Goal:** memory-sync's `SKILL.md` tells the assistant, in prose, that **when it
updates (or records) a lightweight decision it first evaluates the decision
against `ADR_TRIGGER` and, if it clears the trigger, promotes it to an
Architectural Decision Record (ADR) with `decisions.py promote` instead of
filing it as lightweight.** This is the routing enforcement — judgement by the
model already reading the decision, not a keyword matcher on the write path
([ADR-0039](../../decisions/adr-0039-decision-routing-gate.md), Option B).

Why guidance and not a code gate: the maintainer's call on
[#121](https://github.com/ramboz/jig/issues/121). A lexical write-gate is brittle
(the project has seen the pattern fail repeatedly) and gates first-write, when
the reported failure is at revision. See ADR-0039.

Depends on **096-02 and 096-03** because the guidance names their commands
(`update`, `promote`); prose that points at commands which do not exist yet would
ship stale. This slice lands last of the four.

**DoR:**
- ✅ [ADR-0039](../../decisions/adr-0039-decision-routing-gate.md) records the
  chosen approach and the rejected write-gate.
- ✅ `ADR_TRIGGER` is single-sourced (`decisions.py:41-45`) and already quoted at
  four judgement surfaces; this adds a fifth of the same kind.
- ✅ `memory-sync/SKILL.md` already carries a "Load-bearing decision escape hatch"
  block (~`:87-94`, spec 083-06) quoting `ADR_TRIGGER` — the natural anchor to
  extend, not a greenfield section.
- ✅ 096-02 (`update`) and 096-03 (`promote`) are DONE, so the guidance names
  real commands.

**Acceptance Criteria:**

1. **The guidance exists at the update moment.** `memory-sync/SKILL.md` states
   that before revising a recorded lightweight decision, the assistant
   re-evaluates it against the ADR trigger, because a decision's weight can change
   after it was first filed — naming #121's failure mode in one line so the
   *why* travels with the instruction.
2. **It routes a cleared decision to `promote`.** The guidance says: if the
   updated decision now clears `ADR_TRIGGER`, use `decisions.py promote --title
   …` rather than `update`, so the record moves to an ADR and leaves a
   forward-linking stub. The command it names must be the real one 096-03 ships.
3. **It is bound to the canonical `ADR_TRIGGER`, and the binding is tested.**
   The guidance judges against the trigger sentence single-sourced from
   ADR-0031, and a test fails if that linkage is broken.

   **Amended during implementation** (see deviation log). As written this AC
   asked for a *second* verbatim copy of the sentence in `SKILL.md`, asserted as
   a "fifth site" by `SingleSourceDriftTests`. That is unimplementable as
   stated: `_assert_contains_trigger` is a whole-file `assertIn`, and this file
   is *already* one of the four asserted sites — so a second copy would be
   pinned by a test that passes on the **old** copy regardless of what the new
   guidance said. Worse, two copies in one file is weaker single-sourcing, not
   stronger.

   Implemented instead: the guidance **references** the one verbatim quote
   already in this file ("the canonical ADR trigger quoted above"), and
   `UpdateTimeRoutingGuidanceTests` pins what actually carries risk — that the
   revision-time section exists, that it points at the trigger *and* that the
   trigger is still in this file (so the reference resolves), that it routes to
   `promote` and `update`, that it names the lint as advisory, and that it keeps
   the meaning-not-vocabulary caveat. Verified to fail on drift by mutating the
   prose.
4. **Record-time gets a lighter reminder.** The `add-lightweight` guidance block
   notes that if a decision already clears the trigger *when first recorded*, it
   belongs in an ADR (`adr.py new`) from the start — the pre-existing routing
   advice, kept, now sitting beside the sharper update-time rule.
5. **No code gate, no `--confirm-lightweight`.** `add-lightweight` and `update`
   refuse nothing on routing grounds and carry no routing flag — the enforcement
   is the guidance plus the advisory lint, per ADR-0039. (This AC is a guard: a
   later reviewer must not "add the missing gate".)
6. **The host mirrors carry the same text.** After `scripts/build_host_packages.py`,
   `hosts/claude/skills/memory-sync/SKILL.md` and the Codex mirror hold the
   identical guidance — the drift test already covers the `skills/` source; the
   host copies are regenerated, not hand-edited.

**Edge cases covered explicitly:**

- The guidance must not tell the assistant to hand-edit `lightweight-decisions.md`
  — it routes through `update` / `promote`, consistent with every other surface
  that forbids hand-editing the file (`SKILL.md:129-131`).
- The wording distinguishes the two homes the way the rubric does: *clears the
  trigger* → ADR; *settled, local, bounded, no real rejected alternatives* →
  stays lightweight. It must not imply that any rejected-alternative mention
  forces an ADR (that is the Option-A over-fire ADR-0039 rejects).

**Anti-horizontal-phasing check:** with 096-02, 096-03, and this slice in, an
assistant revising a decision that has grown load-bearing is told — at the moment
it revises — to promote it, and has the command to do so. The judgement, the
trigger, and the mechanism are all present end-to-end.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [ ] `SingleSourceDriftTests` extended to the new guidance site and asserted
      to fail if the quoted trigger is altered.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] Host packages regenerated (`scripts/build_host_packages.py`) — SKILL.md is
      mirrored into `hosts/claude/` and `hosts/codex/`.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.
