---
slice: 084-03 — scaffold-init `--docs-root` flag + layout-aware output
pass: arch
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T15:24:27Z
prompt_source: review.py arch (084-03); jig:reviewer subagent; 2 rounds
---

VERDICT: pass

Round 1 — needs-changes: the slice enforced ADR-0033's "push-mode in a subtree is
refused loudly" invariant for `workflow.py new` but left `adr.py reserve_adr`'s
push path UNGUARDED — `adr new --push` in a subtree would reserve against a shared
main / write to the enclosing repo root, contradicting the ADR's own language.
The reviewer also noted git_toplevel's workflow.py home made reuse from adr.py
awkward.

Resolution: extracted subtree detection into a new `_common/subtree.py` leaf
(stdlib subprocess/pathlib + project_layout only; no cycle — team_signal.py is the
subprocess-in-_common precedent), exposing `git_toplevel` + `detect_subtree`. BOTH
push doors now call the single `detect_subtree`: workflow._refuse_push_in_subtree
(WorkflowError) and adr.reserve_adr's guard (AdrError), each placed before
worktree routing and gated on `not no_push`. workflow.git_toplevel re-exports
subtree.git_toplevel (behavior unchanged). New test exercises adr.reserve_adr
refusing in a real git-init'd subtree.

Round 2 — pass: the invariant is now enforced symmetrically across both
reservation doors via one detection home; no cycle, leaf discipline intact, no
regression. adr.py duplicates the small refusal *body* (not the detection) so
subtree.py stays free of skill-specific error classes — intentional, not a defect.
Other axes (default inertness, verify_install stdlib-only, rendered-text rewrite)
were sound in round 1.
