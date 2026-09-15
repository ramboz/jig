---
status: DRAFT
dependencies: [113-04]
last_verified:
# arch_review: true  # permission-decision translation + the mapped/unmappable inventory
---

## Slice 113-05 — enforcing-hooks-and-permissions

**Goal:** jig's gates keep their teeth under Copilot — the permission-decision
hooks (spec-gate, review-evidence, bug-closure) translated to Copilot's
`permissionRequest`/`preToolUse` decision schema, plus the security-floor
permissions rendered in Copilot syntax — with every hook **mapped or explicitly
recorded as unmappable**.

**DoR:**
- ✅ 113-04 done (advisory-hook translation + schema proven).
- ✅ 113-01 finding recorded Copilot's permission-decision (allow/deny) response
  shape.

**Acceptance Criteria:**

1. **Decision-schema translation.** Enforcing hooks render to Copilot's
   allow/deny decision schema so a blocking gate actually blocks in a Copilot
   session (or deterministic substitute). A test asserts a translated enforcing
   hook denies the disallowed action.
2. **Mapped-or-unmappable inventory (invariant).** The slice produces an explicit
   inventory: every jig hook is either mapped to a Copilot event with equivalent
   enforcement, or recorded as unmappable with the residual documented (mirroring
   servo ADR-0028's honesty). No jig hook is silently dropped. A Claude event
   with no Copilot equivalent degrades **visibly** (documented residual), never
   silently.
3. **Permissions floor.** The jig security-floor `permissions.deny` set renders
   into `hosts/copilot/.github/copilot/settings.json` using Copilot syntax
   (e.g. `shell(git:*)`), with the per-session-vs-persistent difference noted.

**DoD:**
- [ ] All ACs pass; full suite green; new tests fail when the feature is removed.
- [ ] Inventory written where a maintainer will find it (architecture.md and/or
      the slice record); residuals cross-linked to refinement-todo if follow-up
      is needed.
- [ ] Reviewed by `reviewer` subagent (compliance + craft; arch pass).
- [ ] Deviation log + reconciliation sweep produced.

**Anti-horizontal-phasing check:** After this slice jig's enforced lifecycle
gates work for a Copilot user (or are documented as degraded) — the core value.
