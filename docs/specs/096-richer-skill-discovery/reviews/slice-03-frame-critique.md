---
slice: 096-03 — enumerate-and-select
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer subagent (frame-critique pass)
reviewed_at: 2026-07-28T02:09:17Z
prompt_source: review.py frame-critique
---

Frame-critique of 096-03 returned **needs-changes**.

**Primary.** The slice assumes Python's enumerated candidate set is the set the
orchestrator actually selects from — the premise that lets 096-05 record it as
"shown and declined". Nothing in the slice creates that channel, and three
artifacts indicate the substrate is the orchestrator's *ambient* skill listing
instead:

- No AC wires enumeration to the orchestrator. AC1 defines a helper's return
  value; AC6 defines *prose* telling the orchestrator to pick; AC2 makes
  `--richer-skill` required on the pass commands, which run *after* the pick.
  There is no subcommand, no output contract, no "run enumeration first" step.
- `adr-0039:159-161` justifies Option D as costing "~nothing in orchestrator
  context (spec 057) **since the descriptions are already loaded**" — ambient
  context is the substrate, and under spec-057 turn discipline the orchestrator
  has a standing incentive to skip an extra Bash turn asked for only in prose.
- `adr-0039:390-394` says a failed OQ6 makes Codex zero-config "structurally
  impossible" — true only if enumerator output never reaches a model.
- `slice-04:60` has the probe ask Codex to pick "**without** naming the skills
  in the prompt."

Consequence: AC1's enumerator ships with no runtime consumer, and 096-05's
calibrated anomaly measures a set the orchestrator never saw. Substituting the
nomination list is what `adr-0039:296-307` forbids, so the "silent
NON-selection" kill criterion (`adr-0039:489-498`) becomes undetectable by
construction. An orchestrator pick that enumeration never nominated is an
unhandled state (AC3 validates resolvability, not membership).

Fix now: either declare an explicit channel (`review.py candidates <category>`
whose printed list is the substrate, echoed back by the pass invocation) or drop
AC1 and record what the orchestrator reports from ambient context. The slice
currently assumes both.

**Secondary.** AC5 deletes `detect_richer_skill` (`review.py:560-581` — a
shipped, deterministic, working user-scope pickup) in the same slice that
introduces the heuristic replacement, while AC3 defers all recording to 096-05.
For the duration of 096-03, any CI or non-orchestrated run on a machine where
today's exact-name deferral works silently drops to jig's baseline — the
reported bug's terminal state — with no evidence trail. Contradicts
`adr-0039:496-498` ("the anomaly state must ship in slice 1 rather than be
deferred to a later observability pass").
