---
slice: 116-02 — orient-surface
pass: frame-critique
verdict: pass
reviewer: reviewer
reviewed_at: 2026-10-03T17:34:01Z
prompt_source: review.py frame-critique docs/specs/116-use-case-progress-report/spec.md 116-02
---

**Round 1 — needs-changes.** Highest-risk assumption: the three-item orient section (totals; use cases with no done slice or no spec; Unanchored names) shows the owner the rabbit-hole drift they reported. Ungrounded and contradicted by the corpus: tangents get cited to broad use cases (spec 116 itself cites UC-11/UC-12), Unanchored holds two DONE legacy infra specs, so the section is static every session; and AC2 drops the per-spec listing the mis-mapping mitigation relied on. Secondary: having the orient model filter the full `progress` tree by hand runs against orient's own "do not re-derive by hand" rule and costs orchestrator context every run.

**Fixes applied:** claim narrowed project-wide (progress view, not drift detector — ADR-0064 bound 5; owner kept the full tree for the CLI on 2026-10-03). New AC1: a deterministic `workflow.py progress --summary` computes the three items in code; orient copies it (AC3) and names `workflow.py progress` for the full listing. Kill signal now names the orient section.

**Round 2 — pass.** Both findings resolved; no new likely-wrong assumption. Non-blocking nits applied: name lists in `--summary` capped at 10 with an `… and N more` line (late adopters start fully unanchored); Goal and anti-horizontal check describe the section accurately (totals, untouched goals, untraced work); the orient kill signal gets an explicit owner checkpoint at the first `/jig:orient` run after the spec lands.
