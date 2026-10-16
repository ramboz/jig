# Fresh sealed-baseline attestation — 2026-10-15

Actual fresh read-only `jig:reviewer` response to the generated design-review
prompt for the isolated sealed-baseline fixture. The original nonpassing
[prior-epoch baseline](positive-attestation.md) is preserved, not rewritten.
This response is recorded unchanged below; a baseline pass is not whole-slice
compliance or final completion.

VERDICT: pass

REASONING:
For the isolated sealed baseline, run
`cbe6b5b3-a60f-4dc1-abb9-23a8fd6f48a2` preserves an authoritative
`gate_result` schema-2 pass, exit code `0`, reason `null`, all 28 required
outcomes passing, and producer-reported quality `0.97` against frozen
threshold `0.8`.
The selected Vellum pilot contract, schema-1 component/output/envelope records,
and separately versioned schema-2 quality configuration are consistent; the
gate/component/envelope raw digests match their selected references:
`c4f3d3714d6615fac0d7072904338b0b46992735bfd5c15328c0145e46dcd5b9`,
`6ea44cd3f4800c91152e6ea328ab7611452b9c8e4a611b11aa64ef0ee34bc640`,
and `0d07ec41cdd9dc74deae5cc0ac431decf654192147ae9a4a3ba4f25cd336b17f`.
Inspection of the independent audit script and preserved comparisons supports
the preselected approval, effective-policy/configuration, source/build/delivery
and served-byte bindings: 4,112 matching comparisons, including all 3,887
declared nested runtime files, complete output inventory, acquisition
nonce/receipt, and unchanged full-oracle/raw-checks pins.
The preserved requests and eight native successful responses support completed
execution, with CLI-reported `claude-opus-5` identity and pinned Claude CLI
`2.1.300`; this is trusted-local consistency evidence, not authenticated
execution, human approval, or a newly derived score.

RECONCILIATION NOTES:
No new baseline-contract deviation identified. The staged draft-checks digest
and subsequently approved raw-checks digest have distinct, documented scopes.
This pass does not certify fixture lifecycle completion, other review
prerequisites, full 119 AC3/4/6, or the whole pilot as DONE.
