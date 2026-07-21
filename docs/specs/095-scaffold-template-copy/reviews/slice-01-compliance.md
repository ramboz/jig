---
slice: 095-01 — claude-scaffold-templates
pass: compliance
verdict: pass
reviewer: jig:reviewer (fresh context, round 2)
reviewed_at: 2026-07-17T06:07:06Z
prompt_source: review.py implementation
---

Round 2 (after fixes). Every AC1..AC6 met and pinned by a non-vacuous test;
implementation faithful to ADR-0038 option (a) — no helper's template
resolution touched. Round 1 was `needs-changes` and found real defects: a
vacuous AC4 edge-case test (asserted the rewrite round-trip against two files
that never take the rewrite branch), a `decisions.py` comment still asserting
the opposite of shipped behaviour, two stale shipped doc contracts, a missing
partial-state assert, and a locale-dependent `read_text()`. All fixed and
re-verified.

Round 2 findings, all addressed: the Codex-*rendered* migrate contract still
omitted the templates step (`finalize_codex_migrate_skill` replaces the section
wholesale — the SKILL.md fix never reached Codex users); the phrase "no helper
changes" survived verbatim in two places the deviation log calls false; a
`scaffold.py:944-947` citation went stale from this slice's own +47-line
insertion; and the "four helpers" learning was itself an undercount — it is
five (`migrate.py` reads the same template through the same shape).

Verified true and worth keeping: deviation §2's memory.py/workflow.py claims,
§7's `load_tests` Python-version claim, §9's honest "knowingly not done".
Residual, recorded not fixed: the `encoding="utf-8"` fix is not pinned by any
test (no fixture forces a non-UTF-8 locale), so dropping it would ship green.
