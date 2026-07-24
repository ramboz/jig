---
status: DRAFT
dependencies: [adr-0039]
last_verified: 2026-07-24
frame_review: true
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about runnable
     surfaces by probe first (run it / read source) or a citation, else mark them
     as assumptions — never assert an unverified claim as fact. -->

## Slice 096-01 — entry-gate nudge

**Goal:** An edit to project source made while the session is **not** inside the
lifecycle produces one agent-facing `additionalContext` nudge — "this edit is
outside jig; route it (claim a slice / open a bug) or record it" — and nothing
else. No block, no owner prompt, no failure mode for the session.

**Blocked-on:** [ADR-0039](../../decisions/adr-0039-lifecycle-entry-gate.md) must
be **Accepted**, and the four open questions in the spec answered, before this
slice leaves DRAFT. The acceptance criteria below are written against ADR-0039's
*recommended* answers.

**DoR:**
- ✅ Field evidence is counted: [#111](https://github.com/ramboz/jig/issues/111)
  records 11 out-of-lifecycle edit incidents (20 Jun – 16 Jul 2026).
- ✅ The co-location target exists: `hooks/hooks.json` has a `PostToolUse` /
  `Edit|Write|MultiEdit` matcher already running `jig-post-edit-verify.sh` and
  `jig-boundary-change-warn.sh`.
- ✅ The nudge/trace path exists:
  `lib/read_attribution.append_additional_context_event`.
- ✅ The anti-nag mechanism exists: `jig-context-check.sh` once-per-band-per-session
  `$TMPDIR` state file.
- ✅ Lifecycle-state sources exist: `claimed_by` in slice frontmatter (spec 049);
  bug records in `docs/bugs/*.md` (bug-fix `bug.py`).

**Acceptance criteria:**

1. **Trigger.** A new hook `hooks/scripts/jig-entry-gate.sh` fires on
   `PostToolUse` / `Edit|Write|MultiEdit`, co-located in the existing matcher
   (third entry after `jig-post-edit-verify.sh`, `jig-boundary-change-warn.sh`).
2. **In-lifecycle detection (coarse).** The hook treats the session as *inside*
   the lifecycle when a locally-claimed `IN_PROGRESS` slice **or** an active bug
   record is present; in that case it stays silent. (Strictness is open question
   #1 — coarse is the recommended answer.)
3. **Source boundary.** The hook nudges only for edits to *project source* — not
   for edits to lifecycle artifacts. The starting rule (open question #3): skip
   any path under the configured `docs_root`, `.jig/`, `.claude/`, or `.git/`;
   everything else is source. The docs root is read via
   `_common/project_layout.py`, so a `.`-rooted / relocated docs layout
   ([ADR-0033](../../decisions/adr-0033-configurable-docs-root.md)) never trips
   the gate.
4. **The nudge.** On an out-of-lifecycle source edit, emit `additionalContext`
   naming the edited file and the two ways out — route it (claim a slice / open a
   bug) or record it — and stating it is informational, not a gate. Mirror the
   `jig-boundary-change-warn` message shape.
5. **Cadence.** Fire at most once per session, re-armed when lifecycle state
   changes, via a `$TMPDIR` per-session state file (open question #2 — recommended
   answer).
6. **No owner friction.** Never sets `continue: false`; never blocks; emits no
   dialog. Always exits 0.
7. **Opt-out.** `JIG_ENTRY_GATE=0` (widened token set `{0,false,off,no}`, matching
   `jig-boundary-change-warn`) disables the hook.
8. **Fail-open.** `except Exception: pass` around all logic; any error leaves the
   session untouched (ADR-0039 / #111 constraint #3).
9. **Auditable.** A fire logs via `append_additional_context_event` (hook name
   `jig-entry-gate`, event kind e.g. `out_of_lifecycle_edit`).
10. **Scaffold-mode parity.** Register the script in
    `skills/scaffold-init/scaffold.py` `_EXPECTED_HOOK_SCRIPTS` and the
    `hooks.json` writer, so a scaffolded install ships the gate too.

**Tests first (TDD):**
- out-of-lifecycle edit to a source file → nudge emitted once.
- edit while a claimed `IN_PROGRESS` slice / active bug exists → silent.
- edit to a path under `docs_root` / `.jig` / `.claude` / `.git` → silent
  (including a relocated docs root).
- second out-of-lifecycle source edit same session, state unchanged → silent
  (cadence).
- `JIG_ENTRY_GATE=0` → silent.
- malformed stdin / missing `file_path` / unreadable state → exits 0, no output
  (fail-open).
- scaffold parity: `_EXPECTED_HOOK_SCRIPTS` lists the new script.

**DoD:**
- [ ] All acceptance criteria met, tests green (red→green witnessed).
- [ ] `hooks.json` + scaffold writer updated; parity test green.
- [ ] Post-impl review (compliance + craft; +frame per frontmatter).
- [ ] Deviation log written; reconciliation review.

### Close-out (post-DONE)
- [ ] Dogfood: confirm the gate stays silent across a normal in-slice jig session
      on this repo (no false fire on lifecycle-artifact edits).
