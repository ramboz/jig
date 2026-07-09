---
status: DEFERRED
dependencies: ["034-02", "034-07"]
last_verified:
arch_review: true
---

## Slice 034-09 — repo-sync-and-drift-hook

**Resolution trigger:** A real distributed-peer / multi-member consumer starts *building* (see spec.md § Peer tier) — jig state scaffolded into many member repos coordinated by a central. Re-open via DEFERRED → DRAFT.

**Goal:** Ship `jig:repo-sync` (member-side pull / check / update) and
`jig-federation-drift` (SessionStart hook in member mode) so members
stay aligned with federation authority repos without polling.

**DoR:**
- Slice 034-02 is DONE.
- Slice 034-07 is DONE (read-through behaviors that drift detection
  references).

**Acceptance Criteria:**

1. **`jig:repo-sync pull`** fetches current federation state (jig
   version, authority conventions content hashes, ADR index hashes,
   registry cache fingerprint, provider metadata timestamp) and writes
   `.jig/federation-state.json` locally.
2. **`jig:repo-sync check`** compares local state vs. declared
   authorities, prints structured drift report (jig-version,
   conventions-hash by authority, adr-index-hash by authority,
   registry-cache fingerprint). Exits 0 if aligned, 1 if drift found,
   2 on helper error.
3. **`jig:repo-sync update`** applies the update: re-fetches
   `repos.yaml` for the local cache, refreshes authority pointers and
   generated caches, re-runs `scaffold-init --role=member` in
   upgrade-in-place mode if the jig version lags.
4. **`jig-federation-drift` hook (SessionStart, member mode only)**
   reads `.jig/federation-state.json`; if missing, >24h old, or
   shows drift, prints a one-line nudge directing the user at
   `/jig:repo-sync update`. Never blocks; exit 0 always.
5. **Hook is gated.** No-op in standalone or central role. Honors
   `JIG_FEDERATION_DRIFT=0` env opt-out.
6. **Cache is git-ignored.** `.jig/federation-state.json` and provider
   fingerprints land in the member repo's `.gitignore` (or
   `.jig/.gitignore`) to avoid noise in PRs.
7. **Provider failures degrade cleanly.** If an authority repo is
   unreachable, `check` reports the stale/missing authority while still
   comparing any reachable local/federated state. The SessionStart hook
   never blocks routine work because of an unreachable authority.

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
