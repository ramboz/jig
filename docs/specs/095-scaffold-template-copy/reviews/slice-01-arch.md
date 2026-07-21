---
slice: 095-01 — claude-scaffold-templates
pass: arch
verdict: pass
reviewer: jig:reviewer (fresh context, round 2)
reviewed_at: 2026-07-17T06:07:32Z
prompt_source: review.py arch-review
---

Round 2 (after fixes). Both round-1 must-fixes — the two shipped doc contracts
that enumerate the copy set (`skills/migrate/SKILL.md`, `docs/architecture.md`)
— are fixed and verified against source rather than taken on trust; the new
Codex-rewrite-table claim checks out.

Design stands. Verified independently: module placement is right; the two copy
functions should NOT be unified at two callers (extract-at-third-caller,
ADR-0002/ADR-0023); the ungated (non-tier-scoped) template copy is sound and
precedented by the ungated `.gitignore` security floor; spec 084's docs_root
interaction is correct (`.claude/templates/` is the template *source* tree, and
destinations honour docs_root via each helper's own `_docs_base`); release
packaging already ships `templates`; no new drift class.

Round-2 must-fixes, both addressed: ADR-0038 contradicted its own live-file
table (said 3, table said 4 — now 5 helpers / 4 files); and §6's encoding fix
stopped at the write side while leaving the read paths this slice newly enabled
— `workflow.py`'s regressed from graceful degrade to unhandled crash under a C
locale, now fixed. Follow-ups recorded to the inbox rather than fixed here:
the rest of the family's default-encoding reads (pre-existing in plugin mode
too), and the two copy functions already having drifted at n=2.
