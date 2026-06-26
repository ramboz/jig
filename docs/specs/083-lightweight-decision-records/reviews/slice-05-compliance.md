---
slice: 083-05 — Routing rubric + `decisions.py add-lightweight` helper
pass: compliance
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-26T19:45:28Z
prompt_source: review.py implementation/pr-review 083-05+06 (paired), read-only jig:reviewer
---

Compliance pass (jig:reviewer, Opus, read-only) covering 083-05 + 083-06 in one PR. Slice 083-05: PASS. All four ACs met — add-lightweight appends well-formed entries with today-date default (AC1); normalized date—title idempotency tested with whitespace/case variation + byte-equality (AC2); four-route rubric present with verbatim ADR_TRIGGER in the ADR row (AC3); drift guard asserts the sentence in all four sites + ADR-0031, em-dash-exact (AC4). Tier-0 placement keeps scaffold helper-closure intact; host copies in sync. Nits (addressed): missing-`## Entries` ValueError now tested; `_existing_keys` scan-breadth documented.
