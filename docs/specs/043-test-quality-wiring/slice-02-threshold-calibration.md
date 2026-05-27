---
status: DONE
dependencies: [043-01]
last_verified: 2026-05-27
kind: spike
---

## Slice 043-02 — threshold-calibration (spike)

**Question:** Are quality.py's four threshold constants
(`THR_PER_FILE_FLOOD_MAX=100`, `THR_PER_CODE_FILE_FLOOD=30`,
`THR_ASSERTION_THIN=1.5`, `THR_MOCK_HEAVY=5.0`) well-calibrated against
jig's actual diffs, or do they need tuning before the snapshot starts
shaping reviewer verdicts in slice 043-03?

**Time-box:** 2 hours.

**Findings:**

**Method.** Sampled the 25 most recent `feat(...): NNN-NN …`
commits on `main` (slice-implementation commits, excluding pure
spec-reservation and chore commits). For each: `git show <sha> |
python3 skills/tdd-loop/quality.py --diff-file /dev/stdin`. Captured
signals + the four key metrics. Cross-checked each fire against the
underlying diff to judge whether the signal was warranted.

**Fire rate (pre-tuning).** 3 fires / 25 samples = 12% fire rate; all
3 false positives by retrospective judgment.

**Sample table** (signals: `flood / thin / mock`; densities are
assertion-per-test / mock-per-test; `it`/`cf`/`max-pf` =
new-it-blocks / new-code-files / max-it-per-file):

| # | SHA | Slice | flood | thin | mock | a-dens | m-dens | it | cf | max-pf |
|--:|---|---|:-:|:-:|:-:|--:|--:|--:|--:|--:|
| 1 | 7622869 | 035-01 fixture-exclusion | – | – | – | 2.00 | 0.00 | 4 | 2 | 2 |
| 2 | d1dd9ec | 032-02 scaffold sentinel | – | – | – | 3.67 | 0.00 | 3 | 1 | 3 |
| 3 | 1f2253b | 032-01 atomic_write_text | – | – | – | 2.17 | 0.33 | 6 | 6 | 5 |
| 4 | 1e04883 | 005-02 supersede | – | – | – | 2.10 | 0.00 | 29 | 1 | 29 |
| 5 | 1c794ab | 005-03 boundary-change-detection | – | – | – | 2.41 | 0.00 | 34 | 2 | 34 |
| 6 | 1ec8501 | 028-03 status-board race | – | – | – | 1.67 | 0.67 | 9 | 1 | 9 |
| 7 | d1b4b09 | 028-02 inbox append-lock | – | – | – | 2.93 | 0.00 | 15 | 1 | 15 |
| 8 | 42a40fc | 028-01 adr-numbering | – | – | – | 2.73 | 1.00 | 22 | 1 | 22 |
| 9 | b3a72d0 | 026-01 byte-based context | – | – | – | 2.55 | 0.00 | 29 | 3 | 17 |
| 10 | b63d183 | 027-01 post-edit verify | – | – | – | 1.57 | 0.00 | 23 | 1 | 21 |
| 11 | 4831112 | 031-02 arch-review wire | – | – | – | 1.78 | 0.00 | 27 | 2 | 17 |
| 12 | b353434 | 031-01 pr-review wire | – | – | – | 1.65 | 0.00 | 20 | 1 | 20 |
| 13 | 6b7b36d | 029-02 status-board spike | – | – | – | 3.29 | 0.00 | 14 | 1 | 14 |
| 14 | 9a57fe7 | 029-01 kind: spike validation | **flood** | – | – | 1.94 | 0.00 | 34 | 1 | 16 |
| 15 | 3b9aca9 | 024-01 analyze skill | – | – | – | 1.62 | 0.00 | 45 | 2 | 38 |
| 16 | 77fc3d3 | 023-01 clarify | – | **thin** | – | 1.47 | 0.00 | 30 | 1 | 30 |
| 17 | dedbd74 | 021-01 copy-machinery | – | – | – | 2.71 | 0.00 | 14 | 2 | 14 |
| 18 | bfa4e17 | 020-01 slice-to-spec | – | – | – | 2.57 | 0.00 | 7 | 0 | 7 |
| 19 | 692c7d1 | 019-01 --no-deviation-log | – | – | – | 2.60 | 0.60 | 5 | 1 | 5 |
| 20 | 62f5471 | 018-04 split-slices | – | – | – | 3.77 | 0.00 | 13 | 1 | 13 |
| 21 | 7300743 | 018-03 file-per-slice scaffold | – | – | – | 2.80 | 0.80 | 5 | 1 | 5 |
| 22 | 057afe7 | 018-02 caller-recognition | – | – | – | 2.41 | 0.00 | 17 | 5 | 8 |
| 23 | 86d30e0 | 018-01 parser-foundation | – | – | – | 1.80 | 0.00 | 15 | 2 | 15 |
| 24 | 6db1c8c | 017-03 re-run protocol | – | – | – | 1.14 | 0.00 | 14 | 0 | 14 |
| 25 | bad832f | 017-02 vision-elicitation | – | **thin** | – | 1.22 | 0.00 | 36 | 0 | 36 |

