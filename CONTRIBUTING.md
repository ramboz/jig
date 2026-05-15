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
`jig`. Installing from it is equivalent to installing jig from
source, but it exercises the same plugin-resolution path an external
user would hit, so the three subagent definitions under
[`agents/`](agents/) become reachable as `subagent_type` values.

### Setup recipe

From a Claude Code session at the repo root:

```text
/plugin marketplace add .
/plugin install jig@jig
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
/plugin uninstall jig@jig
/plugin marketplace remove jig
```

After this, `subagent_type: "reviewer"` and friends will fall back to
`general-purpose` again (the documented pre-spec-011 behavior). You can
keep running jig from source — running `scripts/verify_install.py`
without the install will exit `2` with the actionable
`jig plugin not installed` message.

## Refreshing the install after edits (install-snapshot lag)

**Read this if you're editing jig and want a reviewer subagent to see
your changes.**

The Desktop app's graphical plugin manager installs jig by **copying**
the source tree to `~/.claude/plugins/marketplaces/<source>/jig/` — it
is NOT a symlink or path-link to your working checkout. Concretely:

- A `reviewer` subagent spawned via Task in a Claude Code session reads
  jig's code from the installed snapshot path, not from your working
  copy.
- Edits you make to `skills/`, `agents/`, `review.py`, etc. are
  **invisible** to that reviewer until you refresh the install.
- This bit slice 011-02's dogfood (deviation log §1-2): the first real-
  `jig:reviewer` pass returned `fail` because it reviewed a snapshot
  that pre-dated the slice's implementation by ~minutes.

The refresh recipe (from a Claude Code session, with your jig checkout
as the current dir):

```text
/plugin uninstall jig@jig
/plugin install jig@jig
```

If you originally installed via the graphical plugin manager rather
than `/plugin marketplace add .`, use **Settings → Plugins → jig →
Uninstall**, then re-add via the manager. The `local-desktop-app-uploads`
install path is regenerated each time.

After the refresh, **start a fresh Claude Code session** to get the
new agents reachable as `subagent_type` values (the available-agents
list is fixed at session start — see [docs/inbox.md](docs/inbox.md)
2026-05-13 install-snapshot-lag entry for context).

A `scripts/refresh-install.md` runbook ships with the repo as a
single-page summary of these steps.

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

## Versioning

The plugin's published version lives in
[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)'s `version`
field. **Do not edit it by hand.** It is managed by
[release-please](https://github.com/googleapis/release-please-action):
every merged release PR bumps the field via the
`extra-files` directive in
[`.github/release-please-config.json`](.github/release-please-config.json),
in lockstep with the matching tag and CHANGELOG entry.

The `release-please-manifest.json` tracks the last *released* version
(seeded at `0.1.0` so the first release-please PR can force `v1.0.0`
via `release-as`). After v1.0.0 lands, the manifest and `plugin.json`
both advance together on every subsequent release.

## Releasing

Releases are driven by
[release-please](https://github.com/googleapis/release-please-action). On every
push to `main`, the release workflow at
[`.github/workflows/release.yml`](.github/workflows/release.yml) inspects new
conventional-commit subjects and, if any of them warrant a version bump,
opens or updates a **release PR** that:

- bumps `.claude-plugin/plugin.json`'s `version` field,
- updates `CHANGELOG.md` with the user-facing entries (sections: Features /
  Bug Fixes / Performance / Documentation; `chore`, `refactor`, `test`, `ci`,
  `build` are hidden),
- updates [`.github/.release-please-manifest.json`](.github/.release-please-manifest.json).

Merging that release PR cuts a `vX.Y.Z` git tag and creates the GitHub
Release.

### Conventional-commit shapes that bump the version

| Subject prefix | Effect |
|---|---|
| `feat(scope): ...` | minor bump (e.g. 1.0.0 → 1.1.0) |
| `fix(scope): ...` | patch bump (e.g. 1.0.0 → 1.0.1) |
| `perf(scope): ...` | patch bump |
| Any of the above with `!:` or a `BREAKING CHANGE:` footer | major bump |
| `chore`, `docs`, `refactor`, `test`, `ci`, `build` | no version bump |

The PR-title workflow (`pr-title.yml`) enforces conventional shape on PR
titles. With squash-merge enabled, the PR title becomes the commit subject
on `main` — so release-please sees clean inputs.

### Inspecting / iterating on the release config

Dry-run the config locally before pushing changes to it:

```bash
npx release-please release-pr \
  --token=$GITHUB_TOKEN \
  --repo-url=ramboz/jig \
  --dry-run
```

The static checks in `scripts/test_release_config.py` also catch most
config-shape regressions before CI does.

### After v1.0.0 lands

The current config pins `release-as: "1.0.0"` to force the very first release
to be `v1.0.0` regardless of commit history. Once the v1.0.0 PR is merged
and the tag is cut, raise a small follow-up `chore(release): unpin
release-as after v1.0.0` PR that removes the `release-as` field from
`.github/release-please-config.json`. From that point on, version bumps
follow conventional-commit semantics organically.

### Building and smoke-testing a release zip locally

The release workflow attaches a `jig-vX.Y.Z.zip` asset to every GitHub
Release. You can build and verify the same zip locally before pushing
any change to the build script:

```bash
# Build the zip (writes to ./dist/jig-v<version>.zip):
python3 scripts/build_release_zip.py --version 1.0.0

# Extract + run verify_install against the contents in one step:
python3 scripts/build_release_zip.py --smoke-test dist/jig-v1.0.0.zip
```

The smoke-test prints the same four `PASS marketplace / manifest / agents
/ skills` lines you'd see from `verify_install.py` against the
checked-out repo. The CI `package` job runs the equivalent steps in
the release workflow.

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
