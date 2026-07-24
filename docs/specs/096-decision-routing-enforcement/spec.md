---
status: IN_PROGRESS
skill: memory-sync
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 096: Decision-routing enforcement

> Reserved on 2026-07-22 via `workflow.py new`.

## Overview

**The Architectural Decision Record (ADR) routing rule is stated in four places
and enforced in none.** Reported as
[#121](https://github.com/ramboz/jig/issues/121).

`decisions.py` holds `ADR_TRIGGER` as its single canonical constant
([ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md)), and
four consumer sites quote it verbatim — the routing rubric in
`lightweight-decisions.md:13`, both reconcile checklists
([docs/workflow.md:303](../../workflow.md), `spec-workflow/SKILL.md:684`), and
the memory-sync session-end prompt (`memory-sync/SKILL.md:94`).
`test_decisions.py::SingleSourceDriftTests` fails CI if any of the four drifts.
The *wording* of the rule is defended by machinery on five surfaces.

Nothing evaluates a decision against it. The helper exposes exactly one
subcommand — `add-lightweight` — and that subcommand reads `--title`,
`--decision`, `--context`, `--scope` and appends. `ADR_TRIGGER` is a string the
helper ships to a template; no line in the file reads it. The routing judgement
happens entirely in the agent's head, once, at the moment it chooses which
command to type — and the command name (`add-lightweight`) presupposes the
answer.

### What that costs, in a real case

The reported case (abstracted in #121) ran four steps:

1. An owner decision was recorded with `add-lightweight`. At the time it looked
   genuinely bounded — the cost presented to the owner was "a small piece of
   platform-native code alongside the existing library".
2. Hours later an adversarial review read the vendored library's source and
   showed the estimate was wrong: the library structurally could not do what was
   assumed, so the decision actually meant **replacing that library's whole path
   with a native implementation** — a module-boundary change that also
   force-resolved a separate architectural question the project had explicitly
   parked.
3. The owner re-affirmed the decision against the corrected cost. The existing
   entry was **edited in place, by hand**, to record the new price and the
   rejected alternatives.
4. Nothing asked "does this still belong in `lightweight-decisions.md`?" It did
   not — by then it cleared the ADR trigger comfortably.

The tell was in the entry's own text. The revised entry lists the alternatives
that were rejected and why; the rubric's criterion for a lightweight record is
*"with no real rejected alternatives"*. **The entry disqualified itself, in the
same file whose header states the rule.**

### Why it slips through — four mechanisms, not one

- **There is no revision path.** `add_lightweight` is append-or-no-op keyed on
  normalized `(date, title)`; there is no edit, no delete, no `--force`. Revising
  an entry means hand-editing markdown — outside the helper, so outside any check
  that could exist. (The same absence blocks spec 083's own OQ2, which
  anticipated adding a `**Commit:**` SHA retroactively; today that is a hand-edit
  too.)
- **There is no promotion path.** Nothing moves a lightweight record to an ADR
  and leaves a pointer behind. `adr.py` has no lightweight-record awareness at
  all, and `render_entry` emits no ADR back-reference field. Even *noticing* the
  problem leaves a manual job — manual enough to discourage doing it.
- **Calling the script directly bypasses the guidance.** The routing instruction
  lives in `SKILL.md:133-135`. An agent that invokes `decisions.py` as a plain
  CLI — exactly how the helper is documented, as a copy-pasteable command block —
  never loads that text.
- **Batching flattens judgement.** Several decisions recorded in one pass get
  uniform treatment; a single architectural outlier among four genuinely small
  ones is easy to miss.

Together these make a recorded entry **immutable by omission**: every surface
tells the agent never to hand-write the file (`SKILL.md:129-131`,
`decision_scan.py:365`), and the helper offers no other way to change one.

### A correction to #121's own plan

#121 closes with: *"Fix 1 alone would have caught this case at step 3."* Probed
against the code, **it would not.** Step 3 was a hand-edit that never called the
helper; and had it instead re-run `add-lightweight` with the same title and date,
`add_lightweight` would have returned `False` at the idempotency no-op
(`decisions.py:272-273`) before any check could fire. A first-write check catches
*future* misfilings; it cannot see a revision that never reaches it.

So the reported case closes only when **096-01 and 096-02 are both in**: the
evaluator, plus a revision path for it to run on. This spec keeps them as
separate slices — 096-01 is independently valuable and 096-02 reuses its
evaluator — but states the dependency plainly rather than shipping 096-01 and
declaring #121 fixed.

## Assumptions

None unverified. Each claim above was probed on this worktree at `fd7115a`:

- `add-lightweight` is the helper's only subcommand — `decisions.py:313-332`
  (`_build_parser`), one `sub.add_parser` call; confirmed by `--help`.
- `ADR_TRIGGER` is rendered, never evaluated — defined at `decisions.py:41-45`;
  no other line in the file reads it. `test_decisions.py:378-402`
  (`SingleSourceDriftTests`) asserts it is *present* at four sites; nothing
  asserts it is *applied*.
- A same-title/same-date re-record is a silent no-op — `decisions.py:272-273`.
- No update / promote / lint machinery exists for decision records. `adr.py`
  exposes `new / accept / supersede / index / resolve-todo` only (probed via
  `--help`); `memory.py promote` promotes a glossary *term*, not a decision;
  `scripts/spec_lint.py` is spec-only and has no decision awareness.
- jig's load-bearing-decision routing is already judgement-prompted prose, not a
  matcher — `docs/workflow.md:303`, `spec-workflow/SKILL.md:684`,
  `memory-sync/SKILL.md:94` each quote `ADR_TRIGGER` in a prompt. The chosen
  approach (ADR-0039) extends that existing pattern rather than adding a new
  gate mechanism.
- jig's own `lightweight-decisions.md` holds **zero real entries** — the single
  `### ` entry at `:55` is a self-described illustrative worked example (`:51-53`),
  and a second `### ` heading lives inside the `## Template` fence. Both are
  load-bearing for 096-04: a lint that flags either one is broken on the only
  corpus jig ships.

## Decomposition

SPIDR analysis. **The mechanism is the maintainer's call, recorded in
[ADR-0039](../../decisions/adr-0039-decision-routing-gate.md): route by
skill-prompted judgement at revision, not a lexical write-gate.** A keyword
matcher on the write path is brittle (the project has seen the pattern fail
repeatedly) and gates the wrong moment — first write, when the reported failure
is at revision. So the judgement lives in memory-sync's `SKILL.md` prose, made by
the model already reading the decision; pattern-matching survives only in the
low-stakes advisory lint.

- **Spike:** none left. The one-time unknown — *can a lexical rule route
  reliably?* — was answered **no** by building it: even a rubric-derived
  two-signal rule refused an ordinary "user interface" copy decision until
  narrowed, which is the brittleness ADR-0039 cites. The judgement approach
  removes the unknown by not depending on a matcher.
- **Paths:** four moments in a record's life, and they are the slice boundaries —
  *first write* (`add-lightweight`, already exists), *revision* (no path today),
  *correction* (no path today), and *sweep over what is already on disk* (no path
  today). Each fails independently.
- **Interfaces:** two new subcommands (`update`, `promote`), one advisory
  subcommand (`lint`), and prose guidance in `SKILL.md`. **No write-time gate and
  no `--confirm-lightweight` flag** — that was the rejected mechanism. No change
  to `add-lightweight`'s existing arguments, so every documented command block
  keeps working unchanged.
- **Data:** one file, `lightweight-decisions.md`, in its existing format. No new
  artifact and no schema change beyond the one back-reference `promote` leaves
  behind — `promote` writes its ADR through `adr.py new` rather than inventing a
  second ADR writer.
- **Rules:** the routing criterion stays single-sourced as `ADR_TRIGGER`
  (ADR-0031). The judgement guidance (096-01) quotes it, joining the surfaces
  `SingleSourceDriftTests` covers; the advisory lint (096-04) reuses a lexical
  evaluator derived from it. There is exactly one evaluator, so the lint cannot
  drift from the rule it approximates.

→ **Four slices.** 096-02 (the revision path) plus 096-01 (the judgement that runs
on it) together close the reported case; 096-03 makes the correction one command;
096-04 surfaces what is already misfiled. Build order is dependency-first —
`update` and `promote` are the code the guidance names, so they land before the
`SKILL.md` prose that references them.

## Slices

- [096-01 — routing-judgment-guidance](slice-01-routing-check-on-add.md) —
  `SKILL.md` guidance so the assistant evaluates a lightweight decision against
  `ADR_TRIGGER` when updating (or recording) it, and routes to `promote` when it
  clears the trigger. Replaces the rejected write-gate (ADR-0039).
- [096-02 — update-subcommand](slice-02-update-subcommand.md) — give revision a
  code path at all, so the judgement guidance has a command to attach to.
- [096-03 — promote-subcommand](slice-03-promote-subcommand.md) — move an entry
  to an ADR via `adr.py new` and leave a forward-linking stub behind.
- [096-04 — lint-subcommand](slice-04-lint-subcommand.md) — read-only, advisory
  sweep flagging already-recorded entries whose text reads as ADR-worthy; the one
  home for the lexical evaluator.

## Out of scope

- **Widening or re-tuning `ADR_TRIGGER` itself.** The rule is good and is not the
  problem — #121 says so explicitly. This spec enforces the existing sentence;
  changing it would need its own ADR superseding
  [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md).
- **The unguarded fifth trigger site.** `templates/docs/decisions/lightweight-decisions.md.template:15`
  carries the trigger sentence but is *not* in `SingleSourceDriftTests`' assertion
  set, so a template-only reword ships green and every newly scaffolded project
  gets a drifted rubric. Real, adjacent, and a different defect from this one —
  filed separately rather than fixed as a drive-by.
- **The Tier-2/Tier-3 conversation-scan marker regexes**
  (`hooks/scripts/lib/decision_scan.py:39-53`). That is the open frame question in
  [#108](https://github.com/ramboz/jig/issues/108), parked by
  [spec 094](../094-capture-hygiene/spec.md), and unrelated to routing a decision
  the agent has already chosen to record.
- **Bug 011 / the dedup fix class.** Deliberately deferred; see
  [bug 011](../../bugs/011-decision-dedup-suppresses-reversals.md).
- **A lexical write-gate on `add-lightweight`.** Built first, then removed on the
  maintainer's steer (ADR-0039, Option A). Keyword-matching on a write path is
  brittle and the project distrusts it; the judgement moves to `SKILL.md` prose
  and the markers survive only in the advisory lint.
- **Auto-promoting on a hit.** Nothing rewrites an owner's record unasked.
  Promotion stays an explicit 096-03 call; the lint reports, the guidance
  recommends, the operator decides.
- **Retro-promoting existing entries.** 096-04 reports; acting on its report is an
  operator decision, one `promote` call at a time.
