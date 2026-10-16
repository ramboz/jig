# Fresh sealed-epoch negative attestations — 2026-10-15

Actual fresh read-only `jig:reviewer` batch response, compiled below without
changing its per-case verdicts or reasons. Two genuine final-code executions
and thirteen explicitly labelled copied-result mutations are distinct.
Original producer artifacts were not changed; no evaluator was executed
or score recomputed by this Jig lane.

VERDICT: fail

REASONING:
The canonical quality-control attestation is fail: run
`2de07bf5-fc61-482d-bcf8-1dbc11ec2d5e` explicitly records
`quality_below_threshold`, exit1, and `0.5278427304671842 < 0.8`, despite
component success and all28requiredpass. The genuine ambiguous-acquisition
run is non-clearing env_error with unavailable quality, not a zero score.
Every labelled copy also fails to establish clearance. These are selected
evidence verdicts, not a failure of the negative-fixture concept or a
whole119 compliance determination.

## Actual per-case response

`B` = `cbe6b5b3-a60f-4dc1-abb9-23a8fd6f48a2`;
`Q` = `2de07bf5-fc61-482d-bcf8-1dbc11ec2d5e`;
`A` = `dc9e9733-67de-4b1a-ac53-5643c4d05318`.
Each copied record is session `119-01-labelled-controls/<case>.json:1`;
its exact path/raw pin is in the preserved manifest. Copies are not
producer executions.

| Case | Actual verdict | Run | Concrete observed reason |
|------|----------------|-----|--------------------------|
| genuine-quality-fail | fail | Q | Explicit overall fail/exit1/quality_below_threshold; quality0.5278427304671842<0.8; component/28requiredpasses cannot override |
| genuine-inconclusive | needs-changes | A | Overall env_error2/required_evidence_unavailable;6pass/10fail/12unknown; normal-title-colour missing or ambiguous bound observation; quality unavailable |
| required-missing | needs-changes | B | open-title-text absent from required.items despite mandatory policy inventory; retained pass counts do not supply missing result |
| required-unknown | needs-changes | B | normal-band-fill unknown while overall/count summaries claim pass |
| required-not-run | needs-changes | B | Required normal-band-fill not-run; unsupported/nonconclusive required-item outcome |
| required-inconclusive | needs-changes | B | Required normal-band-fill inconclusive; cannot inherit retained overall pass |
| required-env_error | needs-changes | B | Required normal-band-fill env_error; no alternate namespace/scalar fallback |
| unsupported-gate-namespace | needs-changes | B | Actual gate schema99 versus selected integer schema2 |
| absent-overall-verdict | needs-changes | B | Top-level status absent; exit0/component/composite cannot substitute |
| absent-component-reference | needs-changes | B | spec_oracle_card.result null; subordinate path/hash link missing |
| unreadable-component | needs-changes | B | Direct read confirms intentionally absent not-present-component.json; contents/digest unknown, not fabricated evaluated failure |
| component-digest-mismatch | fail | B | Recorded64zerohex versus exact preserved component6ea44cd3… |
| component-run-mismatch | fail | B | Referenced copy run00000000-0000-4000-8000-000000000000 versus gate/output B; honest new copy digest cannot repair run mismatch |
| overall-pass-required-failure | fail | B | normal-band-fill fail but overallpass/exit0/composite0.97/28passsummary and unchanged subordinatepass: contradiction, not genuine required-failure execution |
| overall-pass-quality-failure | fail | Q | Copied overallpass/exit0 conflicts with retained actual quality_below_threshold/0.5278427304671842<0.8; misalignment context |

## Selected contracts and bindings

Source `6cc759e807cab5411363b44c19c58e7a457b3715`; producer-owned contract
and installed runtime define separately namespaced Vellum
`vellum-design-input/0.1-pilot`, gate2, component1, command-output1,
design-envelope1 and quality-config2. Component-envelope1 never selects
legacy gate semantics.

