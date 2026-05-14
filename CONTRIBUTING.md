# Contributing to jig

> jig is a Claude Code plugin that develops itself. To get the full dev
> experience — including real `implementer` / `reviewer` / `architect`
> subagents — install jig locally as a plugin via the bundled dev
> marketplace.

Before you start, read [docs/workflow.md](docs/workflow.md) (the spec
lifecycle) and skim [docs/architecture.md](docs/architecture.md). Every
change to jig starts with a spec.

## Local dev install

The repo ships a marketplace descriptor at
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
that registers this checkout as a single-plugin marketplace named
`jig-dev`. Installing from it is equivalent to installing jig from
source, but it exercises the same plugin-resolution path an external
user would hit, so the three subagent definitions under
[`agents/`](agents/) become reachable as `subagent_type` values.

### Setup recipe

From a Claude Code session at the repo root:

```text
/plugin marketplace add .
/plugin install jig@jig-dev
```

**Restart Claude Code (or open a fresh session) after install.**
Plugin-provided subagent types (`reviewer` / `implementer` /
`architect`) only become reachable in sessions started **after** the
install lands; an already-running session's available-agents list is
fixed at startup and won't pick up new agents mid-session. The
Desktop app's `/reload-plugins` slash command reloads skill content
but does NOT make new subagent types reachable in the current
session.

Then, from a shell at the repo root, run the **headless verify**:

```bash
python3 scripts/verify_install.py
```

Expected output is four `PASS` lines and `summary: 4/4 passed`. Exit
code `0`. If you see `FAIL — jig plugin not installed`, the install
didn't land; re-run the two `/plugin` commands and try again. If a
specific check fails (e.g. `FAIL agents: missing agent file(s):
reviewer`), the install footprint is incomplete — file an inbox entry
under [docs/inbox.md](docs/inbox.md).

### Live verify (manual gate)

Headless verify confirms the install footprint is on disk. **Live verify
confirms the subagent types actually resolve at runtime** — i.e. that
`subagent_type: "reviewer"` from the Task tool reaches
[`agents/reviewer.md`](agents/reviewer.md) instead of silently falling
back to `general-purpose`.

Live verify is a manual gate run inside a Claude Code session, once,
right after install. The procedure is a runbook for Claude to execute:

1. Pick a temp path the subagent should write, e.g.
   `/tmp/jig-verify-<random>.txt`. Make sure it doesn't already exist.
2. For each agent type in `(reviewer, implementer, architect)`:
   - Run `python3 scripts/verify_install.py probe <agent> --temp-path <temp_path>`
     to get the capability-probe prompt.
   - Spawn the subagent via the Task tool with `subagent_type: "<agent>"`
     and the probe prompt as input. Use a fresh temp path per agent so
     results don't bleed.
   - Note the subagent's reported `write_succeeded:` line **and** check
     the temp file's existence on disk.
3. Expected outcomes:
   - **`reviewer`**: `write_succeeded: no` AND temp file does NOT exist.
     (Read-only tool restriction enforced.) If the temp file exists,
     `reviewer` resolved to `general-purpose` — the install isn't
     wired right.
   - **`implementer`**: `write_succeeded: yes` AND temp file exists
     with `jig-verify-ok`. (Implementer has Write.)
   - **`architect`**: write may or may not succeed depending on the
     agent's tool list. Spec 011-01 treats this as check-only with no
     caller upgrade — record the outcome, don't gate on it.
4. Record the result (timestamp + per-agent outcome) in the spec's
   deviation log for the slice that ran live verify.

If `reviewer` succeeds at writing the temp file, **stop** and file an
inbox entry — the install didn't actually wire the read-only
restriction, which is the whole point of the dogfood.

## Rollback

To remove the local dev install:

```text
/plugin uninstall jig@jig-dev
/plugin marketplace remove jig-dev
```

After this, `subagent_type: "reviewer"` and friends will fall back to
`general-purpose` again (the documented pre-spec-011 behavior). You can
keep running jig from source — running `scripts/verify_install.py`
without the install will exit `2` with the actionable
`jig plugin not installed` message.

## Running the test suite

jig uses per-skill `python3 -m unittest discover` with no top-level
runner. To run everything (current count: 350+ tests):

```bash
for d in skills/*/; do
  [ -e "$d"test_*.py ] && python3 -m unittest discover -s "$d" -p "test_*.py"
done
python3 -m unittest discover -s scripts -p "test_*.py"
```

When you add a new skill or top-level `scripts/`-style dir, make sure
its tests are discoverable by the same pattern.

## Spec workflow (short version)

1. Pick up the next `READY_FOR_IMPLEMENTATION` slice from
   [docs/specs/README.md](docs/specs/README.md).
2. Transition it to `IN_PROGRESS`:
   `python3 skills/spec-workflow/workflow.py transition docs/specs/<spec>/spec.md "<slice>" IN_PROGRESS`
3. Implement TDD: write failing tests per AC, then the minimum code to
   make them pass.
4. Run the test suite (above) and confirm no regressions.
5. Trigger an `independent-review` pass — the upgraded reviewer (post-
   spec-011-02) routes to the real `reviewer` subagent. Pre-spec-011-02,
   it falls back to `general-purpose`.
6. Address findings, write the deviation log under the slice's
   `### Deviation log (NNN-NN)` subsection.
7. Trigger reconciliation review.
8. Transition the slice to `DONE`. Regenerate the status board.
9. Update CLAUDE.md Hot Cache and tick the slice's Close-out checkboxes.

Full details in [docs/workflow.md](docs/workflow.md).
