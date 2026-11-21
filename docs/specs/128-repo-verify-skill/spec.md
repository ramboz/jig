---
status: DRAFT
skill: scaffold-init
use_cases: [UC-1, UC-5, UC-7, UC-15]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 128: Repo-verify skill

> Implements [ADR-0073](../../decisions/adr-0073-repo-verify-skill-contract.md)
> (Proposed). Investigation record:
> [R-002](../../research/R-002-claude-code-verification-assessment.md)
> (mechanism 4). **Status: recorded, not yet built** — reserved alongside the
> ADR so the decision has a home for its build; the ADR must be Accepted before
> 128-01 moves past DRAFT. Reserved on 2026-11-21 via `workflow.py new
> --no-push`; the number is provisional until merged.

## Overview

Give every project one place that says how to run the app: a project-owned
skill named `verify` with Boot, Drive, Inspect, Teardown and Known flaky
sections, plus an optional `verify-command:` a machine can call. scaffold-init
writes a stub once and never touches it again; jig's own repository gets a
filled one; and the slice template and compliance review point runtime evidence
at it.

Today each slice that needs runtime proof works out from scratch how to boot
and drive the app, inside its optional verification scenario
([spec 118](../118-behavioral-verification-pilot/spec.md)). The only per-repo
command jig knows is `.jig/test-command` (`skills/tdd-loop/tdd.py:142-154`),
which runs unit tests, not the app.

**How this relates to spec 118.** 118's non-goals read: "no new skill,
lifecycle state, gate, frontmatter field, parser, runner, wiki sync,
authentication system, or universal end-to-end test mandate." Its Evaluation
section deferred the next step to "a later real-project review … before
considering stronger enforcement." This spec is a deliberate revisit of one
part of that line, recorded in ADR-0073, and it stays inside the rest:

- **Not a new jig skill.** Nothing is added under `skills/`, to
  `scaffold._TIER_SKILLS`, or to any host package. The stub is a template that
  scaffold-init writes into the project, after which the project owns it.
- **Not a gate.** Nothing refuses a transition, review or commit because the
  skill is missing, unfilled or failing.
- **Not a runner in jig.** jig never runs a project's `verify-command`; the
  project's agent runs the skill, and servo spec 049 may call the command.
  The one exception is jig's own repository, where jig is the project.
- **No new slice frontmatter field and no parser.** 128-03 adds one optional
  line to the scenario body, read by the reviewer.
- **No mandate.** An unfilled stub reports `not-run`, which spec 118 already
  treats as "not a pass", not as a failure.

**Non-goals.** No commit gate for verify runs (spec 125). No stamp writing:
ADR-0073 defines what earns ADR-0069's `Verified-by: verify` token, and spec
124's renderer emits it. No seeding of existing projects — they copy the template by
hand until a `migrate` step is asked for (ADR-0073 Open questions). No
per-case input for servo (ADR-0073 Open questions). No change to
`governance.PROTECTED_PATHS` (ADR-0068's scope). No Codex or Copilot run of
jig's own verify journey in 128-02 (Claude plugin mode first).

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **A1 — project-skill folders (grounded in shipped code and the 113-01
  spike, not re-probed).** Claude Code reads `.claude/skills/`, Codex reads
  `.agents/skills/` (`skills/_common/skill_discovery.py:52-71`,
  `skills/scaffold-init/scaffold.py:1352-1353`); Copilot CLI reads
  `.github/skills/`, `.agents/skills/` and `.claude/skills/`
  ([113-01](../113-copilot-third-host/slice-01-copilot-contract-spike.md)
  AC2). So 128-01 writes `.claude/skills/verify/` for Claude and Copilot and
  `.agents/skills/verify/` for Codex.
- **A2 — hosts load a SKILL.md carrying an unknown top-level key
  (unverified).** Partial evidence: jig's Codex and Copilot packages carry
  `user-invocable: true` (`hosts/codex/plugins/jig/skills/tdd-loop/SKILL.md:11`,
  `hosts/copilot/.github/skills/tdd-loop/SKILL.md:11`). 128-01's DoR probes
  an arbitrary key on each host before implementation.
- **A3 — the discovery invariant is pinned only for the jig copy
  (grounded).** `ScaffoldExclusionInvariantTest`
  (`skills/_common/test_skill_discovery.py:349`) runs
  `scaffold._copy_skills_and_agents`, not `scaffold()`, so a stub written by
  `scaffold()` does not break it; the docstring claim at
  `skill_discovery.py:23-29` does become inaccurate and 128-01 corrects it.
- **A4 — the scaffold contract ignores unprefixed skill folders (grounded).**
  `scripts/scaffold_contract.py:153-156` walks only `jig-*` folders, so
  `verify_install.py --mode scaffold` neither requires nor rejects the stub.
- **A5 — `scripts/` does not ship (grounded).** `claude_install_smoke.py`
  guards that "no dev-only dirs — scripts/docs/tests — leak in" to the Claude
  package, so jig's own journey script in 128-02 is repo-local tooling.
- **A6 — the compliance block has room (grounded).** The current block is 838
  characters (measured 2026-11-21); 118's test bounds it at 1,400 with its
  marker (`skills/spec-workflow/test_behavioral_verification.py:158`).
- **A7 — an agent uses the project skill before committing (unverified).**
  Reported by the post for Claude Code; not probed on any host. ADR-0073 Kill
  criteria covers it.

## Decomposition

**SPIDR (Spike / Paths / Interfaces / Data / Rules).** Three slices, each with
its own observable result:

- **128-01 (Interfaces):** the contract reaches users — scaffold-init writes a
  host-neutral, never-overwritten stub, and discovery treats it as the
  project's own skill.
- **128-02 (Paths):** jig's own happy path — a filled verify skill whose
  command scaffolds a throwaway project and drives real helpers through one
  slice's lifecycle.
- **128-03 (Rules):** the slice template, spec-workflow and the compliance
  review point runtime evidence at the verify skill, and a scenario says
  whether its evidence came through it.

No Spike: the one open host question (A2) is a probe in 128-01's DoR, not an
investigation. **Anti-horizontal-phasing:** 128-01 alone gives new projects
the skill; 128-02 alone gives jig contributors a real end-to-end check; 128-03
alone makes existing scenarios name their source. 128-02 and 128-03 depend on
128-01 only for the contract's shape.

## Slices

- [128-01 — scaffold-writes-verify-stub](slice-01-scaffold-writes-verify-stub.md) — scaffold-init writes a host-neutral `verify` stub once; discovery tiers it as the project's own skill.
- [128-02 — jig-verifies-itself](slice-02-jig-verifies-itself.md) — jig's own verify skill scaffolds a throwaway project and drives real helpers through a slice's lifecycle.
- [128-03 — scenarios-name-the-verify-skill](slice-03-scenarios-name-the-verify-skill.md) — template, spec-workflow and compliance review point runtime evidence at the verify skill.
