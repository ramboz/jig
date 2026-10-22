# Selected static design evidence

Jig checks a preserved external verdict, not the interface itself. A selected
static attestation uses the existing `design-review`, `record-review`,
`check-reviews` and REVIEWED/DONE evidence rail. The producer owns acquisition,
measurement, policy interpretation and the native overall verdict; independent
compliance still owns the slice's acceptance criteria.

## Supported contract and retirement

The finite supported selection is `jig/static-design-freshness/1`, with
Vellum `vellum-confirmed-source/0.2` / `static-css-subset/1` and Servo
`static-source-contract-app/1`. Component IDs, roles, goals, environment,
resource paths and counts are approved input data, not application-specific
runtime rules. The supported static snapshot recipe and producer namespaces
are deliberately bounded; this is not an arbitrary-provider/build adapter.

`jig/design-freshness/1` and `vellum-design-input/0.1-pilot` selections are
**retired**. Obtain evidence and independent approval using the supported
generic tooling, then select a new context and obtain a new attestation.
Do not relabel old approvals, patch historical hashes, reinterpret a retired
selection, or fall back to a scalar threshold when selected evidence is
missing or unsupported. Old frozen epochs remain historical, not approvals of
new helper bytes. Unselected historical scalar design-review and unflagged
slices retain their pre-existing behavior.

## Explicit selection

The slice body contains exactly one fence, with a JSON object:

````text
```jig-design-selection
{
  "schema": "jig/static-design-freshness/1",
  "roots": {
    "project": "/reviewed/absolute/target",
    "evidence": "/reviewed/absolute/evidence"
  },
  "context": {
    "root": "evidence",
    "path": "static-context.json",
    "hash": "sha256:<64 lowercase hexadecimal digits>"
  }
}
```
````

Example paths and hashes are placeholders, not runnable evidence. `project` is
the producer's actual target, not the Jig checkout. Add explicit narrow roots
for original source and canonical runtime dependencies where needed.

A **Ref** is exactly `{root, path, hash}`; `root` names a selected root and
`hash` is raw-byte SHA-256 with the `sha256:` prefix. An **Entry** is exactly
`{path, hash}`. A **Tree** is exactly `{root, path, files}`, where `files` is
the complete, nonempty, sorted Entry inventory beneath that directory.
Directory membership is closed: added, missing, aliased or nonregular entries
refuse.

Roots must be canonical absolute existing directories, disjoint and narrowly
scoped, not home/ancestor/system/private roots. Names use lowercase letters,
digits and underscores, starting with a letter. Relative paths cannot contain
empty, dot or parent segments, backslashes, colons, controls, private
credential/Git segments, or ambiguous Unicode/case spellings. Ordinary
Refs/Trees never follow symlinks. Browser membership and explicitly declared
interpreter aliases have the separate, non-traversing rules below.

Only explicitly owned fields are traversed. No arbitrary JSON pointer,
producer command, shell fragment or executable callback is interpreted.
JSON rejects duplicate keys and nonfinite numbers. Bounds are 32 MiB per JSON
document, 100,000 inventory/comparison entries, 64 roots and 64 path/depth
segments. Duplicate/malformed fences, unknown keys/namespaces, incomplete
selected evidence and a bindings block without independent selection refuse.

## Independent context

The pinned context has exactly these top-level fields:

| Field | Shape |
|-------|-------|
| `schema` | `"jig/static-design-freshness/1"` |
| `contracts` | Exact namespace object below |
| `files` | Exactly the singleton and list roles below |
| `trees` | Exactly `source`, `helpers`, `candidate_inputs`, `build_output`, `delivery`; one Tree per role |
| `browser` | `{root, path}` for the selected browser directory |
| `aliases` | Possibly empty list of `{root, path, target}` interpreter aliases |

```json
{
  "vellum_input": "vellum-confirmed-source/0.2",
  "source_profile": "static-css-subset/1",
  "gate_result": 2,
  "required_component_result": 1,
  "command_result_artifacts": 1,
  "static_source_contract_evidence": 1,
  "static_app_policy": "static-source-contract-app/1",
  "snapshot_candidate": 1,
  "snapshot_build": 1
}
```

These are separate namespaces. Integer versions are not booleans or coerced
strings; an envelope version never selects a different gate grammar.

