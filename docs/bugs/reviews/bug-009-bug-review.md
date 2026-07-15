---
bug: 009
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-15T00:44:32Z
prompt_source: review.py bug-review docs/bugs/009-codex-skill-description-limit.md <deliverables>
---

The fix enforces Codex's sanitized 1024-character description limit in the
shared install contract, shortens all six affected canonical descriptions,
and regenerates both host packages. Boundary tests credibly witness 1025 red
before the guard and now pin folded 1024 acceptance plus whitespace-normalized
1025 rejection. Scope and guardrail classification are appropriate; no issues.
