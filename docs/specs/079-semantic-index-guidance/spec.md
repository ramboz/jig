---
status: DONE
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 079: Semantic-index guidance

> Source: [eng-tips self-audit brief-05](../../external-review/eng-tips-2026-06/brief-05-semantic-index-recommendation.md)
> (EngTip #26 "Token Saving", #23 "Your Codebase Is Your AI's Context").
> Reserved 2026-06-19 via `workflow.py new`.

## Overview

jig's context-cost work (spec 055/057) established that cost ≈
orchestrator context × turns and that **turn count** is a top knob. Its
mechanisms attack symptoms (delegate reading, growth nudge) but never name
the root lever EngTip #26 calls out: a **semantic/code index** that lets
the agent ask "where is `foo` declared?" in one query instead of grepping
every match across many turns. jig recommends it nowhere — a scaffolded
project gets jig's advice to keep context lean with no pointer to the
single highest-leverage deterministic tool for doing so.

This is a clean fit for jig's established "orchestrate installed tools,
install nothing, defer to richer" pattern (`contracts`, `code-health`,
the security-floor scanners).

**End state:** `docs/workflow.md`'s context-cost guidance gains a short,
on-the-page-only-when-read section: *when* a semantic index pays for
itself, *which* standard options to reach for (centered on public/portable
tools — IDE indexers, tree-sitter-based local indexers, Glean/Kythe — with
internal ones like Scout/Tokensave mentioned only as "if available"), and
the detect-installed-else-recommend stance.

## Assumptions

None load-bearing about jig's own runnable surfaces — this slice ships
**guidance text**, not code. The empirical "indexes cut turns" claim is
EngTip #26's, cited, not re-derived here; the spec is explicit that a
recommendation is *not* a savings guarantee (EngTip #23's "context isn't
free" caution applies to indexes too).

## Clarifications

- **Skill vs. standing guidance (resolved 2026-06-19):** **standing
  guidance in `docs/workflow.md`** — lighter, on-path-only-when-read, adds
  no always-loaded skill description (respects spec 076's lean-context
  goal). No new skill, no `.py` helper.
- **Public vs. internal tools (resolved):** center the recommendation on
  the *category* + portable/public options; name Adobe-internal Scout /
  Tokensave / Polyget only as "if available," since jig ships publicly.
- **Scaffold nudge (deferred — 079-02):** an opt-out `scaffold-init` hint
  is conditional on the passive guidance proving insufficient.

## Decomposition

SPIDR — primarily a **Rules** split (the rule "when a semantic index pays
for itself," expressed as standing guidance).

- **079-01 (the guidance):** add the context-cost-discipline section to
  `docs/workflow.md` with the when/which/detect-and-defer content. Ships
  the whole user-facing value on its own.
- **079-02 (conditional scaffold nudge):** a one-line `scaffold-init`
  hint + `.jig/no-index-hint` opt-out (mirrors 072-01). **Conditional** —
  only pursued if 079-01's passive guidance demonstrably isn't reaching
  people; otherwise parked DEFERRED.

## Slices

- [079-01 — workflow.md index guidance](slice-01-index-guidance.md)
- [079-02 — scaffold index hint (conditional)](slice-02-scaffold-index-hint.md)
