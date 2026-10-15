# Genuine baseline attestation — non-clearing

Fresh read-only `jig:reviewer`, 2026-10-15. The following verdict, reasoning
and issues are the actual review response, not an orchestrator-invented pass.
Source: generated `119-01-positive-prompt.txt` against the isolated flagged
fixture. This is interoperability evidence, not final-current completion proof.

VERDICT: needs-changes

REASONING:
For the positive fixture, run `b6e14da1-40da-4e76-b37d-580eb3e82844` preserves
an authoritative overall `pass`, exit `0`, quality composite `0.9675`,
threshold `0.8`, and all 28 required passes. The independently selected
source/build/delivery comparisons agree within the supplied audit, and the
invocation, acquisition receipt, observations and retained native responses
credibly support completed execution under the stated trusted-local model.
However, the audit's 175 successful comparisons do not cover all selected
frozen-input references, so I cannot attest the entire predicate. This is an
evidence-coverage refusal, not an observed delivery mismatch or a replacement
score.

SPECIFIC ISSUES:
- `119-01-read-hash.py:71-80` — The audit loads `checks.json` and compares its
  embedded approval binding, but never hashes that file against the
  independently selected raw pin
  `sha256:51bcd1fcd25bc656dfdd64eb034078908aad9c49db9afefaaade369d3b09f50c`.
  Its "component frozen config" comparison compares recorded hash strings,
  not the effective checks content. Supply preserved read/hash evidence
  covering this comparison.
- `119-01-read-hash.py:78-80` — The audit hashes `tools/card/runtime-files.json`
  itself
  (`sha256:38939f3269f84a42315a665bc10b3c3e0cde97a68fc52c965de47dac6493d525`)
  but does not follow its nested executable/browser/dependency references.
  The file's first entry declares Claude executable hash
  `sha256:1495eb7c42d3b4451f5f1cd38b6d498d22a4a38c802bc2be5c1cf1795e64820d`;
  no actual-byte comparison for that entry appears in the audit. Supply the
  remaining closure comparisons without rerunning evaluation.

## Preserved references from the response

Target: `/Users/ramboz/.copilot/session-state/a7784cf6-9f09-4776-8660-bffeb3559e50/files/036-01-current-positive`.
Run: `b6e14da1-40da-4e76-b37d-580eb3e82844`.
Gate/component/envelope raw SHA-256:
`be85185ee007a71c3c6551978c413087fc1ace327ede477d3a8292aac506c369` /
`adc6fb8b550a98c091a0f95ac062188f67b9fbc106b25c4f6414932caf487637` /
`524727c7c0b2a7e973f3fbfa19ac67fca95ee7722a51ee0b95b2d188c02b96a0`.

Gate policy and selected pin:
`fe7a581d951f93e8c2b36f60ed949e78f080e1f45ff04d76e251fca0493e3b0d`.
Quality raw config / definition:
`f94974595efb30c65096ee1ecf459557ebc130f4280714564716bf50527ab0d5` /
`a38198e332cc469fc86aec122b09ba5aa3dabb4159d5da4465bec6536300a2bc`.
Input/output domains:
`servo-input-closure-v1` =
`f466e37eb5e0d621c18e9bf87e7a085a55eddfca12082dd347bae6c1d7850ec2`;
`servo-output-closure-v1` =
`b6fe523c84de3def0b1fe24a7c71c8c9d0dd172e9294c7f1eace37d62e358826`.
Current/sealed output, independent delivery and served response `index.html`
raw hash:
`655d86c5a41078701413e1f002904c30b99fdeda1cd795dfe24b9bdebbaa58f9`.

Required inventory: for each prefix `normal-` and `open-`, these suffixes pass:
`band-fill`, `band-height`, `band-width`, `subtitle-colour`,
`subtitle-font-family`, `subtitle-font-size`, `subtitle-font-weight`,
`subtitle-text`, `title-colour`, `title-font-family`, `title-font-size`,
`title-font-weight`, `title-presence`, `title-text`. Gate evidence indices
0–13 and 14–27 link to component evidence/envelope constraints.

No commands, evaluator imports, image judgments, scoring calculations or
writes were performed by the reviewer. C1 approval is fixture-scoped agent
source approval, not authenticated human approval. Unsigned local records
do not establish forgery-resistant authenticity.

## Later producer context (not a changed reviewer verdict)

After this review the coordinator reported a further execution-closure gap:
the scalar-quality SEED wrapper was not frozen by the producer's generic
driver identity. The actual run used the genuine wrapper, but does not prove
constant-wrapper drift rejection. The producer is sealing exact final
`oracle.sh` bytes through its existing evaluator-artifact closure and staged
review/reapproval. This original run remains historical interoperability
evidence; it must not be relabelled as the future sealed-driver epoch.
