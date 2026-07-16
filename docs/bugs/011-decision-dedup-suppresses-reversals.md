---
status: ROOT_CAUSED
tier: gnarly
severity: medium
regression_test:
main_repro_checked_at: 2026-07-16
main_repro_ref: origin/main@91427b4
main_repro_result: reproduces
red_confirmed_at:
green_confirmed_at:
fix_class:
security_surface: false
escalated_to:
---

# Bug 011: decision-dedup-suppresses-reversals

Reported as [issue #109](https://github.com/ramboz/jig/issues/109) (finding 2). Diagnose-only:
this record stops at ROOT_CAUSED because the fix is a design choice for the maintainer — see
`## Fix class`. Finding 1 of the same issue (no backfill seeds
`docs/decisions/lightweight-decisions.md`) is a separate defect and is not covered here.

Owner check (per `skills/bug-fix/SKILL.md`, "scan for an overlapping active slice"): spec 083
`lightweight-decision-records` owns this subsystem and slice 083-04 delivered
`decision_scan.py` + the Stop hook. Spec 083 is IN_PROGRESS, but its only open slice — 083-08 —
is Codex host-parity validation and does **not** own this defect. No second owner is created.

## Symptom

A Tier-2 user correction that *reverses* an already-recorded decision is silently dropped by
`dedup()` and never reaches the owner. The Stop hook's triage nudge omits it entirely, and
nothing anywhere distinguishes "no candidate decisions found" from "a candidate was found and
suppressed" — suppression leaves no trace in the nudge, the scratch dir, or any log.

The mechanism is strongest exactly where it is most wrong: the better a decision is recorded,
the more its future reversal overlaps it lexically, and the more reliably it is suppressed.

## Repro

Against jig's own source, with a recorded decision LD-3 in the project's
`docs/decisions/lightweight-decisions.md`:

```bash
cd hooks/scripts
python3 -c "
import sys; sys.path.insert(0,'.')
from lib.decision_scan import dedup
from collections import namedtuple
C=namedtuple('C','tier who confidence quote turn')
recorded=['**Decision:** knob circles fill with var(--surface) not the mockup per-frame hex; the app --border 0.07 alpha light was kept over the mockup 0.09. Scope: Home settings button.']
for q in ['actually make the settings button border 0.09 alpha',
          'the settings icon knob fill should use accent not surface']:
    print('SUPPRESSED' if not dedup([C(2,'user','high',q,1)],recorded) else 'kept', '|', q)
"
```

Observed:

```
SUPPRESSED | actually make the settings button border 0.09 alpha
kept       | the settings icon knob fill should use accent not surface
```

The first quote is a direct reversal of the recorded decision, carries the Tier-2 `actually`
marker, and is dropped.

Note the second line **corrects issue #109 as filed**, which reported both quotes as suppressed.
Only the first reproduces; see `## Evidence`. The correction is posted on the issue.

## Evidence

- **The suppression.** `actually make the settings button border 0.09 alpha` normalizes to 8
  tokens, 6 of which (`0`, `09`, `alpha`, `border`, `button`, `settings`) appear in the recorded
  decision. Containment = 6/8 = **0.75**, over the `_DEDUP_CONTAINMENT = 0.6` threshold
  (`decision_scan.py:55`), so it is dropped at `:201-203`.

- **Not a format problem.** The same two candidates were run against identical LD-3 content
  rendered two ways — jig's own `## Entries` / `### date — title` template shape, and the
  reporting project's hand-rolled markdown table — each split into blocks by the hook's real
  logic (`jig-decision-capture.sh:43-61`):

  ```
  jig block format | SUPPRESSED | 0.75 | actually make the settings button border 0.09 alpha
  jig block format | kept       | 0.56 | the settings icon knob fill should use accent not surface
  project table    | SUPPRESSED | 0.75 | actually make the settings button border 0.09 alpha
  project table    | kept       | 0.56 | the settings icon knob fill should use accent not surface
  ```

  Identical. A correctly-scaffolded, fully compliant jig project has this defect today.

- **The near miss.** The second candidate is also a direct reversal of LD-3, but scores 5/9 =
  **0.556** — `accent`, `icon`, `should` and `use` are absent from the record — and survives by
  0.04. That margin is incidental word choice, not a guard: the defect is unpredictable as well
  as wrong.

- **Reproduces on main.** `hooks/scripts/lib/decision_scan.py` is byte-identical between
  `origin/main@91427b4` and the reported 2.7.0 plugin cache (`diff` clean), so this is not
  already-fixed drift.

## Hypotheses

- [ ] H1: the reporting project's hand-rolled table has no blank lines, so the hook's
  `text.split('\n\n')` collapses the whole table into one large block that over-suppresses —
  falsified by the control experiment above: jig's own block format suppresses identically, and
  unrelated candidates survive either way, because containment is measured over the *candidate's*
  tokens, not the block's.
- [x] H2 (leading): containment is a set intersection over stopword-filtered tokens with no
  notion of negation, polarity or direction, so a reversal — which by construction shares
  component, property and vocabulary with the decision it overturns, differing only in a value or
  a "not" that the token set discards — scores *high* rather than low. Confirmed by the 0.75
  measurement and by `dedup()` carrying no tier floor.

## Root cause

`decision_scan.py:200-202` decides suppression solely on lexical containment:

```python
containment = len(cand_tokens & rec) / len(cand_tokens)
if containment >= _DEDUP_CONTAINMENT:
    suppressed = True
```

Token-set containment measures **topical overlap, not agreement**. It cannot represent the one
thing that matters here — whether the candidate *restates* or *overturns* the record. This is a
design gap, not a tuning error: no value of `_DEDUP_CONTAINMENT` separates the two, because a
reversal is topically closer to its record than an unrelated novel decision is.

Neither existing guard applies:

- `_DEDUP_MIN_TOKENS = 3` (`:59`) only protects very short quotes.
- The hook's per-entry block splitting addresses corpus *size*, and is orthogonal.
- **There is no tier floor.** Tier 2 (`\bactually\b`, `:42`) is documented as precision-first and
  "high confidence" — the class that most reliably means the user is correcting something — yet
  it is discarded by `dedup()` with no appeal.

Scope of the claim, stated precisely: this suppresses reversals that are **lexically
near-identical** to the record, not reversals in general. Issue #109's stronger phrasing
("maximally token-overlapping by construction") overstates it — the second candidate is a
genuine reversal that lands under the threshold.

## Fix class

**Deferred — maintainer decision.** The root cause is proven; the remedy is a design choice with
a real trade-off, so this record stops here rather than pre-empt it. Options, neutrally:

1. **Never dedup Tier-2.** Cheapest and most targeted — `dedup()` already receives `cand.tier`.
   The tier already encodes "the user is correcting something", so overlap with a recorded
   decision is evidence *for* surfacing, not against. **Cost:** the Stop hook fires at every Stop,
   not once per session, so an un-deduppable Tier-2 quote re-surfaces for the rest of the session
   even after the owner records it.
2. **Invert the signal.** High containment + a Tier-2 marker *raises* priority — surface it as
   "this may reverse a recorded decision — confirm" instead of suppressing. Keeps visibility while
   telling the owner it may already be handled; same re-surfacing cost, better framed.
3. **Polarity-aware dedup** — negation / antonym / numeric-literal-mismatch detection. Most
   robust, considerably more work, and arguably *missing behaviour* rather than a defect: if this
   is the chosen direction it should `escalate` to a spec rather than grind through the bug gates.
4. **Log suppressions** somewhere inspectable. Orthogonal and additive — does not fix the drop,
   but removes the silence, and would have made this bug self-reporting.

## Fix

## Already tried

Dead ends from the investigation, recorded so they are not re-walked (from issue #109's own
"What this investigation got wrong along the way"):

- **2026-07-16 — "the table format causes over-suppression".** The hook's own comment warns that
  a large single block over-suppresses, and the reporting project's table has no blank lines, so
  the whole table collapses into one block. Plausible and false; see H1.
- **2026-07-16 — "finding 2 is downstream of finding 1".** The assumption was that a
  non-conforming hand-rolled LD file caused the suppression, so seeding the file correctly would
  fix it. The control experiment disproved this: finding 2 is upstream, general, and independent.

## Regression test

## Proof

## Learning

A dedup guard placed over a high-confidence *correction* signal inverts its own intent. For
restatements, lexical overlap with a recorded decision means "already known — drop". For
reversals, the same overlap means "this contradicts something we committed to — surface it
loudest". Overlap alone cannot tell them apart, so a similarity threshold over a correction
channel will always suppress precisely the decisions that most need to reach the owner.

Generalizable: when a signal's tier already encodes "this contradicts an existing record",
similarity to that record is evidence *for* surfacing, not against.

## Main recheck

- 2026-07-16 - `origin/main@91427b4` -> reproduces: decision_scan.py byte-identical on origin/main@91427b4 and the reported 2.7.0 plugin cache; 'actually make the settings button border 0.09 alpha' (tier 2) suppressed at 0.75 containment against LD-3, in both jig's block format and the reporting project's table format

## Release log

- 2026-07-16 - released claim from claude/bug-109-c7b049: diagnose-only; fix choice deferred to maintainer (see issue #109)
