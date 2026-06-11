---
slice: 068-02 — feed-forward-and-trace-links
pass: arch
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-11T00:14:51Z
prompt_source: review.py arch-review
---

VERDICT: pass

REASONING:
This is an architecturally clean change. It adds a typed `use_cases:` frontmatter contract that rides jig's existing generic flow-list machinery (no field-specific parse code — pinned by a round-trip test) and a stdlib-only `skills/_common/use_cases.py` sibling that ships the deterministic predicates slice 03 will reuse, without building slice 03's coverage check. The `UC-N` id scheme, the absence-vs-empty-vs-unresolvable state distinction, and the no-section no-op are all load-bearing design decisions that are made explicit and well-tested (28 module tests, full suite 2580 green). It preserves the documented module boundaries: `use_cases.py` imports only `re`, the deterministic predicates are driven by SKILL.md orchestrator judgment (not a new hook or a workflow.py fork), and it honors the ADR-0011 soft-gate philosophy throughout.

SPECIFIC ISSUES:
- [strength] skills/_common/use_cases.py:92-105 — The absence-vs-empty distinction (`_use_cases_section_body` returning `None` for "no section / layer not adopted" vs `""` for "adopted but empty") is the right primitive, and `classify_spec` checks `no_section` first so a stray cited id on a layer-less project (jig's own repo) still classifies as the no-op. This is the dogfood-safety property (per the "dogfood project-state gates against the jig repo itself" learning) and it's explicitly tested.
- [strength] skills/_common/test_parsing.py:212-239 — Pinning that `use_cases:` round-trips through the generic `parse_frontmatter`/`set_frontmatter_field` (and serializes unquoted as `[UC-1, UC-3]`) proves the contract claim — the new field genuinely reuses the `dependencies:` precedent rather than introducing a parallel parser. This is the correct way to discharge the "no new contract machinery" architecture claim.
- [strength] skills/_common/use_cases.py:214-225 — `next_use_case_id` deliberately allocates `max(existing)+1`, never `count+1`, so a deleted `UC-2` stays retired. This append-only/stable-id property is what makes the trace link durable under reorder/edit/delete, and it mirrors jig's `NNN`/`NNNN` numbering culture. The template prose and vision-elicitation SKILL.md both restate the rule, so the convention won't drift.
- [strength] skills/_common/use_cases.py — Correct scoping for a Rules slice: the module ships `parse_use_cases`/`resolve_use_cases` shaped for slice-03 reuse and explicitly disclaims building the coverage check. The API surface is right-sized — no speculative project-wide query added ahead of demand.
- [nit] skills/_common/use_cases.py:56-63 — Regex asymmetry between `_UC_BULLET_RE` and `_ANY_BULLET_RE`: the latter has a `(?!>)` guard, the former does not. (Orchestrator note: empirically tested at reconciliation — `_UC_BULLET_RE` does NOT in fact match a blockquoted `> - UC-N:` line, because `^\s*[-*+]` requires a bullet char at line start and `>` blocks `[-*+]`; the "`\s*` matches the space after `>`" reasoning is incorrect. The nit is a false positive and no guard was added. See deviation log.)
- [nit] skills/_common/use_cases.py:235 — `is_near_duplicate(text, existing)` takes a pre-parsed `{UC-id: goal}` map while every other public reader takes `vision_text`. The asymmetry is documented and deliberate (the confirm step has already parsed the section to display it), but it's the one signature slice 03 / future callers could trip over by passing `vision_text`. Worth a one-line note in the module docstring's API list.

RECONCILIATION NOTES:
Both nits are non-blockers — fold into the deviation log rather than gate REVIEWED. The `_UC_BULLET_RE` blockquote-guard nit was empirically dismissed (see above). The `is_near_duplicate` signature asymmetry is acceptable as-is given it's documented, and warrants only a docstring callout. No architectural rework needed; the contract, id scheme, module boundary, and ADR-0011 soft-gate posture are all sound.
