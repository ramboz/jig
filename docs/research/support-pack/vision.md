# Vision: counter (working name)

> Status: **Parked seed** — brainstorm artifact from a 2026-07-20 session, set
> aside for later exploration. This is NOT a jig spec and NOT committed work.
> It describes a *separate future sibling project*, not a jig feature. The
> tracking entry (with birth trigger) lives in [docs/inbox.md](../../inbox.md).
>
> Working name candidates: **counter** (the front-of-shop counter where
> customers bring things), *vise*, *bench* — staying in the jig/servo
> workshop-tool family. Nothing is settled.

## Vision statement

A small, opinionated **customer-support scaffold** for solo devs and tiny
teams running multiple products: it installs the intake → triage → answer →
feedback-loop machinery into each product repo on day 1, keeps support
knowledge (FAQ, troubleshooting, recurring themes) as durable in-repo docs an
AI agent can read and maintain, and routes what support learns back into the
dev workflow.

It is a **sibling to jig, not part of it** — the same relationship servo has:

| Tool | Owns |
|---|---|
| **jig** | the build lifecycle (specs, slices, review evidence, bug-fix) |
| **servo** | evaluation (EDD engine) |
| **counter** | intake + the support→dev feedback loop |

Three tools around one `docs/` corpus, integrating through thin explicit
contracts, each installable without the others.

## Target user

- **A solo dev shipping several small products** (the seed case: a
  closed-beta web game + a ~$5 one-time-purchase local-first Android app +
  future apps) who is also the entire support department.
- Support economics that rule out per-resolution SaaS pricing
  ($0.99/AI-resolution doesn't fit a $5 app) and privacy positioning that
  rules out third-party chat widgets with tracking.
- Existing automation infra to reuse (VPS + scheduled headless Claude Code
  runs) rather than new SaaS to buy.

**Not for:** teams with a real support org, a paid helpdesk they're happy
with, or ticket volume that justifies dedicated tooling from day 1
(self-hosted Chatwoot etc. — counter should *hand off to* that tier, not
compete with it).

## The core problem

1. **Support conventions get reinvented per project.** FAQ structure,
   troubleshooting docs, triage rules, response-tone conventions — hand-copied
   between repos, drifting immediately. (Same pain jig solves for dev
   workflow.)
2. **AI support quality is capped by documentation quality**, and most
   tickets are ~8 problems asked 5 different ways — but nothing maintains the
   docs from the ticket stream, so the docs rot while the same questions
   recur.
3. **Support signal evaporates.** Recurring themes, feature asks, and defect
   reports live in a mailbox/Discord and never land in the backlog or bug
   board with any lifecycle. Meanwhile jig's own growth rule *demands* user
   signal before new work enters a project — support is the cheapest source
   of that signal, and it's currently uncaptured.
4. **A shared automation consumer needs uniform repos.** A scheduled
   draft-reply agent (cron reads mailbox → drafts from FAQ → human approves)
   needs every product repo to keep its support docs in a known place and
   shape. A scaffold is how that uniformity is guaranteed.

## Positioning vs. alternatives

(Condensed from the 2026-07 SUPPORT-PLAN evaluation.)

| Option | Why counter instead / how it relates |
|---|---|
| Intercom/Fin-class AI helpdesk | Per-resolution pricing is a margin-killer at small price points; overkill at near-zero volume |
| Flat-price SaaS (Crisp) | Predictable but AI-limited on low tiers; still per-seat SaaS for ~0 tickets/day |
| Self-hosted Chatwoot | The *scale tier* (~10+ tickets/day) — counter hands off to it, ideally keeping the same triage/draft skills as an adapter |
| Docs-bot SaaS | Monthly fee × projects at near-zero volume; counter's FAQ docs could later *feed* one |
| Hand-rolled DIY per repo | Works once; non-portable, no conventions, no feedback loop — the gap counter fills |

## Core features (tiered, jig-style)

### Tier 0 — the floor

1. **`support-init`** — scaffolds `docs/support/` in a product repo: `faq.md`
   + `troubleshooting.md` (bilingual-first templates, FR/EN in the seed
   case), and a one-page `triage.md` stating the routing rule.
2. **`triage`** — judgment skill: classify an inbound message → defect /
   recurring question / idea / pre-sales, and route it (see architecture:
   the jig seam).
3. **`theme-sync`** — the memory-sync analog: cluster recurring questions,
   update the FAQ from the ticket stream, and emit signals to the dev
   workflow (jig inbox / bug board when present, `BACKLOG.md` otherwise).

### Tier 1 — the automation layer

4. **`draft-reply`** — reads a ticket + the repo's support docs → drafts a
   response → **human approval gate** (never auto-send) → durable log of what
   was answered. Designed to run headless (scheduled Claude Code) as well as
   interactively.

### Later / opt-in by signal

- Channel adapters (Discord intake for beta communities; Chatwoot at scale).
- Scale-trigger metrics (tickets/day per project → nudge the Chatwoot
  transition).

## Out of scope (deliberately)

- **No chat widget, no hosted service, no inbox UI.** counter is
  conventions + skills + templates in the product repo, plus a headless
  agent workflow. The mailbox/Discord/Chatwoot stays the system of record
  for conversations.
- **No auto-send.** The human approval gate is load-bearing (solo dev's
  voice + accountability), not a v0 limitation.
- **No dev-lifecycle features.** Anything past "this is a defect" belongs to
  jig's bug-fix workflow (or the project's own process). counter routes; it
  does not diagnose or fix.

