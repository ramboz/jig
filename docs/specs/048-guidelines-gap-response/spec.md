---
status: IN_PROGRESS
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

## References

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
