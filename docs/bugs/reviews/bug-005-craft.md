---
bug: 005
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-11T15:24:24Z
prompt_source: pr-review skill craft pass
---

VERDICT: pass

REASONING:
The rewrite is correct and addresses both failure directions. The regex
`^([-*+]|\d+[.)])\s+\S` matches all Markdown list markers; the indent>=2 (tabs
expanded) cutoff excludes nested confirm/falsify sub-bullets. Helpers are
well-named, comments accurate and proportionate, and it is the simplest change
that works. Tests assert real behavior in both directions. No ReDoS (`\d+[.)]`
is linear). Existing diagnose-gate tests still pass (explicit fixtures, not the
template).

SPECIFIC ISSUES:
- skills/bug-fix/bug.py — template pre-satisfies the anti-anchoring shape gate by
  default; evidence gap still trips. Intentional per "teach by example."
- skills/bug-fix/bug.py — indent>=2 cutoff excludes 2-3 space top-level items;
  acceptable pragmatic tradeoff.
- skills/bug-fix/bug.py — `Leading:` regex runs over full section text while
  `[x]`/`(leading)` check top-level items only; harmless asymmetry.

RECONCILIATION NOTES:
- `_section` exact-match heading fragility deliberately scoped out; logged as a
  deferred item, not a regression.
- Diagnose gate remains shape-only; evidence check is the only part an unedited
  scaffold still trips.
