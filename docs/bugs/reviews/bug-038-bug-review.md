---
bug: 038
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-17T19:55:58Z
prompt_source: review.py bug-review docs/bugs/038-stale-blind-to-proposed-adr.md skills/spec-workflow/workflow.py skills/spec-workflow/test_workflow.py
---

Independent bug-review pass (jig:reviewer subagent, read-only).

VERDICT: PASS

The fix addresses the documented root cause (the conjunctive
`if not lv or not deps: continue` guard that structurally excludes
never-verified Proposed ADRs), not the symptom: it adds a distinct
never-verified-by-definition path keyed on `status == "Proposed" and not lv`,
aging by the proposal date, never by `last_verified` (honoring the
ADR-0024/0046 freshness-field ruling). `StaleProposedAdrTests` is a genuine
regression suite — two detection tests that go red pre-fix (`find_stale_items`
returns [] for an empty-last_verified ADR) plus three scope guards (recent
Proposed, verified-once Proposed, Accepted-empty-lv all correctly left alone).
Repository-closure and call-site-closure are non-vacuous and honest: a real
grep enumeration, an explicit reuse-vs-duplicate decision (local
`_adr_proposed_date` over a cross-skill `adr.py` import), and per-site
dispositions; the new `proposed-unverified` category renders through the
category-agnostic `stale()` with zero renderer change.

Non-blocking: `green_confirmed_at` empty at review time (stamped at REVIEWED);
the `_file_modified_iso` fallback is an untested safety net (documented in the
record).
