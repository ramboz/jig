---
status: DRAFT
---

# Spec 043: Test-quality preflight wiring

## Overview

[skills/tdd-loop/quality.py](../../../skills/tdd-loop/quality.py) shipped
in commit [1a0c93e](../../../) as a standalone stdlib-only preflight that
computes deterministic numerical signals from a test diff
(`per-file-flood`, `assertion-thin`, `mock-heavy`) plus a metrics
snapshot (assertion-density, mock-density, test-to-code-ratio, etc.).
The commit's design intent is explicit: *"machine-readable evidence to
anchor on"* — anti-hallucination scaffolding for the post-implementation
review judgment.

The commit ended with: *"Standalone tool — no skill coupling. SKILL.md
mention can land later."* That follow-up never landed. quality.py is
fully orphaned: zero references in [skills/tdd-loop/SKILL.md](../../../skills/tdd-loop/SKILL.md),
[docs/workflow.md](../../workflow.md), [skills/spec-workflow/SKILL.md](../../../skills/spec-workflow/SKILL.md),
[skills/independent-review/SKILL.md](../../../skills/independent-review/SKILL.md),
or [skills/pr-review/SKILL.md](../../../skills/pr-review/SKILL.md).

This spec lands the deferred wiring. Two pieces of preparatory work
come first: (a) the existing 15-test smoke suite has documented gaps
that leave roughly half the signal logic unverified, and (b) the four
threshold constants (`THR_PER_FILE_FLOOD_MAX=100`,
`THR_PER_CODE_FILE_FLOOD=30`, `THR_ASSERTION_THIN=1.5`,
`THR_MOCK_HEAVY=5.0`) were picked on intuition per the file's own
comments. Both must be addressed before we let reviewers anchor on the
output.

## Why now

- **Three external-review specs (035–042) are about to compound this gap.**
  The next-up cluster expands the reviewer-prompt surface area. Wiring
  a deterministic test-quality signal into the existing review prompts
  before that cluster lands means the new prompts inherit it rather than
  needing a retrofit.
- **The standalone tool works on real diffs.** A spot-check against
  commit `1f2253b` (atomic_write_text helper + sweep) produced a sensible
  snapshot: 6 new test blocks, 13 assertions, density 2.17, no signals
  fired. The core math is sound; the wiring is what's missing.
- **The follow-up has been outstanding for the entire 016→042 cluster.**
  quality.py landed somewhere between specs 016 and the current 042 head.
  Every reviewer prompt built in that window could have cited it; none
  did, because nothing wired it.

## Goals

1. **Close the test-coverage gaps in quality.py** before it becomes
   load-bearing. Specifically: `per-file-flood` and `mock-heavy` signal
   firing (currently zero firing tests for two of three signals);
   `count_parametrize_cases` walker edge cases (trailing commas, nested
   tuples, strings with commas, lookahead boundary); `pytest.raises`
   assertion patterns; the `--against` ref code path; malformed diff
   variants (binary, pure rename, mode-only); YAML schema validation
   (currently only `assertIn` substring checks).
2. **Calibrate thresholds against the real corpus** via a time-boxed
   spike. Run quality.py against the last ~20 merged slice diffs; confirm
   that no signal fires on diffs the reviewer would judge as fine, and
   that signals do fire on diffs the reviewer would push back on. Tune
   constants if calibration shows drift; record the calibration data in
   the slice's deviation log.
3. **Wire quality.py into the implementation-review prompt** built by
   [skills/independent-review/review.py](../../../skills/independent-review/review.py).
   Append a `## Test-quality snapshot (deterministic)` section
   containing the YAML output, plus a reviewer instruction to *cite*
   fired signals when raising test-quality findings and to *not* invent
   test-quality concerns when all signals are false. This converts
   reviewer hallucination into either citation or silence.
4. **Add a one-paragraph SKILL.md mention in
   [skills/tdd-loop/SKILL.md](../../../skills/tdd-loop/SKILL.md)** pointing
   at the wiring — quality.py is sibling-to-tdd.py but acts post-loop,
   not in-loop.