`files` requires singleton Refs named `app_policy`, `policy_review`, `input`,
`approval`, `request`, `manifest`, `checks`, `required_policy`, `build`,
`selection`, `runtime_manifest`, `browser_manifest`, and nonempty Ref lists
named `pre_result`, `pins`, `runtime_files`.

- `pre_result` identifies separately selected authority/context, not a result
  authorizing itself. A wrapper prepared after a run is not an approval.
- `pins` covers installed/frozen/supporting bytes, including the complete
  target `oracle.sh`, `.servo/required_runtime.py`, component runtime, grader,
  source spec, fragment and every live original source file named by
  `core.origin.root` plus `core.originals`. Include supporting installation
  records needed by the reviewer. Fixed owned links must resolve to this
  independently selected inventory or the selected trees/runtime files.
- `runtime_files` expands every row of the pinned runtime manifest into
  canonical regular-file Refs. The selected set equals the entire manifest,
  not just the manifest JSON, interpreter or browser executable.

`source` closes the entire approved package including `input.json`, with
bare hexadecimal hashes preserved inside Vellum documents. `helpers` closes
the actual generic evaluator/source code plus its two runtime manifests:
`static_contract.py`, `static_snapshot.py`, `evidence_io.py`,
`evidence_runtime.py`, `producer/confirmed_source.py`,
`producer/capture_confirmed.py`, `producer/design_input.py`,
`producer/redline_intake.py`, `producer/resolve_redline.py`,
`producer/validate_redline.py`, `runtime-files.json`,
`browser-membership.json`. These are genuine generic modules, not renamed
aliases to historical component-specific code. New bytes require a new
approval epoch.

`candidate_inputs` contains the current candidate manifest, resources and
metadata. `build_output` selects the build's `output` directory. `delivery`
selects the current independently chosen delivery, never just the path asserted
by a result.

The browser manifest is a sorted array of `{path, kind:"directory"}`,
`{path, kind:"file"}` and `{path, kind:"symlink", target}` records. Enumerate
with lstat/readlink; do not descend symlink directories. Every regular file is
also pinned in `runtime_files`. Added/removed files, empty directories and
changed symlink identities refuse. Interpreter `aliases` pin literal readlink
text without following it; parents must be accessible without symlink
traversal. An alias may be a direct child of an explicitly selected canonical
metadata directory, or a relative descendant with a plain parent. Directory
aliases in the interpreter path must be explicitly declared too. For example,
a package-manager label directory can be selected for literal metadata reads;
its symlink is not a canonical root and never grants ordinary Ref/Tree
traversal. Canonical interpreter/native targets are separately pinned.
Every interpreter alias chain must be complete, bounded and acyclic, ending
at the selected canonical interpreter. A missing or retargeted intermediate
alias cannot authorize execution identity merely because the first readlink
text is unchanged. Resolve only declared component-boundary prefixes
lexically, including directory aliases before interpreting a following `..`;
never infer an alias, call `resolve()` through it or discover it from PATH.
Native-loader `path` labels are provenance only: only explicitly selected
canonical `resolved` files authorize reads. This does not certify the host
loader's current resolution.

## Recorded bindings

The independent review body's single `jig-design-bindings` fence contains
exactly:

```json
{
  "schema": "jig/static-design-freshness/1",
  "context": {"root":"evidence","path":"static-context.json","hash":"sha256:..."},
  "run_id": "00000000-0000-4000-8000-000000000001",
  "records": {
    "overall": {}, "oracle_result": {}, "component": {}, "invocation": {},
    "accepted": {}, "claim": {}, "receipt": {}, "envelope": {}
  },
  "output": {"root":"project","path":"spec/oracle/static/runs/RUN/observed","files":[]}
}
```

Every `{}` placeholder must be a full Ref and `files` the nonempty complete
sorted output Entry list including `evidence.json`; abbreviated hashes and
`RUN` are placeholders. `context` must exactly match the independent selection
Ref, and `run_id` is a canonical lowercase UUID.

The overall, oracle-result, invocation, accepted and acquisition claim/receipt
records are native gate-run records. The component result is the required
static result, and its envelope is `static_source_contract_evidence`, not a
relabelled legacy design envelope. The command result artifact binds the
run-scoped output root, manifest hash and complete inventory. There is no
separate legacy served-wrapper field.

## What must agree

