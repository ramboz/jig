---
status: DONE
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
   a "fifth site" by `SingleSourceDriftTests`. Rejected on design grounds: two
   copies of a single-sourced sentence **in one file** is weaker
   single-sourcing, not stronger — it creates an intra-file drift pair where
   there was none.

   A secondary argument made in an earlier draft of this amendment — that the
   assertion was *unimplementable* because `_assert_contains_trigger` is a
   whole-file `assertIn` and would pass on the old copy — was **overstated, and
   the compliance review was right to call it**. It is a real trap for the
   obvious implementation, but `assertEqual(text.count(ADR_TRIGGER), 2)` or an
   assertion scoped to the new section would both have worked. The AC was
   changed because a second copy is the wrong design, not because it could not
   be tested.

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
- [x] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [x] The guidance→trigger binding is pinned and asserted to fail on drift.
      _(Amended with AC3: `UpdateTimeRoutingGuidanceTests`, not a fifth
      `SingleSourceDriftTests` site — see AC3 for why a second in-file copy was
      rejected. Verified by mutating the prose and watching it fail.)_
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
      _(Compliance + craft, both independent; findings addressed below.)_
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] Host packages regenerated (`scripts/build_host_packages.py`) — SKILL.md is
      mirrored into `hosts/claude/` and `hosts/codex/`.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.
      _(No deferred DECISIONS — the three deferred follow-ups are scoped work,
      not open questions, so they went to `docs/inbox.md` per the routing
      rubric: refinement-todo is for decisions with a resolution trigger.)_

### Reconciliation sweep

This slice's mechanism *is* a documentation change, so its sweep is the widest.

| Artifact | Disposition | Why |
|---|---|---|
| `skills/memory-sync/SKILL.md` — frontmatter `description:` | **rewrite** | The load-bearing surface: it is loaded every session, whereas the body may never load on the trajectory #121 describes. Now covers revising / updating / re-pricing a recorded decision and names promotion as the remedy. **Trimmed to fit the Codex host's hard 1024-character description limit** — the first expansion hit 1303 and failed 13 install-contract tests. |
| `skills/memory-sync/SKILL.md` — body | **rewrite** | The full revision-time routing guidance the description points into. |
| `docs/workflow.md` | **rewrite** | Reconcile checklist gains the revision clause beside the `ADR_TRIGGER` quote it already carried, so spec sessions carry it too. |
| `skills/spec-workflow/SKILL.md` | **rewrite** | The skill-side copy of that checklist; fixing only `workflow.md` would leave the pair out of step. |
| `evals/cases/memory-sync.json` | **rewrite** | Two routing cases guard the new description trigger. Eval stays 64/64 positive, 44/44 negative. |
| `docs/memory/glossary.md` | **new** | **advisory lint** — carries the don't-re-wire-it warning. |
| [ADR-0039](../../decisions/adr-0039-decision-routing-gate.md) | **rewrite → accept** | Rewritten to the maintainer's pick; Assumptions section now names the behavioural assumption this slice rests on as load-bearing and **unverified**, with its counter-evidence. |
| `hosts/**` | **regenerate** | Mirrors of both SKILL.md files; never hand-edited. |

See the spec-level `## Reconciliation sweep` for the full cross-slice table.

### Deviation log

The original slice text is preserved above (AC3 carries its amendment inline).
Implementation notes:

**§1 — this slice is not what it was written as.** As authored, 096-01 was a
*lexical write-gate* on `add-lightweight`: a two-signal evaluator wired to
refuse, with `--confirm-lightweight` and `JIG_DECISION_ROUTING_GATE=0` as
escapes, in jig's house gate shape. It was built, and it worked. The maintainer
then rejected the mechanism on [#121](https://github.com/ramboz/jig/issues/121):
keyword-matching is *"likely brittle… we've seen this pattern failing repeatedly
already in the project"*, and he asked instead for a better skill description so
the model judges. [ADR-0039](../../decisions/adr-0039-decision-routing-gate.md)
was rewritten to record that pick, the gate was removed, and this slice was
re-scoped to the prose guidance. See the reframe commit for the removal.

The brittleness was not hypothetical: the gate, in its tuned two-signal form,
refused *"Use 'Preferences' over 'Settings' in the user interface"* — an ordinary
UI-copy decision the rubric routes to the lightweight home **by name** — because
a bare `interface` marker sat in a group that flags with no second signal. That
was caught by probing before the reframe, and the same failure mode recurred in
the surviving advisory lint (see 096-04 §1). Two independent recurrences of the
same class is the argument for the maintainer's call, recorded here so a future
session does not re-propose the gate.

**§2 — this slice now lands LAST, not first.** It names `update` and `promote`,
so it depends on 096-02 and 096-03 rather than being their prerequisite. The
frontmatter dependency and the spec's build order were both inverted.

**§3 — AC3 was amended, and the first draft of that amendment overstated its
case.** The AC asked for a second verbatim `ADR_TRIGGER` copy in `SKILL.md`
asserted as a fifth `SingleSourceDriftTests` site. Rejected: two copies of a
single-sourced sentence in one file is weaker single-sourcing, and the obvious
implementation is untestable because `_assert_contains_trigger` is a whole-file
`assertIn` that would pass on the old copy. My first amendment said this made
the AC "unimplementable" — the compliance review correctly pointed out that
`assertEqual(text.count(ADR_TRIGGER), 2)` would have worked, so the honest
reason is *wrong design*, not *impossible*. AC3 now says so.

**§4 — enforcement is genuinely softer, and that is the accepted trade.** Prose
guidance can be skipped; an agent that shells `decisions.py` without loading
`SKILL.md` gets no prompt at all. ADR-0039 states this under Consequences and
sets a kill criterion for it. The advisory lint (096-04) is the backstop for
records the guidance never saw — not a replacement for it.
