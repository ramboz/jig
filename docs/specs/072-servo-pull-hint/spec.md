---
status: DONE
skill: slice-land
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 072: slice-land → servo pull-hint

## Overview

[servo](https://github.com/ramboz/servo) — jig's autonomous sibling
plugin — documents, in its `README.md`, that the jig↔servo coupling is
already complete:

> Jig's `slice-land prepare` emits soft pull-hints for servo artifacts
> when servo-style infrastructure is missing — **that's the entirety of
> the coupling.**

**jig never built it.** A grep of `skills/slice-land/` finds zero servo
references; `land.py prepare` emits a fixed four-check readiness report
plus mode next-steps and nothing else. [ADR-0022](../../decisions/adr-0022-pluggable-oracle-boundary.md)
records the same fact in its own Assumptions
(*"the jig→servo coupling is NOT yet implemented … the jig→servo
pull-hint is a planned reciprocal described by servo's README, and
building it is part of activating this ADR"*) and lists **"Build the
jig→servo `slice-land` pull-hint"** as a discrete deferred dependency.

So servo's documented coupling is a **phantom**: the present-tense claim
describes behaviour that doesn't exist (servo's own `ADR-0004` is more
honest — it says jig *"could one day"* emit such hints). This spec builds
the reciprocal — a **soft, advisory, filesystem-probed hint** in
`land.py prepare`'s output — which makes servo's README true and points
at servo's *current* runtime shape.

It is the **loosest possible integration**: advisory text only, driven by
a `stat` of the target's `.servo/` directory. jig runs no servo command,
reads no exit code, derives no score, and gains no runtime coupling — the
same "as thin as possible" posture [spec 071](../071-design-review-pass/spec.md)
just took for the `design_review` pass. ADR-0022's tight Option-D
oracle-binding (§2–§5: recognizing `servo` as an oracle value in
`bug.py`/`refactor.py` records) **stays PARKED**; this builds only the
separable pull-hint dependency.

## Why now

- **A live cross-repo doc drift.** servo's README asserts a coupling jig
  doesn't implement. Every reader who trusts "that's the entirety of the
  coupling" is misled. The drift resolves one of two ways: jig ships the
  hint (this spec), or servo softens its README to "planned." Shipping is
  the higher-value resolution — it delivers the reciprocal servo designed
  for, instead of just downgrading a doc.
- **The artifact shape is now stable and current.** servo's
  [`ADR-0008`](https://github.com/ramboz/servo) (*Rebase agent-loop
  orchestration onto Claude Code autonomy primitives — /goal, /background,
  Routines*) was **Accepted 2026-06-12**; the hand-rolled loop is retired
  (`003-06` /goal-driven loop DONE; `003-08` Routine-ready). A hint built
  now points at the right artifacts and won't immediately rot — this is
  the precondition the originating deferred task named.
- **ADR-0022's re-propose triggers fired.** Its Status gates re-engagement
  on *"(c) servo spec 006 ships"* — servo `006-spec-oracle` is **DONE**
  (dogfooded against jig specs 046/047) — and a built consumer now exists
  (`/servo:design-eval`, servo `ADR-0009` Accepted). Re-engaging the
  *separable* pull-hint is sanctioned; the heavy binding is not (its own
  demand trigger — ≥2 real eval refactors — and its consumers
  `bug.py`/`refactor.py` remain unmet).

## Goals

1. **Emit a soft servo pull-hint in `land.py prepare` output**, driven by
   a filesystem probe of the target's `.servo/` directory. The hint is a
   new advisory section in the readiness report — it never invokes servo
   or any autonomy primitive.
2. **Three-way detection.** (a) servo not present (no `.servo/`, plugin
   not detectable) → **silent** — no servo string at all; (b) servo
   *scaffolded* in the target (`.servo/` present) → point at the current
   artifact shape (slice 072-01); (c) servo *plugin available* but the
   target *unscaffolded* → a gentle one-time `/servo:scaffold-init`
   suggestion (slice 072-02, decision-gated).
3. **Point at servo's current (post-`ADR-0008`) shape** — a `/goal`-driven,
   Routine-triggerable loop and (when one exists) a paused run at
   `.servo/runs/<id>/state.json` to resume — never the retired
   "hand-rolled agent-loop."
4. **Soft, opt-out-able, never-gating.** The hint never changes
   `prepare`'s exit code, never adds a blocker, never converts a pass to a
   fail. A `.jig/no-servo-hint` marker suppresses it (parity with
   `.jig/no-people-md`, spec 050). servo-absent and jig-without-servo stay
   fully intact.
5. **Close the phantom coupling.** Once 072-01 ships, servo's README claim
   is true for the present case; ADR-0022's Scope/Status are updated to
   record the pull-hint dependency as built (not deferred).

## Non-goals

- **No autonomy primitive in jig's flow.** jig does **not** invoke `/goal`,
  `/loop`, `/background`, Routines, or any `servo:*` command. The hint is
  text. jig stays supervised and hook-gated — the boundary that is the
  reason servo is a separate plugin. (This is the hard constraint from the
  originating task.)
- **Not the Option-D oracle-binding.** Recognizing `servo` as an oracle
  value in `bug.py`/`refactor.py` records, reading `gate.py`'s exit code,
  capturing `composite`/`threshold` — all of ADR-0022 §2–§5 — stays
  **PARKED**. This spec is advisory discovery, not verification.
- **Not the spec DONE-gate servo integration.** That shipped separately as
  spec 071's attest-only `design_review` review pass (no servo coupling).
  This spec does not touch the review-evidence rails.
- **No advertising servo to non-servo users.** A jig user who has never
  installed servo never sees a servo mention (Goal 2a). The hint is for
  people who already chose servo, not a funnel into autonomy.
- **Not a `scaffold.json` field, not a hook.** Detection is inline in
  `land.py prepare`; no new config surface, no new event.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **servo's per-project layout.** servo's durable manifest is
  `.servo/install.json` (servo `architecture.md`: "the analog of jig's
  `scaffold.json`"); per-run state is `.servo/runs/<run-id>/state.json`
  (servo `ADR-0004`); the heartbeat triage inbox is
  `.servo/triage/inbox.jsonl` (servo spec 011). Verified via the servo
  digest this session + ADR-0022's own (already-grounded) Assumptions.
- **servo's runtime rebased onto /goal+/background+Routines.** servo
  `ADR-0008` Accepted 2026-06-12; `003-06` (/goal-driven loop) and
  `003-08` (detach + Routine-ready) landed. So "point at the current
  artifact shape" has a real, current target. Verified by reading the
  ADR-0008 header + servo's commit log this session.
- **`land.py prepare` exposes an append point and is exit-code-stable.**
  `prepare()` assembles `parts` then joins; a new advisory section appends
  without disturbing the `has_blocker` exit logic. Verified by reading
  `skills/slice-land/land.py` (the `prepare` render pipeline).
- **[RISKY — load-bearing for 072-02 only] servo *plugin* availability is
  detectable from `land.py`.** The `.servo/` *project* probe is reliable
  (a filesystem `stat`). Detecting whether the servo *plugin* is installed
  (to satisfy Goal 2c without advertising to non-servo users) is **not yet
  proven** — `CLAUDE_PLUGIN_ROOT` points at jig's own plugin dir, and the
  sibling-plugin layout is install-method-dependent. 072-02 carries this
  risk (`frame_review: true`); its conservative fallback is "undetectable
  → silent."

## Open questions

1. **ADR-0022 §5 says *"absent → no servo mention"*; servo's README says
   *emit when infrastructure is missing*.** These conflict for the
   slice-land surface. **Lean (reconciles both):** fire the
   "missing-infra" suggestion (072-02) **only when the servo plugin is
   detectably installed** — so a user with no servo sees nothing (§5
   honored, supervised-default boundary honored), while a servo user who
   hasn't scaffolded *this* project gets the gentle nudge (README honored).
   **Alternative if plugin-detection proves unreliable:** drop 072-02 and
   instead soften servo's README to "planned." Decide at READY_FOR_REVIEW.
   **→ RESOLVED (human, 2026-06-15): YES — nudge when servo is available
   and the project is unscaffolded.** The §5 reversal for the slice-land
   surface is approved *in principle*. But the "only when the plugin is
   detectably installed" mechanism is unworkable (Q2 spike) — so the nudge
   is reconciled with §5 via a **reciprocal servo-side "available"
   breadcrumb** (a host-agnostic marker servo writes; jig reads it), not
   plugin auto-detection.
2. **servo-plugin detection mechanism** (the Assumptions risk). Probe a
   sibling of `CLAUDE_PLUGIN_ROOT`? Read a marketplace manifest? If no
   reliable signal exists, 072-02's fallback is silence. May warrant a
   `kind: spike` inside 072-02.
   **→ RESOLVED by spike [072-03](slice-03-servo-plugin-detection-spike.md)
   (2026-06-15): NO-GO on plugin auto-detection.** No signal is at once
   documented/supported, install-method-robust, host-agnostic,
   subprocess-free, and boundary-respecting: `installed_plugins.json` is an
   undocumented internal that misses local-clone servo (incl. the user's
   own setup), `CLAUDE_PLUGIN_ROOT` names only jig's own dir,
   `claude plugin list` is a subprocess (AC5), and a `plugin.json` dependency
   would force servo on every jig user. **Chosen direction (human): a
   reciprocal servo-side breadcrumb** — servo writes a host-agnostic
   "available" marker that jig's `land.py` reads (servo-available AND no
   project `.servo/` → nudge). This is a **cross-repo dependency** (a
   reciprocal servo-side ADR, already named in ADR-0022 Scope); 072-02 is
   reshaped around it and **blocked** until servo emits the marker.
3. **Nag-avoidance for 072-02.** A suggestion on *every* land would be
   noise. Lean: opt-out marker + fire only when the slice has real tests
   (skip doc-only slices, mirroring `prepare`'s own test-warn path).
4. **Hint placement + heading.** A `## servo` section after Next-steps?
   A one-line note under Readiness? Lean: a distinct trailing advisory
   section so it's visually separable from the gating checks. Resolve in
   072-01 implementation.

## Decomposition

SPIDR **Rules / Path** split — the detection states differ in both their
governing decision and their risk, so they slice cleanly along the
present-vs-absent path.

- **072-01** is the ADR-0022-§5-aligned, low-risk core (mention servo only
  when its infra is *present*) and is implementation-ready. It alone makes
  servo's README claim true for the present case and closes the phantom
  coupling. **DONE (2026-06-15).**
- **072-03** (`kind: spike`) settled Q2: can `land.py` reliably detect the
  servo *plugin*? **NO-GO** — see the spike's Outcome. **DONE (2026-06-15).**
- **072-02** is the "missing-infra" suggestion. Q1 approved the nudge, but
  the spike disproved plugin auto-detection — so 072-02 is **reshaped** off
  a reciprocal servo-side "available" breadcrumb (host-agnostic, servo
  writes / jig reads) and is **blocked on that cross-repo contract** (a
  reciprocal servo-side ADR). Stays DRAFT until servo emits the marker;
  retains `frame_review: true`.

## Slices

- [072-01 — present-infra-hint](slice-01-present-infra-hint.md) — **DONE**
- [072-03 — servo-plugin-detection-spike](slice-03-servo-plugin-detection-spike.md) — 🔬 **DONE** (Q2 → NO-GO on plugin auto-detection; direction: reciprocal servo signal)
- [072-02 — unscaffolded-suggestion](slice-02-unscaffolded-suggestion.md) — DRAFT (reshaped off a reciprocal servo breadcrumb; blocked on the cross-repo servo-side contract)

## References

- **servo README** — the phantom claim ("that's the entirety of the
  coupling") this spec makes true.
- **servo `ADR-0008`** — the agent-loop rebase onto /goal+/background+
  Routines (Accepted 2026-06-12); the current artifact shape the hint
  points at.
- **[ADR-0022](../../decisions/adr-0022-pluggable-oracle-boundary.md)** —
  governing boundary. This builds its separable "slice-land pull-hint"
  Scope dependency; its Option-D oracle-binding (§2–§5) stays PARKED. §5's
  "absent → no mention" is the source of Open Question 1.
- **[Spec 071](../071-design-review-pass/spec.md)** — the loosest-
  integration precedent (attest-only `design_review`, no servo coupling).
  This spec is even looser (advisory text, no review-evidence artifact).
- **Spec 050** — `.jig/no-people-md` opt-out-marker precedent reused as
  `.jig/no-servo-hint`.
- **Originating task** — the deferred "reconcile the soft pull-hints
  slice-land emits when servo infra is missing, point at the new artifact
  shape if servo rebased onto /goal+Routines" item. Its premise (hints
  exist, just need repointing) was inverted: the hints never existed; this
  spec builds them.
