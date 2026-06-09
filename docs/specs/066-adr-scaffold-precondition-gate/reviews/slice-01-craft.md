---
slice: 066-01 — classify-and-route-on-adr-new
pass: craft
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-09T17:50:24Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
Slice 066-01 cleanly mirrors the shipped 063-01 onto the ADR-creation door: it consumes
`_common.scaffold_state.classify_scaffold_state`/`precondition_enabled` unchanged (genuine reuse —
no second classifier, no trigger-counting in `adr.py`), routes greenfield→`/jig:scaffold-init` and
adoptable→`/jig:migrate` with clear state-naming messages, and preserves today's behavior behind
the shared `JIG_SCAFFOLD_PRECONDITION` bypass. The new `ReserveAdrPreconditionRoutingTests` class
exercises every state and asserts the load-bearing observable contract on refusal (no ADR file AND
no `git commit` in the recorded argv log). Full suite green (124 adr / 2501 repo); pre-existing
fixtures correctly gained a `scaffold.json` sentinel. Findings are nice-to-haves only.

SPECIFIC ISSUES:
- [strength] adr.py:686-711 — precondition placed after `_validate_slug` and before the
  `_current_branch` worktree dispatch, so bad slugs still refuse first and every reserve sub-path
  (on-main, off-main --no-push, detached-worktree) inherits the routing uniformly. Correct chokepoint.
- [strength] adr.py:704-711 — bypass branch faithfully restores the pre-066 guard (verified against
  HEAD), pinned by `test_bypass_preserves_legacy_weak_refusal` (legacy wording present AND routing
  strings absent).
- [strength] test_adr.py — refusal tests assert observable no-side-effect (no ADR file +
  `assertNotIn("git commit", flat)`), the right behavioral assertion rather than message-only.
- [strength] test_adr.py — `test_interrupted_scaffold_routes_to_scaffold_init` pins the load-bearing
  ordering quirk (watermark + >=3 triggers, no scaffold.json -> greenfield, not adoptable).
- [nit] adr.py:453-457,566,771-775 — the `adrs_dir.mkdir(parents=True, exist_ok=True)` line + its
  identical ~4-line comment is now repeated in all three reserve sub-paths. Consistent with the
  file's ADR-0002 inline-mirror convention, but a `_ensure_adrs_dir(adrs_dir)` helper would remove
  the triplicated comment; the 4th caller is the ADR-0002 extract trigger. Optional.
- [nit] test_adr.py — `_make_greenfield` is an empty `pass` body kept for naming symmetry with
  `_make_adoptable`/`_make_scaffolded`. Trivial; inline or comment.
- [nit] adr.py:693-694,700-701 — both routing messages hard-code "then re-run `new`" rather than
  deriving the subcommand name. Correct (reserve is reached via `adr.py new`); just noting.

RECONCILIATION NOTES:
Both substantive nits (triplicated mkdir+comment; empty `_make_greenfield`) are cosmetic, below the
bar for blocking REVIEWED — log as optional cleanups. If the mkdir pattern gains a 4th caller, that
is the ADR-0002 trigger to extract `_ensure_adrs_dir`.
