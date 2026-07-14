---
adr: 0036
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-14T17:37:57Z
prompt_source: review.py frame-critique docs/decisions/adr-0036-immutable-release-identity.md
---

REASONING:
The strongest attack is that a tag remains movable between draft creation and
publication, so validation before publication alone cannot establish immutable
identity. The ADR survives because stable status is conditional on
post-publication verification that GitHub locked the tag to the tested commit;
a mismatch fails the release rather than blessing altered bytes.

SPECIFIC ISSUES:
- GitHub immutability closes the tag-mutation window — the tag is mutable while
  the draft and assets are prepared, but the required post-publication commit
  check detects any movement before the release is advertised; downstream
  source and archive identities therefore remain anchored to the verified
  locked commit.
