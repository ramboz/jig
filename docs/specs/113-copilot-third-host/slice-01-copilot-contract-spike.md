---
status: DRAFT
kind: spike
dependencies: [adr-0061]
last_verified:
---

## Slice 113-01 — copilot-contract-spike

**Goal:** Resolve the external, Copilot-owned unknowns ADR-0061 flagged so the
rendering slices commit to a verified shape rather than a guessed one.

**Question:** What exact contract must jig's committed `hosts/copilot/` package
present to (a) install via `/plugin`, (b) have its skills load (name/namespace +
description limits), (c) load custom agents (file form/frontmatter), and (d)
register hooks — under a live GitHub Copilot CLI at Adobe?

**Time-box:** 1 day.

**Findings:** _Filled during IN_PROGRESS._

**Outcome:** _Set at DONE — e.g. `spec 113-02..06 unblocked` and/or
`ADR-0061 amended` (open-questions resolved)._

**DoR:**
- ✅ ADR-0061 recorded (Proposed).
- ✅ Access to a licensed GitHub Copilot CLI session (`copilot`) on the Adobe
  tenant, and to GitHub's Copilot CLI hooks/agents/plugin reference docs.

**Acceptance Criteria:**

1. **Plugin install verified.** Record whether `/plugin` installs jig's existing
   Claude-format marketplace package as-is, and the exact manifest/marketplace
   shape a committed `hosts/copilot/` must present (with the commands run and
   their output).
2. **Skill-load contract verified.** Confirm whether the `jig:` namespace
   surfaces as a `:`-bearing loaded skill name (a loader breaker) and confirm the
   >1024-char description failure on `memory-sync`/`vision-elicitation` in a live
   session; record the discovery roots Copilot actually reads
   (`.github/skills` vs `.claude/skills` vs `.agents/skills`).
3. **Agent + hook forms verified.** Resolve the `.github/agents/*.md` vs
   `*.agent.md` extension, the agent frontmatter fields Copilot honors, and the
   concrete Copilot hook JSON schema (event names, payload, and allow/deny
   response shape) for at least one advisory and one permission-decision hook.
4. **Open questions dispositioned.** Each ADR-0061 `## Open questions` item is
   answered or explicitly carried forward; if a finding contradicts an ADR-0061
   premise, an amendment/superseding note is raised (not silently absorbed).

**DoD:**
- [ ] Findings block filled with commands run + observed output (grounding).
- [ ] Outcome set; downstream slices' DoR updated with the verified shape.
- [ ] `docs/refinement-todo.md` updated if any decision was deferred.

**Anti-horizontal-phasing check:** Exempt — `kind: spike`. Delivers verified
decisions that unblock 113-02..06, not user-facing behavior.
