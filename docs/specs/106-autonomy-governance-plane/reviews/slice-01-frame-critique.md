---
slice: 106-01 — scaffold the protected plane and the identity-separation gate
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-06T05:01:03Z
prompt_source: review.py frame-critique docs/specs/106-autonomy-governance-plane/spec.md 106-01 <spec> <slice>
---

Frame-critique of slice 106-01 (scaffold protected plane + identity gate). The
first pass returned needs-changes: AC4 tested identity-*name* distinctness (a
string inequality) rather than merge *capability* (least-privilege: no
merge/admin/bypass), and framed the check as a locally-deterministic observable
when merge capability is a GitHub server-side authorization fact.

Reframed and re-run to PASS. AC4 now mandates four fixtures — single-identity,
distinct-but-merge_capable, distinct-and-not-capable, unknown-capability. The two
distinct-name fixtures differ only in the attested `merge_capable` flag, so any
name-comparison-only implementation is structurally forced to fail the suite; the
unknown-capability fixture forces fail-safe not-ready. Capability is treated as
supplied/attested (derived by servo 023 from the GitHub API), jig deterministic
only over its inputs. Inert-until-armed is stated across spec Assumptions, AC2,
AC5, and the ADR.

Reviewer confirmed the frame holds. Carried notes for the implementer:
- Treat the attested `merge_capable` flag as authoritative for "ready"; never
  conclude not-capable from a `JIG_MERGE_IDENTITY` name mismatch alone (multiple
  merge-capable principals can exist).
- Emit a stable JSON verdict + exit code (the servo 023 contract); note in the
  deviation log if the emitted schema differs at build time.
- Solo-maintainer CODEOWNERS owner-resolution stays an explicitly-deferred open
  question (ADR Open questions), not silently satisfied.
