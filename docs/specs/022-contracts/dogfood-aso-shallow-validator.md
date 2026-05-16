# `/jig:contracts` dogfood — aso-shallow-validator

> **Date.** 2026-05-15
> **Source project.** `/Users/ramboz/Projects/misc/aso-shallow-validator`
> **Spec.** Closes the AC #4 close-out item from slice 022-01 and the AC #6 close-out item from slice 022-02 (the in-branch correctness check was captured in 022-02 §4; this document is the full per-surface recommendation pass).

This is what `/jig:contracts` produces when invoked against aso-shallow-validator. The shape mirrors [SKILL.md](../../../skills/contracts/SKILL.md)'s per-surface recommendation table: for each external surface this project commits to, classify the **current state** and the **recommendation per the canonical table**, then label as **good as-is** / **migrate** / **partial** / **not applicable** with the why.

## Surface inventory

aso-shallow-validator exposes:

1. **HTTP API** — async-by-default validation service (`POST /v1/validate`, `GET /v1/validate/{jobId}`, `POST /v1/feedback/{requestId}`, `GET /v1/health`, `GET /v1/versions`, plus operational probes `/health` `/ready` `/version`)
2. **Internal data shapes** — validation envelope, verdict payload, feedback payload, domain descriptor, reason codes (consumed by spacecat as the upstream caller + by the operator at the wire)
3. **Learning-Agent emission events** — fire-and-forget POSTs to `SHALLOW_LA_INGEST_URL` (per ADR-009); JSONL local log at `SHALLOW_LA_LOG_PATH` as the replay seam
4. **Env vars** — service runtime + caches + external toolchain + feature flags + LA producer + test gates (~25 vars per [`docs/env-contract.md`](../../../../aso-shallow-validator/docs/env-contract.md))
5. **CLI output** — none load-bearing; the service is a daemon, not a CLI tool. `npm run check:env-contract` emits human-readable text but no machine-readable shape

