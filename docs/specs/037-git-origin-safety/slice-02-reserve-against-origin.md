---
status: DONE
dependencies: []
last_verified: 2026-05-28
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
---

## Slice 037-02 — reserve-against-origin

**Goal:** Move `skills/spec-workflow/workflow.py`'s spec-number scan
and divergence preflight off the local working tree and onto
`origin/main`, so a `workflow.py new <slug>` invocation in push mode
honours the team-wide reservation contract upfront rather than
discovering a collision at push time. End-to-end value: a user on a
local `main` that is behind `origin/main` gets an upfront refusal
("pull or rebase before reserving") instead of a confusing late push
failure, and the computed spec number reflects whatever has actually
landed on origin — not just what is in the local tree.

**DoR:**

- ✅ Spec 037 is `READY_FOR_IMPLEMENTATION`; clarifications Q1–Q5
  are resolved and recorded in the spec body.
- ✅ Bug #3 (`_next_spec_number` at `workflow.py:977`) and bug #4
  (`_preflight_branch_and_worktree` at `workflow.py:1109`) are
  re-verified live at slice start (spec 037's 2026-05-26
  verification establishes the baseline).
- ✅ The existing race-on-push classifier (`workflow.py:1190`,
  `_classify_push_failure`) and the on-push race-recovery path
  (`workflow.py:1356`) remain in place as the last-resort catch
  — this slice prevents the race upstream of them, but does not
  remove them.
- ✅ The fetch step at `workflow.py:1272–1282` (skipped on
  `--no-push`) is reachable from `_next_spec_number` callers
  before the next-number computation.

**Acceptance Criteria:**

1. **`_next_spec_number` reads `origin/main` in push mode.** When
   invoked through `reserve_spec` with push mode enabled (not
   `--no-push` / not `--pr`), the helper enumerates `NNN-*` entries
   via `git ls-tree --name-only origin/main docs/specs/` rather than
   `specs_dir.iterdir()`. The max-NNN-plus-one computation is
   unchanged; only the source of the listing changes.

2. **`_next_spec_number` keeps using the working tree on `--no-push`.**
   The `--no-push` path has no remote contract to honor — it scans
   the working tree exactly as it does today. `--pr` (PR-fallback)
   is push-mode-equivalent for the purposes of this AC: it scans
   `origin/main`.

3. **No `origin` / no `origin/main` falls through to working-tree
   scan.** If `git config --get remote.origin.url` fails OR the
   post-fetch `git rev-parse --verify origin/main` fails, the helper
   skips the `git ls-tree` path and runs the existing working-tree
   scan. No refusal; no warning (silent fall-back per Q4 — the
   local-only repo contract).

4. **`_preflight_branch_and_worktree` refuses on diverged main.**
   After the fetch (workflow.py:1272–1282) succeeds, the preflight
   checks whether local `main` is behind `origin/main` via
   `git merge-base --is-ancestor main origin/main` (or equivalent
   ahead/behind probe). If local is behind, raise `WorkflowError`
   with a message containing both `"origin/main"` and a "pull or
   rebase" hint — e.g. `"refusing: local main is behind
   origin/main — pull or rebase before reserving"`.

