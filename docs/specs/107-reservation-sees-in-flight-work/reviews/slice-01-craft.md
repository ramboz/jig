---
slice: 107-01 — protection refusals reach the pull-request fallback
pass: craft
verdict: pass
reviewer: PR #165 in-band review (post-hoc)
reviewed_at: 2026-08-14T19:56:27Z
prompt_source: post-hoc lifecycle close-out; original review on GitHub PR #165
substrate: non-interactive
---

## Post-hoc craft verdict — recorded for lifecycle close-out

**Verdict: pass.** Recorded after the fact (ADR-0014 §5) for a slice that
shipped via [PR #165](https://github.com/ramboz/jig/pull/165) (merged to `main`
as `409ba19`). Craft was reviewed in-band on the PR. The slice carries a written
`## Deviations` section documenting the additive design choices (scan folded in
at the call sites rather than rewriting `_next_spec_number`; the spec-037
contract left untouched), which is the craft trail. Host mirrors were
regenerated and the suite was green at merge. This file supplies the missing
in-repo evidence so the transition need not bypass the gate.
