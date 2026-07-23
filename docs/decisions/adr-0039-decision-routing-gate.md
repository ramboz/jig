---
status: Proposed
dependencies: [adr-0011, adr-0031]
last_verified: 2026-07-22
frame_review: true
---

# ADR-0039: Enforce ADR-vs-lightweight routing with a two-signal deliberateness gate

## Status

Proposed (2026-07-22)

## Context

[ADR-0031](adr-0031-load-bearing-decision-adr-trigger.md) fixed the *wording* of
the Architectural Decision Record (ADR) trigger and single-sourced it as
`decisions.py:ADR_TRIGGER`. Four consumer sites quote it verbatim and
`test_decisions.py::SingleSourceDriftTests` fails CI if any of them drifts.

**Nothing evaluates a decision against it.** `decisions.py` exposes one
subcommand, `add-lightweight`, which reads four text fields and appends;
`ADR_TRIGGER` is a string it ships to a template, never applied to an argument.
The routing judgement happens once, in the agent's head, at the moment it picks
which command to type — and the command name presupposes the answer.
[#121](https://github.com/ramboz/jig/issues/121) reports the consequence: a
decision recorded as lightweight, later re-priced by an adversarial review into a
module-boundary change with rejected alternatives, revised **by hand**, and never
re-routed. The revised entry lists its rejected alternatives while the rubric's
lightweight criterion reads *"with no real rejected alternatives"* — the record
disqualified itself in the same file whose header states the rule.

This ADR decides the **shape of the check**, not the rule. Two forces pull
against each other:

- A check that under-fires is the status quo with extra code.
- A check that over-fires trains operators to bypass it, which is worse than no
  check — a gate people reflexively wave through has negative value, because it
  also launders the cases it *should* have caught.

That tension is sharp here because the rubric sends UI-copy decisions to the
lightweight home **by name** ("UI string or translation choices"), and those
decisions routinely contain rejected-alternative language. jig's own illustrative
entry is *"Onboarding CTA copy: 'Get started' over 'Sign up'"* — a rejected
alternative in the plainest sense, and correctly filed as lightweight.

## Decision Options Considered

### Option A: Flat keyword list — flag on any ADR-ish marker

Scan the text for `rejected`, `instead of`, `alternative`, `module`, `boundary`,
`native`, `protocol`, … and flag on any hit.

- **Pros:** Trivial to implement and to explain. This is what #121 proposes
  ("Scan the `--decision` / `--context` text for markers").
- **Cons:** Fires on jig's own illustrative entry, and on the entire class the
  rubric explicitly routes to the lightweight home. Every UI-copy decision would
  arrive at the gate, and the escape hatch would become the normal path within a
  week — at which point the gate is training operators to ignore it.

### Option B: Two-signal rule derived from the rubric's own two criteria

Read the rubric as it is actually written — **two** criteria, of different
shapes:

| # | Criterion (verbatim) | Condition |
|---|---|---|
| (a) | "A load-bearing design choice **with rejected alternatives**…" | conjunction |
| (b) | "Also: any change to a **module boundary, public contract, or cross-cutting policy**." | unconditional |

Carry three marker groups — `BOUNDARY`, `ALTERNATIVES`, `LOAD_BEARING` — and
flag iff `BOUNDARY`, or (`ALTERNATIVES` **and** `LOAD_BEARING`).

- **Pros:** The precision comes from the rule itself rather than from tuning. The
  rubric's own hedge — *"no **real** rejected alternatives"* — is exactly the
  distinction criterion (a) encodes, so implementing (a) as a conjunction is
  transcription, not invention. Passes both cases that matter: the illustrative
  UI-copy entry does not flag; #121's reported case does.
- **Cons:** Three lists to maintain instead of one, and the conjunction can be
  defeated by a load-bearing decision described in plain language that names no
  marker. It reduces false positives at some cost in recall.

### Option C: Ask a model to judge each decision

Send the text to a judgement pass instead of matching markers.

- **Pros:** Catches the plain-language cases Option B misses.
- **Cons:** Puts a non-deterministic call on a tier-0 helper's write path, in a
  repo where the helper is deliberately self-contained and importable. It would
  also make `add-lightweight` fail differently depending on host, network, and
  model version. jig already has a judgement surface for this — the memory-sync
  session-end prompt — and it is *upstream* of the helper, where a model is
  already in the loop.

### Option D: Warn without refusing

Print the flag, append anyway.

- **Pros:** No false-positive cost at all; nothing is ever blocked.
- **Cons:** The failure #121 reports is precisely that a routing signal existed
  in prose and nobody acted on it. A warning on stdout, in a batch of four
  recorded decisions, reproduces that failure with a new coat of paint.

## Recommended Decision

**Option B**, shipped in jig's established gate shape
([ADR-0011](adr-0011-spec-gate-model.md), [spec 078](../specs/078-gate-bypass-telemetry/spec.md)):
on by default, refuses with the matched groups and phrases named, points at the
ADR route, and carries two escapes — `--confirm-lightweight` for the operator who
has read the flag and disagrees, and `JIG_DECISION_ROUTING_GATE=0` for the
operator who wants the check off, instrumented via `emit_gate_bypass`.

The gate is a **deliberateness** signal, not an authority. It cannot know whether
a decision is load-bearing; it can guarantee the question is asked at the moment
the record is written, and again whenever it is revised. That is the whole of
what #121 asks for.

Option C is not rejected on merit — it is rejected *here*. The judgement surface
belongs upstream, in the prompt, where a model is already reading the
conversation; the helper's job is to be the deterministic floor under it.

## Consequences

**Becomes easier:**
- A misrouted decision is caught at the moment of writing, by the tool, rather
  than by a reviewer who happens to reread the file later.
- The evaluator is a pure importable function, so the revision path (096-02) and
  the sweep over existing records (096-04) reuse one rule instead of three
  copies — the same single-sourcing `SingleSourceDriftTests` protects for the
  sentence, now extended to its application.
- `ADR_TRIGGER` stops being decorative. Its four verbatim quotations are now
  backed by behaviour on at least one surface.

**Becomes harder:**
- `add-lightweight` can now fail on input it used to accept. Every documented
  command block keeps working, but an agent scripting the helper must handle a
  non-zero exit it did not have to before.
- The three marker groups are a maintenance surface, and a genuinely load-bearing
  decision written in plain language still slips through. The gate raises the
  floor; it does not close the hole.
- A false positive costs the operator one flag and one re-run with
  `--confirm-lightweight`. Accepted deliberately — see Kill criteria.

## Assumptions

None unverified. Probed on this worktree at `fd7115a`:

- `ADR_TRIGGER` is defined at `decisions.py:41-45` and read by no other line in
  the file — the constant is rendered, never applied.
- `add-lightweight` is the only subcommand (`decisions.py:313-332`, one
  `sub.add_parser` call; confirmed via `--help`).
- `_common.parsing.env_gate_enabled` (`:88`) and
  `_common.gate_telemetry.emit_gate_bypass` (`:24`) exist and are the shared
  backing for `JIG_REVIEW_EVIDENCE_GATE` / `JIG_SCAFFOLD_PRECONDITION`.
- jig's own `lightweight-decisions.md` holds exactly one `### ` entry outside the
  `## Template` fence, and it is a self-described illustrative example
  (`:51-55`). It is the false-positive corpus AC3 of slice 096-01 asserts
  against.

## Kill criteria

- **Bypass rate.** If `gate-stats` shows `JIG_DECISION_ROUTING_GATE=0` or
  `--confirm-lightweight` on a majority of recorded decisions, the gate is
  over-firing and Option B's marker groups are wrong. Narrow them or withdraw
  the gate — do not leave a gate everyone waves through.
- **Zero catch rate.** If no real misrouting is caught over a meaningful sample
  while misroutings keep being found by review, the conjunction in criterion (a)
  is too strict and the recall cost of Option B over Option A was mispriced.

## Open questions

- **Should the memory-sync session-end prompt call the evaluator?** It is the
  upstream judgement surface, and running the deterministic check alongside the
  model's judgement would catch a decision the model waved through. Out of scope
  for spec 096, which changes helper behaviour only; worth asking once the gate
  has a bypass-rate signal to argue from.
- **Should `lint` (096-04) become a gate rather than a report?** Deliberately
  left as a report: jig has no corpus of real lightweight entries yet — its own
  file has zero — so there is no evidence base for making it blocking.
