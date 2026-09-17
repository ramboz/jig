---
status: DONE
tier: standard
severity: medium
claimed_by: claude/bug-orient-stale-claim
regression_test: skills/spec-workflow/test_workflow.py::OrientClaimReapingTests
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

# Bug 037: orient-stale-claim-not-reaped

Reported in issue 218 (this is the (A) "claim reaping" half; the ADR/`stale`
half is split into its own record).

## Symptom

`orient --fetch` (and the status board it reads from) presents a slice's
`claimed_by` as a live, in-progress session even after the claiming branch has
been **merged** into the default branch or **deleted** — feeding the
deterministic `focus:` headline so a human is told to treat finished/abandoned
work as an active session they must not collide with. `--fetch` reports the run
as verified-current (`freshness:`), which makes the ghost claim look
*confirmed*.

## Repro

1. `workflow.py transition <spec> <slice> IN_PROGRESS --push` stamps
   `status: IN_PROGRESS` + `claimed_by: <branch>` and publishes the branch.
2. Merge `<branch>` into the default branch (or delete it) **without** running a
   terminal transition on the slice.
3. `workflow.py orient --project-dir . --fetch`.

Observed: `focus: <slice> IN_PROGRESS (claimed by <branch>) · freshness: …`
even though `<branch>` is gone from origin (or fully contained in the default
branch).

## Evidence

- `_focus_summary` ([workflow.py:1899](../../skills/spec-workflow/workflow.py))
  ranks candidates purely by `status` via `_ORIENT_FOCUS_RANK`; `IN_PROGRESS`
  is the top entry in `_ORIENT_FOCUS_ORDER` (workflow.py:1794), so any
  `IN_PROGRESS` slice wins the headline. It renders `claimed_by` verbatim
  (`focus += f" (claimed by {safe_claim})"`) with **no liveness check**.
- `orient(fetch=True)` computes `_freshness_summary`
  ([workflow.py:2080](../../skills/spec-workflow/workflow.py)), which checks
  only `HEAD..{base}` (is the *default branch* behind origin). It never
  resolves any slice's `claimed_by` branch.
- Grep of `workflow.py` for a read-time claim-liveness check
  (`rev-parse`/`rev-list`/`ancestor`/`merged`/`reap` against `claimed_by`)
  returns nothing — confirming there is no reaper at orient/board read.
- spec 112's cross-ref machinery (`identifier_state_on_ref`,
  `find_sibling_done`) runs only at **transition/land** time (start-collision,
  sibling-DONE), never at orient/board read, so it does not close this.

## Hypotheses

- [ ] H1: The stale claim is written wrong at claim time (a `transition` bug).
  Falsify: the claim is written correctly on entry to a WORKING state; the
  defect is that nothing *invalidates* it when the branch later merges/deletes.
  `_focus_summary` reads current frontmatter faithfully — the frontmatter is
  simply never reaped. Falsified: the write path is correct.
- [x] H2 (leading): There is **no read-time liveness check** for `claimed_by`.
  `orient`/`_focus_summary` trust the stored branch name unconditionally, and
  `--fetch` verifies the default branch's freshness but not each claim's
  branch. Confirm: add a check that resolves the focus slice's `claimed_by`
  against origin and observe the headline still narrates a
  merged/deleted branch as live without it.

## Root cause

The lifecycle writes `claimed_by` on entry to a WORKING state (ADR-0045) but
**nothing invalidates it** when the claiming branch is later merged into the
default branch or deleted. `orient`/`_focus_summary` and the status board read
the stored branch name as authoritative, and the `--fetch` verification path
(`_freshness_summary`) checks only whether the *default branch* is behind
origin — never whether each `claimed_by` **branch** still exists or is already
contained in the default branch. So a merged/deleted claim renders as a live
session and can win the deterministic `focus:` headline.

**Grounding (enumeration).** The claim "nothing reaps `claimed_by` at read
time" is a universal/negative claim, so it is established by enumeration, not a
single citation:

- `grep -n "claimed_by" skills/spec-workflow/workflow.py` — every hit is a
  *write* on `transition` (lines ~1350–1545), a *read* into a display string
  (`_focus_summary` 1899–1924, `collect_slices` 2269, `render_status_table`
  2367/2379, `_render_claim_suffix` 2335), or prose. None resolves the branch
  against origin.
