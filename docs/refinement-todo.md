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

### Decision: additionalContext format for Stop vs UserPromptSubmit hooks
**Deferred:** Confirmed `{ "continue": true, "additionalContext": "..." }` for these events, but the plan review flagged this as needing empirical verification.
**Resolution trigger:** Slice 002-03 (auto-detect-hooks) — test both hooks against real sessions.

### ~~Decision: AI-first onboarding doc separate from CLAUDE.md~~ — RESOLVED 2026-05-18
~~**Deferred:** Today CLAUDE.md is doing double duty — both the high-frequency hot cache AND the de facto "how to operate this repo as an agent" onboarding doc. Spec 025 slims the hot cache; the open question was whether the onboarding content would survive.~~
**Resolved by:** [Spec 025-01](specs/025-claude-md-hygiene/spec.md) landed with the onboarding content **preserved in CLAUDE.md**: the "Skills in this repo" table, the "Session workflow" section, and the "Constraints for agents working on this repo" stanza all survived the slim (the table got slimmed per-row but the section stayed; the workflow + constraints sections were untouched). The slimming hit Active-specs + Sprint-focus + ADR stanzas instead — content that wasn't serving as onboarding. **No separate `docs/AI-ONBOARDING.md` needed.** If a future audit re-raises this (e.g., the Constraints section grows past ~10 bullets, or a contributor reports CLAUDE.md as confusing for "how do I author skills" vs "what's in flight"), spin a new spec at that point.

## Conventions

### Decision: Skill telemetry granularity
**Deferred:** `jig-telemetry.sh` logs Task tool spawns as a proxy for skill invocations. This is imprecise — skills can trigger without spawning a Task.
**Resolution trigger:** After two weeks of telemetry data. If the log is too sparse to be useful, explore the `SubagentStart` / `InstructionsLoaded` events as alternatives.

