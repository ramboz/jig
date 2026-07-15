---
adr: 0036
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-14T23:34:56Z
prompt_source: review.py frame-critique docs/decisions/adr-0036-immutable-release-identity.md
---

The reviewer attacked the assumption that repository administration preserves
GitHub's immutable-release setting throughout publication. The ADR passes
because it explicitly isolates that trust boundary, verifies the publication
result, quarantines and permanently retires a breached version, and does not
claim that cached ambiguous bytes can be revoked.
