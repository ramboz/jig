---
slice: 098-02 — Codex host parity
pass: craft
verdict: pass
reviewer: reviewer subagent (read-only, independent); round-1 needs-changes findings applied by implementer + test-verified
reviewed_at: 2026-08-02T07:56:26Z
prompt_source: review.py craft prompt; deliverables: test_codex_entry_gate_parity.py, architecture.md, entry_gate.py
---

Independent craft review (read-only reviewer subagent). **Round 1: needs-changes;
all findings applied + verified. Verdict recorded: pass** (applied state).

Strengths recorded: `_eval`'s try/finally env restore is leak-free;
`test_codex_infra_dir_is_silent` genuinely proves the `.codex` transform; the
behavioral spot-check earns its place (Codex-specific `.codex` boundary + shipped-
copy smoke); the matrix table is well-formed. Findings applied:

- architecture.md:131 subgraph label "14 hooks" (encloses 15 nodes) → **"15 hooks"**;
  :109 + :82 prose "fourteen" → **"fifteen"**.
- `test_infra_dirs_rewritten_to_codex` asserted `.codex` present but not `.claude`
  absent → **added** `assertNotIn('".claude"', text)`.
- `setUpClass` leaked the injected `sys.path` entry (no teardown) and carried an
  inaccurate "resolves against the copy" comment → **added `tearDownClass`** that
  pops the path + **corrected the comment** to state the byte-identical-_common
  reality.
