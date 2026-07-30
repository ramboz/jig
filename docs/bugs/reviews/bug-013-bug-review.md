---
bug: 013
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent (fresh context, read-only)
reviewed_at: 2026-07-30T01:47:41Z
prompt_source: review.py bug-review docs/bugs/013-adr-accept-strict-prose-gate.md
---

Independent bug-review pass on bug 013 (`jig:reviewer` subagent, fresh
context, read-only). Reviewed `origin/main...HEAD` at commit `ced525b`.

**Verdict: pass.**

The fix addresses the documented root cause rather than the symptom:
`_STATUS_PROPOSED_RE` is kept strict *only* as the rewrite pattern, and the
gate reads a separate frontmatter-first classifier (`_adr_status`) — the
gate/transform separation hypothesis H2 named. Scope stays inside the
declared `structural_fix` class; no unrelated refactors.

The reviewer independently verified the load-bearing "every status reader is
frontmatter-first" claim rather than taking it on trust: `cmd_accept`, both
`cmd_supersede` gates and `_extract_status_and_date` (driving the README
index and `resolve-todo`) all resolve frontmatter first; `_classify_status`
has exactly one call site; `_STATUS_ACCEPTED_RE` / `_insert_after_accepted`
are used only for anchor location, never for state; and the two
out-of-module readers (`workflow.py::_lookup_adr_accepted`,
`migrate.py::_adr_status_readable`) were already frontmatter-first. Host
mirrors in sync.

**Findings, all addressed in commit `26b75aa`:**

1. *(real coverage gap)* `test_supersede_refuses_when_prose_anchor_is_missing`
   asserted only exit 2, the filename, and the literal `"Status"` — all of
   which the pre-fix code also produced, for a different reason
   (`_classify_status` → `Unknown`). Ruling 5 was therefore unguarded. The
   test now asserts the anchor-specific wording.
2. `assertNotIn("Proposed", index)` was coupled to the whole fixture README;
   now scoped to the ADR's own bullet line.
3. `assertIn("proposed", stderr.lower())` at test_adr.py:349 passed only via
   the fixture *filename*; retargeted at the state the refusal names.
4. Sequencing: ADR-0046 was `Proposed` while the code shipped its rulings.
   Closed by the accept + supersede + index sequence recorded in the
   deviation log.

**Reconciliation notes carried forward:**
- `cmd_supersede`'s ADR-0026 docstring attribution rewritten to name
  ADR-0046 ruling 5 as the reason the sync-lock survives there.
- The two narrowed `WriterStampsFrontmatterStatusTests` cases are recorded
  as a deliberate test inversion, not a coverage loss.
- Behaviour change for downstream callers: `accept` now writes a note to
  **stderr** on non-canonical prose; a caller treating non-empty stderr as
  failure would misread a successful accept.
