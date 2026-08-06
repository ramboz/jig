---
status: DONE
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
owner is currently the only enforcement layer. [ADR-0044](../../decisions/adr-0044-lifecycle-entry-gate.md)
(Accepted 2026-07-30) records the decision this spec implements: lifecycle entry becomes a
teeth-not-trust gate in the same family as the review-evidence gate
([ADR-0014](../../decisions/adr-0014-review-evidence-model.md)) and the TDD loop
— a **fail-open `PostToolUse` nudge aimed at the agent, never a block and never
an owner-facing prompt.**

**This spec was opened design-first for approval.** The maintainer's calls are
recorded in [#128](https://github.com/ramboz/jig/pull/128) and folded into
ADR-0044 and the slices below — see [Settled calls](#settled-calls-maintainer).
A **fifth question**, opened by the frame critique after two successive
definitions of "inside the lifecycle" were falsified, was answered on 2026-07-30:
*"let's do #138 first, and just address the remaining gap here."* ADR-0044 is
now **Accepted**, and the remaining gap is closed inside this spec — see
[settled call 5](#settled-calls-maintainer) and slice 098-04.

**Implementation is sequenced, not blocked.** Slice 098-01 depends on
[#138](https://github.com/ramboz/jig/pull/138) merging (it supplies the
working-lifecycle claim the gate reads) and on slice 098-04 (which supplies the
same signal for the bug lifecycle). Neither is an open question; both are work
items with owners.

**A note on the number.** This spec's decision record is ADR-**0044**, not 0040.
0040 was taken on `main` on 2026-07-27 by an unrelated reservation, and 0041–0043
are claimed by other open PRs; the record was renumbered inside this branch
rather than by pushing a reservation to `main`. Spec 098 itself is unclaimed
elsewhere and stands.

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
- **It does not block edits or prompt the owner.** ADR-0044 rejected the hard-block
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
- **"Inside the lifecycle" = a live working-lifecycle claim held by this
  checkout** (settled call #5). This is an assumption about a surface that does
  **not exist yet on `main`**: it holds only after
  [#138](https://github.com/ramboz/jig/pull/138) merges, which is why 098-01
  declares it as a dependency rather than a background fact. The four
  pre-#138 candidates were probed on 2026-07-27 and all falsify: the *presence*
  of lifecycle records says nothing about this session (jig's `main` has slice
  088-02 `IN_PROGRESS` and bug 008 `REPORTED`); a *live claim* was cleared at
  REVIEWED, before reconciliation runs (`_CLAIM_CLEARING_STATUSES`);
  `bug.py new_bug(push=True)` writes only to `origin/main` and never stamps
  `.jig/spec-ref`; and `_claim_identifier` returns a branch name, not an
  operator.
- **The `PostToolUse` payload carries a real `session_id`** — probed on the
  Claude host, 2026-07-30, closing what was the last unknown in question #5.
  `jig-decision-inflight.sh` runs on `PostToolUse` and keys its scratch file on
  `data.get('session_id') or 'default'`; the session that wrote this revision
  produced `.jig/decision-scratch/411b8c7a-4d9e-45d7-be01-5b4fab17d725.log` —
  the host's real session UUID, not the `default` fallback. Cadence keying (AC5)
  is therefore sound on Claude. ⚠️ **Not probed on Codex** — slice 098-02 must
  re-probe rather than inherit this.
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
| 098-04 | bug-lifecycle claim marker | DRAFT | **Built first.** Settled call #5(a): `bug.py` stamps the working-tree marker `workflow.py` already stamps, so the gate reads one signal for both lifecycles. |
| 098-01 | entry-gate nudge (Claude host) | DRAFT | The core gate — the whole point of the spec. Depends on [#138](https://github.com/ramboz/jig/pull/138) + 098-04. |
| 098-02 | Codex host parity | DRAFT | Settled call #4 — same spec, separately verifiable slice (083-08 pattern). |
| 098-03 | edit-anchored capture stub | DEFERRED | #108 direction #2; gated on the capture-rewrite decision (Track B1). |

**Build order is 098-04 → 098-01 → 098-02**, which is not the numeric order.
098-04 was added after the maintainer's 2026-07-30 call and appended rather than
inserted, so the three earlier slices keep the numbers already discussed on
[#128](https://github.com/ramboz/jig/pull/128). Dependencies are declared in each
slice's frontmatter; the numbering carries no ordering meaning here.

### Settled calls (maintainer)

The four questions this spec was opened with are **answered** (maintainer's calls
on [#128](https://github.com/ramboz/jig/pull/128), 2026-07-27), as is the fifth
the frame critique opened (2026-07-30). All five are recorded here and in
ADR-0044; the slices below are written against them, not against the draft's
recommendations:

1. **Strictness of "inside the lifecycle" — coarse.** The gate does not check
   whether the edited file belongs to the claimed slice's surface.

   ✅ **What the gate reads to decide "inside" is settled — see
   [settled call 5](#settled-calls-maintainer) and
   [ADR-0044 resolved question #5](../../decisions/adr-0044-lifecycle-entry-gate.md#resolved-question-5).**
   Getting there took two adversarial rounds, which falsified two definitions in
   a row; both are kept below because they are the evidence for the rule that
   replaced them:

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

   The coarseness the maintainer settled is unaffected either way. What both
   failures share is mechanical: at the time of the critique jig had no signal
   that spanned a work item from entry through reconciliation, across both
   `workflow.py` and `bug.py`. That is what settled call #5 supplies.
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
5. **"Inside the lifecycle" = a live working-lifecycle claim held by this
   checkout — fix the signal at its source, don't route around it.**
   The maintainer's call on 2026-07-30: *"Yes, let's do #138
   first, and just address the remaining gap here."* The rule, in full, is in
   [ADR-0044 resolved question #5](../../decisions/adr-0044-lifecycle-entry-gate.md#resolved-question-5);
   in short, the gate is silent when `.jig/spec-ref` names a work item that is
   claimed by this checkout **and** still in a working status. This **rejects**
   the narrow fallback ("fire only when there is no lifecycle activity at all"),
   which would have hard-coded the draft's blind spot instead of fixing it.

   Three consequences for this spec:

   **(a) The bug arm needs the marker `bug.py` never writes — new slice 098-04.**
   `new_bug(push=True)` puts the record on `origin/main` and returns `None`;
   nothing lands in the working tree, and `bug.py` never stamps `.jig/spec-ref`.
   098-04 makes the *local* steps of the bug lifecycle — `bug.py pickup <id>`,
   and `transition` into a working status — stamp the same marker `workflow.py`
   stamps at `IN_PROGRESS`, so the gate reads one signal for both lifecycles.
   Existing readers of that marker (`read_attribution.read_spec_ref`,
   `_common/gate_telemetry`, `scripts/usage.py`) must keep parsing what they
   parse today: the marker is extended, not repurposed.

   **(b) Identity is branch scoping, and is written that way.** `_claim_identifier`
   returns `JIG_CLAIM_ID`, else the branch name, else `"detached"`. Spec 049's
   non-goal — no human-identity inference — stands and is not weakened here. The
   test reads *"claimed by this checkout"*, never *"claimed by this operator"*,
   and is coherent only under jig's one-worktree-per-task convention. Two limits
   are stated rather than fixed: two checkouts on same-named branches read as
   each other, and a bug reported on `main` but fixed on a task branch does not
   match until it is re-claimed there. The prescribed answer to the second is
   `bug.py pickup <id>` from the working tree — already step 1 of
   `bug-fix/SKILL.md`, and under 098-04 that is exactly the command that stamps
   the marker. Following the skill is what turns the gate off; there is no new
   ritual.

   **(c) `session_id` is probed and present** (Assumptions, 2026-07-30) on the
   Claude host. Codex is not covered — 098-02 re-probes.

   **Sequencing.** 098-01 declares a hard dependency on
   [#138](https://github.com/ramboz/jig/pull/138) and on 098-04. #138 is what
   makes a claim span `READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` /
   `RECONCILED` instead of clearing at REVIEWED; without it the gate fires at
   every slice's reconciliation. This spec deliberately builds no parallel
   signal while waiting.

## Acceptance (spec-level)

- **ADR-0044 is Accepted and question #5 is answered before any slice leaves
  DRAFT.** ✅ Both done on 2026-07-30. The ADR was held at Proposed through two
  failed frame-critique rounds (evidence:
  `docs/decisions/reviews/adr-0044-frame-critique.md`) precisely because a gate
  that cannot say what "inside the lifecycle" means cannot be built; it now can.
- **098-01 does not start before [#138](https://github.com/ramboz/jig/pull/138)
  merges and 098-04 is DONE.** This is a sequencing gate, not an open question —
  both are declared in 098-01's frontmatter dependencies.
- Slice 098-04 makes `bug.py` stamp the same working-tree lifecycle marker as
  `workflow.py`, without breaking any existing reader of that marker.
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
  is most exposed to — see ADR-0044's under-fire kill criterion.
