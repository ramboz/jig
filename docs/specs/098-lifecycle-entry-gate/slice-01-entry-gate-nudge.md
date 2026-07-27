---
status: DRAFT
dependencies: [adr-0040]
last_verified: 2026-07-27
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

**BLOCKED — do not implement.** AC2 below has no valid definition yet. Two
adversarial rounds falsified two successive readings of "inside the lifecycle"
(see the spec's settled call #1 and
[ADR-0040 open question #5](../../decisions/adr-0040-lifecycle-entry-gate.md#open-question-5-there-is-no-inside-the-lifecycle-signal-yet)).
Everything else in this slice is ready; AC2 is load-bearing for all of it.

**DoR:**
- ❌ [ADR-0040](../../decisions/adr-0040-lifecycle-entry-gate.md) is **Proposed**,
  not Accepted — it fails its own frame-critique gate, correctly.
- ❌ Open question #5 (what signal means "inside the lifecycle") is unanswered.
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
- ❌ **Lifecycle-state sources are NOT sufficient.** `claimed_by` (spec 049) and
  `docs/bugs/*.md` exist and are readable, but neither answers "is *this session*
  inside the lifecycle" — the claim is cleared at REVIEWED before reconciliation
  runs, and a `--push` bug reservation leaves nothing in the working tree. This
  DoR item was ✅ in the draft and is the reason AC2 is blocked.
- ✅ The `.gitignore` oracle is probed, and its gap is measured: `git check-ignore`
  excludes `.claude/settings.local.json` but **not** `docs/specs/README.md` or
  `.claude/` (probe recorded in the spec's Assumptions) — which is why AC3 is
  two-part.

**Acceptance criteria:**

1. **Trigger.** A new hook `hooks/scripts/jig-entry-gate.sh` fires on
   `PostToolUse` / `Edit|Write|MultiEdit`, co-located in the existing matcher
   (third entry after `jig-post-edit-verify.sh`, `jig-boundary-change-warn.sh`).
2. 🚧 **In-lifecycle detection — BLOCKED on open question #5.** Settled: the
   check is *coarse* (it never asks whether the edited file belongs to the
   claimed slice's surface). Unsettled: what it reads. Two candidate rules are
   already falsified — record-presence (silent forever) and live-claim-in-this-
   tree (fires every slice during reconciliation, blind to bug fixes). Whatever
   the maintainer chooses must satisfy, at minimum:
   - silent through **reconciliation**, which runs *after* the claim is cleared
     at REVIEWED (`_CLAIM_CLEARING_STATUSES`) and touches `architecture.md` /
     `CLAUDE.md` / `roadmap.md`;
   - silent during a **bug fix** opened the prescribed way, including after
     `new_bug(push=True)` puts the record on `origin/main` and nothing locally;
   - **fires** on a tree with unrelated open work and no live claim (the
     falsifying case that killed rule 1);
   - no dependence on an "operator identity" — `_claim_identifier` returns a
     branch name, and spec 049's stated non-goal is human-identity inference.
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
   session untouched (ADR-0040 / #111 constraint #3).
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
- edit while this session is legitimately inside the lifecycle → silent
  (mechanism per open question #5).
- **anti-false-fire #1:** edit to `architecture.md` / `CLAUDE.md` during
  **reconciliation**, i.e. after the slice reached REVIEWED and the claim was
  cleared → silent. (The live-claim rule failed exactly here.)
- **anti-false-fire #2:** source edit during a bug fix opened with
  `new_bug(push=True)`, where the record is on `origin/main` and the working
  tree has neither a local bug record nor `.jig/spec-ref` → silent.
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
  globally via the shared `'default'` key (`jig-context-check.sh`). Probe the
  real payload before implementing AC5.
- scaffold parity: `_EXPECTED_HOOK_SCRIPTS` lists the new script.

**DoD:**
- [ ] All acceptance criteria met, tests green (red→green witnessed).
- [ ] `hooks.json` + scaffold writer updated; parity test green.
- [ ] Post-impl review (compliance + craft; +frame per frontmatter).
- [ ] Deviation log written; reconciliation review.
- [ ] Any deviation from the boundary rule (AC3) is carried into slice 098-02, so
      the two hosts cannot drift apart at implementation time.

### Close-out (post-DONE)
- [ ] Dogfood, both directions. Silence alone proves nothing — a dead gate is
      silent too (ADR-0040 under-fire kill criterion):
      - [ ] a normal in-slice jig session on this repo produces no false fire; **and**
      - [ ] a deliberate out-of-lifecycle edit, made on a tree that has an
            unrelated `IN_PROGRESS` slice and an open bug, **does** fire.
