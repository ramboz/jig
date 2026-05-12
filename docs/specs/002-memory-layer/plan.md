# Plan: Slice 002-01 — explicit-sync

## Approach

memory-sync is fundamentally an LLM-driven skill: Claude reads session context, decides what's worth persisting, and calls a small deterministic helper to do the actual file I/O.

**Split of responsibility:**
- **`skills/memory-sync/SKILL.md`** — instructs Claude on when to invoke and what to consider
- **`skills/memory-sync/memory.py`** — the deterministic helper that handles file IO, idempotency, and self-healing

This mirrors the scaffold-init split (LLM layer = SKILL.md; deterministic core = .py).

## Helper CLI surface

```bash
python3 memory.py <command> [args] <target-dir>

# Commands:
add-term <term> <definition> [--category=glossary]
add-learning <title> [--body=<text>]   # body via flag or stdin if omitted
add-inbox <item-text>
promote <term> <definition>             # term → CLAUDE.md Hot Cache
summary                                  # report counts of memory files for the session
```

The helper is **idempotent**: invoking `add-term FOO bar` twice does not double-write. Idempotency is detected by exact-string-presence-of-key-marker (`## FOO` for glossary, etc.).

## Self-healing

If `docs/memory/` or `docs/inbox.md` don't exist, the helper creates them from the scaffold-init templates at `${CLAUDE_PLUGIN_ROOT}/templates/docs/memory/` (matching the format the wizard would produce). This satisfies the DoR clause "self-healing, not a manual prereq."

If `CLAUDE.md` doesn't exist (pre-scaffold-init projects), `promote` writes to `docs/memory/glossary.md` as fallback and warns on stderr.

## Files to create

| Path | Purpose |
|---|---|
| `skills/memory-sync/memory.py` | The helper script |
| `skills/memory-sync/test_memory.py` | Unit tests |

## Files to modify

| Path | Change |
|---|---|
| `skills/memory-sync/SKILL.md` | Add invocation instructions and judgment guidance |
| `docs/specs/002-memory-layer/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Status update |

## Judgment guidance for SKILL.md

When `/jig:memory-sync` is invoked (or auto-triggered on phrases like "remember this", "add to glossary"), Claude:

1. Identifies candidate items from the session: new domain terms, dead-end learnings, parked ideas, frequently-referenced terms.
2. Decides per item: glossary (niche term), learnings (failed approach), inbox (unresolved), hot cache (≥3 session references).
3. Calls `memory.py` once per item with the right command.
4. Reports a summary at the end: "Added X to glossary; logged Y to learnings; parked Z to inbox; promoted W to hot cache."

The "≥3 session references" rule (AC #4) is **Claude's judgment**, not a counter the helper tracks. The session is short-lived enough that explicit counting is overkill.

## Test strategy

`MemoryHelperTests`:
- `test_add_term_appends_to_glossary` — fresh scaffold, invoke once, check file
- `test_add_term_idempotent` — invoke twice, verify single entry
- `test_add_learning_appends_with_body_flag`
- `test_add_learning_via_stdin` — pipe body via stdin
- `test_add_inbox_dates_entry` — verify `[YYYY-MM-DD]` prefix
- `test_promote_writes_to_hot_cache` — verify CLAUDE.md Hot Cache → Key terms gains the line
- `test_promote_idempotent` — same term twice → one entry
- `test_summary_lists_counts`

`SelfHealingTests`:
- `test_creates_memory_dir_if_missing` — invoke against bare dir, verify dir + files created
- `test_creates_inbox_md_if_missing` — verify inbox.md materialized
- `test_promote_warns_when_no_claude_md` — non-scaffolded target

## Out of scope

- Auto-trigger on session Stop (002-03)
- Reading from memory (lookup pattern — slice 002-02)
- Reconciliation integration (002-04)
- A literal `≥3 references` counter in the helper (Claude makes this call)
