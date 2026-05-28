---
status: DRAFT
skill: scaffold-init
tier: scaffold mode
adr_required: false
---

# Spec 046: Scaffold artifact fidelity

## Overview

Scaffold mode currently produces a mostly complete install, but some
generated artifacts still speak in plugin-root terms or stale repo
metadata. A fresh scaffold verified on 2026-05-27 passed
`verify_install.py --mode scaffold`, but the documented stocktake command
failed because `${CLAUDE_PLUGIN_ROOT}` was unset in the scaffolded
project. The generated docs also contain stale skill naming and the
scaffold manifest records `jig_version: 0.1.0` while the plugin manifest
is at `1.7.0`.

This spec makes scaffold output self-consistent: generated commands,
links, skill names, and version metadata must work from inside the
target project without knowing about the source plugin checkout.

## Goals

1. **Render install-shape-specific docs.** Scaffolded docs and hot-cache
   guidance should point at copied `.claude/` artifacts, while
   plugin-mode docs may keep plugin-root commands.
2. **Remove stale generated copy.** Template text should use the current
   `/jig:vision-elicitation` name and should not refer to already-shipped
   work as future.
3. **Derive version provenance from the manifest.** `scaffold.json`
   should record the source plugin version from
   `.claude-plugin/plugin.json`, not a hard-coded constant in
   `scaffold.py`.
4. **Add scaffold-level verification.** Tests should create a temporary
   scaffold and prove that documented local helper commands, links, and
   version metadata are valid in that target.

## Non-goals

- **No scaffold update/migration skill.** Updating an already-scaffolded
  project is still deferred under spec 016-04.
- **No host-adapter redesign.** This spec improves the current Claude
  scaffold output. Broader Codex portability remains spec 033.
- **No product copy rewrite.** Only generated text that is stale,
  unexecutable, or install-shape-confused is in scope.

## Current state verified 2026-05-27

- `templates/docs/workflow.md.template` documents
  `python3 ${CLAUDE_PLUGIN_ROOT}/skills/scaffold-init/stocktake.py .`;
  the command fails in a scaffolded project because the env var is
  unset and the copied helper lives under
  `.claude/skills/jig-scaffold-init/stocktake.py`.
- `templates/docs/architecture.md.template` contains source-tree
  relative skill links that do not resolve in a downstream scaffold.
- `templates/CLAUDE.md.template` references `/jig:vision-elicit` and
  future work that has already landed.
- `skills/scaffold-init/scaffold.py` hard-codes `JIG_VERSION = "0.1.0"`,
  while `.claude-plugin/plugin.json` declares `1.7.0`.

## Decomposition

**Suggested SPIDR axis: Interface.** The user-facing interface is the
generated scaffold tree. Every generated command or link should be valid
from that tree.

### Slices

1. **`046-01 scaffold-doc-command-rendering`** - Render generated docs,
   commands, links, and skill names for the scaffold install shape, and
   add a temp-project verification fixture.
2. **`046-02 scaffold-version-provenance`** - Derive
   `scaffold.json.jig_version` from the plugin manifest and verify the
   recorded value against the source release metadata.

## References

- [skills/scaffold-init/scaffold.py](../../../skills/scaffold-init/scaffold.py)
- [templates/docs/workflow.md.template](../../../templates/docs/workflow.md.template)
- [templates/docs/architecture.md.template](../../../templates/docs/architecture.md.template)
- [templates/CLAUDE.md.template](../../../templates/CLAUDE.md.template)
- [.claude-plugin/plugin.json](../../../.claude-plugin/plugin.json)
