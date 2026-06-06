---
slice: 061-05 - symmetric install + scaffold docs
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-06T01:54:56Z
prompt_source: review.py pr-review <spec> 061-05 <docs>
---

VERDICT: pass

The README/CONTRIBUTING rewrite is clear, internally consistent, and command-accurate.

- All intra-doc anchors resolve (`#codex-distribution`, `#repository-structure-for-contributors`; cross-doc `CONTRIBUTING.md#local-dev-install`, `docs/adoption-readiness.md#choosing-an-install-shape`, `README.md#install-shapes`). No broken anchors.
- Install commands consistent across the Install-shapes table, Codex Distribution, and CONTRIBUTING: Codex uniformly `codex plugin marketplace add hosts/codex` → `codex plugin add jig@jig`; release zips uniformly `build_release_zip.py --host claude|codex`. The table's `<extracted-dir>` zip-extract variant is correctly scoped, not a contradiction.
- Test craft sound: class names map 1:1 to ACs + edge + inverse guards; descriptive failure messages; `\b`-anchored regex avoids matching `hosts/codex/plugins/...`; the repo-root-scaffold inverse guard doesn't false-positive on `hosts/...`/`${PLUGIN_ROOT}/...`. All four inverse guards verified to fail if stale text returned.

BLOCKERS: none

NOTES:
- Inverse guards read the live docs (regression tripwires, the intended doc-guard pattern) rather than fixtures — by design.
