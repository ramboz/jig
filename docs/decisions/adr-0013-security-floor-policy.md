---
dependencies: []
last_verified: 2026-06-01
---

# ADR-0013: Security-scaffold floor policy

## Status

Accepted (2026-06-01)

Drafted under [spec 052-01](../specs/052-security-scaffold/slice-01-security-floor-policy-adr.md);
moves to Accepted when that slice passes review.

## Context

jig's founding design principle is *"everything that MUST happen is a
hook"* — deterministic enforcement over human vigilance. Yet the 2026-06-01
re-review against `adobe/mysticat-ai-native-guidelines`
([spec 048](../specs/048-guidelines-gap-response/spec.md), Gap inventory C)
found that jig scaffolds **no security/secrets floor at all**: the template
CLAUDE.md has no rules block, `conventions.md` is authoring-only, no
`.gitignore` is scaffolded, the scaffolded `settings.json` has no permission
deny-rules, and no hook scans for secrets. The guidelines' single largest
MUST cluster (`must-rules.md`, `env-secrets.md`, `permissions.md`,
`mechanical-enforcement.md`) is therefore entirely unenforced in a
scaffolded jig project.

A first framing deferred all "depth" to Adobe's `adobe-security-*` skills.
That is wrong for jig's actual audience: a regular (non-Adobe) user does not
have those skills, so deferral-to-a-specific-vendor leaves them with
nothing. Design principle #5 is *"jig provides the floor; bring your own
depth"* — defer to **whatever is installed**, but always ship a floor.

