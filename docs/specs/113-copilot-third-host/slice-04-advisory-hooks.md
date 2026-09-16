---
status: DONE
dependencies: [113-02]
last_verified: 2026-09-15
arch_review: true  # introduces the hook-protocol translation layer
---

## Slice 113-04 — advisory-hooks

**Goal:** jig's advisory nudges fire under Copilot — the `additionalContext`-style
hooks (session git-freshness, boundary-change-warn, lifecycle-entry-gate nudge)
translated onto Copilot's event model and emitted as `.github/hooks/*.json`.

**DoR:**
- ✅ 113-02 done (renderer + skeleton).
- ✅ 113-01 finding recorded the concrete Copilot hook JSON schema (event names,
  payload, response shape) for an advisory hook.

**Acceptance Criteria:**

1. **Event-name + payload translation.** `translate_hook_protocol` on
   `CopilotScaffoldRenderer` maps Claude PascalCase events to Copilot camelCase
   (e.g. `SessionStart`→`sessionStart`, `PostToolUse`→`postToolUse`) and adapts
   the payload/field access the hook scripts read. A test asserts a translated
   advisory hook emits Copilot-shaped JSON.
2. **Advisory hooks emitted.** The git-freshness, boundary-warn, and
   entry-gate-nudge hooks are rendered into `hosts/copilot/.github/hooks/` and
   register in a Copilot session (or deterministic substitute), firing their
   `additionalContext` nudge.
3. **Fail-open preserved.** Each translated advisory hook keeps its fail-open
   posture (best-effort; never blocks the session on error/timeout), matching the
   Claude behavior.
4. **Plugin-root path rewrite (owns the 113-02-deferred gap).** Resolve Copilot's
   plugin-root spelling and rewrite `${CLAUDE_PLUGIN_ROOT}/…` runtime paths for
   Copilot in **both** the translated hook commands **and** the rendered SKILL.md
   bodies (`…/skills/…`, `…/scripts/…`, `…/hooks/scripts/…`), so helper-backed
   skills' commands resolve — closing the gap slice 113-02 honestly deferred (see
   `docs/refinement-todo.md`, "Copilot skill-body + hook-command `${CLAUDE_PLUGIN_ROOT}`
   path rewrite"). If no plugin-root env var exists, record the resolved mechanism
   (absolute path, wrapper, or a documented residual) rather than inventing one.

**DoD:**
- [x] All ACs pass; full suite green (4701 tests, pyright clean); new tests fail
      when the feature is removed (red-before/green-after verified); Claude/Codex
      output byte-identical. (AC4 residuals — plugin-root command-path spelling +
      unshipped `scripts/` — honestly deferred + homed to 113-06.)
- [x] Reviewed by `reviewer` subagent — compliance (pass, R2) + craft (pass) +
      arch (pass); verdicts recorded under `reviews/`.
- [x] Deviation log + reconciliation sweep produced; reconciliation review pass.

**Anti-horizontal-phasing check:** After this slice a Copilot user gets jig's
context nudges in-session — observable behavior.

### Deviation log (after reconciliation)

- **Three contract unknowns resolved (grounded in shipped CLI 1.0.84 + `copilot-sdk/types.d.ts`):**
  (1) `translate_hook_protocol` is a **build-time contract with zero runtime call
  sites repo-wide** (Claude/Codex copies equally unwired) — not a runtime output
  adapter; (2) Claude's `continue` has **no Copilot `HookOutput` analogue** → dropped
  (mapped-or-explicitly-unmappable, not guessed); (3) **no `COPILOT_*PLUGIN*` env
  var** exists — the plugin manifest uses relative paths (`mcpServers: "./.mcp.json"`).
- **Input half of the translation layer (built):** `copilot_hook_adapter.py` — a
  **Copilot-render-only, standalone** shim (never imports `scaffold.py`, never
  modifies canonical scripts) — maps Copilot camelCase hook input → jig's snake_case
  script input: `toolName`→`tool_name` (value-translated), `toolArgs`→`tool_input`
  (with `toolArgs.path`→`file_path`), `sessionId`→`session_id`, `workingDirectory`→
  `CLAUDE_PROJECT_DIR` env. Grounded in `types.d.ts` (BaseHookInput + per-event
  inputs) + app.js edit/view/create tool schemas (`path`). Fail-open (forwards raw on
  error, always exit 0). **All 3 advisory hooks fire** under a real Copilot input
  payload (verified: adapter unit tests + end-to-end tests that execute the actual
  built command string; git-freshness proven via a hermetic behind-`origin/main`
  fixture).
