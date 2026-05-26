---
status: DRAFT
dependencies: ["034-02", "034-07"]
last_verified:
arch_review: true
---

## Slice 034-09 — repo-sync-and-drift-hook

**Goal:** Ship `jig:repo-sync` (member-side pull / check / update) and
`jig-federation-drift` (SessionStart hook in member mode) so members
stay aligned with central without polling.

**DoR:**
- Slice 034-02 is DONE.
- Slice 034-07 is DONE (read-through behaviors that drift detection
  references).

**Acceptance Criteria:**

1. **`jig:repo-sync pull`** fetches current central state (jig
   version, conventions content hash, ADR index hash, registry
   timestamp) and writes `.jig/federation-state.json` locally.
2. **`jig:repo-sync check`** compares local state vs. central,
   prints structured drift report (jig-version, conventions-hash,
   adr-index-hash, registry-timestamp). Exits 0 if aligned, 1 if
   drift found, 2 on helper error.
3. **`jig:repo-sync update`** applies the update: re-fetches
   `repos.yaml` for the local cache, refreshes conventions pointer,
   re-runs `scaffold-init --role=member` in upgrade-in-place mode if
   the jig version lags.
4. **`jig-federation-drift` hook (SessionStart, member mode only)**
   reads `.jig/federation-state.json`; if missing, >24h old, or
   shows drift, prints a one-line nudge directing the user at
   `/jig:repo-sync update`. Never blocks; exit 0 always.
5. **Hook is gated.** No-op in standalone or central role. Honors
   `JIG_FEDERATION_DRIFT=0` env opt-out.
6. **Cache is git-ignored.** `.jig/federation-state.json` lands in
   the member repo's `.gitignore` (or `.jig/.gitignore`) to avoid
   noise in PRs.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises pull / check / update +
      hook behavior across role gates.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] `docs/architecture.md` updated to describe the federation
      drift-detection model (cache file + SessionStart hook).

**Anti-horizontal-phasing check:** After this slice lands, an
engineer opening a session in a member repo where central has
advanced sees a one-line nudge in their SessionStart output and can
run one command to catch up.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
