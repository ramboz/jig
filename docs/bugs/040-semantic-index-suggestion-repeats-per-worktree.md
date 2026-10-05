---
status: REVIEWED
tier: standard
severity: medium
claimed_by: claude/github-issue-231-review-229fa0
regression_test: hooks/scripts/test_jig_semantic_index.py::Bug040RepoScopedSuggestionTests
main_repro_checked_at: 2026-10-04
main_repro_ref: origin/main@24b58148
main_repro_result: reproduces
red_confirmed_at: 2026-10-04
green_confirmed_at: 2026-10-04
fix_class: structural_fix
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 040: semantic-index-suggestion-repeats-per-worktree

Reported: GitHub issue 231 (Copilot CLI, macOS). Docs-only attempt: PR 232
(superseded by this fix — its "commit `auto_attach: false`" advice is a no-op
on current code; see Evidence).

## Symptom

The `jig-semantic-index` SessionStart hook documents "at most one compact,
actionable suggestion" (`templates/docs/workflow.md.template`, Semantic-Index
Exploration). On hosts that cut a fresh git worktree per session (GitHub
Copilot CLI), the missing-provider suggestion ("Configured semantic index
provider '<p>' is not installed. Install it or update …") is re-emitted every
session. The reporter's and PR 232's workaround — commit
`{"auto_attach": false}` — does not silence it. The suggestion text also says
"Install it", which in-session agents read as an instruction and attempt
(the sandbox-blocked install message quoted in the issue is the Copilot
agent's own prose, not jig output).

## Repro

`scratchpad/repro040.sh <hook> <true|false>`: `git init` a repo, commit
`.jig/semantic-index.json` = `{"auto_attach": <v>, "provider":
"codebase-memory-mcp"}` (binary absent from `PATH`), run the hook twice in the
primary checkout, then once each in two fresh `git worktree add` checkouts.

```
== auto_attach true
session1 (primary):        {"continue": true, "additionalContext": "Configured semantic index provider 'codebase-memory-mcp' is not installed. Install it or update ...
session2 (primary):        <silent>
session3 (fresh worktree): {"continue": true, "additionalContext": "Configured semantic index provider ...
session4 (fresh worktree): {"continue": true, "additionalContext": "Configured semantic index provider ...
== auto_attach false (issue/PR workaround)
<identical output>
```

## Evidence

- `hooks/scripts/jig-semantic-index.sh:35-36` — `_seen_path()` is
  `Path(project_dir) / '.jig' / 'semantic-index-claude-hook.json'`, i.e. the
  once-only record is per **checkout**; the file is gitignored
  (`.gitignore:24`, `scaffold.py:3345`), so it never travels to a new worktree.
  The Copilot package ships this script byte-identical
  (`cmp` vs `hosts/copilot/.github/hooks/scripts/jig-semantic-index.sh`).
- `skills/_common/semantic_index.py:240` — `load_state` reads
  `auto_attach=_json_bool(raw.get("auto_attach", False))`: an explicit `false`
  is indistinguishable from an absent key. `activate()` (`:441-482`) returns
  `action="recommend"` for a missing provider before `auto_attach` is ever
  consulted, so no committed state silences the suggestion.
- `skills/_common/semantic_index.py:371-382` — `_missing_provider_recommendation`
  reads "Install it or update …" with no host-vs-session qualifier.
- `write_state()` (`semantic_index.py:258`) has no non-test caller
  (`git grep "write_state"`): jig does not write the opt-in; the issue's
  "setup path enables auto_attach for an undetected provider" factor is the
  agent acting on the suggestion text, not jig code.
- History: the per-checkout seen-file arrived in 97b6cb5a (spec 080-02,
  "wire Claude semantic index activation"), designed before Copilot's
  per-session-worktree host existed (spec 113).

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: the hook's once-only dedup is simply broken (key mismatch / write
  failure). Falsify by: session2 in the *same* checkout is silent in the repro —
  dedup works within a checkout. Falsified.
- [ ] H2: `auto_attach: true` on an undetected provider (issue factor 1) causes
  the repeat. Falsify by: the repro with `auto_attach: false` is identical, and
  `activate()` returns recommend/provider_missing before reading `auto_attach`.
  Falsified.
- [ ] H3: Copilot's adapter passes a different `CLAUDE_PROJECT_DIR` each session
  for the same checkout. Falsify by: `copilot_hook_adapter.py:304` sets it from
  the session working dir, which *is* the fresh worktree; the repro shows the
  repeat with plain `git worktree add`, no adapter involved. Not needed to
  explain the symptom.
- [x] H4 (leading): the once-only record is scoped to the checkout, not the
  repository, so every fresh worktree is a "first time"; and there is no
  committed opt-out because explicit `false` == absent. Confirmed by the repro
  (silent on same-checkout rerun, loud on each new worktree, `false` no-op).

## Root cause

Process, not output: the hook models "show this once" as **per-checkout** state
(`<checkout>/.jig/semantic-index-claude-hook.json`), but the documented contract
("at most one compact suggestion") is per **repository**. That held only while
a repo had one long-lived checkout; a host that creates a worktree per session
turns every session into a first run. Compounding it, the state schema has no
way to record a decision to decline: `load_state` collapses explicit
`auto_attach: false` into "unset", so the only durable, committable lever
users reach for is a no-op. The install-inviting wording then makes agents
attempt an install the sandbox blocks.

Enumeration for "the seen-file is the only once-only gate on this path":
`git grep -e _already_suggested -e semantic-index-claude-hook -e seen_path`
outside `hosts/` returns only `hooks/scripts/jig-semantic-index.sh:35-73` plus
docs/ignore lists; the Codex project hook is a string-rewrite of the same body
(`scaffold.py:1660-1668`) and the Copilot one a byte copy, so the set is closed
by the generator, not just the search.

## Repository closure inventory

<!-- Spec 091 / ADR-0037: pre-fix repository closure. Standard & gnarly
     bugs gate ROOT_CAUSED -> FIXING on substantive answers below. This
     is an effort-and-protocol standard, NOT a completeness proof: show
     the search you actually ran. A bare "none found" fails; record
     residual uncertainty as an assumption WITH the protocol behind it,
     applying the same enumeration standard as `## Root cause` (ADR-0052).
     Prefer a configured semantic index; the portable floor is targeted
     search + `git log`/`git blame`. -->

**Equivalent / convergent logic searched:** Scout `keyword_search` +
`git grep` for `_already_suggested`, `_mark_suggested`, `seen_path`,
`semantic-index-claude-hook`, `git-common-dir`, `resolve_repo_root`,
`no-servo-hint`, `servo-hint-shown`. Found: (a) `semantic_index.resolve_repo_root`
(`semantic_index.py:294`) already resolves the canonical root via
`git rev-parse --git-common-dir` — the worktree-aware primitive to reuse;
(b) the convergent once-per-project pattern in `slice-land/land.py:721`
(slice 072-02): per-checkout `.jig/servo-hint-shown` breadcrumb + a **tracked
explicit opt-out** `.jig/no-servo-hint` — the precedent for a committed
opt-out. No existing repo-scoped once-only store exists.

**Relevant history inspected:** `git log -S _already_suggested` → 97b6cb5a
(spec 080-02) introduced the per-checkout seen-file; `git log` on
`semantic_index.py` / the hook / the workflow template (414fe82a, a03f6c87,
0cf63e8c) — none touched dedup scope or `auto_attach` parsing. Copilot host
packaging (spec 113) copied the hook verbatim afterwards; no change adapted it
to per-session worktrees.

**Affected call sites:**
1. `hooks/scripts/jig-semantic-index.sh` `_seen_path/_already_suggested/_mark_suggested` (Claude source).
2. `hosts/copilot/.github/hooks/scripts/jig-semantic-index.sh` + `hosts/claude/...` + `hosts/codex/...` (generated copies).
3. Codex project-hook rewrite `scaffold.py:1660-1668` (string-replaces `semantic-index-claude-hook.json` and `host='claude'`).
4. `semantic_index.load_state` / `ActivationState` / `activate()` (explicit-`false` semantics).
5. `_missing_provider_recommendation` (both message variants).
6. Docs: `templates/docs/workflow.md.template` Semantic-Index section (+ host mirrors); `docs/architecture.md:514` (seen-file location).
7. Ignore lists `.gitignore:24`, `scaffold.py:3345-3346` (legacy seen-file names).
8. `land.py` servo-hint breadcrumb (same per-checkout class, different surface).

**Reuse decision:** Reuse `git rev-parse --git-common-dir` resolution (same
call `resolve_repo_root` makes) via a small `suggestion_state_path()` helper in
`semantic_index.py` so the hook stays thin and all three host hooks share it;
reuse the 072-02 "tracked explicit opt-out" precedent, but express it as the
already-committable `"auto_attach": false` in `.jig/semantic-index.json`
rather than a second file, so the issue's/PR 232's natural workaround becomes
true and there is one config home.

## Fix class

`structural_fix` — moves the once-only record to repository scope and gives the
state schema a committable decline, rather than special-casing Copilot.

## Fix

1. `skills/_common/semantic_index.py` — new `suggestion_state_path(project_dir,
   host)` resolves `<git-common-dir>/jig/semantic-index-<host>-hook.json`
   (checkout `.jig/` outside git). `ActivationState.opted_out` (runtime-only,
   like `provider_explicit`) is set when the file holds JSON
   `"auto_attach": false`; `activate()` short-circuits it to
   `action="detect", outcome="opted_out"` with no recommendation (telemetry
   still recorded). `write_state` omits `auto_attach` unless true or opted out,
   so a default state is not silently written as a decline. Both
   missing-provider texts now say install happens on the host from the user's
   own shell, not inside an agent session, and name the `false` opt-out.
2. `hooks/scripts/jig-semantic-index.sh` — `_seen_path` uses the helper (falls
   back to the legacy checkout path if an older helper lacks it); reads also
   consult the legacy per-checkout file so existing users are not re-prompted
   once on upgrade. Host name goes through `ACTIVATE_KW = dict(host='claude')`
   so the Codex renderer's existing `host='claude'` rewrite still applies.
3. Docs: `templates/docs/workflow.md.template` gains the corrected PR 232 note
   (explicit-`false` opt-out, commit the state for per-session-worktree hosts,
   install from your own shell); `docs/architecture.md` state-file bullet.
4. `hosts/` regenerated (`build_host_packages.py`, `--check` clean).
5. `scripts/usage.py` `_activation_bucket` — new `opted-out` bucket so the new
   `outcome="opted_out"` telemetry is not reported as `activation-failed`
   (craft-review finding); tested in `scripts/test_usage.py`.

**Scope beyond the minimal fix (owner-acknowledged 2026-10-04).** The
repo-scope move alone stops the repeat. In addition, and deliberately:
(a) explicit JSON `"auto_attach": false` is now a committed **decline** that
silences *all* suggestions, including the "provider available, not opted in"
one. Spec 080 defined no decline; precedent is 072-02's tracked
`.jig/no-servo-hint`. The owner chose this when approving the plan for issue 231
("add a real opt-out"). (b) Both missing-provider texts changed (user-visible).
(c) `write_state` serialization changed: a default state no longer writes
`auto_attach`, so it cannot be read back as a decline. `write_state` has no
non-test caller, so no jig-written files exist in the wild to reinterpret.

## Call-site closure

<!-- Spec 091 / ADR-0037: before REVIEWED, account for every site named
     in the inventory above as changed, tested, or intentionally left
     alone. Accounting, not mandatory widening. -->

**Disposition per affected site:**
1. Claude hook source — **changed + tested** (`Bug040RepoScopedSuggestionTests`).
2. Generated `hosts/{claude,codex,copilot}` hooks + `_common` copies — **changed** by regeneration; Copilot copy re-run against `repro040.sh` (sessions 3-4 now silent).
3. Codex project-hook rewrite (`scaffold.py:1660-1668`) — **left alone, verified**: `CodexScaffoldRenderer.rewrite_hook_script_body` on the new body yields `ACTIVATE_KW = dict(host='codex')` and the codex legacy filename; scaffold suites green.
4. `load_state` / `ActivationState` / `activate()` / `write_state` — **changed + tested** (`Bug040OptOutAndSuggestionScopeTests`; existing 22 tests unchanged and green).
5. `_missing_provider_recommendation` — **changed + tested** (`test_missing_provider_text_points_install_outside_the_session`).
6. Docs template + architecture — **changed**; `test_semantic_index_guidance.py` green.
7. Ignore lists — **left alone**: legacy per-checkout files may still exist and stay ignored; the new file lives inside `.git/`, which git never tracks.
8. `land.py` servo-hint breadcrumb (`.jig/servo-hint-shown`) — **left alone**: same per-checkout class but a landing-time (not per-session) surface with an existing tracked opt-out; flagged as a separate follow-up rather than widening this fix.
9. The hook's `fallback` warning — **left alone**: it fires only for an opted-in, installed provider that failed readiness *this* session; per-session reporting is the intended, actionable behaviour.
10. Copilot host label — **left alone**: the Copilot hook is a byte copy carrying `host='claude'`, so on Copilot the record is `<common>/jig/semantic-index-claude-hook.json`, shared with Claude Code on the same clone. Harmless (shared dedup), predates this fix; documented in `docs/architecture.md`.
11. `scripts/usage.py` activation bucketing — **changed + tested** (new `opted-out` bucket).

## Already tried

## Regression test

`hooks/scripts/test_jig_semantic_index.py::Bug040RepoScopedSuggestionTests` —
real `skills/_common` helper, real git repo + `git worktree add`, pinned absent
provider: (a) no re-suggestion in a fresh worktree, (b) committed
`"auto_attach": false` silent in primary and worktree, (c) text points install
to the user's own shell and names the opt-out. Unit companion:
`skills/_common/test_semantic_index.py::Bug040OptOutAndSuggestionScopeTests`.

## Proof

- Red witnessed by `bug.py transition 040 FIXING` (3 failures, pre-fix).
- Post-fix: hook suite 11 OK, `_common` semantic-index 27 OK, guidance 9 OK,
  scaffold + scaffold_mode OK, `build_host_packages.py --check` OK, ruff clean.
- `repro040.sh` against the regenerated Copilot hook: session1 suggests,
  sessions 2-4 (same checkout + two fresh worktrees) silent.

## Learning

Recorded in `docs/memory/learnings.md` ("Scope 'show once' state to the repository, not the checkout"). Once-per-project nudges must key their marker to the repository (git common dir) and offer a tracked opt-out; test with a real `git worktree add`.

## Main recheck

- 2026-10-04 - `origin/main@24b58148` -> reproduces: scratchpad/repro040.sh hooks/scripts/jig-semantic-index.sh {true,false}: suggestion re-emitted in each fresh git worktree (sessions 3,4) and with committed auto_attach:false
