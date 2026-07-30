---
adr: 0039
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer subagent (frame-critique pass 3 of 3)
reviewed_at: 2026-07-27T19:01:22Z
prompt_source: review.py frame-critique docs/decisions/adr-0039-richer-skill-discovery.md
---

Third adversarial frame-critique of ADR-0039. Verdict recorded as returned
(`needs-changes`) — NOT upgraded. Both findings were addressed in the ADR after
this verdict was issued; no fourth pass was run.

## Findings and disposition

**Primary — the option set contained no config-only option, and the ADR builds
the least-guaranteed layer first.** The reviewer noted every option (A–D)
inherited the product-vision "wins without configuration" axiom, while the ADR
itself concedes config is the only guaranteeing path and every kill criterion
falls back to it. ADDRESSED: added **Option E (config-only)**, ruled out
outright but explicitly adopted as the *first slice*; **re-sequenced §6** so
slice 1 ships precedence rule 1 alone (closes the reported bug
deterministically, both hosts, no OQ6 dependency) and the zero-config
enumeration + selection layer lands on top of a working floor. Also recorded
that the vision axiom is *partially falsified* by this ADR's own evidence
(ranking genuine candidates is not derivable from descriptions), so it is no
longer treated as unconditionally true.

**Secondary — the anomaly signal is noisy in one direction and blind in the
other.** Computed off a deliberately recall-only nominator, it fires on
nomination noise (on the probed corpus a legitimate `none` would trip it via
`morning-github`); and if recall fails entirely, nothing is nominated, no
anomaly fires, and the originating bug recurs silently. ADDRESSED: added a
**calibration requirement** (fire only against the candidate set the
orchestrator was actually shown and declined; record that set), corrected the
claim that matcher precision no longer matters (it still governs the anomaly
surface's false-positive rate), and recorded the **recall blind spot as a real
accepted gap** with no automatic instrument — with config-first sequencing as
its mitigation and kill criterion 3 explicitly marked as user-report-only.

## Note on pass 2 and the recorded override

Pass 2 argued for dropping Option D in favour of Option C's stricter
deterministic matcher. That finding was deliberately overridden by the project
owner (overfitting of a hand-tuned matcher judged the greater risk); the
override, the reviewer's reasoning, and the accepted residual risk are recorded
in Recommended Decision §3a. Pass 3 did not re-raise it and instead attacked one
level up — whether zero-config pickup is the right goal at all.

## Why the ADR was accepted at `needs-changes`

The findings were addressed rather than dismissed, and the remaining exposure is
recorded in the document (accepted gap + kill criteria) rather than hidden. The
frame-critique gate was bypassed deliberately via `JIG_REVIEW_EVIDENCE_GATE=0`
with this artifact as the audit trail, per ADR-0011's deliberateness model.
