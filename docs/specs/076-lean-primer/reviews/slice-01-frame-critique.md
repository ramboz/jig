---
slice: 076-01 — relocate + compress the Hot Cache
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-20T14:04:55Z
prompt_source: review.py frame-critique (4 rounds)
---

VERDICT: pass

REASONING:
The single load-bearing assumption — that the always-on-vs-on-demand split correctly bins every behavioral guard, since a mis-binned guard silently stops guarding (push vs. pull) — is named explicitly and not overclaimed. An audit of the actual relocated set vs. kept-inline set found every push-directive guard (PARKED-don't-re-propose, extract-only-at-third-transition, MERGING main→v2-not-rebase, do-not-modify-conventions.md, reviewer-read-only, hook-path/no-jq, ADR/slice paths, compress-on-close) kept inline as its full directive and pinned by the test, while relocated entries are genuinely definitional or helper-encoded. The two-layer mitigation is honestly scoped (whitelist backstop for known guards; residual risk on AC #1 + review).

SPECIFIC ISSUES:
- none — frame survives. (Minor, non-load-bearing: slice AC #5's "complete behavioral-guard set" phrasing self-corrects two sentences later with its explicit "Honest scope: whitelist backstop for the known guards.")

PROVENANCE:
Frame-critique cleared on round 4 (fresh reviewer each round). Prior rounds caught real frame defects, all fixed before this pass: (R0, with the user) the false "AGENTS.md is the lean target" premise — corrected, budget re-anchored to an absolute ≤70 lines/≤14KB; (R1) AC #2 conflated key-resolvability with information preservation + a concrete lossy relocation (Review-evidence gate dropped the PASSES enum / adr.py-accept gating) — AC reframed to recoverability-in-two-hops, glossary detail restored; (R2) AC #5 was a weak-substring whitelist ("v2" wouldn't catch relocating "MERGING main→v2 (not rebase)") + spec overclaimed CI completeness + latent loader first-paragraph-only truncation — markers strengthened to full directives, claim honestly scoped, single-paragraph invariant test added; (R3) index display term "Thin-orchestrator" ≠ glossary key "Thin-orchestrator discipline" so /jig:explain on the copied index term missed, and the test hid it — aligned the term + added a test tying each relocated term to its verbatim **bold** index entry.

RECONCILIATION NOTE (for the deviation log):
The worktree-aware-reservation caveat ("pushing from the temp worktree breaks relative-origin repos") was relocated wholly to the glossary and dropped from the inline index line. Defensible — it is a helper-internal invariant the agent does not execute by hand, not an agent push-directive — but it is the closest classification call; recorded here so the rationale is on file.
