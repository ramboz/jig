---
slice: 096-01 — orientation reports work in flight
pass: compliance
verdict: pass
reviewer: jig:reviewer subagents (compliance rounds 1-2); round-2 closures applied by implementer — see 'Who verified what'
reviewed_at: 2026-07-23T05:06:30Z
prompt_source: review.py implementation docs/specs/096-orient-sees-work-in-flight/spec.md orientation <deliverables>
---

Round 1 returned **needs-changes** and found one genuine defect plus three
vacuous tests. All findings were applied; this file records the round-1 verdict
and its disposition (ADR-0014 §4 — git history is the audit trail).

## The primary finding — no aggregate latency bound (accepted, fixed)

The reviewer counted the worst case honestly: `_in_flight_summary` can issue up
to **nine** git calls, each bounded at 2.0 s, against a SessionStart hook that
bounds the whole command at 4 s and swallows a timeout as *no orientation at
all*. A per-call timeout is not a bound. The failure mode is precisely the one
the spec forbids: a working headline replaced by nothing, i.e. strictly worse
than before the slice.

Fixed by threading a single wall-clock deadline (`_IN_FLIGHT_TOTAL_BUDGET`,
1.5 s) through every call; per-call dropped to 0.75 s. Once the deadline is
spent, remaining calls return `None` immediately.

**AC3 was amended** rather than quietly satisfied: it now states the bound is
aggregate, not per-call, and records why the original wording was too weak.

## Three vacuous tests (accepted, fixed)

The reviewer demonstrated each would pass with the feature deleted:

- `test_hanging_git_is_bounded_and_silent` asserted only silence — which a
  `sleep 5` stub satisfies with no timeout at all, since empty stdout is
  already `!= "true"`. Now asserts **elapsed time**.
- `test_decision_section_cross_checks_open_prs` asserted `"pr" in section`,
  which matches the pre-existing words *Proposed* and *prominently*. Now pins
  `cross-check` and `open prs`.
- `test_the_three_misleading_states_are_named` searched the whole file;
  *superseded*, *stale* and *unmerged* all occur outside the new section. Now
  scoped to the section body.

A new `test_total_git_budget_is_bounded_across_many_calls` covers the primary
finding. **Mutation-checked:** disabling the shared deadline makes it fail
(2.69 s vs a 2.0 s assertion); restoring it makes it pass. The test is real.

## Correctness findings (accepted, fixed)

- **`origin/HEAD` was trusted unverified with no fall-through.** A stale
  `origin/HEAD` (default-branch rename, or a pruned target) would silence the
  segment permanently even with `origin/main` one line down the candidate list
  — or, worse, produce a confidently *wrong* count against an old trunk, which
  AC4 explicitly rules out. Now verified like any other candidate, with
  fall-through and de-duplication. Two tests added, closing what the reviewer
  correctly identified as a completely untested branch.
- **`raw.isdigit()` was the wrong guard for `int()`.** `"²".isdigit()` is True
  but `int("²")` raises — an escape from `orient()` that AC3 forbids. Now
  `isdecimal()`, with a test.
- **`orient()`'s docstring still claimed "durable jig artifacts only"**, which
  the slice's own DoR cited as evidence. Now states the bounded git dependency.
- **`SKILL.md` frontmatter `description`** enumerated the survey without pull
  requests while the body made them the first, never-skip item. The description
  is the routing surface; corrected.

## Reviewer limitations, recorded

The reviewer had read-only tools and could not run `scripts/run_tests.py` or
`git diff`, so two claims went unverified by it and were verified here instead:

- **Full suite:** `Ran 3524 tests … OK (skipped=4)`.
- **`test_scaffolded_headline_compacts_active_specs` unedited:**
  `git diff origin/main -- skills/spec-workflow/test_workflow.py` is
  insertions-only (`+` lines only, no `-`), confirming the DoD item.
- **Host packages:** regenerated via `scripts/build_host_packages.py`;
  `--check` reports in sync. The reviewer's spot-check of faithful
  regeneration is confirmed mechanically.

---

## Round 2 — verification pass (verdict: needs-changes; findings applied)

An independent round-2 reviewer verified each round-1 fix by asking whether the
test would still pass with the fix deleted. **All six were confirmed fixed**
(finding 4 as PARTIAL — see below), the deadline was confirmed threaded to all
six call sites with none missed, and the worst case recomputed independently as
~1.5 s + one spawn against the hook's 4 s.

It then found **two further defects of the same class the round-1 pass was
closing** — neither a regression from the fixes, both now closed:

- **`UnicodeDecodeError` escaped `orient()`.** `subprocess.run(text=True)`
  decodes strictly and `UnicodeDecodeError` is a `ValueError`, so it was not
  caught by `except (OSError, SubprocessError)`. A ref name invalid in the
  ambient encoding — or *any* non-ASCII branch under `LC_ALL=C` — raised
  straight out and the hook emitted no headline at all. Exactly the AC3
  violation, and exactly the "worse than pre-096" failure. Fixed with
  `errors="replace"` **and** `ValueError` added to the except tuple; test
  `test_undecodable_git_output_does_not_raise`.
- **Unsanitised repository-controlled text in the injected headline.** Both ref
  names reached the SessionStart `additionalContext` line with no whitelist and
  no cap, while the sibling claim field has had `_sanitize_orient_claim` and a
  hostile-input fixture since 088. Git permits `·` — the headline's own field
  separator — in a ref, so a branch could forge a field. Fixed with
  `_sanitize_orient_ref`; **AC9 added** to the slice rather than fixing this
  silently. Tests: `test_hostile_branch_name_cannot_forge_a_headline_field`,
  `test_long_branch_name_is_capped`.

**Finding 4 was PARTIAL and is now closed.** The three-state assertion was
scoped to the section, but `unmerged` also appears in the section's own
*heading*, so that one token stayed unpinned. The helper now starts the slice
*after* the heading line and anchors on the heading regex rather than a bare
phrase.

Round 2's three unverified claims (it had read-only tools) were verified here:
full suite `Ran 3527 tests … OK (skipped=4)` with `pyright: clean`;
`git diff origin/main -- skills/spec-workflow/test_workflow.py` has zero
deletion lines; `build_host_packages.py --check` reports in sync.

Its remaining reconciliation notes — the status board missing spec 096, the
0.75 s per-call behaviour change, AC4's `origin/<trunk>` phrasing, and the
first-resolvable-candidate heuristic — are addressed in the deviation log and
the sweep.

---

## Who verified what — stated plainly

Round 2 returned **needs-changes**. Its two new defects and the PARTIAL finding
were closed by the **implementer**, and there is no round-3 independent artifact
re-checking those specific closures. The `pass` verdict on this record therefore
means: *both rounds' findings were applied, and the applied state is covered by
tests that were mutation-checked* — not that a third independent reviewer
re-read the result. A separate reconciliation pass did review the written record
and found four further problems, all fixed (see the slice's deviation log,
entries 10 and 11).
