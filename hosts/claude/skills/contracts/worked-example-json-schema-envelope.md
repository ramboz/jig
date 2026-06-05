# Worked example — JSON Schema for an internal data envelope

This worked example walks through pinning an internal data envelope
with JSON Schema, validating it with `ajv` in tests, and noting where
stack-coupled alternatives (Zod / Pydantic / TypeBox) are idiomatic.

The example uses a synthetic "feedback event envelope" — the kind of
internal contract two services agree on for a message bus, an event
table row, or a queue payload — to keep the focus on the abstraction
(schema artifact + validation tool + CI gate) rather than any one
project's specifics. Unlike the OpenAPI example, this one is
deliberately ecosystem-portable: JSON Schema works in any stack with
a JSON-aware language.

## Before — TS interface, hand-maintained

A typical "internal envelope" starts life as a TS interface:

```ts
// src/events/feedback.ts
export interface FeedbackEvent {
  eventId: string;        // ULID
  occurredAt: string;     // ISO 8601
  customerId: string;
  requestId: string;
  source: 'dvs' | 'customer-feedback' | 'manual-review';
  verdict: 'PASS' | 'REJECT' | 'DROPPED' | 'SHIPPED';
  reason?: string;
  evidenceRef?: string;   // s3:// URI
}
```

Producer publishes the envelope; consumer reads it. Both sides import
the same TS interface — coupled across the wire by a shared module.

Drift modes:

- **Producer and consumer drift apart in different repos.** The two
  sides own their own copies of the interface; one side adds a field
  without telling the other.
- **The runtime payload doesn't match the type.** TS interfaces are
  erased at runtime; a malformed event from upstream (typo'd
  `customerId`, missing `requestId`) deserializes into an object that
  type-checks but fails at the consumer's first field access.
- **No validation at the wire.** Consumer assumes the shape; the bus
  passes whatever was put on it.

## After — JSON Schema as the source of truth

Land the schema as a `.schema.json` file alongside the producer (or
in a shared `contracts/` repo — but for *this* worked example, keep
it inline because there's no contracts-repo to introduce):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/feedback-event.schema.json",
  "title": "FeedbackEvent",
  "type": "object",
  "required": ["eventId", "occurredAt", "customerId", "requestId", "source", "verdict"],
  "additionalProperties": false,
  "properties": {
    "eventId": {
      "type": "string",
      "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
      "description": "ULID (Crockford base32, 26 chars)."
    },
    "occurredAt": {
      "type": "string",
      "format": "date-time"
    },
    "customerId": { "type": "string", "minLength": 1 },
    "requestId": { "type": "string", "minLength": 1 },
    "source": {
      "type": "string",
      "enum": ["dvs", "customer-feedback", "manual-review"]
    },
    "verdict": {
      "type": "string",
      "enum": ["PASS", "REJECT", "DROPPED", "SHIPPED"]
    },
    "reason": { "type": "string" },
    "evidenceRef": {
      "type": "string",
      "pattern": "^s3://"
    }
  }
}
```

What this buys you immediately:

- **Single source of truth** — both producer and consumer validate
  against the same `.schema.json`, even when they live in different
  repos (publish the file to a package, a CDN, an OCI artifact, or
  copy on each side with a checksum check).
- **Runtime validation** — `additionalProperties: false` + `required:`
  + format / pattern constraints catch malformed envelopes at the wire.
- **Codegen to TS / Python / Go / etc.** — see the codegen section.
- **Documentation comes for free** — JSON Schema docs are widely
  parseable (`json-schema-for-humans`, `quicktype --rendering doc`).

## Runtime validation — `ajv`

[Ajv](https://ajv.js.org/) is the standard JSON Schema validator in
the JS / TS ecosystem (and the validator used by most OpenAPI tools
under the hood).

```bash
npm install ajv ajv-formats
```

Producer side (validate before publishing — catch your own bugs):

```ts
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import schema from './feedback-event.schema.json' assert { type: 'json' };

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);
const validate = ajv.compile(schema);

