# eng-tips self-audit — brief bundle

Five briefs from a 2026-06-19 review of jig against Adobe's
[Engineering Tips](https://developers.corp.adobe.com/engtips) series
(EngTips #1–#26, read from a local clone at the time of review). Each is
a half-page input for `/jig:clarify` and `/jig:spec-workflow new`.

The framing finding of the review: jig is an unusually faithful
implementation of the *AI-workflow* half of the tips (EngTips #6, #16,
#20, #23, #24, #26) — in several places ahead of them. The actionable
gaps are all variations on one theme — **jig holds its consumers to its
own tips (tighten the contract, keep context lean) more strictly than it
holds itself.** These five briefs close that gap.

## How to use

Same loop as the [parent bundle](../README.md): each brief is the
*input* to clarify, not a finished spec. Don't paste a brief into
`spec.md`; let jig author the spec in its own conventions.

For each brief:

1. Read the brief and confirm scope/non-goals match your intent.
2. Run `/jig:clarify` with the brief content; address the questions.
3. Run `/jig:spec-workflow new <slug>` to reserve a number.
4. Hand jig the clarified brief and let it draft `spec.md` + slices
   per the suggested SPIDR axis.
5. Drive the normal lifecycle: READY_FOR_REVIEW → spec review pass →
   READY_FOR_IMPLEMENTATION → IN_PROGRESS → three-pass review → DONE.

## Recommended order

**Phase 1 — Dogfood win (do first):**

- **brief-01** — lean the always-loaded primer. Highest leverage, pure
  self-application of jig's own context-cost discipline (spec 055/057).
  The lean `AGENTS.md` already exists as the target shape, so this is
  largely a migration, not a design problem.

**Phase 2 — Tighten jig's own contracts (parallelizable):**

- **brief-02** — type-check floor. Adds the EngTip #3 discipline (make
  nullability/contracts statically enforceable) to jig's own helpers.
  Mechanical once the advisory-vs-gating decision is made.
- **brief-04** — gate-bypass telemetry. Makes the honest "deliberateness,
  not enforcement" escape hatches *observable* instead of silent.
  Extends existing telemetry infra (spec 041 / `jig-telemetry`).

**Phase 3 — New recommendations (standalone):**

- **brief-05** — semantic-index recommendation. Wires EngTip #26
  (Tokensave) / #23 into the context-cost skill as an orchestrated,
  install-nothing recommendation (mirrors `contracts` / `code-health`).

**Phase 4 — Most speculative (consider inbox instead):**

- **brief-03** — test-type taxonomy. The fuzziest of the five; may be
  doc-only (a convention + reviewer nudge) rather than a tool. Pull it
  forward only if a real coverage-gap escape motivates it; otherwise it
  is honest inbox material.

## Brief-to-tip mapping

| Brief | EngTip(s) | jig surface touched | Shape |
|---|---|---|---|
| 01 — lean-primer | #23, #26, #1, #55-self | `CLAUDE.md`, `docs/memory/glossary.md`, `lexicon.json`, `jig:explain` | 1–2 slices |
| 02 — type-check-floor | #3, #11 | `health.py`, `ruff.toml`, `_common/*.py`, ADR-0017 | ADR-light + 1–2 slices |
| 03 — test-type-taxonomy | #21, #12, #15, #17 | reviewer prompts, `coverage` report, `docs/conventions.md` | ADR + 1 doc slice |
| 04 — gate-bypass-telemetry | #19, #20, #11 | `jig-telemetry`, gate hooks, `JIG_*_GATE` envs, `routing-stats` | 1–2 slices |
| 05 — semantic-index-recommendation | #26, #23 | context-cost skill, `docs/workflow.md`, scaffold nudge | 1–2 slices |

## What's not in this bundle

- **The human/team tips (#1, #4, #18, #19, #25)** — psychological safety,
  co-innovation, knowledge sharing, mentorship. A scaffold can't embody
  team culture, and jig is right not to fake it. The one stretch worth
  a *future* inbox note (not a brief): EngTip #18's co-innovation loop
  has no analog — jig captures vision/use-cases at framing time but has
  no mechanism to feed real usage from scaffolded projects back into the
  workflow. No trigger today; leave it per "grow by signal, not
  speculation."
- **Areas jig already leads** — EngTips #6, #16, #20, #24 are already
  well-covered by the spec lifecycle, frame-critique, review-evidence
  gate, and vertical slices. Nothing to add.
- **EngTip #13 (secrets), #14 (dead code), #9 (tests-with-code), #7
  (docs-as-code)** — audited as already-strong (security floor,
  zero shipped dead code, co-located tests, closed-spec drift policy).
  No brief needed.
