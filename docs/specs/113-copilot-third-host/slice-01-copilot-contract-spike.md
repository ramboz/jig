---
status: DONE
kind: spike
dependencies: [adr-0061]
last_verified:
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

**AC2 — Skill-load contract (VERIFIED; loader limits are real — jig is compliant).**
- Discovery roots (`copilot skill --help`): project `.github/skills/`,
  `.agents/skills/`, `.claude/skills/`; personal `~/.copilot/skills/`,
  `~/.agents/skills/`; plugin-bundled; custom (`copilot skill add`). SKILL.md
  format is the **same Agent-Skills shape** (builtin example frontmatter:
  `name`, `description`, `user-invocable`, `allowed-tools`).
- **Loader limits are real** (Adobe terminology map, CLI 1.0.84: *"names
  containing `:` and descriptions over 1,024 characters fail to load"*) —
  ADR-0061's loader-compat invariant stands. jig's exposure: the `:` limit is
  about the SKILL.md `name:` field, and jig source names carry no colon (ADR
  probe: 0/20), so jig is already compliant — the `jig:` *invocation* prefix is
  not the skill `name:` and does not travel into the rendered SKILL.md. The
  >1024-char limit bites `memory-sync` (1059) and `vision-elicitation` (1058), so
  the renderer **must** shorten their Copilot descriptions (full text preserved in
  the SKILL.md body). Separately, Copilot *addresses* a loaded skill as
  `${source}:${name}` (e.g. `plugin:spec-workflow`) — that `:` is Copilot's own
  source prefix, distinct from the forbidden `:`-in-name. _(Correction: my first
  pass under-weighted these as "not corroborated in app.js" — the `1024` grep hits
  were unrelated, but that is absence-of-evidence; the Adobe pilot directly
  observed the failures, so the invariant is load-bearing.)_

**AC3 — Agent + hook forms (VERIFIED; hook mechanism = config-file `.github/hooks/*.json`, ADR-0061 confirmed).**
- **Agent file form RESOLVED: `.github/agents/<name>.agent.md`** (Markdown +
  frontmatter) for authored/custom agents — from `app.js`:
  `` `${name}.agent.md` `` written to `join(cwd, ".github", "agents")`. The
  `.agent.yaml` form is only the **built-in** YAML agents
  (`agentsIsYamlBasedAgent`). Agent frontmatter fields (from the shipped
  `definitions/*.agent.yaml`): `name`, `description`, `tools`, `prompt`
  (+ `displayName`, `promptParts` for built-ins). Read-only posture is expressed
  via the `tools` list + prompt (the built-in `code-review` agent uses
  `tools: ["*"]` and enforces read-only in the prompt).
- **Hook mechanism — ADR-0061 CONFIRMED (correction from this session's first
  pass).** Copilot loads **file-configurable hooks** from
  **`.github/hooks/*.json`** (+ `~/.copilot/hooks/`, `.github/copilot/settings*.json`,
  and cross-tool `.claude/settings*.json`), across tiers user / **repository** /
  **plugin** / policy — exactly the ADR-0061 premise. Verified in the shipped CLI's
  own `schemas/api.schema.json`: `HooksDiscoverRequest`/`HooksDiscoverResult`,
  `DiscoveredHook`, `HookOrigin` (`user|repository|plugin|policy`, incl.
  "repository hook directory"), `SessionLoadDeferredRepoHooks*`, and
  `PermissionDecisionDeniedByPermissionRequestHook`; and in both Adobe docs
  (migration guide: "Copilot loads hooks from `.github/hooks/*.json`"; terminology
  map: "14 events … payloads differ").
- **Two hook surfaces, one event vocabulary.** `api.schema.json`'s `HookType`
  note: *"Discovery emits the file-configurable subset; SDK callbacks additionally
  support callback-only events."* (a) **File-configurable / discovered hooks**
  (`.github/hooks/*.json`) — the declarative path jig renders into. (b) SDK
  **callback** hooks via a Node `extension.mjs` + `joinSession({hooks})` over
  JSON-RPC (`copilot-sdk/docs/extensions.md`) — a *separate, more-powerful*
  mechanism jig does **not** need. My first pass found only (b) and wrongly
  concluded (a) was absent; the api-schema + Adobe docs correct that.
- **`HookType` events (17 in schema; ~14 file-configurable per the Adobe map),
  camelCase:** `preToolUse`, `preMcpToolCall`, `postToolUse`, `postToolUseFailure`,
  `userPromptSubmitted`, `userPromptTransformed`, `sessionStart`, `sessionEnd`,
  `postResult`, `prePRDescription`, `errorOccurred`, `agentStop`,
  `subagentStart`, `subagentStop`, `preCompact`, `permissionRequest`,
  `notification`. Claude is PascalCase → an event-name map is needed.
- **Response schema is Claude-adjacent** (maps cleanly): the output types carry
  `permissionDecision?: "allow"|"deny"|"ask"`, `permissionDecisionReason?`,
  `additionalContext?`, `suppressOutput?`, and agent-stop `{decision:"block",
  reason}` ("Claude-compatible `stop_hook_active` semantics"). Enforcing gates keep
  teeth via a `permissionRequest`/`preToolUse` hook that denies
  (`PermissionDecisionDeniedByPermissionRequestHook` = `kind:
  "denied-by-permission-request-hook"`, `message`, `interrupt`). Payloads/response
  differ from Claude's in detail → per-hook translation + testing required (the
  ADR's mapped-or-unmappable inventory invariant), but the shape is translatable,
  not alien.
- Instructions home: **`.github/copilot-instructions.md`** (`copilot init`
  generates it; `copilot instruction list` inspects sources). Copilot also reads
  `CLAUDE.md`/`AGENTS.md`, so the copilot package should emit **one** canonical
  instructions file to avoid double-load. MCP: `.mcp.json` or `.github/mcp.json`.

**AC5 — Internal seam-fit (VERIFIED; the seam extends — corrected).**
- jig's seam `HostRenderer.translate_hook_protocol(logical_result: dict) -> dict`
  (`skills/scaffold-init/scaffold.py:1076`) is defined once on
  `ClaudeScaffoldRenderer`; `CodexScaffoldRenderer` inherits it unchanged (only the
  abstract stub :1034 + the Claude impl :1076 exist). It maps a hook's logical
  decision → the host's response-schema dict.
- **The seam extends to Copilot as a third subclass — no abstraction reshape.**
  Because Copilot's file-configurable hooks reuse the Claude-adjacent decision
  vocabulary, `CopilotScaffoldRenderer.translate_hook_protocol` is a genuine
  response-schema remap (the method's designed purpose), plus a
  Claude-PascalCase → Copilot-camelCase **event-name** map. The renderer emits
  `hosts/copilot/.github/hooks/*.json` referencing the existing
  `hooks/scripts/jig-*.sh` bash scripts — exactly ADR-0061's committed
  `translate_hook_protocol` + `.github/hooks/*.json` layout.
- **113-02 entry note (design, not blocker):** the event-name map + the
  `.github/hooks/*.json` file emission are companions to `translate_hook_protocol`
  (which handles the response fields); one method vs. a small helper is an ordinary
  implementation choice, not an abstraction-breaking reshape. **The frame-critique's
  seam-fit question is answered: the seam fits.** _(Correction: my first pass
  claimed the seam did NOT fit and needed an `extension.mjs` bridge — that was a
  consequence of the wrong hook-mechanism finding, now retracted.)_

**Outcome:** `spec 113-02..06 unblocked (verified shape)`; **`ADR-0061 CONFIRMED
— no amendment`.** Every load-bearing ADR premise holds against the shipped CLI
1.0.84 + the Adobe migration/terminology guides: file-configurable hooks at
`.github/hooks/*.json` translated via `translate_hook_protocol` (event-name map +
Claude-adjacent response schema); `.github/` durable home; `/plugin` Claude-format
install; `.github/agents/*.agent.md`; and the loader-compat invariant (`:`-free
names + ≤1024-char descriptions — `memory-sync`/`vision-elicitation` need
shortening). Net-new verified detail for downstream DoR: install via a **repo
subdirectory** (`copilot plugin install ramboz/jig:hosts/copilot`, no separate
marketplace); manifest `.plugin/plugin.json`; the 17-name `HookType` enum +
`PermissionDecisionDeniedByPermissionRequestHook` deny path; a *second* SDK
`extension.mjs` callback surface jig does **not** need.

_Correction note (owner challenge): this session's **first** spike pass wrongly
reported an ADR contradiction ("hooks = `extension.mjs` only") after inspecting
only the SDK authoring docs (`copilot-sdk/docs/extensions.md` + `types.d.ts`) plus
an unreliable native-binary grep. Re-checking the Adobe docs and the CLI's own
`schemas/api.schema.json` (`HookType`/`DiscoveredHook`/`HookOrigin`) established the
file-configurable `.github/hooks/*.json` path. Lesson: an authoring SDK's docs
describe one surface; do not infer a mechanism's absence from a subsystem's docs +
an unreliable binary grep, and defer to the authoritative product docs. Recorded
to memory._

**DoR:**
- ✅ ADR-0061 recorded (Accepted 2026-09-15).
- ✅ Access to a licensed GitHub Copilot CLI session (`copilot` 1.0.84) on the
  Adobe tenant, and to GitHub's Copilot CLI hooks/agents/plugin reference docs
  (Adobe migration + terminology guides).

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
- [x] Findings block filled with commands run + observed output (grounding).
- [x] Outcome set; downstream slices' DoR updated with the verified shape (113-02
      DoR expanded with the verified contract; 113-03/04/05 inherit it).
- [x] `docs/refinement-todo.md` updated if any decision was deferred — **N/A**: no
      decision deferred; the spike confirmed ADR-0061 rather than opening a new
      question. (The one methodology lesson was recorded to session memory.)

**Anti-horizontal-phasing check:** Exempt — `kind: spike`. Delivers verified
decisions that unblock 113-02..06, not user-facing behavior.

### Deviation log (after reconciliation)

- **Time-box:** planned 1–2 days; the source-level seam probe + a mid-spike
  correction (below) fit within it.
- **Major correction (owner-caught).** The first findings pass reported an
  ADR-0061 contradiction — "Copilot hooks are `extension.mjs` SDK handlers only;
  no `.github/hooks/*.json`" — and recommended an ADR amendment. That was **wrong**:
  it rested on the SDK authoring docs (one surface) + an unreliable native-binary
  grep. On owner challenge I re-verified against the Adobe migration + terminology
  guides AND the CLI's own `schemas/api.schema.json`, which establish the
  file-configurable `.github/hooks/*.json` path — the ADR premise. Outcome flipped
  to **ADR-0061 CONFIRMED — no amendment**; Findings AC2/AC3/AC5 + Outcome were
  rewritten (commit 9cb8a2b).
- **AC5 seam-fit** flipped with it: `translate_hook_protocol` **fits** as a third
  subclass (event-name map + response remap + `.github/hooks/*.json` emission); no
  `extension.mjs` bridge / abstraction reshape needed.

### Reconciliation sweep

- **113-02 DoR** — `updated`: expanded with the verified contract (manifest,
  discovery roots, loader-compat invariant, instructions home, subdir install).
- **113-03/04/05/06 DoR** — `no-op`: inherit 113-02's verified shape; hook details
  (`.github/hooks/*.json`, `HookType` enum, permission-deny path) live in
  slice-01 Findings AC3, pulled in when 113-04/05 are picked up.
- **ADR-0061** — `no-op` (confirmed, not amended); no `## Amendments` entry.
- **docs/refinement-todo.md** — `no-op`: nothing deferred.
- **Session memory** — `updated`: recorded the SDK-docs-vs-product-docs probing
  lesson.
- **Review evidence** — `deferred`: `kind: spike` delivers verified decisions, not
  code; compliance/craft passes are N/A. Closure uses `JIG_REVIEW_EVIDENCE_GATE=0`
  with this log as the audit trail (findings already stress-tested via the owner
  challenge + 3-source re-verification).