Native overall `gate_result/2` must explicitly PASS with integer exit 0.
Native nonpass is reported before current-candidate comparisons so its
preserved reasons survive later restoration. Component diagnostic fractions
and high composites never override native FAIL/UNKNOWN, required missing/
unknown outcomes or a contradictory gate. No score is recomputed.

Require complete approved policy inventory and matching overall/component/
envelope IDs, outcomes, counts, indices and reasons. Required expectations
come from approved source/policy, not whichever rows appear in a result.
Overall and oracle-result agree; accepted binds actual overall bytes.
Invocation/component/envelope/acquisition claim and receipt agree on run,
nonce and raw envelope/output identities.

The complete native row names, order and numeric weights must match the one
frozen literal `COMPONENTS` roster in the fully pinned driver. The finite
supported shapes are sole static-required, or static-required plus the
producer's existing nongated scalar `quality` row. Dynamic, duplicate,
reassigned/augmented rosters and unknown components refuse; the driver is
never executed to discover its meaning. The finite driver profile permits
no other non-comment `COMPONENTS` reference outside that array; unsupported
shell forms refuse rather than requiring a general shell-write interpreter.
Static weight zero affects only
weighted quality, never the mandatory required-condition veto.
Every row needs exit zero and a finite score in `[0,1]`; scalar quality's
`result: null` is valid, while static still needs its complete result link.
Weights are declared finite nonnegative numbers with at least one positive
weight, not fixture constants. The native overall verdict and its recorded
threshold remain authority: score zero at an explicitly allowed threshold
zero is not itself a quality failure. Jig never calculates a replacement
composite or invents another quality cutoff.

Source target/request/approval domains and package closure, independent
exact-policy review, source constraints/environment, frozen/installed grading,
full driver bytes, runtime files and helper closure must agree. Live original
file bytes **and current original-root Git HEAD identity** are checked;
an archive alone is insufficient. The only metadata subprocess is a fixed
local Git read: no shell, user argv, network, writes or producer execution.
Inherited Git redirection/configuration is isolated. Non-Git roots have
explicit null identity; execution/permission/timeout errors cannot become a
null success. Unrelated target documentation is not invalidated solely by the
Jig checkout's HEAD moving.

Vellum semantic identities use ASCII domain + NUL + sorted compact unescaped
UTF-8 JSON + trailing newline, with integer-only numbers and ASCII object
keys. Servo static identities use ASCII domain + newline + sorted compact
ASCII-escaped JSON without trailing newline. Effective checks content has
its own canonical required-plan hash. File Refs always hash raw bytes; these
domains are not interchangeable.

Current selection/candidate/build/delivery comparisons close resources,
metadata, recipe and input/output domains. Retained served responses must
match declared URL/path/content type, completed status 200, supported resource
type, selected delivery hash and retained response bytes. Observation
run/nonce/environment, acquisition/settlement errors, screenshot hash and
the complete output inventory also agree.

## Recording and reuse

Build the usual prompt, obtain an independent read-only attestation, then
record the actual body through the existing CLI. Use the host-rendered helper
path in this skill's [SKILL.md](SKILL.md) recipes; the argument forms are:

```text
design-review "docs/specs/NNN-name/spec.md" "NNN-NN" "<evidence-reference>"
record-review "docs/specs/NNN-name/spec.md" "NNN-NN" \
  --pass design-review --verdict pass --reviewer "<independent-reviewer>" \
  --prompt-source "review.py design-review ..." --summary-file "<actual-review-body>"
check-reviews "docs/specs/NNN-name/spec.md" "NNN-NN" --stage REVIEWED
```

A selected passing body is checked before atomic overwrite. The same selected
comparisons are re-read by `check-reviews` and REVIEWED/DONE gates; other
required reviews remain necessary. On refusal renew the named producer
evidence and obtain independent attestation. Exact-byte restoration can
restore consistency, but does not create a fresh run or new approval.

## Trust and claim limits

This is a trusted-local consistency check, not proof against a hostile host
or co-edited unsigned records. The reviewer owns complete selection and honest
initial comparison. A prepared wrapper is not an independent verdict.
Jig never imports/calls the producer, captures a browser, measures CSS,
compares visual goals, or re-scores an interface.

Keep source/policy residuals in the review. Finite static measurements do not
certify visual quality, actual font faces, interactions, backend truth,
arbitrary deployed servers, arbitrary CSS/Figma, a full application or
application DONE. Test fixtures and synthetic prerequisite reviews prove
the product boundary only, not a real application's approval or completion.
