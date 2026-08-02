---
slice: 098-04 — bug-lifecycle claim marker
pass: compliance
verdict: pass
reviewer: reviewer subagent (read-only, independent)
reviewed_at: 2026-08-02T06:02:27Z
prompt_source: review.py implementation-style prompt; deliverables: bug.py, test_bug.py, SKILL.md
---

Independent compliance review (read-only reviewer subagent, no access to the
implementation conversation). **Verdict: pass.**

All seven ACs are met in `skills/bug-fix/bug.py` and backed by non-vacuous tests
in `Slice098BugMarkerTests`. The reviewer verified the hard AC3 compatibility
requirement by reading all three readers directly: `read_attribution.read_spec_ref`
requires both `spec=` and `slice=`; `gate_telemetry.read_spec_ref` uses
`startswith("spec=")`; `usage._SPEC_REF_RE` anchors on `^\s*spec\s*=`. A `bug=NNN`
marker is therefore genuinely invisible to all three, and the two AC3 tests pin
real return values (`("","")`, `""`, `None` for bug-shaped; `("098","098-04")`,
`"098"`, `"098"` for spec-shaped), not "didn't crash". "Extend, not repurpose" is
honored; no sibling file needed (so 098-01's AC2 needs no file-name change and the
DoD's conditional sibling-file deviation does not apply).

Findings and disposition:
- MEDIUM — host-package mirrors (`hosts/claude/...`, `hosts/codex/...`) are stale;
  CI drift-guard would fail. **Reconciliation item, not a logic defect** — host
  packages regenerated during reconciliation (see deviation log).
- LOW (test quality) — `test_failed_status_write_leaves_no_marker` patched
  `atomic_write_text` globally, so it would pass even if the stamp preceded the
  status write. **Fixed:** the test now fails only the bug-record (`*.md`) write
  and lets the marker write succeed if reached, truly pinning after-write ordering.
- NIT — the "different bug's marker untouched" branch was covered only for a
  spec-shaped foreign marker. **Fixed:** added
  `test_release_leaves_a_different_bugs_marker_untouched` (seeds `bug=002`).

Reviewer had read-only tools; the full-suite green (78 tests) and the ordering
mutation-reasoning were verified by the implementer.