export function publishFeedback(event: unknown): void {
  if (!validate(event)) {
    throw new Error(
      `FeedbackEvent failed schema validation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  bus.publish('feedback', event);
}
```

Consumer side (validate on receive — catch upstream's bugs):

```ts
bus.subscribe('feedback', (raw) => {
  if (!validate(raw)) {
    metrics.increment('feedback.invalid_envelope');
    log.warn({ errors: validate.errors }, 'invalid feedback envelope; dropped');
    return;
  }
  handle(raw as FeedbackEvent);  // safe cast — validated above
});
```

## Test fixtures — schema in test

The schema enables exhaustive fixture-based testing:

```ts
// tests/feedback-event.schema.test.ts
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { describe, it, expect } from 'vitest';
import schema from '../src/events/feedback-event.schema.json' assert { type: 'json' };

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);
const validate = ajv.compile(schema);

describe('FeedbackEvent envelope', () => {
  it('accepts a minimal valid event', () => {
    const event = {
      eventId: '01HX0000000000000000000000',
      occurredAt: '2026-05-15T10:00:00Z',
      customerId: 'acme',
      requestId: 'req_01HX',
      source: 'dvs',
      verdict: 'PASS',
    };
    expect(validate(event)).toBe(true);
  });

  it('rejects an unknown source', () => {
    const event = {
      eventId: '01HX0000000000000000000000',
      occurredAt: '2026-05-15T10:00:00Z',
      customerId: 'acme',
      requestId: 'req_01HX',
      source: 'made-up-source',  // not in enum
      verdict: 'PASS',
    };
    expect(validate(event)).toBe(false);
  });

  it('rejects extra properties', () => {
    const event = {
      eventId: '01HX0000000000000000000000',
      occurredAt: '2026-05-15T10:00:00Z',
      customerId: 'acme',
      requestId: 'req_01HX',
      source: 'dvs',
      verdict: 'PASS',
      extra: 'sneaky',  // not in schema; additionalProperties: false
    };
    expect(validate(event)).toBe(false);
  });
});
```

## CI gate — schema-as-test

Two CI gates worth running:

1. **The schema is syntactically valid.** `ajv compile` succeeds on
   every PR. Catches typos in the schema itself.
2. **Test fixtures match the schema.** The unit tests above are the
   gate — fixtures that should validate must validate; fixtures that
   should fail must fail. CI runs these tests on every PR.

Optionally:

3. **Schema diff against `main` is non-breaking.** Tools like
   [`json-schema-diff-validator`](https://github.com/Adobe-Consulting-Services/json-schema-diff-validator)
   catch breaking changes (removed required field, narrowed enum,
   tightened pattern) at PR-review time.

Wire (1) as a CLI script:

```jsonc
{
  "scripts": {
    "lint:schemas": "ajv compile -s 'src/**/*.schema.json' --strict=true"
  }
}
```

And in CI:

```yaml
- name: Validate schemas
  run: npm run lint:schemas
```

## Codegen — `quicktype` or `json-schema-to-typescript`

Replace the hand-maintained TS interface with a generated one:

```bash
npm install -D json-schema-to-typescript
```

```jsonc
{
  "scripts": {
    "codegen:schemas": "json2ts -i 'src/**/*.schema.json' -o src/types/"
  }
}
```

Generates `src/types/feedback-event.d.ts`:

```ts
// AUTO-GENERATED; do not edit by hand.
export interface FeedbackEvent {
  eventId: string;
  occurredAt: string;
  customerId: string;
  requestId: string;
  source: 'dvs' | 'customer-feedback' | 'manual-review';
  verdict: 'PASS' | 'REJECT' | 'DROPPED' | 'SHIPPED';
  reason?: string;
  evidenceRef?: string;
}
```

Now `src/events/feedback.ts` becomes a one-line re-export:

```ts
export type { FeedbackEvent } from '../types/feedback-event.js';
```

CI gate: codegen must be up to date.

```yaml
- name: Codegen up to date
  run: |
    npm run codegen:schemas
    git diff --exit-code -- src/types/
```

For polyglot stacks, `quicktype` generates Python / Go / Rust /
Java / Swift from the same JSON Schema. The schema is the lingua
franca; codegen produces the per-language type.

## Stack-coupled alternatives (when JSON Schema isn't the natural choice)

The recommendation table (in [SKILL.md](SKILL.md#per-surface-artifact-recommendations))
prescribes JSON Schema as the canonical artifact for internal data
shapes — for *portability* across stacks. When a team is single-stack
and committed, these stack-native alternatives have real ergonomic
wins:

- **TypeScript: [Zod](https://zod.dev/)** — TS-native schemas with
  static-type-narrowing. The `zod-to-json-schema` package exports a
  JSON Schema artifact when wire-portability matters; you get the
  ergonomics of Zod in code and JSON Schema at the wire.
- **TypeScript: [TypeBox](https://github.com/sinclairzx81/typebox)** —
  TS-native schemas that **are** JSON Schema. No conversion needed;
  the JS value IS the JSON Schema literal. Closest of the three to a
  zero-cost abstraction.
- **Python: [Pydantic](https://docs.pydantic.dev/)** — Python-native
  schemas with runtime validation; `model_json_schema()` exports
  JSON Schema. De facto Python standard for FastAPI / data
  pipelines.

All three are reasonable opt-outs from canonical JSON Schema when:

- The team is single-stack (TS-only or Python-only).
- The ergonomic wins of the stack-native API outweigh the portability
  cost (e.g., Zod's `.transform()` / `.refine()` / `.brand()` chain
  is much nicer than hand-writing `if/then/else` schemas).
- An optional JSON-Schema export keeps the wire-portability story
  available when needed (Zod → `zod-to-json-schema`, Pydantic →
  `model_json_schema`, TypeBox = same artifact).

Capture the opt-out in an ADR via `/jig:adr-workflow` if it's a
project-wide decision. The skill nudges toward JSON Schema; ADRs
document the chosen alternative.

## Recap

- **Artifact:** `*.schema.json` (JSON Schema, ideally draft 2020-12
  or 2019-09)
- **Validation tool:** `ajv` (runtime + test fixtures)
- **CI gate:** `ajv compile --strict=true` on every PR;
  test-fixture matrix; optional schema-diff-vs-main check
- **Codegen tool:** `quicktype` (polyglot) or `json-schema-to-typescript`
  (TS only)
- **Stack-coupled alternatives:** Zod, TypeBox (TS-native);
  Pydantic (Python). Opt-outs captured in ADRs.
- **Cross-repo distribution:** publish the `.schema.json` to a
  package / CDN / OCI artifact so producer and consumer pull from
  one source of truth.

The drift between producer and consumer is closed once both sides
validate against the same `.schema.json`; the CI gates keep the
schema and the generated types in lock-step.
