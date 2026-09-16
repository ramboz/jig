---
status: RECONCILED
dependencies: [113-06]
last_verified: 2026-09-16
arch_review: true
claimed_by: copilot-plugin-audit
---

## Slice 113-07 — plugin-component-discovery

**Goal:** A user who installs `ramboz/jig:hosts/copilot` gets jig's skills,
custom agents, and hook registrations discovered by a clean Copilot CLI
session, rather than a manifest that installs successfully but exposes no jig
components.

**DoR:**
- ✅ The audit has reproduced the failure outside this repository: the installed
  `jig` v2.15.0 plugin appears in `copilot plugin list`, but a clean directory's
  `copilot skill list` exposes none of its plugin skills and
  `copilot --agent reviewer` refuses the agent.
- ✅ Copilot's legacy-plugin reference establishes that non-default component
  directories must be declared by the manifest; the current package keeps its
  components under `.github/`.

**Acceptance Criteria:**

1. **Runnable legacy manifest.** The rendered `hosts/copilot/.plugin/plugin.json`
   declares the exact skills, agents, and hook configuration locations that
   Copilot's legacy loader consumes, or the renderer moves those artifacts to
   its documented defaults. No field is guessed: the selected shape is backed
   by the Copilot CLI reference and a live probe.
2. **Installed-component smoke.** A hermetic test installs the committed
   package into an isolated `COPILOT_HOME`, starts Copilot from an empty
   directory, and proves the plugin's `spec-workflow` skill and `reviewer`
   agent are discoverable. It also proves the hook configuration is accepted
   rather than merely present on disk. Authentication-dependent execution is
   not required for this discovery test.
3. **Contract validation.** The package validator rejects a manifest whose
   declared component paths are absent, misplaced, or do not contain the
   expected component type. The same check protects generated and release-zip
   packages.
4. **Distribution documentation.** The install and verification instructions
   name the exact CLI checks users can run after installation and no longer
   present plugin presence in `copilot plugin list` as proof that components
   loaded.

**DoD:**
- [x] All ACs pass; focused build/package tests are green. The full suite has
      pre-existing remote-fixture and board-staleness failures outside this
      slice's package path; see the deviation log.
- [x] Tests demonstrate the old path-free manifest fails discovery and the
      corrected package succeeds.
- [x] Reviewed by `reviewer` subagent — compliance, craft, and architecture
      passes recorded.
- [x] Deviation log and reconciliation sweep produced under this heading.
- [x] Reconciliation review passed.

**Anti-horizontal-phasing check:** After this slice, installing the published
plugin yields an immediately usable jig skill and custom agent in Copilot CLI.

### Deviation log (after reconciliation)

1. **Legacy discovery contract.** The generated `.plugin/plugin.json` now
   declares the existing `.github/skills`, `.github/agents`, and generated
   `.github/hooks/hooks.json` paths. The builder preserves the per-hook JSON
   files as the source-map-friendly rendered artifacts and emits one
   loader-facing aggregate configuration file after all of them are rendered.
2. **Verification boundary.** The isolated `COPILOT_HOME` smoke installs the
   committed package from a clean directory, proves `spec-workflow` and
   `jig:reviewer` discovery, and reports hook-loader rejection. It deliberately
   stops before firing hooks; that runtime contract belongs to 113-08.
3. **Validation result.** Focused Copilot build/contract tests (202 tests),
   host-package drift check, Copilot release-zip build and smoke, and the live
   discovery smoke passed. The repository-wide runner remains red on existing
   remote-fixture failures and board-staleness caused by this in-flight spec
   mutation; no test was weakened or skipped.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` / `CONTRIBUTING.md` | `updated` | Install verification now distinguishes installed-plugin presence from loaded components. |
| `docs/architecture.md` | `updated` | Documents the declared legacy component paths and loader-facing aggregate. |
| `hosts/copilot/` | `updated` | Regenerated package carries the runnable manifest and aggregate hook configuration. |
| `hosts/claude/` / `hosts/codex/` | `updated` | Regenerated package mirrors of shared source documentation and validator changes. |
| `docs/product-vision.md` / `docs/adoption-readiness.md` | `updated` | Existing spec-113 Copilot host positioning and adopter guidance remain part of the reconciled documentation set. |
| `docs/refinement-todo.md` | `updated` | Records the command-resolution, body-normalization, and conversational-input residuals that 113-08 and 113-09 own. |
| `docs/specs/README.md` | `updated` | Regenerated after adding and advancing these remediation slices. |
| Primer surfaces (`CLAUDE.md`) | `updated` | Existing spec-113 Copilot package reference remains accurate; no close-out compression while the spec is in flight. |
| `docs/inbox.md` / `docs/memory/**` | `no-op` | No new durable decision or learning beyond the slice record. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0061 is indexed as the decision implementing Copilot's third-host architecture. |
