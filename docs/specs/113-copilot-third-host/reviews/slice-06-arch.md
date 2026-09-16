---
slice: 113-06 — committed-package-and-release
pass: arch
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T20:13:02Z
prompt_source: review-113-06-arch.txt (jig:reviewer subagent, Opus)
substrate: non-interactive
---

Architecture review on slice 113-06 (committed-package-and-release) — the spec-113
capstone (arch_review: true). Reviewer: read-only jig:reviewer (Opus). VERDICT: pass.

The capstone is architecturally sound and reaches genuine full PACKAGE parity across
all seven surfaces (install, skills, agents, advisory + enforcing hooks, floor,
release, drift):

- **Multi-event hook merge** is at the correct boundary — render_copilot_hook_file
  stays a pure single-event source→dict function; the builder owns file-grouping —
  and is provably non-lossy because CLAUDE_TO_COPILOT_EVENTS is injective (the six
  pre-existing single-event hook JSONs are byte-unchanged, validating "single-event
  round-trips identical").
- **Release coordination** genuinely closes the v2.0.1 no-zip regression: all five
  manifests are in extra-files, the drift guard reproduces the copilot copy from the
  bumped root, and build_release_zip version-gates on the committed manifest.
- **Static verification substitute** is honest + spec-sanctioned (it even re-checks
  the load-critical 1024-char loader limit).
- **ADR-0061 invariant** genuinely closed (0 MAPPABLE, cross-checked both ways vs the
  real hooks.json).

Nits (both addressed):
- [nit] build_copilot_plugin.py merge relied on an EMERGENT injective-map invariant
  with no defensive assertion — a future non-injective map + dual registration would
  silently reintroduce the drop bug. FIXED: the merge now raises a "merge collision"
  ValueError on a duplicate event key, with a test.
- [nit/context] the rewritten .github/… command-path SPELLING resolves within the
  package (completeness-test-verified) but its live resolution under a /plugin cache
  install is unverified — this stays refinement-todo residual (a). So the close-out
  framing is full PACKAGE parity with a tracked runtime-command-resolution caveat,
  which must survive the spec-113 primer compression (not be dropped as "done").

Reconciliation guidance honored: refinement-todo residual (b) (skill-body rewrite
targeting unshipped .github/scripts/) is CLOSED by this slice (_copy_runtime_scripts);
residual (a) remains open; the live-probe skip is subsumed by (a). All recorded, not
silently dropped.

NOTE (post-review delta): the craft pass subsequently found + drove a fix for the
input-consuming hooks (adapter now forwards `prompt`; host-gated remainder honestly
documented). This is within ADR-0061's "degrade VISIBLY, not silently" invariant and
does not change this architectural assessment.
