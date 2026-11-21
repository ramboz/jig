---
status: DRAFT
skill: independent-review
use_cases: [UC-7, UC-8]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 126: Reviewer-recall eval

> Reserved on 2026-11-21 via `workflow.py new --no-push` (local provisional —
> the number is not yet on `origin/main`).

## Overview

> Implements [ADR-0071](../../decisions/adr-0071-reviewer-recall-eval.md)
> (Proposed). Investigation record: [R-002](../../research/R-002-claude-code-verification-assessment.md).
> **Status: recorded, not yet built** — the ADR must be Accepted before 126-01
> moves past DRAFT.

jig edits its reviewer prompts often (`skills/independent-review/review.py`)
and has never measured what those edits do to the defects reviewers catch.
This spec builds a **recall eval**: replay jig's code-reviewing passes
against the repo as it stood when a past defect landed, and count how often
each pass finds that defect. Recall is the share of known defects a pass
finds. A control set of clean merged slices measures over-flagging, i.e. how
often a pass raises a blocker on work that was fine.

The design follows the Claude Code team's "review the reviewers" practice
(R-002 item 12): one-sentence answer keys, only findings that describe the
bug get credit, merged and stable changes as an over-flagging control, a
tuning set kept apart from a fixed test set, and recall measured per stage
so a pipeline that loses bugs it found shows up.

It is **dev-time tooling for the jig repo**, not a lifecycle feature. The live
run calls a model under the developer's own auth and never runs in CI. It adds
no review pass and no gate (ADR-0055). It is not a servo↔jig boundary
(ADR-0022 stays PARKED). Its numbers inform reviewer-prompt changes and
measure the passes; they do not cut or add passes ("measure, don't cut",
ADR-0071 rule 7).

## Decisions

- **D1 — Backfill lives in the case file, not in closed bug records.** The 38
  DONE bug records are closed. Editing them needs owner approval (spec 102 /
  ADR-0010), so the facts each case needs (introducing change, review-time
  commit, answer key, split) go in `evals/reviewer-recall/cases.json`.
- **D2 — One forward-capture field on bug records: `introduced_by:`.** It is
  optional, blank by default and never gated. It records what the closure
  inventory's history search (`bug.py:279`, ADR-0037) already looks for. The
  answer key is eval data with no use in an adopter's bug lifecycle, so it
  stays in the case file. *This deviates from the suggested shape (both
  fields on the record) on leanness grounds.*
- **D3 — Replayed passes: compliance, craft, arch, code-health, bug-review.**
  These are the builders that review a code deliverable (the
  "CODE-review builders" comment, `review.py:225`). Each replay uses jig's
  baseline prompt. Configured or richer user skills are excluded, because
  jig can tune only what it ships. Frame-critique and design-review are out
  of scope (ADR-0071 rule 3).
- **D4 — Three stages.** The post's raw / post-verification / final stages
  map to jig's envelope as follows:
  - **found:** a credited `SPECIFIC ISSUES` entry;
  - **blocking:** the credited entry is tagged `[blocker]`. Compliance and
    bug-review use the untagged `_OUTPUT_FORMAT` (`review.py:731`, `:1078`),
    so for them, a credited entry under a non-`pass` verdict counts;
  - **stopped:** blocking, and the verdict withholds `pass`.

  A drop from found to blocking means the reviewer saw the bug and called
  it a nit.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **A1 — prompts are importable builders (grounded).** Every replayed pass
  has a builder function in `review.py` (:658, :919, :1024, :1085, :1218).
  Passing `richer_skill=None` with `non_interactive=True` gives jig's
  baseline buckets unless a project config names a skill, and config wins
  (`_resolve_richer_for_pass`, `review.py:800-822`). The harness therefore
  strips `review.*_skill` config from the scratch tree.
- **A2 — two builders read git against a branch named `main` (grounded).**
  The test-quality snapshot and touched-files blocks run
  `git merge-base main HEAD` (`_TEST_QUALITY_BASE_BRANCH`, `review.py:447`,
  `:512`, `:586`). The scratch repo therefore puts the base tree on `main`
  and the case tree on `HEAD`, and the builders need no change.
- **A3 — the bug corpus (grounded counts, estimated eligibility).** 41
  records: 38 DONE, 2 REPORTED, 1 RESOLVED_ON_MAIN. All DONE records have a
  multi-paragraph `## Root cause`. None has a one-sentence cause or a
  structured introducing-change field. About ten name the change in prose,
  e.g. bug 036 → `dc8d453`, bug 039 → `31cbcb4e`, bug 040 → spec 080-02,
  bug 010 → bug 003's fix. The estimated eligible pool is 15–25, and 126-01
  measures it. If it is below the ADR-0071 floor, 126-02 does not start.
- **A4 — host CLI behaviour (unverified, load-bearing).** `claude -p` can
  confine a run to Read/Glob/Grep, keep user-global config, plugins and
  hooks out, pin a model, and report usage and cost as JSON. The precedent
  `scripts/orchestrator_selection_probe.py:113-119` exercises only
  `--allowedTools`. 126-02's DoR probes the rest.
- **A5 — scripts are repo-only (grounded).** `scripts/` is not copied into
  host packages (`find hosts -name skill_routing.py` finds nothing), so the
  harness reaches no adopter. The `introduced_by:` template line is the only
  shipped change.

## Decomposition

SPIDR, mainly along **Data → Interfaces**:

- **126-01 (Data):** the case corpus with controls and a frozen split, plus
  `introduced_by:` capture. It answers on its own the first question: is
  there enough history to measure? (ADR-0071 corpus kill criterion.)
- **126-02 (Interfaces):** the dev-time replay harness and judge. One command
  gives `k/n` recall by stage and the control flag rate for chosen passes.
- **126-03 (Rules):** the persisted per-pass report (which passes earn their
  cost, as-configured vs all-on, tuning vs test) and the advisory re-score
  nudge when a prompt drifts from its last result.

**Spike axis considered and not split out.** A4 is the main unknown. It
is a probe in 126-02's DoR rather than its own slice, because the probe
is small and 126-01 is useful whatever it finds.

**Out of scope, owned elsewhere.** Turning misses into review rules (R-002
item 13) belongs to spec 127 / ADR-0072. Escalation retention across arch
rounds belongs to the arch-review redesign's own round-two evals in the
owner's dotfiles (spec 122 A3). This spec replays single rounds, so it does
not fire the refinement-todo trigger "Warn when an escalated arch record is
overwritten". The semantic skill-routing eval (refinement-todo, "Tier-3")
could reuse 126-02's runner but is not built here. servo's judge regression
set is servo spec 048 / ADR-0053.

## Slices

- [126-01 — case-corpus](slice-01-case-corpus.md) — bug cases + size-matched
  controls + frozen tuning/test split in `evals/reviewer-recall/`;
  `introduced_by:` on new bug records.
- [126-02 — replay-harness](slice-02-replay-harness.md) — dev-time replay of
  each code-reviewing pass at the case commit, judge + human audit, `k/n`
  recall by stage and control flag rate.
- [126-03 — per-pass-report](slice-03-per-pass-report.md) — persisted
  per-pass results with a prompt fingerprint, comparison report, and an
  advisory re-score nudge.
