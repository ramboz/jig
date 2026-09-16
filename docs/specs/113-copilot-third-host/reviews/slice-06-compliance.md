---
slice: 113-06 — committed-package-and-release
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T20:13:02Z
prompt_source: review-113-06-compliance.txt (jig:reviewer subagent, Opus)
---

Compliance review on slice 113-06 (committed-package-and-release). Reviewer:
read-only jig:reviewer (Opus). VERDICT: pass.

All 6 ACs met with non-vacuous, feature-coupled tests (verified independently,
including the silent-failure-prone lib-dependency audit):

- **AC1 (single builder + drift guard)** — build_host_packages builds hosts/copilot
  alongside claude/codex; host-agnostic guard proven by
  `test_check_detects_stale_copilot_file` (writes "DRIFTED", asserts failure +
  names copilot/.plugin/plugin.json). New package pieces covered by
  CommittedCopilotPackageTests.
- **AC2 (release archive + release-please lockstep)** — build_release_zip produces
  jig-copilot-vX.Y.Z.zip, refuses on version mismatch (exit 2); the copilot
  committed manifest is in release-please extra-files AND guarded by
  test_release_config (now expects 5 manifests); release.yml build/smoke/uploads
  the copilot zip; CopilotZipShapeTests present.
- **AC3 (per-host verification)** — validate_copilot_package independently validates
  the copilot package shape, wired into build_release_zip _smoke_copilot; a
  good-package-clean test + 10 failure-injection tests. Live-CLI probe deliberately
  substituted by the static validator (headless `copilot -p` does not reliably fire
  repo hooks) — the "closest deterministic substitute, recorded honestly" AC3 permits.
- **AC4 (docs)** — README Copilot install path + architecture.md tri-host topology.
- **AC5 (package completeness)** — .github/scripts/spec_lint.py + .github/templates/
  shipped; a completeness test fails if a referenced .github/ path is absent.
- **AC6 (remaining advisory-hook parity)** — all 9 MAPPABLE hooks rendered (0 MAPPABLE
  left); test_no_mappable_entry_remains; decision-inflight correctly ships only its
  userPromptSubmitted registration; every lib import across the 9 scripts resolves to
  a shipped file (incl. transitive decision_scratch → decision_scan).

Non-blocking (reconciliation-phase):
- build_copilot_plugin.py docstring wording imprecision (the 4 new libs are called
  "no nested lib imports" but decision_scratch imports decision_scan — shipped, so
  functionally fine; wording to fix).
- Positioning residual: docs/product-vision.md + docs/prompts.md still say "Claude
  Code and Codex" (two hosts). AC4 scopes only README + architecture.md (both done),
  so this is a disclosed residual, not an AC miss.

NOTE (post-review delta, does not invalidate this verdict): the 113-06 craft review
subsequently found the input-consuming hooks were registered-but-inert under Copilot
(the adapter didn't forward `prompt`). That was FIXED (adapter forwards `prompt` →
memory-scan/decision-inflight fire fully) and the host-gated remainder honestly
documented (AC6 caveat + refinement-todo + inventory notes). This STRENGTHENS AC6's
honesty (registration + documented input degradation); it does not change any AC's
met-status assessed here.
