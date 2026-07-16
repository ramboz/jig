---
status: DRAFT
skill: memory-sync
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 094: Capture hygiene

## Overview

Three mechanical defects in spec 083's decision-capture path, reported with
counted field evidence in [#108](https://github.com/ramboz/jig/issues/108). Each
is wrong on its own terms — none depends on how the open frame question in #108
(whether the conversation scan survives at all) is answered.

The reporter classified 27 unique scratch-log entries by hand across 15 sessions
on a downstream scaffolded project (13–16 July 2026). Of those, **3 were
`<task-notification>` harness blobs stamped `who: "user"`** — text the owner
never typed — and **17 were the agent's own `AskUserQuestion` dialog**, captured
because the dialog was *dismissed* and the extractor fell back to quoting the
question. Only 3 were the owner genuinely saying something.

This spec fixes the noise, not the net. It deliberately does **not** touch:

- **The Tier-2/Tier-3 marker regexes** (`decision_scan.py:39-53`). Widening them
  is the open design question in #108 and needs the frame review spec 083's
  frontmatter (`frame_review: true`) requires — not a drive-by.
- **Dedup behaviour** (`dedup` / `prune_recorded_stubs`). Bug 011 defers the fix
  class deliberately; see `docs/bugs/011-decision-dedup-suppresses-reversals.md`.

The three fixes are independent and separately revertable: one filter, one
deleted fallback, one `description:` field. Each is also *additive to* the
existing 083-07 stub machinery rather than dependent on it — if the conversation
scan is later demoted or deleted (#108's open question), 094-01 and 094-02 remain
correct for whatever writes stubs, and 094-03 concerns the routing surface, which
that decision does not touch.

## Assumptions

- **Harness text reaches `UserPromptSubmit` in the `prompt` field.** Grounded in
  #108's evidence: three `<task-notification>` blobs appear in a real
  `.jig/decision-scratch/*.log` with `who: "user"`, and
  `jig-decision-inflight.sh:36,40` hardcodes `'user'` for everything arriving on
  that event. The reporter names this attribution path explicitly.
- **A dismissed `AskUserQuestion` yields a tool response carrying no answer
  text.** Grounded in the same evidence: the captured quote is the question plus
  its option labels ("… Enforcement Hard block …"), which exist only in
  `tool_input` — so `extract_askuserquestion_answer`'s response branch found
  nothing and the documented fallback fired. The exact dismissed-response shape
  is *not* asserted here; 094-02 removes the fallback rather than
  pattern-matching the response, so it does not depend on that shape.
- **`description:` is the routing surface.** Per spec 076 / EngTip #23 the host
  surfaces every skill's `description:` each session, and `skill_routing.py`
  exists to guard exactly that mechanism. Not re-litigated here.

## Decomposition

SPIDR **Rules** split. Three independent rules in the capture path, each with its
own failure mode, evidence, and revert boundary:

- **Attribution rule** (094-01) — what may be stamped `who: "user"`.
- **Extraction rule** (094-02) — what counts as an `AskUserQuestion` answer.
- **Routing rule** (094-03) — what vocabulary reaches the decisions path.

These are not phases of one change: each lands end-to-end value alone, in any
order, and reverting one leaves the other two correct. Splitting by Paths or Data
would have produced horizontal layers (predicate / call-sites / tests) with no
standalone value, which is why Rules is the axis.

## Slices

- [094-01 — machine text is never attributed to the owner](slice-01-machine-text-attribution.md)
- [094-02 — a dismissed dialog produces no stub](slice-02-dismissed-dialog-no-stub.md)
- [094-03 — decision vocabulary on the routing surface](slice-03-decision-routing-vocabulary.md)
