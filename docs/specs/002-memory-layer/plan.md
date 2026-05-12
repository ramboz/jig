# Plan: Slice 002-02 — lookup-pattern

## Approach

Two parts:

1. **Helper-side**: Add a `lookup` command to `memory.py` that searches the hot cache and glossary (in that order) and reports the result. This gives Claude a deterministic primitive for the read side of the pattern, mirroring `add-term` on the write side.

2. **SKILL.md-side**: Update `skills/memory-sync/SKILL.md` to teach Claude the full lookup flow: when an unknown capitalized reference appears in the conversation, look it up; if missing, ask the user once; then persist.

The "ask the user" step is pure SKILL.md instruction — there is no code primitive for it. The "≥3 references" promotion threshold (AC #4) continues to live in Claude's judgment (consistent with slice 002-01).

## `lookup` command shape

```bash
python3 memory.py lookup <term> <target>
```

Search order: CLAUDE.md Hot Cache → Key terms → docs/memory/glossary.md.
Exit codes:
- `0` — found; definition printed to stdout, source (hot-cache|glossary) on a second line
- `2` — not found; nothing on stdout, brief explanation on stderr

This is a tri-output-form: success/failure via exit code, content via stdout, diagnostic via stderr. Composable for SKILL.md invocation.

Edge cases:
- Term matched case-insensitively (so "Spidr" finds "SPIDR")
- If a term appears in BOTH hot cache and glossary, return the hot-cache hit (more authoritative)
- If neither file exists, treat as "not found" (no error)

## AC #6 interpretation

The literal AC says: "Persistence decision is logged (one-liner) to `docs/memory/learnings.md`."

This is awkwardly worded — `learnings.md` is for "dead ends and gotchas" (per its own template), not a persistence audit log. Routine glossary adds would bloat it with non-learnings content.

**Interpretation:** The helper's existing stdout output ("glossary: added 'X'", "hot cache: promoted 'Y'") IS the persistence-decision log. It's a one-liner per decision, surfaced to the caller (Claude), and captured in `skill-usage.jsonl` via the telemetry hook when invoked through Task. No additional file write needed.

Documented as a deviation. If a stronger audit trail is needed later, a separate `docs/memory/.audit.log` (gitignored) is cleaner than polluting learnings.md.

## Files to modify

| Path | Change |
|---|---|
| `skills/memory-sync/memory.py` | Add `lookup` subcommand + parser entry |
| `skills/memory-sync/test_memory.py` | New `LookupTests` class |
| `skills/memory-sync/SKILL.md` | New "Lookup-pattern flow" section |
| `docs/specs/002-memory-layer/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Status update |

## Test strategy

`LookupTests`:
- `test_lookup_finds_glossary_term`
- `test_lookup_finds_hot_cache_term`
- `test_lookup_hot_cache_wins_when_both`
- `test_lookup_returns_2_for_unknown`
- `test_lookup_case_insensitive`
- `test_lookup_on_bare_dir_returns_2` (no CLAUDE.md, no glossary → graceful "not found")
- `test_lookup_after_add_term_round_trip` — AC #5

## Out of scope

- Auto-trigger via `jig-memory-scan` UserPromptSubmit hook → slice 002-03
- Caching lookup results across invocations → not needed; reads are cheap
- Fuzzy matching beyond case-insensitivity → out of scope
