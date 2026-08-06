---
status: Accepted
dependencies: [adr-0011, adr-0013]
last_verified: 2026-08-06
frame_review: true
---

# ADR-0051: Autonomy governance plane and identity separation

## Status

Accepted (2026-08-06)

> **Built (2026-08-06).** This ADR captures the governance-plane decision for the
> long-horizon-autonomy bridge (the `oh-my-cli` follow-on), and is implemented by
> [spec 106-01](../specs/106-autonomy-governance-plane/slice-01-scaffold-protected-plane-and-identity-gate.md):
> `scaffold-init` scaffolds the protected plane (CODEOWNERS + protected-path CI +
> `<docs>/governance.md`), writes `protected_paths` to `scaffold.json`, and ships
> `governance.py identity-check`. The servo halves (readiness gate, servo 023 /
> ADR-0029) remain to be built in `ramboz/servo`.

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
- **Pros:** Turns the recommendation into artifacts — the *scaffoldable half* of
  the firewall (CODEOWNERS + a protected-path CI job), while hooks stay nudges,
  honoring ADR-0011. Names the two-principal requirement explicitly and makes it
  checkable, so a governance plane is never shipped as theatre. Soft hooks
  (`entry-gate`, `boundary-warn`) read `protected_paths` to nudge *in*-boundary
  while CI + branch protection enforce *out*-of-boundary — defense-in-depth per
  ADR-0013.
- **Cons:** Scaffold writes `.github/` content and a CODEOWNERS the project must
  own — **but those files are inert until an out-of-band branch-protection step
  arms them** (require status checks, require Code Owner review, forbid
  bypassing); scaffold-init writes *files*, and branch protection is a
  server-side repository *setting* it cannot commit. jig must therefore document
  that arming step and never advertise the scaffolded files as enforcement on
  their own. The identity check needs a reliable way to compare run-identity vs
  the *merge capability* of that identity — the merge principal is a GitHub
  authorization fact, not a local config value, so this is environment-specific
  and supplied/attested rather than locally derived.

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
   `.servo/**/config.json`, **and the governance plane's own files —
   `.github/workflows/**` and `CODEOWNERS` itself**, so the self-reference the
   Kill criteria demand holds *by construction*: an ordinary commit/PR that edits
   the CI job or removes the owner is itself gated) to an owner distinct from the
   autonomous agent, plus a
   **`.github/workflows/` CI job that fails any PR whose diff touches a protected
   path without owner approval.** These are the **scaffoldable half** of the
   firewall. **They enforce nothing until branch protection is armed** — the CI
   job is only a blocking gate when the branch's protection rules *require* that
   status check and *forbid bypassing*, and CODEOWNERS only forces review when
   "require review from Code Owners" is on. Branch protection is a server-side
   repository setting, not a committable file, so scaffold-init cannot provision
   it. jig therefore **scaffolds the files and documents the out-of-band
   branch-protection arming step** (a checklist in the scaffolded governance
   material), and the autonomy-readiness gate (servo ADR-0029) is what verifies
   the armed state — the scaffolded files are never advertised as enforcement on
   their own.
2. **`protected_paths` in `scaffold.json`.** Existing soft hooks (`entry-gate`,
   `boundary-warn`) read it to nudge when an edit lands in-boundary; CI enforces
   the out-of-boundary firewall. Single source of truth for both layers.
3. **Governance-proposal routing rule (formalized).** A change to a protected
   artifact must open an ADR/spec, never a self-edit — the surface-and-stop
   posture spec 102 already defines in prose. servo's negative-control approval is
   the same rule for frozen evals.
