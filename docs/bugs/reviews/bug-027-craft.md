---
bug: 027
pass: craft
verdict: pass
reviewer: jig:reviewer (subagent a5a31908de45c2c72)
reviewed_at: 2026-08-02T06:22:36Z
prompt_source: review.py pr-review (craft, bug-adapted)
---

VERDICT: pass

The reword drops the unanchored path from both passages and redirects to the
host-agnostic in-project worked example `docs/specs/001-adopt-jig/`. Load-bearing
factual claims check out against source: `workflow.py new` emits `slice-01-tbd.md`;
the template carries the cited frontmatter + DoR/AC/DoD/Close-out; "packaged slice
template" is an accurate path-free description of a template scaffold copies under
`.claude/templates/`. `test_no_unanchored_slice_template_path` is a direct,
non-brittle regression lock; the docstring accurately restates the two-count
defect. Choosing "the packaged slice template" over a concrete path avoids
re-introducing the exact unanchored-path class of bug being fixed.

Nits raised and addressed: step 5's "for each new slice, let `workflow.py new`
emit…" (misread as re-running `new` per slice) reworded to note `new` ran once in
step 2 and further slices follow the same shape; missing relative pronoun fixed
("the worked example that scaffolding installs"). The `assertIn("001-adopt-jig")`
weak-anchor nit is accepted as-is — matches the file's established surface-test
style and is meaningful today (sole occurrence).
