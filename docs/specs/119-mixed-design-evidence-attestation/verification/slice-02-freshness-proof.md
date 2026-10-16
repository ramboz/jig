# 119-02 unchanged-pass freshness proof

The guard rejects changed declared bytes using the **same already-recorded
passing design review**, without a lifecycle back-edge, fresh attester,
producer, evaluator or judge. This proves automatic consistency checking,
not a genuine renewed-build pass: AC5 renewal remains separately required.

## Exact source and genuine evidence

Selected parent, local HEAD and remote parent were verified at
`15c7af924b8d484d8664f4a0db1ff2455a112855` (open parent PR #243).
Command-scoped existing personal `gh` credentials and HTTPS transport were
used after the inherited SSH transport refused access; remotes/global
authentication were not changed.

Exercised implementation raw SHA-256:

| Source | Raw SHA-256 |
|--------|------------|
| `skills/_common/design_bindings.py` | `1254f05e66643fc63062ae79d72c374ef16b4ba9f05cf898c332f409eb28d86e` |
| `skills/_common/review_evidence.py` | `66a654e669b88595c4cc4cb99096a930e448080d797aa22a7deecb90ec51fcf6` |
| `skills/independent-review/review.py` | `3b1f7b6e6d2d573f926632151c72b5c1c526d5a4431a8d4847ddefbfd384c3a8` |
| `skills/spec-workflow/workflow.py` (unchanged) | `e8be31a9b9ce8d1c9da6c72074cf8348e36492cdec403dd7c99929e2939a5460` |

Frozen producer epoch is **6cc759e**, not the later capture-helper fix.
Original index:
`/Users/ramboz/.copilot/session-state/e33c1f8d-6be8-4fb4-8801-6cfe7838aa5c/files/final-proof-6cc759e/proof-index.json`,
raw `45a2df047e05d1dab67982a4b4a0280607537cf78094ad71fcd70b217bb2b2fc`.
All 678 indexed original artifacts and all 3887 declared **current external**
runtime files were independently rehashed with zero mismatch/alias.

Actual original gate/component/envelope run
`cbe6b5b3-a60f-4dc1-abb9-23a8fd6f48a2` remains byte-exact:
overall pass/exit0, quality0.97, all28requiredpass. These are preserved
producer observations, never recomputed scores. No original evidence,
source approval, frozen definition, runtime installation or peer repository
was modified. No newer capture-clipping correctness is attributed to this epoch.

## Reviewed finite wrapper and controlled mirrors

Session artifact root **J**:
`/Users/ramboz/.copilot/session-state/5f46e7ff-757c-4220-b710-7e428c427e8a/files`.
The exact grammar and generic record/revalidate recipe are in
[`design-bindings.md`](../../../../skills/independent-review/design-bindings.md).

`J/freshness-bound-proof/reviewed/selection.json` selects narrow disjoint
roots and context raw
`a42aa6862c531b218b70520d53b4703ee27351d1f50aab45c6507911f95e2553`.
The binding block raw is
`1e970073a5ac6db9648db2d018c579498303649cdae3ff78393ce202e2fd1cba`.
The context pins original independent PRE-RESULT authority, approved C0/
source/target, installed policy/config/checks/full oracle, both source and
installed runtime executables, all3930selectedruntimeRefs (including every
3887actualexternalruntimefile), and closed candidate/build-output/delivery
inventories. Toolchain roots are specific versioned directories/selected
executables, not a home or filesystem root.

The independently selected mutable candidate/build/delivery are disposable
byte-identical copies. Original overall/component records retain their
absolute pinned link; producer-relative command-result output resolves under
the explicitly reviewed controlled copy-project root. No producer record or
frozen reference was rewritten (`transport-selection.json`: `rewrites: []`).
All39actual copied output files were enumerated and rehashed against the
envelope plus manifest, including captures, claims, sealed bytes and native
answers; no extra files or symlinks. Actual normal/open observations'
`loaded_resources` document/path/status200 response hashes match separately
selected delivery bytes. An observation JSON's own raw hash is **not** falsely
treated as the served HTML hash.

The first real wrapper attester returned
[needs-changes](slice-02-binding-attester-first.md): the installed
`.servo/required_runtime.py` pin was missing and the first audit did not
hash the actual copied output tree. Both were corrected, not waived.
The corrected [actual initial attester](slice-02-binding-attester-pass.md)
authorized recording the proposed body unchanged. Its original 119-01
attestation prefix and complete new binding block were recorded with normal
`record-review`; the wrapper review is not whole-slice compliance.

## Unchanged old PASS: actual CLI observations

The stricter final witness is `J/119-02-actual-freshness-trace.json`,
raw `9c22a54aec868e50dc6531f333b65702853bc5f3290798641d3f782100b59011`.
It records exact argv/cwd/exit/stdout/stderr and unchanged-pass comparison
for **72CLI observations**, including36design-freshness refusals:
12preflight checks and24actual REVIEWED/DONE transition refusals.

All unrelated compliance/craft/reconciliation records are explicitly
**synthetic harness preconditions**, not invented app reviews. Initial
normal design clearance and REVIEWED succeed. Every mutation then reuses
the identical recorded pass, raw
`34cb0ec8a442eb0efb73f10e3eb71d826a1877eb70558a26a41a132295a6df49`.
No attestation, selection or pass body is rewritten during the mutation loop.
There is no manual state back-edge before detection.

| Changed bytes, otherwise fixed | Actual result |
|-------------------------------|---------------|
| Candidate HTML / dirty candidate config | `candidate_inputs` refuses |
| Build output only | `build_output` refuses |
| Selected delivery only, same resource/URL-path label | `delivery` refuses |
| Installed policy / quality config | Named policy/config refuses |
| Raw approved checks / full oracle | Named checks/oracle refuses |
| Installed required runtime / declared helper runtime | Named runtime binding refuses |
| Normal capture observation / acquisition receipt | Named output/acquisition refuses |

Every mutation preserves **Git HEAD, file size and nanosecond mtime**.
Exact-byte restoration clears after each case. Restoring bytes is consistency
recovery, **not** a new producer run or the AC5 renewed-build proof.

Synthetic controlled-project Git HEAD during mutation:
`f8daa01d4b5330edd8d165d48046c31c20d2371a`.
A documentation-only commit outside the declared application closure changes
it to `baacbaf47e0fd482f7e276aa2b7de7fe62c97846`; matching app evidence still
clears and the isolated fixture reaches RECONCILED/DONE with the same pass.
These are explicitly synthetic transport Git commits, not relabelled producer
or application source epochs.

An additional actual **already-DONE** reuse check then changed the selected
delivery while leaving the same recorded pass and lifecycle status alone:
`transition ... DONE` refused with a named delivery raw-hash mismatch. After
exact restoration, the same command cleared (`DONE -> DONE`). Thus existing
terminal-state reuse also executes the validator rather than returning early.
`J/119-02-already-DONE-reuse.json`, raw
`cf6eadcebc285b9b2c9232dfdd68163155c535f88e7cfa09afd35816fc306d8b`,
preserves both commands and the unchanged old-pass hash. This is additional
to, not counted inside, the72CLI witness.

The earlier75CLI witness is preserved as
`J/119-02-actual-freshness-trace-v1.json`. The final witness strengthens
metadata preservation from mtime/HEAD to **size plus mtime/HEAD**; its72CLI
successor before the NUL fix is retained as `...trace-v2.json`. The entire
72CLI plus already-DONE witness was repeated on the final NUL-fixed guard
at the source hash above. No earlier negative outcome is hidden. Fixture
setup/initial recording was repeated with the same approved body before
mutation; no fresh attester was used to repair any stale case.

## Reproduction, tests and limits

`J/run-freshness-mutations.py` retains the exact first-run setup/CLI sequence.
Do not rerun setup over completed fixtures as though creating new evidence.
Read-only current restoration check:

```bash
J=/Users/ramboz/.copilot/session-state/5f46e7ff-757c-4220-b710-7e428c427e8a/files
python3 skills/independent-review/review.py check-reviews \
  "$J/freshness-bound-proof/lifecycle/spec.md" 001-01 --stage REVIEWED
```

Expected exit0. The trace contains the actual DONE invocations; the
`check-reviews` CLI itself supports REVIEWED/RECONCILED, not a DONE option.

| J artifact | Raw SHA-256 |
|------------|------------|
| `prepare-bound-proof.py` | `a28ffd97f085ce57894039b32b73d26a0180e904d059c1c5764a616a8ca29cc7` |
| `audit-bound-proof.py` | `c06e15274d617409f2697f91f463923484563527930ffeca1edcc50f2c015b8f` |
| `bound-proof-audit.json` | `b89e9409c44b2ff90cba6cc9902eddc461518e1a7c507f3718d618c00d40ac3e` |
| `run-freshness-mutations.py` | `3cfe2f060fef88a8b3ff93ac21117a842061ce3c28438077d63cd936ac99d2f2` |
| `119-02-tdd-red.txt` | `a8628b61fa761870aeef79d35e17ca0a5615c9f64b20f9daad00870b4f4d44ef` |
| `119-02-tdd-observation-red.txt` | `a95bbab7ed4c342df1ef9b894d371d3f920c2ad8c38d45910b3bf52493b6630e` |
| `119-02-root-control-red.txt` | `6ab8e8b7fd6c412ee9bb77c88a41ee048716b3477ede2535d2b9753ef39ef449` |
| `119-02-root-control-green.txt` | `0e070036b4a06d1917eaa73a0550078d28eef0d2c915cebc53aafa514788c4c4` |

The implementer's initial red observed35failedassertions/subtests for
previously accepted changed bindings; a separate witnessed red caught the
actual served-observation shape before the fixed-field link was implemented.
Full compliance caught a root containing JSON `\u0000` escaping as a Python3.9
`ValueError` instead of a renewal diagnostic. A separate witnessed five-failure
red precedes the four-line lexical preflight fix, with recording/reuse
regressions proving exit2/no traceback/no overwrite of the earlier pass.
25new freshness tests and173affected review/evidence/workflow regressions pass
on Python3.9.6. Additional tests exercise malformed/nonfinite/unsupported,
missing/duplicate/partial/foreign-run references, narrow-root/path aliases,
external runtime drift, complete inventories, historical/unflagged preservation
and explicit-selected missing-binding refusal. These structural fixtures are
labelled synthetic; they are not manufactured producer grades.

The guard and proof perform zero producer/evaluator/judge/browser/recapture
calls. CLI harness subprocesses invoke only Jig/Git; production freshness
validation reads/hashes. No network/live-server claim, hostile-host guarantee
or authenticity/signature claim is introduced. Root authority, initial
semantic equality and closure completeness remain trusted independent review.
Broad legacy migration/renewal UX remains119-03, still DRAFT.

**Outstanding:** genuine changed-build B renewed overall PASS under the same
frozen evaluation definition plus independent delivery context and fresh
attestation (AC5), then whole-slice reviews/reconciliation/lifecycle. The
isolated fixture's DONE is not Jig119-02 DONE.
The [fresh checkpoint compliance](slice-02-compliance-checkpoint.md) identifies
AC5 as the sole remaining acceptance blocker after the NUL fix. Publication
is an explicitly authorized stacked IN_PROGRESS draft, not a release.
