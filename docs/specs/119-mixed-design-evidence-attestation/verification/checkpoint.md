# 119-01 implementation and refusal checkpoint — 2026-10-15

**Historical snapshot at 492f128d.** The records below remain evidence of
the actual initial nonpassing reviews. Subsequent genuine sealed-epoch
evidence is recorded in [sealed-proof.md](sealed-proof.md); it resolves the
named evidence gaps without relabelling or rewriting the old runs.

The source cut is implemented; **the slice is not complete**. It remains
IN_PROGRESS. Compliance is `needs-changes`; supporting craft and architecture
reviews pass for the code cut only. No REVIEWED/RECONCILED/DONE move is earned.

## Exercised code and tests

Base: `dcfcbc5eb8bfaac8f3cf11405a5e6b6f254d5c98`, stacked on
`jig-mixed-evidence-attestation`. The reviewed uncommitted source/guidance
diff (four files: `review.py`, `test_review.py`, `SKILL.md`, `docs/workflow.md`)
has SHA-256 `38c0df03b490a9f279830b56d1e0c8055e3ca65f9637ffb111ab2f3497f0970c`
using `git diff -- <those paths> | shasum -a 256`.

Implementer preserved witnessed red/green results in `119-01-tdd.txt` under
the session artifact root below: eight tests witnessed red then green;
two synthetic verdict-rail tests intentionally started green because that
rail already worked. Final scoped runs: 289 independent-review tests,
103 review-evidence tests, 30 workflow design/transition tests and 18
host-package tests, all passing. Syntax, strict slice lint and official
three-host regeneration/drift check pass. Direct Ruff was initially unavailable;
the orchestrator subsequently ran the existing ephemeral tool path,
`uvx ruff check skills/independent-review/review.py skills/independent-review/test_review.py --output-format concise`,
successfully. A subsequent orchestrator run of the 29 changed-surface tests
and host drift also passed.

Synthetic fixtures assert prompt shape and existing verdict handling, not
the producer's grading or genuine AC completion. The craft review's
nonblocking redundancy nit about the 15 synthetic refusal reasons is retained;
none is counted as semantic producer coverage.

## Genuine producer reads and actual lifecycle refusals

Session artifact root:
`/Users/ramboz/.copilot/session-state/c049095e-5c63-4af4-9e9a-dfd233c5e669/files/`.
Producer artifact root:
`/Users/ramboz/.copilot/session-state/a7784cf6-9f09-4776-8660-bffeb3559e50/files/`.

| Scenario | Actual fresh attester | Existing rail observation |
|---|---|---|
| Genuine `b6e14da1-40da-4e76-b37d-580eb3e82844` overall baseline | `needs-changes`: audit closure incomplete, not a fabricated passing attestation | `record-review` preserves body; `check-reviews --stage REVIEWED` and transitions to REVIEWED/DONE refuse on design-review |
| Genuine `01ec10a8-62fe-448a-81d7-25c06a0e45a7` component pass / quality fail | `fail`: `quality_below_threshold`, `0.5120652827881754 < 0.8` | Same observed refusal, retaining responsible quality/run references in the recorded body |

Actual attester summaries:
[baseline](positive-attestation.md), [quality failure](quality-fail-attestation.md).
`119-01-rail-proof.py` invokes only Jig `record-review`, `check-reviews` and
`workflow.py transition` against isolated flagged session fixtures. Unrelated
reviews are explicitly synthetic harness preconditions, as the scenario
requires; they are not claims of actual application compliance. Fourteen CLI
observations matched expected exits: eight recordings exit0, two checks exit2
and four transitions exit2. Both fixture states remain IN_PROGRESS. No
producer/evaluator import, execution, capture, score computation or judge call.

Runnable local commands:

```bash
python3 /Users/ramboz/.copilot/session-state/c049095e-5c63-4af4-9e9a-dfd233c5e669/files/119-01-rail-proof.py
python3 skills/independent-review/test_review.py DesignReviewPromptTests DesignReviewEvidenceRoundTripTests RichDesignReviewGuidanceTests
python3 scripts/build_host_packages.py --check
```

