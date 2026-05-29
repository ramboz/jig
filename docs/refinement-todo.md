> Decisions the initial setup explicitly deferred. Each item has a resolution trigger.
> Resolve items by writing an ADR and linking it here.

# Refinement Todo: jig

## Architecture

### Decision: Hook strictness profiles
**Deferred:** Shipping an unread `SCAFFOLD_HOOK_PROFILE` env var creates false expectations. Need to define values AND implement profile-switching logic before exposing.
**Resolution trigger:** First spec that touches hook enforcement behavior (likely 001-03 or a dedicated Tier 1 spec).
**Valid values to define:** `minimal | standard | strict`

### Decision: SubagentStart hook event
**Deferred:** `SubagentStart` is documented in the changelog (v2.0.43) but absent from the official plugin docs' hook events list. Risk of API instability.
**Resolution trigger:** First time we need to react to subagent start (e.g., reviewer logging, effort-scaling enforcement).
**Risk:** Event name or behavior may differ from expectations. Test before relying on it.

### Decision: Multi-central federation membership
**Deferred:** Spec 034 (Federation tier) v1 enforces exactly one central per member with a clear error on second-federation attempt. Real shared libraries belonging to two product orgs (e.g., a UI kit consumed by two product federations) would need `central_repo` to become a list, with declared precedence for conventions / glossary / ADR merges — adding schema and merge-precedence complexity to slice 034-01. Surfaced by `/jig:clarify` on `docs/specs/034-federation-tier/spec.md` Q2 (Scope & Boundaries).
**Resolution trigger:** First real shared-library user asks for multi-central support. Until then, `repos.yaml` schema design should leave the door open (treat `central_repo` as a scalar in v1 but reserve the option to widen to a list additively, not as a breaking change).

### ~~Decision: additionalContext format for Stop vs UserPromptSubmit hooks~~ — RESOLVED
Resolved by [Slice 002-03](specs/002-memory-layer/spec.md) — `{ "continue": true, "additionalContext": "..." }` format confirmed in production via `jig-memory-scan` + `jig-task-capture` hooks.

### ~~Decision: AI-first onboarding doc separate from CLAUDE.md~~ — RESOLVED 2026-05-18
Resolved by [Spec 025-01](specs/025-claude-md-hygiene/spec.md) — onboarding content preserved in CLAUDE.md; no separate `docs/AI-ONBOARDING.md` needed.

## Conventions

### Decision: Skill telemetry granularity
**Deferred:** `jig-telemetry.sh` logs Task tool spawns as a proxy for skill invocations. This is imprecise — skills can trigger without spawning a Task.
**Resolution trigger:** After two weeks of telemetry data. If the log is too sparse to be useful, explore the `SubagentStart` / `InstructionsLoaded` events as alternatives.

### ~~Decision: `adr.py index` sentence-end detector mishandles abbreviations~~ — RESOLVED 2026-05-15
Resolved by abbreviation allowlist in `_extract_description` (`skills/adr-workflow/adr.py`); pinned by `ExtractDescriptionAbbreviationTests`. Lifecycle companion: [ADR-0006](decisions/adr-0006-adr-accept-then-index-ordering.md).

### ~~Decision: `adr.py` accept-then-index vs. index-then-accept ordering~~ — RESOLVED 2026-05-15
Resolved by [ADR-0006](decisions/adr-0006-adr-accept-then-index-ordering.md).

