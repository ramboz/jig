---
status: DRAFT
skill: scaffold-init
---

# Spec 001: scaffold-init

## Overview

The `scaffold-init` skill runs a discovery wizard that initializes an AI-native development workspace. It produces the full `docs/` structure, `CLAUDE.md` with Hot Cache section, hook infrastructure, and `scaffold.json` install-state manifest.

## SPIDR Analysis

| Technique | Question | Outcome |
|---|---|---|
| S — Spike | How do we reliably detect LLM/agent work, CI, team size? | Spike 001a (docs/spikes/) — not gated for slice 001-01 |
| P — Path | Greenfield vs. existing repo with signals? | 2 slices (001-01, 001-03) |
| I — Interface | Q&A wizard vs. filesystem-inference only? | Slice 001-05 (last) |
| D — Data | Stub docs vs. content-filled? | Slice 001-02 |
| R — Rules | Draft markers, deferred decision tracking? | Slice 001-04 |

---

## Spike 001a — signal-detection

**STATUS: DRAFT**

Tracking artifact: [docs/spikes/spike-001a-signal-detection.md](../../spikes/spike-001a-signal-detection.md)

This spike is NOT a gate for slice 001-01. Slice 001-01 uses hardcoded defaults.

---

## Slice 001-01 — greenfield-scaffold

**STATUS: DONE**

**Goal:** Happy path wizard — no signal detection, default tier install (Tier 0 + Tier 1), produces complete docs/ skeleton, CLAUDE.md with Hot Cache, hooks.json, and scaffold.json manifest.

**DoR (Definition of Ready):**
- No prior slice dependency.
- spec.md (this file) is STATUS: READY_FOR_IMPLEMENTATION.

**Acceptance Criteria:**
1. Running `/jig:scaffold-init` on an empty directory produces the full expected tree (docs/, CLAUDE.md, .claude/hooks/, scaffold.json).
2. `scaffold.json` is written with: installed tiers, timestamp, jig version.
3. All scaffolded docs carry `Status: Draft (wizard-generated)` marker at the top.
4. `docs/memory/glossary.md`, `learnings.md`, `tooling.md` are seeded with stub content.
5. `docs/inbox.md` is created with a header explaining its purpose.
6. `CLAUDE.md` is generated from `templates/CLAUDE.md.template` and includes a Hot Cache section.
7. After scaffold-init completes, `docs/memory/people.md` is NOT created (solo project detection).
8. Bootstrap note: the spec-gate hook for `docs/conventions.md` activates AFTER scaffold-init. Verify post-completion: editing conventions.md without approval is blocked.

**DoD (Definition of Done):**
- [x] All ACs pass (14 tests, all green)
- [x] Implementer test coverage for the scaffold tree output
- [x] Reviewed by `reviewer` subagent (verdict: needs-changes → all issues resolved)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ Running `/jig:scaffold-init` produces a complete, runnable project structure end-to-end.

### Deviation log (after reconciliation)

The original spec is preserved above. This section records what changed during implementation.

**Reviewer-flagged fixes (all addressed before RECONCILED):**

1. **CLAUDE.md.template leaked a maintainer-only comment** into every scaffolded project. Moved out of the template body. Smoke-tested: head of generated CLAUDE.md is clean.
2. **AC #3 was under-implemented.** Only 4 of 9 generated .md files carried the Status marker. Added markers to glossary, learnings, tooling, inbox, specs/README, adrs/README templates. `test_draft_markers` now walks every `.md` under the scaffolded tree.
3. **Spec-gate hook had a path-traversal weakness.** `foo/docs/conventions.md/../conventions.md` would slip past the suffix check. Fixed via `os.path.realpath` / `os.path.normpath`. Regression test `test_conventions_gate_resists_path_traversal` added.
4. **scaffold.py would silently overwrite existing CLAUDE.md / scaffold.json.** Added `AlreadyScaffoldedError` and refuses unless `--force` is passed; exit code 3. Two tests added.
5. **Unrendered `{{KEY}}` placeholders only emitted a warning.** Now raises `UnrenderedPlaceholderError` and exits non-zero. Test added that injects a bad template and asserts the failure.
6. **`installed_tiers` was duplicated** between `templates/scaffold.json.template` and the `DEFAULT_TIERS` constant in `scaffold.py`. Template now carries an empty array; scaffold.py is the single source of truth.

**Forward-leaning additions noted by reviewer (kept intentionally):**

- `hooks.json` PreToolUse matcher includes `MultiEdit` alongside `Edit|Write`. Plan only mentioned `Edit|Write`. Locks in MultiEdit coverage before it becomes a hole.
- `scaffold.json` includes `scaffold_signals` and `hook_profile` keys not required by AC #2. Forward-compat scaffolding for slice 001-03 (signal detection). All default values are conservative ("false" / "standard").
- AC #1 ("empty directory") is verified by Claude (via SKILL.md instructions) rather than `scaffold.py`. Architectural split: script is dumb, the skill body is the safety layer, and scaffold.py's overwrite-refusal is the second safety layer.

