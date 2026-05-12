---
name: memory-sync
description: >
  Persist new context, terms, learnings, and project knowledge to the memory layer
  (CLAUDE.md hot cache, docs/memory/, docs/inbox.md). Use when the user says remember
  this, save this for later, add to glossary, note this down, or at the end of a
  session to consolidate what was learned. Also auto-fires at session end to surface
  capture-worthy items. Do not use for updating specs, ADRs, or code comments —
  those have their own workflows.
user-invocable: true
---

> Slice 002-01 (explicit-sync) is implemented: helper script + invocation flow.
> Slices 002-02 (lookup-pattern), 002-03 (auto-detect-hooks), 002-04
> (reconciliation-integration) are pending.

## What this skill does

Persists session-derived context to the memory layer via a deterministic helper.
Claude makes the *what / where* decisions; `memory.py` does the file I/O,
idempotency, and self-healing of missing memory structure.

## When to invoke

- User says "remember this", "save this for later", "add this to the glossary",
  "note this down", or similar.
- User explicitly invokes `/jig:memory-sync`.
- Session-end consolidation (after slice 002-03 auto-trigger ships).

## How to use

1. **Identify candidate items** from the recent session:
   - **New domain terms** — anything the user defined or that needed explaining.
   - **Learnings** — failed approaches, dead ends, "we tried X" gotchas.
   - **Parked ideas** — things mentioned but not yet decided on.
   - **Frequently-referenced terms** — anything used ≥3 times this session.
2. **Decide per item** which file it belongs in:
   - Niche/domain term → glossary
   - Failed approach / gotcha → learnings
   - Unresolved/unfinished thought → inbox
   - High-frequency term → hot cache (in CLAUDE.md)
3. **Invoke `memory.py` once per item** with the right command. **Always quote
   the term/definition/body arguments** — terms may contain spaces, definitions
   often contain punctuation:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/memory-sync/memory.py" add-term "<name>" "<definition>" "<target>"
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/memory-sync/memory.py" add-learning "<title>" --body "<text>" "<target>"
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/memory-sync/memory.py" add-inbox "<text>" "<target>"
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/memory-sync/memory.py" promote "<term>" "<definition>" "<target>"
   ```
   Where `<target>` is the project root (usually `.`).
4. **Report a summary** at the end:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/memory-sync/memory.py" summary <target>
   ```

## Judgment guidance

- **Don't over-persist.** Persisting trivia bloats memory files. If you wouldn't
  want to read it back in a future session, don't write it.
- **"≥3 references" is your judgment.** The helper does not track session counts —
  you decide when a term has been used enough to deserve hot-cache promotion.
- **Inbox > glossary** when in doubt. An inbox entry can be promoted later; a
  premature glossary entry pollutes the searchable terminology.
- **The reviewer subagent cannot run this skill.** Reviewers read from memory but
  must not write — defining the glossary is not the reviewer's job (see
  `agents/reviewer.md`).

## Self-healing

If `docs/memory/` or `docs/inbox.md` don't exist (pre-scaffold-init project),
the helper creates them. If `CLAUDE.md` is absent, `promote` falls back to
`add-term` (writes to glossary) and warns on stderr. The skill works on
unscaffolded projects, though scaffold-init is the recommended setup.

## Gotchas

- `add-term` and `add-learning` are idempotent on the exact heading text. Re-running
  with the same `term`/`title` is a no-op. To genuinely update an existing entry,
  edit the file by hand or use Edit.
- `add-inbox` is NOT idempotent — it always appends. The inbox is a stream; near-
  duplicates are tolerated and triaged later.
- `promote` is idempotent on a line-anchored `- **<term>**` match. If a term is
  in the Key terms list with a slightly different label or hyphenation, it counts
  as new.
- `promote` inserts new bullets immediately after the `### Key terms` heading
  (LIFO — newest first). This is intentional: the most recently promoted term is
  the most likely to be referenced in the next session. If alphabetical or
  chronological order is preferred later, this is a design point worth revisiting.
- Definitions are stored as-is; markdown is allowed but be conservative — these
  files are scanned by humans more often than parsed.
