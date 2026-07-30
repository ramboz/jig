---
slice: 100-03 — promote-subcommand
pass: compliance
verdict: pass
reviewer: jig:reviewer (independent, read-only)
reviewed_at: 2026-07-24T23:44:58Z
prompt_source: review.py implementation (spec 100, all slices)
---

Independent compliance review of spec 100 (all four slices), run read-only
against the ACs without access to the implementation conversation.

**Verdict: needs-changes on the first pass; every finding addressed below.**

Confirmed satisfied: the illustrative worked example and the `## Template` fence
are genuinely excluded from `update`/`promote`/`lint` (structural marker, not a
hardcoded title, asserted against the REAL shipped file); `promote`'s ordering
puts every failure point before its single write, proven by an induced `adr.py`
failure; `lint` has no write or seed path; ADR-0042's boundary holds —
`evaluate_routing_signals` has exactly one call site, inside `lint_lightweight`,
and no `--confirm-lightweight` exists on any parser.

Findings, and what was done:

1. **`promote` worked only under `--no-push`** (also found independently by the
   craft pass). Positional stdout parsing broke every other mode *after* the ADR
   was created and pushed. FIXED: resolution is by slug/filename now; added
   `PromoteDefaultPushModeTests` running a real default-mode promotion against a
   real bare origin, verified to catch the original defect.
2. **`## Entries` had no lower bound**, so `promote`/`update` deleted any
   following section. FIXED with `_NEXT_H2_RE` + an anchored heading match;
   `EntriesSectionBoundTests` covers parse/update/promote/lint and the
   prose-mention case.
3. **AC1's phrase assertion and AC5's `assertIn("1", out)` were weaker than
   their ACs.** FIXED — both tightened.
4. **`test_module_source_imports_no_gate_machinery` pinned nothing** (asserted
   absence of strings never in the file). FIXED: replaced with AST-based guards
   for the real invariants — the evaluator's single call site, and the
   self-containment import rule that was previously prose-only. Mutation-tested.
5. **`promote` under `layout.docs_root: "."` has no test.** ACCEPTED as a
   coverage gap and inboxed; the path resolves through `project_layout` exactly
   as the covered helpers do.
6. **Slice 100-01's AC3 amendment was overstated** ("unimplementable" — in fact
   `assertEqual(count, 2)` would have worked). CORRECTED in the slice: the AC was
   changed because a second in-file copy is the wrong design, not because it
   could not be tested. The stale DoD line was amended to match.
7. **Refusal messages fold AC7/AC9 into the generic "no entry titled …".**
   ACCEPTED and recorded in 100-02's deviation log §4.
8. **ADR-0042 was still Proposed.** RESOLVED: frame-critique run and recorded,
   the findings acted on, ADR accepted.
