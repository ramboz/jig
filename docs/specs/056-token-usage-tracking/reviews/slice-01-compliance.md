---
slice: 056-01 — On-demand per-spec orchestrator usage report (MVP)
pass: compliance
verdict: pass
reviewer: jig:reviewer (read-only)
reviewed_at: 2026-06-02T17:09:36Z
prompt_source: review.py implementation docs/specs/056-token-usage-tracking/spec.md 056-01 scripts/usage.py scripts/test_usage.py
---

VERDICT: pass

REASONING:
All five ACs met by scripts/usage.py + scripts/test_usage.py. `report <spec>` locates sessions by encoded-cwd prefix spanning worktrees (--projects-dir override) + content attribution; sums the four orchestrator message.usage fields + total (scoped to assistant turns, excluding subagent toolUseResult); $ via ccusage per-model effective rate applied to attributed token sums (not hard-coded) + graceful degradation; stdout-only/read-only (proven by a size/mtime tree-snapshot test); honest framing (estimate; orchestrator-only). Tests auto-discovered by run_tests.py; hermetic (git/network seams injected).

SPECIFIC ISSUES:
- [medium] usage.py run_ccusage_npx invokes `npx ccusage@latest` with check=True and no timeout=. A network stall during package fetch would hang `report` indefinitely (the degradation path catches errors, not hangs). A modest timeout would make the degrade-gracefully promise (AC #3) hold under a hung network too.
- [low] the tool_use / tool_result branches of _record_texts (attribution mention-counting) are not exercised by any fixture (all test transcripts use plain text). Real transcripts carry spec paths in Read/Grep tool calls — worth a fixture mentioning a spec only inside a tool_use input / tool_result.

RECONCILIATION NOTES:
- --main-root and --ccusage-json are seams beyond the literal ACs (which imply only --projects-dir); reasonable testability/offline seams, documented — note in the deviation log.
- Attribution is the content heuristic (dominant spec-path mention); can mis-attribute a session that reads many other specs' files — an MVP limitation per the spec design-notes, surfaced in the output, replaced by 056-03's .jig/spec-ref.

Provenance: reviewer jig:reviewer (read-only); prompt built by review.py implementation.
