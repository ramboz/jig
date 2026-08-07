---
slice: 096-02 — baseline-exclusion-and-resolve
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (frame-critique, reshaped onto ADR-0040)
reviewed_at: 2026-07-28T14:57:55Z
prompt_source: review.py frame-critique
---

Frame-critique of reshaped 096-02 (onto ADR-0040) — **pass**. The exclusion
invariant ("unprefixed project-scope skill dir a scaffold writes carries no
SKILL.md", + jig- prefix discriminator) verified directly against the tree:
scaffold.py:742 prefixes user-facing skills and only copies dirs with a SKILL.md;
both unprefixed writers (:726, :1485-1489) omit SKILL.md; migrate.py:287 ships the
discriminator. Plugin/admin unprefixed exposure is OQ4-gated (AC4), not glossed.
Observation folded in: AC6 tightened — the admin/plugin-scope reviewer-read claim
now REQUIRES a live probe (a hermetic Python test exercises only resolver path
logic, not a subagent's sandbox reach). Frame survives.
