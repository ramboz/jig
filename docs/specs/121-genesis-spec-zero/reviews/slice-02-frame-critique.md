---
slice: 121-02 — retire-genesis
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-10-27T00:03:45Z
prompt_source: review.py frame-critique docs/specs/121-genesis-spec-zero/spec.md 121-02 <slice> <spec> <adr-0067>
---

Four rounds.
R1 (needs-changes): legacy-stub "untouched" test (DRAFT + H1) too weak — the stub invites in-place edits keeping both markers, risking deletion of real work; rewrite scope (docs check misses AGENTS.md / custom docs roots; `docs_root: .` would rewrite the whole repo). Fixed: stricter frozen content markers + dir holds only spec.md, keep-and-report otherwise, fixtures for edited stub / extra slice file; explicit scoped file list with docs-root resolution; hint's legacy blind spot stated.
R2 (needs-changes): "retired" inferred from the tree fails when no own spec exists — a spec-less specs dir is greenfield, so --force re-seeds. Fixed: retire-genesis refuses when no non-genesis spec exists (+ fixture).
R3 (needs-changes): kept legacy 002 stub links ../001-adopt-jig/ (dangling after retire); list-item rule ambiguous against the real primer bullet / adoption-readiness item. Fixed: kept stub in scope; list item whose first link targets a removed dir deleted with continuation lines; other links elsewhere under docs root reported not rewritten; fixtures for each.
R4 (pass): frame grounded against source; failure modes all land on keep/report. Residuals folded in: marker stability cited from template git history; unrecognised 001-adopt-jig reported by name; numbered list starting at 2. accepted.
