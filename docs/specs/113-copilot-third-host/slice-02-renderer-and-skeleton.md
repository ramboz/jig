---
status: DRAFT
dependencies: [113-01, adr-0061]
last_verified:
# arch_review: true  # this slice adds a HostRenderer subclass + dispatch wiring
---

## Slice 113-02 — renderer-and-skeleton

**Goal:** A Copilot user can install jig and invoke its skills — the walking
skeleton: a `CopilotScaffoldRenderer` wired into host dispatch that renders a
minimal committed `hosts/copilot/` package whose skills and instructions load
correctly under Copilot CLI.

**DoR:**
- ✅ 113-01 done: verified plugin-manifest shape, skill discovery root, and the
  namespace/description loader rules.

**Acceptance Criteria:**

1. **Renderer + dispatch.** A `CopilotScaffoldRenderer(HostRenderer)` exists and
   `renderer_for_host("copilot")` / `read_host_renderer` resolve it; unknown-host
   behavior is unchanged for `claude`/`codex`.
2. **Loader-compat invariant (enforced in the render layer).** Every emitted
   Copilot skill has a namespace-safe name (no `:`) and a description ≤1024
   chars, with the full description preserved in the SKILL.md body. A source
   skill that would violate either limit is transformed by the renderer, not the
   source — Claude/Codex output is byte-for-byte unchanged. A test proves a
   >1024-char source description (e.g. `memory-sync`) renders ≤1024 for Copilot.
3. **Instructions rendered.** `hosts/copilot/.github/copilot-instructions.md` is
   generated from the canonical brief/`CLAUDE.md` source, without double-loading
   against the `CLAUDE.md` Copilot also reads (per the 113-01 finding).
4. **Skeleton installs + runs.** The rendered `hosts/copilot/` package installs
   in a Copilot CLI session (or the closest deterministic substitute, recorded
   honestly) and at least one jig skill loads and is invocable.

**DoD:**
- [ ] All ACs pass; full suite green; new tests fail when the feature is removed.
- [ ] Claude/Codex host output unchanged (drift guard clean for those hosts).
- [ ] Reviewed by `reviewer` subagent (compliance + craft; arch pass — this slice
      sets `arch_review: true`).
- [ ] Deviation log + reconciliation sweep produced.

**Anti-horizontal-phasing check:** After this slice a Copilot user can install
jig and run a skill — observable end-to-end value, not internal plumbing.
