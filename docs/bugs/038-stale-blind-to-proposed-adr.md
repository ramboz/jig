---
status: DONE
tier: standard
severity: low
claimed_by: claude/bug-stale-proposed-adr
regression_test: skills/spec-workflow/test_workflow.py::StaleProposedAdrTests
main_repro_checked_at: 2026-09-17
main_repro_ref: origin/main@1014d3edfd3ee06048a86782e6d73c831857aa26
main_repro_result: reproduces
red_confirmed_at: 2026-09-17
green_confirmed_at: 2026-09-17
fix_class: structural_fix
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 038: stale-blind-to-proposed-adr

Reported in issue 218 (the ADR/`stale` companion half; part B — split from the
`orient` claim-reaping half, bug 037).

## Symptom

`workflow.py stale` never flags a `Proposed` ADR that was scaffolded with an
empty `last_verified` (the `adr.py new` default) and then drifted — the one
decision record most likely to have gone stale is exactly the one the staleness
tool is structurally blind to. A never-verified, never-reconciled `Proposed`
ADR can sit contradicting the shipped code indefinitely and `stale` stays
silent.

## Repro

1. `adr.py new some-decision` → scaffolds `status: Proposed`, `last_verified:`
   empty.
2. Time passes (> the `stale` threshold, default 90 days); the ADR is never
   accepted, verified, or superseded.
3. `workflow.py stale`.

Observed: the Proposed ADR is **not** listed. `find_stale_items` skips it at
`if not lv or not deps: continue`.

## Evidence

- `find_stale_items` ([workflow.py:2847-2851](../../skills/spec-workflow/workflow.py)):
  ```
  lv = fm.get("last_verified", "").strip()
  deps = fm.get("dependencies") or []
  if not lv or not deps:
      continue
  ```
  An empty `last_verified` (scaffold default) OR an empty `dependencies` list
  short-circuits the ADR out of the walk before any check runs.
- `_stale_check` (workflow.py:2765) is a **conjunctive** `last_verified`-aged
  AND a-dependency-changed test — it can only fire for an ADR that *has* a
  `last_verified` to age and deps to compare. It cannot, by construction,
  catch a never-verified ADR.
- `stale()` (workflow.py:2878) renders whatever `find_stale_items` returns; it
  adds no ADR handling of its own. So `find_stale_items` is the sole ADR
  staleness surface.

## Hypotheses

- [ ] H1: The date parsing is wrong (`_stale_check` mis-ages Proposed ADRs).
  Falsify: `_stale_check` is never reached for an empty-`last_verified` ADR —
  the `if not lv ... continue` guard returns first, so no date is parsed at
  all. Falsified: the skip precedes any parsing.
- [x] H2 (leading): The ADR walk **structurally excludes** empty-`last_verified`
  records. `find_stale_items` treats a missing `last_verified` (or missing
  deps) as "nothing to check" and `continue`s, so a `Proposed` ADR that was
  never verified is never considered — there is no "never-verified" code path.
  Confirm: add an ADR with `status: Proposed`, empty `last_verified`, and an
  old proposal date; observe `stale` still reports nothing until the walk
  learns to age a never-verified Proposed ADR by its proposal date.

## Root cause

`find_stale_items` models ADR staleness as a single conjunctive predicate —
`last_verified` older than N days **AND** a dependency changed since. Both
inputs require a *populated* `last_verified` and `dependencies`, so the guard
`if not lv or not deps: continue` silently drops the never-verified case. A
`Proposed` ADR scaffolded by `adr.py new` starts with `last_verified:` empty
(deliberately — `last_verified` is a *freshness* field stamped at RECONCILED /
`reaffirm`, not an acceptance date; see `adr.py::_extract_status_and_date`), so
it has no `last_verified` to age against and is skipped forever. There is no
"an unverified decision record is stale by definition" path.

**Grounding (enumeration).** "`find_stale_items` is the sole ADR-staleness
surface" is a universal claim, established by enumeration:
- `grep -n "last_verified\|find_stale_items\|def stale" skills/spec-workflow/workflow.py`
  — the ADR staleness logic lives only in `find_stale_items` (walk) + its
  helper `_stale_check`; `stale()` is a pure renderer of that list; the CLI
  `stale` sub-command dispatches to `stale()`. No other function ages ADRs.
- The set is `grep`-closable: `last_verified` is a literal frontmatter key read
  only via `fm.get("last_verified")` (no ORM/reflection path), and ADR
  discovery is the single `decisions_dir.glob("adr-*.md")` loop.

## Repository closure inventory

