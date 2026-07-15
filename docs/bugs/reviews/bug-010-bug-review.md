---
bug: 010
pass: bug-review
verdict: pass
reviewer: reviewer-subagent
reviewed_at: 2026-07-15T01:04:28Z
prompt_source: review.py bug-review docs/bugs/010-node-default-discovery.md
---

The fix addresses the documented root cause by preserving whether the path was
explicitly supplied and allowing Node's cwd-based discovery only for default
runs. The named regression would fail against the prior unconditional path
append and passes now; explicit paths and file/name selectors remain covered,
host payloads match the canonical implementation, and the `local_patch` scope
is honest. No reconciliation changes are needed.
