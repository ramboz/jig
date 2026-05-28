---
status: DONE
dependencies: []
last_verified: 2026-05-28
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
---

## Slice 037-01 — land-ff-against-origin

**Goal:** Harden `skills/slice-land/land.py`'s destructive direct-merge
path so it reads the FF condition from `origin/main` (not local `main`)
and refuses to leave the user in a half-merged state when the push
fails. End-to-end value: a user with a stale local `main` runs
`/jig:slice-land execute --mode direct`, gets an upfront refusal with a
clear recovery hint, and never sees the current failure mode (silent
local merge → push rejected → no rollback guidance).

**DoR:**

- ✅ Spec 037 is `READY_FOR_IMPLEMENTATION`; clarifications Q1–Q5 are
  resolved and recorded in the spec body.
- ✅ Bug #1 (`_check_ff_viable` at `land.py:555`) and bug #2
  (`_execute_direct` at `land.py:694`) are re-verified live at slice
  start (spec 037's 2026-05-26 verification establishes the baseline).
- ✅ `reserve_spec`'s precedent for fetch-failure handling
  (workflow.py:1278–1282 — warn + proceed on local view) is unchanged
  and reachable as a reference shape.

**Acceptance Criteria:**

1. **`_check_ff_viable` fetches `origin/main` and checks against it.**
   Before computing the FF condition, the helper runs
   `git fetch origin main`. On success, the ancestor check uses
   `origin/main` rather than local `main`. A local main that is
   *behind* `origin/main` produces a refusal; a local main that is
   ahead, equal, or has the branch as a descendant of `origin/main`
   continues to pass.

2. **Refusal message names the divergence shape.** The refusal text
   on a "local behind origin" condition contains both `"origin/main"`
   and a "pull or rebase" hint — e.g. `"local main is behind
   origin/main — pull or rebase before merging"`. The existing
   "main has diverged" wording is preserved for the local-only
   fall-back path (see AC #5).

3. **Refusal exit code is shared, not new.** The new refusal returns
   via the same exit-code path as today's dirty-tree / off-main
   refusals (currently exit 1 through `execute()`'s error parts).
   Tests assert on message content, not on a distinct numeric code.

4. **Fetch failure degrades to warning + local check.** When
   `git fetch origin main` returns non-zero, the helper writes a
   one-line warning to stderr (form: `"warning: git fetch origin main
   failed: <stderr>; proceeding with local view"`) and then runs the
   existing local-`main` ancestor check. Mirrors `reserve_spec`'s
   precedent at workflow.py:1278–1282. The user's merge is not
   blocked by network failure alone.

5. **No `origin` / no `origin/main` falls through to local check.**
   If `git config --get remote.origin.url` fails (no `origin`
   configured) OR the post-fetch `git rev-parse --verify origin/main`
   fails (ref absent locally), the helper skips the origin-aware
   check entirely and runs the existing local ancestor logic. No
   refusal is emitted on this path; no warning either (silent
   fall-back per Q4 resolution — this is the local-only repo
   contract, not a degraded network case).

6. **`_execute_direct` refuses on push failure with a recovery hint.**
   When the `git push origin main` step fails (network, rejected,
   non-fast-forward, auth), the helper:
   (a) does **not** attempt any automatic rollback (no
   `git reset --hard origin/main`, no destructive helper action);
   (b) appends a `## Error` block to the report that names the
   failed step AND includes a one-paragraph recovery hint —
   minimally: "Local `main` now carries the merge commit but it
   could not be pushed. Inspect the rejection with `git push origin
   main`; if the remote moved, run `git fetch origin main` then
   `git reset --hard origin/main` to drop the local merge, then
   re-run `land.py execute` after rebasing your feature branch on
   the new origin.";
   (c) returns the same non-zero exit code as other `_execute_direct`
   failure paths today.

7. **The four-step git sequence (`checkout main` → `merge --ff-only`
   → `push origin main`) is preserved.** No new step is added between
   `merge` and `push` (e.g. no "verify push will succeed" pre-check).
   The fix shape is: stronger upfront FF check (AC #1) + better
   recovery on the post-push failure (AC #6). The middle stays as it
   was.

8. **Dry-run path is unchanged.** `--dry-run` continues to print the
   four git commands without executing any of them and without
   fetching from origin (no network calls in dry-run mode).

**DoD:**

- [x] All ACs pass; full test suite green (no regressions in the
      existing land.py test corpus).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Required cases: stale-local-main (AC #1, #2), shared
      exit code on the new refusal (AC #3), fetch-failure simulation
      (AC #4), no-`origin`-remote and no-`origin/main`-ref fixtures
      (AC #5), push-rejection simulation with assertion that the
      recovery hint substring is present in the report (AC #6),
      dry-run does not fetch (AC #8).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`. (Three passes: compliance via `review.py
      implementation`, craft via `review.py pr-review`, reconciliation
      via `review.py reconciliation` — all dispatched to `jig:reviewer`
      subagent; arch pass skipped, frontmatter has no `arch_review: true`.)
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. (No decisions deferred during
      implementation; condition trivially satisfied. See deviation-
      log item 11.)

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column carries the load-bearing invariant: "Origin-aware
      FF check (warn-and-fall-back on fetch fail, silent local
      fall-back on missing origin); push-fail prints recovery hint,
      no auto-rollback."
- [x] `CLAUDE.md` hygiene per spec 025-01 rule: **037-02 is still
      in flight** (READY_FOR_IMPLEMENTATION at 037-01 close-out),
      so the spec's Active-specs entry is left intact per the rule.
      No new skill row needed (no new skill ships).

**Anti-horizontal-phasing check:** After this slice lands, a user
running `/jig:slice-land execute --mode direct` against a feature
branch whose local main is stale gets an upfront refusal — and a
user whose push gets rejected mid-flight gets a recovery hint.
Both are user-visible behavior changes in the destructive path,
delivered end-to-end in this one slice. Slice 037-02 is independently
shippable on `workflow.py` and does not depend on this slice's code
changes.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**1. Pre-implementation spec correction — 007-02 framing.** During
`/jig:clarify` (before implementation began), spec body's non-goal +
Q3 framing claimed slice 007-02 was DEFERRED — verification showed
007-02 is DONE; the safety concerns lived in its deviation log, not
in a parked slice. Spec body, Q3 Clarifications entry, and
Dependencies/coordination line were rewritten before slice
implementation. No code impact; logged for traceability since the
original framing is preserved nowhere else.

**2. Test-helper footgun — `MagicMock` callable conflation.** The
first `_patched_run` dispatcher iteration (test_land.py:1750–1787)
treated `MagicMock` results as "callable entries" because `MagicMock`
instances are themselves callable. This silently bypassed configured
`returncode` values and produced false greens in two AC #4/#5 tests
during development. Final dispatcher uses
`isinstance(entry, (types.FunctionType, types.LambdaType, types.MethodType))`
to distinguish lambda/function entries from `subprocess.CompletedProcess`
results. Worth carrying forward as a known footgun for any future
subprocess-mock fixture that builds on this pattern.

**3. Recovery-hint paragraph shape — single append, no new heading.**
AC #6(b) reads as a recovery paragraph appended after the existing
`## Error` block, not a new `## Recovery` heading. Implementation
follows the literal AC shape (`land.py:826`). The two load-bearing
substrings (`could not be pushed`, `git reset --hard origin/main`)
are both present. Craft reviewer noted (`land.py:826-836` [nit])
that splitting into two lines would aid skimmability — left as-is
since the AC contract is satisfied and the cost is cosmetic.

**4. AC #2 local-fallback wording preserved verbatim.** The
pre-existing `"main has diverged — FF merge not possible; pull or
rebase first"` message is retained for the local-only fall-back
branch (AC #5 paths). The new origin-aware refusal uses
`"local main is behind origin/main — pull or rebase before merging"`.
Both messages coexist; tests assert on the new substring path only.

**5. Fetch-warning text matches AC #4 form exactly.** Compliance
reviewer flagged this as a non-deviation worth noting:
`"warning: git fetch origin main failed: <stderr>; proceeding with
local view"` is byte-for-byte the form specified in AC #4. No
paraphrasing or expansion; the substring is fixture-stable.

**6. New runtime cost — unconditional `git fetch origin main` in
live mode.** Every non-dry-run `execute --mode direct` invocation now
performs one extra network round-trip. Required by AC #1; cannot be
elided without breaking the origin-aware contract. Craft reviewer
flagged a related nit (`land.py:602` [nit]): in repos where the
team's default branch isn't `main` (origin exists but exposes only
`master` or another default), the fetch is doomed and a
`git ls-remote --heads origin main` precheck would tighten the
contract. **Not retro-fixed in this slice** — flagged for follow-up
trigger: first real user hitting a non-`main`-default repo with
`execute --mode direct`.

**7. Reconciliation cleanup applied — dead `push_failed` variable.**
Craft reviewer flagged a dead local `push_failed = True` assignment
in `_execute_direct` (`land.py:809`, `:826`). The variable was
written but never read; the recovery-hint append is unconditional
on `args[0] == "push"`. Removed in reconciliation (single-line
cleanup, no behavior change). Full suite re-run after the cleanup:
1,406 tests pass, 3 skipped (unchanged from the post-implementation
count). No new test required — coverage already asserted via the
existing AC #6 fixtures.

**8. Test that patches rather than drives the real helper.**
Craft reviewer flagged `test_ff_refusal_shares_exit_code_with_off_main_refusal`
(`test_land.py:1822` [nit]) as patching `_check_ff_viable` instead
of driving it for real. Other tests in the class do drive the real
helper, so AC #3 coverage is intact end-to-end. Kept as-is — the
test's surface contract (exit 1 + message-in-report) is the
load-bearing assertion for AC #3 and renaming the test would be a
docs-only churn.

**9. Shared-origin-helper extraction candidate for slice 037-03.**
Compliance reviewer noted `_check_ff_viable` is now one of (at most)
two callers for an origin-aware "fetch + verify + handle four
failure modes" pattern; the second caller will be slice 037-02's
preflight + `_next_spec_number`. ADR-0002's "three callers" rule
means duplicate-for-now is correct. Slice 037-02's implementation
will determine whether the optional slice 037-03 extraction becomes
worthwhile. No action this slice.

**10. Strengths flagged for repetition (from craft pass).**
   - **Algorithm-numbered docstring** (`land.py:569-585`): numbers
     the three fall-back branches and cites AC numbers + clarification
     IDs + the `workflow.py` precedent line range. Future readers
     don't need to grep across files. Worth mirroring in slice
     037-02's helper edits.
   - **`_patched_run` tuple-key behavior dispatcher**
     (`test_land.py:1750–1787`): mapping `(cmd_tail) → behavior`
     lets each test declare its world in a few lines. Cleaner than
     the inline `if/elif` chains used elsewhere in the same file
     for AC #4/#5 tests. Recommended as the in-repo idiom for
     subprocess-mock tests in slice 037-02 (`workflow.py` will need
     similar fixtures for `git ls-tree` / `git rev-parse origin/main`
     / `git merge-base` mocking).
   - **Absence-of-effect assertion** (`test_land.py:1994-2000`):
     the AC #6(a) "no auto-rollback" invariant is asserted by
     checking that no `reset --hard` command appears in the
     call log — not just that the recovery hint text is present.
     Catches a future regression where someone adds rollback
     logic but leaves the hint in place.

**11. Inbox / refinement-todo items.** No new inbox parking. No
refinement-todo entry updated for this slice; the "race-on-disk"
entry remains 037-02's potential close-out item. DoD checkbox for
"refinement-todo.md updated if any decisions were deferred" is
ticked because no decisions were deferred during implementation
(condition trivially satisfied).

**12. Deliberate non-parking — items 6 + 9.** Reconciliation
reviewer flagged that item 6's `git ls-remote --heads origin main`
precheck (for non-`main`-default repos) and item 9's
shared-origin-helper extraction (slice 037-03 candidate) are
forward-looking but neither was added to `docs/inbox.md` or
`docs/refinement-todo.md`. **This is deliberate**, not an
omission. Both items are conditional on a real downstream signal
that hasn't fired yet (item 6: first user on a non-`main`-default
repo; item 9: slice 037-02 implementation reaching identical
fetch/verify shape). Per product-vision's "speculative tier
promotion is explicitly disallowed" principle, parking either as a
todo before the trigger fires would be speculative work. The
deviation log itself is the durable record — both items name their
resolution trigger explicitly above, and the status board Notes
column carries the load-bearing invariants for 037-01.
