---
status: IN_PROGRESS
kind: spike
dependencies: [adr-0061]
last_verified:
claimed_by: claude/adr-0061-spec-113-jig-874db3
---

## Slice 113-01 — copilot-contract-spike

**Goal:** Resolve the external, Copilot-owned unknowns ADR-0061 flagged so the
rendering slices commit to a verified shape rather than a guessed one.

**Question:** (1) What exact contract must jig's committed `hosts/copilot/`
package present to (a) install via `/plugin`, (b) have its skills load
(name/namespace + description limits), (c) load custom agents (file
form/frontmatter), and (d) register hooks — under a live GitHub Copilot CLI at
Adobe? (2) **Internal:** can jig's existing `HostRenderer` /
`translate_hook_protocol` seam express Copilot's 14-event/per-event-schema hook
model as a third subclass, or must the abstraction be reshaped before 113-02?

**Time-box:** 1–2 days (adds a source-level probe of the render seam to the
live-session contract checks).

**Findings:**

_Grounded against the **shipped** Copilot CLI, not the Adobe guide: npm pkg
`@github/copilot` 1.0.83 (runtime binary reports `1.0.84-8`), inspected at
`~/.nvm/.../@github/copilot/node_modules/@github/copilot-darwin-arm64/` — the
`app.js` bundle, the native `copilot` binary, the shipped `copilot-sdk/*.d.ts`
type definitions + `copilot-sdk/docs/*.md`, and `copilot <sub> --help`._

**AC1 — Plugin install + manifest (VERIFIED).**
- `copilot plugin install <source>` parses (from `--help`): `plugin@marketplace`,
  `owner/repo`, **`owner/repo:path` (a repo subdirectory)**, `https://…git`.
  → jig's committed `hosts/copilot/` installs directly with **no build step and no
  separate marketplace**: `copilot plugin install ramboz/jig:hosts/copilot`. A
  marketplace entry is optional/additive, not required.
- Plugin manifest = **`.plugin/plugin.json`** (observed in the bundled
  `plugins/computer-use/.plugin/plugin.json`): `{ "name", "version",
  "description", "mcpServers"?: "./.mcp.json" }`. Bundled `skills/`, `agents/`,
  and `.github/extensions/` are directory-discovered within the plugin root; only
  MCP needs an explicit pointer.

**AC2 — Skill-load contract (VERIFIED; two ADR premises corrected).**
- Discovery roots (`copilot skill --help`): project `.github/skills/`,
  `.agents/skills/`, `.claude/skills/`; personal `~/.copilot/skills/`,
  `~/.agents/skills/`; plugin-bundled; custom (`copilot skill add`). SKILL.md
  format is the **same Agent-Skills shape** (builtin example frontmatter:
  `name`, `description`, `user-invocable`, `allowed-tools`).
- **`:` namespace is a non-issue.** Copilot addresses a skill as
  `${source}:${name}` (e.g. `plugin:spec-workflow`) — the `:` is Copilot's own
  *source prefix*, applied to the bare `name:` field. jig source skill `name:`
  fields carry no colon (ADR probe: 0/20), so nothing surfaces a `:`-bearing
  loaded name. The `jig:` Claude *invocation* prefix is not a skill name and does
  not travel into the SKILL.md. → **ADR "hard failure #1a" (`:` names) does not
  reproduce.**
- **1024-char description limit NOT corroborated** in the shipped loader: every
  `1024` occurrence in `app.js` is unrelated (YAML `:`-indicator limit
  `KEY_OVER_1024_CHARS`, LRU cache sizes, diff-size caps). No skill-description
  length gate was found in the code inspected. → Treat the Adobe-guide ">1024
  fails to load" claim as **unverified / likely relaxed in 1.0.84**. The renderer
  should still keep descriptions lean defensively (cheap insurance), but this is
  not a load-bearing breaker. _(Absence-of-evidence, not proven absence — the
  loader path in the native binary was not exhaustively decompiled.)_

