---
status: DRAFT
skill: spec-workflow
use_cases: []
frame_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

# Spec 098: Lifecycle entry gate

## Overview

jig enforces every lifecycle step *inside* the workflow with a gate, but the
step of **entering** the workflow is still enforced only by the agent
remembering. When the agent edits project source without first claiming a slice
or opening a bug record, the change is invisible to capture, records, review
gates, and landing — nothing was ever in the system to protect.

[#111](https://github.com/ramboz/jig/issues/111) measures the failure: **11
distinct incidents, 20 June – 16 July 2026, across four downstream projects**,
where the agent hand-edited source outside jig and conceded when caught. The
owner is currently the only enforcement layer. [ADR-0040](../../decisions/adr-0040-lifecycle-entry-gate.md)
(Proposed) records the decision this spec implements: lifecycle entry becomes a
teeth-not-trust gate in the same family as the review-evidence gate
([ADR-0014](../../decisions/adr-0014-review-evidence-model.md)) and the TDD loop
— a **fail-open `PostToolUse` nudge aimed at the agent, never a block and never
an owner-facing prompt.**

**This spec was opened design-first for approval, and stays in design.** The
maintainer's four calls are recorded in [#128](https://github.com/ramboz/jig/pull/128)
and folded into ADR-0040 and the slices below — see
[Settled calls](#settled-calls-maintainer). A **fifth question is open**: the
frame critique falsified two successive definitions of "inside the lifecycle",
and jig has no signal today that does the job. ADR-0040 therefore stays
`Proposed` and **no slice may be implemented** until question #5 is answered.

The mechanism is deliberately modelled on machinery already in the tree:

- **`jig-boundary-change-warn.sh`** — the co-located `PostToolUse`
  `Edit|Write|MultiEdit` sibling this hook joins: reads
  `tool_input.file_path`, matches a rule, emits a soft `additionalContext`
  nudge, opt-out env var, `except Exception: pass`.
- **`jig-context-check.sh`** — the once-per-band-per-session state-file mechanism
  under `$TMPDIR` that keeps a nudge from re-firing every turn.
- **`append_additional_context_event`** (`lib/read_attribution.py`) — the
  existing path every soft nudge uses to leave an auditable trace.

## What this spec does NOT do

- **It does not create capture stubs.** [#108](https://github.com/ramboz/jig/issues/108)
  direction #2 — leaving a durable stub on an unrouted edit that the 083-07
  re-surfacing loop keeps alive — rides the *same trigger* but couples to the
  capture rewrite the maintainer has not yet settled (fix-plan Track B1). It is
  carried as slice 098-03, **DEFERRED** behind that decision.
- **It does not block edits or prompt the owner.** ADR-0040 rejected the hard-block
  option (B) on exactly the owner's no-friction constraint.
- **It does not touch `conventions.md` or the spec gate.** `jig-spec-gate.sh`
  gates deliberate edits to the constitution ([ADR-0011](../../decisions/adr-0011-spec-gate-model.md));
  that is a different surface and stays as-is.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — ground factual claims by probe/citation, else list
     them here. Risk-gated. -->

- **`PostToolUse` / `Edit|Write|MultiEdit` delivers the edited path in
  `tool_input.file_path`.** Grounded: `jig-boundary-change-warn.sh` reads exactly
  that on this event and ships today.
- ⚠️ **No assumption is available about how "inside the lifecycle" is read.**
  Probed 2026-07-27 and all falsifying: the *presence* of lifecycle records says
  nothing about this session (jig's `main` has slice 088-02 `IN_PROGRESS` and
  bug 008 `REPORTED`); a *live claim* is cleared at REVIEWED, before
  reconciliation runs (`_CLAIM_CLEARING_STATUSES`); `bug.py new_bug(push=True)`
  writes only to `origin/main` and never stamps `.jig/spec-ref`; and
  `_claim_identifier` returns a branch name, not an operator. Open question #5.
- ⚠️ **Unprobed:** whether the `PostToolUse` payload carries `session_id`.
  `jig-context-check.sh` keys its once-per-session state on
  `payload.session_id or 'default'`, so if the field is absent every session
  shares one key and a single fire silences the gate until `$TMPDIR` clears.
  Must be probed before AC5 is implemented.
- **The configurable docs root is discoverable** for the source-boundary rule,
  via `_common/project_layout.py` (`layout.docs_root`,
  [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md)), so lifecycle
  artifacts never trip the gate regardless of where docs live.
- **`git check-ignore` is the reusable `.gitignore` oracle** for the
  source-boundary rule (settled call #3), and it does **not** on its own exclude
  lifecycle artifacts. Grounded by probe in this repo (2026-07-27):
  `git check-ignore -q .claude/settings.local.json` → ignored;
  `git check-ignore -q docs/specs/README.md` → **not** ignored;
  `git check-ignore -q .claude/` → **not** ignored. jig's own `.gitignore`
  lists only per-checkout ephemera (`.claude/*.jsonl`, `.jig/spec-ref`,
  `__pycache__/`), while `docs/` and the tracked parts of `.claude/` and `.jig/`
  are version-controlled by design. The boundary is therefore two-part — see
  settled call #3.

## Slices

| Slice | Title | Status | Why |
|-------|-------|--------|-----|
| 098-01 | entry-gate nudge (Claude host) | DRAFT | The core gate — the whole point of the spec. |
| 098-02 | Codex host parity | DRAFT | Settled call #4 — same spec, separately verifiable slice (083-08 pattern). |
| 098-03 | edit-anchored capture stub | DEFERRED | #108 direction #2; gated on the capture-rewrite decision (Track B1). |

### Settled calls (maintainer) {#settled-calls-maintainer}

The four questions this spec was opened with are **answered**. The maintainer's
calls on [#128](https://github.com/ramboz/jig/pull/128) (2026-07-27), recorded
here and in ADR-0040; the slices below are written against them, not against the
draft's recommendations:

1. **Strictness of "inside the lifecycle" — coarse.** The gate does not check
   whether the edited file belongs to the claimed slice's surface.

   🚧 **What the gate reads to decide "inside" is UNRESOLVED — see
   [ADR-0040 open question #5](../../decisions/adr-0040-lifecycle-entry-gate.md#open-question-5-there-is-no-inside-the-lifecycle-signal-yet).
   Slice 098-01 cannot be implemented until the maintainer answers it.** Two
   adversarial rounds falsified two definitions in a row:

   - *Presence* — "any `IN_PROGRESS` slice or open bug exists on the branch."
     jig's own `main` satisfies both today (slice 088-02 IN_PROGRESS; bug 008
     REPORTED), so the gate would be **permanently silent** here and in any
     project whose board is not perfectly clean.
   - *Live claim in this tree* — `.jig/spec-ref` cross-checked against the
     slice's status, or a bug `claimed_by` this checkout. Fails the other way:
     `workflow.py` clears the claim at **REVIEWED**, and `docs/workflow.md`
     step 7 puts **reconciliation after** that — so the gate would fire once per
     slice while the agent updates `architecture.md` / `CLAUDE.md`, telling it to
     enter a lifecycle it is finishing. It is also blind to bug fixes:
     `bug.py new_bug(push=True)` writes the record to `origin/main` only, and
     never writes `.jig/spec-ref`. And there is no operator identity to compare
     against — `_claim_identifier` returns a **branch name** (or the literal
     `"detached"`), spec 049's explicit non-goal being "no human-identity
     inference."

   The coarseness the maintainer settled is unaffected either way. The open
   question is mechanical: jig has no signal today that spans a work item from
   entry through reconciliation, across both `workflow.py` and `bug.py`.

   ✅ **Most of that gap is closed by [#138](https://github.com/ramboz/jig/pull/138)**,
   which makes `claimed_by` a *working-lifecycle* claim — held across
   `READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED`, cleared only at
   release points. That is precisely the span this gate needs, and it removes the
   reconciliation false-fire. **Spec 098 should depend on #138 rather than build a
   parallel signal.** What remains: the bug arm (`new_bug(push=True)` still writes
   only to `origin/main`), branch-scoped identity wording, and probing
   `session_id`.
2. **Fire cadence — once per session**, re-armed when lifecycle state changes.
   (Matches the draft's recommendation.)
3. **Source/non-source boundary — reuse `.gitignore`; introduce no new ignore
   mechanism.** The maintainer's words: base it off `.gitignore` as a starting
   point and fine-tune later; do not add another "ignore" mechanism unless it is
   proven necessary. This **rejects the `scaffold.json` allow/deny list** and
   supersedes the draft's standalone hardcoded deny-list.

   **The boundary is two-part, because `.gitignore` alone does not express it.**
   Probed above (Assumptions): `.gitignore` covers per-checkout ephemera, not
   lifecycle artifacts — `docs/` and the tracked parts of `.claude/` / `.jig/`
   are version-controlled by design, so a `.gitignore`-only rule would nudge on
   every routine edit to a spec, bug record, or ADR, which is exactly the
   in-lifecycle bookkeeping the gate must stay silent about. The rule is
   therefore:

   > A path is **project source** unless it is (a) ignored by `git check-ignore`,
   > **or** (b) a lifecycle artifact — under `<docs base>/specs/`, `bugs/`,
   > `decisions/`, `memory/`, or under `.jig/`, `.claude/`, `.git/`.

   Part (b) is a fixed list with no configuration surface — it is not the
   "another ignore mechanism" the maintainer refused, and there is nothing for a
   project to tune. If (b) later proves to need tuning, that is the fine-tuning
   the maintainer left open, and it gets its own decision.

   ⚠️ **(b) names the artifact subtrees, never `docs_root` wholesale** (frame
   critique, 2026-07-27). `project_layout.docs_base` returns the *project
   directory itself* when `docs_root == "."`, so a rule phrased as "anything
   under `docs_root`" would classify the entire repository as lifecycle artifacts
   and switch the gate off completely for a `.`-rooted project — the track-local
   adoption shape [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md)
   exists to serve, and plausibly the shape of the downstream projects in #111.
   The earlier draft of this spec listed "edit under a relocated `docs_root`
   (incl. `.`) → silent" as a *passing* test, which would have ratified the dead
   gate as correct; that test is corrected below.
4. **Codex host parity — same spec, separate slice.** Stay symmetric across
   hosts; the Codex equivalent ships in this spec as slice 098-02 so it can be
   verified explicitly and separately (the 083-08 host-parity pattern). This
   **rejects Claude-first-only**.

## Acceptance (spec-level)

- **Open question #5 is answered by the maintainer, and ADR-0040 is Accepted,
  before any slice leaves DRAFT.** Neither has happened: the ADR failed its own
  frame-critique gate twice (evidence:
  `docs/decisions/reviews/adr-0040-frame-critique.md`), and it should — a gate
  that cannot say what "inside the lifecycle" means cannot be built.
- Slice 098-01 ships a fail-open `PostToolUse` hook that nudges (never blocks,
  never prompts the owner) on an out-of-lifecycle edit to project source, with an
  env-var opt-out, scaffold-mode parity, and no new failure mode for the session.
- Slice 098-02 ships the Codex-host equivalent of the same gate, verified by its
  own tests, so neither host carries the gate alone.
- The source boundary reuses `git check-ignore` and adds no project-configurable
  ignore list (settled call #3).
- **The gate demonstrably fires.** Two tests stand as the anti-dead-gate proof:
  an out-of-lifecycle source edit nudges on a tree that has an unrelated
  `IN_PROGRESS` slice and an unclaimed open bug (the falsifying case), and the
  same on a `.`-rooted docs layout. A silent gate is the failure mode this spec
  is most exposed to — see ADR-0040's under-fire kill criterion.
