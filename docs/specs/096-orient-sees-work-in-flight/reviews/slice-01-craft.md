---
slice: 096-01 — orientation reports work in flight
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (craft pass; all 7 findings applied)
reviewed_at: 2026-07-23T04:57:04Z
prompt_source: review.py pr-review docs/specs/096-orient-sees-work-in-flight/spec.md orientation <deliverables>
---

Craft pass returned **needs-changes** with seven findings — no correctness
defects, all convention/clarity, all applied.

## Applied

1. **Constants diverged from the module's own conventions on two axes.** They
   were `_IN_FLIGHT_*`, sat 100 lines from the existing `_ORIENT_*` block
   (`workflow.py:1572-1589`), and used PEP-257 attribute docstrings that appear
   nowhere else in the file. Renamed `_ORIENT_IN_FLIGHT_*`, moved into that
   block, docstrings converted to `#` comments.
2. **`deadline: float | None = None` made the aggregate bound opt-in.** Both
   helpers are module-private with one call site each, both of which pass a
   deadline — so the default bought nothing and re-opened the exact hole round
   1 caught (a future `_in_flight_base(project_dir)` would get five unshared
   0.75 s calls). Now required and keyword-only on both.
3. **The test resolved its own sibling via `parents[2]`.** Every other surface
   test in the repo uses `Path(__file__).resolve().parent` (cf.
   `skills/analyze/test_analyze_skill_surface.py:34-35`). Matched.
4. **Section scoping keyed on a generic phrase, not the heading.** Three tests
   sliced the file at the first occurrence of `"Waiting on you"` /
   `"The one decision blocking the most"`, so a future prose mention would
   silently reroute them. Now a shared `section_body()` helper anchors on the
   `^### \d+\.` heading regex.
5. **The survey bullet stated its rationale three times** in a file loaded into
   context on every invocation. Cut ~3 lines of restatement, keeping the
   instruction; the *why* stays in the Judgment bullet, which is its right home.
6. **Frontmatter `description` was edited without re-wrapping**, leaving a
   37-char line among ~79-char neighbours. Re-wrapped. (Noted for the future:
   the folded description is ~940 chars against the 1024 ceiling enforced at
   `scripts/install_contract.py:661` — roughly one clause of headroom left.)
7. **AC3 carried its own amendment history inside the requirement.** Trimmed to
   the two load-bearing sentences; the story moved to the deviation log, where
   the slice already had an empty section waiting for it.

## Recorded rather than changed

The two deviation-log candidates it raised — AC4's `origin/<trunk>` phrasing not
literally describing the fixed candidate list, and `_in_flight_base` returning
the first *resolvable* candidate rather than a true fork point — are entries 4
and 5 of the deviation log.

## Its calibration notes, kept

It called the aggregate-deadline design the right fix anchored to a real cited
constraint; the `origin/HEAD` verify-don't-trust treatment genuinely
thoughtful; `_in_flight_summary`'s five early returns the right shape ("do not
restructure it"); the shell-`case` stubs the least clever way to get a
partially-slow git; and the timing margins wide enough not to flake. It judged
the slice right-sized at ~55 lines of production code and ~240 of test, and
confirmed the code/prose split is bound by an argument the spec makes
explicitly rather than by convenience.
