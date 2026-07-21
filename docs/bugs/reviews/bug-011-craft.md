---
bug: 011
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-16T21:29:05Z
prompt_source: skills/independent-review/SKILL.md (craft pass, bug 011)
---

Independent craft pass — **pass** on the sixth round. Per ADR-0014 §4 this file holds the
*operative* verdict; the five earlier `needs-changes` rounds live in git history.

## Verdict basis (round 6)

"Both pass-5 blockers are genuinely fixed, not reworded… hosts/ is line-for-line identical to
source across all three changed files; test references, ADR-0010 amendments, and both parked
residuals all resolve. The five deviations are proportionate and the record's length tracks its
gnarly tier." No blocking issues.

## What the rounds found and fixed

1. **Dead comments shipping to both hosts** — six comments described the deleted behaviour,
   worst at `jig-decision-capture.sh:11-12`, the first thing a reader of the changed hook sees.
   Scaffolded projects would have received comments contradicting their code.
2. **Docstrings narrating change history** rather than stating constraints — 8 of 11 lines in
   `flag_duplicates` were bug-record prose. Trimmed to the load-bearing constraint.
3. **`duplicate_note` breached `conventions.md:51-53`** (~45 words on a hook message that fires
   every Stop — context × turns, spec 055). Compressed to ~20.
4. **The containment rule existed in three near-copies**, in two styles, handling the
   empty-token-set edge differently — and the tell was that the docstrings had to *say* they
   mirrored each other. Extracted to `is_contained()` / `token_sets()`; the hedge is gone and
   the mirror that propagated the original defect cannot drift again.
5. **`hosts/` was never rebuilt after the craft fixes** — so the artifacts that actually install
   still carried every stale comment, while the record claimed drift-green. Root cause named by
   the reviewer: regeneration belongs after the *last* source edit, not the first.
6. **Patched-over prose** — a correction jammed into a spec sentence as an em-dash clause leaving
   an orphaned fragment; later, a reworded blockquote whose seam moved rather than closed.
   Rewritten and rewrapped.
7. **Review-process residue in the record** — the same fact stated three times, drafting history,
   and a "Method note" that (ironically) carried a stale citation while preaching citation
   discipline. Cut; its transferable lesson moved to `docs/memory/learnings.md`.
8. **The `git stash` rule breach** — surfaced here, disclosed as deviation 5 rather than
   reworded away. Assessed round 6: "teaches the rule rather than the move."

Verified at round 6: `hosts/` byte-identical to source; zero `###` subsections (sibling
convention); test counts exact (19 + 24 + 11); deviations proportionate.