**Fire analysis.** All three pre-tuning fires were false positives:

1. **9a57fe7 (029-01)** fired `per-file-flood` via the ratio branch
   (34 it-blocks / 1 code file = 34, over the 30 threshold).
   Retrospective: 16 + 5 + 13 well-named single-concept tests across
   three test files covering an enum (`kind`) + body-shape validator.
   Legitimate enum-coverage explosion, not a flood.
2. **77fc3d3 (023-01 clarify)** fired `assertion-thin` at density
   1.47. Retrospective: 30 SKILL.md surface tests, each checking one
   specific structural property. Focused single-concept tests, not
   thinness.
3. **bad832f (017-02 vision-elicitation)** fired `assertion-thin` at
   density 1.22. Same shape as #2 — 36 SKILL.md surface tests.

**Distribution patterns.**

- *assertion-density* sorted: 1.14, 1.22, 1.47, 1.57, 1.62, 1.65,
  1.67, 1.78, 1.80, 1.94, 2.00, 2.10, 2.17, 2.41, 2.41, 2.55, 2.57,
  2.60, 2.71, 2.73, 2.80, 2.93, 3.29, 3.67, 3.77 — median ≈ 2.17. The
  pre-tuning 1.5 threshold catches the bottom ~24% of jig slices,
  which span well-designed focused-surface-test patterns.
- *mock-density* heavily skews toward 0.00 (jig is stdlib + subprocess
  flavoured). Non-zero observations: 0.33, 0.60, 0.67, 0.80, 1.00.
  Max ≈ 1/5 of the 5.0 threshold — no fires possible at current
  sample size.
