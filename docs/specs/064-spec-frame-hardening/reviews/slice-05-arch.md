---
slice: 064-05 — adr-accept-gate
pass: arch
verdict: pass
reviewer: arch-review
reviewed_at: 2026-06-08T20:39:14Z
prompt_source: review.py arch-review (064-05, arch_review:true; re-reviewed after blocker fix)
---

VERDICT: pass

REASONING:
Architecturally sound: the ADR evidence subsystem cleanly parallels the slice-side one (path/validator/schema); parameterizing parse_verdict_file with required_fields is the right minimal seam; moving evidence_gate_enabled to _common is the correct consolidation (load-bearing consistency — two gates that MUST read the bypass identically — not premature rule-of-three; _common.review_evidence stays a leaf over _common.parsing, no import cycle); gate placement at cmd_accept is precise (supersede operates only on already-Accepted sides; new/index/resolve-todo untouched; runs before any Status mutation); the OQ3-stamp-plus-grace-marker design makes "ADRs always-on" hold going-forward while grandfathering legacy ADRs.

HISTORY: The shared [blocker] (frame-critique prompt builder unreachable for ADRs — the gate's own advertised remediation command failed) is resolved: the frame-critique CLI now accepts an ADR target and the gate advertises a resolvable path. Re-review confirmed end-to-end.

STRENGTHS:
- Shared bypass predicate consolidation (no drift).
- ADR evidence parallels slice layout faithfully (reviews/ beside artifacts; adr-keyed schema; same "name the missing artifact + command" diagnostic).
- Grace path clean + forward-only (stamp at creation chokepoint; gate on the marker), matching the default-off pattern of the rest of the evidence model.

OPEN QUESTIONS:
- (resolved during review) ADR frame-critique prompt mode is now in-scope + shipped, closing the gate↔builder contract gap.