**Real bugs discovered during TDD (not in original review):**

- **All hook scripts using `python3 - <<'EOF'` were broken.** The heredoc overrode stdin, so `json.load(sys.stdin)` got the script source, not the hook event JSON. Fixed by switching to `python3 -c "..."`. This affected all 5 hook scripts, not just the new spec-gate. Captured in `docs/memory/learnings.md`.

**Doc updates from this slice:**

- `docs/memory/learnings.md` extended (one new entry: the `python3 -` stdin bug).
- No `architecture.md` changes required (no new module boundaries).
- No ADR required (no irreversible architectural decisions).

---

## Slice 001-02 — doc-content

**STATUS: DONE**

**Goal:** Scaffolded docs have structured content — not empty files. Deferred-decision stubs, architecture template, conventions template, memory layer stubs.

**DoR:** Slice 001-01 STATUS: DONE.

**Acceptance Criteria:**
1. `architecture.md` has a tech-stack section with `> Deferred — no signal from initial pitch.` stubs for undefined choices.
2. `workflow.md` documents the spec lifecycle states and hook strictness profiles (as deferred).
3. `conventions.md` uses the rule → **Why:** → **How to apply:** format throughout.
4. `refinement-todo.md` lists ≥3 wizard-deferred decisions with resolution triggers.
5. Memory stubs: glossary, learnings, tooling have meaningful starter content (not just headers).
6. `docs/inbox.md` exists with a header explaining its purpose.
7. `CLAUDE.md` Hot Cache section is populated with the project name and empty term/spec lists.
8. `docs/memory/people.md` created ONLY when ≥2 git contributors OR user confirms team context.

**DoD:** Same as 001-01. All checked.
- [x] All ACs pass (22 tests, all green)
- [x] Implementer test coverage (4 new tests + 2 reviewer-driven regressions; 2 existing tests sharpened)
- [x] Reviewed by `reviewer` subagent (verdict: pass with 5 flagged issues — 4 addressed, 1 noted)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ Produces end-to-end output with improved content quality.

### Deviation log (after reconciliation)

The original spec is preserved above. This section records what changed.

**Reviewer-flagged bugs (fixed before RECONCILED):**

1. **`detect_team` walked into parent git repos.** Scaffolding a fresh subdir of a multi-author monorepo would inherit the parent's contributor count and emit `people.md` incorrectly. Fixed by adding `git rev-parse --show-toplevel` check — refuses unless target IS the repo root. Regression test `test_people_md_absent_inside_parent_monorepo` added.
2. **`detect_team` ignored mailmap.** One person with two emails (work/personal) would count as 2 contributors. Fixed via `git log --use-mailmap --format=%aE`. Regression test `test_people_md_solo_with_mailmap_aliases` added.
3. **`test_workflow_has_strictness_section` only checked for any `Deferred` token anywhere in the file.** Tightened to require the marker inside the Hook Strictness section specifically (H2 boundary detection).
4. **`test_memory_stubs` was too loose (length-only).** Tightened to require: title heading, usage/format guidance, and `Status: Draft` marker, with length floor raised from 50/100 → 200.

**Reviewer notes accepted as-is (logged, not changed):**

5. **AC #3 "throughout" interpretation.** Deferred sections (Code style / Testing / Git) use deferred-blockquote markers instead of empty Rule/Why/How skeletons. This matches the pattern established in `architecture.md` (deferred sections use blockquotes, not skeletal rule entries). The 3 concrete rules in conventions.md (Documentation/Specs sections) all use Rule/Why/How. Plan documented this scope explicitly; preserving the convention rather than adding empty skeleton rules.

**Real bug surfaced during implementation:**

- **`re` was missing from imports** when sharpening `test_workflow_has_strictness_section`. Test failed with `NameError`. Fixed by importing `re` at the top of `test_scaffold.py`. Caught by the test run — exactly what tests are for.

**Forward-leaning additions (acknowledged, kept):**

- `scaffold.json.scaffold_signals.is_team` is now populated from `detect_team()` result, not required by AC #2 but useful breadcrumb for slice 001-03 (signal detection).
- Print message of `scaffold.py` now resolves the target before formatting — previously showed an empty project name when invoked with `.`. Minor UX fix, no AC impact.

**Doc updates from this slice:**

- No `architecture.md` changes required (no new module boundaries).
- No ADR required (no irreversible architectural decisions).
- No `docs/memory/learnings.md` entry needed — the test `NameError` is a Python beginner-grade issue, not a generalizable lesson.

---

## Slice 001-03 — signal-detection

**STATUS: DONE**

**Goal:** Wizard detects project signals from the filesystem and selects appropriate tiers.

**DoR:** Spike 001a STATUS: DONE. ✅