### ~~Decision: `adr.py index` sentence-end detector mishandles abbreviations~~ — RESOLVED 2026-05-15
~~**Deferred:** The index-description extractor in `adr.py` truncates the first Context paragraph at the first sentence-ending punctuation. It treats the period in `e.g.` / `i.e.` / `cf.` / etc. as a sentence boundary, producing index lines like `... files as NNNN-<slug>.md (e.g.` — cut mid-abbreviation. First hit while writing ADR-0004 (2026-05-12).~~
**Resolved by:** extending `_extract_description` in `adr.py` with an explicit abbreviation allowlist (`e.g.`, `i.e.`, `etc.`, `cf.`, `vs.`, `viz.`, `al.`, `Mr.`, `Mrs.`, `Ms.`, `Dr.`, `Prof.`, `Sr.`, `Jr.`, `St.`). The new `_is_abbreviation_ending_at(text, period_index)` helper does a case-sensitive look-back at each candidate period and refuses to truncate when one of these endings matches (with a `before_idx < 0 or not isalpha()` boundary check so `mile.` doesn't accidentally match `le.`). 7 new `ExtractDescriptionAbbreviationTests` lock the behavior. Companion ADR: [ADR-0006](decisions/adr-0006-adr-accept-then-index-ordering.md) codifies the lifecycle.

### ~~Decision: `adr.py` accept-then-index vs. index-then-accept ordering~~ — RESOLVED 2026-05-15
~~**Deferred:** The `adr-workflow` SKILL.md's end-to-end example runs `accept` → `index`, but the gotchas section says the fix for a truncated index entry is to edit the ADR's first Context sentence and re-run `adr.py index` — which implicitly requires the ADR to still be editable, i.e. NOT yet accepted. The two pieces of guidance conflict. Hit when accepting ADR-0004 (2026-05-12); the truncated description was only visible *after* `index`, which ran *after* `accept`, putting the ADR in an immutable state with an ugly index entry. Worked around by treating Context cosmetic edits as not-decision-content (and thus not under the immutability rule).~~
**Resolution trigger:** Spec deciding the canonical lifecycle, OR next time someone hits the same conflict.
**Open questions:**
- Is the canonical order `new` → edit → `index` (preview) → `accept` → `index` (final)?
- Or do we make `accept` automatically run `index` so the two are atomic?
- Does the immutability rule apply to every character, or only the Recommended Decision / Consequences sections?
**Resolved by:** [ADR-0006: adr.py accept-then-index ordering](decisions/adr-0006-adr-accept-then-index-ordering.md).

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

## Operations

### ~~Decision: scaffold-stable ADR trigger~~ — RESOLVED 2026-05-12
~~**Deferred:** The mechanism to flip docs from `Draft` to `Stable` (after 3-5 reconciled specs) is described but not implemented.~~
**Resolved by:** [ADR-0001: scaffold-stable trigger](adrs/adr-0001-scaffold-stable.md). Threshold is **3 reconciled slices**; flip mechanism remains manual for now (one-liner sed; a `stabilize.py` helper is a candidate for a future slice if needed).

### ~~Decision: Scaffold.json manifest format~~ — RESOLVED 2026-05-18
~~**Deferred:** The `scaffold.json` install-state manifest is referenced in the design but its schema is undefined.~~
**Resolved by:** Slice 001-01 (greenfield-scaffold) defined the initial schema (fields: `schema_version`, `installed_skills`, `scaffold_mode`, plus signal-detection results). [ADR-0007](decisions/adr-0007-scaffold-json-installed-skills.md) formalized the `installed_skills` field shape. Schema lives in `skills/scaffold-init/scaffold.py` (`JIG_VERSION` constant + manifest construction in the main flow); `_TIER_SKILLS` is the per-tier source of truth.

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

### Decision: Transactional writes in scaffold()
**Deferred:** `scaffold()` writes CLAUDE.md, docs/*, scaffold.json, brief.md sequentially without a transaction. A crash between steps leaves partial state; the next run (without `--force`) refuses because some files exist. Currently we rely on the `scaffold.json`-present check as the "scaffolded" sentinel; if creation crashes before scaffold.json is written, a re-run succeeds but may overwrite partial files.
**Resolution trigger:** First report of a partial-scaffold state in the wild.
**Mitigation idea:** write everything to a temp dir, then atomically rename, OR write `scaffold.json` FIRST as an in-progress marker and finalize at the end.

### Decision: Atomic writes across all helper scripts
**Deferred:** `workflow.py transition` and `workflow.py status-board` use `Path.write_text()` directly, like `scaffold.py` and `memory.py`. None are crash-safe — an interrupted run can leave a half-written spec.md or README.md. Probability is low (single-call CLIs that complete in milliseconds) but the impact is "lose state."
**Resolution trigger:** First report of a torn-write incident, OR before jig ships outside personal-dev use.
**Mitigation idea:** add a shared `atomic_write_text(path, content)` helper across `scaffold.py`, `memory.py`, `workflow.py`. Write to `<path>.tmp` then `os.replace()` — POSIX-atomic on same-FS rename.

### Decision: `AGENTS.md` as a sibling to `CLAUDE.md` from scaffold-init
**Deferred:** mysticat-architecture treats `AGENTS.md` as the universal AI-entry-point (recognized by Claude Code, Codex, Cursor, Gemini CLI) and `CLAUDE.md` as the Claude-specific adapter that `@import`s it. jig's vision says "scaffolds AI-native development practices into new projects" — not "Claude-native" — so emitting both files from `scaffold-init` (a slim `AGENTS.md` with 4 sections: project summary / key docs / conventions / session workflow; the existing `CLAUDE.md` template imports it for the Claude-specific bits) would unlock non-Claude users without changing any plugin behavior. The cost is ~50 lines of new template content; the underlying jig tooling (hooks, subagents, `${CLAUDE_PLUGIN_ROOT}` paths, auto-trigger descriptions) stays Claude-only regardless, so the cohesion is partial.
**Resolution trigger:** First credible signal of a non-Claude-Code user wanting jig conventions (Codex / Cursor / Gemini / Aider) — either a direct ask, or a comparison evaluation that flags the gap. Until then, the partial cohesion ("AGENTS.md exists but only Claude Code can actually run the helpers") would invite confusion.
**Open questions:**
- Does `AGENTS.md` repeat the CLAUDE.md hot cache, or does CLAUDE.md `@import` AGENTS.md (mysticat's pattern)? The latter is cleaner but assumes `@import` semantics that non-Claude tools may not respect.
- Should `scaffold-init` emit both unconditionally, or behind a `--multi-agent` flag?
**Comparison source:** See conversation 2026-05-15 (mysticat-architecture vs jig comparison) for the pattern's full context. This was item #4 in the "what to adopt from mysticat" set; items #1–#3 became spec 014.

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
~~**Deferred:** On `non-fast-forward` push rejection, the helper resets the commit but leaves the empty `docs/specs/NNN-<slug>/` directory. Functionally harmless (`_next_spec_number` still works) but untidy. Surfaced by the reviewer of slice 003-03 (workflow.py:1028-1035 region).~~
**Resolved by:** the proposed `shutil.rmtree(spec_dir, ignore_errors=True)` after the `git reset --hard HEAD~1` call. Pinned by `test_new_race_recovery_removes_empty_spec_dir` in `ReserveSpecTests` (mocks the reset so the test still detects whether the helper itself cleans up the dir).

### Decision: `workflow.py new` / `adr.py new` refuse on non-main branches, defeating reserve-on-main when work originates on a feature branch
**Deferred:** `workflow.py new` requires the current branch to be `main` because the reservation commit lands on `main`. Caused the spec 021→022 collision-and-renumber on 2026-05-15: a feature-branch session refused to reserve spec 021 up-front ("must switch to main first"), the session continued without reservation, parallel work landed `021-migrate-copy-machinery` on origin/main in the meantime, the feature branch had to rename `docs/specs/021-contracts/ → 022-contracts/` (+ propagate the renumber across slice files, deviation logs, CLAUDE.md, ADR-0005, dogfood report, test labels) at merge-time. The very pain spec 003-03's reserve-on-main flow was built to prevent reproduced because the flow wasn't usable from where work was happening. **Slice 028-01 (2026-05-19) extended the same preflight to `adr.py new`**, so the gap is now symmetric across both reserve-on-main helpers — a future fix should land in both at once.
**Resolution trigger:** Next time a multi-worktree session has to renumber a spec dir on merge, OR a user-reported "I tried to reserve but workflow.py refused" pain.
**Open questions:**
- Loosen the branch check to allow reservation from a feature branch by (a) doing the commit in a temporary `git worktree add` of main, (b) auto-fast-forwarding the current branch's pointer to origin/main first, then committing on main and merging back into the feature branch, or (c) push-only-no-local-commit (use `git push origin HEAD:refs/heads/main-reservation-<NNN-slug>` then ask origin to fast-forward main when ready).
- (a) is cleanest semantically (cwd never leaves the feature branch's working tree) but adds a temp-worktree dependency to the helper.
- (b) is the smallest code change but moves the feature branch's tip silently, which surprises if the user wasn't ready to FF.
- Should the relaxed flow stay opt-in (`--from-feature-branch`) or default?
**Mitigation idea (interim):** SKILL.md gains a "if you're on a feature branch and can't switch to main, manually `mkdir docs/specs/NNN-<slug>/` and `touch spec.md` so subsequent helpers see the dir; reserve-on-main when you can" workaround — acknowledges the gap without changing the helper.

### Decision: scaffold-mode `--with-machinery` doesn't copy `skills/_common/`, breaking scaffolded helpers
**Deferred:** `scaffold-init --with-machinery` (default-on per slice 016-03) copies `skills/<name>/` directories into the target's `.claude/skills/jig-<name>/` but does NOT copy `skills/_common/` (the shared parsing / iter-slices module imported by `workflow.py`, `review.py`, `land.py`, etc.). When the target's scaffolded `workflow.py status-board .` runs, it fails with `ModuleNotFoundError: No module named '_common'`. Surfaced 2026-05-15 when regenerating aso-shallow-validator's status board from its scaffolded jig install (had to fall back to invoking jig's source-repo `workflow.py` with the project as an arg). Affects every Python helper that imports from `_common`.
**Resolution trigger:** Next user reports a scaffolded helper failing with `ModuleNotFoundError`, OR a scaffolded project tries to run any of `workflow.py {transition,status-board,new}` / `review.py {implementation,reconciliation}` / `land.py {prepare,execute}` and hits the import error. Probably bites immediately for any scaffolded project that tries to use its own bundled helpers.
**Open questions:**
- Copy `skills/_common/` to `.claude/skills/jig-_common/` (jig-prefixed for consistency)? Then the helpers need their `from _common.parsing import ...` rewritten to `from jig_common.parsing import ...` at copy time (path-rewriter extension to `_rewrite_python_imports` or equivalent).
- Or copy unprefixed as `.claude/skills/_common/`? Cleaner from the helper's perspective (no import rewrite needed) but breaks the `jig-<name>/` naming convention from slice 016-01.
- Or vendor `_common/` inside each `.claude/skills/jig-<name>/_common/` (per-skill copy)? Highest disk cost, simplest import semantics.
**Mitigation idea:** spec 016-04 (`update-skill`, currently DRAFT) is the natural home for this fix — it'd ship as part of the same "scaffold-mode parity tightening" arc that 016-01/02/03 began. Until then, scaffolded projects that need to run jig helpers should invoke jig's source-repo `workflow.py` / `review.py` / etc. with `--project-dir <target>` (where the helper supports it) or by path argument.

### Decision: Skill-routing observability
**Deferred:** Surfaced by the 2026-05-18 AI-native review of jig. Jig now ships 13 active skills (`scaffold-init`, `memory-sync`, `spec-workflow`, `independent-review`, `contracts`, `adr-workflow`, `tdd-loop`, `slice-land`, `migrate`, `pr-review`, `arch-review`, `clarify`, `analyze`). The Claude Code skill router picks one per user intent — but jig has no telemetry on which skills fire when, whether the router picks the *right* skill, or whether the deferral hints (pr-review/arch-review/contracts route to richer user-installed skills) actually fire. `jig-telemetry.sh` logs `Task` tool spawns; it does not log Skill / slash-command invocations.
**Resolution trigger:** First observable routing mismatch (user invokes intent X, wrong skill fires) that surfaces in a deviation log or post-mortem. ALSO: revisit if/when a new judgment-skill (eighth+) ships and the routing surface grows further. Probably not bites in practice today — the 13 skills are well-differentiated by description — but the lack of observability means we can't tell.
**Open questions:**
- Extend `jig-telemetry.sh` to log Skill events as well as Task events? (Requires the Skill event being routable to a hook, which may not be supported by the Claude Code hook surface — verify before specifying.)
- Or: add a `workflow.py routing-stats` subcommand that reads `.claude/skill-usage.jsonl` and surfaces the routing histogram?
- Or: defer entirely to a future `SubagentStart` event (per the existing SubagentStart deferred entry above)?
**Mitigation idea:** Cheapest first cut: extend `jig-telemetry.sh` to also fire on `UserPromptSubmit` and log the prompt prefix + detected slash command — gives a coarse "what skills did this session try to invoke" record. Pair with a manual review pass after 2 weeks (same cadence as the existing "Skill telemetry granularity" entry).
