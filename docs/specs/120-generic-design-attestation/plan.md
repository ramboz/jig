# Plan: Generic design attestation

1. Preserve the existing public review/lifecycle rail and selectively transplant
   the strict reader, static validator and public wiring from effort union
   `43fcc30216cafc8caa8ee01b1688d6f86dff2666`. Do not transplant its history,
   private proof exports or closed records.
2. With TDD, replace the pilot validator with explicit retirement, retain
   bounded static semantics, and pin the successor's actual generic runtime
   closure. Add two different non-card supported-profile fixtures and public
   boundary controls. Synthetic prerequisite reviews are test setup only.
3. Update live public instructions and architecture, regenerate packages, and
   verify source/installed/vendored behavior using existing runners.
4. Run independent compliance, craft, architecture and reconciliation reviews;
   record actual verdicts, address findings, complete lifecycle and prepare
   one ready-for-review replacement PR against main.

No changes to old PRs, old worktrees, main or accepted/DONE records. No
producer/evaluator invocation, real-app certification or schema relabelling.

Actual native-profile recovery stayed within this boundary: explicitly pinned
directory/file interpreter aliases and the existing frozen static-plus-scalar-
quality roster required bounded readback corrections. Fresh test-only native
epochs were checked against reviewed source/evaluator commits; original
acquisition claims and older epochs were preserved, not retroactively approved.
