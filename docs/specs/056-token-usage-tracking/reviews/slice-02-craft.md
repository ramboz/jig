---
slice: 056-02 — Subagent accounting (nested transcripts) + orchestrator/subagent split
pass: craft
verdict: pass
reviewer: jig:reviewer (read-only)
reviewed_at: 2026-06-02T18:15:15Z
prompt_source: review.py pr-review docs/specs/056-token-usage-tracking/spec.md 056-02 scripts/usage.py scripts/test_usage.py
---

VERDICT: pass

REASONING:
High-craft, faithful to the measured-from-nested-transcripts design. find_subagent_files derives the nested path + fails soft; sum_subagent_usage sums per-turn, buckets by attributionAgent, tracks per_model, skips usage-less records; _merge_per_model + the shared apply_rates give a defensible combined cost; the 056-01 orchestrator path is untouched (parallel function + regression test). Tests build a real nested subagents/ tree and exercise the split, per-type breakdown, no-subagents, and malformed-skip. Findings are nits only.

SPECIFIC ISSUES:
- [strength] subagent summing folded into the existing attributed-session loop keyed on session_path — clean reuse of the 056-01 seam, no duplication of discovery/attribution.
- [strength] no-subagent -> measured $0.0 (note) vs ccusage-failure -> unavailable is the right distinction, documented inline; combined collapses to orchestrator.
- [strength] one except over derive+apply degrades all three $ dimensions together; missing dir / OSError / malformed JSONL / usage-less records each handled + tested; nothing in the 056-02 path throws.
- [strength] _SubagentTreeMixin states exact sums (DAMP); test_orchestrator_sums_unchanged_by_subagents is a real regression guard.
- [nit] usage.py module docstring ("Cost via ccusage" para) still describes only the single orchestrator $ line; predates the 3-dimension model.
- [nit] test_usage.py module docstring still says "orchestrator-only"; not updated for 056-02.
- [nit] test_subagent_record_missing_usage_skipped tolerates the Explore bucket absent-or-zero; tighten to one branch to document the contract.

RECONCILIATION NOTES: the 2 stale docstrings + the spec.md Goal #2/Design-notes proxy prose are the follow-ups (cheap); none affect behavior.

Provenance: reviewer jig:reviewer (read-only); prompt built by review.py pr-review.
