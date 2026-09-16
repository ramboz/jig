---
status: DONE
dependencies: [113-02, 113-03, 113-04, 113-05]
last_verified: 2026-09-16
arch_review: true  # tri-host release-please coordination + multi-event hook-file merge + verification-substitute design
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
   fail-open preserved), so the Copilot host **registers** jig's full context/nudge
   hook set. Each flips `MAPPABLE`→`SHIPPED` in `_JIG_HOOK_INVENTORY`; the only
   non-`SHIPPED` residuals that survive are the genuinely `UNMAPPABLE` ones
   (Task/Skill/AskUserQuestion), which stay documented. A test asserts **no
   `MAPPABLE` entry remains** (every inventory entry is `SHIPPED` or `UNMAPPABLE`)
   — closing the ADR-0061 "mapped or explicitly unmappable, never silently
   dropped" invariant for real, not just in the ledger.
   (Surfaced by the 113-05 arch review — the inventory homed these hooks to 113-06
   but no AC owned rendering them; this AC is that home.)

   **Input-parity caveat (113-06 craft review).** Registration ≠ full behavior:
   a hook that reads host-supplied *conversational* input only acts when Copilot
   supplies that field on the hook's event. `copilot_hook_adapter.translate_payload`
   forwards `prompt` (`UserPromptSubmittedHookInput`), so `memory-scan` and
   `decision-inflight` fire fully. Copilot supplies **no inline `messages`** on
   `agentStop` (it gives `transcriptPath`, which no jig hook consumes there), so the
   three `messages`-reading Stop hooks (`task-capture`, `claim-check`,
   `decision-capture`) and `context-check`'s transcript-tail on `sessionStart`
   degrade to their designed fail-open no-op — a **documented input residual** (see
   `docs/refinement-todo.md`, "Copilot conversational-input parity"), not a silent
   drop. (`decision-capture`'s in-flight decision stubs, surfaced by the now-working
   `decision-inflight`, still land.) `context-check`'s Read-tracking on `preToolUse`
   and the non-input hooks (`post-edit-verify`, `project-orient`, `semantic-index`)
   fire fully.

**DoD:**
- [x] All ACs pass; full suite green (4862 tests, pyright clean; the only reds were
      2 board-staleness `SpecBoardIntegrityTests`, resolved by `status-board` regen —
      the recurring post-transition pattern, not a defect); new tests fail when the
      feature is removed (merge-guard, completeness, no-MAPPABLE, prompt-forwarding
      E2E all red-before/green-after).
- [x] `uvx ruff check .` + host-package drift `--check` clean (CI-equivalent gate).
- [x] Reviewed by `reviewer` subagent — compliance (pass) + craft (pass, after a
      real blocker + a correction over two rounds) + arch (pass); verdicts under
      `reviews/slice-06-{compliance,craft,arch}.md`.
- [x] Deviation log + reconciliation sweep produced (below).
- [x] Spec 113 closed out: Active-specs entry compressed to a Key-terms line per
      spec 025-01; load-bearing invariants migrated to the status-board Notes column;
      spec.md → DONE.

**Anti-horizontal-phasing check:** After this slice any Copilot user installs jig
with one command from the marketplace and gets a released, drift-guarded package.

### Deviation log (after reconciliation)

- **Multi-event hook-file merge (design).** `_write_copilot_hooks` groups hook
  registrations BY SCRIPT and emits ONE `.github/hooks/<stem>.json` per script with
  all its events under Copilot's flat multi-event schema, instead of one file per
  registration. `render_copilot_hook_file` stays a pure single-event source→dict
  function (113-04/05 contract unchanged); the builder owns grouping. Single-event
  scripts stay byte-identical (the 6 prior hooks are drift-clean). Fixes a real
  filename collision: `jig-context-check.sh` (3 events) would have overwritten its
  own file twice, silently dropping 2 registrations. A `raise`-on-key-collision guard
  (arch nit) makes the non-lossy invariant enforced, not emergent.
- **Tri-host release-please coordination (orchestrator).** The copilot committed
  manifest (`hosts/copilot/.plugin/plugin.json`, no third root descriptor — it takes
  the root `.claude-plugin` version at build time) is wired into release-please
  `extra-files` (5 manifests) + guarded by `test_release_config` (now expects 5).
  `release.yml` builds/smokes/uploads the copilot zip + an install note. Closes the
  v2.0.1-class "committed manifest stale at the tag → build refuses → no host zip"
  failure for copilot.
- **Package completeness (AC5) — closes refinement-todo residual (b).**
  `_copy_runtime_scripts` + `_copy_templates` ship `.github/scripts/spec_lint.py`
  (via new `install_contract.COPILOT_INCLUDE_SCRIPT_FILES`) + `.github/templates/`
  (with the `${CLAUDE_PLUGIN_ROOT}`→`.github/` `.md.template` rewrite, mirroring
  codex), so the rewritten skill-body paths resolve. `PackageCompletenessTests`
  asserts no rendered skill/hook reference points at a path absent from the package.
