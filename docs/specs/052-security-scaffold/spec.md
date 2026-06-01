---
status: DRAFT
skill: scaffold-init, migrate
tier: scaffold machinery
adr_required: true
---

# Spec 052: Security-scaffold floor

## Overview

The 2026-06-01 re-review of jig against
[`adobe/mysticat-ai-native-guidelines`](https://github.com/adobe/mysticat-ai-native-guidelines)
(recorded in [spec 048](../048-guidelines-gap-response/spec.md)'s Gap
inventory C, P1) found that **jig scaffolds no security/secrets floor**.
The guidelines' single largest MUST cluster — `must-rules.md` (no
commit/hardcode/paste/log of secrets; use env vars/secret managers),
`env-secrets.md` (`.gitignore` secret patterns, `.env.example`),
`permissions.md` (conservative deny defaults), and
`mechanical-enforcement.md` (secret scanning as a hook) — has **zero**
mechanical enforcement in a scaffolded jig project. That is the sharpest
divergence in the comparison, because jig's founding design principle is
*"everything that MUST happen is a hook"* — yet the biggest MUST set is
unenforced.

This spec closes the gap by scaffolding a **minimal, deterministic
security floor** into every project — secret-ignore patterns, an
agent-time secret-scan hook, conservative permission deny-rules — **plus a
slim `security-review` baseline skill** so a user with *nothing else
installed* still gets a real (if heuristic) review pass. Depth is layered,
not vendored: the baseline **orchestrates real scanners (semgrep / bandit /
gosec / `npm audit` …) when they are on `PATH`** and **defers to any richer
installed security skill** — the user's own, Adobe's `adobe-security-*`, or
a built-in `security-review` — exactly the way `contracts` and `pr-review`
already work. jig never bundles heavy scanners, and deep IaC / exhaustive
per-language rulesets stay deferred. The point of principle #5 is "jig
provides the floor; bring your own depth" — *defer to whatever is
installed*, not to a specific vendor — so the floor must stand alone.

**Honesty boundary (mirrors [ADR-0011](../../decisions/adr-0011-spec-gate-model.md)
/ [spec 042](../042-spec-gate-model/spec.md)).** The scaffolded floor is
**agent-time prevention + defense-in-depth, not a firewall.** Real
enforcement of "no secrets ever reach history" is out-of-band: CI
secret-scanning, server-side git hooks, and branch protection. This spec
must not overclaim — the floor raises the cost of an accidental leak and
makes the rules legible to the agent; it does not guarantee their absence.

## Goals

1. **Scaffold a secret-prevention floor.** Every scaffolded (and migrated)
   project ships `.gitignore` secret patterns, an agent-time secret-scan
   hook, and a lean security MUST-rules block — with negligible
   always-loaded prompt burden.
2. **Scaffold conservative permission deny-rules.** `settings.json` denies
   force-push / hard-reset / `rm -rf` by default (guidelines
   `permissions.md`), merged via the same marker-based mechanism
   `scaffold-init` already uses for hooks.
3. **Provide a depth floor that stands alone, then defer.** Ship a slim
   `security-review` baseline skill so a user with no security skill
   installed still gets a heuristic pass; it orchestrates installed
   scanners and defers to any richer installed skill (the user's,
   `adobe-security-*`, or a built-in `security-review`). jig never bundles
   scanners; deep IaC / exhaustive per-language rulesets stay deferred.
4. **Stay honest about enforcement.** The hook docstring, block message,
   and docs state the floor is agent-time + defense-in-depth, not a
   guarantee, and name the out-of-band real-enforcement channel.
5. **Parity + verification.** `migrate copy-machinery` brings the floor
   into existing jig projects; install-contract verification (coordinating
   with [spec 047](../047-install-contract-verification/spec.md)) asserts
   the floor is present.

## Non-goals

- **No *bundled* scanners and no deep IaC / exhaustive per-language
  rulesets in jig.** The `security-review` baseline *orchestrates*
  installed scanners (semgrep / bandit / …) and *defers* to richer
  installed skills; it does not vendor a SAST engine or reimplement
  Adobe's `adobe-security-*` depth.
- **No claim of complete secret-leak prevention.** Out-of-band
  CI / git-hooks / branch-protection remain the real enforcement (honesty
  boundary above).
