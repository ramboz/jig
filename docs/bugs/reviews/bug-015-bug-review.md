---
bug: 015
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T04:54:09Z
prompt_source: review.py bug-review docs/bugs/015-codex-brief-seed-claude-md-leak.md skills/scaffold-init/scaffold.py skills/scaffold-init/test_scaffold_mode.py
---

Independent bug-review of the fix for bug 015, run by a fresh reviewer with no
access to the implementation conversation.

**Round 1: `needs-changes`.** The code fix passed on every axis the pass exists
to test — root cause not symptom, correct ordering (`pre_render` on the raw
template, verified against `copy_template`'s substitute-then-post-render
sequence), both guard tests shown to have teeth, host mirrors regenerated, and
the Claude-host no-op claim verified statically (neither the brief nor the seed
templates contain the `${CLAUDE_PLUGIN_ROOT}/skills/` pattern that the Claude
transform touches).

What blocked was **record integrity**, not code. Five findings, all fixed:

1. **The adjacent defect had no tracked artifact.** The record said the
   `Claude-Tools` → `Codex-Tools` primer mangle "deserves its own record" — and
   then no record existed, in the bug board or the inbox. That makes it a
   silently-shipped known bug wearing the language of a deferral. Now filed as
   bug 016 with repro, evidence, and a leading hypothesis; 015 links to it.
2. **`green_confirmed_at` was hand-written while status was `FIXING`.** That
   field is stamped by the REVIEWED gate (`bug.py`) and by nothing else, so a
   hand-set value asserts a machine-witnessed fact that no machine witnessed.
   Cleared; the gate stamped it on the real transition. This is precisely the
   failure mode jig's faithful-recording work exists to prevent, found in a
   record whose own Proof section is about witnessing red and green.
3. **The Proof understated the diff.** It named one changed line; the real diff
   is seven, including two `.claude/` → `.codex/` rewrites in the seed that the
   `CLAUDE.md`-only repro grep never saw. Corrected, with the reason noted: a
   fix whose true diff is wider than its symptom search is how scope gets
   under-reported.
4. **A regression test could go vacuous silently.** `_seed_and_brief_text`
   globbed the seed directory; had seed emission regressed, the glob would be
   empty and the `AGENTS.md` assertion would still pass off `brief.md` alone.
   Now asserts the directory exists and the file list is non-empty.
5. **"the transform the other paths already receive" overstated it.** Only the
   host half is threaded, not the layout half — so the brief's hard-coded
   `docs/…` links remain wrong under a non-default `docs_root` (pre-existing,
   out of scope). Reworded to say "host half" and to name what stays broken.

**Round 2 (this verdict): pass.** All five addressed. Full suite green.

**Standing limitation, stated rather than closed:** bug 016 is open and
unfixed. A Codex project named after Claude still has its name rewritten in
`AGENTS.md` and the `docs/` tree. Bug 015's guard test covers only `brief.md`
and the seed spec, so nothing under test names that gap — which is why it
carries a record instead of a comment.
