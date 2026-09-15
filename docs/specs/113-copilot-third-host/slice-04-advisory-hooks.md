---
status: DRAFT
dependencies: [113-02]
last_verified:
# arch_review: true  # introduces the hook-protocol translation layer
---

## Slice 113-04 — advisory-hooks

**Goal:** jig's advisory nudges fire under Copilot — the `additionalContext`-style
hooks (session git-freshness, boundary-change-warn, lifecycle-entry-gate nudge)
translated onto Copilot's event model and emitted as `.github/hooks/*.json`.

**DoR:**
- ✅ 113-02 done (renderer + skeleton).
- ✅ 113-01 finding recorded the concrete Copilot hook JSON schema (event names,
  payload, response shape) for an advisory hook.

**Acceptance Criteria:**

1. **Event-name + payload translation.** `translate_hook_protocol` on
   `CopilotScaffoldRenderer` maps Claude PascalCase events to Copilot camelCase
   (e.g. `SessionStart`→`sessionStart`, `PostToolUse`→`postToolUse`) and adapts
   the payload/field access the hook scripts read. A test asserts a translated
   advisory hook emits Copilot-shaped JSON.
2. **Advisory hooks emitted.** The git-freshness, boundary-warn, and
   entry-gate-nudge hooks are rendered into `hosts/copilot/.github/hooks/` and
   register in a Copilot session (or deterministic substitute), firing their
   `additionalContext` nudge.
3. **Fail-open preserved.** Each translated advisory hook keeps its fail-open
   posture (best-effort; never blocks the session on error/timeout), matching the
   Claude behavior.

**DoD:**
- [ ] All ACs pass; full suite green; new tests fail when the feature is removed.
- [ ] Reviewed by `reviewer` subagent (compliance + craft; arch pass).
- [ ] Deviation log + reconciliation sweep produced.

**Anti-horizontal-phasing check:** After this slice a Copilot user gets jig's
context nudges in-session — observable behavior.
