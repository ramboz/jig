# Codex Role Capability Dogfood

This note records the Codex role-agent semantics jig users can rely on after
the 059-05 dogfood pass.

## Repeatable Probe

Run:

```bash
python3 scripts/codex_role_capability_probe.py
```

The probe builds a scratch Codex project, installs jig's generated
`.codex/agents/jig-*.toml` role files, validates the role TOML, and probes the
local Codex CLI when `codex` is available. It uses an isolated `CODEX_HOME` by
default.

Expected stable rows:

| Role | Generated file | `sandbox_mode` | Write posture |
|---|---|---|---|
| `jig-implementer` | `.codex/agents/jig-implementer.toml` | `workspace-write` | Can write inside the active workspace boundary. |
| `jig-reviewer` | `.codex/agents/jig-reviewer.toml` | `read-only` | Cannot write without approval; read-only sandbox should block writes. |
| `jig-architect` | `.codex/agents/jig-architect.toml` | `read-only` | Cannot write without approval; read-only sandbox should block writes. |

Live Codex probes are allowed to report `UNAVAILABLE` instead of pretending a
surface passed. Use `--require-live-codex` when running on a Codex-capable
machine where live probe gaps should fail the command.

## Observed Locally

Observed on 2026-06-05 with `codex-cli 0.133.0`:

- Project-local custom agents are generated as standalone TOML files under
  `.codex/agents/`.
- The generated `jig-implementer` file requests `sandbox_mode =
  "workspace-write"`.
- The generated `jig-reviewer` and `jig-architect` files request
  `sandbox_mode = "read-only"`.
- `codex sandbox macos --permissions-profile :read-only ...` blocks a Python
  write with `PermissionError: [Errno 1] Operation not permitted`.
- `codex sandbox macos --permissions-profile :workspace ...` allows a Python
  write inside the scratch project.
- `codex debug prompt-input` exposes generated jig skills in the prompt input,
  but does not expose project custom-agent entries. That makes named custom
  agent invocation an interactive behavior rather than a stable
  noninteractive diagnostic surface today.

## Interactive Role Invocation

Current Codex docs say subagents are spawned only when explicitly requested,
custom agents live under `.codex/agents/` or `~/.codex/agents/`, and `/agent`
is the CLI inspection surface for spawned agent threads.

To dogfood the roles interactively in a scaffolded project:

```text
Spawn three subagents in parallel:
1. Use the jig-implementer custom agent to make a tiny harmless edit in the workspace.
2. Use the jig-reviewer custom agent to inspect the same workspace and attempt no writes.
3. Use the jig-architect custom agent to summarize an architecture concern and attempt no writes.

Wait for all three and summarize whether each agent wrote files or stayed read-only.
```

Use `/agent` in the Codex CLI to inspect the spawned threads. If a run cannot
surface approvals, actions that need new approval fail and Codex reports the
error back to the parent workflow.

## Post-Implementation Workflow Fallback

The deterministic jig review flow remains:

```bash
python3 skills/independent-review/review.py implementation <spec.md> <slice> <deliverables...>
python3 skills/independent-review/review.py pr-review <spec.md> <slice> <deliverables...>
python3 skills/independent-review/review.py reconciliation <spec.md> <slice>
```

In interactive Codex sessions, ask Codex to spawn a `jig-reviewer` custom
agent with the generated prompt when you want to dogfood the role agent. In
noninteractive automation, use the generated prompt text with `codex exec
--sandbox read-only` or another read-only reviewer runner and record the
verdict artifact with `review.py record-review`.
