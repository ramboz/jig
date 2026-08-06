---
adr: 0051
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-06T05:00:49Z
prompt_source: review.py frame-critique docs/decisions/adr-0051-autonomy-governance-plane.md
---

Frame-critique of ADR-0051 (autonomy governance plane). Ran three adversarial
passes. The first two returned needs-changes and surfaced two real frame gaps,
both fixed before this pass:

1. **Inert-without-arming.** The ADR overclaimed scaffolded CODEOWNERS + CI as
   "real enforcement" when those files enforce nothing until server-side branch
   protection (require-status-check + require-Code-Owner-review + forbid-bypass)
   is armed — a setting scaffold-init cannot commit. Reframed: jig scaffolds the
   files and documents the out-of-band arming step; the readiness gate verifies
   the armed state; files are never advertised as enforcement alone.
2. **Name vs capability + self-reference.** The readiness precondition keyed on
   identity-name distinctness; reframed to key on merge *capability*
   (distinct-name necessary-not-sufficient; over-privileged distinct bot is
   unsafe), over supplied/attested inputs (jig does not probe GitHub in-process),
   failing safe when the capability signal is absent. The protected-paths set now
   includes `.github/workflows/**` and `CODEOWNERS` itself so the self-reference
   the Kill criteria demand holds by construction. Added the ADR-0011 posture
   note: the readiness gate is advisory (inside the agent trust boundary); the
   real teeth is credential absence.

Final verdict: PASS. Enforcement is correctly located in branch protection, not
the bypassable CI file or the local hook; ADR-0011/0013 posture intact; frame
internally consistent across ADR, spec, and slice. Residual (non-blocking,
carried to the implementer): pin whether the CI job checks approval *state* or
merely flags protected-path touches for owner review, to avoid re-asserting
enforcement branch protection already owns.
