---
dependencies: []
last_verified:
---

# ADR-0013: Security-scaffold floor policy

## Status

Proposed (2026-06-01)

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

## Open questions

- Source of the secret-pattern ruleset for the hook (a curated minimal set
  vs. wrapping a library like `detect-secrets` / `gitleaks` when present).
- Exact scanner set the baseline shells out to (semgrep / bandit / gosec /
  `npm audit` / `osv-scanner`) and detection order.
- Whether/when to promote the deferred `security_review: true`
  review-flow pass (needs signal).
