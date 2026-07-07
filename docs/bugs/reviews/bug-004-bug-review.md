---
bug: 004
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-07T05:03:53Z
prompt_source: review.py bug-review docs/bugs/004-terminal-status-legibility.md skills/bug-fix/{bug.py,SKILL.md,test_bug.py}
---

VERDICT: pass

REASONING:
The fix addresses the documented root cause — a flat renderer with no terminal
segregation plus a missing Gotchas invariant — rather than masking the symptom.
`_render_board` splits active vs. `TERMINAL_NON_DONE_STATUSES` rows, keeps DONE
in the active table (terminal-success), fully omits the `## Terminal` section
when empty, and preserves the same 10-column shape so `_parse_existing_notes`
keeps working; the SKILL.md Gotchas bullet encodes the standing invariant. The
named regression test asserts `## Terminal` presence, which is absent on trunk
(flat single table) — genuinely red-before / green-after, with
`red_confirmed_at` machine-stamped by the FIXING gate. Stays within
`fix_class: observability` with no unrelated behavior changes.

SPECIFIC ISSUES:
(none blocking)
- Verified safe: `_parse_existing_notes` requires a leading `| \d{3} |`, so the
  blockquote, second header row, and separators cannot mis-match; and
  `regenerate_status_board`'s `existing.find("| ID |")` anchors on the first
  (active) header, so the terminal section is regenerated fresh, never absorbed
  into the preamble or duplicated.

RECONCILIATION NOTES:
- Minor prose/code drift: the record's Fix section describes the set as a plain
  `{...}` set literal; the implementation uses `frozenset({...})` — a
  strengthening (immutability), not a behavioral deviation. Worth a one-line
  deviation-log note.
- `## Proof` / `## Learning` empty — expected; filled before `→ DONE` (standard
  tier skips VERIFIED).
