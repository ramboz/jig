# ADR-0002: `contracts` skill stays a deliberate stub

## Status

Accepted (2026-05-12)
Superseded by [ADR-0005](./adr-0005-contracts-as-judgment-skill.md) (2026-05-15)

## Context

`contracts` is the last Tier 0 skill that remains a `disable-model-invocation: true` stub after specs 001–004 promoted the other four (`scaffold-init`, `memory-sync`, `spec-workflow`, `independent-review`). The natural next move would be spec 005 to promote it. Before doing that, we asked: **do we have signal to design it well?**

The original ambition (see [docs/research/07-research-contracts-and-architecture.md](../research/07-research-contracts-and-architecture.md)) is substantial:

1. Generate a `contracts/` directory with stack-appropriate scaffolding (TS / Python / Go / multi-lang)
2. Generate contract test framework
3. PreToolUse hook blocking cross-module-boundary edits
4. Breaking-change detection (paired with `adr-workflow`, also unspecced)
5. Linter / static-analysis rule blocking cross-boundary imports
6. CI integration
7. Cross-reference contract type names against `docs/memory/glossary.md`

That's 5+ slices of work, much of it coupled to skills (`adr-workflow`) that don't exist yet.

## Decision Options Considered

### Option A: Slim promotion (one slice)
Generate a `contracts/` directory with a `README.md` and stack-aware empty stubs during scaffold-init. No enforcement, no breaking-change detection, no test scaffolding.

- **Pro:** Promotes the skill from stub to active. Provides an on-ramp.
- **Con:** Ships premature surface area — users see `contracts/` and wonder what to put in it before they hit a real cross-module-coupling problem. This is the ECC trap (kitchen-sink scaffolding) we explicitly avoided.

### Option B: Defer the whole spec
Update the stub SKILL.md to reflect that the skill is deliberately not implemented yet, with a clear resolution trigger. No code changes; the stub stays slash-invocable so users discovering it get a clear explanation.

- **Pro:** Honest about what we don't know. Costs five minutes.
- **Con:** One stub remains in Tier 0.

### Option C: Reinterpret for jig itself
Treat each skill's CLI as the contract. Write `contracts/<skill>.md` documenting input/output for each helper. Add a PreToolUse hook blocking Python imports across `skills/*/` directories.

- **Pro:** Dogfoods the skill against its own design.
- **Con:** jig's modules are already independent — they communicate via filesystem, not imports. Encoding rules that aren't being violated doesn't pay off. Risks over-engineering.

## Recommended Decision

**Option B.** The decision rests on three observations:

1. **The other four promotions worked because we'd run the patterns by hand 10+ times.** scaffold-init, memory-sync, spec-workflow, and independent-review all had clear shape from dogfooding before they were codified. `contracts` has been run zero times in jig — we have no real-world coupling to codify.

2. **jig has no real module boundaries to enforce.** The one cross-skill coupling we have (the `find_slice_section` / `find_slice_label` near-duplication between `workflow.py` and `review.py`) was deliberately handled by duplication, not abstraction (see slice 004-01 deviation log, design choice #1). If we couldn't find a third caller, we kept it inline. That is the exact situation contracts is meant to address — and we chose not to address it.

3. **Speculative scaffolding ages badly.** A `contracts/` directory shipped without a real coupling problem creates a "what do I put here?" moment that erodes trust. Better to leave the skill discoverable as a clearly-labeled stub.

## Consequences

**Becomes easier:**
- Spec 005's slot stays open for a higher-signal item (Tier 1 skills, or a real cross-skill coupling pain point if one emerges).
- The `contracts` SKILL.md becomes informational rather than aspirational — users get a clear explanation if they invoke `/jig:contracts` directly.

**Becomes harder:**
- AI-native projects that benefit from boundary enforcement won't get it from jig out of the box. Documented as a known limitation.

**Resolution trigger for revisiting:**
- **First time jig has three callers that need the same helper.** That is the trigger to extract `skills/_common/<module>.py` AND to introduce a real contract for it. From there, the broader `contracts` skill has a concrete case to design against.
- **Alternatively:** first time a real user reports their project hit cross-module-coupling pain that jig could have prevented.

## Open questions

None. (If we later disagree, supersede with a new ADR rather than editing this one.)
