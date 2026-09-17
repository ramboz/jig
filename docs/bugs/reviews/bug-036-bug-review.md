---
bug: 036
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent
reviewed_at: 2026-09-17T17:13:26Z
prompt_source: review.py bug-review
---

Verdict: pass (round 4 of 4).

Scope: root-cause rigor, repository/call-site closure, hook contract, quoting,
version selection, Python 3.9 compatibility.

Round 1 raised a blocker: the claimed call-site closure was incomplete. The
builder pre-rendered `.md.template` files with the in-repo transform, so the
packaged `lightweight-decisions.md.template` carried `.github/skills/...` and a
plugin-mode scaffold emitted the same unresolvable helper path the bug is
about, in a second artifact. Also raised a should-fix: the fresh-shell
bootstrap hardcoded `~/.copilot`, bypassing the locator's own `COPILOT_HOME`
support, and parsed `ls` (not space-safe).

Round 2 confirmed the template call site now preserves the structural fix, the
bootstrap honours `COPILOT_HOME` and spaced paths, and the locator rejects
non-object manifests; one should-fix remained on the stale `_copy_templates`
docstring, which still described the removed render step and could have
reintroduced the regression.

Round 3 confirmed the docstring and the non-vacuous canonical-source test; one
nit remained on `_copy_runtime_scripts`'s stale allowlist description.

Round 4: all findings resolved. The fix is structurally complete, the template
and fresh-shell call sites are closed, the regression tests cover actual
resolution invariants rather than spelling, and the documented runtime-script
allowlist matches the packaged files. `fix_class: structural_fix` is honestly
labelled — the change removes the mode-conflation at its source rather than
patching the rendered output.