## Design principles

1. **Docs first, tooling second.** Support quality is capped by doc quality;
   every feature must either improve the docs or use them.
2. **The repo is the knowledge base.** FAQ/troubleshooting live in the
   product repo where agents, crons, and humans can all read and version
   them — not in a SaaS silo.
3. **Sibling, not extension.** Integrates with jig through thin explicit
   contracts (writer owns the contract, servo-style) and **degrades
   gracefully without jig** — defects route to `BACKLOG.md` when no bug
   board exists. counter must be useful to non-jig projects.
4. **Human gate on everything outbound.** Drafts, never sends.
5. **Privacy-consistent.** No third-party tracking, BYO API key, fits a
   local-first / no-cloud product posture.
6. **Grow by signal.** Same rule as jig: features enter when a real pain
   recurs, not speculatively. (This document itself obeys the rule — see
   birth trigger below.)

## Birth trigger & sequencing (the honest part)

Current ticket volume across the seed projects is ~zero. Building this now
would be tooling-before-tickets, violating principle 1. The agreed sequence:

1. **Now (costs nothing):** hand-write FAQ + troubleshooting docs in each
   product repo per the SUPPORT-PLAN Phase 0, using the shapes this document
   describes. That work *is* the future templates.
2. **Birth trigger:** the SUPPORT-PLAN **Phase-2 draft-reply cron gets
   built** (first real code consumer), OR a **third project** adopts the
   hand-copied conventions (rule of three). At that point: create the repo,
   extract the templates from two projects' real practice, build
   `draft-reply` there from day one, and dogfood the build with jig itself.
3. **Until then:** this stays a parked seed. Revisit at each SUPPORT-PLAN
   phase transition or quarterly.

## References

- [architecture.md](architecture.md) — sibling seed doc: components, the jig
  seam, runtime contexts, open questions.
- [docs/inbox.md](../../inbox.md) — the tracking entry + promotion trigger.
- jig precedents: servo sibling contract (jig spec 072-02 / servo ADR-0013
  `available.json`), per-skill deferral pattern (product-vision § design
  principle 5), grow-by-signal rule (product-vision § How new work enters
  jig).
- Source discussion: 2026-07-20 brainstorm against the owner's
  SUPPORT-PLAN.md (customer-support strategy across projects, July 2026 —
  private doc, not in this repo).
