---
slice: 080-04 - usage attribution digest
pass: craft
verdict: pass
reviewer: jig-reviewer
reviewed_at: 2026-06-22T01:37:34Z
prompt_source: "'review.py pr-review docs/specs/080-semantic-index-auto-activation/spec.md 080-04 scripts/usage.py scripts/test_usage.py docs/specs/080-semantic-index-auto-activation/plan.md docs/specs/080-semantic-index-auto-activation/tasks.md'"
---

VERDICT: pass

REASONING:
The change is tightly scoped to usage.py plus focused tests/docs for the semantic-index digest. The implementation follows the existing read-only, fail-soft JSONL parsing style, keeps activation telemetry separate from transcript/read proxies, and tests the meaningful craft risks: malformed input, time windows, provider/profile bucketing, CLI overrides, and content leakage.

SPECIFIC ISSUES:
- [strength] scripts/usage.py:1427 — Digest docstring explicitly preserves the no row-level join boundary for activation telemetry vs. transcript/read proxies.
- [strength] scripts/usage.py:1900 — Renderer keeps output metadata-only and limits rows without exposing queries, file bodies, provider output, or read paths.
- [strength] scripts/test_usage.py:1506 — Synthetic fixtures exercise mixed providers/hosts/profiles, malformed rows, filtered rows, proxy counts, and empty transcript handling without requiring external providers.
- [strength] scripts/test_usage.py:1554 — Explicit content-leakage regression assertions cover search queries, read paths, and diff-like file names.

RECONCILIATION NOTES:
No blockers or nits from the craft pass. Strengths worth logging: scoped read-only integration, explicit aggregate-only framing, and fixture-friendly coverage of privacy and robustness paths.
