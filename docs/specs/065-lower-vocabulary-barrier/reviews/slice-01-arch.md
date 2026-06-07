---
slice: 065-01 — Lexicon foundation (shipped data + overlay loader)
pass: arch
verdict: pass
reviewer: arch-review
reviewed_at: 2026-06-07T15:52:40Z
prompt_source: review.py arch-review
---

VERDICT: pass

REASONING:
Shipped lexicon.json + loader establish a clean, well-bounded public contract — load_shipped() / load(project_dir) returning a term-key -> entry dict — that the three downstream consumers can depend on without drift, per ADR-0021 Option A and docs/architecture.md module boundaries. Correctly placed under skills/_common/ (stdlib-only, __file__-relative resolution, travels as machinery), fail-soft on every degraded path.

SPECIFIC ISSUES:
- [nit] skills/_common/lexicon.py:47 — _term_key normalizes compound live-glossary headings (`## Tier 0 / Tier 1 / Tier 2`, `## Scaffolded install / scaffold mode`) to keys that do NOT match the shipped keys (`tier 0/1/2`, `scaffolded install`). The override silently becomes an ADD of a parallel key. Fail-soft + within the documented heuristic, but the shipped key spellings and live glossary headings drift on exactly the seed terms.
- [nit] skills/_common/lexicon.py:92 — overlay entries carry only short/plain (no example/see_also); consumers must treat those as optional on overridden terms.
- [strength] __file__-relative resolution; single narrow load() surface keeping the Option-B fallback open; total fail-soft contract.

RECONCILIATION NOTES:
Capture the compound-heading key mismatch in the deviation log: on seed terms tier 0/1/2 and scaffolded install, a real project glossary's documented headings won't override — they add a second key. 065-02/03 consumers should know key collisions are spelling-exact. Also log the entry-shape asymmetry.
