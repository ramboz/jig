---
status: Proposed
dependencies: [adr-0011, adr-0014, adr-0015, adr-0033]
last_verified: 2026-07-27
frame_review: true
---

# ADR-0040: Lifecycle entry gate

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

## Decision

**Option C**, as confirmed by the maintainer on 2026-07-27. Lifecycle *entry* becomes an enforced step in the same
teeth-not-trust family as review-evidence and TDD: a `PostToolUse` hook on
`Edit|Write|MultiEdit`, co-located with the existing `jig-boundary-change-warn`
matcher, that emits an agent-facing `additionalContext` nudge when an edit to
project source happens outside the lifecycle. It is fail-open, carries an env-var
opt-out consistent with the other gates, adds no owner-facing prompt, and logs
its fire via the existing `append_additional_context_event` path so the nudge
leaves an auditable trace.

"Inside the lifecycle" is detected **coarsely** — the gate never asks whether the
edited file belongs to the claimed slice's declared surface. That is settled
(resolved question #1).

**What it reads to decide "inside" is not settled, and this ADR does not fix
it.** Two adversarial rounds falsified two successive definitions — first
"presence of any `IN_PROGRESS` slice or open bug on the branch" (silent forever),
then "a live claim in this working tree" (fires once per slice during
reconciliation, and blind to bug fixes entirely). The decision to build the gate
stands on its own; the detection rule is
[open question #5](#open-question-5-there-is-no-inside-the-lifecycle-signal-yet)
and blocks implementation.

The source boundary reuses the project's existing `.gitignore` — via
`git check-ignore` — plus a fixed, unconfigurable list of lifecycle-artifact
roots. jig introduces **no new ignore mechanism** (see resolved question #3 for
why one test is not enough).

The gate ships on **both hosts** under this decision: the Claude implementation
and the Codex equivalent live in the same spec as separately verifiable slices,
so neither host carries the gate alone
([ADR-0018](adr-0018-dual-host-generated-plugin-artifacts.md)).

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
- A deterministic rule ("is this file project source?") must be kept correct
  across the configurable docs root ([ADR-0033](adr-0033-configurable-docs-root.md)),
  so lifecycle artifacts (specs, bug records, ADRs, memory) never trip the gate.
  Reusing `.gitignore` keeps most of that rule out of jig's hands, but not all of
  it — the lifecycle-artifact roots are tracked files and must be listed.
- Two hosts to keep in step. The build transform mirrors the hook into the Codex
  package automatically, but runtime behaviour there is verified separately
  (spec slice 098-02), which is where the real cost sits.

**Accepted coverage limit — edits that never reach the tool boundary.** The hook
sees `Edit|Write|MultiEdit` only. A file written through Bash — `sed -i`, a
heredoc redirect, `python - <<EOF` — never reaches the gate. Whether that matters
is *unmeasured*: the #111 report counts incidents, not the tool that produced
them, so this gate's real-world coverage is unknown rather than known-partial.
This is recorded as an accepted limit of the chosen trigger, not as a claim that
Bash writes are rare. If the under-fire criterion below trips, this is the first
place to look.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **`PostToolUse` on `Edit|Write|MultiEdit` receives the edited `file_path` in
  `tool_input`.** Grounded: `jig-boundary-change-warn.sh` reads exactly
  `data['tool_input']['file_path']` on this event today and ships in the tree.
- ~~**A locally-claimed `IN_PROGRESS` slice and an active bug record are both
  readable from disk without network** — and their *presence* means the session is
  inside the lifecycle.~~ **Withdrawn 2026-07-27 (frame critique).** The
  readability half holds; the inference does not. Those records are
  branch-durable, so presence says nothing about *this* session — falsified by
  probe on jig's own `main` (resolved question #1). Replaced by:
- **This working tree's live claim is readable from disk without network.**
  Grounded: `.jig/spec-ref` is stamped by `workflow.py transition … IN_PROGRESS`
  (slice 056-03), is working-tree-local and git-ignored so it never travels
  across branches, and is already read on the hook path by
  `read_attribution.read_spec_ref`. Its known limit is also grounded: nothing
  clears it on transition *out* of `IN_PROGRESS` (`workflow.py` writes it only
  under `if new_status == IN_PROGRESS_STATUS`), which is why the rule
  cross-checks the named slice's current status rather than the marker alone.
- **A per-session state file under `$TMPDIR` is enough to make the nudge fire at
  most once per session and re-arm on state change.** Grounded: `jig-context-check.sh`
  already uses exactly this once-per-band-per-session mechanism.
- **`git check-ignore` is a usable, reusable `.gitignore` oracle, and it does not
  cover lifecycle artifacts.** Grounded by probe, 2026-07-27 — see resolved
  question #3 for the three commands and their results.
- **Registering the hook in `hooks/hooks.json` mirrors it into the Codex
  package.** Grounded: `scripts/build_codex_plugin.py._write_codex_hooks`
  generates the Codex `hooks.json` from the Claude one with a `${PLUGIN_ROOT}`
  prefix, and the Codex package's `PostToolUse` / `Edit|Write|MultiEdit` matcher
  already carries `jig-post-edit-verify.sh` + `jig-boundary-change-warn.sh`.
  Packaging parity is therefore free; runtime parity is not (slice 098-02).

## Kill criteria

- **Over-firing.** If usage shows the nudge firing on legitimate edits often
  enough that the agent or owner routinely sets the opt-out, the source boundary
  or cadence is miscalibrated — narrow the boundary (or lower the cadence) rather
  than keep a gate people disable.
- **Under-firing (added 2026-07-27, frame critique).** A gate that never fires
  looks identical to a project with no ad-hoc edits, and the draft's silent-
  forever failure mode would have shipped undetected. Measurable trigger: if over
  **8 weeks** of real use the gate's logged fires (`append_additional_context_event`,
  `out_of_lifecycle_edit`) are **zero** while out-of-lifecycle edits are still
  being caught by the owner, the detection is wrong — suspect the liveness signal
  (resolved question #1), the `.`-root boundary collapse (question #3), or the
  Bash-write blind spot (Consequences) before concluding the problem is solved.
  The close-out dogfood check must not be read as evidence of health: "stays
  silent during a normal in-slice session" passes just as cleanly for a dead gate.
- If a lower-cost signal makes lifecycle entry self-evident without a per-edit
  hook, prefer it.

## Resolved questions

The four questions this ADR was proposed with were answered by the maintainer on
[#128](https://github.com/ramboz/jig/pull/128) (2026-07-27), and are settled
here and in [spec 098](../specs/098-lifecycle-entry-gate/spec.md).

**A fifth question was opened by the frame critique and is not settled** — see
[open question #5](#open-question-5-there-is-no-inside-the-lifecycle-signal-yet).
It blocks implementation, not the decision: *that* the gate should exist is
decided; *how it recognizes "inside the lifecycle"* is not.

1. **Strictness of "inside the lifecycle" — coarse.** The gate does **not**
   require the edited file to belong to the claimed slice's declared surface.
   Settled as asked.

   **Correction to the mechanism under that call (frame critique, 2026-07-27 —
   needs the maintainer's eyes).** The draft implemented "coarse" as *the
   presence of any `IN_PROGRESS` slice or any open bug record on this branch*.
   That reading is falsified by probe on jig's own `main`:
   `docs/specs/088-project-orientation/slice-02-orient-skill.md` is
   `status: IN_PROGRESS`, and `docs/bugs/008-flaky-host-package-drift-guard.md`
   is `status: REPORTED` — an open status per `bug.py OPEN_STATUSES` — with
   `claimed_by: detached`, a stale reservation artifact, not a live claim.
   Under the draft rule the gate would be **permanently silent on this
   repository**, including during the session that builds it. That is the
   general case, not a quirk: any real project's steady state is "at least one
   slice claimed or one bug open", so a presence test fires only on a perfectly
   clean board — the rarest state, not the target one.

   Presence is the wrong signal because the records are **branch-durable**,
   while the thing being detected is a property of *this session*. The obvious
   repair — read a live claim from this working tree —

   > `.jig/spec-ref` names a slice **and** that slice is still `IN_PROGRESS` in
   > this tree, **or** an open bug record is `claimed_by` this checkout

   was itself falsified by the second critique round. **It is not the decision;
   see [open question #5](#open-question-5-there-is-no-inside-the-lifecycle-signal-yet).**
   `.jig/spec-ref` is genuinely the closest existing signal — `workflow.py`
   stamps it on `transition … IN_PROGRESS` (slice 056-03), it is working-tree-
   local and git-ignored, and hooks already read it via
   `read_attribution.read_spec_ref` — but it is not sufficient, and the bug arm
   does not work at all. What "inside the lifecycle" should mean *mechanically*
   is the one thing this ADR cannot yet answer.

   **A second, independent objection the critique raised and this ADR does not
   resolve:** the 11 incidents are, by construction, the ones the owner
   *noticed*. An ad-hoc edit made while a slice is legitimately in flight hides
   inside that slice's diff — systematically the incident least likely to be
   spotted — so "all 11 had nothing in flight" cannot be read as "in-slice ad-hoc
   edits do not happen." The coarse call deliberately does not detect that class.
   Recorded here as an accepted, *measured-later* limitation (see the under-fire
   kill criterion), not as evidence that the class is empty.
2. **Fire cadence — once per session**, re-armed when lifecycle state changes.
   Rejected: once per turn, and every out-of-lifecycle edit — both nag.
3. **Source/non-source boundary — reuse `.gitignore`; add no new ignore
   mechanism.** The maintainer's call: base the rule on `.gitignore` as a
   starting point and fine-tune later, rather than introduce another "ignore"
   mechanism before one is proven necessary. This **rejects the `scaffold.json`
   allow/deny list** outright.

   `.gitignore` alone is not sufficient, and the gap is measured, not assumed.
   Probed in this repo on 2026-07-27: `git check-ignore` reports
   `.claude/settings.local.json` ignored, but `docs/specs/README.md` **not**
   ignored and `.claude/` **not** ignored. jig's `.gitignore` lists per-checkout
   ephemera; `docs/` and the tracked parts of `.claude/` and `.jig/` are
   version-controlled by design. A `.gitignore`-only rule would therefore nudge
   on every routine edit to a spec, bug record, or ADR — precisely the
   in-lifecycle bookkeeping the gate must ignore. The boundary is consequently
   two tests: **(a)** `git check-ignore`, plus **(b)** a fixed list of lifecycle
   artifact locations with no configuration surface. (b) is not the mechanism the
   maintainer refused: there is nothing for a project to configure, and it is the
   minimum needed for (a) to mean what it was chosen to mean.

   **(b) is the named artifact subtrees, never "everything under `docs_root`"**
   (frame critique, 2026-07-27). Writing (b) as "any path under `docs_root`"
   collapses the gate to a no-op for a `.`-rooted project: `project_layout.
   docs_base` returns the project directory itself when `docs_root == "."`
   (`skills/_common/project_layout.py`), so every path in the repo would count as
   a lifecycle artifact. That is not a corner case — `docs_root: "."` is exactly
   the track-local adoption shape ADR-0033 exists to support, i.e. plausibly the
   shape of the downstream projects the incidents came from. (b) is therefore the
   *named* subtrees resolved against the docs base — `specs/`, `bugs/`,
   `decisions/`, `memory/` — plus `.jig/`, `.claude/`, `.git/`, and the gate must
   have an explicit `.`-root test proving it still fires on source there.
4. **Codex host parity — same spec, separate slice.** Stay symmetric across
   hosts. The Codex equivalent ships in spec 098 as slice 098-02 so it can be
   verified explicitly and separately, following the 083-08 host-parity pattern.
   **Rejects Claude-first-only.** Note the asymmetry in cost: packaging parity is
   automatic (`build_codex_plugin.py` generates the Codex `hooks.json` from the
   Claude one), while runtime confirmation needs the Codex host — the same
   constraint that forced 083-08 into its own slice.

### Open question #5 — there is no "inside the lifecycle" signal yet {#open-question-5-there-is-no-inside-the-lifecycle-signal-yet}

**Raised by the frame critique, 2026-07-27. This is the blocker: the decision to
build the gate stands, but it cannot be implemented until this is answered.**

The gate needs to distinguish "this session is working inside jig" from "this
session is editing ad-hoc." Every candidate signal jig has today fails, and the
failures were verified against the tree, not reasoned about:

- **Slice claims are destroyed mid-lifecycle.** `_CLAIM_CLEARING_STATUSES =
  ("REVIEWED", "READY_FOR_IMPLEMENTATION", "DRAFT")` — the claim clears and the
  slice leaves `IN_PROGRESS` at REVIEWED, while `docs/workflow.md` step 7 puts
  **reconciliation after** that transition: updating `architecture.md`,
  `CLAUDE.md`, `roadmap.md`. Those are tracked, not ignored, and not under the
  artifact subtrees — so they read as source. A claim-based rule fires **once
  per slice, on every slice**, telling the agent to enter the lifecycle while it
  performs the mandated last step of a slice. AC5's "re-arm on lifecycle state
  change" lands the re-arm exactly there. This is not tunable noise; it is the
  wrong definition of "lifecycle".
- **The bug arm has no local signal at all.** `bug.py new_bug(push=True)` calls
  `reserve_bug_on_origin` and returns `None`: the record lands on `origin/main`,
  nothing in the working tree. `bug.py` never writes `.jig/spec-ref`. A bug fix
  opened the way jig prescribes is invisible to both arms.
- **There is no operator identity to compare against.** `_claim_identifier` (in
  both `workflow.py` and `bug.py`) returns `JIG_CLAIM_ID`, else the **branch
  name**, else the literal `"detached"` — spec 049's stated non-goal is "no
  human-identity inference". **This corrects an assertion made earlier in this
  ADR's revision:** `claimed_by: detached` on bug 008 is not a stale artifact,
  it is that function's normal return value. Consequences: a bug reported on
  `main` and fixed on a task branch can never match; two agents on same-named
  branches match each other.
- **Per-session state is keyed on a payload field, not on `$TMPDIR`.**
  `jig-context-check.sh` keys once-per-session state on
  `payload.session_id or 'default'`. Whether `PostToolUse` carries `session_id`
  is **unprobed**. If it does not, all sessions share the `default` key and one
  fire silences the gate until `$TMPDIR` is cleared — a silent death the
  under-fire criterion cannot tell apart from success.

**Most of this is already being fixed elsewhere — [#138](https://github.com/ramboz/jig/pull/138).**
That PR (bug 013 / its own ADR, Accepted, implemented and reviewed) reverses
exactly the clearing edge above: claims become *working-lifecycle* claims, stamped
across `READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED` and cleared
only at release points. If it lands, the reconciliation false-fire — the fatal
objection — disappears, and a claim becomes a usable "inside the lifecycle"
signal for the whole span this gate cares about. **Spec 098 should take a hard
dependency on it rather than invent a parallel mechanism.**

What #138 does *not* cover, and what remains of question #5:

- **The bug arm.** `new_bug(push=True)` still leaves nothing in the working tree,
  and `bug.py` still never stamps `.jig/spec-ref`. #138 is about slice claims.
- **Identity is a branch name.** Workable *because* jig's own convention is one
  worktree per task — "claimed by this branch" is then a coherent liveness test —
  but it must be written as branch scoping, not as "operator identity", and the
  report-on-`main`/fix-on-branch case needs a stated answer (re-claim on the task
  branch, most likely).
- **`session_id` in the `PostToolUse` payload** is still unprobed.

**The maintainer's call, given that.** Roughly:

- **(a) Build the signal first.** A genuine session/lifecycle marker — set on
  entry, cleared on exit, spanning IN_PROGRESS *through* reconciliation, written
  by both `workflow.py` and `bug.py`. Correct, and it makes this gate a
  dependent of a new piece of machinery rather than a small hook.
- **(b) Narrow the gate to the high-confidence case only.** Fire only when there
  is *no lifecycle activity of any kind* in this tree — no `.jig/spec-ref` at
  all, no recent transition. Catches the 11 measured incidents (all were
  "nothing in flight"), misses everything subtler, and is honest about it.
- **(c) Re-shape the trigger.** If the real signal is "a session that never
  entered", a Stop/SessionStart-shaped check may beat a per-edit hook — though
  ADR option D was rejected for firing nowhere near the edit.
- **(d) Something else.**

Recommendation, revised in light of #138: **land #138 first, then take (a) for
free** — the working-lifecycle claim it introduces *is* the signal this gate
needs, for slices. Close the bug arm and the identity wording on top of it, probe
`session_id`, and only then implement 098-01. Falling back to (b) — fire only
when there is no lifecycle activity of any kind in this tree — stays available if
#138 stalls. Either way, no slice should be implemented before this is settled.

### Still open (deliberately)

- **Fine-tuning the boundary.** The maintainer left "fine-tune as needed" open.
  If test (b) proves to need per-project tuning in the field, that reopens the
  configurable-list question and gets its own decision — it is not settled here
  by default.
- **Bash-written edits.** Recorded as an accepted coverage limit in Consequences,
  not resolved.
