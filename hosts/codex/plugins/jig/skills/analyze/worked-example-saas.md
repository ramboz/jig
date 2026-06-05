# Worked example: analyze against a non-jig SaaS OAuth spec

> **Purpose.** Demonstrates the six-category taxonomy applied to a
> non-jig hypothetical: a small consumer-SaaS spec for "add OAuth
> login." Proves the taxonomy generalizes beyond jig vocabulary.
>
> The spec is deliberately drifty: it references an ADR that doesn't
> exist, has two ACs that overlap, and uses "user" + "account
> holder" interchangeably. Analyze catches every variant.

## Input excerpt: a SaaS OAuth-login spec

The team's product spec wiki contains the following spec, which the
dev runs `/jig:analyze` against before starting implementation:

```markdown
---
status: READY_FOR_IMPLEMENTATION
title: OAuth login for YarnFinder
---

# OAuth login

## Overview

Users want to sign in with Google instead of creating yet another
password. Per ADR-0014, we're shipping Google OAuth as the first
provider, with Apple/GitHub deferred. The new account holder
provisioning flow extracts profile data from Google.

## Acceptance criteria

1. Clicking "Sign in with Google" redirects the user to Google's
   OAuth consent screen.
2. Clicking "Sign in with Google" takes the user to Google's
   authorization page.
3. After Google consent, the callback at `/auth/callback?code=...&state=...`
   validates the state parameter and exchanges the code.
4. For an email that matches an existing user, the session is
   created against that account holder (no duplicate row).
5. For a new email, a user is provisioned and the session is
   created.
6. The implementation should be fast.
7. The OAuth flow MUST be secure.
8. Logout works correctly.

## Out of scope

- Apple, GitHub, Facebook OAuth (later)
- Account merging (password account → OAuth on same email)
```

The dev runs analyze. It walks:

- The spec body above.
- `decisions/` directory (looking for `ADR-0014`).
- The team's `glossary.md` (which defines "user" but not "account
  holder").
- The architecture doc (which has no `## Contract surfaces` section
  for the OAuth callback API).

## Findings (sorted by severity)

| # | Severity | Category | Location | Finding |
|---|---|---|---|---|
| 1 | CRITICAL | Terminology Drift | spec.md:Overview | Reference to `ADR-0014` does not resolve — the team's `decisions/` directory has no `adr-0014-*.md` file. The Overview asserts a decision rationale that doesn't exist. Block on this before implementation: either the ADR needs to be written (it's a load-bearing decision) or the reference needs to be removed. |
| 2 | HIGH | Duplication | spec.md:AC#1 vs AC#2 | ACs #1 and #2 say the same thing in slightly different words ("redirects to Google's OAuth consent screen" vs "takes the user to Google's authorization page"). Either consolidate into one AC or split clearly (e.g., "AC #1: button click redirects" + "AC #2: redirect URL has correct OAuth params"). |
| 3 | HIGH | Terminology Drift | spec.md:AC#4, AC#5, Overview | Inconsistent use of "user" vs "account holder" vs (implied) "session". The glossary defines "user" as the canonical term; the spec uses "account holder" interchangeably in AC #4 and the Overview. Lock one term and replace the other. |
| 4 | HIGH | Underspecification | spec.md:AC#6 | "The implementation should be fast" — no measurable threshold (latency budget? p95 callback time? perceived load time?). AC has no measurable outcome verb. Either name a number (e.g., "callback returns within 500ms p95") or remove the AC. |
| 5 | HIGH | Underspecification | spec.md:AC#7 | "The OAuth flow MUST be secure" — no measurable security criteria (state parameter? PKCE? token storage location? cookie flags?). Decompose into specific testable security ACs, or reference an external security spec. |
| 6 | MEDIUM | Coverage Gaps | spec.md:AC#3 | AC #3 mentions a public callback URL `/auth/callback` (an external HTTP contract surface — Google's OAuth flow POSTs the redirect back), but the spec doesn't reference a contract artifact (OpenAPI? a documented expected payload shape?). Recommend running the team's contract-spec workflow on this surface. |
| 7 | MEDIUM | Ambiguity | spec.md:AC#8 | "Logout works correctly" — what is "correctly"? Session is destroyed? Cookies are cleared? Browser is redirected to landing page? OAuth grant is also revoked at Google? Each interpretation is testable; the AC names none. |
| 8 | LOW | Coverage Gaps | spec.md:AC#5 | AC #5 references "a user is provisioned" but the spec doesn't define what fields the user row gets (`auth_provider`? `provider_user_id`? `display_name`? `avatar_url`?). Mostly a schema-design gap but the AC ships without naming the contract. |

## Coverage summary

| Category | Findings |
|---|---|
| Duplication | 1 |
| Ambiguity | 1 |
| Underspecification | 2 |
| Principle Violations | 0 |
| Coverage Gaps | 2 |
| Terminology Drift | 2 |

Five of six categories light up. **Principle Violations** is 0
because this hypothetical project doesn't have jig's seven
principles — the team has its own engineering norms, which analyze
doesn't have visibility into. (If the team wanted similar
governance, they'd point analyze at their `docs/principles.md`
file via a per-team configuration — not in the MVP.)

