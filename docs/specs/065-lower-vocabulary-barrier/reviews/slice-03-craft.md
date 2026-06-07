---
slice: 065-03 — `/jig:explain` skill (term + artifact modes)
pass: craft
verdict: pass
reviewer: jig:reviewer / pr-review
reviewed_at: 2026-06-07T18:06:31Z
prompt_source: review.py pr-review
---

VERDICT: pass

Judgment-only skill (no `.py`); deliverable is SKILL.md prose + a structural surface
test + four registration touchpoints. SKILL.md is well-shaped: clear two-mode contract,
fixed six-block walkthrough, honest "never invent / fail-soft / ephemeral" framing, a
precise deferral clause that doesn't shadow a richer onboarding skill. Registration
consistent across scaffold/install_contract/scaffold_contract + CLAUDE.md row; the inline
`lexicon.load('.')` recipe matches the 065-01 loader signature and dict-keyed-by-term shape.
Tests pin every structural AC meaningfully and stay pure-file.

[strength] Framing block ties design to lineage (065-01 loader, clarify-Q3 ephemeral,
judgment-skill pattern) and is honest about the accepted AC-testability gap.
[strength] DescriptionBoundsTests (anti-over-claiming) + tier-registration cross-checks are
the right structural surface for a no-helper skill — calibrated, not theater.
[nit, addressed] term-mode bash recipe hardcoded `sys.path.insert(0,'skills/_common')` with
the scaffolded path only in prose — fixed during reconciliation to probe both layouts.
[nit] tier-registration tests mutate sys.path without cleanup — harmless for the current
suite (unique jig-internal module names); could use try/finally. Non-blocking. (Reviewer:
jig:reviewer / pr-review, read-only.)
