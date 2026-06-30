---
slice: 084-02 — Route read/write helpers through the layout helper
pass: arch
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T05:00:29Z
prompt_source: review.py arch (084-02); jig:reviewer subagent
---

VERDICT: pass

Module-boundary shape is sound. project_layout imports only stdlib, so the new
_common → _common edges (team_signal → project_layout) cannot form a cycle (both
targets are import sinks). Both discovery consumers genuinely delegate to the
single project_root_for resolver rather than re-implementing the sentinel walk,
with legacy depth/marker logic isolated inside per-caller fallback closures. The
per-call scaffold.json reads are O(1) per command (dirs computed once before
iteration, not per-spec) — memoization is unnecessary and was deliberately NOT
added (per-call freshness is a feature for long-lived processes).

Leaf discipline holds; single-resolver invariant (ADR-0033 §5a) honored across all
workflow discovery sites + review._find_project_root; the only bare parents[3]
remaining is inside the _legacy fallback closure. Exclusions confirmed correct
(migrate.py pre-sentinel; review_evidence file-relative; push-mode wt/docs
allowlisted). Default-layout behavior unchanged (no scaffold.json → project_root_for
fallback; jig's own repo).

Rule-of-three watch item (not actionable now): lexicon._memory_dir is a sanctioned
stdlib-only mirror of project_layout's docs_root resolution. If a THIRD hook-safe
consumer appears, extract a stdlib-only `docs_root_relaxed()` (importable-by-path,
no package) into project_layout.