5. **Refusal exit code is shared.** The new diverged-main refusal
   raises `WorkflowError`, which `main()` already converts to exit 2
   (today's refusal contract). No new exit code is introduced.

6. **Fetch failure preserves existing warn-and-proceed behavior.**
   The existing fetch-failure handling at workflow.py:1278–1282
   (warn to stderr, continue with local view) is unchanged. When
   fetch fails, the slice's new diverged-main check is skipped
   (no `origin/main` ref to compare against) and `_next_spec_number`
   falls back to the working-tree scan per AC #3.

7. **Race classifier remains intact.** No code is removed from
   `_classify_push_failure` (workflow.py:1190) or the on-push
   race-recovery path (workflow.py:1356). They continue to catch
   the residual race where two reservations are committed
   simultaneously between the fetch and the push.

8. **Stale comment at workflow.py:1269 corrected.** The current
   comment ("Fetch origin/main first so the next-number scan
   reflects the freshest state") is misleading once AC #1 lands —
   the fetch updates the ref AND the scan now consults it. The
   comment is rewritten to reflect both effects (e.g. "Fetch
   origin/main first; both the next-number scan and the divergence
   preflight read from it.").

**DoD:**

- [x] All ACs pass; full test suite green (no regressions in the
      existing workflow.py test corpus).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Required cases: push-mode scan reads from
      `origin/main` not working tree (AC #1) — simulate a spec
      committed to `origin/main` but absent from the working tree
      and confirm it is counted; `--no-push` mode preserved (AC #2);
      no-`origin` and no-`origin/main` fixtures (AC #3); diverged-
      main fixture exercises the new refusal (AC #4) with assertion
      on the message substrings (AC #5); fetch-failure path
      preserved (AC #6); race classifier path still reachable
      and unchanged (AC #7).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`. (Two passes — compliance via `review.py
      implementation` + craft via `review.py pr-review` — both
      dispatched to `jig:reviewer` subagent; arch pass skipped,
      frontmatter has no `arch_review: true`.)
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. (No decisions deferred during
      implementation; the "race-on-disk" entry was re-evaluated and
      deliberately left open — see deviation-log item 12 for the
      narrowed-but-not-closed rationale.)

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column carries the load-bearing invariants: push-mode
      `git ls-tree` scan + `_preflight_diverged_main` helper +
      race-on-disk narrowed-but-not-closed + 037-03 not-promoted.
- [x] `CLAUDE.md` hygiene per spec 025-01 rule: spec 037 is now
      closed (037-01 + 037-02 both DONE, no DEFERRED slices except
      the optional 037-03 which was deliberately NOT promoted per
      deviation-log item 9). Active-specs section in CLAUDE.md was
      already `_(none — see status board)_` at session start; no
      compression needed. Per-slice load-bearing invariants live in
      the status board Notes column. No new skill ships → no Skills
      table edit.
- [ ] If `docs/refinement-todo.md`'s "race-on-disk" entry is now
      moot (the upfront fetch + diverged-main refusal closes the
      gap), mark it RESOLVED with a pointer to this slice.
      **Deliberately not ticked** — per deviation-log item 12, the
      entry was re-evaluated and the conclusion is "narrowed but
      not closed". The sub-second mkdir/commit window the entry
      describes is unchanged by this slice's preflight. Leave the
      entry parked per its stated resolution trigger ("first
      user-observable race-on-disk incident").

**Anti-horizontal-phasing check:** After this slice lands, a user
running `/jig:spec-workflow new <slug>` from a stale local main gets
an upfront refusal with a clear remediation, and the assigned spec
number is computed against whatever is on `origin/main` — not just
the local working tree. Both are user-visible behavior changes in
the reservation path, delivered end-to-end in this one slice.
Independent of 037-01 (touches `workflow.py`, not `land.py`).

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**1. Patterns mirrored from sibling slice 037-01.** Per 037-01's
deviation log items 2 + 10 and the craft-reviewer recommendations,
this slice deliberately mirrors three patterns:
   - **Algorithm-numbered docstrings** with AC citations + precedent
     line refs (`workflow.py:988-1006` for `_next_spec_number`;
     `workflow.py:1061-1080` for `_preflight_diverged_main` — both
     cite `_check_ff_viable` at `land.py:555-655`).
   - **`_patched_run` tuple-key behavior dispatcher** with the
     `isinstance(entry, (types.FunctionType, types.LambdaType,
     types.MethodType))` guard against MagicMock callable conflation
     (`test_workflow.py:3186-3281`).
   - **Absence-of-effect assertions** on `git ls-tree`, `git fetch`,
     and `git reset --hard` call logs rather than only positive
     substring presence (`test_workflow.py:3362-3372`, `3457-3462`,
     `3497-3501`, `3681-3686`, `3720-3728`).

**2. Signature change to `_next_spec_number` (deviation from
"only the source of the listing changes").** Spec AC #1 text reads
"The max-NNN-plus-one computation is unchanged; only the source of
the listing changes." The implementation adds two new kwargs
(`project_dir=None`, `use_origin=False`) instead of e.g. a wrapper
function. Both kwargs default to the working-tree behavior, so
existing callers (none outside `reserve_spec`) are source-compatible.
The kwargs make `--no-push` the explicit `use_origin=False` path
and keep call sites minimal. Documented in the function's docstring.

**3. New helper `_preflight_diverged_main` boundary choice.** Spec
AC #4 names `_preflight_branch_and_worktree` as the locus for the
diverged-main refusal. The implementation adds a *separate*
module-level helper (`_preflight_diverged_main` at
`workflow.py:1054-1108`) rather than inlining the check into the
existing preflight. Functionally equivalent — the call site in
`reserve_spec` runs the new helper after the existing preflight + fetch,
matching the spec's "After the fetch succeeds, the preflight checks…"
shape. Boundary choice is consistent with `land.py`'s
`_check_ff_viable` precedent (one helper per origin-aware concern)
and makes the divergence check independently testable.

**4. SHA-equality short-circuit before `--is-ancestor`.** Spec AC
#4 says "via `git merge-base --is-ancestor main origin/main` (or
equivalent ahead/behind probe)". `--is-ancestor` alone returns 0
for both equal *and* strictly-ancestor cases, which would falsely
refuse an in-sync repo. The implementation reads both SHAs first
(`git rev-parse --verify origin/main`, `git rev-parse main`) and
short-circuits to "in sync" on equality before invoking the
ancestor check. Three tests anchor the regression (behind, equal,
ahead).

**5. Stale line refs in slice DoR/AC.** The slice's DoR cites
`workflow.py:1272-1282` (fetch step) and `workflow.py:1356`
(race-recovery path). With the new helper inserted upstream, those
lines shifted to `~1396-1404` and `~1486-1500` respectively in the
delivered file. Not a deviation in behavior — both code paths are
untouched (AC #6, AC #7) — but readers consulting the spec's
line references against the post-landing file should expect drift.

**6. Three minimal existing-test edits.** AC #1 adds a
`git config --get remote.origin.url` call inside `_next_spec_number`
that runs *before* the existing `_check_gh_and_remote` call.
`_SubprocessRecorder`'s FIFO stub queue was consumed prematurely
in three existing PR-mode tests
(`test_new_falls_back_on_protected_branch`,
`test_new_pr_mode_skips_direct_push`,
`test_new_pr_mode_refuses_without_github_remote`). Each test got
a one-line stub addition annotated with `# Spec 037-02:` to surface
the rationale. Edits are minimal and scoped strictly to the FIFO
ordering issue.

**7. Reconciliation cleanup applied — dead dispatcher stubs.**
Craft reviewer flagged ([nit]) that five test methods stubbed
`("rev-parse", "origin/main")` but the dispatcher routes
`git rev-parse --verify origin/main` through the `("verify", …)`
key, not `("rev-parse", …)`. The stubs were dead (never consumed,
defaulted to `(0, "", "")` which still satisfied the read paths).
Removed in reconciliation along with the misleading docstring entry
at `test_workflow.py:3203`. Five test methods + one docstring line
trimmed; 1,418 tests still green (3 skipped). No new test required.

**8. AC #5 test is structural, not end-to-end.** Craft reviewer
flagged ([nit]) that `test_diverged_refusal_exits_2_through_main`
triggers a different `WorkflowError` (no-git → symbolic-ref failure
in an empty tmpdir) and asserts the *structural* claim that
`_preflight_diverged_main` raises `WorkflowError`. The
exit-2-from-WorkflowError contract is already pinned by other
tests in the file. Kept as-is — driving the diverged path through
`main()` end-to-end would require a fuller fixture (real git repo
with fake origin/main) and the structural assertion is sufficient
for AC #5's claim that no new exit code is introduced.

**9. Duplicate `git config --get remote.origin.url` call —
037-03 promotion signal.** Craft reviewer flagged ([nit]) that
`_next_spec_number` now invokes `git config --get remote.origin.url`
even when `_check_gh_and_remote` runs the identical probe shortly
after. Tightening per the reconciliation reviewer: the duplication
is only observable in **PR-fallback mode** (`_check_gh_and_remote`
runs inside `_do_pr_fallback` at `workflow.py:1296`, not on direct
push); direct-push runs the origin-url probe exactly once. Extra
subprocess is harmless either way, and the FIFO test edits above
accommodate it. Reviewer notes this is a candidate trigger
for slice 037-03 (shared-origin-helper) — combined with
`_check_ff_viable` in slice-land, there are now arguably three
origin-presence probes across the codebase. **Decision:** leave
duplicated, do NOT promote 037-03 yet. The three probes have
*different* contracts: `_check_ff_viable` does fetch + verify
origin/main + falls back; `_next_spec_number` does origin-url +
verify origin/main + falls back; `_check_gh_and_remote` does
origin-url + github.com-check + raises. Their shared shape is
"check origin presence" — but their failure semantics, return
values, and recovery paths diverge. Per ADR-0002, "three callers"
with *divergent shapes* doesn't trigger extraction. Reconsider
if/when a fourth caller appears with the same fetch + verify +
fall-back shape as `_check_ff_viable` / `_next_spec_number`'s
shared portion.

**10. `_mkspec` test-helper duplication.** Craft reviewer flagged
([nit]) that `ReserveSpecAgainstOriginTests._mkspec` duplicates
`ReserveSpecTests._mkspec` verbatim. Cosmetic; kept as-is.
Extraction to a module-level helper is reasonable but adds module
state for two callers in one file. ADR-0002 "three callers"
threshold not crossed.

**11. Strengths flagged for repetition (from craft pass).**
   - **SHA-equality short-circuit** (`workflow.py:1057-1108`):
     `_preflight_diverged_main` reads both SHAs and short-circuits
     to "in sync" before invoking `--is-ancestor`, sidestepping
     the equal-vs-ancestor ambiguity. Negative tests
     (`test_preflight_allows_when_local_equals_origin`,
     `test_preflight_allows_when_local_ahead_of_origin`) are
     exactly the regression anchors a future refactor needs.
   - **Defensive ls-tree parser** (`workflow.py:1027-1038`):
     `name.strip().rstrip("/").rsplit("/", 1)[-1]` handles both
     `docs/specs/NNN-slug` and `NNN-slug` forms; `re.match(r"^(\d{3})-")`
     filters non-spec entries. Future-proof against `git ls-tree`
     flag changes.
   - **AC #8's structural-and-prose comment test**
     (`test_workflow.py:3743-3767`): asserts BOTH the old comment
     is gone AND new prose names "next-number scan" + "divergence
     preflight" (or close synonyms). Catches both a forgotten edit
     and a half-edit; ergonomic for future re-wording.

**12. `docs/refinement-todo.md` "race-on-disk" entry — narrowed
but NOT closed.** Spec body's coordination note and slice DoR
suggested 037-02 "may close" the race-on-disk entry at
`refinement-todo.md:115-118`. **Resolution after implementation:**
the entry stays open. Slice 037-02's preflight catches the
*pre-session* divergence case (local main already behind
origin/main at `workflow.py new` invocation) — but the original
race-on-disk window (between `mkdir spec_dir` and `git commit`,
when two operators each compute the same next-number from a fresh
fetch) is unchanged. The fetch + diverged-main preflight narrows
the window's edge cases but doesn't eliminate the sub-second window
the entry describes. Per the entry's stated resolution trigger
("First user-observable race-on-disk incident"), the right move is
to leave it parked and let real failure data, not theoretical
narrowing, decide whether further work is needed. DoD checkbox
for "refinement-todo.md updated if any decisions were deferred"
is ticked because no decisions were deferred during implementation
(the race-on-disk evaluation is documented here as a deliberate
non-close decision).

**13. Inbox status.** No new inbox parking. No tooling watch-items
surfaced.
