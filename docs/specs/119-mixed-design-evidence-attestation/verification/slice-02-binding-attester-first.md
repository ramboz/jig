VERDICT: needs-changes

REASONING:
The preserved run `cbe6b5b3-a60f-4dc1-abb9-23a8fd6f48a2` supports the original semantic pass: overall exit 0, quality 0.97, and all 28 required outcomes passing. The inspected audits support hashing all 3930 selected runtime references, including all 3887 actual current external runtime files—not merely their manifest. However, the new wrapper omits an installed executable binding, and its audit does not establish complete mirrored output-byte equality; I do not authorize recording THIS proposed body/block yet.

SPECIFIC ISSUES:
- `freshness-bound-proof/reviewed/context.json:19925–19929` — The wrapper pins the producer's `quality-gate/required_runtime.py`, but nowhere pins **`project/.servo/required_runtime.py`**, which the copied `oracle.sh:66` executes. The original independent PRE-RESULT context explicitly pins that installed file. Mutating this copied executable would escape the selected closure. Add its original raw pin, `sha256:f0f9d90cf7c0f25c5f7163966ae9cfd8010261522f9842438da67622aa858bfe`, and renew the wrapper/context attestation.
- `audit-bound-proof.py:114–119` — The output check compares declared inventories against envelope entries without enumerating and raw-hashing the actual mirrored output directory. The frozen-index audit hashes the **original** bundle, not this mirror. Supply a preserved pure read/hash comparison of the complete 39-file mirrored output tree, including captures/native answers and rejection of extra files or symlinks. This is an evidence gap, not an observed byte mismatch.

RECONCILIATION NOTES:
Retain the disclosed disposable transport-mirror and synthetic lifecycle-prerequisite limitations. These findings concern initial wrapper completeness only—not a failed producer verdict, new evaluation, whole-119-02 compliance decision, or authenticity certification.
