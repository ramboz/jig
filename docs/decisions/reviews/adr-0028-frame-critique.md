---
adr: 0028
pass: frame-critique
verdict: pass
reviewer: Explore (jig frame-critique)
reviewed_at: 2026-07-09T02:40:26Z
prompt_source: review.py frame-critique
---

Adversarial frame-critique of ADR-0028 (revised 2026-07-08 to add the two-topology model: hub-and-referenced first, peer-members deferred). Two rounds.

**Round 1 → needs-changes** (two blockers):
1. A4 too clean — claimed the hub needs "no distributed-state machinery." Conflated *where jig state lives* (centralized — true) with *where coordination cost lives* (across the ~8 referenced work repos — unchanged). The hub's own shipped slices 034-12/13 (relabeled "cross-track") must reason over referenced-repo file paths, so a subset of cross-repo work-coordination is a hub-tier need at v1.
2. A2 overstated 084 — claimed 084/ADR-0033 "already delivers the multi-track hub org." ADR-0033:142-166 explicitly scopes OUT multi-jig-per-repo coordination, subtree git-anchoring (per-track reserve/land — flagged possible "category mismatch"), and migrate-into-subtree — exactly what a multi-track hub needs.

**Remediation:** A4 rewritten to split the axis — state-coherence machinery (membership/drift/read-through/cross-repo-spec-pinning) is peer-only; cross-repo touchset/collision (034-12/13) is hub-tier, computed *locally* over `repo:path` (no network), cross-repo not cross-track. A2 rewritten to name the three ADR-0033 deferrals as hub-tier *dependencies* the hub must close (making it a real spec with real risk, not a recipe). Kill criteria updated (collision doesn't trip the distributed-sync trigger; the "category mismatch" is the foundation risk). spec.md aligned: 034-12/13 relabeled cross-repo hub-local, Hub-tier note cites the 084 deferrals.

**Round 2 → pass.** Both fixes verified honest against ADR-0033:142-166 and spec 034. A4 split propagated consistently (034-12/13 hub-local-active, 034-11/14 peer-deferred, closeout-drift correctly peer). Kill criteria consistent with new A4.

VERDICT: pass

Findings:
- [strength] A4 split verified end-to-end; the slice disposition enforces the "no network in hub" boundary rather than just asserting it.
- [strength] A2 honest — all three deferrals present verbatim in ADR-0033's scoped-out list; the "category mismatch" carried forward as the hub tier's biggest unknown + kill-criterion #3.
- [nit] Hub-local collision sees only cross-repo work routed through hub touchsets; a direct push to a shared referenced repo is invisible (added to Open questions for 034-13 slicing).
- [nit] The `personalization` two-track scope claim was asserted, not cited — now grounded to the exemplar's `repos.yaml scope: [rtb, offer-management]` in A4.
