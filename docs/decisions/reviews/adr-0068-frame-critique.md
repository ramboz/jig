---
adr: 0068
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-20T21:59:37Z
prompt_source: review.py frame-critique docs/decisions/adr-0068-no-per-framework-runner-adapters.md
---

VERDICT: pass

REASONING:
Round 3 (rounds 1 and 2 returned needs-changes: the exit-status polarity, the `|| exit 1` advice, the `slice-land` read site, `tdd.py`'s own crash path and the built-in runners were all raised there and folded into the ADR before this round). The single highest-risk load-bearing assumption is that an exit status is a sufficient channel for red, with status 1 (the generic Unix failure status) as the only red, so soundness rests on each project's wrapper being honest. That exposure is real, but the ADR states it itself (Consequences; kill criterion 3), and the claims the frame depends on check out against the tree: the three read sites, the fail-closed polarity, and the Gradle recipe's reading of Gradle. No disclosure was found to be wrong in a way that changes the decision.

SPECIFIC ISSUES:
- Primary assumption: exit 1 can carry the claim "a test ran and failed" — the ADR's own polarity argument against Option F applies most strongly to status 1 itself (bare Gradle/Maven, an uncaught Python or Node exception, `set -e`). The options never considered a red that a crash cannot produce (a dedicated status or an output marker). Not blocking: the residual is disclosed, the caveat is in `NO_RUNNER_HINT` and the recipes document, and the alternative would break every native exit-1 runner including jig's own. Asked for one sentence recording why red stays at 1.
- Grounding checked and holding: `→ FIXING` refuses exit 2; `→ REVIEWED` routes any non-zero to `DIAGNOSING` (unchanged, accurate); `slice-land` blocks on exit 2 when `detect` finds a runner; no fourth code read site of `tdd.py run` in `skills/`, `hooks/`, `agents/`, `scripts/`, `templates/`; the helper's catch-all returns 2; the Gradle recipe matches Gradle behaviour as the reviewer knows it (not run).
- Secondary, factual — "pytest (through jig's own `scripts/run_tests.py` custom command …) is the one jig dogfoods" was inaccurate: `run_tests.py` is unittest-based and runs through the custom path.
- Secondary, kill criteria — criteria 1 and 3 depend on signals jig cannot observe; in practice the trip-wire is an issue report.
- Residual edge — an empty `.jig/test-command` with no built-in match showed the doc-only warning at `slice-land`.

Orchestrator follow-up after this verdict (not seen by the reviewer): the ADR now records why red stays at 1, corrects the dogfooding sentence, states the kill-criteria trip-wire, and `land.py` treats a present `.jig/test-command` as a declared runner.
