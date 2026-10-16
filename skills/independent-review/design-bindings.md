# Selected rich design freshness — finite local bindings

This is a read/hash-only consistency contract inside the **existing** design
review. It is not a producer format, evaluator, new verdict/pass/state or
slice frontmatter. The reviewer attests the producer's semantic comparisons,
overall policy verdict and closure completeness. The helper only revalidates
the exact approved bytes/inventories and fixed run links. It never derives
scores, executes commands, imports Servo, accesses the network or discovers
comparison inputs. Examples below describe structure, **not producer PASS**.

## Encoding

JSON is UTF-8, finite, duplicate-key-free. Each named Markdown fence occurs
exactly once at column zero, with exactly three backticks and no attributes.
The closing fence is a separate line. No JSON comments, unknown keys or type
coercion. Versions are integers, not strings/bools. Hashes are raw-byte
`sha256:` plus exactly 64 lowercase hexadecimal digits, not semantic digests.
JSON documents/blocks are bounded to 32 MiB; comparisons/inventories to
100,000 files and directory traversal to depth 64.

Use these structural types:

- **Ref**: `{"root":"ROOT_ID","path":"relative/file","hash":"sha256:..."}`.
- **Entry**: `{"path":"relative/tree/file","hash":"sha256:..."}`.
- **Tree**: `{"root":"ROOT_ID","path":"relative/directory","files":[Entry,...]}`.
  The entries are nonempty, sorted lexicographically by path, unique including
  casefold, and cover **every regular file** recursively, with no exclusions.
  Added/deleted files refuse. Symlinks and other file types refuse.

Paths use `/`, no empty/`.`/`..` segments, absolute Ref paths, backslashes,
colons, control characters or non-NFC spelling. References resolve to exact
case-sensitive names; case aliases refuse even on case-insensitive hosts.
Only explicitly reviewed, canonical, absolute **directory** roots are allowed.
Root IDs match `[a-z][a-z0-9_]{0,63}`; `project` is required and anchors fixed
producer-relative links. At most 64 roots, disjoint even under casefold.
Roots cannot be symlink aliases, home/ancestors of home, filesystem/system
roots or private credential/git directories. Choose narrow versioned runtime
directories; never authorize `/Users`, a home or a generic runtime install.
Individual runtime executables use explicit `runtime_files` Refs under a
narrow containing directory, without inventorying unrelated versions.
Root authorization remains a trusted-local reviewer choice, not sandboxing.

### 1. Slice-body selection (required to select this contract)

````markdown
```jig-design-selection
{
  "schema": "jig/design-freshness/1",
  "roots": {
    "project": "/absolute/reviewed/project",
    "evidence": "/absolute/reviewed/evidence"
  },
  "context": {"root":"evidence","path":"context.json","hash":"sha256:..."}
}
```
````

Missing/malformed/unsupported/duplicate selection or missing bindings refuses;
missing rich fields never select a historical/scalar fallback. Unselected
historical plain evidence and unflagged slices retain existing behavior.

### 2. Pinned context JSON

The context has **exactly** `schema`, `contracts`, `files`, `trees`:

- `schema`: `"jig/design-freshness/1"`.
- `contracts`: exactly
  `{"vellum_input":"vellum-design-input/0.1-pilot","gate_result":2,
  "required_component_result":1,"command_result_artifacts":1,
  "design_evidence":1,"design_eval_config":2}`.
  These are distinct supported namespaces, not an inferred version.
- `files`: exactly the following roles, each a nonempty list of Refs except
  `runtime_files`, which is explicitly present but may be empty:
  `pre_result`, `source_approval`, `approved_target`, `c0`, `frozen_policy`,
  `frozen_config`, `installed_policy`, `installed_config`, `installed_gate`,
  `checks`, `full_oracle`, `runtime_files`.
  Duplicate references within a role refuse.
- `trees`: exactly `runtime`, `candidate_inputs`, `build_output`, `delivery`,
  each a nonempty list of Trees, except `runtime` may be empty if
  `files.runtime_files` is nonempty. Duplicate/overlapping file inventories
  within a role refuse.

`pre_result` pins the **independently selected original PRE-RESULT context**
bytes, even when a reviewer authors this finite wrapper later. The reviewer
must verify every wrapper expectation against that original context and
approved C0. A changed result/context cannot silently authorize changed
source/target or policy/config. Preserve the initial independent selection.

All nested runtime files must be expanded into these reviewed inventories:
a producer manifest's outer hash never substitutes for its referenced bytes.
A producer inventory may itself be an unversioned list of `{path,hash}` rows;
it is reviewed data, not an instruction to follow arbitrary JSON strings.
For directory closures use closed Trees; for individually selected binaries
use `runtime_files`. Pin the original manifest among the relevant file refs.
Do not auto-generate/approve inventories by scanning current results/files.

Candidate inputs include dirty source, assets, dependencies and effective
runtime/build config per the owner-defined closure. Build output and delivery
are **independently selected mutable directories**, not only frozen copies or
the producer's own delivery assertion. A Git HEAD, URL or timestamp is not
that closure. Unknown/inaccessible/partial closure is non-clearing.

