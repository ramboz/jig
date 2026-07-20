# Architecture seed: counter (working name)

> Status: **Parked seed** — minimal companion to [vision.md](vision.md),
> 2026-07-20. Deliberately thin: just enough structure to resume the
> exploration later without re-deriving it. Nothing here is built.

## Shape

Same packaging philosophy as jig: a **skill pack scaffolded into the product
repo** (owned, readable, extensible by the dev), not a plugin runtime or a
hosted service. The pack itself, when born, gets built in its own repo using
jig's spec lifecycle (dogfooding, like servo).

Two runtime contexts, same skills:

- **Interactive** — dev runs `triage` / `theme-sync` in a normal session.
- **Headless** — a scheduled Claude Code run (existing VPS hourly-slice
  infra) drives `draft-reply` over the support mailbox. Headless mode only
  ever produces *drafts* and log entries; the human gate is between draft
  and send, always.

## Data layout in a consumer repo

```
docs/support/
  faq.md              # user-facing Q&A, bilingual-first (FR/EN in seed case)
  troubleshooting.md  # symptom → check → fix
  triage.md           # the routing rule, one page, human-readable
  log/                # (Tier 1) durable record of drafted/sent replies
BACKLOG.md            # fallback signal sink when jig is absent
```

The docs are the knowledge base; everything reads from and writes to them.
Formats stay plain Markdown with stable headings so a headless agent can
parse them without a schema layer.

## Components

| Component | Kind | Notes |
|---|---|---|
| `support-init` | skill + templates | scaffolds `docs/support/`; templates extracted from real Phase-0 practice, not designed upfront |
| `triage` | judgment skill | classify + route; no `.py` expected initially |
| `theme-sync` | skill (+ maybe `.py` later) | cluster recurring questions → FAQ update + signal emission |
| `draft-reply` | skill + helper | mailbox read → draft from docs → approval gate → log; the headless workhorse |
| channel adapters | later | Discord intake; Chatwoot handoff at scale |

## The jig seam (the load-bearing design)

Two thin contracts, both **degrading gracefully when jig is absent** —
counter must work for non-jig projects:

1. **Defects in.** `triage`'s defect route invokes jig's bug-fix workflow
   when jig is present; falls back to appending a structured entry to
   `BACKLOG.md` when it isn't. Everything past "this is a defect" is jig's
   job (diagnose gate, red→green, bug board) — counter never duplicates it.
2. **Signal out.** `theme-sync` writes recurring themes / feature asks to
   jig's `docs/inbox.md` (and defect clusters toward the bug board) when
   jig-scaffolded; to `BACKLOG.md` otherwise. This mechanizes jig's own
   "user signal" growth input — support becomes the signal supplier.

**Detection:** how counter knows jig is present is an open question (below).
Candidate: cheapest-possible probe (does `docs/bugs/README.md` /
`docs/inbox.md` exist?) rather than a formal breadcrumb, unless real
ambiguity shows up. Precedent for the formal version if needed: servo
ADR-0013's host-global `available.json` + jig spec 072-02.

Per the writer-owns-the-contract rule, anything counter *writes into* jig's
artifacts (inbox entry shape, backlog entry shape) is specified on counter's
side; jig needs no changes at all in v0.

## What it deliberately does not own

- Conversation storage (mailbox / Discord / Chatwoot remain the system of
  record).
- Sending (human gate; counter stops at draft + log).
- Bug diagnosis/fixing (jig), evaluation (servo), project management.
- Any UI.

## Open questions (for the future exploration session)

1. **Name.** counter / vise / bench / other — workshop-tool family.
2. **Detection contract:** filesystem probe vs. formal breadcrumb; is a
   reciprocal jig-side ADR ever needed, or is v0 truly zero-jig-changes?
3. **v0 intake scope:** email-only, or is Discord (the beta channel) in from
   the start? Lean: email-only; Discord stays human-read per SUPPORT-PLAN
   Phase 1 ("beta support = user research; read every message personally").
4. **Log format** for `docs/support/log/` — needs to be greppable by
   `theme-sync` and safe to commit (PII: strip sender identity? keep only
   question-shape + resolution?). The PII question may be the hardest real
   design problem in the pack.
5. **Approval-gate mechanics** in headless mode: draft lands where — a git
   branch, a drafts folder, the mail provider's Drafts via API?
6. **Does `theme-sync` need teeth** (a deterministic check that the FAQ was
   actually updated when a theme crossed a threshold), or is it
   judgment-only? Lean: judgment-only until a real miss.

## References

- [vision.md](vision.md) — why, for whom, tiers, birth trigger.
- jig `docs/architecture.md` — packaging/scaffold-mode precedents.
- servo ADR-0013 + jig spec 072-02 — the sibling-contract precedent.
