---
slice: 056-01 — On-demand per-spec orchestrator usage report (MVP)
pass: craft
verdict: pass
reviewer: jig:reviewer (read-only)
reviewed_at: 2026-06-02T17:09:36Z
prompt_source: review.py pr-review docs/specs/056-token-usage-tracking/spec.md 056-01 scripts/usage.py scripts/test_usage.py
---

VERDICT: pass

REASONING:
High-craft, within orchestrator-only scope. Validated against real transcripts: the non-recursive child.glob("*.jsonl") captures top-level orchestrator session files and excludes nested <session>/subagents/agent-*.jsonl (subagent turns, isSidechain:true, carrying their own usage) — so the orchestrator-only sum is genuinely orchestrator-only. Anchored attribution patterns resist date/version false positives; every external boundary fails soft / never throws; the testability seams let the suite run offline. Gaps are test-coverage edges, not defects.

SPECIFIC ISSUES:
- [strength] find_sessions non-recursive glob excludes subagent transcripts -> enforces the orchestrator-only contract given the real on-disk layout. The right seam for 056-02 to extend.
- [strength] anchored attribution patterns (specs/NNN-, \b(\d{3})-\d{2}\b, \bspec\s+NNN\b) resist false positives; deterministic lowest-number tie-break.
- [strength] ccusage failure wrapped in except Exception over derive+apply -> missing npx / non-zero exit / bad JSON / missing-or-malformed --ccusage-json all degrade to a labeled "unavailable" with tokens intact.
- [nit] the partial-rate branch (some attributed models priced, some not -> "partial: no rate for ..." note) is untested — all fixtures use a single model. A two-model fixture would close it.
- [nit] no test asserts the --ccusage-json missing/garbage-file degradation via the _from_file seam specifically (the generic raising-runner test covers the raise path in principle).
- [nit] minor polish: sum_usage admits typeless records (harmless); zero-session render f-strings have no interpolation.

RECONCILIATION NOTES:
- Validated invariant for the 056-02 handoff: subagent turns live in ~/.claude/projects/<encoded-cwd>/<session-uuid>/subagents/agent-*.jsonl (nested, isSidechain:true, full per-turn usage); the orchestrator session is the flat <session-uuid>.jsonl. 056-01's non-recursive glob keeps them apart; 056-02 should read those nested transcripts for accurate subagent usage rather than the lossy toolUseResult proxy the spec currently describes.
- The two test-coverage nits + the timeout are cheap follow-ups for reconciliation.

Provenance: reviewer jig:reviewer (read-only); prompt built by review.py pr-review.
