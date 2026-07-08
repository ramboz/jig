---
slice: 078-01 — emit bypass events
pass: frame-critique
verdict: pass
reviewer: Explore (jig frame-critique)
reviewed_at: 2026-07-08T21:14:35Z
prompt_source: review.py frame-critique
---

Adversarial frame-critique of spec 078 / slice 078-01 (emit bypass events), run retroactively during the shipped-ahead-of-slicing reconciliation ceremony (2026-07-08).

Both load-bearing assumptions verified TRUE against the shipped code:
- **A1** — the shared `.claude/skill-usage.jsonl` sink carries a new `gate_bypassed` event type without disrupting `routing-stats` readers. `routing_stats` already filters to `skill_invoked` (workflow.py:2078, a documented load-bearing invariant); `gate_stats` filters to `gate_bypassed` (workflow.py:2170); the emitter writes the `event` discriminator (gate_telemetry.py:41-46). Legacy rows without an `event` key are skipped by both.
- **A2** — spec 056's `.jig/spec-ref` marker is best-effort: `read_spec_ref` returns "" on any miss, the emitter only adds the field `if spec_ref:`, and `emit_gate_bypass` swallows all exceptions, so absence never blocks the emit (both call-sites at workflow.py:896 + jig-spec-gate.sh:66-69).

Both assumptions were also hedged in the spec (A1 pre-registered a probe-back + sibling-JSONL fallback; A2 marked best-effort/non-blocking), so even a miss would have degraded gracefully.

VERDICT: pass

Findings:
- [strength] Load-bearing claims were hedged (probe-back + fallback), not merely asserted.
- [nit] A1 is scoped to "routing-stats readers", but the sink now multiplexes three event types; any consumer not filtering by `event` (e.g. scripts/usage.py, the skill-routing-verification verifier) is a latent risk. (Follow-up confirmation recommended — captured in deviation log.)
- [nit] The gate env-vars are agent-settable by design, so counts measure "flag set at gate time", not "deliberate human bypass" — an over-interpretation risk that lands on 078-02 (addressed there by the override-frequency reframe).
