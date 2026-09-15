---
status: DRAFT
dependencies: [113-02]
last_verified:
---

## Slice 113-03 — agents

**Goal:** A Copilot user gets jig's custom-agent roster — implementer, reviewer,
architect — rendered as Copilot custom agents under `.github/agents/`.

**DoR:**
- ✅ 113-02 done (renderer + skeleton).
- ✅ 113-01 finding fixed the agent file form (`.md` vs `.agent.md`) and honored
  frontmatter fields.

**Acceptance Criteria:**

1. **Agents rendered.** Each jig source agent renders to the verified Copilot
   agent form under `hosts/copilot/.github/agents/`, with frontmatter mapped to
   the fields Copilot honors (tools, description, read-only/edit posture).
2. **Model-id neutrality.** No rendered agent hard-codes `opus`/`sonnet`; model
   selection defers to Copilot's `/model` (Adobe default GPT-5.6 Terra). A test
   asserts no Claude-specific model id leaks into the Copilot agent output.
3. **Reviewer read-only posture preserved.** The rendered reviewer agent retains
   its read-only tool restriction (Read/Glob/Grep), matching the Claude/Codex
   renderings.

**DoD:**
- [ ] All ACs pass; full suite green; new tests fail when the feature is removed.
- [ ] Reviewed by `reviewer` subagent (compliance + craft).
- [ ] Deviation log + reconciliation sweep produced.

**Anti-horizontal-phasing check:** After this slice a Copilot user can invoke
jig's subagents — new end-to-end capability.
