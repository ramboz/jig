---
slice: 083-07 — In-flight decision stubs
pass: compliance
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-27T00:19:10Z
prompt_source: review.py implementation/pr-review 083-07; read-only jig:reviewer
---

Compliance pass (jig:reviewer, Opus, read-only). Slice 083-07: PASS. All six ACs met with meaningful tests: AC1 AskUserQuestion→stub (PostToolUse); AC2 UserPromptSubmit override→stub (reuses is_user_override); AC3 ephemera→no stub; AC4 Stop dedups stubs vs scan (no double-surface); AC5 re-surface-until-recorded then pruned (prune_recorded_stubs + write_stubs) — durability parity with the scan; AC6 fail-open throughout. Deterministic capture correctly placed in hooks (principle #1); surfacing owner-gated; host packages (claude+codex) rebuilt consistently; .gitignore scopes the scratch dir; 12-hook restated constants consistent across verify_install.py + test_install_contract.py vs hooks.json. Honest-scope callout faithfully reflected; Codex parity deferred to 083-08. Nits (one addressed inline): dedup_scan_against_stubs lacked the _DEDUP_MIN_TOKENS floor the docstring claims to mirror → ADDED. Deferred (low value): multi-question AskUserQuestion answers concatenate into one stub quote (documented coarseness, owner-gated).
