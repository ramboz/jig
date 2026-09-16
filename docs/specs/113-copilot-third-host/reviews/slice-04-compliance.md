---
slice: 113-04 — advisory-hooks
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T06:14:31Z
prompt_source: review.py compliance 113-04 (R2)
---

Compliance pass on slice 113-04 (advisory-hooks). Reviewer: read-only jig:reviewer.

R1 — needs-changes: `translate_hook_protocol`'s response-schema half is never
runtime-applied (the adapter forwards child stdout verbatim), the
"genuinely exercised" claim was misleading, the AC1 test was vacuous-integration,
and the shipped advisory output leaked the Claude-ism `continue`.

R2 — PASS (accepted-deferral disposition + honesty fix). Wording corrected across
`build_copilot_plugin.py` + `scaffold.py` + `translate_hook_protocol` docstrings +
the AC1 test comment: the response half is repo-wide-unwired (Claude/Codex equally),
only the config-level translation (event/matcher map + `build_hook_command`) + the
runtime input adapter are exercised this slice; runtime response-wiring is 113-05.
New `ShippedAdvisoryOutputThroughAdapterTests` pins the real shipped output
(`additionalContext` fires; `continue` survives un-stripped) with a genuine
behind-origin git fixture proving git-freshness actually fires. AC1–AC4 hold with
non-vacuous, negative-controlled tests. Deferrals homed as first-class items:
slice-05 DoR (enforcing-adapter output/exit post-processing) + slice-06 AC5
(unshipped-`scripts/` residual).

VERDICT: pass. Carry-forward (no action this slice): the "Copilot ignores an
unrecognized `continue` key" claim is asserted, not live-verified — de-risked by
113-05 stripping it + the fail-open posture + the spec-wide 113-01 live-session
unknown.
