---
status: DRAFT
skill: spec-workflow
use_cases: []
frame_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

# Spec 096: Lifecycle entry gate

## Overview

jig enforces every lifecycle step *inside* the workflow with a gate, but the
step of **entering** the workflow is still enforced only by the agent
remembering. When the agent edits project source without first claiming a slice
or opening a bug record, the change is invisible to capture, records, review
gates, and landing — nothing was ever in the system to protect.

[#111](https://github.com/ramboz/jig/issues/111) measures the failure: **11
distinct incidents, 20 June – 16 July 2026, across four downstream projects**,
where the agent hand-edited source outside jig and conceded when caught. The
owner is currently the only enforcement layer. [ADR-0039](../../decisions/adr-0039-lifecycle-entry-gate.md)
(Proposed) records the decision this spec implements: lifecycle entry becomes a
teeth-not-trust gate in the same family as the review-evidence gate
([ADR-0014](../../decisions/adr-0014-review-evidence-model.md)) and the TDD loop
— a **fail-open `PostToolUse` nudge aimed at the agent, never a block and never
an owner-facing prompt.**

**This spec is design-for-approval.** It is opened for the maintainer's review of
the shape and the open questions below. No slice is built until ADR-0039 is
Accepted; the slices are DRAFT / DEFERRED accordingly.

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
  carried as slice 096-02, **DEFERRED** behind that decision.
- **It does not block edits or prompt the owner.** ADR-0039 rejected the hard-block
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
- **Lifecycle state is readable from disk without network:** a claimed
  `IN_PROGRESS` slice carries `claimed_by` in its frontmatter (spec 049) and an
  active bug record lives in `docs/bugs/*.md` (bug-fix `bug.py`).
- **The configurable docs root is discoverable** for the source-boundary rule,
  via `_common/project_layout.py` (`layout.docs_root`,
  [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md)), so lifecycle
  artifacts never trip the gate regardless of where docs live.

## Slices

| Slice | Title | Status | Why |
|-------|-------|--------|-----|
| 096-01 | entry-gate nudge | DRAFT | The core gate — the whole point of the spec. |
| 096-02 | edit-anchored capture stub | DEFERRED | #108 direction #2; gated on the capture-rewrite decision (Track B1). |

### Open questions for the maintainer

Carried from ADR-0039; slice 096-01's acceptance criteria are written against the
**recommended** answers but must not be treated as settled until confirmed:

1. **Strictness of "inside the lifecycle"** — coarse (any locally-claimed
   `IN_PROGRESS` slice or active bug) *[recommended]* vs. edit-scoped.
2. **Fire cadence** — once per session, re-armed on state change *[recommended]*
   vs. once per turn vs. every out-of-lifecycle edit.
3. **Source/non-source boundary** — hardcoded deny of `docs_root` + `.jig` +
   `.claude` + `.git` *[recommended starting point]* vs. a `scaffold.json`
   allow/deny list.
4. **Codex host parity** — ship Claude-first vs. require a Codex equivalent now
   (083-08 pattern).

## Acceptance (spec-level)

- ADR-0039 is Accepted before any slice leaves DRAFT.
- Slice 096-01 ships a fail-open `PostToolUse` hook that nudges (never blocks,
  never prompts the owner) on an out-of-lifecycle edit to project source, with an
  env-var opt-out, scaffold-mode parity, and no new failure mode for the session.
- The four open questions above are answered (in the issue or the ADR) before
  096-01 is implemented.
