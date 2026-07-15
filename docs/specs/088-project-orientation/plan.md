# Plan: 088 project orientation

## 088-01 — computed orientation command

1. Add failing workflow and hook tests for headline classification, active-spec range
   compaction, lifecycle priority/claims, empty state, filesystem purity, and automatic
   SessionStart injection.
2. Implement a pure project-orientation renderer and expose it as
   `workflow.py orient --project-dir`.
3. Add the non-blocking SessionStart hook and update pickup guidance in source and
   scaffold templates.
4. Regenerate both host packages and run focused plus full verification.
5. Run compliance, craft, architecture, code-health, and reconciliation reviews;
   record evidence and close the lifecycle.

## 088-02 — the `/jig:orient` judgment skill

1. Adopt the contributed skill as `skills/orient/SKILL.md`; register it as a Tier-1
   skill across every pinned inventory (`_TIER_SKILLS`, install/scaffold contracts,
   tier tests) and the product prose counts.
2. Layer the skill on the 088-01 `workflow.py orient` headline; keep it zero-write
   (renders to stdout) and `docs_root`-aware; route ready-slice work through
   `jig:spec-workflow`.
3. Author the routing eval (`evals/cases/orient.json`) with project-level positives
   and mid-implementation route-away negatives; keep the routing gate green.
4. Regenerate both host packages; run routing plus full verification.
5. Architecture review (`arch_review: true`) via PR #90; record the accepted decisions
   in the slice, then reconcile and close.