- *per-code-file ratio*: highest observed = 34 (#14). Pre-tuning
  threshold 30 was inside the normal-coverage range.

**Tuning decision.** Two thresholds tuned to silence the false
positives without losing genuine-problem detection:

| Constant | Old | New | Justification |
|---|---|---|---|
| `THR_ASSERTION_THIN` | 1.5 | **1.0** | 1.5 fires on focused-single-concept tests (jig style). 1.0 fires only when the average drops below 1 — i.e., *some tests have zero assertions*, the case the signal is meant to catch. Silences both jig fires (#16, #25) while preserving the real-thinness detector. |
| `THR_PER_CODE_FILE_FLOOD` | 30 | **50** | 30 caught a 34-test legitimate enum-coverage slice (#14). 50 reserves the signal for diffs where one new code file gets ≥50 tests — genuinely unusual. |
| `THR_PER_FILE_FLOOD_MAX` | 100 | 100 | No data points near it; kept as backstop. |
| `THR_MOCK_HEAVY` | 5.0 | 5.0 | Zero fires in sample (max observed = 1.0). Kept as cross-language insurance — jig doesn't mock, but JS / Java extensions in slice 043-03 may. |

**Post-tuning verification.** Re-ran quality.py against the three
former-fire SHAs:

```
9a57fe7 → per-file-flood: false  assertion-thin: false  mock-heavy: false
77fc3d3 → per-file-flood: false  assertion-thin: false  mock-heavy: false
bad832f → per-file-flood: false  assertion-thin: false  mock-heavy: false
```

All three now silent. The remaining 22 samples were already silent
pre-tuning, so the tuning is monotone w.r.t. this sample (no new
fires introduced).

**Outcome:** `thresholds tuned (assertion-thin: 1.5 → 1.0;
per-code-file-flood: 30 → 50); slice 043-03 unblocked`. Constants
edited in [skills/tdd-loop/quality.py](../../../skills/tdd-loop/quality.py),
two affected tests in [skills/tdd-loop/test_quality.py](../../../skills/tdd-loop/test_quality.py)
adjusted to match (assertion-thin firing test now uses density 0.88
with three zero-assertion tests; ratio test now uses 51/1 vs 50/1).
Full 35-test suite green.

**DoR:**
- ✅ Slice 043-01 DONE — quality.py's signal logic must be tested
  before calibration data is trustworthy.
- ✅ Repo has at least ~15 merged slices to sample from (currently
  well past 30, satisfied).

**Acceptance Criteria:**

1. **Calibration data captured.** A table or list in the Findings
   block records, for each sampled slice: SHA, signal triad
   (`per-file-flood` / `assertion-thin` / `mock-heavy`), key
   metrics (assertion-density, mock-density, test-to-code-ratio),
   and a one-line retrospective judgment ("reviewer flagged
   test-thinness" / "no test-quality concerns raised" / etc.).
2. **Threshold decision is justified.** The Outcome line links each
   tuned constant (if any) to specific data rows that motivated the
   change. "Tuned because it felt high" is not acceptable; "tuned
   because 7 of 20 fired with no reviewer concern, suggesting the
   threshold catches noise" is.
3. **If thresholds change, quality.py and test_quality.py are
   updated in the same commit** so the test suite reflects the new
   values. (Signal-firing tests from 043-01 may need fixture
   adjustment.)

**DoD:**
- [x] Findings + Outcome filled in this slice body (per
      `kind: spike` shape).
- [x] If thresholds changed: tests adjusted, full suite green.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed (spike rigor: was the method
      sound? are the conclusions supported by the data?).
- [x] Deviation log produced under this slice heading (covers any
      mid-spike pivots).
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`
      (🔬 prefix renders on this row per spec 029).
- [x] No `CLAUDE.md` Skills-table change.

**Anti-horizontal-phasing check:** The spike reduces an unknown
(are the thresholds load-bearing?) that gates slice 043-03's
trustworthiness claim. End-to-end value: a maintainer can read this
slice and answer "should I trust quality.py's signals?" with data,
not intuition.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Outcome was `tune`, not `confirm` or `abandon`.** Anticipated by
   the spec's Outcome enum — no methodological deviation. Two
   constants moved (assertion-thin 1.5 → 1.0; per-code-file-flood
   30 → 50). Two constants explicitly kept (per-file-flood-max 100;
   mock-heavy 5.0) as cross-language backstops.

2. **Sample size 25, not 20.** Spec said "~20 merged slice diffs."
   Used 25 to give the assertion-density distribution a slightly
   wider tail; no methodological cost. The 25 commits span 017-02
   through 035-01 — the full reachable range of slice-implementation
   commits at this point in main's history.

3. **Reviewer findings folded back in.** Two craft-pass nits were
   addressed inline before transitioning to REVIEWED:
   - `test_assertion_thin_requires_min_tests` was rewritten from
     density 0.0 / 3 tests (min-test-gate only) to density 0.9 /
     10 tests, so the test now couples to BOTH the min-test gate
     AND the 1.0 threshold edge. A future regression that drops
     the threshold to 0.5 would now break this test, where the
     previous shape would have remained green.
   - `quality.py`'s threshold-constants comment block now carries
     an explicit "Python-only sample" caveat pointing forward to
     slice 043-03's polyglot-extension calibration responsibility.

4. **Reviewer nit deferred (intentional non-edit).** Both reviewers
   noted that
   [slice-01-quality-test-coverage.md](slice-01-quality-test-coverage.md)
   AC1 still references "ratio 31, over the 30 threshold" — i.e.,
   pre-spike thresholds. Slice 043-01 is DONE; spec-text in DONE
   slices is frozen by convention. The AC remains historically
   accurate ("over the threshold *at the time*"); the live
   thresholds and tests reflect the post-spike values. Logging here
   instead of retroactively editing 043-01.

5. **No doc updates beyond this slice body.** No new skill, no new
   contract surface, no architectural change. CLAUDE.md Skills
   table unchanged. `docs/refinement-todo.md` unchanged (no
   decisions deferred — the polyglot caveat is the next slice's
   problem, not a refinement-todo entry). Status-board regen
   happens at close-out, with the 🔬 prefix per spec 029.

6. **Plan adherence.** The expected method (sample, run, tabulate,
   cross-check fires, cross-check non-fires for missed concerns,
   examine distributions) was followed step-by-step. No mid-spike
   pivot. Time-box of 2 hours was respected.