- **Response half DEFERRED to 113-05 (accepted deferral, compliance-reviewed):**
  `translate_hook_protocol`'s response-schema mapping is **not applied at runtime**
  this slice — advisory output works because `additionalContext` is spelled
  identically and Copilot ignores the residual `continue: true` (documented + pinned
  by `ShippedAdvisoryOutputThroughAdapterTests`, not assumed away). The runtime
  response-wiring (strip `continue`; `exit 2`/`block_reason`→`permissionDecision:deny`;
  a per-hook advisory-vs-enforcing mode) is homed to **slice-05 DoR**. The earlier
  "translate_hook_protocol is now genuinely exercised" claim was **corrected across 4
  sites** (build_copilot_plugin + scaffold docstrings + the AC1 test comment) — it was
  misleading.
- **Event/matcher/schema:** PascalCase→camelCase events (`CLAUDE_TO_COPILOT_EVENTS`,
  all 10, single-source vs the `HookType` enum); matcher `Edit|Write|MultiEdit`→
  `edit|create`; one `.github/hooks/<name>.json` per hook, **keyed directly by
  camelCase event**, Claude-compatible `{matcher, hooks:[{type:"command", command,
  timeout}]}` structure.
- **Path rewrite (AC4):** `rewrite_skill_md_paths` + `rewrite_hook_command` rewrite
  `${CLAUDE_PLUGIN_ROOT}/…` → Copilot plugin-relative paths for skill bodies AND hook
  commands. **Residuals (both fail-open-masked → verify by positive confirmation, not
  absence-of-error):** (a) the plugin-root command-path *spelling* (plugin-relative
  hypothesis) is unverified live — carried to 113-06 install verification; (b) the
  skill-body rewrite targets `.github/scripts/` which is **not shipped until 113-06**
  (homed slice-06 AC5).
- **Craft/test fixes:** test hermeticity — E2E tests now set `CLAUDE_PROJECT_DIR`
  (closed a genuine local-red/CI-green fragility where entry-gate would evaluate the
  real repo under Claude Code); git-freshness E2E strengthened; adapter `main()`
  derivation unit-tested; exit-0 comment narrowed to "advisory"; `{script_path}`
  quoted. Also found+fixed a test-isolation bug: entry-gate's fire-once-per-session
  cadence (keyed on `TMPDIR`+`session_id`) needed per-test `TMPDIR` isolation.

### Reconciliation sweep

- **docs/architecture.md** — `updated`: the host-adapter section notes the Copilot
  hook translation (build-time config/event/matcher + the runtime `copilot_hook_adapter.py`
  input shim; advisory `.github/hooks/*.json`).
- **docs/specs/113-05 (slice-05) DoR** — `updated`: homes the enforcing-hook adapter
  requirement (runtime output/exit post-processing, advisory/enforcing mode,
  verify-by-positive-confirmation).
- **docs/specs/113-06 (slice-06) AC5** — `updated`: homes the unshipped-`scripts/`
  package-completeness residual.
- **docs/refinement-todo.md** — `updated`: the `${CLAUDE_PLUGIN_ROOT}` path-rewrite
  entry now notes the rewrite *mechanism* landed in 113-04, with the plugin-root
  *spelling* live-verification + `scripts/` shipping carried to 113-06.
- **Architecture impact / ADR** — `no-op` (no new ADR): implements ADR-0061; the
  response-wiring deferral is within its "gates keep their teeth / degrade **visibly**"
  invariant (honestly deferred + homed, not silently dropped).
- **docs/conventions.md** / **Lightweight decisions** / **Inbox** — `no-op`.
- **Primer hygiene (CLAUDE.md)** — `no-op`: spec 113 not closed (113-05/06 remain).
- **hosts/ regeneration** — `updated`: `build_host_packages.py` re-emitted
  `hosts/copilot/.github/hooks/**` + `copilot_hook_adapter.py` + the shared
  `scaffold.py` mirrors under `hosts/{claude,codex}` (drift-guard regen, inert
  outside Copilot); `--check` clean.
- **slice-03-agents.md** — `no-op`: shows modified in the tree only from its own
  earlier RECONCILED→DONE frontmatter flip (committed here); no 113-04 content.
- **Status board** — `updated (regenerated)` after the IN_PROGRESS transition.
- **Memory-sync** — light; per-slice progress on the board; copilot-migration project
  memory updated at spec close.
