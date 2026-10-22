VERDICT: needs-changes

REASONING:
The bounded static variant is isolated from the inherited card contract and preserves native verdict authority without executing producer code. Tests meaningfully separate semantic contradictions from ordinary hash drift, and the proof receipt distinguishes genuine evidence from synthetic prerequisites. However, initial-record validation has a fail-open case for an absent screenshot witness.

SPECIFIC ISSUES:
- [blocker][impl] skills/_common/static_design_bindings.py:786 — `same(obs["capture_hash"], self.pins.get(root / "app.png"), ...)` succeeds when `capture_hash` is null and `app.png` is absent. With output/result links repinned, this incomplete native acquisition can clear validation. Require a valid SHA-256 capture hash and explicit screenshot membership in the output inventory; add a repinned omission regression. This concerns initial recording, not deletion against an unchanged recorded inventory.
- [nit][impl] skills/_common/test_static_design_bindings.py:594 — The runtime-order test checks fixture ordering and valid-input acceptance, but still passes if the ordering guard is deleted. Add a misordered, repinned manifest rejection case.
- [strength][impl] skills/_common/test_static_design_bindings.py:704 — Repinning result links while retaining contradictory semantic rows tests the validator beyond incidental digest failures.

RECONCILIATION NOTES:
Log the test nit and evidence-labeling strength; the blocker is an implementation defect, not a proposed scope change.

Routing/evidence gap: Applied the richer Scout rubric statically. Scout instrumentation and shell execution were unavailable; no fresh Git comparison, lint/tests, digest verification, or network/thread lookup occurred. Scope was anchored to the supplied base-`756f39dcdd842f9cdf3b34b6924e9b216212af13` checkpoint diff and current listed deliverables, not inherited parent changes. Preserved validation receipts were read, not independently rerun; cross-provider independence is unconfirmed.

> Publication cleanup (2026-10-22): the withdrawn mixed-app proof reference was
> removed at the owner's explicit request. This edited export retains the
> original nonpass and findings but is not the archived original review bytes.
