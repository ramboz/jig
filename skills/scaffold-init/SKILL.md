---
name: scaffold-init
description: >
  Initialize an AI-native development workspace with spec-driven workflow infrastructure.
  Use when starting a new project, setting up Claude Code on a codebase for the first
  time, or when the user says scaffold, initialize, set up AI workflow, onboard this
  repo, or similar. Do not use for adding an individual skill or config to an already-
  scaffolded project — that is handled by the relevant tier skill directly.
user-invocable: true
---

> Slice 001-01 (greenfield-scaffold) is implemented. Slices 001-02 (rich doc content),
> 001-03 (signal detection), 001-04 (deferred-decision structure), and 001-05 (Q&A
> wizard) are still pending — see [docs/specs/001-scaffold-init/spec.md](../../docs/specs/001-scaffold-init/spec.md).

## What this skill does

Generates an AI-native development workspace by copying templates from
`${CLAUDE_PLUGIN_ROOT}/templates/` into a target directory. Greenfield only in
this slice — no signal detection, no Q&A, default tier install (Tier 0 + Tier 1).

## How to use

1. Determine the target directory. Default: the current working directory.
   If you're unsure, **ask the user once** before scaffolding.
2. Check if the target already has a `scaffold.json` or `docs/specs/` — if so,
   the project is already scaffolded. **Stop and tell the user** rather than
   overwriting.
3. Run the wizard:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/scaffold-init/scaffold.py" <target-dir>
   ```
4. Read the wizard's stdout summary and report back to the user. List the files
   that were created and the immediate next steps.

## Output

After running, the target directory contains:
- `CLAUDE.md` (with Hot Cache section, project name substituted)
- `docs/` (architecture, workflow, conventions, refinement-todo, inbox, memory/, specs/, adrs/)
- `.claude/hooks/` (empty — project-specific gates can go here)
- `scaffold.json` (install-state manifest)

Every scaffolded doc carries `Status: Draft (wizard-generated)`.
`docs/memory/people.md` is NOT created (solo-project default — team detection is slice 001-03).

## Immediate next steps to surface to the user

After scaffolding succeeds, tell the user:
1. Open `CLAUDE.md` and fill in the Hot Cache section with project-specific terms.
2. Open `docs/refinement-todo.md` to see what was deferred.
3. The first spec to write is in `docs/specs/` — use `/jig:spec-workflow` (when implemented)
   or write `docs/specs/001-<feature>/spec.md` by hand.
4. **Note:** `docs/conventions.md` is now gated. Edits require
   `JIG_CONVENTIONS_APPROVED=1` in the shell session.

## Constraints

- Do not invoke this skill in a directory that is already scaffolded (has `scaffold.json`).
- Do not overwrite an existing `CLAUDE.md` without explicit user confirmation.
- The wizard is deterministic — do not edit the generated files yourself before
  reporting back. The user should see exactly what `scaffold.py` produced.

## Gotchas

- The spec-gate hook for `docs/conventions.md` activates AFTER scaffold-init completes.
  It cannot gate its own creation (bootstrap paradox — documented and intentional).
- `templates/CLAUDE.md.template` is the source template; do NOT use the jig repo's own
  `CLAUDE.md` as a template — the two diverge over time.
- `${CLAUDE_PLUGIN_ROOT}` is the right env var inside the plugin. Don't confuse it with
  `$CLAUDE_PROJECT_DIR` (which is the target project's root after install).
- Signal detection (existing CI, LLM/agent files, team size) is deferred to slice 001-03.
  Until then, the wizard installs default tiers regardless of project context.
