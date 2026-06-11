---
slice: 068-02 — feed-forward-and-trace-links
pass: craft
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-11T00:14:51Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
The craft is high. skills/_common/use_cases.py is a clean, stdlib-only, well-documented deterministic core that faithfully mirrors its cited siblings (parsing.py / lexicon.py): tolerant legacy-shape parsing, max+1 append-only id allocation with explicit "never reuse a retired number" reasoning, __slots__ on the result type, and a no-section no-op that is correctly checked first. Tests are thorough and behavior-named (28 use_cases tests + frontmatter round-trip + 11 skill-surface assertions), the full 2580-test suite is green with no regressions, and the template/worked-example/SKILL.md prose updates are mutually consistent. The findings below are all nits — naming/prose drift and two latent robustness edges — none of which block the REVIEWED transition.

SPECIFIC ISSUES:
- [strength] skills/_common/use_cases.py:214-225 — next_use_case_id uses max(existing)+1 (not count+1) with an explicit comment and a dedicated test (test_never_reuses_a_retired_number) proving a deleted UC-2 is not back-filled. Correct and well-guarded against the obvious off-by-one trap.
- [strength] skills/_common/use_cases.py:92-105,185-211 — the absence-vs-empty-body distinction (None ⇒ no_section ⇒ no-op; "" ⇒ empty ⇒ prompt) is load-bearing for the dogfood case (jig's own repo has specs but no use-case layer), is checked first in classify_spec, and is pinned by test_no_section_is_the_no_op_dogfood_case + test_no_section_wins_even_with_unresolvable_id. This is exactly the kind of self-host gate that has bitten jig before, and it's handled deliberately.
- [strength] skills/_common/use_cases.py:160-177 — resolve_use_cases reports unresolvable ids rather than raising (AC3), normalizes cited ids case-insensitively (uc-2 resolves), and treats None as empty — robust input handling with matching tests.
- [nit] skills/spec-workflow/SKILL.md:188,191,215 — the prose names the helper `classify`, but the actual function is `classify_spec` (skills/_common/use_cases.py:185). A reader grepping the named file for `classify` still finds it, so this is cosmetic, but the exact symbol name would read truer.
- [nit] skills/spec-workflow/SKILL.md:202 — "(`workflow.py`/`use_cases.py` allocate `max + 1`...)" overstates current reality: only use_cases.py has next_use_case_id; workflow.py does not import or call it (workflow.py's only 068-02 change is the static `use_cases: []` stub line). The AC5 grow/cite/decline flow and id allocation are orchestrator-followed prose, not workflow.py code. Naming workflow.py as an allocator is slightly aspirational — consider "use_cases.next_use_case_id allocates max+1" alone.
- [nit] skills/_common/use_cases.py:127-145 — parse_use_cases has no fenced-code-block awareness: a `- UC-1: ...` line inside a fence within the `## Use cases` section is parsed as a real entry. The cited sibling lexicon.py shares this class of limitation, and a real vision section body holds entries not fences, so practical risk is low — but a one-line note in the docstring acknowledging the no-fence-stripping assumption would set expectations for slice 03's reuse.
- [nit] skills/_common/use_cases.py:141-145 — a vision with two identical UC-N ids (a hand-edit data error) silently last-wins in the returned dict, with no signal. Not in scope to fix here, but slice 03's coverage query (which reuses this) would see only one entry; worth a docstring note or a future duplicate-id check.

RECONCILIATION NOTES:
All four nits are documentation/robustness polish, not behavioral defects — fold them into the deviation log rather than blocking REVIEWED. The two most worth carrying forward to slice 03 (which reuses parse_use_cases / resolve_use_cases): the no-fence-stripping assumption and the silent duplicate-UC-N last-win, since slice 03's project-wide coverage query inherits both. The classify vs classify_spec and the workflow.py-allocates prose nits are pure SKILL.md wording fixes that can be corrected inline (live operational prose, ADR-0010) at reconciliation. Strengths worth repeating: the max+1 append-only id discipline and the absence-vs-empty no-op-first ordering with explicit dogfood tests.
