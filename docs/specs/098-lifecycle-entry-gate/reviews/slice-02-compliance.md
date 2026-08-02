---
slice: 098-02 — Codex host parity
pass: compliance
verdict: pass
reviewer: reviewer subagent (read-only, independent); round-1 needs-changes findings applied by implementer + test-verified
reviewed_at: 2026-08-02T07:56:26Z
prompt_source: review.py compliance prompt; deliverables: test_codex_entry_gate_parity.py, architecture.md, entry_gate.py
---

Independent compliance review (read-only reviewer subagent). **Round 1:
needs-changes; all findings applied + verified. Verdict recorded: pass** (applied
state; no independent round-2 — findings are mechanical + test-covered, ADR-0014 §4).

Round 1 confirmed the core is sound + honest: packaging parity (AC1) registered +
tested against the shipped Codex package; the runtime rows recorded without a
dishonest `supported` cell; the `.codex` transform (AC3) + opt-out (AC4)
behaviorally proven against the shipped Codex copy; fail-open (AC7) structural.
Five needs-changes findings, all applied:

1. AC3 "assert on a relocated docs root" missing on Codex → **added**
   `test_relocated_docs_root_artifacts_silent_source_nudges`.
2. Tests-first "silent on a `.gitignore`-matched path" missing → **added**
   `test_gitignored_path_is_silent` (git init + .gitignore).
3. AC4 opt-out only tested `"0"` → **parametrized** over `{0,false,off,no}`
   (`test_opt_out_disables_full_token_set`).
4. Stale hook counts at architecture.md:82/109/131 (14 vs the 15 the diagram +
   spine prose now show) → **all bumped to fifteen/15**; verified 0 remaining
   "fourteen"/"14 hooks".
5. Same (line 82 "fourteen logical hooks") → fixed.

Positive recorded by the reviewer: no overclaim of Codex *runtime* verification;
the runtime rows + frame_review rationale are honest.
