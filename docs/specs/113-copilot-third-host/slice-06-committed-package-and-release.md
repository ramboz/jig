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
- ✅ 113-02..05 done (renderer + skeleton, agents, and a **representative** hook
  set: 3 advisory hooks in 113-04 + 3 enforcing/floor hooks in 113-05). The
  renderer does **not** yet emit jig's *complete* hook set — the remaining
  `MAPPABLE` advisory hooks recorded in `_JIG_HOOK_INVENTORY` are rendered here
  (AC6) to reach full Claude↔Copilot hook parity.

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
5. **Package completeness (rewritten command targets resolve).** The committed
   `hosts/copilot/` ships every tree a rendered skill/hook body references, so the
   `${CLAUDE_PLUGIN_ROOT}` → Copilot path rewrites actually resolve — notably the
   `scripts/` tree (e.g. `spec_lint.py`, referenced by the `analyze` skill body and
   rewritten to `.github/scripts/…` in 113-04, but **not yet shipped**) alongside the
   already-shipped `.github/skills/`, `.github/agents/`, `.github/hooks/`. A test
   asserts no rendered skill/hook command points at a path absent from the package.
   (Surfaced by the 113-04 compliance review — the skill-body rewrite currently
   targets an unshipped dir; homed here as the packaging-completeness slice.)

6. **Remaining advisory-hook parity (completes the mapped-or-unmappable
   invariant).** Every hook the 113-05 inventory marks `MAPPABLE` — the remaining
   advisory context/nudge hooks (`context-check`, `post-edit-verify`,
   `project-orient`, `semantic-index`, `memory-scan`,
   `decision-inflight`[userPromptSubmit], `task-capture`, `decision-capture`,
   `claim-check`) — is rendered into `hosts/copilot/.github/hooks/` via the
   existing advisory-render path (translate + adapter + `render_copilot_hook_file`,
   fail-open preserved), so the Copilot host fires jig's **full** context/nudge
   hook set. Each flips `MAPPABLE`→`SHIPPED` in `_JIG_HOOK_INVENTORY`; the only
   non-`SHIPPED` residuals that survive are the genuinely `UNMAPPABLE` ones
   (Task/Skill/AskUserQuestion), which stay documented. A test asserts **no
   `MAPPABLE` entry remains** (every inventory entry is `SHIPPED` or `UNMAPPABLE`)
   — closing the ADR-0061 "mapped or explicitly unmappable, never silently
   dropped" invariant for real, not just in the ledger.
   (Surfaced by the 113-05 arch review — the inventory homed these hooks to 113-06
   but no AC owned rendering them; this AC is that home.)

**DoD:**
- [ ] All ACs pass; full suite green; new tests fail when the feature is removed.
- [ ] `uvx ruff check .` + host-package drift `--check` clean (CI-equivalent gate).
- [ ] Reviewed by `reviewer` subagent (compliance + craft; arch pass).
- [ ] Deviation log + reconciliation sweep produced.
- [ ] Spec 113 closed out: compress the Active-specs entry per spec 025-01;
      migrate load-bearing invariants to the status-board Notes column.

**Anti-horizontal-phasing check:** After this slice any Copilot user installs jig
with one command from the marketplace and gets a released, drift-guarded package.
