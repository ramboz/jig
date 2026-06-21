---
slice: 077-01 — pyright advisory probe
pass: reconciliation
verdict: pass
reviewer: main-session-fallback-reconciliation
reviewed_at: 2026-06-21T17:30:57Z
prompt_source: review.py reconciliation docs/specs/077-type-check-floor/spec.md 077-01
---

Reconciliation pass: the deviation log is faithful and scope-appropriate.

The implementation claims match the diff: pyright is an AdvisoryProbe in the Python ecosystem list; resolver order is PATH, uvx, pipx; summary is tight; advisory execution cannot change cmd_check primary-linter exit mapping; SKILL.md and ADR-0017 were updated rather than creating a new ADR.
The DoD updates are honest: full suite and focused tests passed; docs/refinement-todo is N/A because no decisions were deferred; the review-flow note explicitly records the main-session fallback instead of pretending a subagent ran.
No unrelated docs, architecture, conventions, or inbox changes are required. Coverage check was a documented no-op because docs/product-vision.md has no use-case breadth layer.