An attempted `check-reviews --stage DONE` revealed that CLI supports
READY_FOR_REVIEW/REVIEWED/RECONCILED only; it was an argument error, not
design-refusal proof. The corrected script exercises DONE through
`workflow.py transition`, where the actual design evidence is revalidated.
No production change was necessary.

## Preserved raw-byte artifact identities

| Session artifact | SHA-256 |
|---|---|
| `119-01-read-hash.py` | `3f098a2b248f49ae8be332051824ec04281a9d5327f0ececd2a1c0cae20512fe` |
| `119-01-positive-audit.json` | `7cd8bc194f1252eb13a1d441482f3f6d0d07c6e604c033f27168643f85185b44` |
| `119-01-quality-fail-audit.json` | `7b0ba8aff6ed77dc5d94caa21745aecb1a55d34cbbda1d35a30ec16166a34651` |
| `119-01-rail-proof.py` | `1621f05bfee00b9c3cc68fa6acde249aa6105c5ae3f6e089cbb1b8b969cc4a94` |
| `119-01-rail-proof.json` | `4e8368fa5d6730e8a44f8143293023c6394f1cb7d6aca84857c84290d5f99c00` |

The initial audits compare 175 raw-reference/domain bindings each with zero
mismatches. That is **not complete closure**: the attester correctly found
missing independent raw `checks.json` and nested runtime-file comparisons.
The audits are preserved unchanged as the evidence actually reviewed.

## Exact requirements for renewed completion evidence

The producer's independently selected positive context
`036-01-independent-current-context.json` has raw SHA-256
`712ee2decae6d6ea9bcca3eb421f0d2358d8b5d93448b379048a4a175ce3019c`.
It explicitly selects source `candidate/`, build `builds/baseline/`,
delivery `delivery/`, selection, approved C1 source/approval and frozen
policy/config/checks/review files. Future contexts must be independently
selected and pinned the same way; never initialize expected values from the
envelope being attested.

Before a new pass, obtain the final producer head and reapproved frozen
context, then read/hash **all** declared closure, including:

- Raw checks bytes versus the separately selected expected pin, approved
  effective checks binding/content identity, installed required-policy pin,
  threshold_default exactly `"0.8"`, quality config/definition and source
  approval. Raw file SHA-256 and semantic domain identities are distinct.
- Nested `runtime-files.json` executable/browser/dependency file references
  and complete file inventories, not only the manifest's own digest.
- Exact installed `oracle.sh` execution-wrapper bytes in the producer's
  existing evaluator-artifact closure, with staged independent driver
  review/reapproval. Generic driver identity alone did not cover the SEED
  scalar-quality wrapper. Await actual producer-owned keys; invent none.
- Separately chosen source/dirty-input/build/runtime/config/assets/dependencies
  and delivery bytes, sealed input/output manifests and loaded served response
  hashes under `servo-input-closure-v1` / `servo-output-closure-v1`.
  Servo semantic canonical JSON is UTF-8, sorted keys, compact separators,
  ASCII escaping and finite native numbers, with domain + LF prefix where
  defined; Vellum's own namespaced domains remain separate.
- Full gate/component/envelope/capture references, independent acquisition
  receipt, complete required-policy inventory, explicit overall quality
  verdict and preserved genuine invocation/raw requests/replies. Read/hash
  only; never recompute a weighted score or run a producer.

Need renewed genuine baseline, high-composite/required-failure, inconclusive
and component-pass/quality-fail evidence with appropriate independently
selected contexts, actual fresh attestations and attributable fixture CLI
traces. Existing diagnostic controls are explicitly synthetic-quality
negative runs, not genuine live quality judgments. No further judge calls
are authorized or performed by this Jig lane.

The producer is now sealing the execution wrapper. Both reviewed captures
remain honest historical interoperability evidence, not final-current proof.
Do not rewrite them, change their pins to turn green, waive ACs, require all
Servo036 DONE to start, or advance Jig119 lifecycle while these obligations
remain. 119-02 automatic reuse freshness and 119-03 broad legacy are untouched.
