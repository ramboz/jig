---
slice: 073-01 — reader honors frontmatter status
pass: compliance
verdict: pass
reviewer: jig:reviewer (independent, read-only)
reviewed_at: 2026-06-15T17:12:45Z
prompt_source: review.py implementation docs/specs/073-adr-status-frontmatter/spec.md 073-01
---

VERDICT: pass

REASONING:
All five acceptance criteria of slice 073-01 are met: frontmatter-first resolution (satisfied only on exact `status: Accepted`), Superseded/Proposed refusal with state-naming reasons, prose fallback for legacy ADRs, the bug fix (a `Superseded by` line beats the `Accepted (date)` line in the prose path), and ADR-filename diagnostic parity. Binding guidance honored — inline `Superseded by` regex check, no `_classify_status` lift (rule-of-three), case-sensitive exact match. Tests are meaningful (the no-prose-`## Status` Accepted fixture proves the no-prose-consult path; the prose-superseded fixture mirrors real adr-0002/0008, verified against the line `adr.py supersede` writes). Test-quality snapshot: no signals fired.

SPECIFIC ISSUES:
- workflow.py:782 — Minor robustness asymmetry (Low/non-blocking, no AC violation): the frontmatter branch guards on `"status" in fields` only, whereas sibling `_lookup_slice_status` guards on `"status" in fields and fields["status"]`. A bare empty `status:` would enter the frontmatter branch and return "<name> is  (not Accepted)" (doubled space) instead of falling back to prose. Not reachable via 073-02's writer (always stamps a value) or any legacy ADR (lacks the key) — cosmetic/defensive nit.

RECONCILIATION NOTES:
- No behavioral deviation from spec/ADR-0026; read-side contract as specified; "do not extract _classify_status" followed.
- Deviation log still the unfilled _TODO placeholder; complete during reconciliation before the RECONCILED gate.
- Optionally align the guard to `"status" in fields and fields["status"]` for symmetry — optional, not required for this slice.
