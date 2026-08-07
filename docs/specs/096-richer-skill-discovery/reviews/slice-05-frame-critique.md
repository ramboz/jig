---
slice: 096-05 — anomaly-record-and-consumers
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (frame-critique, reshaped onto ADR-0040)
reviewed_at: 2026-07-28T14:57:56Z
prompt_source: review.py frame-critique
---

Frame-critique of reshaped 096-05 (onto ADR-0040) — **pass**. All load-bearing
code claims verified in-tree: craft is a shared pass token (review_evidence.py:235
vs :260), record_review has three keying paths (:1452-1455) so keying mode is
observable at the chokepoint, check_reviews is binary, parse_verdict_file never
raises on content. The frame consumes 096-03's sidecar contract (OQ2) rather than
assuming it away. Observations folded in: AC5 tightened — the check-reviews warning
is explicitly non-blocking stderr with its exit-code contract unchanged, all
aggregation on status-board; AC3's dependency on the sidecar retaining per-candidate
tier labels is now pinned as a 096-03 contract (AC9 there). Frame survives.
