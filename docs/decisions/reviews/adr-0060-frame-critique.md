---
adr: 0060
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer (Opus, 2 fresh rounds)
reviewed_at: 2026-09-08T19:03:12Z
prompt_source: review.py frame-critique docs/decisions/adr-0060-unattended-execution-write-boundary.md
---

Two fresh-context adversarial frame-critique rounds (jig:reviewer, Opus —
equal-or-stronger than the Opus author per ADR-0020), each reading the ADR plus
linked ADR-0011/0013/0022/0051/0059 and verifying the state claims against
`hooks/hooks.json` + `skills/scaffold-init/governance.py`. Verified-state
grounding confirmed sound in both rounds (no PreToolUse `Bash` matcher;
`identity-check` is report-only, exit 0/3/2 — not an in-process block).

## Round 1 — needs-changes (addressed)

Finding: the ADR conflated "unattended" with "servo-driven" and assigned the
hard-deny owner solely to servo, leaving the jig-native (ADR-0051-bridge,
servo-absent) unattended path with no enforcer while claiming the gap was "closed
by construction." ADR-0011 itself frames unattended operation as a mode not
predicated on servo.

Incorporated: added Decision point 4 broadening "unattended" beyond servo; de-biased
Open Question 1 (a servo-written mode signal is spoofable because servo *is* the
governed loop — the identity-check lesson).

## Round 2 — needs-changes (addressed)

Finding (deeper): the round-1 fix still didn't hold — server-side branch
protection gates *merge only*, not push+PR (the ADR's own Option-D con),
`identity-check` cannot block, and point 3 forbids jig's skill layer owning an
in-process hard-deny. So for a servo-absent jig-native run with unarmed
protection, the asserted "fail-closed / stop the run" had no executor: the
push+PR boundary stayed as open as status-quo Option A, contradicting the
closure claim.

Incorporated: reframed the enforcer as the run's *executor* — a trust domain
separate from the driven agent (servo, or the jig-native orchestrator/harness as
the servo analogue), an executor-level control distinct from jig's skill/hook
layer and therefore not forbidden by the point-3 coupling rule. Added Decision
point 5 (honest boundary): where no executor-level enforcer and no armed
server-side backstop exist, jig cannot close the push+PR boundary and does not
pretend to — the posture there is "do not initiate unattended," with jig making
the missing enforcer loud/checkable (point 3d). Narrowed the Consequences closure
claim, added a "Becomes harder" bullet (the jig-native executor enforcer is
unbuilt), and pinned the write-boundary terminology (push+PR vs merge) as
load-bearing (Open Question 2).

## Status

Verdict recorded as **needs-changes**: no reviewer has read the post-round-2
revision, so no `pass` has been earned on the final text. The revision converts
the flaw into an explicitly-owned residual (Decision §5 + Open questions) rather
than a hidden overclaim — the honest frame the pass demands — but per the
ADR-0020 accept-gate, acceptance requires a fresh frame-critique reaching `pass`
against the final text. The ADR is deliberately left **Proposed** (acceptance
deferred until the servo pilot is first scheduled unattended, per the
refinement-todo "Operations" entry). This evidence records that the adversarial
read happened and what it changed; it is not an approval.
