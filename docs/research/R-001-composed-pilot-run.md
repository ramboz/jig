---
status: OPEN
topic: Composed autonomous UI pilot (jig × vellum × servo) — end-to-end run record
created: 2026-08-31
related:
  - docs/decisions/adr-0059-servo-delivered-work-design-review-gate.md
  - docs/specs/071-design-review-pass/spec.md
  - docs/specs/104-design-fidelity-routing/spec.md
  - docs/inbox.md (2026-08-30 composed-pilot entry — resolution trigger feeds here)
---

# R-001: Composed autonomous UI pilot (jig × vellum × servo) — run record

> This is an **open investigation**, not a decision and not committed work.
> The pilot's *work item* lives in the target app's repo (a gauge spec); this
> note is jig's coordination + evidence record. Its conclusion feeds
> [ADR-0059](../decisions/adr-0059-servo-delivered-work-design-review-gate.md)'s
> frame-critique/accept flow and triages the 2026-08-30 inbox entry.

## Question

Does the composed stack — jig spec-lifecycle + attestation × vellum measured
redline × servo suitability/spec-oracle/design-eval/agent-loop — run end to end
on one small real UI slice of a real app, and what does the run teach:

1. **ADR-0059 OQ1** — is `servo_driven: true` frontmatter the right trigger
   marker, or should jig infer from `.servo/runs/*`?
2. **ADR-0059 OQ2** — where does the design-review verdict live (the spec 071
   `design_review` pass verdict file vs. a new home)?
3. **servo 012-05** — the deferred first-consumer wiring (revival trigger =
   "the composed pilot being scheduled or run" — it now is).
4. **vellum** — does the proven manual redline pass compose as the AC source
   for a jig spec authored per spec 104's nudge?
