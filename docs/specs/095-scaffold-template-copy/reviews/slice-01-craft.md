---
slice: 095-01 — claude-scaffold-templates
pass: craft
verdict: pass
reviewer: jig:reviewer (fresh context, round 2)
reviewed_at: 2026-07-17T06:07:32Z
prompt_source: review.py pr-review
---

Round 2 (after fixes). All five round-1 craft findings fixed: the AC2 git
fixture is isolated (`commit.gpgsign=false` + a `shutil.which("git")` guard +
a comment stating why `checkout -b` is load-bearing); `workflow.py`'s docstring
and fallback comment are true again; `docs/architecture.md` reconciled; the
`_rewrite_skill_md_paths` docstring precondition now describes reality for all
three callers; the byte-copy drift guard iterates instead of hand-listing.

Round 2 raised and this addressed: `workflow.py`'s newly-reachable
`read_text()` had no `encoding=` inside an `except OSError`, so a C-locale
scaffold-mode project would crash where it used to degrade cleanly — a
regression this slice would have introduced. Fixed (utf-8 + widened except).
The weak `test_slice_template_is_reachable_...` (a strict subset of AC3, whose
name over-claimed and whose docstring said "three") was replaced with two real
end-to-end tests that run the copied `workflow.py` and `memory.py` and assert
the consumer actually uses the copied template. `migrate.py`'s own `--help` and
`report` Operations text now name templates (SKILL.md alone was not the whole
contract). Review-history narration was cut from the ADR and a test docstring
per the cut-list — the deviation log owns that history.

Explicitly defended and kept: not unifying the two copy functions at n=2
(extract-at-third-caller); the encoding comment naming the Codex sibling's
divergence; `memory.py`'s rewritten degrade message.
