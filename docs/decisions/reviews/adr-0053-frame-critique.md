---
adr: 0053
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (fresh)
reviewed_at: 2026-08-05T17:04:13Z
prompt_source: review.py frame-critique docs/decisions/adr-0053-reservation-numbering-sees-in-flight-branches.md
---

Adversarial frame-critique of ADR-0053 (fresh independent reviewer, read-only).

VERDICT: pass.

Load-bearing assumption attacked: that reading every in-flight ref's docs tree
(after a best-effort fetch) makes every live claim visible, shrinking the race
window "from days to seconds." The reviewer noted all three cited incidents
(#161/#162, bugs 015/016) are same-machine, sequential — where a lingering
local/remote-tracking ref closes the collision without any timing guarantee.
Cross-machine visibility instead requires the claimant to have pushed promptly
AND this session's best-effort fetch to have retrieved that ref, so the
"seconds" characterization is inferred from same-machine evidence rather than
measured against a genuinely concurrent two-machine race.

Frame survives: the mainline reservation flow (`--pr`, ADR-0015) pushes
immediately, the fetch is designed in, the only uncovered cases (`--no-push`,
fork branches) are explicitly scoped out with maintainer sign-off, and the ADR
hedges exactly this exposure with a kill criterion ("duplicate numbers keep
appearing after this ships → promote Option D from deferred to required"). That
is honest ruling-out, not a hidden assumption. Option C is correct and
necessary regardless of the residual cross-machine window. Suggested (non-
blocking) follow-up: confirm the "seconds" window against one real two-machine
trial before treating it as settled.
