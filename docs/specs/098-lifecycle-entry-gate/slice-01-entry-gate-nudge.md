---
status: DONE
dependencies: [adr-0044, 098-04]
last_verified: 2026-08-02
frame_review: true
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about runnable
     surfaces by probe first (run it / read source) or a citation, else mark them
     as assumptions — never assert an unverified claim as fact. -->

## Slice 098-01 — entry-gate nudge (Claude host)

**Goal:** An edit to project source made while the session is **not** inside the
lifecycle produces one agent-facing `additionalContext` nudge — "this edit is
outside jig; route it (claim a slice / open a bug) or record it" — and nothing
else. No block, no owner prompt, no failure mode for the session.

**Scope:** the Claude host. The Codex-host equivalent is slice 098-02 (settled
call #4 — same spec, separately verifiable slice).

**STARTABLE — both sequencing dependencies satisfied (2026-08).** AC2's
definition was settled (maintainer, 2026-07-30); both surfaces it reads now exist:

1. **[#138](https://github.com/ramboz/jig/pull/138) merged 2026-07-30.** A slice
   claim spans the whole working lifecycle (`_CLAIM_WORKING_STATUSES` in
   `workflow.py`) instead of clearing at REVIEWED, so the gate stays silent
   through reconciliation.
2. **Slice 098-04 is DONE.** It stamps the same working-tree marker for the bug
   lifecycle (`bug=NNN` in `.jig/spec-ref`), which #138 does not touch.

Both are declared in the frontmatter and confirmed in the tree
(`workflow.py._CLAIM_WORKING_STATUSES`, `bug.py` marker stamping).

**DoR:**
- ✅ [ADR-0044](../../decisions/adr-0044-lifecycle-entry-gate.md) is **Accepted**
  (2026-07-30), after being held at Proposed through two failed frame-critique
  rounds.
- ✅ Question #5 (what signal means "inside the lifecycle") is answered — see
  [ADR-0044 resolved question #5](../../decisions/adr-0044-lifecycle-entry-gate.md#resolved-question-5).
- ✅ #138 merged (2026-07-30) — `_CLAIM_WORKING_STATUSES` present in `workflow.py`.
- ✅ Slice 098-04 DONE — `bug.py` stamps the `bug=NNN` marker.
- ✅ The **four** questions this spec was opened with are settled by the
  maintainer on [#128](https://github.com/ramboz/jig/pull/128); the criteria
  below are written against those calls, not against the draft's
  recommendations.
- ✅ Field evidence is counted: [#111](https://github.com/ramboz/jig/issues/111)
  records 11 out-of-lifecycle edit incidents (20 Jun – 16 Jul 2026).
- ✅ The co-location target exists: `hooks/hooks.json` has a `PostToolUse` /
  `Edit|Write|MultiEdit` matcher already running `jig-post-edit-verify.sh` and
  `jig-boundary-change-warn.sh`.
- ✅ The nudge/trace path exists:
  `lib/read_attribution.append_additional_context_event`.
- ✅ The anti-nag mechanism exists: `jig-context-check.sh` once-per-band-per-session
  `$TMPDIR` state file.
- ✅ **Lifecycle-state sources are now sufficient.** `claimed_by` (spec 049) spans
  the working lifecycle via #138's `_CLAIM_WORKING_STATUSES`, and the bug arm reads
  098-04's `bug=NNN` marker — so the gate answers "is *this session* inside the
  lifecycle" for both arms. (This DoR item was ✅ in the original draft, falsified
  by the frame critique, and is now genuinely satisfied by the two merged deps.)
- ✅ **`session_id` is present in the `PostToolUse` payload** — probed on the
  Claude host 2026-07-30 (spec Assumptions). AC5's cadence keying is safe here;
  the Codex equivalent is 098-02's to re-probe.
- ✅ The `.gitignore` oracle is probed, and its gap is measured: `git check-ignore`
  excludes `.claude/settings.local.json` but **not** `docs/specs/README.md` or
  `.claude/` (probe recorded in the spec's Assumptions) — which is why AC3 is
  two-part.

**Acceptance criteria:**

1. **Trigger.** A new hook `hooks/scripts/jig-entry-gate.sh` fires on
   `PostToolUse` / `Edit|Write|MultiEdit`, co-located in the existing matcher
   (third entry after `jig-post-edit-verify.sh`, `jig-boundary-change-warn.sh`).
2. **In-lifecycle detection — a live working-lifecycle claim held by this
   checkout** (settled call #5). The check is *coarse*: it never asks whether the
   edited file belongs to the claimed work item's surface. The session counts as
   **inside** when either arm holds:
   - **Slice arm.** `.jig/spec-ref` names a slice, that slice's `claimed_by`
     equals this checkout's `_claim_identifier`, **and** its status is one of
     #138's `_CLAIM_WORKING_STATUSES` (`READY_FOR_REVIEW` / `IN_PROGRESS` /
     `REVIEWED` / `RECONCILED`).
   - **Bug arm.** The same three-part test over the bug record named by the
     marker 098-04 stamps.

   Everything else is **outside**: a clean tree, an unrelated open slice on the
   branch, a claim held by another checkout, or a work item that has reached a
   release point.

   The status cross-check is load-bearing, not belt-and-braces: nothing clears
   `.jig/spec-ref` on the way out of a working state (`workflow.py` writes it
   only under `if new_status == IN_PROGRESS_STATUS`), so the marker alone would
   assert a finished slice forever. Reading the named record's *current* status
   is what makes a stale marker harmless.

   The rule must, by construction, satisfy all four of the properties the two
   falsified drafts failed — each has a test below:
   - silent through **reconciliation** (which is inside `_CLAIM_WORKING_STATUSES`
     under #138, and was outside the old `_CLAIM_CLEARING_STATUSES` behaviour);
   - silent during a **bug fix** opened the prescribed way, via 098-04's marker;
   - **fires** on a tree with unrelated open work and no live claim (the
     falsifying case that killed the presence rule);
   - no dependence on operator identity — the comparison is **branch scoping**
     (`_claim_identifier` returns a branch name), and spec 049's non-goal of
     human-identity inference is preserved.
3. **Source boundary — `.gitignore` plus lifecycle artifacts** (settled call #3).
   The hook nudges only for edits to *project source*. A path is source unless
   either test excludes it:
   - **(a) `git check-ignore`** — the path is ignored by the project's
     `.gitignore`. Reuses the project's existing ignore mechanism; the hook adds
     **no** configurable ignore list of its own.
   - **(b) lifecycle artifact** — the path is under one of the *named* artifact
     subtrees resolved against the docs base — `specs/`, `bugs/`, `decisions/`,
     `memory/` — or under `.jig/`, `.claude/`, `.git/`. A fixed list, no
     configuration surface. Required because these are *tracked, not ignored*
     (see the spec's Assumptions probe), so (a) alone would nudge on routine
     spec / bug-record / ADR edits.

   The docs base is read via `_common/project_layout.py`. **It must never be used
   wholesale:** `docs_base` returns the project directory itself when
   `docs_root == "."` ([ADR-0033](../../decisions/adr-0033-configurable-docs-root.md)
   track-local adoption), so a "anything under `docs_root`" rule would classify
   the whole repo as lifecycle artifacts and silence the gate entirely. A failing
   or unavailable `git check-ignore` (no repo, git missing, non-zero exit other
   than "not ignored") must degrade to test (b) alone rather than error — see AC8.
4. **The nudge.** On an out-of-lifecycle source edit, emit `additionalContext`
   naming the edited file and the two ways out — route it (claim a slice / open a
   bug) or record it — and stating it is informational, not a gate. Mirror the
   `jig-boundary-change-warn` message shape.
5. **Cadence — once per session** (settled call #2). Fire at most once per
   session, re-armed when lifecycle state changes, via a `$TMPDIR` per-session
   state file.
6. **No owner friction.** Never sets `continue: false`; never blocks; emits no
   dialog. Always exits 0.
7. **Opt-out.** `JIG_ENTRY_GATE=0` (widened token set `{0,false,off,no}`, matching
   `jig-boundary-change-warn`) disables the hook.
8. **Fail-open.** `except Exception: pass` around all logic; any error leaves the
   session untouched (ADR-0044 / #111 constraint #3).
9. **Auditable.** A fire logs via `append_additional_context_event` (hook name
   `jig-entry-gate`, event kind e.g. `out_of_lifecycle_edit`).
10. **Scaffold-mode parity.** Register the script in
    `skills/scaffold-init/scaffold.py` `_EXPECTED_HOOK_SCRIPTS` and the
    `hooks.json` writer, so a scaffolded install ships the gate too.

**Tests first (TDD):**
- out-of-lifecycle edit to a source file → nudge emitted once.
- **anti-dead-gate #1 (the falsifying case):** an unrelated slice is
  `IN_PROGRESS` and an unclaimed open bug exists on the branch, but this tree
  holds no live claim → the edit **still nudges**. This is the exact tree state
  of jig's own `main`; the pre-critique rule failed it silently.
- edit while this session holds a live claim on an `IN_PROGRESS` slice → silent.
- **anti-false-fire #1:** edit to `architecture.md` / `CLAUDE.md` during
  **reconciliation** — slice at `REVIEWED`, then `RECONCILED` — → silent.
  Under #138 both are working statuses and the claim is still held; the
  pre-#138 behaviour cleared it at `REVIEWED` and this is exactly where the
  live-claim rule fired. Assert against the claim state, not just the output,
  so the test fails loudly if #138's semantics regress.
- **anti-false-fire #2:** source edit during a bug fix opened with
  `new_bug(push=True)` and picked up locally (`bug.py pickup <id>`) → silent,
  via 098-04's marker. The record originates on `origin/main`; the point of the
  test is that the *local* pickup step is what makes the gate quiet.
- **anti-stale-marker:** `.jig/spec-ref` names a slice that has since reached a
  release point (`DONE` / `DEFERRED` / `ABANDONED` / back to the pickup queue)
  → the edit **nudges**. Nothing clears the marker, so a rule that trusted it
  without the status cross-check would go silent forever after the first slice.
- **foreign claim:** marker names a slice claimed by a *different* checkout
  → **nudges** (branch scoping, AC2).
- edit to a `.gitignore`-matched path (e.g. `__pycache__/x.pyc`,
  `.jig/spec-ref`) → silent (boundary test (a)).
- edit to a *tracked* lifecycle artifact — `docs/specs/…`, `docs/bugs/…`,
  `docs/decisions/…` — → silent (boundary test (b); the case `.gitignore`
  alone would miss).
- edit under a **relocated** `docs_root` → lifecycle artifacts silent, source
  still nudges.
- **anti-dead-gate #2:** with `docs_root: "."`, an edit to project source at the
  repo root → **nudges** (the `docs_base`-returns-project-dir collapse).
- `git check-ignore` unavailable / erroring → still silent on lifecycle
  artifacts, still nudges on source; never raises (degradation path, AC3).
- second out-of-lifecycle source edit same session, state unchanged → silent
  (cadence).
- lifecycle state changes mid-session → cadence re-arms (nudge can fire again).
- `JIG_ENTRY_GATE=0` → silent.
- malformed stdin / missing `file_path` / unreadable state → exits 0, no output
  (fail-open).
- **missing `session_id` in the payload** → cadence still scopes per session, or
  the gate degrades to a documented safe behaviour; it must not silence itself
  globally via the shared `'default'` key (`jig-context-check.sh`). The field
  *is* present on Claude (probed 2026-07-30); this test guards the degradation
  path, since a host that stops sending it would silently kill the gate.
- scaffold parity: `_EXPECTED_HOOK_SCRIPTS` lists the new script.

**DoD:**
- [x] All acceptance criteria met, tests green (red→green witnessed). 30 entry-gate tests green; the two anti-dead-gate behaviors were **manually mutation-checked** — the code was hand-edited to drop the status cross-check / use `docs_base` wholesale, the pinning tests were witnessed to go red, then the edits reverted (not an automated mutation-testing run).
- [x] `hooks.json` + scaffold registration updated; parity test green: hooks.json now references **15** scripts (`test_real_hooks_json_references_fifteen_scripts`), and the separate scaffolded-scripts tuple `verify_install._EXPECTED_HOOK_SCRIPTS` includes `jig-entry-gate.sh`; a scaffolded install ships + registers the hook — validated end-to-end incl. the `_common` import.
- [x] Post-impl review (compliance + craft + frame) — all three **pass**; see `reviews/slice-01-{compliance,craft,frame-critique}.md`.
- [x] Deviation log written; reconciliation review.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Boundary rule (AC3) implemented as specified — NO deviation to carry into 098-02. The bug-arm/slice-arm liveness asymmetry (bug arm uses full OPEN_STATUSES) is recorded as an accepted limit in code and must be mirrored by 098-02.

### Deviation log (after reconciliation)

**1. `subprocess.run` timeouts added (craft review).** `_claim_identifier` (git branch — runs on every edit) and `_git_ignores` (git check-ignore) had no `timeout=`; `except Exception` catches errors but not a *hang*, so a locked index or slow FS could stall the session on every edit. Both now pass `timeout=5`; `TimeoutExpired` is an `Exception`, so the existing handlers still fail open. Pinned by `test_hung_git_times_out_and_still_evaluates` + `test_git_subprocess_calls_pass_a_timeout`.

**2. Testable helper + thin wrapper split (design choice).** All logic lives in `hooks/scripts/lib/entry_gate.py`; `jig-entry-gate.sh` only marshals stdin, prints, and logs — matching the `context_fill.py` / `jig-context-check.sh` pattern. The wrapper adds `../../skills` to `sys.path` so the helper can `from _common import project_layout` (spec AC3 mandates reading the docs base via `project_layout`); the same relative path resolves in both plugin and scaffold layouts (validated end-to-end).

**3. Status sets re-listed for hook self-containment, pinned in sync.** `_SLICE_WORKING_STATUSES` / `_BUG_OPEN_STATUSES` / `_DISABLE_VALUES` are inlined rather than imported (the established hook-self-containment pattern); `ConstantSyncTests` exec the real `workflow.py` / `bug.py` / `parsing.py` and assert equality, so a lifecycle change cannot silently drift them.

**4. Bug-arm liveness span is broader than the slice arm (accepted limit, frame review).** The bug arm uses the full `OPEN_STATUSES` (incl. REPORTED — `pickup` stamps before the first transition — and VERIFIED); the slice arm uses the curated `_CLAIM_WORKING_STATUSES`. Recorded as an accepted limit in code at the `_BUG_OPEN_STATUSES` definition; bounded because 098-04 clears the marker at every terminal state; 098-02 must keep the same span.

**5. Stale DoR corrected (frame review).** The "NOT YET STARTABLE" banner and the ⏳ DoR items for #138 / 098-04 were false by the time of implementation (both merged/DONE); corrected to ✅ with in-tree confirmation, rather than left asserting the slice could not start.

**6. Branch re-home (process note).** The primary working tree was switched off the intended `claude/issue-111-lifecycle-entry-gate` onto a stray `claude/bug-028-scaffold-gitignore-runtime-state` branch mid-session (unrelated to the real concurrent bug-028 session, which runs in its own linked worktree on a differently-named branch). Detected via the reviewers' `claimed_by` mismatch note; the branch was re-homed to `claude/issue-111-…` (commits preserved) and the claim re-stamped on the REVIEWED transition. No work lost. Inherited bug-027/028 WIP was isolated in a tagged stash before any 098 work began.

### Reconciliation sweep

- **`hooks/hooks.json`** — 3rd PostToolUse `Edit|Write|MultiEdit` entry added; mirrored to both host packages. Disposition: **updated**.
- **`scripts/verify_install.py` `_EXPECTED_HOOK_SCRIPTS` + `scripts/test_install_contract.py`** — script registered; hook-count contract test moved 14→15. Disposition: **updated**.
- **`skills/scaffold-init/scaffold.py`** — Codex status-message map gains a friendly `jig-entry-gate.sh` label. Disposition: **updated**.
- **Host packages** — regenerated via `scripts/build_host_packages.py`; `--check` in sync (115 files). Disposition: **updated**.
- **CLAUDE.md hot cache** — the Active-specs line already names spec 098; a one-line hot-cache term for the entry gate will be added at spec close (098-02) via `/jig:memory-sync`, not per-slice. Disposition: **deferred to spec close**.
- **`docs/refinement-todo.md`** — nothing deferred during implementation (the fine-tuning of boundary part (b) is already an ADR-0044 "still open" item, unchanged). Disposition: **no-op**.
- **`docs/architecture.md` host support matrix** — the per-mechanism entry-gate capability row is 098-02's deliverable (AC6). Disposition: **deferred to 098-02**.

### Close-out (post-DONE)
- [x] Dogfood, both directions (real-repo, 2026-08). Silence alone proves nothing
      — a dead gate is silent too (ADR-0044 under-fire kill criterion):
      - [x] a normal in-slice session on this repo produces no false fire — an
            edit to `skills/bug-fix/bug.py` while this checkout holds the live
            claim on 098-01 (REVIEWED) is **silent**; **and**
      - [x] a deliberate out-of-lifecycle edit, on this repo (which carries an
            unrelated `IN_PROGRESS` slice 088-02 and open bug 008), under a
            foreign claim identity, **does** fire the nudge.
      - _Continued real-session dogfooding over time still feeds the 8-week
        under-fire kill criterion; this is the shipping-gate proof, not the end._
