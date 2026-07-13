# Contributing to jig

> jig is a Claude Code plugin that develops itself. To get the full dev
> experience — including real `implementer` / `reviewer` / `architect`
> subagents — install jig locally as a plugin via the bundled dev
> marketplace.

Before you start, read [docs/workflow.md](docs/workflow.md) (the spec
lifecycle) and skim [docs/architecture.md](docs/architecture.md). Every
change to jig starts with a spec.

## Two install shapes

jig serves two distinct install shapes from a single source of truth.
Knowing the difference is load-bearing when you're hacking on jig
itself, because what you edit propagates differently to each mode.

- **Plugin install** (`/plugin install jig@jig`): the marketplace
  resolution path. Skills, agents, hooks, and helper `.py` files live
  under `${CLAUDE_PLUGIN_ROOT}` on disk; the project tree gets only
  docs and `scaffold.json`. Right for "install-and-forget" users who
  want central upgrades and an opaque runtime.
- **Scaffold install** (`/jig:scaffold-init`, default-on as of slice
  016-03): `scaffold.py` copies `skills/`, `agents/`, and
  `hooks/scripts/` into the target's `.claude/` (`.claude/skills/jig-*/`,
  `.claude/agents/jig-*.md`, `.claude/hooks/scripts/jig-*.sh`,
  `.claude/settings.json`), rewriting `${CLAUDE_PLUGIN_ROOT}/skills/<name>/`
  → `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` in SKILL.md
  bodies at copy time. Right for "scaffold-and-extend" users who want
  to own and customize the machinery under version control.

**jig's own working tree is the canonical scaffolded install.** The
repo root has `skills/`, `agents/`, and `hooks/scripts/` directly —
one level up from where they'd be in `.claude/` on a scaffolded
downstream project. This is by design; jig dogfoods by being its own
scaffolded install. The plugin distribution
(`scripts/build_release_zip.py`) packages the same tree as a zip.

### How changes propagate

- **Source SKILL.md edits** propagate to both modes. Plugin install
  reads source directly via `${CLAUDE_PLUGIN_ROOT}`; scaffold-mode
  applies the path rewrite at copy time. No separate build step is
  needed for either mode.
- **Hook scripts** (`hooks/scripts/jig-*.sh`) are mode-agnostic:
  they use `$CLAUDE_PROJECT_DIR` exclusively (audit-confirmed), so the
  same script body works under both `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/`
  and `${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`. Edits land in
  both without any rewrite.
- **Helper `.py` files** are mode-agnostic too. The `plugin_root()`
  helper at the top of each `.py` falls back to
  `Path(__file__).resolve().parents[N]`, so running a copied
  scaffolded `tdd.py` self-locates the right tree even with
  `${CLAUDE_PLUGIN_ROOT}` unset.

### Precedence when both modes coexist

If a user scaffolds jig into a project AND has the plugin installed
session-wide, **the scaffolded (project-scoped) skills win** by Claude
Code's existing project-scoped precedence. jig does not introduce a
new arbiter — this is the documented Claude Code skill-discovery rule.
The same applies to agents and hooks: the project's `.claude/`
versions take precedence over the plugin's.

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
runner. To run everything (current count: 800+ tests):

```bash
for d in skills/*/; do
  [ -e "$d"test_*.py ] && python3 -m unittest discover -s "$d" -p "test_*.py"
done
python3 -m unittest discover -s scripts -p "test_*.py"
```

The repo ships [`scripts/run_tests.py`](scripts/run_tests.py) as the
canonical fast test wrapper (CI calls it for the unit-test step); use it
locally while iterating:

```bash
python3 scripts/run_tests.py
```

Before pushing, run the CI-equivalent local gate:

```bash
python3 scripts/ci_check.py
```

That command mirrors [`.github/workflows/ci.yml`](.github/workflows/ci.yml):
tests, spec lint, manifest validation, the code-health floor, and host package
drift checks. The code-health floor reads [`.jig/lint-command`](.jig/lint-command),
which currently pins ruff via `pipx run --spec ruff==0.15.16 ...`; install
`pipx` locally so this gate exercises the same ruff path as CI.

When you add a new skill or top-level `scripts/`-style dir, make sure
its tests are discoverable by the same pattern.

### Test file naming — avoid bare-module collisions

Python 3.14's `unittest.discover` is stricter than 3.12: it refuses
to import two test modules with the same `__name__` across sibling
directories. Two skills that both ship `skills/<skill>/test_skill_surface.py`
collide because each imports as the bare module name `test_skill_surface`.

**Naming rule for skill test files**: include the skill name in the
file name so it's globally unique under `skills/*/test_*.py`. Examples:

- `skills/pr-review/test_skill_surface.py` ← bare name; **don't add a second**.
- `skills/arch-review/test_arch_review_skill_surface.py` ← correct shape.
- `skills/migrate/test_migrate.py` ← skill name is the file name.
- `skills/spec-workflow/test_workflow.py` ← skill name embedded.

