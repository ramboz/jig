# Worked example — OpenAPI for an HTTP API

This worked example walks through formalizing a prose HTTP API
contract into an OpenAPI 3.x spec, wiring `spectral` as the CI gate,
and generating typed clients via `openapi-typescript`. The source
material is intentionally a real-world drift case: aso-shallow-validator's
[architecture.md §5](https://github.com/ramboz/aso-shallow-validator/blob/main/docs/architecture.md)
has ~230 lines of prose API contract (endpoint table, request /
response jsonc bodies, RFC 7807 error model, idempotency rules,
rate-limit policy) but no machine-readable artifact — and the
hand-typed `src/problem-details.ts` is the symptom (the RFC 7807
shape was re-declared in TS code because there was no schema to
codegen from).

The example is in the JS/Node ecosystem because the source project
is; the abstraction (artifact + validation tool + CI gate +
optional codegen) is ecosystem-neutral.

## Before — prose only

Excerpt of §5.2 (request shape for `POST /v1/validate`):

````markdown
### 5.2 Request — `POST /v1/validate`

```jsonc
{
  "requestId": "req_01HX…",               // idempotency key; caller-generated
  "customerId": "acme",
  "deliveryMode": "AEM_CS",               // V1: "AEM_CS" | "EDS"
  "targetDomain": "CWV",                  // optional; V1 default "CWV"
  "baselineUrls": [
    "https://www.acme.com/en.html"
  ],
  "sourceRef": {
    "kind": "zip",                        // V1: "zip" only.
    "location": "s3://spacecat-src/acme/req_01HX.zip",
    "checksum": "sha256:…"
  },
  "patch": {
    "kind": "source-diff",
    "diff": "…",
    "touchedFiles": ["/apps/acme/clientlibs/.../header.js"]
  }
}
```
````

Excerpt of §5.9 (error model):

````markdown
### 5.9 Error model

RFC 7807 Problem Details for non-2xx responses:

```jsonc
{
  "type": "https://shallow-validator/errors/source-ingest-failed",
  "title": "Source repository ingestion failed",
  "status": 422,
  "detail": "Zip missing required EDS marker files",
  "instance": "/v1/validate",
  "requestId": "req_01HX…",
  "remediation": "Ensure the source zip is an EDS project root."
}
```
````

And the corresponding TS code (`src/problem-details.ts`), hand-typed
to match — the drift symptom:

```ts
export type ProblemDetails = {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  requestId?: string;
  remediation?: string;
};
```

If §5 were OpenAPI, this type would be codegen'd. Hand-typing it
means a future change to §5.9 (add a `traceId` field?) updates the
prose without touching code — drift.

## After — OpenAPI 3.x

Land an `openapi.yaml` at the repo root (or `docs/api/openapi.yaml`,
or wherever your CI looks):

```yaml
openapi: 3.0.3
info:
  title: aso-shallow-validator
  version: 1.0.0
  description: |
    Async-by-default patch validation service. See architecture.md §5
    for design rationale.

paths:
  /v1/validate:
    post:
      summary: Submit a patch for validation
      operationId: submitValidation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ValidateRequest'
      responses:
        '202':
          description: Job accepted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/JobAccepted'
        '4XX':
          $ref: '#/components/responses/ProblemDetails'
        '5XX':
          $ref: '#/components/responses/ProblemDetails'

  /v1/validate/{jobId}:
    get:
      summary: Poll for verdict
      operationId: getVerdict
      parameters:
        - name: jobId
          in: path
          required: true
          schema: { type: string }
      responses:
        '200':
          description: Verdict or in-progress
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: '#/components/schemas/VerdictPass'
                  - $ref: '#/components/schemas/VerdictReject'
                  - $ref: '#/components/schemas/InProgress'

components:
  schemas:
    ValidateRequest:
      type: object
      required: [requestId, customerId, deliveryMode, baselineUrls, sourceRef]
      properties:
        requestId:
          type: string
          description: Idempotency key; caller-generated.
        customerId: { type: string }
        deliveryMode:
          type: string
          enum: [AEM_CS, EDS]
        targetDomain:
          type: string
          enum: [CWV, ACCESSIBILITY, SECURITY, SEO]
          default: CWV
        baselineUrls:
          type: array
          items: { type: string, format: uri }
          minItems: 1
        sourceRef:
          $ref: '#/components/schemas/SourceRef'
        patch:
          $ref: '#/components/schemas/Patch'
        patches:
          $ref: '#/components/schemas/Patches'

    SourceRef:
      type: object
      required: [kind, location, checksum]
      properties:
        kind: { type: string, enum: [zip] }
        location: { type: string }
        checksum:
          type: string
          pattern: '^sha256:[a-f0-9]{64}$'

    # ... Patch / Patches / Verdict / InProgress schemas ...

    ProblemDetails:
      type: object
      required: [type, title, status]
      properties:
        type: { type: string, format: uri }
        title: { type: string }
        status: { type: integer, minimum: 100, maximum: 599 }
        detail: { type: string }
        instance: { type: string }
        requestId: { type: string }
        remediation: { type: string }

  responses:
    ProblemDetails:
      description: RFC 7807 problem details
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ProblemDetails'
```

What this buys you immediately:

- **Validation in CI** (next section) catches prose / schema drift
  before merge.
- **Codegen for types** (the section after) removes hand-typed
  `ProblemDetails` — the schema is the source of truth.
- **Generated docs** (`redoc-cli build openapi.yaml`) replace the
  hand-maintained §5.1 endpoint table.
- **Mockable for FE / contract tests** (`prism mock openapi.yaml`)
  unblocks parallel FE/BE work.

## CI gate — `spectral lint`

[Spectral](https://github.com/stoplightio/spectral) is the de facto
OpenAPI linter. Install dev-only:

```bash
npm install -D @stoplight/spectral-cli
```

Add a config (`.spectral.yaml`) — the built-in `spectral:oas` ruleset
is a sane default; override or extend per project:

```yaml
extends: ["spectral:oas"]
rules:
  operation-operationId-unique: error
  operation-tag-defined: warn
  info-contact: false  # we don't track contact info
```

Wire it as an npm script:

```jsonc
{
  "scripts": {
    "lint:openapi": "spectral lint openapi.yaml"
  }
}
```

Wire it in CI (`.github/workflows/ci.yml`):

```yaml
- name: Lint OpenAPI
  run: npm run lint:openapi
```

That's the gate. If a PR changes `openapi.yaml` in a way that breaks
the rules (missing operationId, undocumented response, undefined
schema ref), CI fails before merge.

For richer drift detection between code and spec, layer on:

- [`openapi-diff`](https://github.com/Azure/openapi-diff) — compares
  two OpenAPI specs for breaking changes (block-merge on breaking
  diffs against `main`).
- [`schemathesis`](https://schemathesis.readthedocs.io/) — generates
  property-based tests from the spec against a running server (catches
  cases where the implementation doesn't match the spec).

## Codegen — `openapi-typescript`

Replace hand-typed boundary types with generated ones:

```bash
npm install -D openapi-typescript
```

Add the script:

```jsonc
{
  "scripts": {
    "codegen:openapi": "openapi-typescript openapi.yaml -o src/types/openapi.generated.ts"
  }
}
```

Generated output (excerpt):

```ts
// src/types/openapi.generated.ts (auto-generated; do not edit)
export interface paths {
  "/v1/validate": {
    post: operations["submitValidation"];
  };
  "/v1/validate/{jobId}": {
    get: operations["getVerdict"];
  };
}

export interface components {
  schemas: {
    ValidateRequest: { /* …generated… */ };
    ProblemDetails: {
      type: string;
      title: string;
      status: number;
      detail?: string;
      instance?: string;
      requestId?: string;
      remediation?: string;
    };
    // …
  };
}
```

Now `src/problem-details.ts` becomes a one-liner re-export:

```ts
import type { components } from './types/openapi.generated.js';
export type ProblemDetails = components['schemas']['ProblemDetails'];
```

A change to §5.9's ProblemDetails shape now requires a change to
`openapi.yaml`, which regenerates `openapi.generated.ts`, which
type-checks against every callsite. Drift is structurally impossible
without a corresponding CI failure.

Gate the codegen step on no-uncommitted-diff in CI to catch "you
edited the schema but didn't regenerate":

```yaml
- name: Codegen up to date
  run: |
    npm run codegen:openapi
    git diff --exit-code -- src/types/openapi.generated.ts
```

## Migration order (incremental, not big-bang)

Don't try to land a complete `openapi.yaml` in one PR. Stage:

1. **PR 1** — Land a stub `openapi.yaml` covering one endpoint
   (start with `/health` or `/version` — minimal schema) +
   `spectral` config + the npm scripts + the CI gate. No code
   changes yet. Establishes the artifact + gate; subsequent PRs add
   coverage.
2. **PR 2** — Add `/v1/validate` request schema. Generate types.
   Use the generated `ValidateRequest` type in one callsite (e.g.,
   the route handler's body parser). Leave hand-typed code elsewhere
   untouched.
3. **PR 3..N** — One PR per schema component. Each PR replaces one
   hand-typed boundary type with the generated equivalent. Each PR
   passes lint + codegen-up-to-date in CI.
4. **PR final** — Once §5 prose is fully mirrored in `openapi.yaml`,
   replace §5.2 / §5.3 / §5.4 / etc. with a one-line reference to
   the OpenAPI artifact (or delete entirely if `redoc-cli` /
   `swagger-ui` is serving the spec). architecture.md §5.1 stays as
   prose intro; the schema lives in OpenAPI.

This staging preserves the working code at every step. No big-bang
schema generation; no day-where-everything-breaks.

## Recap

- **Artifact:** `openapi.yaml` (OpenAPI 3.x)
- **Validation tool:** `spectral lint` (+ optional `openapi-diff`,
  `schemathesis`)
- **CI gate:** `npm run lint:openapi` on every PR; codegen-up-to-date
  check
- **Codegen tool:** `openapi-typescript` → typed clients, replaces
  hand-typed boundary types
- **Mocking / parallel FE work:** `prism mock openapi.yaml`
- **Generated docs:** `redoc-cli build openapi.yaml`

The drift is closed once the codegen path replaces the hand-typed
boundary types; the CI gate keeps it closed.
