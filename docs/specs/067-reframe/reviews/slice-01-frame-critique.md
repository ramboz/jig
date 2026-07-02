---
slice: 067-01 — The `/jig:reframe` skill: keystone ADR + dispositions
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T16:33:32Z
prompt_source: review.py frame-critique docs/specs/067-reframe/spec.md 067-01 <slice>
---

VERDICT: pass

REASONING:
The slice's single load-bearing assumption — that a two-level coverage floor makes a
weak coverage statement *visible* rather than rubber-stampable — is grounded verbatim in
accepted ADR-0024 §2–§4, not merely asserted. The L1 class list is a fixed, named,
unit-tested template (so a whole class cannot be dropped by silent omission the way the
n=2 servo `skills/` miss occurred), and L2 forces an artifact-level read inside touched
classes to confront the motivating intra-class shape. The plan does not over-claim:
ADR §Assumptions §4 retracts the earlier "owned, not assumed" framing, names three
genuinely-open residuals, and backstops each with T1's two-pronged evidence. Strongest
attack (no `.py` helper → L1 enumeration is unverifiable narration; a class could vanish
by not appearing in the table) is defeated: the class list is baked into the SKILL.md
contract and structurally tested. Frame is an owned-and-bounded risk with an honest
backstop, not a silent assumption.

SPECIFIC ISSUES:
- (primary, NON-BLOCKING) The fixed L1 class list is jig-corpus-shaped; nothing binds it
  to the actual top-level structure of a downstream repo, so a future artifact class not
  in the baked-in list would be invisible to L1 (the whole-class-drop failure moved up one
  level, into the template). Bounded/foreseeable, adjacent to the T2 corpus-growth trigger
  and residual (iii). Does not warrant needs-changes, but worth a one-line note in the
  SKILL.md that the L1 class list must be revisited if the downstream corpus grows a
  top-level class the template doesn't name — consistent with the spec's "omissions must
  be visible" ethos. (Folded into the SKILL.md at implementation.)
