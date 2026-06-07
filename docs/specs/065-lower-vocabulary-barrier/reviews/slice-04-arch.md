---
slice: 065-04 — Self-defining generation convention
pass: arch
verdict: pass
reviewer: jig:reviewer / arch-review
reviewed_at: 2026-06-07T19:58:10Z
prompt_source: review.py arch-review
---

VERDICT: pass

The change extends copy_machinery() to inject a marker-delimited managed block into a
project's docs/workflow.md, faithfully mirroring the established ADR-0013
_write_gitignore_secret_block precedent (same idempotent create/append/replace-in-place
contract, atomic writes, half-block guard; called from both scaffold() and copy_machinery()).
Non-clobber is sound (replace-in-place only touches the delimited region; pre-existing
content preserved verbatim and tested) and HTML-comment markers keep the block invisible in
rendered prose. No architecture.md module boundary is violated: copy_machinery already writes
outside .claude/ (the project-root .gitignore floor), so reaching docs/ is an incremental
step on an already-crossed boundary — riding ADR-0013's lineage rather than a new ADR is
defensible.

[strength] third caller of the audited managed-block shape (rule-of-three consistent).
[strength] migrate test seeds pre-existing custom content and asserts it survives the append.
[nit, addressed] potential drift between _render_self_defining_block() and the dogfooded
docs/workflow.md copy — added a byte-identity cross-check (050 people.md precedent).
[noted] copy-machinery's surface now includes docs/; recorded in the deviation log so the
widened contract is discoverable. (Reviewer: jig:reviewer / arch-review.)
