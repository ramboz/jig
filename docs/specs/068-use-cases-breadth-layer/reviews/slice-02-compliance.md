---
slice: 068-02 — feed-forward-and-trace-links
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-11T00:14:50Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All five acceptance criteria are met and meaningfully tested. The deterministic trace surface (`skills/_common/use_cases.py`) cleanly separates the mechanical trigger predicate (`classify_spec`, append-only `next_use_case_id`, `is_near_duplicate`) from the judgment-driven cite/grow/decline contract in SKILL.md, correctly honoring ADR-0011 (advisory, never a hard gate) and the principle-1 hooks-vs-skills split. The critical `no_section` no-op for layer-not-adopted projects (jig's own repo) is implemented and tested. Full suite green via `scripts/run_tests.py` (exit 0), ruff clean, and edge cases (EOF heading, `## Use cases extended` non-match, id-less legacy tolerance) all behave correctly.

AC coverage:
- AC1 (read use cases as framing): SKILL.md step 1a instructs reading `## Use cases` before drafting; surface tests pin it.
- AC2 (machine-resolvable trace link): `use_cases:` flow-list seeded in the spec stub + both templates; round-trips through `parse_frontmatter`/`set_frontmatter_field`.
- AC3 (resolves to a vision id): `parse_use_cases` + `resolve_use_cases` map `UC-N` ids; unresolvable reported not raised; UC-N rendered in both worked examples + product-vision template + surface tests.
- AC4 (soft, never blocked but never silent): `use_cases: []` non-erroring in the stub; `classify_spec` returns `empty`→prompt; SKILL.md states it never blocks.
- AC5 (mechanical grow trigger): `classify_spec` is the deterministic predicate over the trace field; the three-path cite/grow/decline prompt + grow-quality guards (`next_use_case_id` append-only, `is_near_duplicate`) documented in SKILL.md; the `no_section` no-op is correct and tested as the critical dogfood case.

SPECIFIC ISSUES:
- skills/spec-workflow/SKILL.md:188,191,215 — Refers to the trigger predicate as `classify`, but the function in use_cases.py is named `classify_spec`. Minor documentation-accuracy nit; the link to the module resolves so a reader can still find it, and the surface test (test_names_the_classify_predicate_helper) only asserts the `"classify"` substring so it does not catch the `_spec` drift. (Medium confidence; non-blocking.)

RECONCILIATION NOTES:
- The new module `skills/_common/use_cases.py` exposes a broader API than slice 068-02 strictly consumes (e.g. `has_entries`, `is_resolved`, `ResolveResult`) — this is intentionally shaped for slice 03's project-wide coverage reuse and is documented as such in the module docstring; note it in the deviation log as forward-shaping for 03, not scope creep.
- Running `test_workflow.py` standalone surfaces 4 `ModuleNotFoundError: No module named 'skills'` errors (NewSpecScaffoldsFilePerSliceTests) from `importlib.import_module(...)` / `import skills`; these pass under `scripts/run_tests.py` and are unrelated to this slice. Worth a learnings/inbox note that those tests are runner-only, not standalone-runnable.
- Consider aligning the SKILL.md predicate name to `classify_spec` (or renaming the function to `classify`) so the contract prose and the code agree exactly.
