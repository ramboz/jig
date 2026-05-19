---
status: DONE
skill: (none — dev infrastructure)
tier: N/A
---

# Spec 013: release-pipeline

## Overview

jig has shipped Tier 0 + Tier 1 skills and is functionally stable, but the
distribution surface is still dev-only. [.claude-plugin/plugin.json](../../../.claude-plugin/plugin.json)
is pinned at `0.1.0`. No GitHub Actions exist. The bundled marketplace is
named `jig-dev` to signal local-checkout-only. There are no git tags, no
`CHANGELOG.md`, and the README defers public installation ("Not yet on the
plugin marketplace").

This spec adds a minimal-but-real CI + release pipeline on top of the existing
structure, without restructuring runtime code. The repo itself stays the
single source of truth: it serves as both source code AND the published
marketplace (no separate marketplace repo). Four slices land four
independently-mergeable pieces; after all four, anyone can install jig via
the Claude Code CLI (`/plugin marketplace add ramboz/jig`) or via a zip
asset attached to a GitHub Release.

## Why now

- **Public installability is the missing dogfood.** Slice 011-01 closed the
  local-plugin-install gap. The next gap is "a contributor who isn't me
  (or isn't the implementer agent) can install jig without cloning the
  repo." Today that's blocked solely by missing CI + release artifacts.
- **`tdd-loop` + `slice-land` are credible local gates but invisible to
  outsiders.** A green test suite on the contributor's laptop doesn't
  prove anything to a reviewer evaluating a PR or to a user evaluating
  whether to install jig. CI is the signal channel.
- **`pr-review` (slice 012-01) just landed.** It assumes PRs as the
  primary collaboration shape, but jig itself doesn't ship via PRs to
  any branch outside the contributor's local checkout. Closing the
  distribution loop completes the picture.
- **Existing commit history is already conventional-commits-shaped.**
  Spot-checking `git log`: `feat(slice-land):`, `fix(pr-review):`,
  `chore:`, `docs(...):` — already aligned with what release-please
  consumes. The cost to adopt is low; the cost to keep diverging grows.
- **Plan reviewed and approved.** See approved plan file
  `i-think-it-s-time-flickering-quilt.md` for the full rationale + the
  user-locked decisions (release-please, marketplace rename to `jig`,
  first release at `v1.0.0`, MIT license).

## Goals

1. **Continuous integration on PR + push to main.** Every PR runs the
   full test suite + spec_lint + JSON validation. Status visible on the
   PR page.
2. **Conventional-commit-driven releases.** Merging a PR with a `feat`,
   `fix`, or `perf` commit triggers a release-PR opened by
   `release-please`. Merging that release-PR cuts a tag + GitHub Release
   + CHANGELOG entry, and bumps `.claude-plugin/plugin.json` in lockstep.
3. **Release asset zip ready for Desktop install.** Each GitHub Release
   carries a `jig-vX.Y.Z.zip` whose contents (.claude-plugin/, agents/,
   skills/, hooks/, templates/, README, LICENSE) install cleanly when
   dragged into the Claude Code Desktop `/plugin` UI or loaded via
   `claude --plugin-dir <zip>`.
4. **Install documentation reflects the new reality.** README's
   Installation section names three install paths (CLI from repo, zip
   from release, source for contributors) with copy-pasteable commands.
   CONTRIBUTING.md updates the marketplace name and adds a short
   "Releasing" section.

## Non-goals

- **Submission to `claude.com/plugins`.** Distinct concern with its
  own surface; happens after `v1.0.0` is dogfooded externally.
- **Coverage reporting / codecov.** The test suite is already broad;
  adding coverage tooling is a separate ask.
- **Multi-platform CI matrix.** Ubuntu-only is sufficient for a
  Python + Markdown plugin.
- **Pre-commit hooks (`.pre-commit-config.yaml`).** `tdd-loop` already
  covers local test discipline.
- **Branch-protection rules on `main`.** User-facing GitHub setting;
  user configures it once CI is green.
- **A new skill or tier-class.** This spec is dev-infrastructure — same
  shape as spec 011-plugin-self-install. No new active skill, no
  Tier assignment.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** — Spike | Do we need a spike on release-please or zip packaging? | **No.** release-please is well-documented Google tooling with first-class GitHub Action support. Zip packaging uses Python stdlib (`zipfile`, `pathlib`) — no novel risk. The late-2026 plugin-distribution research (in the approved plan) closes the unknown about zip layout (flat at root, no wrapping dir). |
| **P** — Path | Single marketplace repo vs. publishing to a separate distribution repo? | **Single repo serves as both source and marketplace.** jig's `.claude-plugin/marketplace.json` already lists `source: ".."`. No reason to fork a marketplace repo when the user-facing install (`/plugin marketplace add ramboz/jig`) works against this repo directly. |
| **I** — Interface | One mega-PR or four slices? | **Four slices.** CI baseline (013-01), release-please scaffold (013-02), zip artifact (013-03), marketplace rename + docs (013-04). Each is independently mergeable; ordering lets each slice ride green-CI signal from the previous. |
| **D** — Data | What files does this introduce? | `.github/workflows/{ci,pr-title,release}.yml`, `.github/release-please-config.json`, `.github/.release-please-manifest.json`, `scripts/build_release_zip.py`, `scripts/test_build_release_zip.py`, `CHANGELOG.md`, `LICENSE`. Modifies `.claude-plugin/plugin.json` (version), `.claude-plugin/marketplace.json` (name), `README.md`, `CONTRIBUTING.md`, `.gitignore`. |
| **R** — Rules | What happens if a contributor lands a non-conventional commit? | PR-title workflow rejects the PR. Squash-merge → PR title becomes the commit subject, so release-please sees clean conventional commits on `main`. Edge case: direct push to `main` bypasses the PR-title check; mitigated by branch protection (out of scope here — user enables when ready). |

## Out of scope for spec 013 (any slice)

- **`scaffold-init` templating of release infrastructure for downstream
  projects.** Whether new projects scaffolded by `/jig:scaffold-init`
  should auto-include CI / release-please / etc. is a separate question
  (likely answer: no — too opinionated for a generic scaffold). Filed as
  a future inbox candidate if the question recurs.
- **Renovate / dependabot for GitHub Action version pinning.** Worth
  adding eventually but doesn't gate v1.0.0.
- **Signed commits / signed releases.** Out of scope; can be added later
  without redesign.
- **A "next" or "beta" release channel.** Single linear `main` channel
  is sufficient until contention exists.

## Known constraints

- **Conventional Commits is now load-bearing.** Post-013-02, the
  release version is computed from commit subjects. A `chore:` or
  `docs:` commit on `main` does NOT trigger a release. Only `feat`
  (minor), `fix` (patch), `perf` (patch), or anything with `!:` /
  `BREAKING CHANGE:` footer (major) triggers a version bump. This
  is intentional but worth knowing.
- **`release-as: "1.0.0"` is single-use.** The first release-please
  PR must be configured to force `v1.0.0` regardless of commit
  history. After that PR merges, the `release-as` field must be
  removed from `.github/release-please-config.json` so subsequent
  versions follow conventional-commit semantics organically. This is
  a one-line cleanup in slice 013-02's close-out.
- **Squash-merge is assumed for PRs.** The PR-title lint targets PR
  titles because squash-merge collapses the PR's commits into one
  subject = the PR title. Merge-commit or rebase-merge would require
  per-commit lint instead. User should set "Allow squash merging" as
  the only enabled merge type on the GitHub repo (user-facing
  setting — call out in 013-04's CONTRIBUTING.md update).
- **`scripts/verify_install.py` doesn't currently accept a `--root`
  flag.** The plan's verification step (4) suggests passing a custom
  root. If the flag doesn't exist when 013-03 reaches it, the smoke
  test runs the four checks ad-hoc via `cd` + relative paths inside
  the extracted zip. Decided by 013-03's implementer.
- **No `secrets.GITHUB_TOKEN` setup required.** GitHub Actions provides
  this token automatically; release-please uses it. No additional repo
  secrets needed.

---

## Slice 013-01 — ci-baseline

**STATUS: DONE**

**Goal:** Every PR + every push to `main` runs the existing test suite
(`scripts/run_tests.py`), the existing spec linter (`scripts/spec_lint.py`),
and a JSON-validation pass over the three manifest files
(`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
`hooks/hooks.json`). PR titles are validated as conventional-commit
shaped via a separate workflow. After this slice, contributors see a
green-CI signal on PRs before merge, and the bad-PR-title failure mode
is surfaced before merge instead of biting release-please later.

**DoR:**
- ✅ `scripts/run_tests.py` exists and is the canonical test entry point
  (per `.jig/test-command`).
- ✅ `scripts/spec_lint.py` exists with a documented exit-code contract.
- ✅ Repo is hosted on GitHub at `ramboz/jig` (verified via
  `git remote get-url origin`).
- ✅ No prior slice dependency — first slice of spec 013.

**Anti-horizontal-phasing check.** This slice is vertical: the *user* is
the contributor opening a PR; the user-observable outcome is the GitHub
Actions check appearing on the PR with pass/fail status. The slice
crosses all layers because it introduces:
- a new top-level directory (`.github/`),
- workflow YAML that GitHub's CI runtime parses,
- and an external observable signal (the PR's Checks tab).
No skill behavior changes — the test command being invoked already
exists and is unchanged.

**Acceptance Criteria:**

1. **`.github/workflows/ci.yml` exists** and triggers on:
   - `pull_request` (any branch)
   - `push` to `main`

2. **The `ci` job runs on `ubuntu-latest`** with a matrix over Python
   versions `3.11` and `3.12`. Both must pass for the check to be
   green.

3. **Job steps (in order):**
   - `actions/checkout@v4`
   - `actions/setup-python@v5` with the matrix Python version
   - `python3 scripts/run_tests.py` (no extra args — runs the
     documented full suite)
   - `python3 scripts/spec_lint.py` (no args — runs against
     `docs/specs/` by default)
   - A JSON-validation step that parses
     `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
     and `hooks/hooks.json` and exits non-zero on any parse failure
     OR if any required field is missing (`plugin.json.name`,
     `marketplace.json.name`, `hooks.json` parseable as object/array
     per the existing format).

4. **`.github/workflows/pr-title.yml` exists** and triggers on
   `pull_request` events `opened`, `edited`, `synchronize`. Uses
   `amannn/action-semantic-pull-request@v5`. Allowed types:
   `feat`, `fix`, `perf`, `docs`, `chore`, `refactor`, `test`,
   `build`, `ci`. Scope is required (`requireScope: true`) since the
   existing commit history consistently uses scopes
   (`feat(slice-land):`, `fix(pr-review):`).

5. **Both workflows are pinned to action SHAs OR major versions.**
   Use major-version pinning (`@v4`, `@v5`) for readability; the
   plan calls out that renovate/dependabot is out of scope but the
   format must be future-friendly.

6. **No existing test fails or changes.** The new workflows do not
   modify any code under `scripts/`, `skills/`, `agents/`, or
   `hooks/`. The test suite remains at its pre-slice count (485
   tests + the new tests added by this slice for the JSON-validation
   logic — see AC #7).

7. **The JSON-validation step is a testable Python script** at
   `scripts/validate_manifests.py` (NOT inline shell in the YAML),
   so it can be unit-tested under `scripts/test_validate_manifests.py`
   using the existing `unittest`-based suite. Tests cover:
   (a) all-valid: exits 0;
   (b) plugin.json missing `name`: exits non-zero with a clear
       message naming the missing field;
   (c) marketplace.json missing `name`: exits non-zero;
   (d) malformed JSON in any file: exits non-zero with the offending
       file path in the error message.
   The CI YAML calls `python3 scripts/validate_manifests.py`.

8. **`scripts/run_tests.py` continues to discover the new
   `test_validate_manifests.py`** automatically (it already discovers
   `scripts/test_*.py` per slice 011-01's deviation log §7). No
   wiring change in `run_tests.py` itself.

**Definition of Done:**

- [x] `.github/workflows/ci.yml` committed.
- [x] `.github/workflows/pr-title.yml` committed.
- [x] `scripts/validate_manifests.py` committed.
- [x] `scripts/test_validate_manifests.py` committed with the four
  test cases from AC #7.
- [x] Full test suite green locally (`python3 scripts/run_tests.py`).
- [x] Spec_lint clean (`python3 scripts/spec_lint.py`).
- [x] Implementation review passed.
- [x] Deviation log written.
- [x] Reconciliation review passed.

### Deviation log (013-01)

**1. Implementer was the main agent, not the real `jig:implementer` subagent.**
Mirrors slice 011-01 §1 — work was done in the main session under
implementer.md's TDD-first protocol (red → green → tests-stay-green
between every step) but without the fresh-context guarantee that
spawning the real subagent would provide. Implementation reviewer
subagent (next item) WAS the real `jig:reviewer`, so the
independent-evaluation half of the spec lifecycle held.

**2. Implementation review used the real `jig:reviewer` subagent.**
The session's available-agents list included `jig:reviewer` (jig is
installed locally as a plugin in this dev env, per spec 011's
outcome). Review returned `VERDICT: pass` with three SPECIFIC ISSUES
(items 3–5 below) and five RECONCILIATION NOTES (items 3–7 below).
The reviewer made 8 read-only Read tool calls; no Write/Edit/Bash
attempts. Output followed the documented VERDICT format.

**3. AC #3 spec_lint invocation diverges from "no args" wording.**
The AC said `python3 scripts/spec_lint.py` (no args — runs against
`docs/specs/` by default), but `scripts/spec_lint.py` requires a
positional `spec` argument (`spec_lint.py:256`). The implementer
worked around this with a bash `for` loop in
`.github/workflows/ci.yml:25-29`:
```
for spec in docs/specs/*/spec.md; do
  python3 scripts/spec_lint.py "$spec"
done
```
Under GitHub Actions' default `bash -e -o pipefail`, the loop
short-circuits on the first failing spec. Either the AC is wrong
about the tool's interface or `spec_lint.py` needs a no-arg /
directory-walking mode. Filed as a future inbox candidate; no
behavior impact on this slice.

**4. AC #4 pr-title trigger types include `reopened` (benign superset).**
The AC listed `opened`, `edited`, `synchronize`. The implementation
also fires on `reopened`. Closing-and-reopening a PR shouldn't be a
path that bypasses the title lint, so this is a defensive widening
rather than a deviation that needs unwinding.

**5. AC #4 pr-title also pins `subjectPattern: ^[a-z].*[^.]$`.**
The AC mandated `requireScope: true`. The implementation additionally
constrains the subject to start lowercase and not end with a period,
matching the existing commit-history style in jig
(`feat(slice-land): ...` — lowercase, no trailing period). Surfaced
as a custom error message so contributors see "must start lowercase
and not end with a period" instead of a generic regex failure. Worth
acknowledging as intentional extra strictness.

**6. AC #7 test scope expanded beyond the four required cases.**
The required four (all-valid; plugin.json missing name; marketplace.json
missing name; malformed JSON) are covered. Additionally:
`MissingFileTests` (covers missing plugin.json and missing hooks.json),
`RealRepoIntegrationTests` (the checked-in manifests validate clean),
`CliTests` (main() entry point with and without --root flag), and
`GeneratorIterableTests` (regression test from item 7). Positive
direction; total 15 tests in this file.

**7. Latent-bug fix from reviewer item 3 — generator exhaustion in `run()`.**
Reviewer flagged `validate_manifests.py:74` (pre-fix):
```python
total = len(tuple(manifests)) if not isinstance(manifests, tuple) else len(manifests)
```
The `manifests` parameter is typed `Iterable[ManifestSpec]`. If a
caller passed a generator, the `for spec in manifests:` loop above
would exhaust the iterator, so `len(tuple(manifests))` would compute
`len(())` = 0 and the summary line would print "0/0 manifest(s)
valid" regardless of how many manifests had been checked. Fixed by
snapshotting `specs = tuple(manifests)` at the top of `run()`. Added
`GeneratorIterableTests.test_generator_manifests_summary_counts_correctly`
as a regression test — verifies passing a generator yields "3/3"
in the summary.

**8. Test counts.** Pre-013-01 baseline: 485 (3 skipped). Post-013-01:
500 (3 skipped). New tests: 15 in `scripts/test_validate_manifests.py`
across 8 test classes (AllValidTests, PluginJsonMissingNameTests,
MarketplaceJsonMissingNameTests, MalformedJsonTests, MissingFileTests,
RealRepoIntegrationTests, GeneratorIterableTests, CliTests).

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache `Active specs` updated to reflect 013-01 DONE.
- [ ] CI workflow runs green on the PR introducing 013-01 itself
  (dogfood — the first PR with CI is also the first PR that proves
  CI works). Record the CI run URL in the deviation log.

---

## Slice 013-02 — release-please-scaffold

**STATUS: DONE**

**Goal:** Adding `release-please` to the repo so that merging a PR with
a `feat`, `fix`, or `perf` commit opens a "release PR" that bumps the
version + writes a CHANGELOG entry, and merging that release PR creates
a git tag + GitHub Release. First release is forced to `v1.0.0` via
`release-as`. No zip asset yet — that's slice 013-03.

**DoR:**
- ⏳ Slice 013-01 DONE (CI baseline is green so release-PR PRs ride
  the same signal).
- ✅ Conventional Commits are already in use across the existing
  commit history (verified by inspecting recent commits in
  `git log`).
- ✅ release-please supports a `release-type: "simple"` mode that
  doesn't assume a language-specific package manifest (verified in
  release-please docs research, approved plan).

**Anti-horizontal-phasing check.** Vertical: the user is the
maintainer; the user-observable outcome is "a release PR appears in
the PR list after the next merged `feat:` PR, and merging it tags
+ releases v1.0.0." Crosses all layers: GitHub Actions config
(release.yml), release-please config + manifest, version state in
`plugin.json`, a seeded CHANGELOG, and the on-GitHub artifact (Release
+ tag). No skill code changes.

**Acceptance Criteria:**

1. **`.github/workflows/release.yml` exists** and triggers on:
   - `push` to `main` (release-please observes the post-merge state)
   - `workflow_dispatch` (manual rerun for debugging)

2. **The `release-please` job uses `googleapis/release-please-action@v4`**
   with:
   - `config-file: .github/release-please-config.json`
   - `manifest-file: .github/.release-please-manifest.json`
   - Exposed outputs: `release_created`, `tag_name`, `version`
     (these will be consumed by 013-03's `package` job).

3. **`.github/release-please-config.json` exists** with the structure
   from the approved plan (§4). Critical fields:
   - `release-type: "simple"`
   - `packages."."` block with:
     - `release-as: "1.0.0"` (single-use; removed after v1.0.0 lands)
     - `extra-files: [{"type": "json", "path": ".claude-plugin/plugin.json", "jsonpath": "$.version"}]`
     - `changelog-sections` per the plan's full list (feat / fix /
       perf visible; docs visible; chore / refactor / test / ci /
       build hidden)

4. **`.github/.release-please-manifest.json` exists** declaring the
   current version of `.` as the pre-release baseline. Since the
   plugin.json is at `0.1.0`, the manifest seeds at `0.1.0`. The
   `release-as: "1.0.0"` in the config overrides the manifest for
   the first release.

5. **`.claude-plugin/plugin.json` is bumped from `0.1.0` to `1.0.0`**
   in the same slice commit. This synchronizes the source-tree state
   with what release-please will publish, so any contributor doing
   `cat .claude-plugin/plugin.json` post-merge sees the truth. The
   `extra-files` config keeps `plugin.json` in lockstep on every
   future release-please-driven bump.

6. **`CHANGELOG.md` is seeded** at the repo root with an empty
   `# Changelog` heading and a `## [Unreleased]` placeholder.
   release-please will rewrite this file from `v1.0.0` onward,
   replacing the placeholder with the v1.0.0 section.

7. **A dry-run section in CONTRIBUTING.md** (or a new
   `docs/releasing.md` — implementer's choice, recorded in the
   deviation log) explains:
   - the conventional-commit shapes that bump the version,
   - how to inspect / merge the release PR,
   - the post-merge cleanup of `release-as: "1.0.0"`,
   - that the dry-run command is
     `npx release-please release-pr --token=$GITHUB_TOKEN --repo-url=ramboz/jig --dry-run`
     for local validation of config changes.

8. **No release-related code changes in `scripts/`.** Release-please
   runs entirely as a GitHub Action; no helper script lives in `scripts/`.

9. **A `scripts/test_release_config.py` validates the
   release-please config statically** so the test suite catches a
   broken JSON / missing field before CI does. Tests:
   (a) `.github/release-please-config.json` parses as JSON;
   (b) it contains `packages."."`;
   (c) it sets `release-type: "simple"`;
   (d) the `extra-files` entry points at `.claude-plugin/plugin.json`
       with `jsonpath: "$.version"`;
   (e) `.github/.release-please-manifest.json` parses as JSON and
       declares a version for `.`.

10. **No regression in existing tests.** Full suite remains green
    post-slice.

**Definition of Done:**

- [x] 013-01 DONE.
- [x] `.github/workflows/release.yml` committed.
- [x] `.github/release-please-config.json` committed with
  `release-as: "1.0.0"`.
- [x] `.github/.release-please-manifest.json` committed.
- [x] `.claude-plugin/plugin.json` bumped to `1.0.0`.
- [x] `CHANGELOG.md` seeded.
- [x] CONTRIBUTING.md (or `docs/releasing.md`) "Releasing" section
  added per AC #7.
- [x] `scripts/test_release_config.py` committed with the five test
  cases from AC #9.
- [x] Full test suite green.
- [x] Implementation review passed.
- [x] Deviation log written.
- [x] Reconciliation review passed.

### Deviation log (013-02)

**1. Implementer was the main agent, not the real `jig:implementer` subagent.**
Same shape as 013-01 §1 — TDD-first work in the main session.

**2. Implementation review came back `needs-changes` on first pass; the real
`jig:reviewer` subagent caught a material AC #4 violation.** Initial
implementation seeded `.github/.release-please-manifest.json` at `"1.0.0"`
(reasoning: keep manifest and `plugin.json` in lockstep at HEAD). The
spec's "Known constraints" section + AC #4 explicitly said to seed at
`"0.1.0"` so `release-as: "1.0.0"` could override it on the first
release. With manifest == release-as == "1.0.0", release-please's
`simple` release type treats v1.0.0 as already-released and declines
to open the first release PR — defeating the slice's primary goal.
Fix: manifest re-seeded at `"0.1.0"` per AC #4; added
`test_manifest_seed_below_release_as_target` regression test in
`ReleasePleaseManifestTests` (scripts/test_release_config.py:110-128)
that pins the invariant during the bootstrap window AND self-disables
once `release-as` is removed (per the "After v1.0.0 lands" CONTRIBUTING
section). A confirmation review pass against the corrected files
returned `pass`.

**3. CHANGELOG seed initially carried a Keep-a-Changelog preamble; tightened
to match AC #6 literally.** Original seed had a paragraph block between
`# Changelog` and `## [Unreleased]` explaining the release-please
convention. AC #6 specified "an empty `# Changelog` heading and a
`## [Unreleased]` placeholder" — the preamble was a (minor) deviation
from "empty." Tightened to a literal heading + placeholder. The
release-please-managed CHANGELOG will pick up its own preamble shape
on first release; the CONTRIBUTING.md "Releasing" section now carries
the contributor-facing explanation that used to live in the CHANGELOG.

**4. `release.yml` permissions block omits `issues: write` intentionally.**
The reviewer noted release-please-action@v4 docs mention `issues:
write` "if release-please ever labels release PRs or comments on
issues." Current config uses neither — `contents: write` (tags +
release creation) + `pull-requests: write` (release PR) are
sufficient. Will add `issues: write` if a future change wires
release-please to label issues or comment.

**5. `release.yml` does not pass an explicit `token:` parameter.**
Standard release-please-action@v4 setup — the action defaults to
`${{ github.token }}` and uses the workflow's `permissions:` block.
Flagged here only because release-please setups commonly break on
token configuration, so a future maintainer searching for
"GITHUB_TOKEN" in the workflow won't find it explicitly.

**6. Test scope expanded beyond AC #9's five required cases.**
Required (a)–(e) all covered (5 tests in `ReleasePleaseConfigTests`
and `ReleasePleaseManifestTests`). Additionally: `VersionLockstepTests`
(1 test — plugin.json version matches `release-as` or manifest, catches
desync during the bootstrap window), `ChangelogSeedTests` (2 tests —
CHANGELOG exists; CHANGELOG has `# Changelog` heading),
`test_manifest_seed_below_release_as_target` in
`ReleasePleaseManifestTests` (1 test — the regression test from
item 2; self-disables once `release-as` is removed). Positive
direction; total 10 tests in this file across 4 test classes
(5 required + 4 additional test methods on top).

**7. Test counts.** Pre-013-02 baseline: 500 (3 skipped). Post-013-02:
510 (3 skipped). New tests: 10 in `scripts/test_release_config.py`.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache updated.
- [x] Post-v1.0.0 merge: `release-as: "1.0.0"` removed from
  `.github/release-please-config.json` and a `chore(release): unpin
  release-as after v1.0.0` follow-up PR raised. Tracked here, not
  in this slice's DoD (depends on the v1.0.0 release PR being
  merged, which happens after this slice DoNE). — Resolved 2026-05-18:
  config has no `release-as` field; release-please has driven v1.0.0
  → v1.1.0 → v1.2.0 → v1.3.0 naturally.

---

## Slice 013-03 — release-zip-artifact

**STATUS: DONE**

**Goal:** When release-please publishes a new GitHub Release (via
slice 013-02), an additional CI job builds a `jig-vX.Y.Z.zip` from the
release tag's tree, smoke-tests that the zip's contents pass
`verify_install.py`'s four checks, and attaches the zip to the Release
as a downloadable asset. After this slice, the v1.0.0 GitHub Release
will have an installable zip alongside its CHANGELOG entry.

**DoR:**
- ⏳ Slice 013-02 DONE (release-please is creating Releases that 013-03
  can hook onto).
- ✅ `scripts/verify_install.py` exists and runs 4 headless checks.
- ✅ The runtime-vs-dev file taxonomy is documented in the approved
  plan (§5).

**Anti-horizontal-phasing check.** Vertical: the user is anyone wanting
to install jig from a downloaded zip; the user-observable outcome is
a `.zip` asset attached to the GitHub Release that, when extracted and
loaded via `claude --plugin-dir <zip>` or dragged into Desktop, works.
Crosses all layers: a new Python builder script, a CI job that runs
it, a smoke test that proves it, and a release asset upload via `gh`.

**Acceptance Criteria:**

1. **`scripts/build_release_zip.py` exists** as a standalone Python
   script (no external deps; stdlib only). CLI:
   ```
   python3 scripts/build_release_zip.py --version <X.Y.Z> [--output <path>]
   ```
   Produces `dist/jig-v<X.Y.Z>.zip` (or the user-specified path) from
   the current working directory.

2. **Zip contents are flat at the root** (NO wrapping `jig/` directory):
   - `.claude-plugin/` (plugin.json + marketplace.json)
   - `agents/` (architect.md, implementer.md, reviewer.md)
   - `skills/` — all skill directories AND their helper `.py`
     files (adr.py, workflow.py, tdd.py, land.py, migrate.py,
     review.py, etc.), BUT **excluding** any `test_*.py` files.
   - `hooks/` (hooks.json + hooks/scripts/*)
   - `templates/` (loaded at runtime by `scaffold-init`)
   - `README.md`
   - `LICENSE` (added in slice 013-04 — if not yet present at
     build time, the builder warns but doesn't fail; the v1.0.0
     zip cuts AFTER 013-04 lands so the warning never fires in
     practice).

3. **Zip explicitly excludes:**
   - All `test_*.py` files anywhere in the tree
   - `scripts/` (entire directory — dev tooling only)
   - `docs/` (entire directory)
   - `.github/`, `.git/`, `.gitignore`
   - `.jig/`, `.claude/`
   - `CLAUDE.md`, `CONTRIBUTING.md`
   - `settings.json`
   - `__pycache__/`, `*.pyc`, `.DS_Store`, `.pytest_cache/`,
     `.mypy_cache/` (defensive — none exist today but future-proof)

4. **The builder validates its output before exiting 0:**
   - The produced zip contains `.claude-plugin/plugin.json` at the
     expected path (not nested in a wrapping dir).
   - The version inside the zipped `plugin.json` matches `--version`.
     If they don't match, the builder fails (exit 2) rather than
     producing a mislabeled artifact.

5. **`scripts/test_build_release_zip.py` covers:**
   - Builder produces a non-empty zip at the expected path.
   - Zip contains `.claude-plugin/plugin.json` at root.
   - Zip contains `agents/reviewer.md` at root.
   - Zip contains at least one SKILL.md under `skills/`.
   - Zip does NOT contain any `test_*.py` files.
   - Zip does NOT contain `scripts/`, `docs/`, `.github/`,
     `CLAUDE.md`, `CONTRIBUTING.md`.
   - Version-mismatch case: passing `--version 9.9.9` against a
     `plugin.json` that says `1.0.0` exits non-zero with a clear
     mismatch message.
   - Builder is idempotent: running twice produces a bit-identical
     zip (sorted entries, fixed mtimes — use `zipfile.ZipInfo`
     with a stable timestamp or `git archive`'s approach).

6. **`.github/workflows/release.yml` gains a `package` job** that:
   - Requires `release-please` (`needs: release-please`).
   - Runs only when `needs.release-please.outputs.release_created == 'true'`.
   - Checks out at `ref: ${{ needs.release-please.outputs.tag_name }}`.
   - Sets up Python 3.12 (single version — release-bound, not a
     matrix concern).
   - Runs `python3 scripts/build_release_zip.py --version ${{ needs.release-please.outputs.version }}`.
   - Smoke-test step: extracts the zip to a tempdir and runs the
     four-check core of `verify_install.py` against the extracted
     tree (either via `--root <path>` if added by the implementer,
     or by ad-hoc Python calls that exercise the same checks).
   - Upload step: `gh release upload ${{ needs.release-please.outputs.tag_name }} dist/jig-v${{ needs.release-please.outputs.version }}.zip` using `GITHUB_TOKEN`.

7. **The smoke test is also runnable locally** via a single command:
   `python3 scripts/build_release_zip.py --version 1.0.0 && python3 scripts/build_release_zip.py --smoke-test dist/jig-v1.0.0.zip`
   (or equivalent — implementer's call on the exact CLI shape).
   Documented in CONTRIBUTING.md.

8. **`.gitignore` is updated** to include `dist/` and `*.zip` so the
   local-built zip doesn't accidentally land in a commit.

9. **No regression in existing tests.** Full suite green.

**Definition of Done:**

- [x] 013-02 DONE.
- [x] `scripts/build_release_zip.py` committed.
- [x] `scripts/test_build_release_zip.py` committed.
- [x] `.github/workflows/release.yml` extended with the `package` job.
- [x] `.gitignore` updated.
- [x] Local smoke test passes (`python3 scripts/build_release_zip.py
  --version 1.0.0` + `verify_install.py` on the extracted tree).
- [x] Full test suite green.
- [x] Implementation review passed.
- [x] Deviation log written.
- [x] Reconciliation review passed.

### Deviation log (013-03)

**1. Implementer was the main agent, not the real `jig:implementer`
subagent.** Same shape as 013-01 §1 and 013-02 §1 — TDD-first work in the
main session.

**2. Implementation review came back `needs-changes` on first pass; the
real `jig:reviewer` subagent caught two material AC violations.**
- **AC #7 unmet**: no local-runnable smoke-test command, no CONTRIBUTING.md
  documentation for one.
- **AC #2 LICENSE-warning missing**: builder silently skipped when LICENSE
  was absent rather than emitting a warning per the AC.
Fix described in §3–§4. Confirmation review pass returned `pass`.

**3. Fix for AC #7 — added `--smoke-test ZIP` mode + documentation.**
`build_release_zip.py` now exposes a `smoke_test(zip_path)` function and a
`--smoke-test ZIP` CLI flag that extracts the named zip to a tempdir and
runs `verify_install.run_headless` against the extracted tree, returning
the underlying verify exit code (0/1/2). CONTRIBUTING.md gains a
"Building and smoke-testing a release zip locally" section under the
"Releasing" header (two-step recipe; AC explicitly allowed "or
equivalent — implementer's call on the exact CLI shape"). The release.yml
`package` job's smoke-test step now invokes the same
`build_release_zip.py --smoke-test ...` command instead of an inline
heredoc, so local and CI smoke-tests share one code path.

**4. Fix for AC #2 — `_warn_missing_optional_files` warning.**
Added a warning step that iterates `_INCLUDE_FILES` (README + LICENSE)
and emits `WARN: optional file '<name>' not found at source root; ...`
for each missing entry. The build still succeeds (exit 0) when LICENSE is
absent, matching AC #2's "the builder warns but doesn't fail" wording.
The warning self-silences once 013-04 lands LICENSE. Slightly more
general than AC #2's LICENSE-specific phrasing — README would also
trigger it if absent, but README is present so no extra noise.
`MissingLicenseWarningTests` covers both present-LICENSE and
absent-LICENSE branches.

**5. Bug found and fixed during implementation — `hooks/scripts/*.sh`
was silently excluded by an over-broad directory name filter.**
Initial `_EXCLUDE_DIR_NAMES` included `"scripts"` to match the top-level
dev-only `scripts/` directory. The walker checks every path component
against this set, so `hooks/scripts/jig-*.sh` (the actual hook scripts
invoked at runtime by `hooks/hooks.json`) was filtered out — silently
breaking every hook event on the installed plugin. First builder run
produced 32 entries; correct count is 63. Fixed by limiting
`_EXCLUDE_DIR_NAMES` to defensive cache exclusions only (`__pycache__`,
`.pytest_cache`, `.mypy_cache`) and relying on `_INCLUDE_ROOTS` to
implicitly exclude top-level dev-only dirs (which are never walked).
Comment at `build_release_zip.py:50-56` explains the rationale to deter
future re-broadening. Added `test_hook_scripts_present` as regression
test in `InclusionTests`.

**6. Idempotency tightened to cross-platform — `ZipInfo.create_system`
pinned to `3` (Unix).** Default `create_system` is platform-dependent
(macOS = 3, Windows = 0). Without pinning, the zip built on a
contributor's macOS laptop and the zip built on `ubuntu-latest` CI would
differ in two bytes of metadata per entry. `IdempotencyTests` previously
only checked same-machine reproducibility (the AC's literal requirement);
the pin makes the stronger guarantee true. Documented for the next
maintainer who wonders why the field is set explicitly.

**7. CONTRIBUTING.md presents two separate commands instead of the AC's
`&&`-chained one-liner.** AC #7's example was
`python3 scripts/build_release_zip.py --version 1.0.0 && python3
scripts/build_release_zip.py --smoke-test dist/jig-v1.0.0.zip`. The
implemented documentation presents these as two separate code blocks
because the second relies on the artifact produced by the first — easier
to scan when read by a human, and the AC explicitly allowed "or
equivalent — implementer's call." Worth flagging for transparency.

**8. `_validate_output` post-write version check is defensive layering.**
The pre-build check at the top of `build()` already enforces the
`--version` ↔ `plugin.json` match before any I/O fires, so the
post-write read of plugin.json from inside the produced zip is
strictly dead code for the version-mismatch path. Kept anyway because
it's cheap and protects against a hypothetical future where the
builder mutates the manifest mid-build (today it doesn't; copy-only
construction). Flagged by reviewer; intentionally kept.

**9. Test counts.** Pre-013-03 baseline: 510 (3 skipped). Post-013-03:
540 (3 skipped). New tests: 30 in `scripts/test_build_release_zip.py`
across 9 test classes (BuildOutputTests, InclusionTests with
`test_hook_scripts_present` regression, ExclusionTests, VersionMismatchTests,
IdempotencyTests, ManifestContentTests, CliTests, SmokeTestTests,
MissingLicenseWarningTests).

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache updated.
- [x] The v1.0.0 release (created by 013-02's PR merge) gets the
  zip retroactively attached IF the slice landed after the release.
  If 013-03 lands before v1.0.0, the zip is automatically attached
  via the `package` job. Either path produces the same end state.
  — Resolved 2026-05-18: `gh release view v1.0.0` confirms
  `jig-v1.0.0.zip` is attached (113,557 bytes, sha256
  `f93b2cd064bb932195f2bd1585f08748d7df6843102b6705db510551a431324a`).

---

## Slice 013-04 — marketplace-rename-and-docs

**STATUS: DONE**

**Goal:** Rename the marketplace from `jig-dev` to `jig` (public-facing
canonical name), rewrite README's Installation section to document the
three install paths (CLI from repo, zip from release, source for
contributors), update CONTRIBUTING.md to match the new marketplace
name, and add a top-level `LICENSE` file (MIT). This slice doubles as
the dogfood pass: a fresh contributor following the new README in a
clean Claude Code session should be able to install jig from scratch.

**DoR:**
- ⏳ Slice 013-03 DONE (the zip artifact format documented in the new
  README install path actually exists by the time the docs reference it).
- ✅ Marketplace rename target is `jig` (user-locked decision).
- ✅ License choice is MIT, copyright "Julien Ramboz" (user-locked).

**Anti-horizontal-phasing check.** Vertical: the user is a brand-new
contributor / installer; the user-observable outcome is being able to
run `/plugin marketplace add ramboz/jig` + `/plugin install jig@jig`
and have it work. Crosses all layers: marketplace.json (config),
README (public docs), CONTRIBUTING.md (contributor docs), LICENSE
(legal surface).

**Acceptance Criteria:**

1. **`.claude-plugin/marketplace.json` is renamed** at the marketplace
   `name` field: `"jig-dev"` → `"jig"`. The plugin entry name stays
   `"jig"`. Resulting public install command is
   `/plugin install jig@jig`.

2. **`README.md` Installation section is rewritten** to document three
   install paths, in this order:
   - **From this repository (Claude Code CLI):**
     `/plugin marketplace add ramboz/jig` + `/plugin install jig@jig`
   - **From a release zip (Claude Code Desktop):** Download
     `jig-vX.Y.Z.zip` from the Releases page; drag into Desktop
     `/plugin` UI; or `claude --plugin-dir path/to/jig-vX.Y.Z.zip`
     for a session-only install.
   - **From source (contributors):** Pointer to CONTRIBUTING.md.

3. **The README also calls out the squash-merge convention** in a
   short "Contributing" section (or appended to the existing one),
   since the PR-title lint introduced in 013-01 depends on it.

4. **`CONTRIBUTING.md` updates:**
   - Marketplace ID references change from `jig-dev` to `jig`
     everywhere (`/plugin install jig@jig-dev` → `/plugin install
     jig@jig`).
   - A new "Releasing" section (referenced by 013-02 AC #7) is in
     place or refined.
   - A "Versioning" subsection explains that the version lives in
     `.claude-plugin/plugin.json` and is managed by release-please.

5. **`LICENSE` file exists** at the repo root, with standard MIT
   text, copyright "Julien Ramboz" and the current year.

6. **The `LICENSE` file is included in the release zip** (verified
   by re-running `scripts/build_release_zip.py` after 013-04 and
   asserting `LICENSE` is present in the zip listing). If
   `build_release_zip.py` was written in 013-03 without `LICENSE`
   in the include list, 013-04 fixes that — explicit deviation
   log entry if so.

7. **Tests cover the marketplace rename:**
   `scripts/test_validate_manifests.py` (from 013-01) gains an
   assertion that `marketplace.json.name == "jig"`. The earlier
   tests would have passed with `jig-dev` too; this slice tightens
   the check.

8. **Dogfood: a contributor following the README's "From this
   repository" path in a fresh Claude Code session can install jig
   from `main` and have at least one jig skill discoverable**
   (e.g. `/jig:scaffold-init`). Either the implementer or the user
   performs this dogfood manually and records the result in the
   deviation log with a timestamp. **This dogfood is an AC, not just
   a DoD line** — it's the load-bearing why-now claim of the entire
   spec, mirroring 011-02 AC #6's pattern.

9. **No regression in existing tests.** Full suite green.

**Definition of Done:**

- [x] 013-03 DONE.
- [x] `.claude-plugin/marketplace.json` renamed.
- [x] README.md install section rewritten per AC #2.
- [x] CONTRIBUTING.md updated per AC #4.
- [x] LICENSE committed.
- [x] `scripts/build_release_zip.py` (or its include list)
  references `LICENSE`.
- [x] `scripts/test_validate_manifests.py` updated per AC #7.
- [x] Full test suite green.
- [x] Dogfood per AC #8 completed and recorded in deviation log.
  — Resolved 2026-05-18: user-driven dogfood ran successfully
  (`/plugin marketplace add ramboz/jig` + `/plugin install jig@jig`
  in a fresh Claude Code session); jig skills discoverable post-install.
- [x] Implementation review passed.
- [x] Deviation log written.
- [x] Reconciliation review passed.

### Deviation log (013-04)

**1. Implementer was the main agent, not the real `jig:implementer`
subagent.** Same shape as 013-01/02/03 §1 — TDD-light work (this slice
was mostly documentation + rename, with one new test pin).

**2. Implementation review came back `needs-changes` on first pass; the
real `jig:reviewer` subagent caught three stale `jig-dev` references
that the main-pass rename missed.**
- `scripts/refresh-install.md:34-35` — the user-facing install/uninstall
  recipe still said `jig@jig-dev`. **Blocking** — would break any
  contributor following the runbook after the rename.
- `docs/architecture.md:49` — prose said "the `jig-dev` local
  marketplace." **Material but not blocking** — stale narrative.
- `scripts/test_verify_install.py:35` — fake test-fixture marketplace
  name still hardcoded `"jig-dev"`. **Cosmetic** — harmless but
  noisy for grep-driven future renames.
All three fixed in one pass. Refresh-install.md and architecture.md now
say `jig`; architecture.md retains the historical context "renamed from
`jig-dev` in slice 013-04" so the audit trail stays readable. Test
fixture pinned to `"jig"`. Confirmation review returned `pass` on all
three.

**3. AC #6 — `_INCLUDE_FILES` already references LICENSE from 013-03.**
Slice 013-03's `_warn_missing_optional_files` step (013-03 deviation
§4) added LICENSE to the include list; 013-04 only committed the
LICENSE file itself. Verified post-013-04 build: zip now has 64
entries (was 63 pre-LICENSE), `LICENSE` is the first entry by sort
order. No `WARN: optional file 'LICENSE'` line fires anymore.

**4. AC #8 dogfood deferred to user post-merge.** The dogfood scenario
requires installing jig in a fresh Claude Code session from the
GitHub repo URL (`/plugin marketplace add ramboz/jig` +
`/plugin install jig@jig`) and confirming at least one jig skill is
discoverable. The implementer can't easily spawn a fresh session from
inside the current one; per precedent in slice 011-01 §9 and slice
012-01 §9, the user performs this verification post-merge and the
result is recorded as a Close-out item. AC #8 is therefore
**implementer-prepared, awaiting user confirmation**. The DoD
"Dogfood per AC #8" checkbox stays unticked until the user records
the result.

**5. CONTRIBUTING.md "Versioning" section added.** Per AC #4, a new
subsection landed above the existing "Releasing" section (added in
013-02). Covers: the version lives in `plugin.json`, release-please
manages it via `extra-files`, the manifest tracks last released
version, `release-as: "1.0.0"` is single-use for the bootstrap.

**6. README.md "Contributing" section gained a squash-merge call-out.**
Per AC #3, the existing "Contributing" section now explicitly states
that PRs are merged via squash-merge so release-please reads clean
conventional-commit subjects, and points at the PR-title workflow
introduced by slice 013-01.

**7. Test count.** Pre-013-04 baseline: 540 (3 skipped). Post-013-04:
541 (3 skipped). New test: 1 — `test_marketplace_name_is_jig` in
`RealRepoIntegrationTests` (`scripts/test_validate_manifests.py`).
The existing four `RealRepoIntegrationTests` cases would have passed
with `jig-dev` too — this slice tightens the check.

**8. Rollback name collision is a deliberate trade-off.** Renaming
the marketplace from `jig-dev` to `jig` means the rollback command
`/plugin marketplace remove jig` now refers to the same name a public
user would have added via `/plugin marketplace add ramboz/jig`.
Contributors who installed under the old `jig-dev` name should
update their local install (or use `scripts/refresh-install.md` —
already pointed at `jig@jig`) before relying on the rollback. Worth
calling out for any maintainer who develops jig on multiple machines
and needs to interop with pre-013-04 installs.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache `Active specs` updated to mark spec 013
  effectively complete.
- [x] Inbox entry "Public installability of jig" (if present) marked
  RESOLVED with a reference back to this spec. — N/A; no such inbox
  entry existed at the time of close-out (verified via `grep -n
  "Public installability" docs/inbox.md` returning no matches).
- [x] **User-driven dogfood per AC #8** — fresh Claude Code session,
  `/plugin marketplace add ramboz/jig` + `/plugin install jig@jig`,
  confirm `/jig:scaffold-init` (or any other jig skill) is
  discoverable. Result recorded here with timestamp. Only fires
  after this PR merges to `main` (the marketplace.json rename
  is on `main`). — Resolved 2026-05-18: user confirmed the
  marketplace add + plugin install completed successfully in a fresh
  session and jig skills were discoverable. Spec 013 fully closed.

---

## References

- **Approved plan:** `/Users/ramboz/.claude/plans/i-think-it-s-time-flickering-quilt.md`
- **Precedent — same dev-infra shape:** [spec 011-plugin-self-install](../011-plugin-self-install/spec.md)
- **release-please documentation:**
  https://github.com/googleapis/release-please-action
- **Claude Code plugin distribution docs:**
  https://code.claude.com/docs/en/plugin-marketplaces
- **Conventional Commits:** https://www.conventionalcommits.org/
- **PR-title lint action:** https://github.com/amannn/action-semantic-pull-request