**Equivalent / convergent logic searched:** Terms `last_verified`, `Proposed`,
`_stale_check`, `find_stale_items`, `_file_modified_iso`,
`_extract_prose_status_and_date`. `adr.py::_extract_prose_status_and_date`
already parses the `## Status` body's `Proposed (YYYY-MM-DD)` line — the exact
proposal date I need — but importing `adr.py` into `workflow.py` crosses the
skill boundary (`workflow.py` never imports a sibling skill's module), so the
reuse decision is to add a small local extractor mirroring that regex rather
than couple the skills. `_file_modified_iso` (workflow.py:already present) is a
git-commit-date age source (reliable across checkouts) for the fallback.

**Relevant history inspected:** `stale` was built by specs 014/015 and extended
by 050-02 (the `category` field + team-context finding). No prior bug on the
Proposed-ADR blind spot. The `last_verified`-is-a-freshness-field ruling
(ADR-0024 / ADR-0046) is *why* the field is empty on a fresh ADR — the fix must
not conflate `last_verified` with the proposal date (a plausible wrong date is
worse than none, per `_extract_status_and_date`), so age is measured from the
`Proposed (date)` line, not by back-filling `last_verified`.

**Affected call sites:** `find_stale_items` (the ADR branch) is the only surface
changed. `stale()` renderer prints `  <display>: <reason>` for any category, so
the new `proposed-unverified` finding renders with no renderer change. The slice
walk and the existing `last-verified` / `team-context` findings are
**intentionally left alone** (a Proposed ADR that *does* carry a `last_verified`
still flows through the existing dep-change path unchanged).

**Reuse decision:** Add a local `_adr_proposed_date` extractor (small regex,
mirrors adr.py's canonical `Proposed (YYYY-MM-DD)` shape) + a new branch in
`find_stale_items`; reuse `_file_modified_iso` for the fallback age. No new
module, no cross-skill import.

## Fix class

`structural_fix` — adds the missing "never-verified decision record is stale by
definition" path to the staleness checker; the root cause is the structural
skip, not a mis-parse.

## Fix

In `find_stale_items`, before the existing `if not lv or not deps: continue`
skip, add: when an ADR is `status: Proposed` with an **empty** `last_verified`,
measure its age from the `## Status` body's `Proposed (YYYY-MM-DD)` line
(`_adr_proposed_date`, falling back to `_file_modified_iso`), and when that age
exceeds `days`, emit a finding under a new `proposed-unverified` category:
"Proposed ADR, never verified (empty last_verified); proposed <date> (N days
ago) — the record most likely to have drifted; verify or supersede."

Scope guards:
- Only `Proposed` + empty `last_verified` fires the new path — a Proposed ADR
  that carries a `last_verified` still flows through the existing dep-change
  check (it has been verified at least once).
- Age is the proposal date, never `last_verified` (which is a freshness field);
  no back-filling.
- Informational only (`stale` stays exit-0); it is advisory noise-tolerant,
  matching the existing report's non-gating design.

Known residual (low, documented): `_adr_proposed_date` uses `search`, so it
takes the first `Proposed (YYYY-MM-DD)` line document-wide. In a canonical ADR
that is the `## Status` line; a body that placed an earlier line starting with
that exact shape (rare — ADR options are `### Option …` headings) would win.
Accepted as low-risk given the specificity of the pattern; hardening to the
`## Status` section is a cheap future tightening if it ever bites.

## Call-site closure

**Disposition per affected site:**

- `find_stale_items` ADR branch (workflow.py) — **changed**: adds the
  `proposed-unverified` path before the existing skip.
- `_adr_proposed_date` — **new** local helper.
- `stale()` renderer — **left alone**: category-agnostic, renders the new
  finding unchanged.
- slice walk + `last-verified` / `team-context` findings — **left alone**:
  orthogonal to the Proposed-ADR gap.

**Known untested path:** the `_file_modified_iso(adr_path)` fallback (used only
when an ADR lacks a parseable `Proposed (YYYY-MM-DD)` line) is a defensive
safety net not directly exercised by `StaleProposedAdrTests` — every fixture
supplies the status line. Testing it deterministically would need a
git-committed ADR without the line; deferred as low-value (canonical ADRs
always carry the line, and `_file_modified_iso` is already covered where it is
reused for dep dates).

## Already tried

(None — the leading hypothesis held on first cut.)

## Regression test

`skills/spec-workflow/test_workflow.py::StaleProposedAdrTests` — five cases:
never-verified old Proposed ADR flagged (structured + CLI-exit-0), a recent
Proposed ADR not flagged, a Proposed ADR that *has* a `last_verified` not
flagged by the new path, and (scope guard) an Accepted empty-`last_verified`
ADR not flagged.

## Proof

- **Red** at `origin/main@1014d3edfd3ee06048a86782e6d73c831857aa26` (fix absent): the two detection
  tests FAIL (`find_stale_items` returns `[]` / CLI reports "no stale items");
  the three scope-guard tests already pass. Witnessed by the `→ FIXING` gate
  (`red_confirmed_at`).
- **Green** after the fix: `StaleProposedAdrTests` 5/5 OK; `StaleCheckTests` +
  `StaleTeamSignalTests` still OK (existing conjunctive path unchanged).
- Full `test_workflow.py`: **552 tests OK**. `uvx ruff check` on the changed
  files: clean.

## Learning

`workflow.py stale`'s ADR check was a single conjunctive predicate
(`last_verified` aged AND a dep changed), which structurally excluded the very
record it most needed to catch: a `Proposed` ADR scaffolded with an empty
`last_verified` and never reconciled. When a checker's guard clause treats
"input field is empty" as "nothing to check," it silently exempts the
never-touched case — usually the highest-risk one. The fix ages a never-verified
Proposed ADR by its **proposal date** (the `Proposed (YYYY-MM-DD)` status line),
not by `last_verified` — conflating a freshness field with an acceptance date
would publish a plausible-but-wrong age (ADR-0024 / ADR-0046 rationale).

## Main recheck

- 2026-09-17 - `origin/main@1014d3edfd3ee06048a86782e6d73c831857aa26` -> reproduces: find_stale_items on a Proposed ADR with empty last_verified + a 200-day-old 'Proposed (date)' line returns [] (skipped at 'if not lv or not deps: continue'); StaleProposedAdrTests::test_never_verified_old_proposed_adr_is_flagged + ::test_flagged_adr_appears_in_cli_report_exit_zero FAIL against this ref.
