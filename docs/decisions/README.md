# Decisions

> Architectural Decision Records. Nygard convention: immutable after acceptance.
> New decisions supersede old ones — never edit an accepted ADR.

## Index

- [ADR-0001: scaffold-stable trigger](adr-0001-scaffold-stable.md) — scaffold-init generates docs with `Status: Draft (wizard-generated)` markers at the top. (2026-05-12, Accepted)
- [ADR-0002: `contracts` skill stays a deliberate stub](adr-0002-contracts-stays-deferred.md) — `contracts` is the last Tier 0 skill that remains a `disable-model-invocation: true` stub after specs 001–004 promoted the other four (`scaffold-init`, `memory-sync`, `spec-workflow`, `independent-review`). (2026-05-15, Superseded)
- [ADR-0003: Extract `find_slice_section` to `skills/_common/parsing.py`](adr-0003-extract-find-slice-section.md) — [ADR-0002](adr-0002-contracts-stays-deferred.md) named "first time jig has three callers that need the same helper" as the trigger to extract `skills/_common/<module>.py`. (2026-05-12, Accepted)
- [ADR-0004: Rename docs/adrs/ to docs/decisions/ and prefix files with adr-](adr-0004-decisions-folder-naming.md) — jig's default ADR layout (at the time of this ADR) was `docs/adrs/NNNN-<slug>.md`, which is internally consistent and matches Nygard's original blog post but has two usability gaps that surfaced while dogfooding jig against the aso-shallow-validator project — a mature spec-driven repo that organically grew the same workflow jig codifies but landed on a different naming convention (`docs/decisions/adr-NNN-<slug>.md`). (2026-05-12, Accepted)
- [ADR-0005: contracts skill is a judgment-skill nudging toward standard external-interface artifacts](adr-0005-contracts-as-judgment-skill.md) — [ADR-0002](./adr-0002-contracts-stays-deferred.md) deferred the `contracts` skill until "a third caller needs the duplicated lookup, OR a real user reports cross-module-coupling pain." Both triggers framed contracts as an **internal-boundary** problem inside the codebase: duplication of lookup logic, cross-module imports, scaffolding-with-stubs. (2026-05-15, Accepted)
- [ADR-0006: adr.py accept-then-index ordering](adr-0006-adr-accept-then-index-ordering.md) — `adr.py` ships four subcommands: `new`, `accept`, `index`, `resolve-todo`. (2026-05-15, Accepted)
- [ADR-0007: scaffold.json gains per-skill install list](adr-0007-scaffold-json-installed-skills.md) — The `scaffold.json` install-state manifest currently tracks granularity at the tier level only. (2026-05-15, Accepted)
- [ADR-0008: Closed-spec drift policy](adr-0008-closed-spec-drift-policy.md) — jig's process treats ADRs as immutable per ADR-0006 / Nygard. (2026-05-29, Superseded)
- [ADR-0009: RTK (Rust Token Killer) not adopted for jig](adr-0009-rtk-not-adopted.md) — [RTK](https://github.com/rtk-ai/rtk) is a Rust-based CLI proxy ("Rust Token Killer") that compresses command output before it reaches an LLM's context window. (2026-05-28, Accepted)
- [ADR-0010: Amendment scope — records vs. live operational prose](adr-0010-amendment-scope-records-vs-live-prose.md) — The `## Amendments` drift mechanism fits records but not live operational prose; this ADR narrows its scope accordingly. (2026-05-29, Accepted)
- [ADR-0011: Spec-gate model — deliberateness signal, not human-only approval](adr-0011-spec-gate-model.md) — `hooks/scripts/jig-spec-gate.sh` blocks `Edit`/`Write`/`MultiEdit` to `docs/conventions.md` unless `JIG_CONVENTIONS_APPROVED=1` is set in the environment (PreToolUse, exit 2 to block). (2026-05-29, Accepted)
- [ADR-0012: Scaffold-init tiers gate which skills install](adr-0012-scaffold-tier-gated-install.md) — jig's positioning rests on "tier-gated installs": the README and product-vision docs present Tier 0 as a small, opinionated floor and Tier 1 as an opt-in default. (2026-05-29, Accepted)
- [ADR-0013: Security-scaffold floor policy](adr-0013-security-floor-policy.md) — jig's founding design principle is *"everything that MUST happen is a hook"* — deterministic enforcement over human vigilance. (2026-06-01, Accepted)
- [ADR-0014: Review-evidence model — durable verdict artifacts gate the lifecycle](adr-0014-review-evidence-model.md) — jig's workflow documentation presents post-implementation review and reconciliation as load-bearing gates. (2026-06-01, Accepted)
- [ADR-0015: Worktree-aware number reservation — branch-routed reserve, detached worktree off main](adr-0015-worktree-aware-reservation.md) — [Spec 003-03](../specs/003-spec-workflow-promotion/spec.md) (spec numbers, `workflow.py new`) and [spec 028-01](../specs/028-parallel-session-locks/slice-01-adr-numbering-on-main.md) (ADR numbers, `adr.py new`) built reserve-on-`origin/main`: claim a sequential number by committing a stub and pushing it to `origin/main`, so parallel sessions cannot both grab the same `NNN`/`NNNN`. (2026-06-02, Accepted)
- [ADR-0016: Parallel proportional bug-fix lifecycle](adr-0016-bug-fix-lifecycle.md) — Not all work in a jig project is spec-driven. (2026-06-03, Proposed)
- [ADR-0017: Code-health as a scaffolded, language-detected capability](adr-0017-scaffolded-code-health.md) — jig has no code-health capability. (2026-06-04, Accepted)
- [ADR-0019: Parallel proportional refactor / migration workflow](adr-0019-refactor-workflow.md) — jig is growing a small family of work-shaped lifecycles. (2026-06-05, Proposed)
- [ADR-0020: Spec/ADR Frame-Hardening: Grounding + Adversarial Frame-Critique](adr-0020-spec-frame-hardening.md) — jig's reviewer subagents (compliance / craft / arch / code-health, per [ADR-0014](adr-0014-review-evidence-model.md)) all validate that an *implementation conforms to its spec/ADR*. (2026-06-07, Accepted)
- [ADR-0021: Canonical lexicon home and project-glossary overlay](adr-0021-lexicon-home-and-overlay.md) — [Spec 065](../specs/065-lower-vocabulary-barrier/spec.md) lowers the vocabulary barrier for non-expert readers of jig artifacts. (2026-06-07, Accepted)
- [ADR-0022: Pluggable oracle boundary — bind the lifecycle oracle to servo](adr-0022-pluggable-oracle-boundary.md) — jig now has a **family of three gated-evidence lifecycles**, all mirroring ADR-0014's transition-gate architecture and r… (2026-06-09, Proposed)
- [ADR-0023: The lifecycle-family spine — shared contract and convergence rule for gated-evidence workflows](adr-0023-lifecycle-family-spine.md) — jig has organically grown a **family of work-shaped lifecycles**, each recorded in its own ADR, each independently re-de… (2026-06-09, Proposed)
- [ADR-0024: Reframe on a load-bearing reference shift — a lightweight correction capability over the spine](adr-0024-reference-reframe.md) — jig is built to keep work **consistent with prior decisions**. (2026-06-09, Proposed)
- [ADR-0025: Use cases as a first-class breadth layer](adr-0025-use-cases-breadth-layer.md) — jig's artifact stack runs **vision → spec → slice**. (2026-06-10, Accepted)
- [ADR-0026: Frontmatter is the canonical home for ADR status](adr-0026-adr-status-frontmatter.md) — ADR status lives only in prose; slice status lives in frontmatter. (2026-06-15, Accepted)
- [ADR-0027: Host-native phase modes are advisory workflow affordances](adr-0027-host-native-phase-modes.md) — Jig already has a durable workflow model: specs, slices, review evidence, state transitions, deviation logs, and ADRs. (2026-06-17, Proposed)

## Format

Each ADR lives at `docs/decisions/adr-NNNN-<slug>.md`. Title: `# ADR-NNNN: <Title>`.

Required sections: Status, Context, Decision Options Considered, Recommended Decision, Consequences.

## When to write an ADR

- Hard-to-reverse decisions
- Decisions that affect multiple modules or the public API
- When a contract changes in a breaking way
- When the `architect` subagent produces a proposal that is accepted