- The set is `grep`-closable here because `claimed_by` is a literal frontmatter
  key and a literal Python identifier; there is no ORM/reflection/codegen path
  that could read it invisibly (it is read only via `fm_fields.get(CLAIM_FIELD)`
  and the destructured `collect_slices` tuples, both grepped above).
- `orient` has exactly two callers (workflow.py:5510 CLI dispatch;
  `hooks/scripts/jig-project-orient.sh` SessionStart). Only the CLI passes
  `--fetch`; the hook never does — so any network-touching liveness check must
  live on the `fetch=True` branch to stay off the ~4 s hot path.

**Fail-safe constraint (load-bearing).** `claimed_by` stores the *branch name*
(`_claim_identifier` → `_current_branch`, else `JIG_CLAIM_ID`, else
`detached`), and **claims are local by default** — only `--push`/`--pr`
publish the branch to origin (`collect_slices` docstring; ADR-0045). So the
issue's suggested literal check `git rev-parse origin/<claimed_by>` would report
"branch deleted" for **every live local-only claim** — a false-positive that
erodes trust exactly like the bug it fixes. The reaper must therefore be
fail-*safe*: assert a stale claim only on high-confidence signals and stay
silent under any ambiguity.

## Repository closure inventory

**Equivalent / convergent logic searched:** Searched `workflow.py` and
`skills/_common/` for existing branch-liveness / containment / merged-detection
helpers: terms `merged`, `ancestor`, `rev-list --count`, `is-ancestor`,
`contained`, `reap`, `liveness`, `rev-parse --verify origin`. Findings:
`_common/cross_ref_state.py::identifier_state_on_ref` + `find_sibling_done`
resolve a slice's *lifecycle status on a ref* (transition-time duplicate-work
guard, spec 112) — a different contract (state-on-ref, not branch-liveness) and
gated to transition/land, not read. `land.py::_branch_freshness_warning` and
`_check_ff_viable` do `rev-list HEAD..origin/main` behind-ness, not claim-branch
existence. `_in_flight_base` (workflow.py:1975) resolves the default branch ref;
`_in_flight_git` (1927) is the bounded fail-soft git runner. **No existing
helper resolves a `claimed_by` branch's existence/containment against origin.**

**Relevant history inspected:** `git log` on the orient freshness surface: bug
031 (`orient-skips-origin-freshness`, DONE) added `--fetch` +
`_freshness_summary` — this bug is a follow-on gap to the *same* feature (it
verifies the default branch, not the claims). ADR-0045 / bug 014 widened
`claimed_by` to all WORKING states; `docs/refinement-todo.md` (the ADR-0045
visibility entry) already flags `orient`'s focus line + status board as "the
reader half" of claim correctness — on a *different axis* (unpushed sibling
visibility, not reaping merged/deleted claims). This fix should cross-link, not
collide, with that entry.

