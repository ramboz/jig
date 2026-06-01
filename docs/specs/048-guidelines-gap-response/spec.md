---
status: DONE
skill: scaffold-init, spec-workflow, analyze
tier: product/docs
adr_required: false
---

# Spec 048: Guidelines gap response

## Overview

The 2026-05-28 comparison between
`adobe/mysticat-ai-native-guidelines` and jig showed a clean split:
Mysticat is the stronger playbook, while jig is the stronger machine.
jig has executable workflow machinery, tests, hooks, helpers, plugin
packaging, and dogfooded specs. It is weaker at first-read product
framing, adoption guidance, cross-tool expectation setting, and
reader-friendly handling of amendment-heavy docs.

This spec addresses the gaps that are product-facing and adoption-facing
without duplicating the deeper mechanical specs already open:

- Spec 033 owns host adapter portability and the `AGENTS.md` route.
- Spec 038 owns tier policy and scaffold reality.
- Spec 040 owns isolation-honesty wording.
- Spec 046 owns scaffold artifact fidelity.
- Spec 047 owns install contract verification.
- Spec 045 owns review lifecycle evidence and transition gates.

The work here is the connective layer: make jig's public story current,
show users how to evaluate/adopt it, expose the gap response roadmap, and
reduce the reading cost of closed-spec amendments.

> **Re-review (2026-06-01).** A second pass over the full guidelines corpus
> (EDD excluded — owned by servo) confirmed the May framing and refined the
> gap map. It surfaced one gap the May comparison missed: jig scaffolds
> **no security/secrets floor**. The refreshed, routed gap inventory lives
> in the "Re-review update (2026-06-01)" section below; the machinery gaps
> it found are routed OUT of this spec per the Non-goals.

## Goals

1. **Make first-read docs current and honest.** `README.md` and the
   product-facing docs should no longer imply early draft status, hidden
   cross-tool support, strict reviewer isolation, or tier behavior that
   has not landed.
2. **Add a small adoption/readiness guide.** Borrow Mysticat's useful
   adoption posture, but keep it jig-sized: who should use jig, what a
   repo needs before scaffolding, what happens in the first 30 minutes,
   and what to check after a few slices.
3. **Expose the gap response map.** A reader should see which gaps are
   fixed by this spec and which are intentionally delegated to existing
   draft specs.
4. **Improve amendment readability.** Closed-spec amendments preserve
   history, but readers need a concise "effective current state" view so
   they do not have to mentally patch every old paragraph.
5. **Keep the machine tight.** This spec should not turn jig into a
   broad organizational handbook. It adds just enough playbook surface to
   make the existing machinery legible.
6. **Close the cold-start cliff.** A freshly scaffolded project should
   open with a complete `DONE` worked-example spec and a deterministic
   "scaffold complete and verified" signal. jig enforces little via hooks,
   so a blank scaffold gives the model neither enforcement nor a pattern
   to imitate — and it skips the workflow. A seeded reference spec plus a
   completion check supply the missing pattern and assurance. Lifecycle
   *enforcement* itself is delegated to spec 045 (review lifecycle gates),
   not decided here.

## Non-goals

- **No Codex implementation.** Spec 033 owns future Codex scaffold and
  plugin support. This spec can point to that work, but does not ship it.
- **No tier-policy decision.** Spec 038 decides whether tiers are real
  copy gates or informational groupings.
- **No isolation-mechanism change.** Spec 040 aligns wording with the
  current reviewer mechanism. This spec should coordinate with it, not
  replace it.
- **No scaffold command/link repair.** Spec 046 owns install-shape
  correctness for generated scaffold artifacts.
- **No MkDocs site or leadership curriculum.** Mysticat's broader docs
  are useful, but jig should stay a compact workflow scaffold.
- **No rewrite of closed specs.** Amendment digesting must preserve the
  original historical artifacts and ADR-0008's amendment policy.

## Current state verified 2026-05-28

- jig's full local suite passes: `python3 scripts/run_tests.py` ran 1397
  tests with 3 skipped.
- `python3 scripts/spec_lint.py --all` found no contradictions across
  46 specs.
- `python3 scripts/validate_manifests.py` passed 3/3 manifest checks.
- `README.md` still contains an outdated `Status` section that says Tier
  0 skills are in spec/draft phase and names the first implementation
  slice, even though Tier 0 and Tier 1 are effectively implemented and
  the current open work is specs 033-047.
- `README.md`, `docs/product-vision.md`, and `docs/workflow.md` are
  already known coordination points for specs 038 and 040.
- Several closed artifacts now carry `## Amendments` sections per
  ADR-0008, which is correct for auditability but increases reader cost.

## Re-review update (2026-06-01)