### 3. Existing design-review body

One `jig-design-bindings` JSON fence with **exactly**:

- `schema`: `"jig/design-freshness/1"`.
- `context`: the exact Ref from the slice selection.
- `run_id`: nonempty string identifying the actual pinned run, never `latest`.
- `records`: exactly `overall`, `component`, `envelope`, `acquisition`, each
  a Ref. Overall is `gate_result` schema 2; component is
  `required_component_result` schema 1; envelope is `design_evidence` schema 1.
  All have the selected `run_id`. Acquisition is the preserved receipt with
  exactly `run_id`, `envelope_hash`, `nonce`; the raw envelope hash must match
  and its nonempty nonce must equal the envelope's `acquisition_nonce`.
  Pin additional acquisition claims/receipts/captures in the complete output
  inventory or context refs as appropriate.
- `result_artifact`: the **exact copied raw result's** `result_artifact`
  object, with exactly `kind`, `schema_version`, `run_id`, `root`, `manifest`,
  `artifacts`. `kind` is `"command_result_artifacts"`, version is integer 1,
  run matches. `root` is the declared output directory, either absolute
  under a reviewed root or relative to `roots.project`. `manifest` is an
  Entry for the selected envelope. `artifacts` is the complete sorted Entry
  list, excluding **only** that manifest, which is separately included.
- `output`: a Tree for that entire output directory, **including** the
  envelope/manifest and every capture/raw answer/claim/build/delivery file.
- `served`: a nonempty list of exactly
  `{"capture":Ref,"delivery":Ref,"resource_path":"index.html"}`.
  `capture` pins the actual normal/open observation JSON in `output`, **not**
  an HTTP body file, screenshot or sealed-output file. `delivery` belongs to
  the independently selected `trees.delivery` closure and is rehashed.
  `resource_path` is a safe relative path selecting exactly one
  `loaded_resources` row by exact path. That row must have
  `resource_type: "document"`, integer `status: 200`, and a raw response `hash`
  equal to the independently selected delivery file's raw hash. The observation
  file's own raw hash is separately pinned; it is **not** the response hash.
  Duplicate captures and duplicate/case-aliased resource paths refuse.

The supported unversioned observation record has exactly these producer fields:
`acquisition_error`, `acquisition_nonce`, `capture_hash`, `capture_id`, `driver`,
`elements`, `facts`, `loaded_resources`, `root`, `run_id`, `state`, `state_error`,
`viewport`. Its `run_id` must equal the selected gate/component/envelope run.
Each loaded-resource row has exactly `path`, `hash`, `resource_type`, `status`;
paths and raw hashes are validated, never followed as new file references.
Missing/partial/duplicate/foreign-run/unsupported observation or response records
are non-clearing. Other observation fields remain raw-pinned producer data;
their semantic interpretation remains the reviewer's job.

The helper checks the selected overall's explicit `status: "pass"` and unique
`components[].result.{path,hash}` link to the selected component; every raw
component `evidence[].result_artifact` must equal the copied result artifact.
The artifact binds the envelope and the complete output inventory. Fixed
producer link fields alone are resolved; other path-like JSON strings are
never followed. Other overall components remain pinned as part of the raw
overall bytes; the producer's scalar-quality component may have `result: null`.
The reviewer attests their semantics. The helper does not
reconstruct required/quality policy or producer semantic identity domains.

## Record and revalidate

The independent reviewer writes its real verdict/reasons plus the block into
`review-body.md`. No extra record option or pass is needed:

```bash
python3 skills/independent-review/review.py record-review \
  docs/specs/NNN-slug/spec.md NNN-NN --pass design-review --verdict pass \
  --reviewer ACTUAL_REVIEWER --prompt-source 'review.py design-review ...' \
  --summary-file /reviewed/path/review-body.md
python3 skills/independent-review/review.py check-reviews \
  docs/specs/NNN-slug/spec.md NNN-NN --stage REVIEWED
```

The writer validates a selected `pass` **before overwriting** old evidence.
`fail`/`needs-changes` preserve honest refusal reasons without requiring valid
bindings. REVIEWED and the existing DONE revalidation compose the same check
with the ordinary reviews; no workflow changes or manual back-edge required.
A `design-freshness` refusal names the binding and requests fresh producer
evidence and independent attestation. Exact-byte restoration can restore
consistency; changes outside the declared app closure do not invalidate it
solely because HEAD changed.

The transport is a controlled sealed local bundle: served-response hashes
declared in the pinned observation link to selected bundle bytes, **not**
arbitrary live HTTP servers. No separately captured HTTP body is presumed.
This certifies neither a hostile host nor authentic execution. Unsigned local
records are not forgery-proof against co-edited claims/artifacts. Initial
semantic comparisons, full closure selection and review honesty remain
trusted-local preconditions. Do not claim a fresh producer run or PASS solely
because this deterministic consistency check clears.