Constraints: stay below the dumb zone (#2) — no heavy always-loaded content
or bundled scanners; three subagents only (#3) — no new subagent; honesty
(per [ADR-0011](./adr-0011-spec-gate-model.md)) — a hook living in the
agent's own trust boundary cannot be a firewall.

## Decision Options Considered

### Option A: Full deferral — document expectations, ship no floor
- **Pros:** zero footprint; no maintenance; no false positives.
- **Cons:** a user with nothing installed gets nothing; contradicts "jig
  provides the floor"; leaves the guidelines' biggest MUST cluster
  unenforced — the status quo this ADR exists to fix.

### Option B: Bundle scanners / ship a full SAST + secret-detection engine
- **Pros:** strongest detection out of the box.
- **Cons:** blows the dumb-zone budget; heavy maintenance; duplicates mature
  tools (semgrep / bandit) and Adobe's `adobe-security-*` depth; not jig's
  job — jig is a workflow scaffold, not a security product.

### Option C: Minimal mechanical floor + slim baseline skill that orchestrates-if-present, defers-if-richer
- **Pros:** every project gets a real floor (secret-ignore + agent-time
  secret-scan hook + permission deny-rules + lean MUST-rules block); the
  `security-review` baseline gives even a tooling-less user a heuristic
  pass, runs real scanners when present, and yields to any richer installed
  skill; mirrors the proven `contracts` / `pr-review` pattern; stays lean;
  honest.
- **Cons:** Tier 1 grows 7 → 8 skills (small dilution of the "fixed-size"
  identity); the secret-scan hook carries false-positive risk; heuristic
  categories need occasional maintenance.

### Sub-decision: secret-scan hook — block vs. warn
- **Block (with a deliberate override env var)**, mirroring the spec-gate /
  `JIG_CONVENTIONS_APPROVED` model of ADR-0011: stops an obvious secret from
  being written; overridable, so it is a *deliberateness gate*, not a hard
  sandbox.
- **Warn-only:** never blocks; lower friction but weaker — an accidental
  secret still lands on disk.

## Recommended Decision

Adopt **Option C**. jig scaffolds a security floor of five parts:
1. secret-ignore `.gitignore` patterns,
2. an agent-time secret-scan `PreToolUse` hook,
3. conservative `permissions.deny` defaults (force-push / hard-reset /
   `rm -rf`),
4. a lean `## Security (MUST)` block in the scaffolded CLAUDE.md, and
5. a slim Tier-1 `jig:security-review` baseline skill that orchestrates
   installed scanners (never bundles them) and defers, via a
   description-based hint, to any richer installed skill (the user's own,
   Adobe's `adobe-security-*`, or a built-in `security-review`).

For the secret-scan hook: **block on a high-confidence secret pattern,
overridable by a deliberate env var** (the ADR-0011 deliberateness-gate
model), emitting a structured "file + matched rule + how-to-override"
message.

**Honesty boundary:** the floor is agent-time prevention + defense-in-depth,
**not** a guarantee. Real enforcement of "no secret ever reaches history"
stays out-of-band: CI secret-scanning, server-side git hooks, branch
protection. Docs and the hook message must say so.

Depth jig explicitly does **not** ship: a bundled SAST engine,
dependency/CVE scanning, deep IaC/cloud rules, exhaustive per-language
dangerous-function rulesets — all deferred to richer installed skills.
Wiring `jig:security-review` into the post-implementation review flow (a
`security_review: true` pass parallel to `arch_review`) is **deferred until
signal**, per jig's growth rule.

## Consequences

**Becomes easier:**
- Every scaffolded/migrated project gets a real secret + destructive-command
  + review floor, with no Adobe-only dependency.
- jig finally applies its own "MUST → hook" principle to the guidelines'
  largest MUST cluster.
- A user who later installs a richer security skill is auto-routed to it,
  with no configuration.

**Becomes harder:**
- Tier 1 becomes 8 skills — `product-vision.md` / `README.md` /
  the vision-elicitation worked example and the `_TIER_SKILLS` constant must
  be updated together (the 038-03 `TierSkillSetTests` pin this), nudging the
  "fixed-size" identity.
- The secret-scan hook must balance precision vs. false positives; the
  override is the escape valve.
- jig now carries a small heuristic security-category set to maintain in the
  baseline skill.

**Neutral:**
- Real secret-leak enforcement still depends on out-of-band CI / git-hooks /
  branch-protection; jig raises the floor, it does not replace them.

## Scope

**In scope:**

- What the scaffolded jig security floor contains (the five parts above)
  and what it explicitly does **not** ship.
- The block-vs-warn posture of the secret-scan hook and its
  deliberate-override mechanism.
- The honesty boundary: agent-time prevention + defense-in-depth, not a
  guarantee.
- The `jig:security-review` baseline's orchestrate-if-present /
  defer-if-richer shape and its Tier-1 (default-on) placement.

**Out of scope (deferred or non-goal):**

- The concrete secret-pattern ruleset for the hook — curated set vs.
  library wrap ([refinement-todo](../refinement-todo.md)).
- The exact scanner roster + detection order the baseline shells out to
  ([refinement-todo](../refinement-todo.md)).
- Wiring `jig:security-review` into the post-implementation review flow as
  a `security_review: true` pass — deferred until signal
  ([refinement-todo](../refinement-todo.md)).
- Secret *remediation* (history rewriting, rotation) — spec 052 non-goal;
  the floor prevents introduction and ignores secret files.
- Deep IaC / cloud rules and exhaustive per-language dangerous-function
  rulesets — deferred to richer installed skills.
- `docs/conventions.md` content — unchanged; it stays authoring-only.

## Relationship to other decisions

- **[ADR-0011](adr-0011-spec-gate-model.md) (spec-gate model).** The
  honesty boundary and the deliberateness-gate-with-override model are
  borrowed directly: the secret-scan hook is the same shape as the
  spec-gate — an env-var-overridable gate inside the agent's own trust
  boundary, **not** a firewall. Real enforcement stays out-of-band.
- **[ADR-0012](adr-0012-scaffold-tier-gated-install.md) (tier-gated
  install).** Adding `jig:security-review` grows Tier 1 from 7 → 8 skills;
  ADR-0012's `_TIER_SKILLS` source-of-truth rule and the 038-03
  `TierSkillSetTests` doc↔code consistency pins both apply to slice
  052-05.
- **[ADR-0010](adr-0010-amendment-scope-records-vs-live-prose.md)
  (amendment scope).** Any edits this spec's slices make to closed
  specs/records follow ADR-0010's `## Amendments` convention; live
  operational prose is corrected inline.
- **Spec 048 (guidelines-gap-response), Gap inventory C (P1).** The origin
  of this floor — the largest unenforced MUST cluster in the
  guidelines re-review.
- **Spec 047 (install-contract verification).** Slice 052-04 coordinates
  the floor-presence check with 047's validator (or adds a minimal
  standalone check if 047 hasn't landed).
- **`contracts` / `pr-review` skills.** The orchestrate-if-present /
  defer-if-richer baseline pattern this ADR's `security-review` baseline
  mirrors.

## Open questions

The three implementation-level open questions are tracked in
[`docs/refinement-todo.md`](../refinement-todo.md), each with a resolution
trigger:

- **Secret-pattern ruleset source** for the hook — curated minimal set
  (shipped by 052-02) vs. wrapping `detect-secrets` / `gitleaks` when
  present.
- **Scanner set + detection order** the `jig:security-review` baseline
  shells out to (semgrep / bandit / gosec / `npm audit` / `osv-scanner`).
- **Whether/when to promote** the deferred `security_review: true`
  review-flow pass (needs signal).

None of these blocks the policy decision; all three are tunable after the
floor ships.
