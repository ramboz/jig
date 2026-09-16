# Worked example: clarify against a non-jig SaaS OAuth spec

> **Purpose.** Demonstrates the six-category taxonomy applied to a
> non-jig hypothetical: a small consumer-SaaS spec for "add OAuth
> login." Proves the taxonomy generalizes beyond jig vocabulary.
>
> The spec is deliberately ambiguous in places real specs often
> hand-wave: which OAuth provider, what happens on revocation,
> what's tested, what's the migration story for existing
> password-only users.

## Input excerpt: a SaaS spec draft

```markdown
---
status: DRAFT
title: Add OAuth login to YarnFinder
---

# OAuth login

## Overview

Users want to sign in with their Google account instead of creating
yet another password. Add OAuth login flow to the YarnFinder app.

## Why now

Multiple user requests, conversion drop-off on the sign-up page,
and a competitor just shipped it.

## Scope

- "Sign in with Google" button on the landing page
- OAuth callback handling on `/auth/callback`
- New user provisioning from Google profile data
- Existing-user matching by email

## Out of scope

- Account merging (someone with a password account who tries
  to OAuth in)
- Apple, Facebook, GitHub OAuth (later)

## Open questions

- What about logout flows?
- Do we need MFA on top?
```

That's all the PM wrote in the wiki. The dev assigned to implement
runs `/jig:clarify` against the spec before starting.

## Internal coverage scan (not shown to user)

| Category | Status | Notes |
|---|---|---|
| Scope & Boundaries | Partial | Sign-in flow named, but session lifecycle (cookie? JWT? expiry?) not declared; "existing-user matching by email" is ambiguous if email is unverified on the user's Google account. |
| Acceptance Criteria Testability | Missing | No ACs at all — "users can sign in with Google" is the implicit goal, but how do you test it (manual? automated? unit/e2e?). |
| Dependencies & Blockers | Missing | Google OAuth client ID/secret provisioning, OAuth consent screen approval (can take weeks for sensitive scopes), legal review of privacy implications — none mentioned. |
| Non-functional Requirements | Missing | Performance (callback latency budget), security (CSRF protection? state parameter? PKCE?), observability (auth failure logging), backwards-compat (existing sessions during rollout) all absent. |
| Edge Cases & Failure Modes | Partial | Account-merging called out as out of scope (good), but revocation, scope downgrade, deleted Google account, network failures during callback, all absent. |
| Terminology Consistency | Clear | "Sign in" and "sign up" used distinctly; OAuth used consistently; "user" means one thing. |

Five categories Partial/Missing. The model picks five questions —
budget hits the ceiling because the spec is genuinely thin.

## Q&A trace

### Q1: What's the session lifecycle after a successful OAuth callback — short-lived JWT, server-side session with a cookie, or something else? And what's the expiry?

**(category: Scope & Boundaries)**

**User answers:**

> Server-side session with an httpOnly secure cookie, 30-day rolling
> expiry (refreshes on activity). Matches our existing password-auth
> session model — OAuth callback creates the same session shape, just
> with a different identity provider field on the user row.

### Q2: List 3-5 acceptance criteria that demonstrate "OAuth login works." Each AC should be testable.

**(category: Acceptance Criteria Testability)**

**User answers:**

> 1. Clicking "Sign in with Google" redirects to Google's OAuth consent screen with the correct client_id and scopes.
> 2. After Google consent, callback at `/auth/callback?code=...&state=...` validates the state parameter and exchanges the code for an access token.
> 3. For an email that matches an existing user row, the session is created against that user (no duplicate row).
> 4. For a new email, a user row is provisioned with `auth_provider: "google"` and the Google profile name + avatar URL.
> 5. After successful login, the user is redirected to the URL they were trying to access pre-auth (or to /dashboard if none).

### Q3: What's blocking us from starting? OAuth consent screen for sensitive scopes takes 4-6 weeks for Google to approve; do we need that, and is it filed?

**(category: Dependencies & Blockers)**

**User answers:**

> We only need `openid email profile` scopes, which don't need sensitive-scope review. Client ID was provisioned last sprint and is in 1Password. Privacy review approved 2 weeks ago (no new PII categories — we already store email + name). No blockers.

### Q4: CSRF protection on the OAuth callback — are you using the state parameter and PKCE? Specify how `state` is generated, stored between request and callback, and validated.

**(category: Non-functional Requirements)**

**User answers:**

> State parameter: 32-byte URL-safe random token generated server-side, stored in a short-lived cookie (`oauth_state`, 10-minute expiry, httpOnly, secure, sameSite=lax). Validated on callback by comparing query string `state` to cookie value, then deleting the cookie. PKCE not used — server-side flow, the client secret never leaves the server. Code exchange happens server-to-server.

### Q5: What happens if a user revokes the OAuth grant in their Google account settings — does our session stay alive until natural expiry, or do we detect revocation and force a re-login?

