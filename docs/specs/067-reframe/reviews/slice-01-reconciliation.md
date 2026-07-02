---
slice: 067-01 — The `/jig:reframe` skill: keystone ADR + dispositions
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T16:58:21Z
prompt_source: review.py reconciliation docs/specs/067-reframe/spec.md 067-01
---

VERDICT: pass

REASONING:
The deviation log and reconciliation sweep are substantially faithful and honest — every
claimed doc change was spot-checked and present/accurate: both CLAUDE.md + AGENTS.md
hot-cache mentions (parity), the glossary Reframe entry (6-disposition + two-level floor +
capability-not-lifecycle), all five tier-registration surfaces, the SKILL.md L1
authority-bearing-corpus clarification, the 6-disposition Close-out correction, host-package
regeneration, ADR-0024 Accepted + reindexed, product-vision item 19 + counts, the
worked-example tier line. The disposition set is credible: architecture.md is a genuine
no-op (no .py/subagent/hook), and the workflow.md + inbox deferrals to 067-03 are legitimately
owned. Scope is appropriate (judgment-only skill + registration, no creep, no principle
violations).

One real drift the reconciliation review CAUGHT and this session then FIXED: README.md:33
"7 Tier 0 + 11 more (Tier 1)" was stale after the slice made Tier 1 = 12 (an internal
contradiction with "all 19 skills"; 7+11=18). Fixed to 12, host mirror regenerated, recorded
in deviation-log #8 + the sweep's README entry. With that resolved, the reconciled state is
clean → pass.

SPECIFIC ISSUES:
- [resolved] README.md:33 Tier-1 subtotal "11 more" was stale (should be 12; contradicted
  "all 19 skills"). Fixed during reconciliation to "12 more"; hosts/claude/README.md mirror
  regenerated; build_host_packages --check back in sync. Recorded in deviation-log #8.

RECONCILIATION NOTES:
- Deferred (honest, not silent): docs/inbox.md reframe/occurrence-3 carries now-stale status
  prose ("067-01 is DRAFT … ADR-0024 still Proposed"). The sweep deliberately defers inbox
  pruning to spec close (067-03) and keeps the occurrence entries as the live T1/T2/T3
  trigger-watch evidence ledger — reaffirmed here so it isn't mistaken for drift at close.
