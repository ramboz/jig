---
bug: 027
pass: bug-review
verdict: pass
reviewer: jig:reviewer (subagent a62c79410ceadba22)
reviewed_at: 2026-08-02T06:22:36Z
prompt_source: review.py bug-review
---

VERDICT: pass

Fix addresses the documented root cause (repo-centric wording never re-anchored
for the shipped audience), not the symptom. The bare unanchored
`templates/docs/specs/slice-template.md` is removed from both live references
and both host mirrors (verified 0 hits); authors are redirected to the
mechanical `workflow.py new` starter (emits `slice-01-tbd.md` from the packaged
template) plus the host-agnostic project-root worked example
`docs/specs/001-adopt-jig/` (scaffold-seeded per scaffold.py / verify_install.py).
The regression test genuinely flips red→green on both assertions and is neither
brittle nor tautological; file-inspection is the correct test class for a prose
bug. Inline-code (not a markdown link) is the right choice since
`docs/specs/001-adopt-jig/` does not exist in the jig source repo but does in
every scaffolded project. In-scope for `local_patch`.

Reconciliation note (addressed): host mirrors regenerated via
scripts/build_host_packages.py; drift guard --check now passes.
