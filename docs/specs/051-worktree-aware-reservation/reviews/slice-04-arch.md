---
slice: 051-04 — start-time claim-collision guard (→ IN_PROGRESS)
pass: arch
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-11T15:56:38Z
prompt_source: review.py arch (051-04)
---

Independent architecture review of slice 051-04 (fresh reviewer).

VERDICT: pass — architecturally sound; no blockers.

Reuses ADR-0015's `git show origin/main:<path>` remote-read shape rather than inventing a mechanism; places the hard block at the only point where "surface the collision at start" is achievable (the IN_PROGRESS transition); keeps the transition-level guard and `_reserve_claim_on_main` cleanly split with an explicit not-double-fetch condition. No documented module boundary or public contract is violated; `docs/architecture.md` asserts no "transition is network-free" invariant. The env-gate matches jig's ADR-0011 deliberateness-gate family exactly. The trunk-integrity (never-bypassable AC6 DONE refusal) vs local-start (bypassable) asymmetry is a correct, well-argued decision.

No new ADR required — this extends Accepted ADR-0015; the spec `## Amendments` + Resolved-decisions record is sufficient per ADR-0010.

Non-blocking notes (→ reconciliation log):
- The default → IN_PROGRESS path is no longer network-free, reversing 049-01's "local by default, no network" claim UX. Correct semantic location for a hard block, degrades softly offline, but the reversal should be recorded durably (not only in code comments).
- Intentional reachability asymmetry: soft transition-level guard vs hard push-path reservation. Record so a future reader does not "harmonize" them by mistake.
- `_origin_slice_state` maps every non-zero `git show` to "absent" (silent proceed); a non-absent post-fetch failure would skip rather than warn — consistent with `_reserve_claim_on_main`'s existing simplification.
