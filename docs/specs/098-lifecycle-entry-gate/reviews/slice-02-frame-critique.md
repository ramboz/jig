---
slice: 098-02 — Codex host parity
pass: frame-critique
verdict: pass
reviewer: reviewer subagent (read-only, independent); round-1 needs-changes findings applied by implementer + test-verified
reviewed_at: 2026-08-02T07:56:26Z
prompt_source: review.py frame-critique prompt; deliverables: test_codex_entry_gate_parity.py, architecture.md, entry_gate.py
---

Adversarial frame critique (frame_review: true). **Round 1: needs-changes; both
gaps closed. Verdict recorded: pass** (applied state).

The reviewer confirmed the framing is largely honest (runtime unprovable from
Claude; no false DONE parity while IN_PROGRESS). Two real gaps, both closed:

1. **`assumed` was a smuggled fourth state** outside the AC6 legend
   (supported/degraded/unsupported) — and the slice Goal was to *eliminate*
   assumed-from-transform parity. **Fixed:** the two runtime rows are relabeled
   **`degraded`** (a wired fail-open/safe-over-fire fallback is degraded
   semantics, which the legend supports), and a legend defining
   supported/degraded/unsupported was added to the matrix.
2. **Dual-host infra hole** (AC3 over-stated): the blind `.claude`→`.codex`
   rewrite meant a Codex session treated `.claude/` as source — and the jig repo
   itself carries both dirs. **Fixed (Claude side) + documented (Codex side):**
   the source `_INFRA_DIRS` now lists both `.claude` and `.codex`, so the Claude
   gate treats an also-present `.codex/` as infra (closes the dogfood case). The
   Codex build collapses them, so the Codex gate still nudges on `.claude/` — a
   residual accepted limit, now **documented** in the matrix AC3 caveat and
   **pinned** by `test_dual_host_claude_dir_nudges_on_codex_accepted_limit`.
   AC3's "resolves the same" was softened to name the dual-host exception.

The reviewer's "shares jig-boundary-change-warn's payload contract" point was
graded acceptable-and-documented (shared-fate plausibility, not corroboration);
kept scoped as a packaging fact, not used to upgrade a row to `supported`.

Note: the frame subagent's output carried a harness notice that some text matched
an instruction-shaped pattern ("settings-json"); it was neutralized by the harness
and treated as data. No injected instruction was acted on.
