---
slice: 061-01 - committed Claude package + repoint marketplace
pass: craft
verdict: pass
reviewer: pr-review (jig:reviewer)
reviewed_at: 2026-06-05T20:52:22Z
prompt_source: review.py pr-review <slice> 061-01 <deliverables>
---

Clean, idiomatic sibling of build_codex_plugin.py / build_release_zip.py. Genuinely reuses release-zip exclusion predicates + include sets by reference (not restated), pinned by an identity test; mirrors codex _validate_output_dir (widened to allow hosts/); adds a clean positive validate_claude_package helper. Tests cover every AC + both edge cases with real fixtures.

Nits (non-blocking):
- _is_relative_to copy-pasted from build_codex_plugin.py (second caller; ADR-0002 rule-of-three not tripped — extract on third use).
- Committed hosts/claude/ has no byte-equality-vs-build assertion; regenerate-and-diff guard deferred to 061-03 (recorded in deviation log).
- _iter_package_files returns sorted(...) vs the sibling generator shape — harmless.
