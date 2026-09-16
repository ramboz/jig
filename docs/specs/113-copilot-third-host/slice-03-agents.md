---
status: RECONCILED
dependencies: [113-02]
last_verified: 2026-09-15
claimed_by: claude/adr-0061-spec-113-jig-874db3
---

## Slice 113-03 — agents

**Goal:** A Copilot user gets jig's custom-agent roster — implementer, reviewer,
architect — rendered as Copilot custom agents under `.github/agents/`.

**DoR:**
- ✅ 113-02 done (renderer + skeleton).
- ✅ 113-01 finding fixed the agent file form (`.md` vs `.agent.md`) and honored
  frontmatter fields.

**Acceptance Criteria:**

1. **Agents rendered.** Each jig source agent renders to the verified Copilot
   agent form under `hosts/copilot/.github/agents/`, with frontmatter mapped to
   the fields Copilot honors (tools, description, read-only/edit posture).
2. **Model-id neutrality.** No rendered agent hard-codes `opus`/`sonnet`; model
   selection defers to Copilot's `/model` (Adobe default GPT-5.6 Terra). A test
   asserts no Claude-specific model id leaks into the Copilot agent output.
3. **Reviewer read-only posture preserved.** The rendered reviewer agent retains
   its read-only tool restriction (Read/Glob/Grep), matching the Claude/Codex
   renderings.

**DoD:**
- [x] All ACs pass; full suite green (4608 tests, pyright clean); new tests fail
      when the feature is removed (red-before/green-after verified); Claude/Codex
      output unchanged.
- [x] Reviewed by `reviewer` subagent — compliance (pass) + craft (pass); verdicts
      recorded under `reviews/`.
- [x] Deviation log + reconciliation sweep produced; reconciliation review pass (R2).

**Anti-horizontal-phasing check:** After this slice a Copilot user can invoke
jig's subagents — new end-to-end capability.

### Deviation log (after reconciliation)

- **Claude→Copilot tool mapping (verified against shipped CLI 1.0.84):** Read→view,
  Glob→glob, Grep→grep, Write→create, Edit→edit, **Bash→bash** (NOT `shell` — the
  brief's initial hypothesis; `shell` is the CLI's *session-permission-flag*
  vocabulary + a permission-request "kind", not the agent `tools:` allowlist —
  evidenced by `explore.agent.yaml`'s restrictive list), WebSearch→fetch. Encoded
  as `CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS` with the evidence chain
  inline. Unmapped source tools fail loud (`CopilotAgentToolError`), never silently
  dropped.
- **WebSearch→fetch is a capability approximation, not a 1:1 equivalence** (Claude
  WebSearch = web search; Copilot `fetch`/`web_fetch` = fetch a known URL). Closest
  verified Copilot analog; preserves the architect's web-access posture. Logged so a
  later reader doesn't treat it as a verified equivalence; revisit if Copilot ships a
  distinct search tool.
- **Agent bodies ship verbatim,** so the rendered prompts still carry Claude
  tool-name prose (e.g. the reviewer body's "read-only (Read/Glob/Grep)"). Cosmetic
  only — Copilot enforces the reviewer's read-only restriction via the frontmatter
  `tools:` allowlist (`view/glob/grep`), not body prose. This is a **distinct** gap
  from the `${CLAUDE_PLUGIN_ROOT}` path-variable rewrite (agent bodies contain no
  `${CLAUDE_PLUGIN_ROOT}` — only Claude tool-name/vocab prose), so it is homed as its
  **own** `docs/refinement-todo.md` entry ("Copilot rendered-body Claude tool-name /
  vocab prose normalization"): a **cosmetic** residual, considered in 113-04 or left
  as a documented residual. It stays deferred, not silently in-scope.
- **Read-only mechanism (AC3):** restrictive `tools:` allowlist **and** kept prompt
  language (belt-and-suspenders, as spike 113-01 AC3 recommended). Empirical
  tool-call *denial* under a restrictive `.agent.md` allowlist could not be proven
  non-interactively (no `copilot agent list/inspect`; provoking a denial needs a
  live credit-consuming session — deliberately not run). The rendered
  `reviewer.agent.md` carries exactly `[view, glob, grep]` (no mutating tool),
  verified firsthand by the orchestrator + pinned by tests.
- **Model-neutrality (AC2):** no `model:` field emitted (Copilot picks via `/model`
  or auto); source agents carry no model field, so nothing to strip; a test asserts
  no `opus`/`sonnet`/`claude-…` token leaks into any rendered agent.
- **Craft nits (logged, not fixed — cosmetic on the controlled 3-agent roster):**
  `name` emitted unquoted while `description` is `json.dumps`-quoted (YAML-safety
  asymmetry, harmless for the current names); a source agent with no `tools:` would
  render an empty `tools:` block (degenerate, unexercised); the agent render path
  does not `assert_namespace_safe_name` the agent name (the agent-name constraint
  differs from skills' — Copilot requires ≥1 ASCII letter/digit, not `:`-free — a
  small follow-up if agent names ever get non-trivial); the reviewer read-only test
  also asserts absence of `shell`/`write` (tokens the mapping can never emit —
  partly redundant).

### Reconciliation sweep

- **docs/architecture.md** — `updated`: the `hosts/copilot/` package description now
  lists `.github/agents/<name>.agent.md` as rendered (previously "agents … land
  across 113-03..06").
- **Architecture impact / ADR** — `no-op` (no new ADR): the agent-render additions
  live inside the `CopilotScaffoldRenderer` boundary already recorded by 113-02; no
  module boundary or public contract changed.
- **docs/refinement-todo.md** — `updated`: added a **distinct** entry, "Copilot
  rendered-body Claude tool-name / vocab prose normalization" (cosmetic; considered
  in 113-04 or a documented residual), separating it from the `${CLAUDE_PLUGIN_ROOT}`
  path-variable rewrite it was wrongly conflated with. (The agent-name
  namespace-guard nit is a sub-refinement-todo minor, noted above.)
- **hosts/ regeneration** — `updated`: `python3 scripts/build_host_packages.py`
  re-emitted `hosts/copilot/.github/agents/{architect,implementer,reviewer}.agent.md`
  + the shared `scaffold.py` mirrors under `hosts/{claude,codex,copilot}`; `--check`
  drift-clean.
- **docs/conventions.md** — `no-op`.
- **Lightweight decisions** — `no-op`: the tool mapping is a spec-implementation
  detail (deviation log + code comments), not a UI/copy lightweight decision.
- **Inbox** — `no-op`.
- **Primer hygiene (CLAUDE.md)** — `no-op`: spec 113 not closed (113-04..06 remain).
- **Status board** — `updated (regenerated)` after the IN_PROGRESS transition (the
  board check was stale until regen; now `check-board` clean).
- **Memory-sync** — light; per-slice progress is on the board; the
  copilot-migration project memory is updated at spec close.
