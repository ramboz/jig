---
slice: 096-02 — update-subcommand
pass: reconciliation
verdict: pass
reviewer: jig:reviewer (independent, read-only)
reviewed_at: 2026-07-24T23:59:00Z
prompt_source: review.py reconciliation (spec 096, all slices)
---

Independent reconciliation review of spec 096 — does the written record match
reality? Run read-only against the artifacts, not the conversation.

**Verdict: needs-changes on the first pass. Every finding executed or corrected.**

The reviewer judged the *narrative* honest and complete: the mid-flight reversal
of the central mechanism is recorded in four independent places, and both
load-bearing defects are logged with mechanism, blast radius, and the regression
test pinning each. It confirmed no live surface still describes the removed
write-gate as real (the only `--confirm-lightweight` hits in `skills/` are
absence-guards).

What failed was the **sweep table**: written as a plan, it read as a record.
Three dispositions were not executed and three changed artifacts were missing.
Corrected:

1. **`docs/memory/glossary.md`** claimed **new**, was absent. NOW WRITTEN —
   "advisory lint", carrying the don't-re-wire-it warning and the false-negative
   weakness.
2. **`docs/inbox.md`** claimed **new (3 entries)**, was absent. NOW WRITTEN —
   the adr.py filename-contract drift test, the `promote` docs_root coverage
   gap, and the scaffold template's helper block.
3. **`hosts/**` was half-stale** — mirrors carried the new `decisions.py` but
   the *pre-096* `SKILL.md`, which would have tripped CI and shipped code whose
   documentation did not mention it. REGENERATED and verified.
4. **`docs/specs/README.md` had no 096 rows.** REGENERATED (280 slices / 95
   specs) and the four rows annotated with the load-bearing invariants —
   crucially **"PARKED: don't re-propose the lexical write-gate"**, which
   previously lived only in a slice deviation log nothing loads by default.
   Notes verified to survive a board re-run.
5. **Three changed artifacts were missing from the table** — `docs/workflow.md`,
   `skills/spec-workflow/SKILL.md`, `evals/cases/memory-sync.json`, plus the
   memory-sync **skill description** (the always-loaded surface the whole
   mechanism now rests on). ALL ADDED, the description as its own row.
6. **DoD checkboxes understated reality.** RECONCILED against the recorded
   verdicts and the deviation logs; the only deferral (`promote` under
   `docs_root: "."`) is now stated in the box, in the deviation log, and in the
   inbox rather than in one place.
7. **`spec.md` still claimed "Assumptions: None unverified"** while ADR-0039 now
   names a load-bearing unverified one. CORRECTED — the spec names it and points
   at the ADR.

Caught while finishing, not by any reviewer: expanding memory-sync's description
pushed it to 1303 characters against a **hard 1024 limit for the Codex host** —
13 install-contract failures. Trimmed to under the ceiling with every
eval-tested trigger phrase preserved; routing eval stays 64/64 positive, 44/44
negative.

Final state: 3618 tests OK, pyright clean, hosts in sync, ADR-0039 Accepted with
its frame-critique recorded.
