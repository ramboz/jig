---
status: RECONCILED
dependencies: [adr-0048]
last_verified: 2026-08-03
frame_review: true
claimed_by: claude/issue-105-status-check-8f45c0
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 103-01 — SessionStart git-freshness nudge

**Goal:** When a session starts on a branch that is behind its integration base
(`origin/main`; see AC3 for resolution), the agent receives one
`additionalContext` nudge — "HEAD is N commit(s) behind <base>; sync before
trusting repo state" plus the review command — before it reads a single file. Silent when up-to-date, not in a repo, or opted out. Never
blocks, never mutates working-tree state, always exits 0.

**Scope:** one host-agnostic hook (pure git + stdout). Both host packages
receive it via `build_host_packages.py` regen; there is no host-specific payload
to re-probe (contrast slice 098-02), so Codex parity is asserted in the DoD, not
split into its own slice.

**DoR:**
- ✅ [ADR-0048](../../decisions/adr-0048-session-git-freshness-fetch-and-nudge.md)
  records the two load-bearing calls (always-fetch timeout-guarded; active
  nudge) — Proposed, and accepted before this slice leaves DRAFT.
- ✅ The five open questions from [#105](https://github.com/ramboz/jig/issues/105)
  are settled by the maintainer (spec § Settled calls).
- ✅ The co-location target exists: `hooks/hooks.json` `SessionStart` runs three
  hooks today (`jig-context-check.sh`, `jig-project-orient.sh`,
  `jig-semantic-index.sh`).
- ✅ The wrapper/helper pattern exists: `jig-context-check.sh` +
  `lib/context_fill.py`.
- ✅ The nudge/trace path exists:
  `lib/read_attribution.append_additional_context_event`.
- ✅ The fetch-then-compare shape is proven here:
  `land.py._check_ff_viable()` fetches `origin/main` at command time (bug 001).
- ✅ Registration surfaces are known: `scripts/verify_install.py`
  `_EXPECTED_HOOK_SCRIPTS`, `scripts/test_install_contract.py`
  `test_real_hooks_json_references_*_scripts`, `skills/scaffold-init/scaffold.py`
  status-message map, and `scripts/build_host_packages.py` regen.

**Acceptance Criteria:**

1. **Trigger.** A new hook `hooks/scripts/jig-git-freshness.sh` fires on
   `SessionStart`, registered as the 4th `SessionStart` entry in
   `hooks/hooks.json` (after `jig-context-check.sh`, `jig-project-orient.sh`,
   `jig-semantic-index.sh`), with a hook-level `timeout` generous enough to
   contain a bounded fetch (≥ 10s).

2. **Testable helper + thin wrapper** (established pattern). All logic lives in
   `hooks/scripts/lib/git_freshness.py`; `jig-git-freshness.sh` only marshals
   stdin, prints the JSON result, and logs. The wrapper resolves its own
   directory so the helper imports whether jig runs as a plugin
   (`${CLAUDE_PLUGIN_ROOT}/hooks/scripts/`) or a scaffolded install
   (`${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`), mirroring
   `jig-context-check.sh`.

3. **Integration-base resolution — the smart-target rule**
   (ADR-0048 § Upstream semantics; load-bearing). The staleness target is the
   ref this branch integrates *into*, resolved in order:
   1. **`@{upstream}` iff it resolves AND is not this branch's own remote
      (`origin/<current-branch>`)** — a tracking upstream pointing elsewhere is a
      real integration base (git-flow `origin/develop`, fork `upstream/main`,
      explicit `set-upstream-to` a base). This case wins over the trunk.
   2. **else `origin/main`, then `origin/master`** — the trunk base. This is
      jig's case: a pushed task branch's `@{upstream}` is `origin/<branch>`
      (its own remote), excluded by rule 1's own-remote guard, so it falls here.
   3. **else silent** (not a work tree, or nothing resolves), exit 0.

   The **own-remote guard in rule 1 is load-bearing**: without it, a pushed task
   branch would compare `HEAD..origin/<branch>` (own-branch advancement ≈0, not
   base drift) and go silent on the exact #105 base-drift case. Neither
   "prefer `@{upstream}`" nor "prefer `origin/main`" alone is correct across
   branching models — the guarded two-rule form is.

4. **Always fetch, timeout-guarded** (ADR-0048 Q1). Before comparing, the hook
   attempts `git fetch <remote> <branch>` for the resolved base (AC3) under a
   hard subprocess timeout `JIG_GIT_FRESHNESS_TIMEOUT` (default 5s; out-of-range /
   non-numeric → default). The fetch is **best-effort**: on timeout, non-zero
   exit, offline, or missing git, the hook does **not** error — it falls through
   to the comparison against the last-known ref. The subprocess timeout is
   strictly less than the hook-level timeout so a nudge can still be emitted
   after a slow/failed fetch.

5. **Behind computation + nudge** (ADR-0048 Q2). `behind = git rev-list --count
   HEAD..<base>` where `<base>` is the target resolved in AC3. When
   `behind > 0`, emit an `additionalContext` nudge that (a) states the count and
   base ref, (b) says the repo state may be stale and to sync before forming
   conclusions, and (c) gives the review command
   (`git log HEAD..<base> --oneline`) and the sync hint (fetch + merge or
   rebase). When `behind == 0`, the hook is **silent**. The nudge is advice: it
   names commands, it does not run merge/rebase.

6. **No owner friction / fail-open.** Never sets `continue: false`; never blocks;
   emits no dialog; makes no working-tree mutation. `except Exception: pass`
   around all logic; any error (malformed stdin, git failure, timeout) leaves
   the session untouched. Always exits 0.

7. **Compact-source skip (best-effort).** When the SessionStart payload's
   `source` is `compact`, the hook skips the fetch + check (no re-fetch on
   mid-session compaction). If `source` is absent/unknown, it runs normally —
   degradation, not error (spec Assumptions).

8. **Opt-out.** `JIG_GIT_FRESHNESS` ∈ `{0, false, off, no}` disables the hook
   (silent, exit 0), matching the widened token set the sibling hooks use.

9. **Auditable.** A fire logs via `append_additional_context_event` (hook name
   `jig-git-freshness`, event kind e.g. `branch_behind_upstream`).

10. **Scaffold + both-host parity.** Register the script in
    `scripts/verify_install.py` `_EXPECTED_HOOK_SCRIPTS`, add its friendly
    status message in `skills/scaffold-init/scaffold.py`, bump the hook-count
    contract in `scripts/test_install_contract.py`, and regenerate host packages
    (`scripts/build_host_packages.py`) so `hosts/claude/**` and
    `hosts/codex/**` both reference the script and `--check` is clean.

**Tests first (TDD):**
- behind branch (HEAD behind `origin/main`) → nudge emitted once, names the
  count and base ref, includes the review command.
- **anti-dead-gate:** up-to-date branch (`behind == 0`) → **silent**. (A dead
  gate is also silent — this pins the positive case above against it.)
- **own-remote-guard regression (jig case):** a *pushed* task branch whose
  `@{upstream}` is `origin/<branch>` (itself 0 behind its own remote) but whose
  `origin/main` base has advanced N commits → **nudges** against `origin/main`.
  Asserts base drift is measured, not own-branch advancement — a rule preferring
  `@{upstream}` would go silent here.
- **non-own-upstream wins (git-flow case):** a branch whose `@{upstream}` is
  `origin/develop` (≠ its own remote) and is behind it, while `origin/main` also
  resolves and is *not* behind → **nudges** against `origin/develop`, not
  `origin/main`. Asserts a real non-own upstream is preferred over the trunk.
- not a git work tree → silent, exit 0.
- nothing resolves (no non-own `@{upstream}`, no `origin/main`/`origin/master`) →
  silent, exit 0.
- resolution precedence: non-own `@{upstream}` wins; else `origin/main`; else
  `origin/master`; own-remote `@{upstream}` is excluded by the guard.
- **fetch is attempted** with the configured timeout — assert the fetch
  subprocess is invoked with a `timeout` argument (mirror spec 098's
  `test_git_subprocess_calls_pass_a_timeout`).
- **fetch times out / fails / offline** → no error; the hook still computes
  `behind` against the last-known ref and nudges if behind (degradation path).
- `JIG_GIT_FRESHNESS_TIMEOUT` out-of-range / non-numeric → falls back to default.
- `source == "compact"` → skipped (no fetch, silent); `source` absent → runs.
- `JIG_GIT_FRESHNESS=0` (and `false`/`off`/`no`) → silent.
- malformed stdin / missing fields → exits 0, no output (fail-open).
- a fire calls `append_additional_context_event` with the hook name + event kind.
- scaffold parity: `_EXPECTED_HOOK_SCRIPTS` lists `jig-git-freshness.sh`.
- contract: `hooks/hooks.json` references the new script (count bumped); both
  host packages reference it (`build_host_packages.py --check` clean).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one fixture;
      edge cases above covered explicitly.
- [ ] Each new test shown to fail when its feature is removed (red→green
      witnessed; the anti-dead-gate test in particular).
- [ ] Reviewed by `reviewer` subagent (compliance) — prompt built by
      `review.py`; passes.
- [ ] Craft pass (`pr-review`) — passes (no `[blocker]`).
- [ ] Frame pass if `frame_review: true` — passes.
- [ ] `hooks.json` + scaffold registration updated; parity/contract tests green;
      both host packages regenerated and `build_host_packages.py --check` clean.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice lands, an agent starting a
session on a drifted branch is told so — with the count, the upstream, and the
commands to sync and review — before it reads any file. That is the complete,
observable, end-to-end value #105 asks for; nothing here is intermediate state
for a later slice.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Primer hygiene per spec 025-01: this slice closes the spec, so add a
      one-line hot-cache term for the freshness hook (via `/jig:memory-sync`) and
      compress the Active-specs entry.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**1. AC3 resolution rule evolved across frame critique (spec-frame, not code deviation).**
The proposal (#105) and the first draft resolved `@{upstream}` first, falling
back to `origin/main`. Three ADR frame rounds + two slice frame rounds reshaped
this: `@{upstream}`-first was falsified (a pushed jig task branch measures
own-branch advancement, ~0, silencing the #105 case); base-first was then
falsified for git-flow/fork (where `@{upstream}` *is* the base but `origin/main`
also resolves). The final **smart-target rule** — a non-own `@{upstream}` wins,
else `origin/main`→`origin/master`, else silent — is correct across all three
models. This shaped the spec/ADR before implementation, so the code matches AC3
as written; recorded here because the AC itself moved substantially from the
issue's prototype. Pinned by the own-remote-guard + git-flow regression tests.

**2. Test-isolation defect found during orchestrator verification (not by the
implementer).** `test_missing_project_dir_still_exits_zero` ran the wrapper with
no `CLAUDE_PROJECT_DIR` and no `cwd`, so `project_dir` defaulted to `.` = the
real repo, and the hook did a **live network fetch** and wrote its audit log
into `hooks/scripts/.claude/`, dirtying the tree and breaking
`build_host_packages.py --check`. Fixed by running that subprocess in an
isolated temp cwd (+ asserting empty stdout). Root cause: the hook's audit log
(`append_additional_context_event`) writes under `project_dir/.claude/`, so a
test must never let `project_dir` resolve to the source tree.

**3. Craft nits addressed pre-REVIEWED (craft pass, all non-blocking).**
- `JIG_GIT_FRESHNESS_TIMEOUT` is now clamped to `_MAX_TIMEOUT=8s` (< the 10s
  hook budget) so AC4's "subprocess timeout < hook timeout" invariant holds by
  construction, not by operator discipline (+ a clamp test).
- `_fetch` now routes through `_run_git` (DRY; single timeout/except path).
- The git-flow test pins its upstream explicitly (`branch --set-upstream-to`)
  rather than relying on git's default `autoSetupMerge`.
- `os.sys.path` → `import sys`; removed the now-unused `os` import (ruff clean).

**4. `evaluate()` takes an optional `env` param** (defaults to `os.environ`)
rather than reading `os.environ` inline like `entry_gate.evaluate()` — an
injectable-for-tests choice, behaviour-identical in production.

**Cumulative-timeout observation (accepted, not changed):** up to five sequential
git calls each carry the full resolved timeout, so a worst case could in theory
exceed the 10s hook budget. Not a real risk — only `_fetch` can approach its
bound; the local reads (`branch`, `rev-parse`, `rev-list`) return in
milliseconds. Left as an accepted observation; the hook-level timeout kills any
runaway and the session continues (fail-open).

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door unaffected — an internal hook addition. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`; 103 row present (and 104 after the origin/main merge). |
| `docs/product-vision.md` | `no-op` | No behaviour/scope/positioning drift; the hook sits within the existing deterministic-spine philosophy (principle 1). |
| `docs/architecture.md` | `updated` | Hook-inventory count 15→16; `git-freshness` added to the mermaid spine, the `additionalContext`-injector list, and a describing sentence (spec 103 / ADR-0048). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | `CLAUDE.md` hot cache gains a **Session git-freshness** key-term line (spec closes → 025-01 compress rule; no Active-specs entry since it ships DONE). `AGENTS.md` / `templates/CLAUDE.md.template` are generic scaffold sources that don't enumerate jig's own specs — no-op. |
| `docs/inbox.md` | `no-op` | Nothing parked by this slice. |
| `docs/refinement-todo.md` | `no-op` | The behind-floor threshold is already an ADR-0048 kill-criterion/"still-open" item; two out-of-scope findings (build `_is_ephemeral` gap; pre-existing `.claude/settings.json` entry-gate drift) filed as separate background tasks rather than deferred here. |
| `docs/memory/**` | `updated` | memory-sync: smart-target resolution rule + the hook-test isolation gotcha captured. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0048 Accepted (frame-critique evidence recorded) + indexed; regenerated after the origin/main merge added ADR-0049. |
| Host packages (`hosts/**`) | `updated` | Regenerated via `build_host_packages.py`; both hosts reference the new hook; `--check` clean. |
| `.claude/settings.json` (jig dogfood wiring) | `updated` | Intentionally registered `jig-git-freshness.sh` as a 5th `SessionStart` entry so jig dogfoods its own hook — distinct from the pre-existing entry-gate PostToolUse drift (filed as a separate background task). |
| Registration surfaces (`hooks/hooks.json`, `verify_install.py` `_EXPECTED_HOOK_SCRIPTS`, `test_install_contract.py`, `scaffold.py`) | `updated` | AC1/AC10 wiring — 4th `SessionStart` entry, script list, contract count 15→16, scaffold status message. |