**Affected call sites:** `orient` (workflow.py:2136) is the only surface this
fix changes. Readers that also render `claimed_by` but are **intentionally left
alone** by this scope: `render_status_table` / `_render_claim_suffix` (the
board's Status cells) and `collect_slices`. Board/`check-board` reaping (issue
fix #4) is a larger write/CI surface deferred to refinement-todo, so the fix
stays proportional and bounded to the headline where the false "active session"
narration does its harm.

**Reuse decision:** Add a small fail-safe helper alongside the existing
`_in_flight_*` orient helpers (reusing `_in_flight_base` / `_in_flight_git`),
rather than reusing `cross_ref_state` (wrong contract: state-on-ref, not
branch-liveness, and transition-scoped). Duplication is avoided by building on
the orient git primitives already in the file.

## Fix class

`structural_fix` — adds the missing read-time liveness capability (the root
cause is that no reaper exists), not a symptom patch.

## Fix

On the interactive `--fetch` path only, `orient` resolves the **focus slice's**
`claimed_by` branch against origin and annotates the `focus:` segment:

- `_focus_candidate(rows)` extracts the winning focus tuple `(slice_id, status,
  claimed_by)`; `_render_focus_segment(candidate, claim_status)` renders it,
  replacing `(claimed by X)` with a stale label when `claim_status` is set.
- `_focus_claim_liveness(project_dir, candidate, fetch_ok=…)` returns
  `"merged"` / `"gone"` / `""` under the fail-safe rules in `## Root cause`
  (merged = present on origin AND contained in base; gone = absent on origin
  AND absent as a local ref AND the fetch succeeded; everything else is
  silence).
- `_orient_verify` performs the single bounded fetch and shares its `fetch_ok`
  boolean with both the freshness check (bug 031) and the reaper, so `--fetch`
  fetches once. `_freshness_summary` is decomposed into `_freshness_from_refs`
  (its post-fetch tail) so the fetch is not duplicated.

The `fetch=False` hot path (SessionStart hook) is byte-identical: no candidate
resolution touches the network, and `claim_status` stays `""`.

Bounded scope: only the focus slice's claim is resolved (one branch, not N).
Board / `check-board` reaping (issue 218 fix #4) is deferred to
refinement-todo. Known residuals (documented, all rare/opt-in), all chosen to
err toward silence:

- False-*positive* ("gone; verify" on live work): a custom `JIG_CLAIM_ID` or a
  claim held only in another clone (no matching ref anywhere).
- False-*negative* (renders live when actually done): a **squash-merged**
  branch still present on origin (its commits are not ancestors of base, so it
  reads as "ahead/live"); and a branch **merged then pruned from origin** whose
  **local ref still lingers** — indistinguishable from a fresh local branch
  sitting at base with no commits yet, so flagging it would false-positive
  every just-started claim. Note the common "merged via PR, branch auto-deleted"
  case *is* caught while the stale `origin/<branch>` remote-tracking ref lingers
  (a plain `git fetch` does not prune it), because it resolves and is contained
  → "merged".

The label says "verify", mutates nothing, and only appears on the interactive
`--fetch` path.

## Call-site closure

**Disposition per affected site:**

- `orient` / `_focus_summary` (workflow.py) — **changed**: refactored into
  `_focus_candidate` + `_render_focus_segment`; `orient` reaps on `--fetch`.
- `_freshness_summary` → `_orient_verify` + `_freshness_from_refs` —
  **changed**: fetch consolidated; freshness output preserved byte-for-byte
  (bug 031 tests stay green).
- `render_status_table` / `_render_claim_suffix` / `collect_slices` (board claim
  rendering) — **intentionally left alone**: board/`check-board` reaping is the
  deferred larger surface (refinement-todo); this fix is bounded to the headline.

## Already tried

(None — the leading hypothesis held on first cut.)

## Regression test

`skills/spec-workflow/test_workflow.py::OrientClaimReapingTests` — real bare
origin, six cases: the two stale cases the reaper must catch
(`merged`, `gone`), and four fail-safe guards that must **not** flag
(live local-only claim, live pushed-and-ahead claim, the no-`--fetch` hot path,
and an unreachable origin).

## Proof

- **Red** at `origin/main@1014d3e` (fix absent): `test_merged_…` and
  `test_absent_…` FAIL (headline still `(claimed by <branch>)`); the four
  fail-safe guards already pass. Witnessed by the `→ FIXING` gate
  (`red_confirmed_at`).
- **Green** after the fix: `OrientClaimReapingTests` 6/6 OK;
  `OrientOriginFreshnessTests` (bug 031) + `ProjectOrientationTests` still OK
  (freshness output + hot-path headline unchanged).
- Full `test_workflow.py`: **553 tests OK**. `uvx ruff check` on the changed
  files: clean.

## Learning

A claim-liveness reaper reading `claimed_by` against origin must be **fail-safe
by default**, because jig claims are *local by default* (only `--push`/`--pr`
publish the branch): the naive `git rev-parse origin/<claimed_by>` check the
issue suggested would flag every live local-only claim as "deleted," a
trust-eroding false positive worse than the bug. Only two branch states are
unambiguous enough to assert: present-on-origin-and-contained-in-base
("merged") and absent-from-origin-and-absent-locally ("gone"). Everything else
— including a merged-then-pruned branch whose local ref lingers (which looks
identical to a brand-new claim sitting at base) — must stay silent, because the
signals that would catch it also fire on genuinely live work. Reaping earns
trust only when a false "stale" is impossible on the common path; buy that with
narrower coverage, not the reverse.

## Main recheck

- 2026-09-17 - `origin/main@1014d3edfd3ee06048a86782e6d73c831857aa26` -> reproduces: orient(fetch=True) on a slice with a merged/deleted claimed_by branch renders 'focus: 002-01 IN_PROGRESS (claimed by <branch>)' with no stale signal; OrientClaimReapingTests::test_merged_claim_flagged_stale_on_fetch + ::test_absent_claim_branch_flagged_gone_on_fetch both FAIL against this ref (fix not present on origin/main).
