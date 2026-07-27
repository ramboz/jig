---
status: DONE
skill: memory-sync
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 100: Decision-routing enforcement

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

So closing the reported case needs **both** a compliant revision path and a
trigger that fires on it: 100-02's `update` and 100-03's `promote` supply the
path, and 100-01's guidance supplies the judgement that routes onto it. Neither
half is sufficient alone — stated plainly rather than shipping one and declaring
#121 fixed.

_(Corrected after the reframe: this paragraph previously described 100-01 as
shipping "the evaluator" that 100-02 would reuse. That was the rejected
write-gate design; per [ADR-0042](../../decisions/adr-0042-decision-routing-gate.md)
100-01 ships prose guidance and the lexical evaluator survives only inside
100-04's advisory lint.)_

## Assumptions

**One load-bearing assumption is UNVERIFIED**, and it is the one the chosen
mechanism rests on: *the routing guidance is in the acting agent's context at the
moment a recorded lightweight entry is revised.* Named, with its counter-evidence
(four `ADR_TRIGGER` judgement prompts predate #121 and did not fire; ADR-0031
explicitly declines to claim a prompt lifts attention), in
[ADR-0042 § Assumptions](../../decisions/adr-0042-decision-routing-gate.md).
That is why the guidance landed on memory-sync's always-loaded **skill
description** and both reconcile checklists, not the skill body alone. It is not
claimed to be enforcement.

The remaining claims are code facts, each probed on this worktree at `fd7115a`:

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
  approach (ADR-0042) extends that existing pattern rather than adding a new
  gate mechanism.
- jig's own `lightweight-decisions.md` holds **zero real entries** — the single
  `### ` entry at `:55` is a self-described illustrative worked example (`:51-53`),
  and a second `### ` heading lives inside the `## Template` fence. Both are
  load-bearing for 100-04: a lint that flags either one is broken on the only
  corpus jig ships.

## Decomposition

SPIDR analysis. **The mechanism is the maintainer's call, recorded in
[ADR-0042](../../decisions/adr-0042-decision-routing-gate.md): route by
skill-prompted judgement at revision, not a lexical write-gate.** A keyword
matcher on the write path is brittle (the project has seen the pattern fail
repeatedly) and gates the wrong moment — first write, when the reported failure
is at revision. So the judgement lives in memory-sync's `SKILL.md` prose, made by
the model already reading the decision; pattern-matching survives only in the
low-stakes advisory lint.

- **Spike:** none left. The one-time unknown — *can a lexical rule route
  reliably?* — was answered **no** by building it: even a rubric-derived
  two-signal rule refused an ordinary "user interface" copy decision until
  narrowed, which is the brittleness ADR-0042 cites. The judgement approach
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
  (ADR-0031). The judgement guidance (100-01) quotes it, joining the surfaces
  `SingleSourceDriftTests` covers; the advisory lint (100-04) reuses a lexical
  evaluator derived from it. There is exactly one evaluator, so the lint cannot
  drift from the rule it approximates.

→ **Four slices.** 100-02 (the revision path) plus 100-01 (the judgement that runs
on it) together close the reported case; 100-03 makes the correction one command;
100-04 surfaces what is already misfiled. Build order is dependency-first —
`update` and `promote` are the code the guidance names, so they land before the
`SKILL.md` prose that references them.

## Slices

- [100-01 — routing-judgment-guidance](slice-01-routing-check-on-add.md) —
  `SKILL.md` guidance so the assistant evaluates a lightweight decision against
  `ADR_TRIGGER` when updating (or recording) it, and routes to `promote` when it
  clears the trigger. Replaces the rejected write-gate (ADR-0042).
- [100-02 — update-subcommand](slice-02-update-subcommand.md) — give revision a
  code path at all, so the judgement guidance has a command to attach to.
- [100-03 — promote-subcommand](slice-03-promote-subcommand.md) — move an entry
  to an ADR via `adr.py new` and leave a forward-linking stub behind.
- [100-04 — lint-subcommand](slice-04-lint-subcommand.md) — read-only, advisory
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
  maintainer's steer (ADR-0042, Option A). Keyword-matching on a write path is
  brittle and the project distrusts it; the judgement moves to `SKILL.md` prose
  and the markers survive only in the advisory lint.
- **Auto-promoting on a hit.** Nothing rewrites an owner's record unasked.
  Promotion stays an explicit 100-03 call; the lint reports, the guidance
  recommends, the operator decides.
- **Retro-promoting existing entries.** 100-04 reports; acting on its report is an
  operator decision, one `promote` call at a time.

## Reconciliation sweep

| Artifact | Disposition | Why |
|---|---|---|
| [ADR-0042](../../decisions/adr-0042-decision-routing-gate.md) | **rewrite → accept** | Authored for the lexical write-gate, rewritten to record the maintainer's pick (judgement at revision; markers advisory-only). Accepted at close. |
| `skills/memory-sync/SKILL.md` — **frontmatter `description:`** | **rewrite** | The load-bearing one. The always-loaded surface now covers *revising / updating / correcting / re-pricing* an already-recorded decision and names promotion as the remedy. The first implementation put the guidance in the skill **body** only; the frame-critique pass showed the body may never load on the trajectory #121 describes (a revision during a review session, not a memory-sync run), and the maintainer's ask was literally "a better skill description". |
| `skills/memory-sync/SKILL.md` — body | **rewrite** | The full revision-time routing guidance the description points into (100-01). |
| `docs/workflow.md` | **rewrite** | Reconcile checklist gains the revision clause, beside the `ADR_TRIGGER` quote it already carried — so a spec session carries the trigger too, not just a memory-sync run. |
| `skills/spec-workflow/SKILL.md` | **rewrite** | The skill-side copy of that same checklist; fixing only `workflow.md` would leave the two out of step. |
| `evals/cases/memory-sync.json` | **rewrite** | Two routing cases guarding the new description trigger ("update that decision we recorded…", "revise the lightweight decision entry…"). Full eval stays green: 64/64 positive, 44/44 negative; the adr-workflow × memory-sync collision moves 0.21 → 0.24, far under the 0.50 warn threshold. |
| `skills/memory-sync/decisions.py` | **rewrite** | Three new subcommands; the write-gate built in the first pass was removed on the reframe. |
| `skills/memory-sync/test_decisions.py` | **rewrite** | 51 → 158 tests. Gate-CLI tests deleted with the gate; structural guards added for the ADR-0042 boundary and the self-containment rule (previously prose-only). |
| `docs/decisions/lightweight-decisions.md` | **no-op** | The rubric is unchanged — this spec enforces the existing rule, it does not restate it. jig's own file still holds zero real entries. |
| `templates/docs/decisions/lightweight-decisions.md.template` | **no-op (knowing)** | The scaffold seed's helper block still shows only `add-lightweight`. Adding `update`/`promote`/`lint` there widens what every newly scaffolded project is told about, which is a scaffold-output change; deliberately out of this spec's scope and inboxed instead. |
| `hosts/claude/**`, `hosts/codex/**` | **regenerate** | Mirrors of `SKILL.md` + `decisions.py`; rebuilt via `scripts/build_host_packages.py`, never hand-edited. |
| `docs/conventions.md` | **no-op** | Untouched by design — needs explicit human approval, and nothing here is a convention change. |
| `docs/memory/glossary.md` | **new** | **advisory lint** — the distinction between an advisory signal and a gate is the whole point of ADR-0042 and is not obvious from the command name. Carries the don't-re-wire-it warning and the false-negative weakness. |
| `docs/inbox.md` | **new** (3 entries) | Follow-ups surfaced by review, out of scope here — see below. |
| `docs/specs/README.md` | **regenerate + annotate** | Board regenerated (280 slices / 95 specs); the four 096 rows carry the load-bearing invariants in the Notes column — most importantly **PARKED: don't re-propose the lexical write-gate**, which otherwise lived only inside a slice deviation log that nothing loads by default. Notes verified to survive a re-run. |
| `CLAUDE.md` | **no-op** | Spec closes in one pass; per spec 025-01 no Active-specs entry is grown, and the primer is at its line budget (spec 076-01). The invariants live in the status-board Notes column and the glossary, which is the on-demand home the primer indexes into. |

**Inboxed follow-ups** (found by review, deliberately not fixed here):

1. **`adr.py`'s print contract is unguarded.** `promote` now resolves the created
   ADR by filename (`adr-NNNN-<slug>.md`) rather than by parsing stdout, which
   removes the fragile coupling — but nothing on the adr-workflow side pins that
   filename shape. A drift test belongs there.
2. **`promote` under `layout.docs_root: "."`** has no test, unlike `lint` and
   `add-lightweight`. The path resolves through `project_layout.decisions_dir`
   exactly as the covered helpers do, so this is a coverage gap, not a known
   defect.
3. **The scaffold template's helper block** documents only `add-lightweight`.
   Whether newly scaffolded projects should be told about the other three
   subcommands is a scaffold-output question, not a helper question.

**Not swept, deliberately:** the unguarded fifth `ADR_TRIGGER` site in
`templates/…lightweight-decisions.md.template` (already listed under Out of
scope, and filed separately as its own task), and the Tier-2/3 conversation-scan
markers parked by [#108](https://github.com/ramboz/jig/issues/108).
