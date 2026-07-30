---
bug: 015
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T05:13:33Z
prompt_source: craft review of bug 015 deliverables (scaffold.py, test_scaffold_mode.py, bug records 015/016)
---

Independent craft review of the bug 015 fix, by a fresh reviewer.

**Round 1: `needs-changes`** — one blocker, six nits. All addressed.

Judged sound: `pre_render`/`post_render` are named against the module's own
`render()` so the ordering contract is self-describing; the docstring states the
trap explicitly; `_render_brief` needed no signature churn; and the mangle guard
was independently confirmed to fail under the obvious `post_render=doc_rewrite`
fix.

**Blocker — a newly-live path with no test.** `test_claude_host_brief_and_seed_
are_unchanged` ran `--plugin-only` only, where `host_rewrite` is `None`. But the
change makes the *other* Claude arm newly reachable: under `--with-machinery`,
`_rewrite_skill_md_paths` now fires pre-substitution on the brief and seed,
where it never did. Inert against today's templates (neither carries the
`${CLAUDE_PLUGIN_ROOT}/skills/` pattern) — but the seed's whole job is to
describe jig machinery, so it could grow one. Now runs both modes via
`subTest`.

**Nits, all applied:**

- `host_rewrite = doc_rewrite` was an alias whose correctness depended on
  sitting above a later reassignment — temporal coupling defended by a 7-line
  comment. Inverted: `host_rewrite` is assigned from the host branch and
  `doc_rewrite` derived from it, so `doc_rewrite` is assigned once and the
  comment shrinks to two lines.
- The "blanket `Claude` → `Codex` must not reach `PROJECT_NAME`" rationale was
  stated in full four times. Canonical statement kept in `copy_template`'s
  docstring; the other three reduced to pointers.
- The mangle test used an ad-hoc `tempfile.mkdtemp` + `try/finally` + a local
  `import shutil` (already imported at module level) while its sibling used the
  class's `setUp`/`tearDown` tmpdir. Two idioms for one need, in one commit —
  now one.
- `copy_template`'s parameter order was the inverse of execution order. No
  caller passes them positionally, so reordering to `pre_render, post_render`
  was free.
- Two paragraphs of the record narrated the review process rather than the
  defect. Facts kept, meta-commentary cut.
- The Claude control test lives in `CodexScaffoldAdapterTests`; flagged as a
  naming mismatch. Kept there — it is the control arm of the same host-parity
  gate and splitting it would separate the two halves of one assertion — but
  its docstring now says so explicitly.

**Reconciliation notes acted on:** the Proof now names *which* Claude mode was
compared (in-repo — the arm this change makes newly reachable), and a stale
`scaffold.py:195-197` line citation inside `## Fix`, which post-fix points at
different lines, was replaced with a symbolic reference.

**Round 2 (this verdict): pass.** Full suite: 3690 tests OK, pyright clean.

Proportionality noted: bug 015's record is long, but within this repo's range
(bug 013 = 222 lines, 011 = 341, 014 = 656). Bug 016 is short and honest.
