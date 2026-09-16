---
status: DONE
dependencies: [113-07]
last_verified: 2026-09-16
arch_review: true
---

## Slice 113-08 — live-hook-runtime-contract

**Goal:** Copilot executes jig's installed hook commands from the real plugin
cache with the expected working directory, input payload, advisory response,
and enforcing deny behavior, so a loaded hook cannot be silently inert.

**DoR:**
- ✅ 113-07 makes the package components discoverable in an isolated Copilot
  installation.
- ✅ The audit has identified that existing tests invoke the adapter directly,
  while rendered commands use a cwd-relative `.github/...` path whose live
  cache-install resolution is unproven.

**Acceptance Criteria:**

1. **Runtime command resolution.** A Copilot CLI-backed integration test causes
   at least one advisory hook and one enforcing hook to execute from an
   installed package, proving the generated command path, current working
   directory, adapter location, and stdin payload are compatible.
2. **Observable advisory behavior.** The advisory probe asserts the emitted
   Copilot continuation/context response, not just a zero exit code, so
   fail-open masking cannot produce a false pass.
3. **Observable enforcement.** The enforcing probe requests a known-disallowed
   operation and verifies Copilot receives a deny decision with a reason. A
   safe operation remains allowed.
4. **Executable package contract.** Static validation resolves every generated
   hook command and its adapter dependency from the installed package layout,
   and rejects invalid event names, malformed matchers, missing executables,
   or missing command dependencies.
5. **Supported-test boundary.** If a headless CLI invocation cannot fire hooks,
   the repository supplies and documents a repeatable authenticated/manual
   smoke command with machine-checkable success evidence; static tests are
   explicitly labelled package checks rather than E2E proof.

**DoD:**
- [x] All ACs pass; focused hook/package tests are green. The full suite's
      unrelated remote-fixture baseline remains red; see the deviation log.
- [x] Each new test is red when its hook command, response translation, or
      adapter dependency is removed.
- [x] Reviewed by `reviewer` subagent — compliance, craft, and architecture
      passes recorded.
- [x] Deviation log and reconciliation sweep produced under this heading.
- [x] Reconciliation review passed.

**Anti-horizontal-phasing check:** After this slice, a Copilot user sees jig's
nudges and is blocked by jig's gates in a real installed plugin session.

### Deviation log (after reconciliation)

1. **Runtime proof.** `copilot_live_hook_smoke.py` performs an authenticated,
   isolated-package probe and emits machine-readable PASS, FAIL, or
   INCONCLUSIVE evidence. It observes advisory `additionalContext`, a real
   protected-file deny with a reason, and a permitted safe edit; the expensive
   probe is opt-in in normal test runs.
2. **Path contract settled.** The live probe proves `.github/...` hook command
   paths resolve from the installed plugin root while Copilot passes the
   session repository as `workingDirectory`; the adapter exports that latter
   value as `CLAUDE_PROJECT_DIR`. Earlier best-hypothesis wording was corrected
   inline rather than retained as a live contradiction.
3. **Validator hardening.** Static package checks now reject invalid events or
   matchers, adapter bypasses, path escapes, missing dependencies, and
   non-executable shell targets. They remain package validation, not a
   substitute for the live smoke.
4. **Validation.** 233 focused tests passed, including the opt-in live-smoke
   test. A fresh authenticated run is captured at
   [`evidence/slice-08-live-hook-smoke.json`](evidence/slice-08-live-hook-smoke.json)
   with advisory context, deny reason, and safe-control results. The smoke
   runner now resolves its package argument to an absolute path before plugin
   installation; a bare relative `hosts/copilot` was otherwise parsed by
   Copilot as a GitHub repository identifier. The full suite has unrelated
   remote-fixture baseline failures; no test was weakened or skipped.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `scripts/copilot_live_hook_smoke.py` / tests / `evidence/` | `updated` | Adds machine-checkable, installed-package advisory, deny, and safe-operation proof, including a persisted authenticated PASS result. |
| `scripts/install_contract.py` / `scripts/test_install_contract.py` | `updated` | Validates executable hook dependencies in the rendered package. |
| `scripts/test_build_copilot_plugin.py` | `updated` | Labels static package checks explicitly as non-E2E and covers their retained rendering contract. |
| `skills/scaffold-init/scaffold.py` / `hosts/**` | `updated` | Documents the now-proven command/CWD binding and regenerates packages. |
| `CONTRIBUTING.md` / `docs/architecture.md` | `updated` | Separates static package checks from authenticated E2E smoke usage. |
| `README.md` / `CHANGELOG.md` / host root manifests / release workflow | `no-op` | Checked as front-door and release surfaces; their prior spec-113 updates remain accurate and this runtime-contract slice needs no additional change. |
| `docs/adoption-readiness.md` | `no-op` | Existing Copilot readiness guidance remains accurate. |
| `docs/product-vision.md` / `docs/refinement-todo.md` | `no-op` | Runtime command-resolution residual is closed; conversational parity remains owned by 113-09. |
| `docs/specs/README.md` | `deferred` | Regenerate after terminal lifecycle transition. |
| Primer surfaces (`CLAUDE.md`) / `docs/inbox.md` / `docs/memory/**` | `no-op` | Existing Copilot primer entry remains accurate; spec remains in flight with no new standalone learning. |
| `docs/decisions/README.md` / ADR index | `no-op` | Implements ADR-0061 without changing the decision. |
| `docs/specs/113-copilot-third-host/{spec.md,slice-07-plugin-component-discovery.md,reviews/slice-07-*.md,slice-09-conversational-hook-parity.md}` | `no-op` | Checked as adjacent lifecycle records; 113-07 is closed and 113-09 remains the separately scoped next slice. |
| `docs/specs/113-copilot-third-host/reviews/slice-08-{compliance,craft,arch}.md` | `updated` | Durable required post-implementation verdict evidence for this slice. |
