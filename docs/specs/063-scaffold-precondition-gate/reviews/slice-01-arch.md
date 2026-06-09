---
slice: 063-01 — classify-and-route-on-new
pass: arch
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-08T23:22:48Z
prompt_source: review.py arch-review
---

VERDICT: pass

REASONING:
This slice introduces a clean new shared-helper boundary (`skills/_common/scaffold_state.py`)
that is a true import leaf — only stdlib plus the frozen `GATE_DISABLE_VALUES` tuple from
`_common.review_evidence`, no cycle and no dependency on `skills/scaffold-init/`, exactly as
`_common`'s sibling modules do. The route-don't-block precondition is correctly layered (pure
classifier in `_common`, policy/messaging in `workflow.py reserve_spec`), consistent with the
documented ADR-0011/0013 deliberateness-gate doctrine, and preserves the existing reserve path
verbatim behind a `scaffold.json`-first short-circuit. No public contract surface is touched
(architecture.md § Contract surfaces is "skipped"), the CLI consumer contract degrades
gracefully via the bypass, and the one genuine architectural compromise — a third copy of the
trigger predicate — is a deliberate, spec-sanctioned deferral, not an accidental layering
violation.

SPECIFIC ISSUES:
- [strength] scaffold_state.py:45 — `_common` leaf discipline preserved precisely (stdlib +
  `GATE_DISABLE_VALUES` only; no cycle; watermark literal duplicated to avoid the upward dep).
- [strength] scaffold_state.py:65 — sharing the single `GATE_DISABLE_VALUES` vocabulary across
  the spec-precondition gate and the review-evidence gate is the correct anti-drift seam.
- [strength] workflow.py:2586 — good separation: `_common` owns pure classification;
  `reserve_spec` owns policy + bypass; `scaffolded` falls through to the untouched legacy flow,
  so blast radius on the proven 003-03/037-02/051 reserve path is structurally nil.
- [strength] scaffold_state.py:130 — load-bearing ordering documented AND pinned by a dedicated
  test; the crashed-scaffold misclassification failure mode is anticipated and guarded.
- [nit] scaffold_state.py:54 — `_JIG_CLAUDE_MD_WATERMARK` is now a 3rd independent copy of the
  watermark string (scaffold-init's, this module, plus two test files). Leaf-discipline
  justification for not importing is sound, but if the template watermark text changes these
  copies drift silently — no cross-check test pins byte-identity to scaffold-init's literal
  (contrast spec 050's people.md byte-identity cross-check). Worth a one-line guard test or an
  inbox note.
- [nit] workflow.py:2604 — under bypass, the legacy weak `docs/specs/`-absent refusal is
  retained, so the dead-end message that motivated this spec still exists on that one path.
  Deliberate "preserve today's behavior exactly" choice (tested) — flagging that the dead-end
  is retained rather than removed.

RECONCILIATION NOTES:
Both nits are non-blocking and belong in the deviation log, not a blocker on REVIEWED.
(1) Watermark literal triplicated with no byte-identity cross-check — add an inbox note or a
small pin test so a future template-watermark edit can't silently break interrupted-scaffold
detection. (2) Bypass path intentionally re-exposes the legacy dead-end; by design, covered by
`test_bypass_preserves_legacy_weak_refusal` — recording for traceability. The deliberate third
copy of the trigger predicate is already documented in the deviation log + spec non-goals as an
out-of-scope rule-of-three EXTRACT; no new architectural debt beyond what the spec sanctioned.