**AC3 — Agent + hook forms (VERIFIED; hook mechanism is the big finding).**
- **Agent file form RESOLVED: `.github/agents/<name>.agent.md`** (Markdown +
  frontmatter) for authored/custom agents — from `app.js`:
  `` `${name}.agent.md` `` written to `join(cwd, ".github", "agents")`. The
  `.agent.yaml` form is only the **built-in** YAML agents
  (`agentsIsYamlBasedAgent`). Agent frontmatter fields (from the shipped
  `definitions/*.agent.yaml`): `name`, `description`, `tools`, `prompt`
  (+ `displayName`, `promptParts` for built-ins). Read-only posture is expressed
  via the `tools` list + prompt (the built-in `code-review` agent uses
  `tools: ["*"]` and enforces read-only in the prompt).
- **Hook mechanism — CONTRADICTS ADR-0061.** Copilot has **no shell-command
  hooks via a JSON settings file** (Claude's model). Per the shipped
  `copilot-sdk/docs/extensions.md` + `copilot-sdk/types.d.ts`: hooks are **typed
  JS handler functions** registered by a forked **Node `extension.mjs`**
  (`.github/extensions/<name>/extension.mjs`, ES module) that calls
  `joinSession({ hooks: {…} })` from `@github/copilot-sdk/extension` over
  **JSON-RPC/stdio**. No `hooks.json` / `settings.json` hook-config path exists in
  the shipped CLI. There is **no `.github/hooks/*.json`** as the ADR-0061 layout
  diagram assumed.
- **`SessionHooks` surface (10 handlers, `types.d.ts`):** `onPreToolUse`,
  `onPreMcpToolCall`, `onPostToolUse`, `onPostToolUseFailure`,
  `onUserPromptSubmitted`, `onUserPromptTransformed`, `onSessionStart`,
  `onSessionEnd`, `onErrorOccurred`, `onAgentStop`.
- **Output field vocabulary is Claude-compatible** (the good news — the *logical*
  decision maps 1:1): `PreToolUseHookOutput { permissionDecision?:
  "allow"|"deny"|"ask"; permissionDecisionReason?; modifiedArgs?;
  additionalContext?; suppressOutput? }`; `SessionStartHookOutput {
  additionalContext?; modifiedConfig? }`; `PostToolUseHookOutput {
  modifiedResult?; additionalContext?; suppressOutput? }`; `AgentStopHookOutput {
  decision?: "block"; reason? }` (docs cite "Claude-compatible `stop_hook_active`
  semantics"). It is the **delivery mechanism** (shell + `settings.json` +
  exit-code-2/stdout → JS handler + typed return over JSON-RPC) that differs, not
  the decision vocabulary.
- Instructions home: **`.github/copilot-instructions.md`** (`copilot init`
  generates it; `copilot instruction list` inspects sources). Copilot also reads
  `CLAUDE.md`/`AGENTS.md`, so the copilot package should emit **one** canonical
  instructions file to avoid double-load. MCP: `.mcp.json` or `.github/mcp.json`.

**AC5 — Internal seam-fit (VERIFIED; the decisive architectural result).**
- jig's current seam `HostRenderer.translate_hook_protocol(logical_result: dict)
  -> dict` (`skills/scaffold-init/scaffold.py:1076`) is defined once, concretely,
  on `ClaudeScaffoldRenderer`; `CodexScaffoldRenderer(ClaudeScaffoldRenderer)`
  **inherits it unchanged** (confirmed: only the abstract stub at :1034 and the
  Claude impl at :1076 exist). It assumes the Claude/Codex model: hooks are shell
  scripts wired in `settings.json`, and "protocol translation" is a
  response-schema **dict remap**.
- **Copilot does not fit that seam as "just a third subclass."** (Frame-critique
  secondary finding CONFIRMED.) Copilot needs a **new renderer responsibility**:
  emit `.github/extensions/jig/extension.mjs` that registers `SessionHooks`
  handlers, each shelling out to the existing `hooks/scripts/jig-*.sh` bash
  scripts, capturing exit-code + stdout, and mapping to the Copilot `HookOutput`
  object (exit 2 → `permissionDecision:"deny"` + `permissionDecisionReason`;
  stdout `additionalContext` → `additionalContext`; agent-stop block →
  `{decision:"block", reason}`). This is a **bridge/adapter generator**, not a
  dict remap and not `.github/hooks/*.json`.
- **Minimal seam change (113-02 entry condition):** add a hook-**emission** seam
  to `HostRenderer` (e.g. `emit_hooks(pkg_dir)` / `render_hook_delivery`) — Claude
  & Codex implement it as their existing `settings.json` hooks block (refactor
  current behavior behind the method); Copilot implements it as
  `extension.mjs` + the bash-bridge. Keep `translate_hook_protocol` for the
  reusable logical-decision → host-output field mapping. This is a genuine
  reshape of the abstraction, not a subclass drop-in.

**Outcome:** `spec 113-02..06 unblocked (verified shape)`;
**`ADR-0061 amendment REQUIRED`** — the hook-delivery mechanism in the Recommended
Decision (layout `hooks/*.json`; `translate_hook_protocol` as the sole hook seam)
is contradicted by the shipped CLI (hooks = `extension.mjs` SDK handlers). Per
spike AC4 + ADR-0010 (records need an owner-approved `## Amendments` entry) the
contradiction is **surfaced for owner approval, not silently absorbed** — see the
session hand-off. Two Adobe-guide "hard failures" (`:` names, >1024 desc) did
**not** reproduce and are downgraded.

**DoR:**
- ✅ ADR-0061 recorded (Proposed).
- ✅ Access to a licensed GitHub Copilot CLI session (`copilot`) on the Adobe
  tenant, and to GitHub's Copilot CLI hooks/agents/plugin reference docs.

**Acceptance Criteria:**

1. **Plugin install verified.** Record whether `/plugin` installs jig's existing
   Claude-format marketplace package as-is, and the exact manifest/marketplace
   shape a committed `hosts/copilot/` must present (with the commands run and
   their output).
2. **Skill-load contract verified.** Confirm whether the `jig:` namespace
   surfaces as a `:`-bearing loaded skill name (a loader breaker) and confirm the
   >1024-char description failure on `memory-sync`/`vision-elicitation` in a live
   session; record the discovery roots Copilot actually reads
   (`.github/skills` vs `.claude/skills` vs `.agents/skills`).
3. **Agent + hook forms verified.** Resolve the `.github/agents/*.md` vs
   `*.agent.md` extension, the agent frontmatter fields Copilot honors, and the
   concrete Copilot hook JSON schema (event names, payload, and allow/deny
   response shape) for at least one advisory and one permission-decision hook.
4. **Open questions dispositioned.** Each ADR-0061 `## Open questions` item is
   answered or explicitly carried forward; if a finding contradicts an ADR-0061
   premise, an amendment/superseding note is raised (not silently absorbed).
5. **Internal seam-fit verified.** Inspect the `HostRenderer` seam in
   `scaffold.py` (`translate_hook_protocol`, `bind_paths`, `renderer_for_host`,
   `_HOST_RENDERERS`) and map Copilot's verified hook schema onto it. Record
   whether a `CopilotScaffoldRenderer(HostRenderer)` subclass can express the
   Claude-PascalCase→Copilot-camelCase event mapping **and** the per-event
   payload/response-schema differences without reshaping the seam. If reshaping is
   needed, name the minimal seam change and record it as the 113-02 entry
   condition — so the renderer slice doesn't discover it mid-implementation.

**DoD:**
- [ ] Findings block filled with commands run + observed output (grounding).
- [ ] Outcome set; downstream slices' DoR updated with the verified shape.
- [ ] `docs/refinement-todo.md` updated if any decision was deferred.

**Anti-horizontal-phasing check:** Exempt — `kind: spike`. Delivers verified
decisions that unblock 113-02..06, not user-facing behavior.