**(category: Edge Cases & Failure Modes)**

**User answers:**

> Session stays alive until natural 30-day expiry. We don't poll Google for grant status. On next OAuth refresh (we don't currently refresh tokens — we only use the initial code exchange for identity), revocation would surface; but since we use the session cookie as the authority, the user effectively stays signed in to YarnFinder until session expiry. This is intentional — re-login on revocation would be a noticeable UX regression for the rare case it'd happen.

## Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Resolved |
| Non-functional Requirements | Resolved |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |

All six categories closed in five questions (one was already
Clear). The PM/dev can now update the spec body to incorporate
the answers — session cookie semantics in Scope, ACs spelled out
explicitly, dependencies acknowledged (none blocking), CSRF/state
NFRs noted, revocation behavior documented.

## Rendered `## Clarifications` section (appended to spec)

The skill writes the following to the wiki spec doc:

```markdown
## Clarifications

### Q1: What's the session lifecycle after a successful OAuth callback — short-lived JWT, server-side session with a cookie, or something else? And what's the expiry?
_(category: Scope & Boundaries)_

Server-side session with an httpOnly secure cookie, 30-day rolling
expiry (refreshes on activity). Matches our existing password-auth
session model — OAuth callback creates the same session shape, just
with a different identity provider field on the user row.

### Q2: List 3-5 acceptance criteria that demonstrate "OAuth login works." Each AC should be testable.
_(category: Acceptance Criteria Testability)_

1. Clicking "Sign in with Google" redirects to Google's OAuth consent screen with the correct client_id and scopes.
2. After Google consent, callback at `/auth/callback?code=...&state=...` validates the state parameter and exchanges the code for an access token.
3. For an email that matches an existing user row, the session is created against that user (no duplicate row).
4. For a new email, a user row is provisioned with `auth_provider: "google"` and the Google profile name + avatar URL.
5. After successful login, the user is redirected to the URL they were trying to access pre-auth (or to /dashboard if none).

### Q3: What's blocking us from starting? OAuth consent screen for sensitive scopes takes 4-6 weeks for Google to approve; do we need that, and is it filed?
_(category: Dependencies & Blockers)_

We only need `openid email profile` scopes, which don't need sensitive-scope review. Client ID was provisioned last sprint and is in 1Password. Privacy review approved 2 weeks ago (no new PII categories — we already store email + name). No blockers.

### Q4: CSRF protection on the OAuth callback — are you using the state parameter and PKCE? Specify how `state` is generated, stored between request and callback, and validated.
_(category: Non-functional Requirements)_

State parameter: 32-byte URL-safe random token generated server-side, stored in a short-lived cookie (`oauth_state`, 10-minute expiry, httpOnly, secure, sameSite=lax). Validated on callback by comparing query string `state` to cookie value, then deleting the cookie. PKCE not used — server-side flow, the client secret never leaves the server. Code exchange happens server-to-server.

### Q5: What happens if a user revokes the OAuth grant in their Google account settings — does our session stay alive until natural expiry, or do we detect revocation and force a re-login?
_(category: Edge Cases & Failure Modes)_

Session stays alive until natural 30-day expiry. We don't poll Google for grant status. On next OAuth refresh (we don't currently refresh tokens — we only use the initial code exchange for identity), revocation would surface; but since we use the session cookie as the authority, the user effectively stays signed in to YarnFinder until session expiry. This is intentional — re-login on revocation would be a noticeable UX regression for the rare case it'd happen.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Resolved |
| Non-functional Requirements | Resolved |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |
```

## What this run produced

The dev now has:

- A session lifecycle to implement against (cookie shape +
  expiry, defined; matches existing password-auth path)
- Five named ACs that map 1:1 to test cases
- No blockers — they can start today
- A documented CSRF/state-parameter pattern to copy from
  similar OAuth integrations
- An intentional behavior decision (revocation doesn't force
  re-login) that an ADR or a comment in the auth module should
  record

The spec author can update the wiki spec with the locked-down
session shape + ACs, and the dev can start branching off without
the usual "wait, let me ping the PM first" overhead.

## Why the taxonomy generalizes

This run uses none of jig's internal vocabulary (no slices, no
ADRs, no Tier 0/1/2, no `${CLAUDE_PLUGIN_ROOT}`). The six
categories work because they're aligned with universal spec
authoring concerns:

- **Scope & Boundaries** — every spec defines what's in and out.
- **Acceptance Criteria Testability** — every spec needs to be
  verifiable, otherwise "done" is a guess.
- **Dependencies & Blockers** — every spec depends on something
  upstream (a service, a fixture, an approval).
- **Non-functional Requirements** — every shipped feature has
  perf/security/observability/compat surface.
- **Edge Cases & Failure Modes** — every system fails sometime;
  the spec should say how.
- **Terminology Consistency** — every spec collapses if two
  words mean three things.

The categories travel.