- **Per-host verification (AC3).** `install_contract.validate_copilot_package` — a
  static, deterministic shape-validator (`.plugin/plugin.json` + `.github/{skills,
  agents,hooks,scripts,templates}` + flat hook schema + loader limit), wired into
  `build_release_zip._smoke_copilot`. The live `copilot` CLI probe was SKIPPED
  (spec-sanctioned "closest deterministic substitute, recorded honestly"): headless
  `copilot -p` does not reliably fire repo hooks (folder-trust/mode limits). This
  live-install gap is subsumed by refinement-todo residual (a).
- **AC6 input-parity correction (craft review, two rounds).** The 9 new hooks route
  through `copilot_hook_adapter.translate_payload`, which (from 113-04) forwarded only
  `source`/`tool_input`. Six read more, so they were registered-but-inert and AC6
  over-claimed "fires the FULL hook set". RESOLUTION grounded in the Copilot SDK
  types (CLI 1.0.86): the adapter now forwards `prompt` (`UserPromptSubmittedHookInput`)
  → `memory-scan` + `decision-inflight` fire fully (unit + E2E tests). The three
  `messages`-reading Stop hooks (`task-capture`, `claim-check`, `decision-capture`)
  + `context-check`'s `sessionStart` transcript-tail are host-gated — Copilot supplies
  no inline `messages` on `agentStop` (it gives `transcriptPath`, which no jig hook
  consumes there) and no `transcriptPath` on `sessionStart`. Honestly reclassified
  INPUT-DEGRADED (fail-open no-op) across `_JIG_HOOK_INVENTORY` notes, AC6's
  "Input-parity caveat", and a new refinement-todo entry; AC6 "fires" → "registers".
  A first correction wrongly claimed `decision-capture` was fixed via `transcriptPath`;
  the craft re-review caught that it reads `messages`, so the dead `transcriptPath`
  forwarding was dropped (pinned by a negative test) and `decision-capture` re-homed
  to the degraded set (its in-flight stubs still land via the fixed `decision-inflight`).
- **Nits.** Removed dead `install_contract._COPILOT_HOOK_REQUIRED_ENTRY_FIELDS`.
  Fixed a `build_copilot_plugin.py` docstring imprecision (`decision_scratch` DOES
  have one nested lib import, `decision_scan`, which is shipped).
- **Positioning docs.** `docs/product-vision.md` general-positioning lines updated to
  the tri-host reality (Claude Code, Codex, GitHub Copilot CLI); scaffold-context
  lines (and `docs/prompts.md`) left as-is — Copilot is plugin-install, not scaffold,
  so those correctly address the scaffold audience.
- **Residual (a) stays open (arch note).** The rewritten `.github/…` command-path
  *spelling* resolves WITHIN the package (completeness-test-verified), but its live
  resolution under a `/plugin` cache install is unverified. So spec 113 closes on full
  **package** parity + a tracked runtime-command-resolution caveat (refinement-todo
  residual (a)) — carried into the primer compression, not dropped as "done".

### Reconciliation sweep

- **docs/architecture.md** — `updated` (implementer): host-support matrix +Copilot
  rows; a "Copilot plugin packaging" section; install path + tri-host topology; the
  `_JIG_HOOK_INVENTORY` reference; "dual-host"→"tri-host" in Contract surfaces.
- **README.md / CONTRIBUTING.md** — `updated` (implementer): Copilot install recipe,
  verify-a-host-install bullet, repo-structure tree, release-zip build/smoke commands.
- **docs/adoption-readiness.md** — `updated` (implementer): Copilot CLI added to the
  host-fit bullets/prerequisites/checklist (the "Claude Code or Codex" disqualifier
  was factually wrong once Copilot shipped).
- **docs/product-vision.md** — `updated`: general-positioning lines → tri-host (above).
- **docs/refinement-todo.md** — `updated`: residual (b) marked CLOSED by 113-06 AC5;
  residual (a) marked OPEN (runtime-command spelling); NEW "Copilot conversational-input
  parity" entry homing the INPUT-DEGRADED hooks.
- **.github/release-please-config.json + workflows/release.yml + test_release_config.py**
  — `updated` (orchestrator): copilot manifest + zip build/smoke/upload/note + guard test.
- **Architecture impact / ADR** — `no-op` (no new ADR): implements ADR-0061; the
  input-parity degradation is within its "degrade VISIBLY, not silently" invariant.
- **docs/conventions.md / Lightweight decisions / Inbox** — `no-op`.
- **CLAUDE.md primer** — `updated` (spec close): Active-specs "shipped through 112" →
  113; compressed spec-113 Key-terms line (tri-host / Copilot third host), preserving
  the full-**package**-parity + runtime-caveat + input-parity residual framing.
- **hosts/ regeneration** — `updated`: `build_host_packages.py` re-emitted the copilot
  package + scaffold/adapter mirrors; `--check` clean.
- **Status board** — `updated (regenerated)` after the DONE transition; per-slice
  invariants migrated to the Notes column.
- **Memory-sync** — `copilot-migration-tri-host` project memory updated (spec 113
  DONE on the branch; jig-half complete).
