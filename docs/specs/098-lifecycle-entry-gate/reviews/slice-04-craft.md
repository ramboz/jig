---
slice: 098-04 — bug-lifecycle claim marker
pass: craft
verdict: pass
reviewer: reviewer subagent (read-only, independent)
reviewed_at: 2026-08-02T06:02:27Z
prompt_source: review.py pr-review-style craft prompt; deliverables: bug.py, test_bug.py
---

Independent craft review (read-only reviewer subagent). **Verdict: pass.**

The marker block is clean, idiom-consistent with the `workflow.py`
`_write_spec_ref_marker` sibling (same best-effort `try/except Exception: pass`
posture, `# noqa: BLE001`, side-effect isolation, after-write ordering), and the
"one signal, two shapes / no cross-talk" comment carries real rationale. Edge
cases hold: 3-digit id padding lines up with `_marker_names_bug`; the regex
tolerates whitespace; the clear-only-if-it-names-this-bug guard leaves spec/other
markers untouched; absent / non-dir / unreadable `.jig` all swallowed.

Findings and disposition:
- RECONCILIATION (substantive) — root-resolution asymmetry: `workflow.py`
  sentinel-anchors `.jig` (`_project_root_for_spec`), while `bug.py` wrote to
  `project_dir / .jig` directly, which could diverge under track-local adoption
  (`docs_root="."`) or a non-root `--project-dir`. **Fixed:** `_spec_ref_marker_path`
  now resolves via `project_layout.project_root_for(project_dir, fallback=…)`, so
  both writers and the entry gate agree on one `.jig` location. Tests still green
  (temp fixtures have no sentinel → fall back to project_dir, unchanged).
- NIT — two pickup tests were near-identical. **Fixed:** the push-reservation
  test now exercises the distinct re-pickup-by-owner path (`existing == owner`).
- NIT — no direct `_marker_names_bug` leniency test. **Fixed:** added
  `test_marker_names_bug_is_lenient_and_normalizes`.
- NIT — terminal branch nominally lists ESCALATED/RESOLVED_ON_MAIN though only
  DONE is reachable via `transition_bug`. **Fixed:** added a clarifying comment.
- Deliberate choice noted for the deviation log: four inline call sites recompute
  the bug id and write/clear; extraction shared with workflow.py is correctly
  deferred to a third caller (ADR-0002).