## Non-goals

- **pr-review craft-pass wiring.** Deferred to a follow-up spec.
  Compliance pass first; craft pass can adopt the same injection once
  the implementation pass proves the pattern works. Logged in
  [docs/inbox.md](../../inbox.md) for follow-up.
- **arch-review wiring.** Architecture pass is scoped to module
  boundaries and contracts; test-diff signals aren't relevant evidence
  there.
- **TDD inner-loop wiring.** Mid-loop the diff is ephemeral and
  meaningless; injecting signals into tdd.py would also tempt the model
  to dismiss findings ("I'll fix it next iteration") and undermine the
  guardrail framing.
- **Polyglot extension.** quality.py is pytest-focused by design;
  extending to vitest/jest is a separate spec. The YAML schema is
  already language-agnostic to make that future extension trivial.
- **Promoting `assertion-density` / `test-to-code-ratio` to signals.**
  They stay in the metrics block as raw evidence; the reviewer reads
  them as context, not as a binary fire/quiet judgment.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** — Spike | Are the thresholds (100 / 30 / 1.5 / 5.0) calibrated against jig's actual diffs, or hand-picked on intuition? | **Spike** (slice 043-02). File comments admit the constants are intuition. Run against last ~20 merged slice diffs; confirm no false positives + at least one true positive on the assertion-thin / mock-heavy edges. Time-box: 2 hours. Outcome: thresholds confirmed as-is OR tuned with calibration data in deviation log. |
| **P** — Path | Test-hardening first vs. wiring first vs. both together? | **Test-hardening first** (slice 043-01). Wiring quality.py into reviewer prompts before the script's edges are tested would propagate any latent walker bugs into review verdicts. Tests-then-wiring is the safer order. |
| **I** — Interface | Where does the YAML snapshot live in the reviewer prompt? | **Dedicated `## Test-quality snapshot (deterministic)` section** in `build_implementation_prompt`. Mirrors the existing precedent of `_contract_surface_check_block()` and `_principles_check_block()` (slice 022-02 / 024-01) — a named block the reviewer can locate by heading. |
| **D** — Data | What diff is fed to quality.py at review time? | `git diff <merge-base>...HEAD` for the slice branch. review.py already has a `Path` to the spec; the slice branch is the current checkout. The merge-base computation lives in the wiring slice (043-03). |
| **R** — Rules | What does the reviewer DO with the snapshot? | **Cite the signal name when raising a test-quality finding** (so reviewers can audit which findings were anchored on evidence vs. judgment); **do not invent test-quality concerns when all signals are false** (the anti-hallucination lever). Both rules are in the prompt fragment, not in code. |

## Known constraints

- **quality.py is Python-focused.** The path classifier matches
  `test_*.py` / `*_test.py` / `tests/` and the line patterns match
  pytest / unittest. On a vitest / jest project, the snapshot will read
  `applicable: false` with reason `docs-only-or-no-test-or-code-changes`.
  That's acceptable for now (jig itself is pure-Python); the YAML schema
  stays language-agnostic so a polyglot extension can drop in.
- **The snapshot is evidence, not a gate.** Signals don't block the
  review verdict; they shape the reviewer's findings. A reviewer can
  still raise a test-quality finding the script missed (judgment over
  signals) and can still pass a slice that fires a signal if the signal
  is a false positive for that change. The prompt fragment makes this
  precedence explicit.
- **`--against HEAD` is the wrong default for review-time use.** The
  reviewer evaluates the *slice*, not the working tree. The wiring slice
  (043-03) passes `--against <merge-base>` explicitly; the helper's
  HEAD default stays as-is for the TDD-author standalone use case.
- **No retroactive snapshot for already-reviewed slices.** This spec
  wires the snapshot going forward; old slices stay un-snapshotted in
  their existing deviation logs.

---

## Slices

- [043-01 — quality-test-coverage](slice-01-quality-test-coverage.md)
- [043-02 — threshold-calibration (spike)](slice-02-threshold-calibration.md)
- [043-03 — review-prompt-injection](slice-03-review-prompt-injection.md)
