---
slice: 096-01 — config-precedence
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer subagent (frame-critique pass)
reviewed_at: 2026-07-28T02:08:34Z
prompt_source: review.py frame-critique
---

Frame-critique of 096-01 returned **needs-changes**.

**Primary (orchestrator-verified against the tree).** The slice's DoR asserts
as ✅ that all five extensible passes exist as `review.py` prompt-builders.
False for three of them:

- `review.py` defines builders at :617 (pr-review), :755 (arch), :858
  (code-health), :1094 (design) — and **no security builder at all**;
  `subagent-type` (:1724) enumerates no security mode.
- `skills/security-review/SKILL.md:71-72` — "The deferral is a router hint,
  not a filesystem probe."
- `skills/bug-fix/SKILL.md:232` — there is "**no** `review.py pr-review` call
  for a bug", so bug-fix's craft pass cannot inherit `review.py`-mediated
  config resolution as spec.md:28-30 claims.

Consequence: `review.<category>_skill` is guaranteed on 4 surfaces and only a
prose nudge on 3 — the inert-prose class ADR-0039 §3 rule 2 explicitly forbids.
AC6 (record the applied skill) is unreachable on those surfaces for the same
reason. The residual gap lands on security, the category ADR-0039 Context §3
named as the user's real concern.

**Secondary.** AC2's hard-fail on an unresolvable configured name conflates an
authoring-time typo with runtime absence on another machine. `scaffold.json` is
committed and team-shared while AC1 resolves bare names against per-machine
user scope, so a teammate or CI runner without the install gets a typed error
on every review pass — blocking the ADR-0014 REVIEWED gate. This reverses
`review.py:571`'s documented "never block the craft/arch pass" posture and
contradicts ADR-0039 §3 rule 4.

**Secondary.** The slice ships zero behavior change in jig's own repo (no
`scaffold.json`), so the "closes the reported bug" claim cannot be dogfooded
end-to-end — worth stating explicitly rather than leaving it in an edge-case
bullet.