When porting a slim-baseline skill from an existing one (e.g.
mirroring `pr-review`'s structure for a new judgment-only skill), do
NOT copy `test_skill_surface.py` verbatim — rename to
`test_<skill_name>_skill_surface.py` first.

Surfaced by spec 014-01 deviation §1.

## Contributing a bundled skill

jig is intentionally lean. Adding a bundled skill expands the default routing
and maintenance surface, so treat it as an exception rather than the normal
extension path. Before proposing one, establish all three of these conditions:

- the capability addresses recurring user pain, not a one-off workflow;
- it belongs in jig's spec, decision, review, or delivery workflow; and
- no existing jig skill already owns the job.

If those conditions do not hold, prefer a standalone skill that users can opt
into separately.

When a bundled skill is justified, use this author-register-validate flow:

1. Read the [skill-authoring conventions](docs/conventions.md#skill-authoring),
   then author the canonical source at `skills/<name>/SKILL.md` with any helper,
   examples, and focused tests beside it. Follow the existing
   [globally unique test-file naming rule](#test-file-naming--avoid-bare-module-collisions).
   Files under `hosts/` are generated package output; never edit them by hand.
2. Add the skill to its tier in `scaffold._TIER_SKILLS` in
   [`skills/scaffold-init/scaffold.py`](skills/scaffold-init/scaffold.py). This
   is the canonical per-tier inventory.
3. Update the two validator mirrors:
   `install_contract.EXPECTED_SKILLS` in
   [`scripts/install_contract.py`](scripts/install_contract.py) and
   `scaffold_contract._TIER_SKILLS` in
   [`scripts/scaffold_contract.py`](scripts/scaffold_contract.py). These
   validators deliberately restate the inventory to preserve their stdlib-only
   package-validation boundary; consistency tests pin both mirrors to the
   canonical table.
4. Update the two intentionally pinned test inventories for the selected tier:
   `TierSkillSetTests.EXPECTED_TIER_<N>` in
   [`skills/scaffold-init/test_scaffold.py`](skills/scaffold-init/test_scaffold.py)
   and `TierUpgradeTests.TIER<N>` in
   [`skills/migrate/test_migrate.py`](skills/migrate/test_migrate.py).
5. Add `evals/cases/<name>.json` with realistic positive and negative routing
   prompts. [`scripts/test_skill_routing.py`](scripts/test_skill_routing.py)
   enforces a one-to-one mapping between routable `SKILL.md` descriptions and
   these case files, so the skill must arrive with routing coverage.
6. Reconcile every product-facing inventory and count affected by the new
   skill: [`docs/product-vision.md`](docs/product-vision.md),
   [`README.md`](README.md),
   [`skills/vision-elicitation/worked-example-jig.md`](skills/vision-elicitation/worked-example-jig.md),
   and the Tier list in [`docs/memory/glossary.md`](docs/memory/glossary.md).
   If the skill has a Python helper, also update the helper rosters in
   [`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md). Check both counts and
   enumerations; some prose mirrors are not fully protected by tests.
7. Iterate with the fast wrapper:

   ```bash
   python3 scripts/run_tests.py
   ```

8. Regenerate both committed host packages, then run the final CI-equivalent
   gate:

   ```bash
   python3 scripts/build_host_packages.py
   python3 scripts/ci_check.py
   ```

   Commit the regenerated `hosts/` trees with the canonical source. The final
   gate covers routing, tests, manifests, lint, and host-package drift.

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

The release workflow attaches **one host-explicit zip per host** —
`jig-claude-vX.Y.Z.zip` (flat, drag-droppable) and `jig-codex-vX.Y.Z.zip`
(extract-then-add marketplace bundle) — to every GitHub Release. Both are
archived from the committed host packages under `hosts/` (see
[README § Install shapes](README.md#install-shapes)). The build script now
requires `--host`; you can build and verify either zip locally before pushing
any change to it:

```bash
# Build the Claude zip (writes to ./dist/jig-claude-v<version>.zip):
python3 scripts/build_release_zip.py --host claude --version 1.0.0

# Extract + run verify_install against the contents in one step:
python3 scripts/build_release_zip.py --host claude --smoke-test dist/jig-claude-v1.0.0.zip

# Build the Codex zip (extract-then-add bundle; no direct zip-drop install):
python3 scripts/build_release_zip.py --host codex --version 1.0.0
python3 scripts/build_release_zip.py --host codex --smoke-test dist/jig-codex-v1.0.0.zip
```

The Claude smoke-test prints the same `PASS marketplace / manifest / agents
/ skills` lines you'd see from `verify_install.py`. The CI `package` job runs
the equivalent steps in the release workflow. Because the committed `hosts/`
packages are source-derived build outputs kept fresh by the drift guard
(`python3 scripts/build_host_packages.py --check`) and **not hand-edited**,
regenerate them with `python3 scripts/build_host_packages.py` after any source
change rather than editing `hosts/` directly.

### Smoke-testing the Codex plugin package locally

Codex has a separate generated package and install path. Before shipping
Codex-facing packaging or hook-trust changes, run:

```bash
python3 scripts/codex_install_smoke.py
```

This builds the generated package under a temp workspace, validates the
Codex manifest/skills/hooks/marketplace descriptor, runs
`--install-codex-agents` against a temp agents directory, and then probes
`codex plugin marketplace add`, `codex plugin list`, `codex plugin add`,
model-visible skill discovery, hook config visibility, and the hook-trust
surface when a usable `codex` CLI is present. The command creates an isolated
child `CODEX_HOME` by default, so the marketplace and plugin add probes do
not mutate your real Codex config.

Useful knobs:

```bash
# Keep the temp build/CODEX_HOME around for inspection:
python3 scripts/codex_install_smoke.py --keep-work

# Make live Codex unavailability fail the run (useful on a Codex-capable box):
python3 scripts/codex_install_smoke.py --require-live-codex

# Reuse a named isolated home or choose a specific CLI:
JIG_CODEX_SMOKE_CODEX_HOME=/tmp/jig-codex-home \
JIG_CODEX_SMOKE_CODEX_BIN=/opt/homebrew/bin/codex \
python3 scripts/codex_install_smoke.py
```

If Codex is missing or a live-only command is not available in CI, the script
prints an `UNAVAILABLE ...` row instead of silently counting that probe as a
pass. Static package and custom-agent install failures remain hard failures.

When changing Codex custom-agent role behavior or sandbox assumptions, also
run:

```bash
python3 scripts/codex_role_capability_probe.py
```

This validates `jig-implementer`, `jig-reviewer`, and `jig-architect` TOML
files, then probes local Codex debug/sandbox surfaces when available. See
[docs/codex-role-capability.md](docs/codex-role-capability.md) for the
interactive `/agent` dogfood prompt and the noninteractive review fallback.

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

## Comparison and gap response

jig is regularly compared against other AI-native playbooks (notably
[adobe/mysticat-ai-native-guidelines](https://github.com/adobe/mysticat-ai-native-guidelines)).
A 2026-05 comparison — refreshed by a 2026-06-01 re-review — surfaced a set of
gaps. Each is either already addressed in the current docs/machinery or
delegated to an owner spec. This table is the triage, so contributors don't
have to rediscover it (it used to live in the README; spec 054-03 moved it
here to keep the public front door lean):

| Gap | Status | Owner |
|---|---|---|
| Stale first-read status | Landed | [slice 048-01](docs/specs/048-guidelines-gap-response/slice-01-first-read-status-and-gap-map.md) |
| Adoption / readiness guidance | Landed | [slice 048-02](docs/specs/048-guidelines-gap-response/slice-02-adoption-readiness-guide.md) + [048-03](docs/specs/048-guidelines-gap-response/slice-03-scaffolded-onboarding-handoff.md) |
| Amendment readability | Landed | [slice 048-04](docs/specs/048-guidelines-gap-response/slice-04-amendment-effective-state-digest.md) |
| First-read craft / leanness | This spec | [spec 054](docs/specs/054-docs-front-door/spec.md) |
| Tier truth (real copy gates) | Landed | [spec 038](docs/specs/038-tier-reconciliation/spec.md) |
| Reviewer-isolation honesty | Landed | [spec 040](docs/specs/040-isolation-honesty/spec.md) |
| Security & secrets floor (MUST-rules / `.gitignore` / secret-scan / permission deny-rules) | Planned | [spec 052](docs/specs/052-security-scaffold/spec.md) |
| Cross-tool portability (Codex / `AGENTS.md`) | Planned | [spec 033](docs/specs/033-host-adapter-portability/spec.md) |
| Scaffold artifact fidelity | Planned | [spec 046](docs/specs/046-scaffold-artifact-fidelity/spec.md) |
| Install-contract verification | Planned | [spec 047](docs/specs/047-install-contract-verification/spec.md) |
| Review-lifecycle evidence + gates | Planned | [spec 045](docs/specs/045-review-lifecycle-gates/spec.md) |

Legend: **Landed** = already in `main`; **This spec** = delivered by the named
in-flight spec (check the [status board](docs/specs/README.md) for which of
its slices have landed); **Planned** = a separate spec that moves on user
signal.

The 2026-06-01 re-review surfaced further net-new gaps — AI-usage disclosure
in PR bodies, baseline-alignment depth, operating-mode framing, model-routing
guidance, config-evolution discipline, and ADR-template parity. Each is routed
to an owner in spec 048's full
[gap inventory](docs/specs/048-guidelines-gap-response/spec.md#gap-inventory-routed).
