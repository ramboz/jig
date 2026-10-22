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

## Finite static source variant

`jig/static-design-freshness/1` is a separate incompatible encoding, not new
allowed labels in the preceding card grammar. It retains Vellum 0.2's real
source and Servo's `static_source_contract_evidence` bytes. No C0 card fields,
`design_evidence` relabel, absent-field inference or scalar fallback.
The same public `record-review`, `check-reviews` and REVIEWED/DONE rail applies.
Unselected historical/card records retain their original behavior.

### Static selection and context grammar

Use the same strict **Ref**, **Entry** and **Tree**, roots, JSON, fence and
size/path limits above. Ordinary Refs and Trees STILL forbid symlinks.
The slice's `jig-design-selection` is exactly:

```json
{
  "schema": "jig/static-design-freshness/1",
  "roots": {"project": "/reviewed/absolute/target", "evidence": "/reviewed/absolute/context"},
  "context": {"root": "evidence", "path": "static-context.json", "hash": "sha256:..."}
}
```

`project` is the actual producer target, not the Jig checkout or proof fixture.
Add disjoint narrow roots for the original source and runtime version dirs.
No home, `/opt/homebrew`, broad Cellar/opt, overlapping roots or implicit aliases.
The pinned context has **exactly**:

| Key | Exact shape |
|---|---|
| `schema` | `"jig/static-design-freshness/1"` |
| `contracts` | The exact object below; no bool/string coercion |
| `files` | Object with precisely the roles below |
| `trees` | Object with precisely `source`, `helpers`, `candidate_inputs`, `build_output`, `delivery`; each is ONE Tree, not a list |
| `browser` | `{"root":"ROOT_ID","path":"relative/browser/directory"}` |
| `aliases` | List (possibly empty) of `{"root":"ROOT_ID","path":"relative/symlink","target":"literal readlink text"}` |

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

`files` has singleton Refs for `app_policy`, `policy_review`, `input`, `approval`,
`request`, `manifest`, `checks`, `required_policy`, `build`, `selection`,
`runtime_manifest`, `browser_manifest`; plus nonempty Ref lists `pre_result`,
`pins`, `runtime_files`. All roles are mandatory; unknown roles refuse.

- `pre_result`: independently selected original context/authority, not a result
  that authorizes itself. Preparing the wrapper later does not confer approval.
- `pins`: reviewed installed/frozen/supporting bytes, including full target
  `oracle.sh`, `.servo/required_runtime.py`, component native runtime, grader,
  source spec, fragment, and **all current original source files** named by
  source `core.origin.root` + `core.originals` keys. Include installation and
  release records needed by the independent reviewer. Fixed producer links must
  land in these or the selected Trees/runtime files; no arbitrary discovery.
- `runtime_files`: expand **every** row of the pinned runtime manifest as
  canonical regular-file Refs. The selected set must equal that entire manifest.
  Pinning only its outer JSON, one executable or browser binary refuses.
- `source`: entire approved package, including `input.json`. Its original bare
  hexadecimal artifact hashes remain bare inside the producer document.
- `helpers`: entire source/evaluator helper closure named by APP
  `evaluator_files` (including producer helpers and both runtime manifests).
- `candidate_inputs`: current mutable candidate manifest, all resources and
  metadata. `build_output`: selected build's `output` directory.
  `delivery`: separately selected current delivery, not a result assertion.

The browser manifest is the producer's sorted array of exact
`{path,kind:"directory"}`, `{path,kind:"file"}` or
`{path,kind:"symlink",target}` rows. The helper enumerates all membership using
lstat/readlink, without descending symlink directories; every regular file is
also in `runtime_files`. Added/removed files, empty directories and changed
symlink identities refuse. The distinct `aliases` list pins interpreter aliases
such as venv `bin/python3` and `bin/python3.14`, **without following them** or
relaxing ordinary Ref traversal. Alias parents must be accessible without
symlink traversal, and `target` is literal identity, not a new read permission.
Canonical interpreter/native targets are separately rehashed in `runtime_files`.
Native loader `path` labels (e.g. Homebrew opt aliases) remain pinned provenance;
only their explicitly selected canonical `resolved` files are read. This does
not certify the current host loader's resolution or authorize broad opt reads.

### Static recorded bindings

The review body's one `jig-design-bindings` object has **exactly**:

```json
{
  "schema": "jig/static-design-freshness/1",
  "context": {"root":"evidence","path":"static-context.json","hash":"sha256:..."},
  "run_id": "41a3554e-8fd3-4d14-a59c-e7b8f2ec7593",
  "records": {
    "overall": {}, "oracle_result": {}, "component": {}, "invocation": {},
    "accepted": {}, "claim": {}, "receipt": {}, "envelope": {}
  },
  "output": {"root":"project","path":"spec/oracle/static/runs/RUN/observed","files":[]}
}
```

The `{}` record placeholders MUST each be full Refs; the output `files` is the
nonempty complete sorted Entry list, including `evidence.json`. `context` must
be the exact independent selection Ref. `run_id` is a canonical lowercase UUID.
The native command artifact is read verbatim from each component evidence row,
not separately reconstructed by the reviewer. No `served` card wrapper is used.

The native overall must be explicit `gate_result` integer schema 2, PASS/exit0.
FAIL and env_error/UNKNOWN refuse **before** current-candidate comparisons so
their preserved producer reasons survive even if the app has since restored.
Overall and `oracle-result.json` agree; `consumer-accepted.json` binds the actual
overall bytes. Invocation, component, envelope and claim/receipt agree on run;
receipt binds raw envelope hash, nonce and output claim. Every command artifact
binds that output root, manifest and exact complete inventory.

