---
status: DRAFT
dependencies: ["034-01"]
last_verified:
arch_review: true
---

## Slice 034-11 — cross-repo-impact-hook

**Goal:** Ship `jig-cross-repo-impact` — a PreToolUse hook on
Edit/Write that warns when the user is editing a file declared as a
typed contract surface in the local repo's declared or generated
federation metadata, nudging them toward cross-repo coordination before
the edit lands.

**DoR:**
- Slice 034-01 is DONE.

**Acceptance Criteria:**

1. **`hooks/scripts/jig-cross-repo-impact.sh` fires on PreToolUse
   `Edit|Write|MultiEdit`** and matches the edited path against the
   local repo's declared/discovered contract surfaces in registry and
   generated federation cache metadata.
2. **On match, emits `additionalContext`** with a structured nudge:
   "This file is a federation contract surface for <repo>. Edits may
   affect <list of dependent cross-repo specs>. Consider running
   `/jig:cross-repo-spec` to coordinate, or `/jig:adr-workflow new`
   to record a boundary change."
3. **Never blocks.** Soft warning only; exit 0 always.
4. **Standalone / central mode no-op.** Hook self-disables when
   `role: standalone` (no federation metadata to consult) or when the
   repo doesn't appear in `repos.yaml` / generated cache as a member
   with contract surfaces.
5. **Opt-out via `JIG_CROSS_REPO_IMPACT=0`.** Matches the
   established pattern from `jig-post-edit-verify` (slice 027-01)
   and `jig-boundary-change-warn` (slice 005-03).
6. **Scaffold-mode parity.** Hook is wired through
   `_EXPECTED_HOOK_SCRIPTS` so scaffold installs get it alongside
   the other federation-aware hooks.
7. **Typed-surface wording.** The hook output names the surface kind
   when known (`npm-package`, `openapi`, `event-topic`, `db-rpc`,
   `deploy-unit`, etc.) so the user sees why a file edit matters
   beyond raw path overlap.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises match, no-match, opt-out,
      standalone no-op, generated-cache match, typed-surface wording,
      and scaffold-mode install.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] Hook count in `docs/architecture.md` updated (seven → eight).

**Anti-horizontal-phasing check:** After this slice lands, an
engineer about to edit a contract-surface file gets a soft warning
in their session naming the cross-repo specs that may be affected,
before the edit completes.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