- **No new subagent** (design principle #3) and **no always-loaded
  mega-prompt** (design principle #2 — the rules block stays lean).
- **No secret *remediation*** (history rewriting, rotation). The floor
  prevents introduction and ignores secret files; remediation is
  documented, not automated.
- **No change to `docs/conventions.md`** without explicit human approval.

## Current state verified 2026-06-01

- The scaffolded [`templates/CLAUDE.md.template`](../../../templates/CLAUDE.md.template)
  has no rules / security block.
- [`docs/conventions.md`](../../conventions.md) is authoring-only (skill /
  hook / agent / document) — no security rules.
- No `.gitignore` is scaffolded (`templates/docs/` ships docs only).
- The scaffolded `settings.json` carries **hooks only**; `scaffold.py`
  merges the hooks block and the repo's own `settings.json` is `{"env":{}}`
  — no `permissions` deny block.
- None of the seven hooks in `hooks/hooks.json` is a secret-scan.
- `python3 scripts/spec_lint.py --all` is green across all specs at the
  time of this spec's authoring.

## Decomposition

**SPIDR axis: Rules.** Split by guardrail, highest-value / simplest first.
**No spike** — this is a design-and-build, not a research question; the
open decisions (floor scope — including the `security-review` baseline's
orchestrate/defer shape — and block-vs-warn for the secret-scan hook) are
an *ADR*, captured as the first slice per jig's `policy-adr` precedent
(specs 036-01, 038-01).

### Slices

1. **`052-01 security-floor-policy-adr`** — ADR deciding floor scope (what
   jig ships vs. defers to `adobe-security-*`), block-vs-warn for the
   secret-scan hook, and the honesty boundary. Gates the rest.
2. **`052-02 secret-prevention-floor`** — the core vertical slice:
   scaffold `.gitignore` secret patterns + a `jig-secret-scan.sh`
   PreToolUse hook + a lean security MUST-rules block. A fresh scaffold
   refuses to write an obvious secret and ignores `.env`.
3. **`052-03 destructive-command-guardrail`** — scaffold conservative
   `permissions.deny` defaults (force-push / hard-reset / `rm -rf`) into
   `settings.json` via marker-merge, with honest defense-in-depth framing.
4. **`052-04 migrate-parity-and-verify`** — `migrate copy-machinery`
   brings the floor into existing jig projects (ungated infra); install
   verification asserts the floor is present.
5. **`052-05 security-review-baseline`** — a slim Tier-1 `jig:security-review`
   skill: heuristic security pass + orchestrate-installed-scanners +
   defer-to-richer-installed, with honest best-effort framing. Gives a user
   with nothing installed a real review lens, and auto-routes to a richer
   skill when one is present.

## Dependencies / coordination

- `052-01` (policy ADR) gates `052-02` / `052-03` / `052-04`.
- `052-02` and `052-03` are independent guardrails — either order after
  `052-01`.
- `052-04` depends on `052-02` + `052-03`, coordinates with
  [spec 047](../047-install-contract-verification/spec.md) (install-contract
  verification, DRAFT — if it hasn't landed, this slice adds a minimal
  floor-presence check rather than blocking on it), and reuses
  [spec 038-04](../038-tier-reconciliation/spec.md)'s `copy-machinery` /
  `--add-tier` path. The floor is **infra → always copied, never
  tier-gated** (consistent with 038-02).
- `052-05` depends on `052-01` (the ADR fixes the baseline's
  orchestrate/defer shape + Tier placement) and is independent of 02/03/04.
  Adding `jig:security-review` makes **Tier 1 = 8 skills**: 052-05 must
  update `_TIER_SKILLS` (the `scaffold.py` constant) **and** the tier lists
  in `README.md` / `docs/product-vision.md` /
  `skills/vision-elicitation/worked-example-jig.md`, or the 038-03
  `TierSkillSetTests` doc↔code consistency tests fail. Wiring it into the
  post-implementation review flow (a `security_review: true` pass parallel
  to `arch_review`) is **deferred until signal** per jig's growth rule.
- **Deferral / composition targets (examples, not requirements):** any
  installed skill identifying as security-review / SAST / vulnerability
  analysis — the user's own, Adobe's `adobe-security-*`, or a built-in
  `security-review`. jig's `jig:security-review` baseline is the floor when
  none is present; nothing is vendored.
- If any slice needs to change `docs/conventions.md`, stop and ask for
  explicit human approval before implementation.

## References

- [spec 048 — Gap inventory C](../048-guidelines-gap-response/spec.md)
  (origin of this spec).
- [`adobe/mysticat-ai-native-guidelines`](https://github.com/adobe/mysticat-ai-native-guidelines)
  — `05-guardrails/must-rules.md`, `04-configuration/env-secrets.md`,
  `04-configuration/permissions.md`, `05-guardrails/mechanical-enforcement.md`.
- [ADR-0011: spec-gate model](../../decisions/adr-0011-spec-gate-model.md)
  / [spec 042](../042-spec-gate-model/spec.md) — honesty-boundary precedent
  for a gate that cannot be a firewall.
- [spec 038-04](../038-tier-reconciliation/spec.md) — tier-gated /
  `--add-tier` copy machinery (the floor is ungated infra).
- [spec 047](../047-install-contract-verification/spec.md) — install
  contract verification.
- [skills/contracts](../../../skills/contracts/SKILL.md) /
  [skills/pr-review](../../../skills/pr-review/SKILL.md) — the
  orchestrate-if-present / defer-if-richer baseline pattern that 052-05's
  `security-review` skill follows.
- [docs/product-vision.md](../../product-vision.md) — design principles #1
  (hooks deterministic), #2 (dumb zone / lean context), #5 (bring your own
  depth).