## Next steps

- Address Finding #1 (CRITICAL) before any implementation work: the
  ADR-0014 reference is load-bearing and the ADR doesn't exist.
  Either write the ADR (capturing the "Google first, others
  deferred" decision durably) or remove the reference from the
  Overview.
- HIGH findings (#2, #3, #4, #5) should be resolved before merge.
  Finding #3 (terminology drift) is the cheapest to fix — global
  search-and-replace. Finding #4 and #5 need real product decisions
  (latency budget, security baseline) that the PM/dev pair owe the
  team before implementation lands.
- MEDIUM findings (#6, #7) and LOW (#8) can ship if tracked in the
  team's followups doc. Finding #6 specifically is worth surfacing
  to the platform team — if other teams add OAuth flows later, a
  contract-artifact baseline now saves rework.

## What this run produced

The dev now has:

- An ADR to write (or a reference to delete) — Finding #1.
- Two ACs to consolidate or clearly split — Finding #2.
- A vocabulary fix to apply globally — Finding #3.
- Two measurable thresholds to negotiate with the PM (latency budget,
  security checklist) — Findings #4 + #5.
- Three testable behaviors to add to AC #8 — Finding #7.
- A schema decision to document — Finding #8.

The dev opens the spec, fixes the cheap wins (Findings #3 + #2 +
#8), routes the ADR to the architect for Finding #1, and books a
15-minute sync with the PM to negotiate Findings #4 + #5. That's
analyze's signal-to-noise on a real spec.

## Why the taxonomy generalizes

This run uses none of jig's internal vocabulary (no slices, no
Tier 0/1/2, no `${CLAUDE_PLUGIN_ROOT}`, no SPIDR axes). The six
categories work because they're aligned with universal cross-artifact
authoring concerns:

- **Duplication** — every spec eventually grows redundancy as authors
  re-explain.
- **Ambiguity** — every spec includes some "should be fast" placeholder
  the author intended to nail down.
- **Underspecification** — every spec ships some AC without a
  testable threshold.
- **Principle Violations** — every team has principles (jig or
  otherwise); the category exists in the taxonomy whether the
  source is jig's product-vision.md or some other team's
  engineering-norms doc.
- **Coverage Gaps** — every spec eventually mentions a surface
  (API endpoint, schema, config flag) without naming the
  verification artifact.
- **Terminology Drift** — every spec collapses if two words mean
  three things, or one concept appears under three names.

The categories travel.

## What the skill did NOT do

- **Did not modify the spec.** Even Finding #1 (CRITICAL) didn't
  trigger an edit. The skill's job is to surface; resolution is the
  spec author's.
- **Did not file the missing ADR.** Finding #1 points at an
  ADR-shaped gap, but writing ADRs is `/jig:adr-workflow new`'s
  job, not analyze's.
- **Did not contact the PM.** Finding #4 / #5 need a product
  conversation; analyze surfaces the gap but doesn't negotiate.
- **Did not run security tests.** Finding #5 says "MUST be secure"
  is unmeasurable; that's an underspecification finding, not a
  security audit. A real security audit is its own skill.
