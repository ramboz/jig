---
bug: 014
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-25T01:58:12Z
prompt_source: review.py bug-review (round 8 of 8)
---

Eight rounds of this pass ran against successive states of the fix; this
record stamps the verdict on the final one. The findings themselves are not
reproduced here — they are recorded, with the reproduction and the fix for
each, in the bug record's `## Already tried`
([014-slice-claim-covers-only-in-progress.md](../014-slice-claim-covers-only-in-progress.md)),
which names the pattern behind six of the seven self-corrections: a condition
that was correct only because of a narrower context it no longer sits in.
Read that section for the substance behind this `pass`.
