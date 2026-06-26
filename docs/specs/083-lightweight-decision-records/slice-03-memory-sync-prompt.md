---
status: DONE
dependencies: [083-01]
last_verified: 2026-06-25
---

## Slice 083-03 — Memory-sync session-end prompt (OQ1)

**Goal:** `/jig:memory-sync` prompts the writer to record missed non-spec
shipped decisions at session end — the forcing function for out-of-spec work,
which has no reconciliation phase. Conditional, to avoid noise. Resolves OQ1
(yes, prompt conditionally).

**DoR:**
- ✅ OQ1 resolved (maintainer decision, 2026-06-25): yes, conditional prompt.
- ✅ Re-review of 083-01 established that the reconcile-checklist prompt covers
  only the minority case (decisions made during a spec slice); memory-sync is
  the session-end catch for pure out-of-spec sessions.
- ✅ `memory-sync/SKILL.md` candidate-items list and when-to-invoke list are the
  insertion points; no `memory.py` helper is added (the file lives in
  `docs/decisions/`, not `docs/memory/`, and is hand-edited).

**Acceptance Criteria:**

1. **When-to-invoke trigger.** `memory-sync/SKILL.md` lists "session settled a
   non-spec shipped decision" as an invocation trigger, noting it's the forcing
   function for out-of-spec work.
2. **Candidate-item category, conditional.** The "Identify candidate items"
   list gains a "Non-spec shipped decisions" entry that is **explicitly
   conditional** — only surfaced when the session touched UI/product/out-of-spec
   work, skipped for pure backend/refactor/spec sessions (OQ1 noise mitigation).
3. **Destination + hand-edit guidance.** The skill routes the item to
   `docs/decisions/lightweight-decisions.md`, states there is **no `memory.py`
   subcommand** for it, and directs the writer to append via `Edit`/`Write`
   using that file's template — confirming with the user before writing.

---

### Deviation log

_No deviations from acceptance criteria. No `memory.py` change: the destination
file is human-browsable prose in `docs/decisions/`, deliberately outside the
`memory.py`-managed `docs/memory/` tree, so the skill nudges a hand-edit rather
than adding a subcommand. This matches the spec's Assumption that the file needs
no machine-readable structure._

**Accepted craft nit (non-blocking):** the candidate-item enumeration in
SKILL.md ("UI string, visual/CSS choice, translation correction, scoped
brand/icon call") uses the terser README phrasing rather than the live-file's
richer one — same intent; left aligned to the README/SKILL family. The craft
reviewer rated the double-stated conditional (when-to-invoke + candidate list,
each with an explicit "skip for pure backend/refactor/spec sessions" clause) a
strength for over-prompt resistance.

### Reconciliation sweep

| Surface | Status | Notes |
|---|---|---|
| `skills/memory-sync/SKILL.md` | updated | when-to-invoke trigger + conditional candidate category + hand-edit guidance |
| `hosts/` (claude + codex) | updated | committed host packages regenerated (`build_host_packages.py`); claude copy byte-identical, codex copy carries standard host transforms (CLAUDE.md→AGENTS.md, CLAUDE_PLUGIN_ROOT→PLUGIN_ROOT); drift `--check` green |
| `skills/memory-sync/memory.py` | no-op | no subcommand added (file is hand-edited prose) |
| `docs/workflow.md` | no-op | reconcile-checklist prompt (083-01) unchanged; memory-sync is the complementary session-end half |
| `docs/architecture.md` | no-op | no module boundary changed |
