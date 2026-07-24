---
status: Proposed
dependencies: [adr-0011, adr-0014, adr-0015, adr-0033]
last_verified: 2026-07-24
frame_review: true
---

# ADR-0039: Lifecycle entry gate

## Status

Proposed (2026-07-24)

## Context

Every teeth-not-trust gate jig has was built because "the agent will remember"
was not good enough. The review-evidence gate ([ADR-0014](adr-0014-review-evidence-model.md))
exists because remembering to get a review was not good enough; the red-to-green
TDD loop exists because remembering to watch the test fail was not good enough;
the spec gate ([ADR-0011](adr-0011-spec-gate-model.md)) catches the *accidental*
edit to `conventions.md`.

One step is still enforced purely by the agent remembering: **entering the
lifecycle at all.** When the agent edits project source without first claiming a
slice or opening a bug record, nothing downstream can protect the change —
capture, records, review gates, and landing all operate on work that is already
*inside* jig. An ad-hoc edit is not merely unrecorded; it is invisible to every
other mechanism.

This failure mode is measured, not hypothetical.
[#111](https://github.com/ramboz/jig/issues/111) records **11 distinct incidents
over 20 June – 16 July 2026 across four downstream projects** where the agent
hand-edited source outside jig and, when caught, conceded. Those 11 are only the
times the owner noticed; the owner is currently the sole enforcement layer. The
worked example: the project's own `refinement-todo.md` named an owner-tuning
trigger, the trigger fired, the agent edited `--card-cap: 1100px -> 720px`
ad-hoc, and because nothing entered the lifecycle nothing was captured, recorded,
or landed — today the code reads `1100px` again while `refinement-todo.md`
documents a value the owner overruled.

The owner's constitution rule — "every change on this project goes through jig,
never ad-hoc edits" — is exactly the kind of prose rule the other gates were
built to replace.

Two hard constraints come from the downstream owner:

- **No new permission prompts or dialogs.** The owner runs Auto mode
  deliberately. Any teeth must aim at the agent, the way the review-evidence
  gate does — never a modal that interrupts the owner.
- **Fail-open.** Any error in the mechanism must leave the session untouched,
  matching the existing decision hooks.

## Decision Options Considered

### Option A: Keep the prose rule (status quo)

Rely on `CLAUDE.md` / `conventions.md` prose ("every change goes through jig")
plus the agent's attention.

- **Pros:** Zero new machinery.
- **Cons:** This is the mechanism that failed 11 recorded times. It is the exact
  "agent will remember" pattern every other jig gate was built to replace. Not a
  real option — listed to be explicit that the report already falsifies it.

### Option B: Hard block on out-of-lifecycle edits (PreToolUse, exit 2)

A `PreToolUse` hook on `Edit|Write|MultiEdit` refuses the edit (exit 2) whenever
the session is not inside the lifecycle, forcing the agent to claim a slice or
open a bug first.

- **Pros:** Strongest possible teeth — an out-of-lifecycle edit cannot land.
- **Cons:** Blocks legitimate fast paths (a one-line typo fix, an exploratory
  spike) with no owner-visible way to proceed except an env-var the owner would
  have to learn — friction the owner explicitly refused. It also breaks the gate
  family's own posture: the review-evidence and TDD gates gate *state
  transitions and evidence*, not the keystroke of editing a file. A hard block on
  every edit is heavier than the problem and risks the owner disabling it
  wholesale.

### Option C: Fail-open PostToolUse nudge aimed at the agent (recommended)

A `PostToolUse` hook on `Edit|Write|MultiEdit` checks, *after* an edit to project
source, whether the session is inside the lifecycle. If not, it injects
`additionalContext`: "this edit is outside jig — route it or record it." No
block, no owner prompt; opt-out via env var; any error fails open.

- **Pros:** Same teeth-not-trust posture as `jig-boundary-change-warn`
  (PostToolUse nudge) and `jig-claim-check` (Stop nudge) — proven, low-risk
  shapes already in the tree. Fires at the moment of the ad-hoc edit, so the
  nudge is anchored to the exact event the report is about. Aims solely at the
  agent; the owner in Auto never sees a dialog. Leaves room for the
  edit-anchored capture stub ([#108](https://github.com/ramboz/jig/issues/108)
  direction #2) to ride the same trigger later.
- **Cons:** A nudge is softer than a block — a determined or distracted agent can
  still ignore it. Accepted: the gate family's job is to make the omission
  *visible and durable*, not physically impossible; the durability (a re-surfacing
  stub) is what closes the loop, and that is a separate, deferrable slice.

### Option D: SessionStart reminder only

Surface the "route your edits through jig" reminder once at session start.

- **Pros:** Trivial; no per-edit machinery.
- **Cons:** Fires nowhere near the ad-hoc edit; degrades to prose-in-context, the
  same class of thing that already failed. Rejected.

## Recommended Decision

Choose **Option C.** Lifecycle *entry* becomes an enforced step in the same
teeth-not-trust family as review-evidence and TDD: a `PostToolUse` hook on
`Edit|Write|MultiEdit`, co-located with the existing `jig-boundary-change-warn`
matcher, that emits an agent-facing `additionalContext` nudge when an edit to
project source happens outside the lifecycle. It is fail-open, carries an env-var
opt-out consistent with the other gates, adds no owner-facing prompt, and logs
its fire via the existing `append_additional_context_event` path so the nudge
leaves an auditable trace.

"Inside the lifecycle" is detected coarsely — the presence of a locally-claimed
`IN_PROGRESS` slice or an active bug record — not per-edit scope. Coarse is
correct here: all 11 incidents were edits with *nothing at all* in flight, and a
coarse check is deterministic, cheap, and cannot mis-police legitimate
in-slice work.

The edit-anchored capture stub ([#108](https://github.com/ramboz/jig/issues/108)
direction #2) is explicitly **out of scope for this decision** and deferred to
its own slice behind the capture-rewrite decision (Track B1 of the fix plan / the
spec 083 successor), because it couples to machinery whose shape the maintainer
has not yet settled. This ADR commits only to the entry-gate nudge.

## Consequences

**Becomes easier:**
- Catching the "edited with nothing in flight" case at the moment it happens,
  instead of relying on the owner to notice.
- Extending the same trigger later to leave a durable capture stub, once the
  capture rewrite is decided.
- Explaining lifecycle entry as a gate like every other, rather than an exception
  enforced by prose.

**Becomes harder:**
- The agent gets one more piece of `additionalContext` on out-of-lifecycle edits;
  miscalibration would be noise. Cadence (once per session, re-armed on state
  change) and a narrow source boundary keep this bounded — see the spec.
- A new deterministic rule ("is this file project source?") must be defined and
  kept correct across the configurable docs root ([ADR-0033](adr-0033-configurable-docs-root.md)),
  so lifecycle artifacts (specs, bug records, ADRs, memory) never trip the gate.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **`PostToolUse` on `Edit|Write|MultiEdit` receives the edited `file_path` in
  `tool_input`.** Grounded: `jig-boundary-change-warn.sh` reads exactly
  `data['tool_input']['file_path']` on this event today and ships in the tree.
- **A locally-claimed `IN_PROGRESS` slice and an active bug record are both
  readable from disk without network.** Grounded: slice claim is stamped in the
  slice file's frontmatter (spec 049 `claimed_by`) and bug state lives in
  `docs/bugs/*.md` (bug-fix `bug.py`); both are files under the project root.
- **A per-session state file under `$TMPDIR` is enough to make the nudge fire at
  most once per session and re-arm on state change.** Grounded: `jig-context-check.sh`
  already uses exactly this once-per-band-per-session mechanism.

## Kill criteria

- If usage shows the nudge firing on legitimate edits often enough that the agent
  or owner routinely sets the opt-out, the source boundary or cadence is
  miscalibrated — narrow the boundary (or lower the cadence) rather than keep a
  gate people disable.
- If a lower-cost signal makes lifecycle entry self-evident without a per-edit
  hook, prefer it.

## Open questions

These are the maintainer's calls; the spec carries them forward as its own open
questions and does not presume the answers.

1. **Strictness of "inside the lifecycle":** coarse (any locally-claimed
   `IN_PROGRESS` slice or active bug on this branch) — recommended — versus
   edit-scoped (the edited file must belong to the claimed slice's declared
   surface).
2. **Fire cadence:** once per session re-armed on state change (recommended)
   versus once per turn versus every out-of-lifecycle edit.
3. **Source/non-source boundary:** the exact deterministic rule and how
   configurable it should be (a hardcoded deny of `docs_root` + `.jig` + `.claude`
   + `.git`, versus a `scaffold.json` allow/deny list).
4. **Codex host parity:** whether the gate needs a Codex-host equivalent now, per
   the 083-08 host-parity pattern, or can ship Claude-first.
