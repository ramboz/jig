---
slice: 112-05 — classb-claim-reservation
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-28T15:31:10Z
prompt_source: review.py craft 112-05
substrate: non-interactive
---

Craft pass — PASS. claim_ref.py implements local CAS + remote --force-with-lease CAS +
classify_push_failure-driven reserve/<N> fallback, timeout-guarded on all network paths.
_refuse_start_collision extension surgical (firing condition untouched). Reserve/release
wiring symmetric, has_frontmatter-guarded, releases on forward move out of IN_PROGRESS.
55 tests non-vacuous with explicit ADR-0045 regression guards.

Reconciliation-log nits (non-blocking):
- push_claim same-SHA no-op: two machines at the same HEAD both report a win (git no-op
  returns 0 without exercising the lease); AC5 remote race not fully closed for same-SHA
  racers — acceptable, local CAS + identity read carry the load-bearing halt.
- Enumeration loop duplicated ~40 lines from find_sibling_done (2nd copy; extract a
  _scan_sibling_refs helper at the 3rd consumer per rule-of-three).
- refinement-todo unification trigger fired (05 touched _refuse_start_collision); read
  converged onto cross_ref_state, preamble unification re-deferred — record trigger status.

Reviewer: jig:reviewer (isolated, read-only).
