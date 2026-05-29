---
dependencies: []
last_verified: 2026-05-29
---

# ADR-0010: Scaffold-init tiers gate which skills install

## Status

Accepted (2026-05-29)

## Context

jig's positioning rests on "tier-gated installs": the README and
product-vision docs present Tier 0 as a small, opinionated floor and
Tier 1 as an opt-in default. The `scaffold.json` manifest reflects
that claim — its `installed_skills` list is derived from
`installed_tiers` per [ADR-0007](adr-0007-scaffold-json-installed-skills.md).
**The on-disk copy ignores it.**

Verified at HEAD `b7117c5` (2026-05-29), confirming spec 038's
2026-05-26 audit still holds:

- `scaffold.py:_select_tiers` picks `installed_tiers = ["tier-0"]` by
  default and adds `"tier-1"` only when `signals.has_tests`.
- `scaffold.py:_copy_skills_and_agents` iterates every skill directory
  that contains a `SKILL.md` and copies it — **with no filter on
  `installed_tiers`**. All 14 skills land on disk regardless of the
  flags or the wizard's answers.

Both invocations (with and without `--has-tests`) therefore produce
**byte-identical skill sets**. Three consequences follow:

1. **The manifest is fiction at the boundary it matters most.**
   `scaffold.json` says 7 skills (Tier 0); the `.claude/skills/`
   directory has 14. ADR-0007's derivation invariant holds on the
   manifest side and is silently violated on the disk side.
2. **The wizard's "Existing tests?" question (slice 001-05) is a
   no-op for on-disk outcomes.** The user is asked to influence an
   install they cannot influence; the answer only changes manifest
   text and a diagnostic line.
3. **Three secondary doc-vs-code inconsistencies have been latent for
   months** because no test asserts manifest ↔ on-disk consistency:
   `vision-elicitation` is in `_TIER_SKILLS["tier-0"]` but absent from
   the vision doc's numbered Tier 0 list; `contracts` is in
   `_TIER_SKILLS["tier-0"]` but the vision doc places it at item #11
   (Tier 1); the README still says "5 Tier 0 skills" / "8-12 total"
   when reality is 7 / 14. (This is drift #5, deferred to spec 038 by
   [ADR-0008](adr-0008-closed-spec-drift-policy.md) to avoid a
   double-edit.)

This is a **positioning decision**, not a bug-fix: it determines what
"tier" *means* in jig. Spec 038 is `adr_required: true` and ADR-first
for exactly this reason.

### What the numbers say about the dumb-zone rationale

The "small Tier 0 floor" pitch is usually justified by the
dumb-zone principle (>40% context fill degrades recall). Measured at
HEAD:

| | Always-in-context (SKILL.md descriptions) | Bodies (load only on invocation) |
|---|---|---|
| Tier 0 (7) | ~1,456 tokens | ~98 KB |
| Tier 1 (+7) | +1,218 tokens | +93 KB |
| **All 14** | **~2,674 tokens** | ~197 KB |

Skill **bodies** are not a persistent context cost — they load only
when a skill is invoked. The always-on cost of all 14 skills is the
~2,674 tokens of frontmatter descriptions used for routing. Gating
Tier 1 saves ~1,218 tokens — roughly **0.6%** of a 200K window, far
below the ~80K dumb-zone threshold.

**Therefore the dumb-zone argument does not, by itself, justify
gating.** This ADR is decided on three other grounds — promise
integrity, wizard correctness, and routing-surface discipline — not
on token budget. Naming this explicitly prevents a future reader from
citing a token-budget rationale the evidence doesn't support.

## Decision Options Considered

### Option A: Tiering is informational (always copy all 14)

Accept the current copy behavior as correct-by-design. `installed_tiers`
records a *workflow opt-in* (which tiers the project intends to lean on)
rather than a copy gate. Reword the README + vision docs ("14 skills
ship; tiers are conceptual groupings"). Drop or repurpose the wizard's
test-presence question. Add a regression test asserting manifest ↔
on-disk consistency under the all-14 reality.

- **Pros:** Cheapest implementation — deletes the gap rather than
  closing it. No upgrade/uninstall story. All skills immediately
  discoverable. The ~2,674-token cost is genuinely negligible, so the
  install is honest.
- **Cons:** Abandons the "small opinionated floor" promise that is
  part of jig's stated identity. The wizard question is removed rather
  than made meaningful. Routing surface stays at 14 descriptions for
  every project regardless of need — more chances for spurious
  auto-trigger / mis-route, a cost the token table doesn't capture.

### Option B: Tiering is real (gated copy), with a first-class upgrade path

`_copy_skills_and_agents` filters by `installed_tiers`; only the
skills whose tier is installed land on disk. The wizard's `--has-tests`
answer actually gates Tier 1. The README/vision "small floor" claim
becomes literally true. A regression test pins manifest ↔ on-disk
consistency under gating. **And** post-scaffold tier upgrade is a
supported, designed capability: a project that scaffolded Tier 0 can
later add Tier 1 (when tests/workflow appear) without re-scaffolding
from scratch or hand-copying skill directories.

- **Pros:** Honors the floor promise; converts the wizard from a no-op
  into a real control (fixes a latent correctness bug); shrinks the
  default routing surface to the 7 Tier-0 descriptions; the upgrade
  path removes gating's main downside (being stuck at Tier 0 as a
  project grows).
