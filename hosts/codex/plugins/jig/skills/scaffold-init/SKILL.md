---
name: scaffold-init
description: >
  Initialize an AI-native development workspace with spec-driven workflow infrastructure.
  Use when starting a new project, setting up Codex on a codebase for the first
  time, or when the user says scaffold, initialize, set up AI workflow, onboard this
  repo, or similar. Do not use for adding an individual skill or config to an already-
  scaffolded project — that is handled by the relevant tier skill directly.
user-invocable: true
---

> Spec 001 is fully implemented: greenfield-scaffold, doc-content, signal-detection,
> deferred-decisions, and Q&A wizard.
> See [docs/specs/001-scaffold-init/spec.md](../../docs/specs/001-scaffold-init/spec.md).

## What this skill does

Generates an AI-native development workspace by copying templates from
`${PLUGIN_ROOT}/templates/` into a target directory. Detects project
signals from the filesystem (LLM/agent files, CI, tests, team), runs an optional
Q&A flow to let the user override those signals, and selects tiers accordingly.
Tier 0 always installs; Tier 1 installs when test signals are present; Tier 2
is offered (not auto-installed) when LLM/agent signals are present.

## How to use

1. Determine the target directory. Default: the current working directory.
   If you're unsure, **ask the user once** before scaffolding.
2. Check if the target already has a `scaffold.json` or `docs/specs/` — if so,
   the project is already scaffolded. **Stop and tell the user** rather than
   overwriting.
3. **Run the Q&A flow** (see next section). Collect answers as flag values.
4. Invoke the wizard with the collected flags:
   ```bash
   python3 "${PLUGIN_ROOT}/skills/scaffold-init/scaffold.py" \
     [--runtime <name>] [--team|--solo] [--has-ci|--no-ci] \
     [--has-tests|--no-tests] [--plans-ai|--no-ai] \
     <target-dir>
   ```
5. Read the wizard's stdout summary and report back to the user. List the files
   that were created and the immediate next steps.

## Codex custom-agent install

Codex scaffold mode (`--host codex`) writes project-local custom agents as
TOML under `.codex/agents/`. For Codex plugin users who want jig's role agents
globally available, run the explicit post-install helper:

```bash
python3 "${PLUGIN_ROOT}/skills/scaffold-init/scaffold.py" --install-codex-agents
```

The default destination is `~/.codex/agents`. Use
`--codex-agents-dir <dir>` to target a different Codex agents directory.
The helper refuses to overwrite user-owned `jig-*.toml` files unless
`--force` is passed.

## Q&A flow (slice 001-05)

Ask each question in order. **Each question is independently skippable** — if the
user says "skip", "I don't know", "unsure", or similar, do not pass the flag
(the wizard's filesystem inference handles it).

1. **Runtime/language** — "What runtime or language is this project?
   (e.g. Python, TypeScript, Go, Rust, mixed, unsure)"
   → `--runtime <name>` if answered; omit if skipped or unsure.
2. **Team context** — "Solo project or team setting?"
   → `--team` for team, `--solo` for solo; omit if skipped (uses git-author detection).
3. **Existing CI** — "Does the project already have CI configured?"
   → `--has-ci` for yes, `--no-ci` for no; omit if skipped.
4. **Existing tests** — "Does the project already have a test suite?"
   → `--has-tests` for yes, `--no-tests` for no; omit if skipped.
   This affects whether tier-1 (`tdd-loop` and friends) is auto-installed.
5. **LLM/agent work planned** — "Will this project involve LLM or agent development?"
   → `--plans-ai` for yes, `--no-ai` for no; omit if skipped.
   This affects whether tier-2 is offered.

Skipping every question is the legitimate "pure inference" mode (slice 001-03
behavior) — the wizard infers from filesystem signals alone. Do not invent
answers when the user is unsure.

## Output

After running, the target directory contains:
- `AGENTS.md` (with Hot Cache section, project name substituted)
- `docs/` (architecture, workflow, conventions, refinement-todo, inbox, memory/, specs/, decisions/)
- `.codex/hooks/` (empty — project-specific gates can go here)
- `scaffold.json` (install-state manifest)

Every scaffolded doc carries `Status: Draft (wizard-generated)`.
`docs/memory/people.md` is NOT created (solo-project default — team detection is slice 001-03).

## Immediate next steps to surface to the user

After scaffolding succeeds, tell the user:
1. Open `AGENTS.md` and fill in the Hot Cache section with project-specific terms.
2. Open `docs/refinement-todo.md` to see what was deferred.
3. The first spec to write is in `docs/specs/` — use `/jig:spec-workflow` (when implemented)
   or write `docs/specs/001-<feature>/spec.md` by hand.
4. **Note:** `docs/conventions.md` is now gated. Edits require
   `JIG_CONVENTIONS_APPROVED=1` in the shell session.

## Constraints

- Do not invoke this skill in a directory that is already scaffolded (has `scaffold.json`).
- Do not overwrite an existing `AGENTS.md` without explicit user confirmation.
- The wizard is deterministic — do not edit the generated files yourself before
  reporting back. The user should see exactly what `scaffold.py` produced.

## Gotchas

- The spec-gate hook for `docs/conventions.md` activates AFTER scaffold-init completes.
  It cannot gate its own creation (bootstrap paradox — documented and intentional).
- `templates/AGENTS.md.template` is the source template; do NOT use the jig repo's own
  `AGENTS.md` as a template — the two diverge over time.
- `${PLUGIN_ROOT}` is the right env var inside the plugin. Don't confuse it with
  `$CODEX_PROJECT_DIR` (which is the target project's root after install).
- Signal detection (existing CI, LLM/agent files, team size) is deferred to slice 001-03.
  Until then, the wizard installs default tiers regardless of project context.
- **scaffold-init refuses if the target looks spec-driven but lacks `scaffold.json`.**
  Slice 008-05 introduced a second pre-flight check: if ≥3 of the four migrate
  triggers (`docs/specs/`/`docs/slices/`, `docs/decisions/`/`docs/adrs/`,
  `docs/workflow.md`, `docs/architecture.md`) are present without a
  `scaffold.json`, the helper raises `LooksAlreadySpecDrivenError` (exit 2)
  and points at `/jig:migrate`. Pass `--force` to scaffold over the existing
  tree anyway (NOT recommended — overwrites docs).
