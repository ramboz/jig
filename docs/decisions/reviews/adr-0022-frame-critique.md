---
adr: 0022
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer
reviewed_at: 2026-06-09T21:27:55Z
prompt_source: review.py frame-critique docs/decisions/adr-0022-pluggable-oracle-boundary.md
---

## VERDICT
needs-changes

## REASONING
(Second, independent frame-critique on the revised ADR — supersedes the first.) servo-side facts are now meticulously grounded and self-correct the prior over-claim (exit contract, gate.py --json fields, no per-component map, 006 DRAFT + Non-goals, coupling model — all verified against servo source). But the *frame* rests on one assertion the evidence does not support: that "the signal has arrived" to resolve ADR-0019's OQ2 now. ADR-0019's own named trigger is demand-side ("≥2 eval-oracle refactors where the attest-only posture proves too loose"), not supply-side ("a sibling tool now exists"). The ADR ships the binding for the deterministic path (where routing through servo *downgrades* jig's existing tdd.py machine-witnessing to attest-only) while the motivating eval/AC path is conceded unbacked (servo 006 DRAFT). One Assumptions claim presented as *verified* is false on jig's own disk.

## SPECIFIC ISSUES
- Primary (frame): "The signal has arrived" conflates tool-availability (supply) with demonstrated need (demand). ADR-0019 defines the integrate-on-signal trigger as >=2 real eval-oracle refactors straining attest-only; the ADR presents no such case (the only worked example, CWV, is external/hypothetical AND an eval oracle the ADR classifies as not-shipped). So the binding ships for the deterministic path and defers the path that motivated it — Option B's "premature" critique landing on Option D. Fix: cite a concrete refactor/bug that strained attest-only eval, OR reframe the trigger as "a contract is now available to bind to" (supply) and reconsider whether 0019's schema-only deferral should hold until a real eval case appears.
- Grounding error (must-fix): the ADR claims jig's slice-land prepare "already emits soft pull-hints for servo artifacts" and the Assumptions section calls it "verified." Grep of jig's skills/ (incl. slice-land/land.py + SKILL.md) for servo/oracle returns no matches — the pull-hint does not exist in jig's code; the only "hint" in land.py is a git pull/rebase recovery message. The claim's source is servo's README describing what it expects jig to do; the ADR took servo's self-description as ground truth for a jig-side behavior, and cites it 3x as the precedent / reciprocal-symmetry justifying Option D over C and grounding the §5 discovery. Either the pull-hint must ship (an un-scoped jig change) before it can be cited, or downgrade "existing/verified" -> "planned reciprocal."
- Secondary (disclosed, sharpens the frame): for a deterministic equivalence oracle, jig today shells to tdd.py and machine-witnesses green-before/green-after (real teeth); routing through servo's composite makes jig attest-only. So oracle: servo on the deterministic path trades stronger teeth for normalization+discovery — strictly weaker for the one case the ADR calls "real today." Disclosed in §6, but the Consequences "becomes easier" framing obscures that the only fully-backed path is also where the binding downgrades jig's existing teeth.