- **Cons:** More implementation than Option A — filter logic, wizard
  wiring, and an upgrade mechanism that must reconcile with the
  existing `AlreadyScaffoldedError` re-run guard. Introduces an
  upgrade UX surface that needs its own design.

### Option C: Real tiers, scaffold-time only (no upgrade path)

Option B's gating, but tier membership is frozen at scaffold time —
upgrading means re-scaffolding or manual copy.

- **Pros:** Slightly less work than B; same promise integrity at
  install time.
- **Cons:** A Tier-0 project that grows tests is stranded: the wizard
  gate becomes a one-way door. This is the failure mode the
  decision-maker explicitly called out ("make sure we can update this
  later to higher tiers as the project evolves"). Rejected on that
  basis.

## Recommended Decision

**Option B — tiers gate the install, and tier upgrade is a first-class
capability.**

Reasoning:

1. **Promise integrity over the cheapest patch.** Option A is cheaper
   but resolves the inconsistency by abandoning a stated identity
   ("small opinionated floor"). The decision-maker chose to keep the
   promise and make the install match it.
2. **The wizard no-op is a correctness bug, and B fixes it.** Slice
   001-05 ships a question whose answer changes nothing on disk. B
   makes the answer load-bearing; A deletes the question. Fixing beats
   deleting when the question encodes a real intent (how much workflow
   machinery this project wants).
3. **Routing-surface discipline is the real win, not token budget.**
   The token table shows the dumb-zone rationale is weak (~0.6%). The
   defensible benefit is a smaller default *routing* surface: 7
   descriptions instead of 14 means fewer mis-route opportunities for
   projects that only want the floor. This is a behavior-quality
   argument, not a context-budget one.
4. **Upgradeability neutralizes the only serious objection to gating.**
   Gating without an upgrade path strands growing projects (Option C).
   Making upgrade first-class means Tier 0 is a starting point, not a
   ceiling — the gate is a default, not a one-way door.

The **upgrade mechanism already largely exists**: `migrate.py
copy-machinery` (spec 021) copies skills/agents/hooks into an
already-set-up project, reusing scaffold's helpers, and deliberately
bypasses the fresh-scaffold `AlreadyScaffoldedError` guard. Once
`_copy_skills_and_agents` is tier-aware (this spec) and `copy_machinery`
reads `installed_tiers` from the target's existing `scaffold.json`, a
tier upgrade is just: bump the manifest's `installed_tiers` and re-run
`copy-machinery`, which additively installs the newly-included tier's
skills. The remaining UX choice (a `--tiers`/`--add-tier` flag on
`copy-machinery` vs. a documented manifest edit, and whether this
finally promotes the deferred `update` skill, slice 016-04) is an
implementation detail, not decision content, deferred to spec 038's
slices. What this ADR commits to is that **the design must not
foreclose post-scaffold tier upgrade**, and that upgrade must be
*additive* (it adds the newly-installed tier's skills; it does not
remove or clobber what the project already has) — which the existing
`copy-machinery` path already satisfies.

**Source-of-truth rule for the secondary inconsistencies:** the code's
`_TIER_SKILLS` table is authoritative; the vision/README docs are
reconciled *to it*, not the reverse. This keeps the doc edits
mechanical and avoids relitigating tier membership (which spec 038
lists as a non-goal). `vision-elicitation` and `contracts` keep their
current `_TIER_SKILLS` assignment; the docs are corrected to match.

## Consequences

**Becomes easier:**

- The README/vision "Tier 0 floor" claim becomes verifiable and true;
  the install honors what the positioning promises.
- The wizard's test-presence answer has an observable effect, closing
  a latent no-op.
- A manifest ↔ on-disk regression test can finally exist (today both
  sides are verified independently and the gap slips between them).
- Growing projects have a sanctioned path to more machinery without
  re-scaffolding — Tier 0 is a low-commitment entry point.

**Becomes harder:**

- `_copy_skills_and_agents` gains tier-awareness; the shared `_<name>`
  modules and `agents/` copy must still come through regardless of
  tier (they are infrastructure, not tier-gated skills). The filter
  must not accidentally drop them.
- **Both** callers of `_copy_skills_and_agents` must pass
  `installed_tiers`: the greenfield `scaffold()` path (which has it
  from `_select_tiers`) and the `copy_machinery()` façade used by
  `migrate.py copy-machinery` (which today passes nothing and must
  learn to read `installed_tiers` from the target's existing
  `scaffold.json`). Missing the second caller would leave the migrate
  path tier-blind — the same gap, relocated.
- The upgrade entry point does **not** need to be built from scratch:
  `copy-machinery` already bypasses the `AlreadyScaffoldedError` guard
  and copies additively. The remaining work is making it tier-aware
  and adding a tier-bump affordance — not inventing a new re-run path
  with its own refusal rules.
- Existing projects that scaffolded under the old all-14 behavior now
  have "extra" Tier-1 skills relative to a fresh gated install. Per
  spec 038's non-goals there is **no automatic uninstall**: they keep
  what they have, or remove skills manually. The gated behavior
  applies to fresh scaffolds and to additive upgrades going forward.

**Implementation status:**

- This ADR records the policy only. The gated-copy implementation,
  wizard wiring, regression test, doc reconciliation, and upgrade-path
  slice are spec 038 work (slices 038-02 … 038-04).
- No tooling falls out of this ADR directly.

## Scope

**In scope:**

- The meaning of `installed_tiers` for the scaffold-init **copy**
  step (gate vs. metadata).
- The commitment that post-scaffold tier upgrade must remain possible
  and be additive.
- The source-of-truth rule for reconciling the `_TIER_SKILLS` table
  against the vision/README docs.

**Out of scope:**

- Which skills belong in which tier (spec 038 non-goal — no tier
  reassignment; current `_TIER_SKILLS` membership stands).
- Per-skill opt-out (tier-level granularity only).
- Introducing a Tier 2 (the vision's "Tier 2 stays empty until pain is
  reported" rule is upheld).
- The concrete upgrade UX (a tier-bump flag on `copy-machinery` vs. a
  documented manifest edit vs. promoting the `update` skill) — an
  implementation choice for spec 038's slices.
- Migration tooling to retroactively trim over-installed legacy
  scaffolds.

## Relationship to other decisions

- **[ADR-0007](adr-0007-scaffold-json-installed-skills.md)
  (scaffold.json installed_skills derivation).** This ADR makes the
  on-disk reality finally obey the same `installed_tiers` derivation
  that ADR-0007 defined for the manifest. The two become consistent;
  the regression test pins that consistency.
- **[ADR-0002](adr-0002-contracts-stays-deferred.md) /
  [ADR-0005](adr-0005-contracts-as-judgment-skill.md) (contracts
  skill).** `contracts` is a deliberate stub that is still copied;
  this ADR's source-of-truth rule resolves the vision-doc placement
  inconsistency without changing the contracts decision.
- **[ADR-0008](adr-0008-closed-spec-drift-policy.md) (closed-spec
  drift policy).** ADR-0008 explicitly defers drift #5 (the README
  "5 Tier 0 / 8-12 total" line) to spec 038. Any edits this work makes
  to closed specs or load-bearing prose follow ADR-0008's
  `## Amendments` convention.
- **Spec 021 (migrate `copy-machinery`).** The existing additive
  machinery-copy path into an already-set-up project. It bypasses the
  fresh-scaffold guard and is the leading vehicle for the committed
  upgrade capability — it shares the same `_copy_skills_and_agents`
  helper this spec makes tier-aware, so it inherits gating and needs
  only an `installed_tiers` source + a tier-bump affordance.
- **Spec 016-04 (deferred `update` skill).** The committed upgrade
  path may be satisfied by extending `copy-machinery` (spec 021), or
  by finally promoting 016-04. This ADR requires the *capability*;
  spec 038 chooses the *vehicle*, with `copy-machinery` the default
  candidate.
- **Spec 040 (isolation honesty).** Both edit the README. Land in
  series, not parallel, to avoid adjacent-line conflicts. (040 is
  DONE as of 2026-05-29, so the README is free for 038's edits.)

## Open questions

None at the policy level. The decision (real, gated, upgradeable
tiers) and the source-of-truth rule are fixed. The one deferred item —
the upgrade vehicle (extend `migrate.py copy-machinery`, the leading
candidate, vs. promote the `update` skill, 016-04) — is an
implementation choice, not decision content; spec 038's slices resolve
it, and it does not reopen this ADR.
