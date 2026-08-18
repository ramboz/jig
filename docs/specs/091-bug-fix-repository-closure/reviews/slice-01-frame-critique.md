---
slice: 091-01 — repository-closure evidence and gates
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (2 independent passes)
reviewed_at: 2026-08-18T21:39:27Z
prompt_source: review.py frame-critique docs/specs/091-bug-fix-repository-closure/spec.md 01 <slice>
---

Pre-implementation frame-critique of spec 091 slice 01 (repository-closure
evidence and gates). Two independent passes; the second returned pass.

**Verdict: pass.**

## Load-bearing assumption

Backward compatibility for the new closure schema is keyed to an explicit,
creation-time `closure_schema:` frontmatter marker stamped by `bug.py new` —
not to the presence/absence of the closure body sections, and not to an
enumerated record range.

## What the first pass forced (fixed before this pass)

The slice originally (during this critique cycle) defined "legacy" as "a record
without the closure sections." The first reviewer showed this is self-defeating:
section-absence is exactly what the FIXING gate enforces, so the parser has no
independent discriminant — a genuine pre-schema record and a new record that
evaded by deleting the headings hand the parser identical text. That forced an
unwinnable choice (exempt section-absent records → silent bypass, the bug-005
"green-light for the wrong reason" dynamic; or enforce on all → the 001-033
legacy corpus can no longer transition, the very invalidation the assumption
denies).

Resolved by keying compatibility to an explicit creation-time frontmatter
marker distinct from the body sections, so *legacy-by-omission* (no marker →
exempt) is distinguishable from *evasion-by-omission* (marker present, sections
empty → gate fires). Grounded: verified that no existing record (001-033)
carries any schema/version frontmatter field and `bug.py`'s template
(`_record_text`, sole path via `new_bug`) emits none, so the field is additive
and cannot collide. AC2, AC7, and the DoR were updated to reference the marker
rather than section presence.

## Residual, folded in

The scheme presumes tool-mediated creation: a hand-authored record is unmarked
and travels the legacy-exempt path. Accepted as the same deliberateness-gate /
`*_GATE=0` bypass limit the ADR-0011 lineage already concedes, and stated in the
spec — with the dogfood implication that jig's own bug records must be created
via `bug.py new` to be gated. Compatibility fixtures pin both the marked-new and
unmarked-legacy cases.

## Disposition

Frame survives. The remaining note was a wording sharpening, folded in before
recording this verdict.
