---
status: DRAFT
skill: scaffold-init
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 095: Scaffold-template copy

> Reserved on 2026-07-16 via `workflow.py new`.

## Overview

**Record helpers cannot reach their templates in Claude scaffold mode.** jig's
record helpers — `decisions.py` (the lightweight-decisions home) and `adr.py`
(new Architectural Decision Records) — seed their files from
`templates/docs/decisions/…`, resolved as `CLAUDE_PLUGIN_ROOT`, else
`Path(__file__).parents[2] / "templates"`. That fallback reaches the template in
three of jig's four install modes:

| Install mode | Helper lives at | `parents[2]` | Template reachable? |
|---|---|---|---|
| Claude plugin | `<plugin>/skills/memory-sync/` | `<plugin>` | ✅ (env var, and the fallback) |
| Codex plugin | `<plugin>/skills/memory-sync/` | `<plugin>` | ✅ |
| Codex scaffold | `<project>/.codex/skills/jig-memory-sync/` | `<project>/.codex` | ✅ — `_copy_codex_templates` copies `templates/` |
| **Claude scaffold** | `<project>/.claude/skills/jig-memory-sync/` | `<project>/.claude` | ❌ — **no `templates/` tree** |

`copy_machinery` copies `skills/` and `hooks/` into `.claude/`, but not
`templates/`. Only the Codex path copies templates. So a Claude-scaffolded
project — one that carries jig's machinery in-repo rather than as a plugin, with
`CLAUDE_PLUGIN_ROOT` unset — cannot record a lightweight decision or open an
ADR: both helpers fail with a template-not-found error.

This is the gap [bug 012](../../bugs/012-decisions-no-template-backfill.md)
mitigated but could not close. Bug 012 made `decisions.py` seed its record home
from the template instead of failing on an absent file; in Claude scaffold mode
the seed has no template to read, so the fix stops at a loud error naming two
manual remedies. `adr.py` has the identical gap and no mitigation. The question
of how the *family* should reach its templates was parked in
[refinement-todo.md](../../refinement-todo.md) and
[asked of the maintainer on #109](https://github.com/ramboz/jig/issues/109#issuecomment-4996295388)
with three options; **he picked option (a)** — mirror `_copy_codex_templates` on
the Claude side. This spec implements that pick.

## Decision (maintainer's, not this spec's)

**Option (a) — Claude-side template copy.** `copy_machinery` in Claude scaffold
mode also copies `templates/` into `.claude/templates/`, mirroring what
`_copy_codex_templates` already does for `.codex/`. The copied helpers' existing
`parents[2]/templates/` fallback then resolves with **no change to any helper's
template resolution**: `.claude/skills/jig-memory-sync/decisions.py` →
`parents[2]` = `.claude` →
`.claude/templates/docs/decisions/lightweight-decisions.md.template`.

Precisely: no helper's `_plugin_root()` / `_template_path()` logic is touched.
Four helper files do change — comments and error messages that asserted the old
"scaffold mode has no templates" premise are re-premised (`decisions.py`,
`migrate.py`, `workflow.py`, `memory.py`). Prose, not behaviour; but "no helper
changes" as an unqualified claim is false, and the distinction is the point of
the option.

Rejected (recorded in [ADR-0038](../../decisions/adr-0038-claude-scaffold-template-copy.md)):

- **(b) Embed each template in its helper** as a constant plus a drift test.
  Works in every mode and makes `decisions.py` self-contained, but duplicates
  template bodies into helpers (`adr.py` too), and every template edit then has
  two homes.
- **(c) Leave it.** Scaffold mode stays permanently unable to record a decision;
  the reported case (#109) was plugin mode, so the pain stays latent — until it
  isn't.

The cost accepted with (a) is stated plainly: **every scaffolded Claude project's
`.claude/` grows a `templates/` tree** (25 files, ~120 KB), and that is a change
to scaffold output for every install, not just projects that record decisions.

## Assumptions

None unverified. The three claims this spec rests on were each probed on
`main@af53265`:

- Codex already copies templates and rewrites `.md.template` bodies —
  `scaffold.py:1386` `_copy_codex_templates`.
- The Claude copy set today is skills + hooks only — `scaffold.py:1904`
  `copy_machinery`.
- Both record helpers resolve templates via `parents[2]` —
  `decisions.py:73-81`, `adr.py:73-81` (byte-identical `_plugin_root`).

## Decomposition

SPIDR analysis. The change is one mechanical copy behind one existing seam, so
four of the five axes collapse to nothing worth splitting:

- **Spike:** none. The mechanism is already shipped and proven on the Codex side;
  there is no unknown to reduce.
- **Paths:** one — `copy_machinery(host="claude")`. The Codex path already has
  its copy; the plugin path needs none (the plugin root *is* the template home).
- **Interfaces:** none new. No new flag, subcommand, or helper argument; the
  copy rides the existing `--with-machinery` / `migrate copy-machinery` calls.
- **Data:** one tree — `templates/`, copied whole. Splitting it (e.g. "only
  `docs/decisions/`") would make the copy set a second thing to keep in sync
  with the template tree, and would still fail the next helper that grows a
  template.
- **Rules:** one — `.md.template` bodies get the same `${CLAUDE_PLUGIN_ROOT}`
  → copied-path rewrite that SKILL.md bodies and rendered docs already get in
  scaffold mode. Without it, a seeded record would hand a scaffold-mode project a
  command naming a variable that is unset there.

→ **One slice.** A vertical slice here is "a scaffold-mode project can record a
decision", which needs the copy, the rewrite, and both helpers proven end-to-end
together; anything smaller is horizontal phasing.

## Slices

- [095-01 — claude-scaffold-templates](slice-01-claude-scaffold-templates.md)

## Out of scope

- **Retrofitting existing scaffolded projects.** Whether a `migrate
  copy-machinery` re-run should backfill `templates/` into projects scaffolded
  before this spec is a separate question, posted on
  [#109](https://github.com/ramboz/jig/issues/109) rather than decided here.
  Mechanically, a re-run **from a jig install** picks the tree up
  (`copy_machinery` is the same call); a re-run of the project's *own copied*
  `migrate.py` does **not** — probed, see
  [ADR-0038](../../decisions/adr-0038-claude-scaffold-template-copy.md) Open
  questions. So this slice fixes every project scaffolded after it, and leaves
  the existing ones to that question.
- **Helper resolution changes.** The point of option (a) is that the existing
  `parents[2]` fallback resolves unchanged; an edit to `_plugin_root()` /
  `_template_path()` in this slice would mean the copy is not doing its job.
  (Helper *prose* does change — see the Decision section.)
- **Bug 011 / the dedup fix class**, and the capture-rewrite design work
  ([#108](https://github.com/ramboz/jig/issues/108)) — unrelated.
