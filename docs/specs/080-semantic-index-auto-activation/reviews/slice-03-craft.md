---
slice: 080-03 - Codex adapter activation
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-22T03:50:44Z
prompt_source: python3 review.py pr-review docs/specs/080-semantic-index-auto-activation/spec.md 080-03 <080-03 deliverables>
---

VERDICT: pass

REASONING: The two prior blockers are fixed: Codex scaffold template copies now render `.md.template` files through `CodexScaffoldRenderer.rewrite_skill_md_paths`, and the generated Codex host copy carries the same fix. `scripts/build_codex_plugin.py` now only permits the canonical in-tree host output `hosts/codex/plugins/jig`, so `hosts/claude` is no longer deletable through the builder. Nearby regression tests cover both paths, and no new craft blocker was found in the touched areas.

SPECIFIC ISSUES: None

RECONCILIATION NOTES: [strength] `skills/scaffold-init/test_scaffold_mode.py:1260` pins project-local Codex template rendering; [strength] `scripts/test_codex_plugin_packaging.py:312` protects sibling host outputs with a sentinel.
