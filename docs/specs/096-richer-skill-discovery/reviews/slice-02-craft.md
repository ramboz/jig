---
slice: 096-02 — baseline-exclusion-and-resolve
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (craft pass, re-review after blocker fix)
reviewed_at: 2026-07-29T04:22:59Z
prompt_source: review.py pr-review
---

## VERDICT
pass

## REASONING
The prior [blocker] is resolved: is_jig_baseline_path anchors the `jig` match to
a `plugins/` ancestor via exact-segment membership (avoiding both the jig-anywhere
bug and substring false positives like `plugins-backup` / `jig-tools`), backed by
targeted regression tests (jig-named project root resolves in discovery,
jig-before-plugins not matched, symlinked dir, admin-roots glob). The exclusion
invariant is tested end-to-end against the REAL scaffold writer. review_config
"stdlib only" docstring + Claude-then-Codex precedence documented; relative
explicit config path anchored to project_dir.

## SPECIFIC ISSUES
- [strength][impl] test_skill_discovery.py ScaffoldExclusionInvariantTest —
  invariant tested against real scaffold._copy_skills_and_agents, both directions.
- [strength][impl] skill_discovery.py — exact path-segment membership avoids
  substring false positives; searching skill_dir.parent.parts (excluding the
  skill dir name) is sound + documented.
- [nit][impl] Codex admin-scope exclusion asymmetry (a /etc/codex/skills jig
  baseline slips the path test) → recorded as a 096-03 obligation.
- [nit][impl] _FM_RE requires a trailing newline after closing `---`; a
  frontmatter-only SKILL.md with no body parses None. Real files carry a body.
- [nit][impl] relative explicit config path → now anchored to project_dir (fixed).

## RECONCILIATION NOTES
- Codex admin-scope exclusion + parse_skill_frontmatter fidelity carried to
  096-03 (its exclusion/candidate channel is the real consumer). Recorded in the
  deviation log's "Known gaps" so AC5 honesty is explicit.
- Cross-host precedence (Claude fully swept before Codex) is a documented,
  deliberately-accepted tiebreak for the pathological both-hosts-collide case.
