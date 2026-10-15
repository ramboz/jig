# Genuine component-pass / overall-quality-fail attestation

Fresh read-only `jig:reviewer`, 2026-10-15. Verdict/reasoning below are the
actual response to generated `119-01-quality-fail-prompt.txt`; the preserved
reference summary follows. This is a negative interoperability control, not
final-current completion proof.

VERDICT: fail

REASONING:
For the quality-fail fixture, run `01ec10a8-62fe-448a-81d7-25c06a0e45a7`
preserves an authoritative overall `fail`, exit `1`, reason
`quality_below_threshold`, despite component success and all 28 required
passes. The producer-recorded composite is `0.5120652827881754` against its
frozen threshold `0.8`; retained native requests/responses support a genuine
completed quality evaluation, not an infrastructure error or fabricated
scalar. The preserved overall failure is independently sufficient to refuse
clearance, irrespective of the audit-coverage limitations identified above.

SPECIFIC ISSUES:
- `gate.json:1` — Overall policy explicitly fails with
  `quality_below_threshold`. Component passes cannot override this verdict;
  clearance requires a new completed producer run satisfying the approved
  policy, not alteration or rescoring of this record.

## Preserved references from the response

Target: `/Users/ramboz/.copilot/session-state/a7784cf6-9f09-4776-8660-bffeb3559e50/files/036-01-fixed-misalignment`.
Run: `01ec10a8-62fe-448a-81d7-25c06a0e45a7`.
Gate/component/envelope raw SHA-256:
`f7da633743bdfcec81442ec676ea359bad157f63b6af42d4898503cf45b3412d` /
`a830f3150bb8d9bab09f5b807f48c9ce96188001a0515c2626ff1c646d1ad81c` /
`957bc02dee7e65a8ca1f6b61aa0cb4a5406bfc99264e34c9b06983fdaabda45d`.

Selected installed pin and gate policy:
`34eca4af08447a36149c6c210046643e46c7ce73d9fc532144a23424cbdd58f6`.
Quality raw config / definition:
`72d9e45f9f642f6596c21430274349cbeff20afa04e546cefd05915db2fddf70` /
`2aecc532eb4fbf763da26c87128dc51892ce5c562e7869ce32030f46e10473b7`.
Input/output domain identities:
`7dc8d46f65391c20cb2c6265b3b84ba7ddeb5d79187a56c8097dab00c9f42ae1` /
`ae17dc2ba4c7f3369f333a9468c0f11422b67d53d3f2f3e666b56ca1a99cc1a2`.
Current/sealed output, independent delivery and both loaded responses agree
on `index.html` raw hash
`ac497e6621b968f394f0016923ac38902369451b2fde5e9c7f9fe8f113ea9275`.

All 28 condition IDs/outcomes are the two-prefix inventory in
[positive-attestation.md](positive-attestation.md), each pass, same index
mapping. The failing authority is overall quality, not a deterministic
condition. Invocation/claim/receipt, observations and retained quality
attempts 10–17 support completed execution within trusted-local limits;
native responses report `claude-opus-5`, not immutable provider authentication.

The 175-comparison audit reports no mismatches but shares the baseline
audit's frozen-input coverage gaps. No evaluation was rerun or composite
recomputed. No high-composite-required-failure, inconclusive case or pilot
completion is claimed. Later producer execution-closure sealing applies
to future completion proof, not a rewrite of this historical run.