Independent pre-result contexts under parent session files:
`036-sealed-misalignment-independent-context.json` raw
`bd09affabe5e8e8853599389875939e64b67ce5d3a93903b04326bd14632b355`;
baseline context raw
`a08b529026a3a81f1a2e414b87fb654a34ee7ab2a570b34fce15b5a79131b32d`.
They select roots/raw policy/checks/config/full-oracle/source/build/delivery
pins before results, not from the envelope. C1 approval raw
`d4322d16444bba75f6e4384430284595ecf2b203f4278c3ac0fda9564f8c4c5b`
is fixture-scoped agent source approval, not authenticated human approval.

Q's selected installed policy raw pin matches gate policy
`97280db6762bcfd8f138dc0ec460ad6a731fa086fa81990ed09ba6cd124e4ba7`;
selected quality config matches envelope
`bbc445f5722daa7b9878195554140afa2b334d4514ca57f239da2817f70933d5`.
Source/current build/sealed output/loaded response/independent delivery
agree on index.html raw
`ac497e6621b968f394f0016923ac38902369451b2fde5e9c7f9fe8f113ea9275`,
output-domain identity
`ae17dc2ba4c7f3369f333a9468c0f11422b67d53d3f2f3e666b56ca1a99cc1a2`.

Q gate/component/envelope raw pins:
`3020a4b26677899972b7c99e3d61821f27911ce4677b1f74f7f11045a8b85f07` /
`1e95a19ea6823574ed865ad68b2c8fc9b7ece6521c6880d96e5c11ec72fe76fd` /
`f96865c25384e9a73e234e0cf3335b2632eb5fa0155d046213fa41c22dcd8382`.
A gate/component/envelope raw pins:
`79a6ad30093c42ddbb12ddfa60c9fcd566e7313a6c0f860f07c2174cff5a7b38` /
`254ed11b62d0531777da82aed7281508f550bd64b77536599bf5e06dd101466b` /
`a4cb9349542e9d06a8e5202cbb679229c52ed82c9a2494de34ca4e4a052e1032`.

Paths: proof root is
`/Users/ramboz/.copilot/session-state/e33c1f8d-6be8-4fb4-8801-6cfe7838aa5c/files/final-proof-6cc759e`;
Q target `misalignment`, A target `baseline`;
gate `.servo/gate-runs/<run>/gate.json`, component
`spec/oracle/card/runs/<run>/result.json`, envelope sibling
`design/evidence.json`. A independently selected pre-control context raw
`fc356d976c174a0c529e8146bd456587f2f58027b1517bff740021ea8a982f05`
chooses candidate-ambiguous/builds/ambiguous/delivery-ambiguous; temporary
inputs were restored. A is not the currently selected positive delivery.

## Required coverage, execution and limits

Required IDs: for each `normal-`/`open-`, band-fill/height/width;
subtitle-colour/font-family/font-size/font-weight/text; title-colour/
font-family/font-size/font-weight/presence/text. Q records all28pass.
A records6bandpasses/10subtitlefailures/12titleunknowns, linked by component
indices/envelope observations; no optional-outcome veto was added.

Q has actual invocation, matching acquisition claim/receipt nonce and
envelope hash, served-response closure and eight retained native requests/
replies, invocations34–41. Real wrapper calls card_evidence quality; inspected
native reply completed with CLI usage claude-opus-5. Full audit covers all
eight bindings; no synthetic constant substituted.

Q full audit raw
`4f995e3a0b0056039c12e03a4b30a84adeeb1251ccaa30097d5fa6a9a83e0c14`
preserves4175matching comparisons without regrading. Jig's separate
3941raw-pin comparisons, including3887runtime files, also match.
Raw file references versus named Servo LF and Vellum NUL semantic domains
are not conflated. Preserved read/hash evidence is trusted-local, not
forgery-proof provider attestation. No fresh execution/capture/grading
occurred; no genuine high-quality required-failure or whole119 completion
was claimed by this review.

RECONCILIATION NOTES:
The reviewer found the copied quality-contradiction manifest's generic
"baseline context" wording inconsistent with its explicit misalignment
context. The fixture body was correct. The orchestrator preserved the
reviewed manifest unchanged as `119-01-labelled-controls-manifest-as-reviewed.json`
(raw `f0ad12d72d2b1199b130a7f2514b7d430544e1671792ac324cc90b45afe2bbd8`),
then corrected only the current manifest/generator wording; no copied
gate or original producer result changed. This disposition is not a new
reviewer verdict.
