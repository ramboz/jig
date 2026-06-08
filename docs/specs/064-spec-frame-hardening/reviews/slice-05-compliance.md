---
slice: 064-05 — adr-accept-gate
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-08T20:39:14Z
prompt_source: review.py implementation (064-05, 5 deliverables)
---

VERDICT: pass

REASONING:
All 3 ACs met + proven by tests. AC1: ADR verdict home docs/decisions/reviews/adr-NNNN-frame-critique.md written via record-review --adr, reusing review_evidence.py with ADR_REQUIRED_FIELDS keyed on `adr` not `slice`. AC2: adr.py cmd_accept calls _gate_frame_critique BEFORE the Status flip, refusing a non-clearing frame-critique with a message naming the artifact + the exact (now-resolvable) record/build commands, soft-bypassable via JIG_REVIEW_EVIDENCE_GATE=0. AC3: ADRs always-on — frame_review:true stamped in _render_adr_content (the shared chokepoint covering the real reserve_adr CLI path), gate keys on the truthy flag so legacy markerless ADRs grace through. No-drift: evidence_gate_enabled moved to _common, workflow.py re-imports as alias (byte-identical). parse_verdict_file backward-compatible (required_fields defaults to slice set). record-review --adr mutually exclusive with spec+slice.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- Log the grace-path-as-real-mechanism (gate keys on truthy frame_review; new ADRs stamped at creation → always-on going forward, legacy grandfathered) — load-bearing for the OQ3 reconciliation.
- Log the cmd_new→_render_adr_content stamp-location deviation (the CLI routes through reserve_adr, not cmd_new).