Source target/request domains, approval/request/package closure, APP exact-policy
independent review/domain, source constraints/environment, installed approved
binding, effective grading hash, component evaluator/config/source/policy
identities and complete required inventories must agree. Every required outcome
in native overall/component/envelope is conclusive PASS, with exact ID order,
indices, counts and producer reasons; duplicate/extra/missing rows refuse.
APP property/family and visibility `/3` namespaces remain distinct. No source
normalization, CSS measurement, scoring or policy evaluation is performed.
Vellum semantic domains use ASCII domain + **NUL** + sorted compact unescaped
UTF-8 JSON + a **trailing newline** (integer-only numbers, ASCII object keys).
Servo static domains use ASCII domain + **newline** + sorted compact
ASCII-escaped JSON with **no trailing newline**. Effective checks content
uses the producer's raw SHA-256 of canonical required-plan content. All file
Refs remain raw-byte hashes; these identities are not interchangeable.

Current candidate/selection/build/delivery is independently pinned, then compared
to the evaluated closure, including resources, metadata, recipe and the producer's
input/output domains. Every served resource must match the declared URL/path/
content-type, completed integer status200 and supported resource type; its hash
must match independently selected delivery AND retained response body bytes.
Observation run/nonce/environment, acquisition/settlement errors, screenshot
hash and complete output inventory are checked. This checks recorded conclusions
and bytes, not the truth of raw DOM observations.

### Actual M04 preparation paths and usage

Read-only artifact root **F** is
`/Users/ramboz/.copilot/session-state/43b73062-3958-42e3-879f-4f588494ff00/files`.
For the existing actual positive, `project` is **F/independent-marker-static-04**;
do not relocate/relabel a real run. Select:

| Role | Path relative to actual target |
|---|---|
| Source documents / Tree | `design-input/{input,approval,request,manifest}.json` / `design-input` |
| APP policy / review | `spec/oracle/static/{app-policy,policy-review}.json` |
| Checks / required policy | `spec/oracle/static/checks.json` / `.servo/required-policy.json` |
| Build / root selection | `builds/baseline/build.json` / `candidate-selection.json` (**not** under candidate) |
| Candidate / build output / delivery Trees | `candidate` / `builds/baseline/output` / `delivery` |
| Helpers / runtime / browser manifests | `tools/static` / `tools/static/{runtime-files,browser-membership}.json` |
| Installed/frozen pins | `.servo/{install.json,required_runtime.py}`, `oracle.sh`, `spec/static.md`, `spec/oracle/static/{checks.py,required_runtime.py,oracle.sh.fragment}` |

Current originals are under **F/independent-marker-control/source**, explicitly
select its narrow root and every `core.originals` file. The runtime root is
`/Users/ramboz/Projects/misc/vellum/.worktrees/musical-potato/.venv`;
browser membership is beneath `browsers`. Use narrow canonical
`/opt/homebrew/Cellar/NAME/VERSION` roots for manifest entries outside that venv.
Select canonical targets, not symlink Ref paths. Inspect and select the literal
venv `bin/python3` → `python3.14` and `bin/python3.14` → recorded absolute label
as aliases separately. Do not run Python from that runtime or launch a browser.

For run **41a3554e-8fd3-4d14-a59c-e7b8f2ec7593**, record Refs are:

- `overall`, `oracle_result`, `invocation`, `accepted`, `claim`, `receipt`:
  `.servo/gate-runs/RUN/{gate.json,oracle-result.json,invocation.json,
  consumer-accepted.json,static-acquisition-claim.json,static-acquisition-receipt.json}`.
- `component`: `spec/oracle/static/runs/RUN/result.json`.
- `envelope` / output Tree: `spec/oracle/static/runs/RUN/observed/evidence.json`
  / that entire `observed` directory. There is no sibling `receipt.json`;
  acquisition receipt is in the gate-run directory above.

Prepare a deterministic wrapper from **reviewed selection**, not an approval or
new run: enumerate only the selected closures, map every runtime manifest row
to a reviewed root, hash actual bytes, serialize context, and obtain independent
attestation separately. Keep preparation output labelled as preparation, not an
independent verdict. Use the earlier `record-review`/`check-reviews` commands
with that real review body and selected slice. The parent owns genuine independent
proof and lifecycle prerequisites; synthetic fixture reviews are not substitutes.
For M04 required UNKNOWN use run
**9bef2a53-924e-4d0f-b4ec-eb323c488823**. Preserve their original verdicts/reasons,
even where component diagnostic is 1.0 and threshold is 0.

### Mandatory scope in the independent review

Preserve source/policy residuals, including historical Jig-incompatibility prose;
it is historical producer data, not a reason to rewrite the producer bytes.
Explicitly state in the recorded review: finite static declarations do **not**
certify visual quality, actual font faces, interactions, backend truth, full APP
or arbitrary Jig app-DONE. Independent compliance still owns acceptance.
The marker's four approved presence/width/height/background goals do not add
empty APP text, circle shape or meaning. No deployed-server/backend, arbitrary
CSS/Figma, hostile-host, honest-execution/signature or full-application claim is
supported. Exact restoration can restore consistency; repository HEAD alone
cannot invalidate documentation outside these selected closures.
