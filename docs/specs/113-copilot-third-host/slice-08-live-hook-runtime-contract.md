---
status: DRAFT
dependencies: [113-07]
last_verified:
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
- [ ] All ACs pass; focused hook/package tests and the full suite are green.
- [ ] Each new test is red when its hook command, response translation, or
      adapter dependency is removed.
- [ ] Reviewed by `reviewer` subagent — compliance, craft, and architecture
      passes recorded.
- [ ] Deviation log and reconciliation sweep produced under this heading.
- [ ] Reconciliation review passed.

**Anti-horizontal-phasing check:** After this slice, a Copilot user sees jig's
nudges and is blocked by jig's gates in a real installed plugin session.

### Deviation log (after reconciliation)

_Pending implementation._

### Reconciliation sweep

_Pending implementation._
