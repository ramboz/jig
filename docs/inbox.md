# Inbox

> Thin capture layer for unresolved ideas, observations, and items that surfaced during
> sessions but aren't ready for a spec. Triage during reconciliation or session end:
> (a) promote to a spec, (b) promote to an ADR, (c) drop.
>
> This is NOT a task list. Items here are not committed work — they're parked thoughts.

<!-- Add items below. Format: - [date] description -->

- [2026-05-11] JIRA integration: map jig specs → Epics, slices → Stories. Slices are the sprint-planning unit (they carry DoR/AC/DoD), so they belong at Story level. Specs are feature containers, so Epic is the right fit. Consider a future spec (e.g. 003-jira-integration) to automate or document the sync workflow.
- [2026-05-11] Slice landing step: slice DoD currently ends at "reviewed + reconciled" with no integration back to main, causing worktree drift, duplicated effort, and merge conflicts when parallel specs finally land. Proposed `/jig:slice-land` skill branches on a `scaffold.json` flag — `integration: "direct"` (solo: run tests, merge to main, optionally delete worktree) or `integration: "pr"` (team: run tests, push, open PR pre-filled with spec/slice context, AC checklist, deviation log). Likely shares a spec with the JIRA integration above (a DONE slice should also flip its JIRA story).
