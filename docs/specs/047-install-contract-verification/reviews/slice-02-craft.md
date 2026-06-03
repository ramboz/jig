---
slice: 047-02 - scaffold-contract-validator
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-03T00:04:53Z
prompt_source: review.py pr-review 047-02
---

VERDICT: pass

REASONING:
A clean, well-scoped parallel of the 047-01 plugin contract: a pure, stdlib-only, diagnostics-returning validator with strong reuse (`install_contract._iter_hook_commands`, the restate-plus-consistency-test tier-table convention) and no duplication of the sibling module. Correctness is sound — the validator's regexes match the scaffold's actual rewrite shape (`[A-Za-z0-9_-]+` skill names, `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` local helpers), the stale-path vs prose-mention distinction is deliberate and tested, and the manifest/settings checks enforce real invariants (ADR-0007 tier coherence, scaffold-mode command shape, dangling script references). Tests exercise every AC with both unit fixtures and a real end-to-end scaffold, asserting diagnostic content (offending path + rule), not just presence.

SPECIFIC ISSUES:
- [strength] scripts/scaffold_contract.py:135-145 — regexes pinned to the exact shape scaffold.py `_rewrite_skill_md_paths` produces; stale-path detector scoped to the path-shaped `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` form (not the bare token), so legitimate prose mentions don't false-fail. Covered by `test_prose_plugin_root_mention_is_tolerated`.
- [strength] scripts/scaffold_contract.py:298-300 — reusing `install_contract._iter_hook_commands` via a synthesized jig-managed-only view is the right DRY move; non-jig entries correctly out of scope.
- [strength] scripts/test_scaffold_contract.py:591-643 — `RealScaffoldContractTests` runs the actual generator into a temp dir; strongest possible guard that the contract encodes the intended (spec-046-coordinated) output, not a drift-prone hand-built fixture.
- [strength] scripts/verify_install.py:513-546 — seed-coupling of the `docs` check in `run_completion_summary` (gate on `seed_expected`) is a subtle correctness call that avoids false-failing a legitimate non-greenfield scaffold; documented inline.
- [nit] scripts/scaffold_contract.py:445 — `_MD_LINK_RE` truncates a link target containing `)` and doesn't handle angle-bracket (`[x](<path>)`) or reference-style (`[x][ref]`) links. Low risk for local relative-path targets; docstring scopes the check honestly.
- [nit] scripts/scaffold_contract.py:514,529 — `doc.read_text()` uses platform-default encoding rather than explicit `encoding="utf-8"`. Mirrors `install_contract`'s same habit (consistency-preserving), but explicit UTF-8 would harden against CI locale surprises.

RECONCILIATION NOTES:
Both nits minor and non-blocking — log, don't gate REVIEWED. The Markdown-link regex limitation and the implicit `read_text()` encoding are reasonable follow-up polish; the encoding habit is inherited from the 047-01 sibling module, so if tightened it should be tightened in both `scaffold_contract.py` and `install_contract.py` together. No scope deviations: the four ACs map cleanly onto four public helpers, checks wired into `_SCAFFOLD_CHECKS`, and the restate-plus-consistency-test convention is faithfully extended (`TierTableConsistencyTests` pin against `scaffold._TIER_SKILLS`).

— reviewer: jig:reviewer (read-only, fresh context); craft pass via file-read dispatch to ~/.claude/skills/pr-review/SKILL.md.
