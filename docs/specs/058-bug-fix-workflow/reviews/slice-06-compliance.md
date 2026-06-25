---
slice: 058-06 — `jig:bug-fix` skill + plugin wiring + workflow.md routing
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-24T22:06:36Z
prompt_source: /tmp/058-06-compliance.txt
---

Independent compliance review of slice 058-06. All four ACs met: SKILL.md exists with bare `name: bug-fix` (host prefixes jig:), trigger-rich description, full owned orchestration (lifecycle, two teeth gates, diagnose/diagnose_and_fix modes, borrowed diagnostic question, tier model, de-escalation), defers only pr-review + security-review. Plugin wiring consistent across scaffold._TIER_SKILLS, install_contract.EXPECTED_SKILLS, scaffold_contract._TIER_SKILLS, verify_install; bug.py rides the whole-dir copy in scaffold-init + migrate copy-machinery. Routing rule + bookend + CLAUDE.md roster name the real skill. Wiring tests exercise each AC. No blockers.
