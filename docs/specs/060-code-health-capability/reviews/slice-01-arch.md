---
slice: 060-01 — Python lint, detect-and-drive
pass: arch
verdict: pass
reviewer: arch-review
reviewed_at: 2026-06-05T03:04:14Z
prompt_source: review.py arch-review
---

VERDICT: pass

REASONING:
health.py is a genuine fourth member of the detect-and-orchestrate family: detect → drive → normalize → summarize → degrade with the same 0/1/2 exit contract and .jig/*-command override idiom as tdd.py. The deviation from tdd.py (capture-and-summarize JSON rather than stream) is correctly motivated by spec 057's tight-envelope requirement and the read-only reviewer constraint from ADR-0017. ADR-0017 fidelity is strong — Tier-1 detect-and-drive imposes no tool, PATH→uvx→pipx honors "installs nothing," judgment cleanly deferred to the 060-05 reviewer pass (Principle 1 respected), and the slice avoids horizontal scaffolding for later slices. The resolver/summary shape leaves a clean extension seam for 060-03's multi-ecosystem table.

SPECIFIC ISSUES:
- [strength] health.py:104-127 — ephemeral-runner naming + JSON-parse-with-fallback are factored so a 060-03 ecosystem dispatch table drops into resolve_lint_command without reshaping cmd_check.
- [strength] health.py:141-186 — capture-summarize-then-normalize divergence from tdd.py's stream-through is the right call: the reviewer pass (060-05) consumes a summary, not a transcript, per ADR-0017 §Layering.
- [concern] SKILL.md:99 — markdown link pointed at non-existent adr-0002-extract-helper-on-third-caller.md (real file: adr-0002-contracts-stays-deferred.md). FIXED during review — link now points at the correct file. Broader repo-wide occurrences (ADR-0017:14, slice-05:10) flagged as a separate follow-up.
- [concern] health.py:159 — (FileNotFoundError, OSError)→2 mainly guards the .jig/lint-command override case (resolver already gated on shutil.which); a bad override command → 2 not 1. Intended; pinned by tests.

RECONCILIATION NOTES:
- Record the deliberate tdd.py divergence: health.py captures+summarizes (count + top codes) rather than streaming, because the 060-05 reviewer pass and spec 057's tight-envelope contract need a summary. Family-consistent design choice.
- ADR-0002 link target corrected in SKILL.md during review; repo-wide broken-link sweep deferred to a follow-up task.
