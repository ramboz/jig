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

## Conventions

### Decision: Skill telemetry granularity
**Deferred:** `jig-telemetry.sh` logs Task tool spawns as a proxy for skill invocations. This is imprecise — skills can trigger without spawning a Task.
**Resolution trigger:** After two weeks of telemetry data. If the log is too sparse to be useful, explore the `SubagentStart` / `InstructionsLoaded` events as alternatives.

### Decision: `adr.py index` sentence-end detector mishandles abbreviations
**Deferred:** The index-description extractor in `adr.py` truncates the first Context paragraph at the first sentence-ending punctuation. It treats the period in `e.g.` / `i.e.` / `cf.` / etc. as a sentence boundary, producing index lines like `... files as NNNN-<slug>.md (e.g.` — cut mid-abbreviation. First hit while writing ADR-0004 (2026-05-12).
**Resolution trigger:** Next time the bug bites (i.e. an ADR's Context paragraph contains an abbreviation in the first sentence). Workaround documented in the SKILL.md gotchas: rewrite the first sentence to be index-friendly and re-run `adr.py index`.
**Mitigation idea:** extend the sentence-end detector to skip common abbreviations (`e.g.`, `i.e.`, `etc.`, `cf.`, `vs.`, `Mr.`, `Dr.`) — small allowlist, no NLP needed. Or detect "lowercase letter immediately before the period" as a not-end-of-sentence signal.

### Decision: `adr.py` accept-then-index vs. index-then-accept ordering
**Deferred:** The `adr-workflow` SKILL.md's end-to-end example runs `accept` → `index`, but the gotchas section says the fix for a truncated index entry is to edit the ADR's first Context sentence and re-run `adr.py index` — which implicitly requires the ADR to still be editable, i.e. NOT yet accepted. The two pieces of guidance conflict. Hit when accepting ADR-0004 (2026-05-12); the truncated description was only visible *after* `index`, which ran *after* `accept`, putting the ADR in an immutable state with an ugly index entry. Worked around by treating Context cosmetic edits as not-decision-content (and thus not under the immutability rule).
**Resolution trigger:** Spec deciding the canonical lifecycle, OR next time someone hits the same conflict.
**Open questions:**
- Is the canonical order `new` → edit → `index` (preview) → `accept` → `index` (final)?
- Or do we make `accept` automatically run `index` so the two are atomic?
- Does the immutability rule apply to every character, or only the Recommended Decision / Consequences sections?

### Decision: Sub-slice topology and naming
**Deferred:** Real-world projects routinely discover mid-flight that a Ready slice is too big and needs splitting — usually triggered by an ADR. The aso-shallow-validator hit this on slice-18, which decomposed into 18.1–18.5 (skeleton → corpus-AEMCS → corpus-EDS → synthetic-battery → promotion). jig's current helpers (`workflow.py`, `land.py`, `review.py`) assume flat slice IDs and have no concept of a parent-slice / sub-slice relationship.
**Resolution trigger:** Spec 008 (`--migrate`) needs to handle the validator's sub-slice files, OR the first time a jig user reports needing to split a slice after marking it Ready. Tentatively tracked as [Slice 008-04](specs/008-migrate-existing-project/spec.md#slice-008-04--slice-to-spec-mapping) (sub-slice topology must be decided before slice-to-spec mapping can work mechanically). If sub-slicing is needed before 008-04 is picked up, spin a dedicated slice.
**Open questions:**
- Naming: `slice-18.1-...` (validator style) or `slice-018-01-...` (matching the spec/slice number scheme used elsewhere in jig)?
- Should sub-slices live in the same dir as the parent, or under a `slice-18/` subdir?
- Does the parent slice stay open as an index, or close when all children are Done?
- How does `land.py prepare` aggregate sub-slice readiness — all children Done, or each child landed independently?

## Operations

### ~~Decision: scaffold-stable ADR trigger~~ — RESOLVED 2026-05-12
~~**Deferred:** The mechanism to flip docs from `Draft` to `Stable` (after 3-5 reconciled specs) is described but not implemented.~~
**Resolved by:** [ADR-0001: scaffold-stable trigger](adrs/0001-scaffold-stable.md). Threshold is **3 reconciled slices**; flip mechanism remains manual for now (one-liner sed; a `stabilize.py` helper is a candidate for a future slice if needed).

### Decision: Scaffold.json manifest format
**Deferred:** The `scaffold.json` install-state manifest is referenced in the design but its schema is undefined.
**Resolution trigger:** Slice 001-01 (greenfield-scaffold). The implementer defines the schema as the first deliverable.

### Decision: Signal detection time-box and resource bounds
**Deferred:** Spike 001a calls for a 3-second wall-clock time-box and "no recursion deeper than 2 levels" with skip-dirs. The current `detect_signals()` honors the depth/skip-dir rule implicitly (no rglob in detectors) but does NOT enforce a wall-clock limit. `_read_text_safe()` reads files unboundedly — a multi-GB `requirements.txt` would be fully read into memory.
**Resolution trigger:** First time a user reports a slow or hung scaffold-init on a real project, OR when adding network-touching detectors.
**Risk:** Currently theoretical — local-only scaffolder on user-owned dirs.

### Decision: jig-memory-scan + jig-task-capture firing-rate measurement
**Deferred:** Slice 002-03 tuned the heuristics deterministically (strip code blocks / URLs / absolute paths; common-acronym skiplist) but did not measure actual firing rate against real session traffic. AC #5 calls for 10–40% as the healthy band; we have no telemetry yet.
**Resolution trigger:** After ~2 weeks of jig being enabled in a real session, scan the captured stderr/stdout of these hooks (or add a lightweight counter file in `.claude/`) and either confirm we're in band, or tune the COMMON acronym set / regex specificity.
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