### Decision: Sub-slice topology and naming
**Deferred:** Real-world projects routinely discover mid-flight that a Ready slice is too big and needs splitting — usually triggered by an ADR. The aso-shallow-validator hit this on slice-18, which decomposed into 18.1–18.5 (skeleton → corpus-AEMCS → corpus-EDS → synthetic-battery → promotion). jig's current helpers (`workflow.py`, `land.py`, `review.py`) assume flat slice IDs and have no concept of a parent-slice / sub-slice relationship.
**Resolution trigger:** Spec 008 (`--migrate`) needs to handle the validator's sub-slice files, OR the first time a jig user reports needing to split a slice after marking it Ready. Tentatively tracked as [Slice 008-04](specs/008-migrate-existing-project/spec.md#slice-008-04--slice-to-spec-mapping) (sub-slice topology must be decided before slice-to-spec mapping can work mechanically). If sub-slicing is needed before 008-04 is picked up, spin a dedicated slice.
**Open questions:**
- Naming: `slice-18.1-...` (validator style) or `slice-018-01-...` (matching the spec/slice number scheme used elsewhere in jig)?
- Should sub-slices live in the same dir as the parent, or under a `slice-18/` subdir?
- Does the parent slice stay open as an index, or close when all children are Done?
- How does `land.py prepare` aggregate sub-slice readiness — all children Done, or each child landed independently?