A second comparison pass read the full guidelines corpus (EDD excluded —
owned by servo). It confirmed the May framing ("Mysticat is the stronger
playbook; jig is the stronger machine") and changed the picture in three
ways.

**Several delegated gaps have since landed.** As of 2026-06-01: spec 038
(tier truth), 040 (isolation honesty), 042 (spec-gate model), and 036
(closed-spec drift) are **DONE**; 016 (scaffold-mode) and 026 (context-fill
telemetry) are **DONE**.

**The product/docs gaps this spec owns are still unbuilt.** All four 048
slices remain DRAFT, and the cross-tool route (033) is DRAFT with its Codex
slices DEFERRED — so the gaps the May pass *identified* are still open in
practice.

**Net-new finding (not in the May comparison): jig scaffolds no
security/secrets floor.** The guidelines' single largest MUST cluster
(`05-guardrails/must-rules.md`, `04-configuration/env-secrets.md`,
`permissions.md`, `05-guardrails/mechanical-enforcement.md`) has *zero*
mechanical enforcement in a scaffolded jig project: the
[CLAUDE.md template](../../../templates/CLAUDE.md.template) has no rules
block, [conventions.md](../../conventions.md) is authoring-only, there is
no scaffolded `.gitignore`, the scaffolded `settings.json` carries no
`permissions` deny-rules, and none of the seven hooks is a secret-scan.
This is the sharpest divergence in the comparison, because jig's founding
principle is "everything that MUST happen is a hook" — yet the biggest MUST
set is unenforced.

Verification (2026-06-01): `python3 scripts/spec_lint.py --all` passes (no
cross-spec contradictions) after this update.

### Gap inventory (routed)

Where jig *meets or exceeds* the guidelines — mechanical-enforcement-first
hooks, progressive disclosure / tiers, context-fill telemetry,
multi-session / worktree / parallel-locks, the spec-driven lifecycle, and
memory continuity — is omitted here; this table is the gap surface only.

**A. Owned by this spec (product / docs / adoption).**

| Gap | Guideline source | Owner |
|---|---|---|
| Stale first-read status | `06-adoption` | 048-01 |
| Cross-tool expectation-setting (state "Claude-only today") | `04-configuration/cross-tool-setup.md` | 048-01 (doc) |
| Adoption / readiness guide | `06-adoption/ai-readiness-checklist.md` | 048-02 |
| Scaffolded onboarding handoff | `06-adoption/onboarding-guide.md` | 048-03 |
| Amendment-readability digest | jig-specific (ADR-0008) | 048-04 |

**B. Delegated to existing specs (status as of 2026-06-01).**

| Gap | Owner | Status |
|---|---|---|
| Cross-tool / `AGENTS.md` implementation | [033](../033-host-adapter-portability/spec.md) | DRAFT (Codex DEFERRED) |
| Tier truth | [038](../038-tier-reconciliation/spec.md) | **DONE** |
| Isolation honesty | [040](../040-isolation-honesty/spec.md) | **DONE** |
| Scaffold artifact fidelity | [046](../046-scaffold-artifact-fidelity/spec.md) | DRAFT |
| Install contract verification | [047](../047-install-contract-verification/spec.md) | DRAFT |

**C. Net-new (2026-06-01) — routed OUT of this spec.** 048 stays
product/docs-scoped (see Non-goals); these are recorded for the gap map and
routed to their proper home. None is fixed by 048.

| Gap | Guideline source | Severity | Proposed home |
|---|---|---|---|
| **Security/secrets floor** — MUST rules + `.gitignore` secret patterns + secret-scan hook + a `security-review` depth baseline | `must-rules.md`, `env-secrets.md`, `mechanical-enforcement.md` | P1 | **[Spec 052](../052-security-scaffold/spec.md)** (052-02 mechanical floor + 052-05 slim `security-review` baseline that orchestrates installed scanners and defers to any richer installed skill — not vendor-specific) |
| **Permission deny-rules** in scaffolded `settings.json` (force-push / hard-reset / `rm -rf`) | `04-configuration/permissions.md` | P1 | **[Spec 052](../052-security-scaffold/spec.md)** (052-03) |
| **AI-usage disclosure** block in the generated PR body | `03-templates/pull-request-template.md` | P1 | slice on the `slice-land` PR-body renderer, or new spec |
| **Baseline-alignment** depth — bidirectional (directional + volume) + diagonal impl-vs-spec check | `02-lifecycle/baseline-alignment.md` | P2 | enhancement to `independent-review` / `analyze` |
| **Operating-mode + substrate framing** + director-mode prerequisites | `01-foundations/operating-modes.md`, `substrate-model.md` | P2 | docs slice (here or a foundations doc) |
| **Model-routing / token playbook** (Sonnet default, effort, `/compact`, MCP audit) | `04-configuration/token-efficiency.md` | P2 | small `docs/workflow.md` addition |
| **Config-evolution discipline** (Three-Times rule, promote/demote, quarterly review) | `02-lifecycle/06-config-evolution.md` | P2 | `memory-sync` enhancement |
| **ADR-template parity** (Integrity Challenge; Positive/Negative/Neutral consequences) | `03-templates/decision-record.md` | P3 | `adr-workflow` template tweak |

**D. Deliberate divergence / out of jig scope (no action).**

- **Component contracts / TFD+DBC** — guidelines prescribe a
  component-contract altitude + tests-from-contract; jig goes spec → slice
  → TDD with no contract layer by decision
  ([ADR-0002](../../decisions/adr-0002-contracts-stays-deferred.md),
  [ADR-0005](../../decisions/adr-0005-contracts-as-judgment-skill.md)).
- **Migration-plan template, 5-layer validation / staging / observability
  / rollback, workspace bootstrap (`init.sh`, `mani.yaml`), MkDocs site,
  leadership / leveling curricula** — project-specific or excluded by
  [product-vision](../../product-vision.md) ("No MkDocs site or leadership
  curriculum"); the workspace-level ambition is tracked by
  [034 federation-tier](../034-federation-tier/spec.md) (DRAFT).
- **Eval-driven development family** (eval datasets, LLM-as-judge,
  dual-tracing, tool-replay, self-improving / auto-improve agents, an
  `evals/` dir per skill) → **servo**.

## Decomposition

**Suggested SPIDR axis: Interface.** The gaps are about the interface a
new user or evaluator encounters: README, adoption docs, scaffolded
first-run guidance, and current-state summaries.

### Slices

1. **`048-01 first-read-status-and-gap-map`** - Refresh the public
   entry points so a reader can tell what jig does today, what is
   intentionally Claude-specific today, and where the known gap specs
   live.
2. **`048-02 adoption-readiness-guide`** - Add a concise guide/checklist
   for deciding whether and how to adopt jig in a repo.
3. **`048-03 scaffolded-onboarding-handoff`** - Make the scaffolded
   project point users at the new adoption/readiness material without
   adding a large always-loaded prompt burden.
4. **`048-04 amendment-effective-state-digest`** - Add a generated or
   scriptable digest of amendment-bearing artifacts so readers can find
   current truth without rereading historical drift blocks.
5. **`048-05 seed-reference-spec`** - Emit a complete `DONE` worked-example
   spec (`001-adopt-jig`) plus a `DRAFT` `002-first-spec` hand-off stub and
   a populated status board, so a cold-start project has a faithful pattern
   to imitate. Honest-by-construction: review boxes are satisfied by the
   deterministic completion check (048-06), never a rubber-stamp subagent
   verdict.
6. **`048-06 scaffold-completion-verification`** - Run the existing
   `verify_install.py` scaffold checks at the end of `scaffold-init` and
   surface a pass/fail summary, so the user gets a deterministic "complete
   and wired" signal. Reuses existing/047 checks; defines no new contract
   and no new skill.

## Dependencies / coordination

- Slice 048-01 must coordinate with specs 038 and 040 because all three
  touch README/product positioning. If those specs have not landed, this
  slice should point at them rather than deciding their policies.
- Slice 048-03 should coordinate with spec 046 because both touch
  scaffolded documentation and first-run commands.
- Slice 048-04 depends on ADR-0008 / spec 036 and must preserve the
  closed-spec drift policy rather than replacing it.
- Slice 048-05 should coordinate with spec 046 (scaffold output must not
  leak plugin-root/source paths) and emits a real spec that must pass
  `spec_lint.py` like any other.
- Slice 048-06 depends on 048-05 (the verifier's expected set includes the
  seed) and coordinates with spec 047, which owns the contract surface —
  048-06 *calls* the verifier, it does not redefine it. The re-runnable
  on-demand verification skill is explicitly deferred until signal.
- If a slice needs to change `docs/conventions.md`, stop and ask for
  explicit human approval before implementation.
- The 2026-06-01 net-new gaps (Gap inventory C) are routed OUT of this
  spec by its Non-goals; standing up their specs is follow-up work, not a
  048 dependency. The security/secrets floor (P1) is the recommended first
  new spec.

## References

- [adobe/mysticat-ai-native-guidelines](https://github.com/adobe/mysticat-ai-native-guidelines)
  — comparison baseline (2026-05-28 and 2026-06-01 passes).
- servo owns the eval-driven-development surface deliberately excluded from
  this comparison.
- [README.md](../../../README.md)
- [docs/product-vision.md](../../../docs/product-vision.md)
- [docs/workflow.md](../../../docs/workflow.md)
- [docs/specs/033-host-adapter-portability/spec.md](../033-host-adapter-portability/spec.md)
- [docs/specs/038-tier-reconciliation/spec.md](../038-tier-reconciliation/spec.md)
- [docs/specs/040-isolation-honesty/spec.md](../040-isolation-honesty/spec.md)
- [docs/specs/046-scaffold-artifact-fidelity/spec.md](../046-scaffold-artifact-fidelity/spec.md)
- [docs/specs/047-install-contract-verification/spec.md](../047-install-contract-verification/spec.md)
- [docs/specs/045-review-lifecycle-gates/spec.md](../045-review-lifecycle-gates/spec.md)
- [ADR-0008: Closed-spec drift policy](../../decisions/adr-0008-closed-spec-drift-policy.md)