**Acceptance Criteria:**
1. LLM/agent file presence → Tier 2 (`eval-harness`) is offered.
2. CI files present → hook strictness default set to `strict` (recorded in scaffold.json, not yet enforced).
3. Existing test suite → `tdd-loop` (Tier 1) auto-installed.
4. Signal detection produces a `brief.md` summary at the project root.
5. No false positives on a bare `git init` repo (no signals → default tiers, no Tier 2 offered).

**DoD:** Same as 001-01. All checked.
- [x] All ACs pass (39 tests, all green)
- [x] Implementer test coverage (17 new tests in `SignalDetectionTests` covering each detector category positive + negative + exclusions)
- [x] Reviewed by `reviewer` subagent (verdict: pass with 4 non-blocking issues — 2 fixed, 2 deferred)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ Still end-to-end; adapts output to project context.

### Deviation log (after reconciliation)

The original spec is preserved above. This section records what changed.

**Reviewer-flagged fixes (in this slice):**

1. **pyproject.toml description false-positive.** Original implementation did a substring match (`"openai" in pyproject and "dependencies" in pyproject`) which would trigger on `description = "openai integration helper"` if any deps key existed. Tightened to require the lib name in dependency-position (quoted list entry with version pin or closing-quote-comma-bracket, OR poetry table-key form). Regression tests added: `test_llm_signal_not_triggered_by_pyproject_description_alone` and `test_llm_signal_via_pyproject_dep`.
2. **`detect_signals` on non-existent target raised `FileNotFoundError`** from library callers. CLI is safe (it `mkdir`s first), but a programmatic caller would hit it. Added an existence guard that returns an all-False `Signals` for non-existent targets.

**Reviewer issues deferred to `docs/refinement-todo.md`:**

3. **Wall-clock time-box for signal detection** (spike calls for 3 seconds; not enforced). Theoretical concern on local-only scaffolder; deferred.
4. **Unbounded `_read_text_safe`** could read a multi-GB requirements.txt. Same risk profile; deferred.
5. **Transactional writes in `scaffold()`.** A crash mid-scaffold leaves partial state without `scaffold.json`. Deferred with mitigation idea.

**Contract change traceability (from 001-01):**

- Slice 001-01 hard-coded `installed_tiers = ["tier-0", "tier-1"]` as the happy-path default. Slice 001-03 changes this: Tier 1 is now signal-gated (only installs when test signals are present). On a bare repo, `installed_tiers` is just `["tier-0"]`.
- Existing test `test_scaffold_json_schema` was updated from `assertIn("tier-1", installed_tiers)` to `assertNotIn("tier-1", installed_tiers)` to reflect the new contract.
- This is a **legitimate spec evolution**: 001-01 wrote the happy-path default; 001-03 redefined what "happy path" means based on Spike 001a findings.

**Forward-leaning additions:**

- `scaffold.json` now has an `offered_tiers` key when Tier 2 is offered. Not strictly required by AC #1 (recording in `scaffold_signals.has_llm_agent_files` would suffice), but `offered_tiers` is a cleaner contract for downstream consumers (slice 001-05 Q&A wizard, future install-on-confirm flows).
- `brief.md` is committed-state but Status: Draft marker isn't strictly required by AC #4. Added for consistency with all other scaffolded docs.

**Doc updates from this slice:**

- 2 new entries in `docs/refinement-todo.md` (time-box+unbounded read bundled into one; transactional writes a second).
- No `architecture.md` changes (no new module boundaries; signal detection is internal to scaffold-init).
- No ADR required.
- No `learnings.md` entry — the pyproject regex bug was a "first attempt was too coarse" issue, not a generalizable lesson.

---

## Slice 001-04 — deferred-decisions

**STATUS: DRAFT**

**Goal:** `refinement-todo.md` is structured and complete — not just a flat list.

**DoR:** Slice 001-02 STATUS: DONE.

**Acceptance Criteria:**
1. Each entry format: `## Decision: <name>` / `**Deferred:** <reason>` / `**Resolution trigger:** first <X>-touching spec`.
2. Decisions categorized: Architecture, Conventions, Operations.
3. After 3 reconciled specs in a dogfood project, scaffold-reconciliation check (skill, not hook) suggests promoting stale deferred items.

**DoD:** Same as 001-01.

**Anti-horizontal-phasing check:** ✅ Adds governance layer to existing output.

---

## Slice 001-05 — wizard-qa

**STATUS: DRAFT** _(implement last)_

**Goal:** Q&A interaction mode — wizard asks project-scoping questions before generating output.

**DoR:** Slice 001-03 STATUS: DONE.

**Acceptance Criteria:**
1. 3-5 targeted questions: runtime/language, team size, existing CI, LLM/agent work planned.
2. User answers override filesystem inferences.
3. Questions are skippable — filesystem inference used as fallback if user skips.
4. If all questions skipped, output is identical to 001-03 (pure inference mode).

**DoD:** Same as 001-01.

**Anti-horizontal-phasing check:** ✅ UX layer on top of existing functional output.
