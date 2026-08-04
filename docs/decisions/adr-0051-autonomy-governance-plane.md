---
status: Proposed
dependencies: [adr-0011, adr-0013]
last_verified: 2026-08-04
frame_review: true
---

# ADR-0051: Autonomy governance plane and identity separation

## Status

Proposed (2026-08-04)

> **Recorded, not yet built.** This ADR captures the governance-plane decision for
> the long-horizon-autonomy bridge (the `oh-my-cli` follow-on). It is paired with
> the DRAFT [spec 106](../specs/106-autonomy-governance-plane/spec.md). No
> `scaffold-init` code changes ship with this record.

## Context

`oh-my-cli`'s "the agent can't rewrite its own rules" plane is only as strong as
CODEOWNERS + branch protection behind it. jig already *says* this — `jig-spec-gate.sh`
comments explicitly direct enforcement out-of-band ("CODEOWNERS … a CI check on
the PR diff … branch protection"), consistent with ADR-0011 (hooks are
*deliberateness* nudges, real control is out-of-band) and ADR-0013 (security
floor is defense-in-depth, not a firewall). But jig only **recommends** these; it
never **scaffolds** them. An autonomous loop pointed at a repo with no CODEOWNERS
and no protected-path CI has soft nudges and nothing else standing between it and
its own governing artifacts (`conventions.md`, the decision log, the oracle).

A second, deeper gap surfaced in design review: **identity collapse.** Every
GitHub "owner approval" gate keys off *author identity* — "require a review from
someone other than the author," "require review from Code Owners," the block on
self-approval. All of them assume the principal that **proposes** a change and the
principal that **approves** it are different. If the autonomous agent commits,
pushes, and opens PRs under the *human's own credentials*, there is exactly one
principal, and:

- the human cannot approve the PR (GitHub blocks self-approval);
- even if they could, a self-review does not satisfy "require review from a
  non-author";
- so the branch-protection rule is either unsatisfiable or vacuous.

The gate is not weak — it is **fictional**, because nobody is on the other side of
it. A governance plane layered on a single identity is theatre. This ADR decides
that jig must (a) scaffold the out-of-band teeth it currently only recommends, and
(b) treat **two-principal identity separation as a precondition** for claiming a
repo is autonomy-ready.

## Decision Options Considered

### Option A: Keep recommending; scaffold nothing (status quo)
- **Pros:** Zero new scaffold surface.
- **Cons:** The plane exists only as prose comments. Leaves the identity-collapse
  hole entirely unaddressed. Rejected: does not meet the autonomy target.

### Option B: Scaffold CODEOWNERS + protected-path CI + `protected_paths`, and gate autonomy on identity separation (recommended)
- **Pros:** Turns the recommendation into artifacts with teeth (CI is the
  firewall; hooks stay nudges, honoring ADR-0011). Names the two-principal
  requirement explicitly and makes it checkable, so a governance plane is never
  shipped as theatre. Soft hooks (`entry-gate`, `boundary-warn`) can read
  `protected_paths` to nudge *in*-boundary while CI enforces *out*-of-boundary —
  defense-in-depth per ADR-0013.
- **Cons:** Scaffold writes `.github/` content and a CODEOWNERS the project must
  own; the identity check needs a reliable way to compare run-identity vs
  merge-identity (may be environment-specific).

### Option C: Enforce entirely in hooks (make the PostToolUse gate hard-fail on protected paths)
- **Pros:** No dependency on GitHub settings.
- **Cons:** Directly violates ADR-0011 — hooks are deliberateness nudges, not
  firewalls; a local hook is trivially bypassable by the same agent it governs
  (it runs with the agent's own privileges). Rejected on principle.

## Recommended Decision

Adopt **Option B**. jig scaffolds the governance plane and gates autonomy on
identity separation:

1. **`scaffold-init` writes a `CODEOWNERS`** naming protected paths
   (`docs/conventions.md`, `docs/decisions/**`, `oracle.sh`, frozen
   `.servo/**/config.json`) to an owner distinct from the autonomous agent, plus a
   **`.github/workflows/` CI job that fails any PR whose diff touches a protected
   path without owner approval.** CI is the real enforcement.
2. **`protected_paths` in `scaffold.json`.** Existing soft hooks (`entry-gate`,
   `boundary-warn`) read it to nudge when an edit lands in-boundary; CI enforces
   the out-of-boundary firewall. Single source of truth for both layers.
3. **Governance-proposal routing rule (formalized).** A change to a protected
   artifact must open an ADR/spec, never a self-edit — the surface-and-stop
   posture spec 102 already defines in prose. servo's negative-control approval is
   the same rule for frozen evals.
4. **Identity separation is a precondition, not an afterthought.** For a repo to
   be *autonomy-ready*, the principal that runs the loop must differ from the
   principal that can merge its output and edit branch protection. Concretely:
   - the agent commits/pushes/opens PRs under a **distinct machine identity**
     (GitHub App installation or dedicated bot), never the human's personal
     credentials — so the human is a genuine non-author approver;
   - that identity is **least-privilege**: no merge rights on protected branches,
     no `administration` scope (cannot edit branch protection / CODEOWNERS), and
     "do not allow bypassing the above settings" is on;
   - **the degenerate single-identity case is named as unsafe.** When the loop's
     identity *is* the merge identity (e.g. a personal PAT), no GitHub-side gate
     can work; enforcement must move fully off-GitHub (the agent's environment
     holds no credential that can merge to the base branch). The servo
     autonomy-readiness gate (servo ADR-0029) encodes this as a deterministic
     **run-identity ≠ merge-identity** check that returns `unsafe_for_autonomy`
     when they coincide.

## Consequences

**Becomes easier:**
- A scaffolded repo ships with real, out-of-band protection of its governing
  artifacts, not just advice.
- "Is this repo safe to run unattended?" becomes a concrete, checkable question
  instead of an assumption.

**Becomes harder:**
- Operators must provision a second (bot/App) identity to unlock autonomy — the
  right friction, but friction. jig should explain *why* rather than just refuse.
- Scaffolding now owns `.github/` templates that projects may need to adapt.

## Assumptions

- The target's host is GitHub (CODEOWNERS + branch protection semantics). _Other
  forges are out of scope for this record; a non-GitHub host would need its own
  mapping._
- The runtime can observe enough to compare run-identity vs merge-identity (token
  identity / configured merge principal). _Probe before building: the exact signal
  is environment-specific and must be pinned in slice 106-01 / servo 023-01, not
  assumed here._

## Kill criteria

- If, in target environments, a second identity cannot be provisioned at all, the
  "two principals or refuse" stance blocks every real user — revisit toward a
  clearly-labelled degraded mode rather than a hard refusal.
- If CI protected-path enforcement proves trivially bypassable in practice (e.g.
  the agent can also edit the workflow), the plane is theatre again — the workflow
  file itself must be a protected path, and that self-reference must hold.

## Open questions

- Where the "independent owner" comes from in a solo-maintainer repo (the human
  is both author-of-record and owner) — resolve in spec 106; may reduce to "the
  human merges manually, agent holds no merge credential."
- Exact CODEOWNERS + workflow templates and their placement under `templates/`.