### Decision: Memory-recall verification (claims-from-memory linter)
**Deferred:** Surfaced by the 2026-05-18 AI-native review of jig. The user-global CLAUDE.md has a "Before recommending from memory, verify" stanza, but enforcement is convention-only. When the agent says "spec NNN has slice X" or "function Y exists at file Z", no tool fact-checks the claim before action. The reviewer subagent catches some of this at the slice boundary, but mid-session hallucinations against the memory layer remain unflagged.
**Resolution trigger:** First observable mid-session hallucination where the agent acted on a stale memory claim AND the resulting bug survived past reconciliation (i.e., the reviewer didn't catch it). Until that happens, the convention-only stance is upheld manually. ALSO: revisit if/when spec 025-02 (the deferred `workflow.py audit-claude-md` helper) ships — it covers the doc-to-reality direction; this entry covers the agent-claim-to-reality direction.
**Open questions:**
- Where would the linter live (hook? helper? skill?)?
- Surface as same-turn warning vs end-of-session report?
- Granularity: spec/slice references only, or also file paths and symbol names?
**Mitigation idea:** The cheapest first cut would be a `Stop`-hook regex that flags assistant messages claiming `spec NNN` / `slice NNN-NN` / `ADR-NNNN` and cross-checks against the on-disk inventory. Surface as `additionalContext` next turn.

### Decision: JS/TS threshold calibration with real adopter data
**Deferred:** Slice 043-03 extended `quality.py` to recognize vitest + jest test diffs (path classifier, test-block counting, `expect()`/`assert.X()`/`chai.expect()` assertions, `vi.*` / `jest.*` mocks). The threshold constants (`THR_PER_FILE_FLOOD_MAX=100`, `THR_PER_CODE_FILE_FLOOD=50`, `THR_ASSERTION_THIN=1.0`, `THR_MOCK_HEAVY=5.0`) were calibrated by slice 043-02 against a Python-only corpus. JS/TS diffs have different natural distributions (e.g. `it.each` table forms often yield higher per-file test counts than Python `@parametrize`; vitest's `expect(...).toBe(...).not.toBe(...)` chained assertions may inflate or deflate assertion-density depending on counting rules). Until we have a real JS/TS adopter sample, the thresholds are best-guess polyglot defaults — accurate signal firing is unverified for non-Python languages.
**Resolution trigger:** First adopter project with ≥10 reconciled JS/TS slices produces an assertion-thin / mock-heavy / per-file-flood signal that disagrees with reviewer judgment. Re-run a 25-commit-style calibration spike (mirror 043-02's shape) against that adopter's diff corpus and tune the constants — or, if the distribution diverges materially, split per-language threshold tables.
**Related limitation:** `count_each_cases` handles the array-of-arrays form of `it.each([[1,2],[3,4]])` but treats the template-literal tagged form (`` it.each`a | b\n1 | 2` ``) as a single block. A future refinement could count rows in the template literal — out of scope for 043-03 since it's a minority idiom in vitest/jest projects.

### Decision: quality.py schema-version handling in review.py
**Deferred:** Surfaced by `/jig:clarify` on `docs/specs/043-test-quality-wiring/spec.md` Q4 (Non-functional Requirements). quality.py's YAML carries `schema-version: 1`. Slice 043-04's prompt builder ignores the field and embeds the YAML as-is. When a future change bumps the schema (e.g., adds a new signal), the builder will silently embed an unfamiliar shape — reviewers may misinterpret or quietly skip new fields. Pinning to v1 with a "snapshot version mismatch" path would force a coordinated upgrade but adds plumbing the v1-only world doesn't need yet.
**Resolution trigger:** First PR that bumps quality.py's `SCHEMA_VERSION` constant. Whoever lands the schema change updates `_test_quality_snapshot_block()` in `skills/independent-review/review.py` in the same change-set — either to accept the new shape, or to grow a version-aware branch.
**Risk:** Currently theoretical — schema v1 is the only version and there's no in-flight proposal to evolve it.

## Operations

### ~~Decision: scaffold-stable ADR trigger~~ — RESOLVED 2026-05-12
Resolved by [ADR-0001](decisions/adr-0001-scaffold-stable.md) — threshold is 3 reconciled slices; flip mechanism stays manual.

### ~~Decision: Scaffold.json manifest format~~ — RESOLVED 2026-05-18
Resolved by [Spec 001-01](specs/001-scaffold-init/spec.md) + [ADR-0007](decisions/adr-0007-scaffold-json-installed-skills.md); schema lives in `skills/scaffold-init/scaffold.py`.

### Decision: `jig update` managed-file reconciliation
**Deferred:** Slice 033-04 records manifest-only metadata for scaffolded managed files and refuses `--force` re-runs when a managed file's content hash differs from `scaffold.json`. That gives future tooling enough evidence to detect untouched vs. edited output, but there is still no `jig update` command that can diff a newer jig template/runtime against a user's scaffolded copy and offer merge choices.
**Resolution trigger:** First user asks to update an already-scaffolded project to a newer jig version/template set, OR before a non-Claude adapter depends on update semantics for safe repeated scaffolds.
**Likely shape:** Read `scaffold.json.managed_files.files`, recompute current hashes, regenerate candidate output in a temp tree, and offer per-file actions: replace untouched managed files, show diff for edited files, skip user-owned changes, or write a conflict report.

### Decision: Signal detection time-box and resource bounds
**Deferred:** Spike 001a calls for a 3-second wall-clock time-box and "no recursion deeper than 2 levels" with skip-dirs. The current `detect_signals()` honors the depth/skip-dir rule implicitly (no rglob in detectors) but does NOT enforce a wall-clock limit. `_read_text_safe()` reads files unboundedly — a multi-GB `requirements.txt` would be fully read into memory.
**Resolution trigger:** First time a user reports a slow or hung scaffold-init on a real project, OR when adding network-touching detectors.
**Risk:** Currently theoretical — local-only scaffolder on user-owned dirs.

### Decision: jig-memory-scan + jig-task-capture firing-rate measurement
**Deferred:** Slice 002-03 tuned the heuristics deterministically (strip code blocks / URLs / absolute paths; common-acronym skiplist) but did not measure actual firing rate against real session traffic. AC #5 calls for 10–40% as the healthy band; we have no telemetry yet.
**Status as of 2026-05-18:** Original 2-week trigger window has elapsed without anyone reporting hook-firing noise or unknown-reference spam. Treating as "never bites in practice" without formally resolving — re-open if (a) a session reports excessive firing, OR (b) a contributor decides to implement the `.claude/hook-firing.jsonl` mitigation to actually measure.
**Resolution trigger (revised):** First user-reported noise complaint OR explicit ask for telemetry. Default treatment: no action.
**Mitigation idea:** add a `.claude/hook-firing.jsonl` write at the bottom of each hook (one line per fire) — cheap, gitignored, easy to grep.
**Watch-list (reviewer-flagged low-priority items):**
- Schemeless URLs like `example.com/FooBar` leak `FooBar` (the strip regex requires `http(s)://`)
- Nested triple-backtick fences leak the middle content (non-greedy `.*?` pairs outermost)
- `CSS` in COMMON skiplist could mask a frontend project's `CSS Modules` term — harmless today (single capitalized word doesn't match camelCase regex) but worth watching as the skiplist grows

### ~~Decision: Transactional writes in scaffold()~~ — RESOLVED 2026-05-20
Resolved by [Slice 032-02](specs/032-atomic-writes/slice-02-scaffold-completion-marker.md) — `scaffold.json` is now the LAST file written by `scaffold()`, making it the completion sentinel. A crash before that write leaves no `scaffold.json`, so a re-run without `--force` correctly resumes (a small `_is_jig_partial_state` watermark gate skips `_looks_already_spec_driven` when CLAUDE.md carries jig's watermark — see deviation log §3–§4).

### ~~Decision: Atomic writes across all helper scripts~~ — RESOLVED 2026-05-20
Resolved by [Slice 032-01](specs/032-atomic-writes/slice-01-atomic-write-helper.md) — `atomic_write_text` shipped at `skills/_common/atomic_io.py`; 16 callsites swept across 6 helpers (`scaffold.py`, `workflow.py`, `memory.py`, `adr.py`, `land.py`; `review.py` audit-clean); regression-guard test in `_common/test_atomic_io_sweep.py` keeps the surface honest.

### Decision: `AGENTS.md` as a sibling to `CLAUDE.md` from scaffold-init
**Status:** Tracked by [Spec 033](specs/033-host-adapter-portability/spec.md). The direct Codex-support ask fired the original trigger, and [slice 033-02](specs/033-host-adapter-portability/slice-02-agents-md-canonical-primer.md) makes `AGENTS.md` the canonical scaffolded primer while `CLAUDE.md` becomes the Claude adapter. [Slice 033-05](specs/033-host-adapter-portability/slice-05-codex-scaffold-adapter.md) implements Codex scaffold mode; Codex plugin packaging remains deferred to 033-06.
**Deferred:** mysticat-architecture treats `AGENTS.md` as the universal AI-entry-point (recognized by Claude Code, Codex, Cursor, Gemini CLI) and `CLAUDE.md` as the Claude-specific adapter that `@import`s it. jig's vision says "scaffolds AI-native development practices into new projects" — not "Claude-native" — so emitting both files from `scaffold-init` (a slim `AGENTS.md` with 4 sections: project summary / key docs / conventions / session workflow; the existing `CLAUDE.md` template imports it for the Claude-specific bits) would unlock non-Claude users without changing any plugin behavior. The cost is ~50 lines of new template content; the underlying jig tooling (hooks, subagents, `${CLAUDE_PLUGIN_ROOT}` paths, auto-trigger descriptions) stays Claude-only regardless, so the cohesion is partial.
**Resolution trigger:** Fired by a direct Codex-support ask on 2026-05-27. Execution now follows Spec 033: first document the support matrix and adapter contract, then add the canonical `AGENTS.md` primer and renderer boundary before implementing Codex scaffold mode.
**Answered by slice 033-02:** `scaffold-init` emits both files unconditionally for Claude scaffold mode. `AGENTS.md` carries the hot cache and host-neutral primer content; `CLAUDE.md` uses `@AGENTS.md` plus Claude-specific adapter notes so there is no second source of truth.
**Comparison source:** See conversation 2026-05-15 (mysticat-architecture vs jig comparison) for the pattern's full context. This was item #4 in the "what to adopt from mysticat" set; items #1–#3 became spec 014.

### Decision: host-aware migrate machinery in Codex scaffold mode
**Deferred:** Slice 033-05 materializes the `migrate` skill into Codex so `report`, `rename-decisions`, and `split-slices` can run from the `.codex/skills/jig-migrate/` helper path. The existing `copy-machinery` operation still delegates to Claude scaffold machinery and writes `.claude/` files, and `rename-decisions` still scans the helper's Claude-shaped cross-reference scope (`docs/`, `CLAUDE.md`, `.claude/`). The Codex scaffold renderer therefore keeps that generated skill prose honest instead of promising `.codex/` parity for those legacy migrate paths.
**Resolution trigger:** First Codex user needs `migrate copy-machinery`, first Codex user expects `rename-decisions` to rewrite `AGENTS.md` / `.codex/`, or before any future slice claims migrate parity across hosts.
**Mitigation idea:** Make `migrate.py` host-aware (`--host claude|codex`) and route machinery copy, primer names, hook config paths, and cross-reference scan roots through the same renderer boundary used by `scaffold-init`.

### Decision: `workflow.py new --from-branch` to migrate already-drafted feature branches into a reservation
**Deferred:** Today `workflow.py new <slug>` only works as a clean-room reservation from `main`. If a user already drafted slice content on a feature branch (the common case before adopting `new`), there's no path to retroactively reserve the number on origin/main while keeping the drafted body. Surfaced as a "likely candidate" in slice 003-03's DoD.
**Resolution trigger:** First user request to retroactively reserve a number for an already-drafted branch, OR a second slice in jig itself starts life as a draft-first branch and hits the renumber friction.
**Mitigation idea:** `--from-branch <branch>` reads the slug + draft from the named branch, opens main, runs the standard reservation flow with the next-free number, then rebases/cherry-picks the branch's content onto the reservation commit.

### Decision: `workflow.py unreserve <NNN>` for abandoned reservations
**Deferred:** A reservation that's never drafted leaves a permanent stub `docs/specs/NNN-<slug>/spec.md` on main. No tooling exists to cleanly retract a reservation. Surfaced as a "likely candidate" in slice 003-03's DoD.
**Resolution trigger:** First abandoned reservation in the wild (≥30 days at DRAFT with zero slices and no activity), OR a user explicitly asks how to un-reserve.
**Mitigation idea:** `unreserve <NNN-slug>` removes the spec directory + commits `docs(specs): unreserve NNN-<slug>` on main with the same push/PR-fallback flow `new` uses. Refuse if the spec has any slices defined or any commits referencing it.

### Decision: post-stub-create / pre-local-commit race window in `workflow.py new`
**Deferred:** `workflow.py new` fetches origin/main, computes `next_number`, creates the stub directory + spec.md, THEN commits. Between mkdir and commit, another reservation could land on origin (caught by `git push`'s non-fast-forward later). The race detection fires correctly at push time, but a small window of stranded-on-disk state exists between `mkdir` and `git commit`. Surfaced as a "likely candidate" in slice 003-03's DoD.
**Resolution trigger:** First user-observable race-on-disk incident (e.g., two operators report seeing a "dirty worktree" error from a `new` that didn't run cleanly). Probably never bites in practice (window is sub-second).
**Mitigation idea:** stash-or-revert the stub-create on push failure (already done in the `non-fast-forward` path). Generalize the cleanup to fire on any push-failure shape, not just race.

### ~~Decision: race-recovery `git reset --hard HEAD~1` leaves empty spec directory on disk~~ — RESOLVED 2026-05-15
Resolved by `shutil.rmtree(spec_dir, ignore_errors=True)` in `workflow.py` race-recovery path; pinned by `test_new_race_recovery_removes_empty_spec_dir`.

### Decision: `workflow.py new` / `adr.py new` refuse on non-main branches, defeating reserve-on-main when work originates on a feature branch
**Deferred:** `workflow.py new` requires the current branch to be `main` because the reservation commit lands on `main`. Caused the spec 021→022 collision-and-renumber on 2026-05-15: a feature-branch session refused to reserve spec 021 up-front ("must switch to main first"), the session continued without reservation, parallel work landed `021-migrate-copy-machinery` on origin/main in the meantime, the feature branch had to rename `docs/specs/021-contracts/ → 022-contracts/` (+ propagate the renumber across slice files, deviation logs, CLAUDE.md, ADR-0005, dogfood report, test labels) at merge-time. The very pain spec 003-03's reserve-on-main flow was built to prevent reproduced because the flow wasn't usable from where work was happening. **Slice 028-01 (2026-05-19) extended the same preflight to `adr.py new`**, so the gap is now symmetric across both reserve-on-main helpers — a future fix should land in both at once.
**Resolution trigger:** Next time a multi-worktree session has to renumber a spec dir on merge, OR a user-reported "I tried to reserve but workflow.py refused" pain.
**Open questions:**
- Loosen the branch check to allow reservation from a feature branch by (a) doing the commit in a temporary `git worktree add` of main, (b) auto-fast-forwarding the current branch's pointer to origin/main first, then committing on main and merging back into the feature branch, or (c) push-only-no-local-commit (use `git push origin HEAD:refs/heads/main-reservation-<NNN-slug>` then ask origin to fast-forward main when ready).
- (a) is cleanest semantically (cwd never leaves the feature branch's working tree) but adds a temp-worktree dependency to the helper.
- (b) is the smallest code change but moves the feature branch's tip silently, which surprises if the user wasn't ready to FF.
- Should the relaxed flow stay opt-in (`--from-feature-branch`) or default?
**Mitigation idea (interim):** SKILL.md gains a "if you're on a feature branch and can't switch to main, manually `mkdir docs/specs/NNN-<slug>/` and `touch spec.md` so subsequent helpers see the dir; reserve-on-main when you can" workaround — acknowledges the gap without changing the helper.

### ~~Decision: scaffold-mode `--with-machinery` doesn't copy `skills/_common/`, breaking scaffolded helpers~~ — RESOLVED 2026-05-20
Resolved by extending `_copy_skills_and_agents` in `skills/scaffold-init/scaffold.py` to copy `_`-prefixed private shared dirs unprefixed (e.g. `_common/` → `.claude/skills/_common/`); helpers' `sys.path.insert(0, parent.parent)` resolves `from _common.parsing import ...` at scaffold-mode runtime. Pinned by `test_common_module_copied_unprefixed` + `test_scaffolded_helper_imports_common_at_runtime`.

### Decision: Skill-routing observability
**Deferred:** Surfaced by the 2026-05-18 AI-native review of jig. Jig now ships 13 active skills (`scaffold-init`, `memory-sync`, `spec-workflow`, `independent-review`, `contracts`, `adr-workflow`, `tdd-loop`, `slice-land`, `migrate`, `pr-review`, `arch-review`, `clarify`, `analyze`). The Claude Code skill router picks one per user intent — but jig has no telemetry on which skills fire when, whether the router picks the *right* skill, or whether the deferral hints (pr-review/arch-review/contracts route to richer user-installed skills) actually fire. `jig-telemetry.sh` logs `Task` tool spawns; it does not log Skill / slash-command invocations.
**Resolution trigger:** First observable routing mismatch (user invokes intent X, wrong skill fires) that surfaces in a deviation log or post-mortem. ALSO: revisit if/when a new judgment-skill (eighth+) ships and the routing surface grows further. Probably not bites in practice today — the 13 skills are well-differentiated by description — but the lack of observability means we can't tell.
**Open questions:**
- Extend `jig-telemetry.sh` to log Skill events as well as Task events? (Requires the Skill event being routable to a hook, which may not be supported by the Claude Code hook surface — verify before specifying.)
- Or: add a `workflow.py routing-stats` subcommand that reads `.claude/skill-usage.jsonl` and surfaces the routing histogram?
- Or: defer entirely to a future `SubagentStart` event (per the existing SubagentStart deferred entry above)?
**Mitigation idea:** Cheapest first cut: extend `jig-telemetry.sh` to also fire on `UserPromptSubmit` and log the prompt prefix + detected slash command — gives a coarse "what skills did this session try to invoke" record. Pair with a manual review pass after 2 weeks (same cadence as the existing "Skill telemetry granularity" entry).
