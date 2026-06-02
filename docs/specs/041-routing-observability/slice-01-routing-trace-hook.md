---
status: DONE
dependencies: []
last_verified: 2026-06-02
---

## Slice 041-01 — routing-trace-hook

**Goal:** A `PreToolUse`/`Skill` hook records every Skill-tool invocation
(including auto-triggered ones) to `.claude/skill-usage.jsonl`, capturing the
chosen skill name verbatim — so a reader can later tell whether jig's baseline
(`jig:pr-review`) or a richer user-installed skill (`pr-review`) actually fired.

> **Record note (closed retroactively).** This slice shipped *ahead of* its
> formal lifecycle transitions (committed in `734e424`, alongside the spec
> 053 craft-pass work) and was **not** independently reviewed. It is recorded
> here as an honest closed record per the spec 041 reconciliation note and
> ADR-0010 (inline correction on a still-open spec). See the deviation log
> for what diverged from the drafted plan and why the review boxes are
> unticked. — 2026-06-02

**DoR:**
- ✅ `PreToolUse`/`Skill` events are routable to a hook and the payload
  carries `tool_input.skill_name` (this spec's open Q1 — verified during
  implementation).
- ✅ `hooks/hooks.json` + `hooks/scripts/jig-telemetry.sh` exist (the shared
  `.claude/skill-usage.jsonl` log surface already established).

**Acceptance Criteria:**

1. **Logs Skill invocations.** A new `hooks/scripts/jig-skill-trace.sh`
   appends one JSONL entry per Skill-tool invocation to
   `.claude/skill-usage.jsonl` with `event: "skill_invoked"`, `skill_name`,
   `tool_name`, `session_id`, and an ISO-8601 `timestamp`.
2. **Records scope verbatim.** Plugin-scoped names are recorded as-is
   (`jig:pr-review`) and distinguishable from the bare richer-skill name
   (`pr-review`) — this distinction is the whole point.
3. **Appends, shares the file.** Entries append (never overwrite) and coexist
   with `jig-telemetry.sh`'s `Task`-spawn rows in the same file; readers
   filter `event == "skill_invoked"`.
4. **Fail-open.** Missing `tool_input` → empty `skill_name`; malformed/empty
   stdin → no crash, exit 0; `.claude/` is created if absent. The hook never
   blocks a tool call.
5. **Registered.** `hooks/hooks.json` registers the script under a
   `PreToolUse`/`Skill` matcher, `async`, with a timeout.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one fixture
      (`hooks/scripts/test_jig_skill_trace.py` — 7 tests, one per behaviour
      incl. malformed/empty/missing-input edges).
- [ ] Reviewed by `reviewer` subagent — **not performed** (shipped ahead of
      formal slicing; see deviation log §3).
- [ ] Implementation review passed — **not performed** (see §3).
- [x] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed — **not performed** (see §3).
- [x] `docs/refinement-todo.md` updated — handled at spec close (slice 041-02):
      both "Skill telemetry granularity" and "Skill-routing observability"
      entries are resolved together.

**Anti-horizontal-phasing check:** End-to-end value: after this slice, a user
can read `.claude/skill-usage.jsonl` and see *which skill the router actually
picked* for any auto-triggered or main-agent Skill invocation — the routing
that was previously unobservable by construction (spec 041 Overview).

### Deviation log (after reconciliation)

The original drafted plan (spec 041 Goal 1 / slice list) is preserved above.
Implementation notes:

**§1 — Shipped as a NEW hook on `PreToolUse`/`Skill`, not as an extension of
`jig-telemetry.sh` on `UserPromptSubmit`.** This crosses the spec's "No new
hook events" non-goal. Rationale (also recorded in the spec.md reconciliation
note): `PreToolUse`/`Skill` carries `tool_input.skill_name` and captures
*implicit* (auto-triggered) routing — the actual question this spec asks —
which `UserPromptSubmit` cannot. The drafted `UserPromptSubmit` approach would
have seen only explicit `/jig:` slash commands. Verifying that `Skill` events
are routable resolved this spec's open Q1.

**§2 — Shared-file contract.** The hook writes to the same
`.claude/skill-usage.jsonl` as `jig-telemetry.sh`. To keep the two sources
disambiguable, skill-trace rows carry `event: "skill_invoked"` and `Task`
rows do not. Every reader (the verification doc's recipe and the slice 041-02
`routing-stats` helper) MUST filter on that field. `tool_input.skill_name` is
an *observed* payload field, not a documented upstream contract — the hook
logs an empty name rather than crashing if upstream renames it (pinned by
`test_missing_tool_input_is_graceful`).

**§3 — Not independently reviewed.** Per the spec 041 close-out decision, this
already-shipped, already-committed work is recorded as a closed record rather
than retro-fitted with fabricated review evidence. Its acceptance rests on the
7 committed tests in `test_jig_skill_trace.py` (all green in the full suite)
and its in-session use. The three review-pass DoD boxes are deliberately left
unticked to keep the record honest (ADR-0014's evidence gate is about *real*
verdicts; manufacturing them after the fact would defeat it).