Surfaces NOT exposed (negative inventory worth recording — they ARE asked about in the wizard's Section 13):

- **Event bus / async messaging** — no Kafka/NATS/MQTT/WebSocket. The LA emission is a fire-and-forget HTTP POST, not a true event bus; treated as a one-way notification, not a contract-shaped pub/sub. Listed under (3) above as "Learning-Agent emission" rather than "Event bus."
- **RPC** — no gRPC, no Smithy, no JSON-RPC. Service-to-service is all HTTP per ADR-004.
- **GraphQL** — none. Future scope only if a richer query surface emerges.

## Per-surface recommendation

### 1. HTTP API → **migrate (recommended)**

- **Current state.** Prose contract at [`docs/api-contract.md`](../../../../aso-shallow-validator/docs/api-contract.md) (~225 lines: §1 Endpoints table + §2-§10 request/response jsonc bodies + RFC 7807 error model + idempotency + rate-limit policy). Zero machine-readable schema; the prose is the source of truth.
- **`/jig:contracts` recommendation.** **OpenAPI 3.x** (`openapi.yaml`) + `spectral lint` CI gate + `openapi-typescript` codegen.
- **Why migrate.** This is the canonical drift surface: spacecat is the upstream caller, FE clients (or codegen for them) consume the response shape, operators read the prose to write integration tests. Today every consumer hand-rolls types against the prose. Tomorrow's drift cost compounds linearly with caller count.
- **Migration path.** See [`skills/contracts/worked-example-openapi-http.md`](../../../skills/contracts/worked-example-openapi-http.md) — the worked example ships with §2 already excerpted from this very project's `api-contract.md`. Stage incrementally: PR 1 lands an `openapi.yaml` covering `/health` + `/version` + spectral CI + the codegen script; PRs 2..N migrate one component per PR; final PR replaces §2-§10 prose with a one-line `[redoc-cli build openapi.yaml]` reference.
- **Caveat.** `api-contract.md` has informal-but-load-bearing prose that doesn't map cleanly to OpenAPI fields (e.g., `evidence.fromCache` "typically returned on the first poll within milliseconds" — a behavioral hint, not a schema constraint). Keep §6 (Async-by-default policy), §7 (Idempotency and caching), §8 (Auth, rate limiting) as prose siblings; migrate only the wire-shapes.

### 2. Internal data shapes → **partial — keep zod, add JSON Schema export**

- **Current state.** `src/types/{envelope,verdict,domain-descriptor,reason-codes}.ts` define the boundary types via **zod** (e.g., `envelope.ts` opens with `import { z } from 'zod';`). Runtime validation already happens at the boundary. Stack-coupled (TS-only) — spacecat and any other-stack caller cannot consume the same schema artifact.
- **`/jig:contracts` recommendation.** Per [SKILL.md's per-surface table internal-data-shapes row](../../../skills/contracts/SKILL.md#per-surface-artifact-recommendations) — canonical is JSON Schema; **zod is a documented opt-out** when the team is single-stack and committed. The aso-shallow-validator team has chosen zod and the choice is paying off (runtime validation works, types narrow correctly).
- **Recommended next step.** Add `zod-to-json-schema` to the build chain; emit `src/types/*.schema.json` alongside the zod definitions. Publish those schemas alongside the OpenAPI spec (as `components/schemas` references). Cross-stack callers (e.g., a future Python evaluation script) consume the JSON Schema; in-tree TS continues to use zod ergonomically.
- **Opt-out justification needed?** No additional ADR required — zod-for-TS-stacks is named as an explicit opt-out in ADR-0005. If the team later goes polyglot and the lack of a published schema bites a non-TS caller, write a follow-up ADR to migrate to JSON Schema canonical.
- **`src/problem-details.ts`** is the **exception** to the partial story — it is hand-typed TS WITHOUT zod (verified by reading the file). Either: (a) add a zod schema for ProblemDetails too (one-line fix); (b) once the HTTP API migrates to OpenAPI (recommendation 1), `ProblemDetails` becomes a codegen'd component and the hand-typed file becomes a one-line re-export. (b) is cleaner; do it as part of recommendation 1's PR sequence.

### 3. Learning-Agent emission events → **migrate (recommended) — JSON Schema or AsyncAPI**

- **Current state.** `src/feedback/la-http-producer.ts` posts the event as `body: JSON.stringify(event)` with no schema validation; `appendFileSync(logPath, JSON.stringify(line) + '\n')` for the local JSONL replay seam. The event shape is documented informally in slice docs only (per env-contract.md row for `SHALLOW_LA_INGEST_URL`).
- **`/jig:contracts` recommendation.** Per [SKILL.md's internal-data-shapes row](../../../skills/contracts/SKILL.md#per-surface-artifact-recommendations), **JSON Schema** (`src/feedback/la-event.schema.json` validated by `ajv` on both producer and consumer sides). Per the [JSON Schema worked example](../../../skills/contracts/worked-example-json-schema-envelope.md), this is the textbook fit — producer-and-consumer-in-different-repos pattern, with the LA service as the cross-process consumer.
- **Why migrate.** The LA team is an organizationally-separate consumer of this event shape. Today they reverse-engineer the shape from the appended JSONL log; tomorrow a producer-side change silently breaks their ingestion. A published JSON Schema (publishable to a package, a CDN, an OCI artifact, or just committed in both repos with a checksum check) is the right vehicle.
- **Alternative.** **AsyncAPI** — if jig later treats the LA emission as a first-class event-bus surface (e.g., if we move from HTTP POST to Kafka), AsyncAPI is the canonical artifact for that. For the current HTTP-POST shape, JSON Schema for the payload alone is sufficient; AsyncAPI's protocol-binding metadata is overkill until the transport actually pluralises.

### 4. Env vars → **good as-is (bespoke env-contract triple, opt-out per ADR-0005)**

- **Current state.** Full triple shipped: [`docs/env-contract.md`](../../../../aso-shallow-validator/docs/env-contract.md) (markdown reference table) + `.env.example` (machine-readable seed) + [`tools/env-contract/check.mjs`](../../../../aso-shallow-validator/tools/env-contract/check.mjs) (139-line stdlib enforcer; `WAITING_FOR_CONSUMER:` annotation convention for in-flight slices) + `npm run check:env-contract` CI gate.
- **`/jig:contracts` recommendation.** Per [SKILL.md's Config / env vars row](../../../skills/contracts/SKILL.md#per-surface-artifact-recommendations), JSON Schema for structured config OR bespoke env-contract pattern (the validator's exact shape) is a worked-example-friendly alternative. **The validator's pattern is the worked example**; no migration recommended.
- **Why keep it.** This is the artifact that motivated ADR-0005 in the first place (Context §1). The triple works, the CI gate catches drift before merge, the `WAITING_FOR_CONSUMER:` annotation handles the slice-staging edge case. Migrating to per-config JSON Schema would lose the elegant "all env vars in one table" view and gain nothing — env-var sprawl is shaped differently from a single structured config file.
- **Caveat for jig.** Spec 022-02's `migrate.py report` "Contract surfaces detected" section correctly flags this as the canonical worked example for the env-contract row of the recommendation table. No follow-up.

### 5. CLI output → **not applicable**

- **Current state.** The service is a daemon (`src/index.ts` boots Fastify); there is no `--json` / `--format json` CLI surface. `npm run check:env-contract` emits human-text output but isn't itself a contract surface.
- **`/jig:contracts` recommendation.** None — the per-surface CLI-output row only applies when a project has a CLI that emits machine-readable output for downstream pipes. Not the validator's shape.

### 6. Event bus / RPC / GraphQL → **not applicable (negative inventory)**

- **Recommendation.** None today. Listed explicitly per Section 13's "'No external surfaces' is a valid and honest answer" convention so future-jig knows these were considered and not deferred-by-omission.
- **Resolution trigger.** If the LA emission graduates from HTTP POST to a Kafka topic (V2 per ADR-009 §Consequences), `event bus → AsyncAPI` becomes recommendation 7. If a future RPC surface emerges (e.g., a low-latency in-cluster API for cache-warming), `RPC → .proto` applies.

## Summary table

| Surface | Current state | Recommendation | Action |
|---|---|---|---|
| HTTP API | `docs/api-contract.md` prose only | OpenAPI 3.x + spectral + openapi-typescript | **migrate** (staged) |
| Internal data shapes | zod (envelope, verdict, domain-descriptor, reason-codes) | zod + zod-to-json-schema (publish JSON Schema for cross-stack callers) | **partial** — keep zod, add JSON Schema export |
| `src/problem-details.ts` | Hand-typed TS, no zod | OpenAPI components codegen (folds into HTTP API migration) | **migrate** (PR-sequence under HTTP API) |
| Learning-Agent emission | `JSON.stringify(event)` raw, no schema | JSON Schema + ajv (producer + consumer both validate) | **migrate** |
| Env vars | Full env-contract triple, CI gate green | None — the validator's pattern IS the worked example | **good as-is** (ADR-0005 documented opt-out) |
| CLI output | N/A (daemon) | N/A | **not applicable** |
| Event bus / RPC / GraphQL | N/A (HTTP POST + no RPC/GraphQL) | N/A today; AsyncAPI / .proto / SDL if V2 introduces them | **not applicable** (resolution trigger documented) |

## Recommended sequencing

If aso-shallow-validator decides to adopt the recommendations:

1. **Recommendation 4 stays as-is.** No work needed. Already-shipping pattern is the canonical opt-out.
2. **Recommendation 3 (LA emission JSON Schema) lands first.** Smallest blast radius — single file in `src/feedback/`, no cross-team coordination beyond publishing the schema to the LA team. Closes the "producer-and-consumer-in-different-repos" drift mode.
3. **Recommendation 1 (HTTP API OpenAPI) lands second.** Larger PR sequence; staged per the [worked example](../../../skills/contracts/worked-example-openapi-http.md). Picks up `ProblemDetails` codegen automatically (recommendation 2 sub-issue) at the right PR step.
4. **Recommendation 2 (zod-to-json-schema for internal data shapes) lands third.** Optional follow-up once polyglot consumers actually exist; today's TS-only consumer base makes zod sufficient.

Total effort estimate (rough, per the contracts skill's "orchestrate ecosystem tools, don't reinvent" framing): ~2-3 PRs for LA-emission JSON Schema; ~5-8 PRs for HTTP API OpenAPI sequence; deferred for the zod-to-json-schema work until polyglot need emerges.

## Nudge-don't-mandate audit

Every recommendation above is **a suggestion**, not a directive. The validator team should:

- Adopt recommendations 1 and 3 if they value drift-prevention more than the migration cost.
- Defer recommendations 2's JSON Schema export if zod-only is working and no polyglot consumer has signaled pain.
- Keep recommendation 4 as-is unconditionally; the env-contract pattern is the worked example.
- If they choose to systematically opt out of any recommendation (e.g., "we're staying on prose `api-contract.md` for V1; OpenAPI is V2"), capture the rationale in an ADR via `/jig:adr-workflow`.

No part of jig refuses, blocks, or fails when a project opts out — `/jig:contracts` recommends; the dev decides; `/jig:migrate report`'s "Contract surfaces detected" section will continue to flag the gap; `/jig:independent-review`'s reviewer-prompt check stays silent until a `## Contract surfaces` slot is filled. Per the nudge-don't-mandate ethos.

## Validation that this dogfood matches the skill's design

This dogfood report was produced by:

1. Inventorying aso-shallow-validator's external surfaces (Section 13 question — "What external surfaces does this project expose?").
2. For each surface, looking up the recommendation in [SKILL.md's per-surface table](../../../skills/contracts/SKILL.md#per-surface-artifact-recommendations).
3. Cross-referencing against the worked examples ([OpenAPI-HTTP](../../../skills/contracts/worked-example-openapi-http.md) is literally based on this project's §5; [JSON Schema envelope](../../../skills/contracts/worked-example-json-schema-envelope.md) covers the LA emission case).
4. Applying the nudge-don't-mandate language consistently — each recommendation has a "why migrate" + a "caveat / opt-out" pair.
5. Capturing negative inventory explicitly per Section 13's "'no external surfaces' is a valid and honest answer" convention.

The skill produced a useful, project-specific report **without any code execution** — judgment-only, exactly as ADR-0005 designed. The per-surface table proved its value as the canonical reference; the worked examples proved their value as the where-to-look-next pointers. ✅
