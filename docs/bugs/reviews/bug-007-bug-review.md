---
bug: 007
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-13T19:03:46Z
prompt_source: bug-fix bug-review subagent
---

VERDICT: pass

REASONING: The change fixes the diagnosed root cause by enforcing exact-set
semantics between public `skills/*/SKILL.md` directories and the tier-derived
`EXPECTED_SKILLS` contract. The validator reaches repository CI, Claude
package validation, Codex package smoke validation, and installed-plugin
verification. `_...` infrastructure remains exempt, matching scaffold
behavior. The verifier-level regression test is behaviorally red on fresh
main and green with the fix.

SPECIFIC ISSUES:

- [strength] The source-repository test catches accidental plugin-only skills
  before packaging, while package validators provide defense in depth.
- [strength] `EXPECTED_SKILLS == union(_TIER_SKILLS)` remains mechanically
  pinned, completing the two-hop invariant.
- [strength] The diagnostic names both the offending path and required
  registration locations.
- [strength] The private-infrastructure regression test preserves the
  `_`-prefixed scaffold contract.

RECONCILIATION NOTES: The regression reference was changed to the stronger
production-facing verifier test suggested during review. Keep `.codex/` out
of the PR and reference GitHub issue #89.
