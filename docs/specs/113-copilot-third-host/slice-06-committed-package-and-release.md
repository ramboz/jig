---
status: DRAFT
dependencies: [113-02, 113-03, 113-04, 113-05]
last_verified:
# arch_review: true  # extends the builder/drift/release pipeline to a third host
---

## Slice 113-06 — committed-package-and-release

**Goal:** The Copilot host reaches full parity with Claude and Codex — a
committed, drift-guarded `hosts/copilot/` built by the single builder, a
host-explicit `jig-copilot-vX.Y.Z.zip` release archive, and per-host install
verification — so remote `/plugin` install works from the repo with no build
step.

**DoR:**
- ✅ 113-02..05 done (renderer emits the full `hosts/copilot/` content).

**Acceptance Criteria:**

1. **Single builder + drift guard.** The one host builder regenerates
   `hosts/copilot/` alongside `hosts/claude` and `hosts/codex`; CI regenerates
   and fails on a dirty `git diff` for the copilot package too (extends the
   ADR-0018 drift guard). A test proves a stale `hosts/copilot/` is caught.
2. **Release archive.** `scripts/build_release_zip.py` produces
   `jig-copilot-vX.Y.Z.zip` from the committed package, and release-please is
   coordinated to bump the Copilot manifest version in lockstep with the others
   (no hand-edited versions).
3. **Per-host verification.** A Copilot install/smoke check runs in a Copilot CLI
   environment (or the closest deterministic substitute, recorded honestly),
   independent of the Claude/Codex checks — a green Claude build is not proof
   Copilot installs.
4. **Docs.** README/install docs and `docs/architecture.md` document the Copilot
   install path and the tri-host package topology.

**DoD:**
- [ ] All ACs pass; full suite green; new tests fail when the feature is removed.
- [ ] `uvx ruff check .` + host-package drift `--check` clean (CI-equivalent gate).
- [ ] Reviewed by `reviewer` subagent (compliance + craft; arch pass).
- [ ] Deviation log + reconciliation sweep produced.
- [ ] Spec 113 closed out: compress the Active-specs entry per spec 025-01;
      migrate load-bearing invariants to the status-board Notes column.

**Anti-horizontal-phasing check:** After this slice any Copilot user installs jig
with one command from the marketplace and gets a released, drift-guarded package.