4. **Capability separation is the precondition, not an afterthought.** For a repo
   to be *autonomy-ready*, the principal that runs the loop must lack the
   *capability* to merge its own output and edit branch protection. The safety
   fact is **merge capability, not identity name** — two facts that are easy to
   conflate and must not be:
   - the agent commits/pushes/opens PRs under a **distinct machine identity**
     (GitHub App installation or dedicated bot), never the human's personal
     credentials — so the human is a genuine non-author approver. Distinct
     identity is **necessary but not sufficient**: a *distinct* bot that is also
     an org admin (can merge / bypass protection) is still unsafe.
   - that identity is **least-privilege**: no merge rights on protected branches,
     no `administration` scope (cannot edit branch protection / CODEOWNERS), and
     "do not allow bypassing the above settings" is on. This is the property that
     actually matters, and it is a **GitHub server-side authorization fact** —
     there is no single local "who can merge this branch" value to read; deriving
     it requires the GitHub API against an already-configured repo.
   - **the degenerate single-identity case is named as unsafe.** When the loop's
     identity *is* the merge identity (e.g. a personal PAT), no GitHub-side gate
     can work; enforcement must move fully off-GitHub (the agent's environment
     holds no credential that can merge to the base branch).
   - **Division of labour.** jig's half provides a **deterministic comparison
     over supplied/attested inputs** — run-identity and the merge-capability of
     that identity — that returns `unsafe_for_autonomy` when they coincide *or*
     when the run identity is attested to hold merge/admin/bypass capability, and
     reports **not-ready when the capability signal is unavailable** (the safe
     direction — jig never asserts an unverified "ready"). The servo
     autonomy-readiness gate (servo ADR-0029) is what **derives the capability
     input from the GitHub API** (and the armed-branch-protection state) and feeds
     it in; jig does not claim to observe merge permissions in-process.
   - **The readiness check is advisory; the real teeth is credential absence
     (ADR-0011 posture).** Like every jig in-process check, the readiness gate
     sits inside the agent's trust boundary and is satisfiable by the agent it
     governs — so it is a *deliberateness/observability* signal, not enforcement.
     The property that actually holds the line is that the loop's environment
     **holds no credential that can merge to the base branch or edit protection**.
     The gate exists to make an unsafe configuration *visible and refused early*,
     never to be mistaken for the enforcement itself.

## Consequences

**Becomes easier:**
- A scaffolded repo ships with the scaffoldable half of its governance plane —
  the CODEOWNERS + protected-path CI files — plus an explicit checklist of the
  out-of-band branch-protection step that arms them, instead of only a prose
  recommendation buried in a hook comment.
- "Is this repo safe to run unattended?" becomes a concrete, checkable question
  (identity distinct **and** least-privilege **and** branch protection armed)
  instead of an assumption — checked by the servo readiness gate, not merely
  asserted by the presence of the scaffolded files.

**Becomes harder:**
- Operators must provision a second (bot/App) identity **and** arm branch
  protection to unlock autonomy — the right friction, but friction. jig should
  explain *why* rather than just refuse, and must not let the scaffolded files
  read as "already protected" before the arming step is done.
- Scaffolding now owns `.github/` templates that projects may need to adapt.

## Assumptions

- The target's host is GitHub (CODEOWNERS + branch protection semantics). _Other
  forges are out of scope for this record; a non-GitHub host would need its own
  mapping._
- **The scaffolded CODEOWNERS + CI files are inert until branch protection is
  armed.** jig scaffolds files; the arming (require-status-check,
  require-Code-Owner-review, forbid-bypass) is a server-side setting jig can only
  document and the readiness gate can only verify. jig never claims the files
  alone enforce anything.
- **Merge capability is a GitHub server-side authorization fact, not a local
  config value.** run-identity is locally observable (token / git identity); the
  merge-capability of that identity is not — there is no canonical local "who can
  merge this branch" to read. jig's check is deterministic *over its inputs*, and
  those inputs are **supplied/attested** (by the environment or the servo gate,
  which derives them from the GitHub API), not locally probed. _Probe before
  building: the exact signal is environment-specific and must be pinned in slice
  106-01 / servo 023-01, not assumed here. jig's half fails safe (reports
  not-ready) when the capability input is absent._

## Kill criteria

- If, in target environments, a second identity cannot be provisioned at all, the
  "two principals or refuse" stance blocks every real user — revisit toward a
  clearly-labelled degraded mode rather than a hard refusal.
- If CI protected-path enforcement proves trivially bypassable in practice (e.g.
  the agent can also edit the workflow), the plane is theatre again — the workflow
  file itself must be a protected path, and that self-reference must hold.
- **If the scaffolded files read as enforcement to operators who then skip the
  branch-protection arming step, the plane is theatre by omission** — a repo that
  looks protected but isn't is worse than an honest recommendation. The scaffolded
  material must state, at the point of scaffolding, that the files are inert until
  branch protection is armed, and the readiness gate must verify the armed state
  rather than infer it from file presence.
- **If the readiness gate passes on identity-name distinctness alone** (a distinct
  but over-privileged bot), it green-lights an unsafe repo on the exact decision
  this ADR exists to protect. The gate must key on merge *capability*, not merely
  a distinct name.

## Open questions

- Where the "independent owner" comes from in a solo-maintainer repo (the human
  is both author-of-record and owner) — resolve in spec 106; may reduce to "the
  human merges manually, agent holds no merge credential."
- Exact CODEOWNERS + workflow templates and their placement under `templates/`.
