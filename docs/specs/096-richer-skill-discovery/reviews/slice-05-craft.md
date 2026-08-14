---
slice: 096-05 — anomaly-record-and-consumers
pass: craft
verdict: pass
reviewer: jig:reviewer (independent, post-hoc close-out)
reviewed_at: 2026-08-14T20:09:57Z
prompt_source: review.py pr-review --richer-skill none --non-interactive (096-05)
substrate: non-interactive
---

## Craft verdict — slice 096-05 (anomaly-record-and-consumers)

**Verdict: pass.** Independent read-only `jig:reviewer` craft pass over the
on-disk implementation (merged via PR #194), run during lifecycle close-out.

The code is idiomatic to jig and well-structured:
- `_substrate_lines` (review.py:754-809) reads top-to-bottom as an ordered
  precedence with AC-numbered comments.
- `substrate_anomaly` (review_evidence.py:289-320) is genuinely defensive —
  wraps the body in `try`, tolerates a scalar `shown_candidates`, coerces via
  `str()`, returns `[]` on Attribute/Type/ValueError. The malformed-data edge
  case is really handled, not just asserted.
- The non-blocking contract is cleanly expressed in both consumers: the advisory
  swallows all exceptions and is sequenced before the exit-code branch;
  `_substrate_audit_section` returns "" on a clean corpus and is discarded on
  board recompose (no duplication).
- Tests round-trip through real file write → frontmatter parse → subprocess, so
  they exercise the serialization boundary, not in-memory dicts — non-vacuous.

**Non-blocking nits (accepted, low-risk; recorded here as the durable home):**
1. `shown_candidates` is serialized as a hand-built flow list `[name:tier, …]`
   (review.py:805-806); a skill name containing `,` or `]` would corrupt it.
   Low-risk because skill names are directory-constrained (no such chars).
2. `_substrate_audit_section` renders the "shown-and-declined anomaly(ies)"
   bullet even when that count is 0 if other signals are nonzero
   (workflow.py:2339) — minor board noise, honest.
3. The `slice-NN-` glob prefix is derived by string-slicing an evidence path's
   stem (review.py:1895-1897) — works, mildly indirect for the reader.

None block close-out; all are captured here for the record.