5. **ADR-0051** — first live exercise of `governance.py identity-check` on an
   unattended run (expected: **fails safe → branch-only, no auto-merge**,
   because the target's governance plane is not armed).

## Target selection (decided 2026-08-31)

**App: gauge** (`~/Projects/misc/gauge`, github.com/ramboz/gauge) — the
manager/portfolio dashboard.

- The **proven** vellum loop (design → consistency pass → redline → build →
  score) ran on gauge and scored **0.85** via servo design-eval (vellum
  `docs/pilots/consistency-pass.md`; gauge slice 013-02 era, ~2026-08-04).
- servo is scaffolded and instrumented: `.servo/install.json` has
  `signals.tests: true` (node --test suite) + components `node_test`,
  `design_fidelity`; `.servo/design-eval/config.json` is **approved** with one
  screen (`portfolio-cards`) judged against the frozen mockup.
- jig rails are proven on gauge: spec 015 (manager-card-redesign, 4 slices
  DONE) already ran `design_review: true` + design-eval gating interactively.
- **Tests present** ⇒ the pilot deliberately sidesteps servo's suitability
  signal gap; servo **ADR-0036 / spec 030** (frozen evals satisfy
  `has_signal`) stay un-exercised and un-blocking. The run still records what
  `edd-suitability` says, as adjacent evidence for that Proposed ADR.

**Slice: the mockup's Table view.** The frozen design reference
(`docs/specs/012-portfolio-manager-analytics/design/manager-dashboard-mockup.html`)
ships **two** views — "▦ Cards view" (built, spec 015) and "▤ Table view
(same data, comparison-first)" with "a real build toggles between them". The
current dashboard has **no table view and no toggle** (verified 2026-08-31:
the only `table` hits in `public/index.html` are comments). Small, real,
testable (pure row-assembly + sort-key helpers under node --test), and
design-gateable (a second design-eval screen, `selector: table` on the same
mockup file).

Rejected alternatives:
- *Attention queue redesign* — the cross-project attention queue was
  **removed per owner feedback** (`public/index.html:644`); rebuilding it
  contradicts a product decision.
- *food-log* (servo 012-05's original candidate) — not present on this
  machine.
- *airlock / cwv-workbench / game-engine* — servo-scaffolded but no
  design-eval; airlock is the ADR-0059 evidence source, already used.

## The chain (phases, commands, evidence to capture)

Phase state legend: `[ ]` pending · `[~]` in progress · `[x]` done.

### Phase 0 — runbook `[x]`
This note, committed on jig branch `claude/servo-velum-pilot-e8e406`.

### Phase 1 — jig spec on gauge `[x]`
Reserve + author gauge **spec 016 — portfolio table view** per spec 104's
authoring nudge: design values extracted into checkable ACs;
`design_review: true` on the visual slice; **`servo_driven: true`** stamped on
the slice (the ADR-0059 OQ1 experiment — record whether anything reads it and
whether inference from `.servo/runs/*` would have sufficed). Scope: cards⇄table
toggle + table view to the mockup, default order = existing worst-first
`ragSortKey`; column re-sorting **deferred** (behavior, not fidelity — keep the
pilot slice small). Reservation via `workflow.py new` against gauge
origin/main (ADR-0015 flow); spec body lands on gauge main (docs-only) so
sibling sessions see it — implementation stays branch-only.

### Phase 2 — vellum measured redline `[~]`
Run vellum's **proven manual pass** against the mockup's table region →
measured facts (colors, spacing, borders, typography — not hand-read CSS).
The redline verifies/replaces the spec's hand-extracted AC values; deviations
between hand-read and measured values are themselves pilot evidence (the
reason vellum exists). Evidence: the redline artifact path + any corrections
it forced on the ACs.

### Phase 3 — servo compile on gauge `[ ]`
1. `edd-suitability` → expect `suitable` on the `tests` signal (capture the
   verdict JSON; note what it would have said with no tests — ADR-0036
   adjacent evidence).
2. `spec-oracle` → compile spec 016's ACs into a checks overlay
   (`.servo/spec-oracles/016/…`), approve + freeze.
3. `design-eval` → add screen `portfolio-table` (`referenceSource.selector`
   on the mockup's `table`; a setup script toggles the app into table view),
   re-capture refs, **freeze** (approval provenance per servo 028-02).
   ⚠ Preflight: the servo *plugin install* on this machine may predate servo
   origin/main's design-eval v2 schema work (specs 028/029, release 0.10.0)
   — verify plugin version before this phase and update if needed.

### Phase 4 — servo agent-loop `[ ]`
Attended run first (one iteration, human-watched), then `--background`,
**branch-only** on gauge — no auto-merge: `governance.py identity-check` is
expected to fail safe (gauge has no CODEOWNERS / governance.md /
protected_paths — verified 2026-08-31), which *is* the ADR-0051 exercise.
Evidence: run ledger under `.servo/runs/<run-id>/`, oracle scores per
iteration, guardrail behavior, cost.

### Phase 5 — jig attest + human disposal `[ ]`
`review.py design-review` (attest-only, slice 071-01) reads the frozen
design-eval verdict → `record-review` → REVIEWED/DONE gates on gauge spec
016. Then **human disposal** per ADR-0059: diff review for reward-hacking,
eval-contract design look, reconciliation micro-sweep. Evidence: where the
verdict file actually lands (OQ2), what the light pass catches that the green
oracle missed (the ADR-0059 assumption under test).

### Phase 6 — evidence disposal `[ ]`
- Feed this note's findings into ADR-0059's frame-critique/accept flow.
- Triage jig's 2026-08-30 inbox entry (resolution trigger fired).
- servo: revive deferred 012-05 per its stated trigger (re-open to DRAFT;
  wiring hosted in gauge).
- vellum: report the seam findings against its pilot entry (its
  jig-servo-autonomous-sessions branch).
- `/jig:memory-sync` per house discipline.

## Preflight ledger (verified 2026-08-31)

- **jig**: spec 071 DONE (attest pass exists — `review.py design-review`),
  spec 104 DONE (authoring nudge), ADR-0059 Proposed (`frame_review: true` —
  accept flow needs a recorded frame-critique), ADR-0051 built.
- **servo**: local checkout is **behind origin/main by 19** and **ahead 1**
  — the unpushed local commit mints **ADR-0033
  `agent-loop-permission-preflight`**, which **collides** with origin/main's
  ADR-0033 `design-eval-structured-scoring-policy`. Needs renumbering before
  push (flagged to owner; not a pilot blocker). ADR-0036 + spec 030 (DRAFT,
  DoR gated on the ADR's acceptance) are the companion filings — **not**
  needed for this pilot (gauge has tests).
- **vellum**: pilot entry + companion filings (ADR-0009 design-source
  adapters, spec 011 figma-source-adapter, slice 010-03 audit-artifact-emit)
  live on **unmerged branch** `claude/jig-servo-autonomous-sessions-99ec25`;
  main is fine for the *proven manual pass* (slice 010-01 verified-apply
  landed via PRs #37/#38/#40). Local checkout behind origin by 6 (fetched).
- **gauge**: clean on main; governance plane **not armed** (expected — the
  identity-check fail-safe is the exercise, not a gap to fix first).

## Open questions

- Does anything *read* `servo_driven: true` today, or is the marker purely
  evidence for ADR-0059 OQ1? (Expect: nothing reads it — record that.)
- Which vellum entry point is the canonical "proven manual pass" for a
  single-file HTML mockup region (vs. a CD design folder)? Resolve at Phase 2.
- servo plugin version on this machine vs. origin 0.10.0 design-eval schema
  (Phase 3 preflight).

## Log

- **2026-08-31** — Pilot started (jig session, branch
  `claude/servo-velum-pilot-e8e406`). Cross-repo state surveyed; target
  (gauge) + slice (table view) decided; this note committed. Phase 1 begun.
- **2026-08-31 — Phase 1 done.** gauge **spec 016 — portfolio-table-view**
  reserved on origin/main (`ae601ef`, ADR-0015 flow) and authored
  (`2bc7e30`, landed on gauge main): slice 016-01 "table view + cards⇄table
  toggle", `design_review: true` + `servo_driven: true` (OQ1 marker stamped,
  with an explicit "nothing reads this" comment), 7 design-value +
  functional ACs, vellum-redline + design-eval wiring as DoR items, spec_lint
  clean (16 specs), board regenerated. Authoring done in gauge worktree
  `.claude/worktrees/pilot-016-portfolio-table` (branch
  `pilot/016-portfolio-table`) — the implementation branch for the loop.
  **Seam finding (autonomy-relevant):** `workflow.py new`'s reservation push
  failed on this machine — the default git credential is the EMU account
  (`ramboz_adobe`), denied on personal `ramboz/*` HTTPS remotes; the dangling
  reservation commit had to be recovered and re-pushed via the SSH URL
  (`git push git@github.com:… <sha>:refs/heads/main`). An unattended
  servo/jig autonomy path on this machine inherits this: any flow that
  pushes to a personal-repo HTTPS remote fails until the remote (or a
  pushurl) is SSH. Feed into the run-evidence for ADR-0051-adjacent
  preflights.
- **2026-08-31 — Phase 2 begun.** Redline of the mockup's table region
  delegated (vellum contract per `plugin/skills/redline-request` +
  `build-to-redline`); deliverables land under gauge
  `docs/specs/016-portfolio-table-view/design/`. Clarified en route: the
  consistency pass (vellum spec 010) is CD-facing design *repair* — for a
  single-file, already-frozen mockup the audit half applies at most; the
  redline is the load-bearing Phase-2 artifact here.

## Conclusion

_Open — fills in as phases complete._
