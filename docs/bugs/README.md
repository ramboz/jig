# Bug Status Board

> Related: [Spec Status Board](../specs/README.md). Check both boards before
> folding reported defects into spec acceptance criteria.

| ID | slug | severity | tier | status | reproduces? | regression test | claimed_by | escalated_to | Notes |
|----|------|----------|------|--------|-------------|-----------------|------------|--------------|-------|
| 001 | branch-freshness-preflight | medium | standard | DONE | yes | skills/slice-land/test_land.py::PrepareBranchFreshnessWarningTests::test_prepare_warns_when_branch_behind_origin_main | main |  |  |
| 002 | bug-registry-invisible | medium | standard | DONE | yes | targeted unittest command in bug record | detached |  |  |
| 003 | node-test-runner-detection | medium | standard | DONE | yes | skills/tdd-loop/test_tdd.py::DetectTests::test_node_via_package_json_test_script | codex/work-on-issue-64 |  |  |
| 004 | terminal-status-legibility | low | standard | DONE | yes | skills/bug-fix/test_bug.py::TerminalSegregationTests::test_escalated_bug_rendered_under_terminal_section | claude/fervent-shannon-da9219 |  |  |
