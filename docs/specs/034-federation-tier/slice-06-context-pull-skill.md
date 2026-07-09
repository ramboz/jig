---
status: DEFERRED
dependencies: ["034-02"]
last_verified:
---

## Slice 034-06 — context-pull-skill

**Resolution trigger:** A real distributed-peer / multi-member consumer starts *building* (see spec.md § Peer tier) — jig state scaffolded into many member repos coordinated by a central. Re-open via DEFERRED → DRAFT.

**Goal:** Ship `jig:context-pull` — a declarative "load the hot caches
for repos X, Y, Z" skill that protects the ~40% context ceiling by
making cross-repo context loads explicit and short-lived.

**DoR:**
- Slice 034-02 is DONE (registry queryable).

**Acceptance Criteria:**

1. **`jig:context-pull <repo1> <repo2> ...`** fetches each named
   repo's `CLAUDE.md` (or scaffold-mode `AGENTS.md`) via the repo
   access provider and loads it as `additionalContext` for the current
   session.
2. **Per-call, not persistent.** Pulled context is not written to
   local disk; it's session-scoped. A new session re-issues
   `context-pull` if needed.
3. **Refuses when the projected fill exceeds a budget.** A
   configurable ceiling (default: bring the session's total load to
   no more than 50% of an Opus 4.7 context window) is enforced; the
   helper refuses the call rather than silently overshooting.
4. **`--list` prints what's available** (every registered repo with
   its hot-cache path) without pulling anything.
5. **Standalone-safe.** Standalone scaffold installs do not install
   Tier 2 skills. If the skill is invoked from a manually copied or
   stale install in standalone mode, it refuses with "context-pull
   requires federation; not configured".
6. **No central dependency at call time** for already-resolved repos
   — if `repos.yaml` is cached locally (slice 034-09), context-pull
   uses the cache rather than re-fetching the registry.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises happy path, budget
      refusal, list mode, standalone refusal.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.

**Anti-horizontal-phasing check:** After this slice lands, a dev
working on a cross-repo feature can pull the two specific upstream
hot caches they need without loading the other 37, and the session
stays below the dumb-zone ceiling.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
