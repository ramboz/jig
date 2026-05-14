# Plan: Slice 011-01 — local-plugin-install

> Plan landed alongside the implementation. The spec defers a few
> design points here (marketplace descriptor location, verify-script
> invocation shape, file layout). Each one is decided below.

## Approach

Three deliverables, one new top-level dir:

1. **`.claude-plugin/marketplace.json`** — the local dev marketplace
   descriptor. Lives alongside `plugin.json` so Claude Code's plugin
   tooling finds both in the conventional `.claude-plugin/` dir.
2. **`scripts/verify_install.py`** — the verify script, with two
   subcommands (`headless` default + `probe <agent>`).
3. **`CONTRIBUTING.md`** at repo root — the human-facing recipe
   (setup, rollback, live-verify runbook, test-suite invocation,
   short spec-workflow pointer).

## Design points decided

### Marketplace descriptor location

**Picked:** `.claude-plugin/marketplace.json` (alongside `plugin.json`).
**Rejected:** dedicated `dev-marketplace/` directory.

Rationale: keeping marketplace + plugin manifests in the same
conventional dir matches the public-marketplace shape (where a
marketplace repo also has `.claude-plugin/marketplace.json` at root)
and avoids inventing a separate "this is the dev marketplace" path.
The `source: ".."` field points at the repo root (one level up from
`.claude-plugin/`), which is also where `plugin.json` lives — so the
marketplace correctly registers this same checkout as the plugin's
source. No surface confusion at install time.

### Verify-script location and invocation

**Picked:** `scripts/verify_install.py` (top-level `scripts/` dir).
**Rejected:** `skills/_common/verify_install.py` or
`skills/plugin-install/verify_install.py`.

Rationale: `verify_install.py` is dev-infrastructure, not a user-
facing skill. Putting it under `skills/` would imply a SKILL.md or an
auto-trigger surface neither exists nor is wanted. `skills/_common/`
is for code that's shared *between skills*; verify_install isn't.
The cleanest framing is a peer of `skills/`, `hooks/`, `templates/`,
`agents/`, named `scripts/`.

Invocation:

```bash
python3 scripts/verify_install.py                      # headless (default)
python3 scripts/verify_install.py --plugin-root <path> # headless against a custom root
python3 scripts/verify_install.py probe <agent> --temp-path <path>  # probe-prompt mode
```

Tests at `scripts/test_verify_install.py`; discovered by
`python3 -m unittest discover -s scripts -p 'test_*.py'`. The
[CONTRIBUTING.md "Running the test suite" section](../../../CONTRIBUTING.md)
documents the second invocation a contributor needs alongside the
per-skill discoveries.

### Live mode is two-phase, not in-process

**Picked:** the script generates probe prompts (`probe` subcommand);
Claude drives the actual subagent spawns from the runbook in
CONTRIBUTING.md.
**Rejected:** in-process spawn (the Task tool is not callable from a
Python CLI; live-spawn is necessarily Claude-driven).

Rationale: cleanly separates the deterministic part (the probe-prompt
text — kept consistent via `verify_install.py probe`) from the
Claude-driven part (the spawn + result interpretation). The runbook
in CONTRIBUTING.md is the canonical place for the Claude-driven steps;
the probe-prompt generator gives it stable text to use.

### Capability test: attempted write at a script-provided temp path

**Picked:** the probe asks the subagent to attempt a write to a
caller-supplied temp file; expected outcome is per-agent (reviewer
refuses or fails; implementer succeeds; architect is recorded but
not gated).
**Rejected:** "subagent self-describes its tool list" (no reliable
introspection mechanism — Claude responses to such prompts have LLM
variance and can be confabulated).

The capability test grounds the verdict in filesystem state — the
temp file's existence is a falsifiable signal that's independent of
the subagent's textual response. The subagent's `write_succeeded:`
line is cross-check, not authority.

### Static checks for headless mode

Picked the four checks (`marketplace`, `manifest`, `agents`, `skills`)
because they cover the install-footprint surface the spec calls out:

- `marketplace` — `.claude-plugin/marketplace.json` exists, parses,
  lists `jig`.
- `manifest` — `.claude-plugin/plugin.json` exists, parses, has
  `name: "jig"`.
- `agents` — all three agent definitions are at
  `agents/{implementer,reviewer,architect}.md`.
- `skills` — at least one `skills/*/SKILL.md` is reachable. (Generic
  rather than hardcoded list: future skills don't require this check
  to be updated.)

The "uninstalled" sentinel: if `plugin.json` AND `marketplace.json`
AND `agents/` are all absent, we treat the plugin as unequivocally
not installed and exit 2 with a single actionable error
(`jig plugin not installed`), rather than emit four cascading FAILs.

### Exit-code semantics

Mirrors `tdd.py`:

- 0 — all headless checks passed.
- 1 — at least one check failed (install present but broken).
- 2 — plugin clearly not installed (the "uninstalled sentinel" above).

Argparse usage errors (unknown subcommand, missing `--temp-path`,
unknown agent name) also exit 2. This collision is benign for human
callers but is recorded in the deviation log so CI consumers know to
distinguish "headless says 2" from "argparse rejected my args."

## Open questions, deferred to later slices or inbox

- **Worktree behavior.** This slice landed from a worktree; whether
  `/plugin marketplace add` inside a worktree resolves correctly
  across worktree switches is unknown. The recipe in CONTRIBUTING.md
  steers contributors toward the main checkout. If a real worktree
  issue surfaces, file an inbox entry.
- **CI integration.** Live mode requires Claude Code; we don't have CI
  for that. Headless mode is in the test suite. If jig adopts CI
  later, headless mode is the only auto-runnable piece — live
  remains a manual gate.
- **Other callers of subagents.** AC #6 keeps `independent-review`
  unchanged. Caller upgrades (including the architect path) live in
  011-02 and later slices; not this slice.
