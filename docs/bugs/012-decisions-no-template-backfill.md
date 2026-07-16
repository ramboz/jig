---
status: DONE
tier: standard
severity: medium
claimed_by: claude/session-a2-decisions-template-7c3341
regression_test: skills/memory-sync/test_decisions.py::SeedFromTemplateTests::test_missing_file_is_seeded_and_entry_appended
main_repro_checked_at: 2026-07-16
main_repro_ref: origin/main@91427b4
main_repro_result: reproduces
red_confirmed_at: 2026-07-16
green_confirmed_at: 2026-07-16
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 012: decisions-no-template-backfill

Reported upstream as [#109](https://github.com/ramboz/jig/issues/109) **finding 1**
(from food-log, jig 2.7.0). Sibling of bug 011
(`011-decision-dedup-suppresses-reversals`, #109 finding 2, ROOT_CAUSED on
`claude/bug-011-decision-dedup-reversals`). The two are independent: #109's control
experiment showed finding 2 reproduces identically in jig's own template format, so
this fix does not address it and bug 011 does not address this. Numbered 012, not
011, because 011 is already taken on that unmerged branch and `bug.py new` cannot
see it (see `## Already tried`).

## Symptom

`decisions.py add-lightweight` — the documented recording path for
`docs/decisions/lightweight-decisions.md` — fails permanently and unrecoverably in
any project scaffolded before the lightweight-decisions feature landed. It has two
consecutive failure modes and neither names a way out:

1. **File absent** → `FileNotFoundError`, telling the agent to run `scaffold-init`,
   which a scaffolded project cannot re-run.
2. **File present but hand-rolled** → `ValueError: … missing its '## Entries'
   heading`, naming the missing heading but no remedy.

Mode 2 is *caused by* mode 1: the Stop-hook nudge hands the agent a bare file path
with no shape, so the agent creates the file freehand in a format the helper then
refuses forever. In the reporting project the helper recorded **zero** successful
writes across its entire jig lifetime, with no signal that anything was wrong.

## Repro

Both modes, against this repo's `decisions.py` (verified 2026-07-16):

```bash
# Mode 1 — a project with no lightweight-decisions.md (pre-LD-feature scaffold)
mkdir -p /tmp/repro/nofile/docs/decisions
python3 skills/memory-sync/decisions.py add-lightweight \
  --title probe --decision probe --project-dir /tmp/repro/nofile
# error: no docs/decisions/lightweight-decisions.md — scaffold the
#        lightweight-decisions home first (jig:scaffold-init seeds it)
# exit=1

# Mode 2 — a hand-rolled LD table, the format an unguided agent actually writes
mkdir -p /tmp/repro/foreign/docs/decisions
printf '# Lightweight Decisions\n\n| ID | Date | Decision |\n|----|------|----------|\n| LD-1 | 2026-07-15 | Something durable |\n' \
  > /tmp/repro/foreign/docs/decisions/lightweight-decisions.md
python3 skills/memory-sync/decisions.py add-lightweight \
  --title probe --decision probe --project-dir /tmp/repro/foreign
# error: docs/decisions/lightweight-decisions.md is missing its `## Entries`
#        heading — cannot place the entry
# exit=1
```

Both reproduce verbatim. Mode 2 raises before writing, so the file is untouched —
confirmed by re-reading it after the run.

## Evidence

- `skills/scaffold-init/scaffold.py:2515` — `for src in docs_template_root.rglob("*.md.template")`
  seeds the docs tree, picking up `templates/docs/decisions/lightweight-decisions.md.template`.
  This runs at **init only**. A plugin upgrade does not re-run it, so a project
  scaffolded before the feature existed never receives the file.
- `skills/migrate/migrate.py` — subcommands are `report`, `rename-decisions`,
  `split-slices`, `copy-machinery`, `adopt-layout`. **None** seeds the LD home, and
  `report` does not flag its absence. There is no backfill path anywhere in the
  plugin.
- `skills/memory-sync/decisions.py:121-124` — refuses to create the file, by design
  ("it is seeded by scaffold-init / Phase 1; this helper does not create it").
- `skills/memory-sync/decisions.py:129-132` — hard-gates on `## Entries` with a
  message that names the missing heading but neither the expected shape nor any
  command that would produce it.
- `hooks/scripts/lib/decision_scan.py` `render_summary()` — the Stop nudge says
  "record durable ones in `docs/decisions/lightweight-decisions.md` (lightweight)".
  It names a **path** and nothing else: not the helper, not the required shape. An
  agent told only a path invents a format.
- Field evidence from #109: an agent created the file freehand as an `LD-N` markdown
  table (food-log `9392d79`, 2026-07-15). Every entry since was hand-written.

## Hypotheses

- [ ] H1: The template is orphaned — never wired into any scaffold path, so no
      project ever receives it. Falsify by grepping scaffold.py for the docs-template
      walk. **Falsified:** `scaffold.py:2515`'s `rglob` picks it up; greenfield
      scaffolds do get the file correctly. (#109 nearly filed this — a name-grep for
      the template returns zero hits because the walk is recursive and unnamed.)
- [x] H2 (leading): Seeding is **init-time only** and no upgrade/backfill path exists,
      so pre-feature projects never receive the file; `decisions.py`'s deliberate
      refusal-to-create then converts a recoverable gap into a permanent hard failure,
      and the shapeless nudge converts that into a divergent hand-rolled format.
      Confirm by checking every migrate subcommand for a seed op and re-running both
      repro modes. **Confirmed** — see Evidence.
- [ ] H3: The `## Entries` gate is simply too strict; the helper should degrade and
      append under a created heading. Falsify by asking what happens to a user's
      hand-rolled file. **Rejected as the fix** (not as a description): #109's own
      comment notes `## Entries` is a gate, not an anchor — `decisions.py:135` appends
      at end-of-file regardless. So degrading is *easy*, which is the trap: it would
      silently graft jig-shaped entries onto a foreign document the owner wrote
      deliberately, splitting the record across two formats with no signal. That is
      the same silent-divergence failure this bug is about, moved one step later.

## Root cause

Two defects compound, and neither is the error message itself:

1. **No backfill.** The LD home is seeded exclusively by `scaffold-init`'s init-time
   template walk (`scaffold.py:2515`). Upgrades don't backfill and `migrate.py` has no
   seed op, so every project scaffolded before the feature landed is permanently
   without the file and cannot tell.
2. **A shapeless nudge plus a create-refusal.** `render_summary()` names a path but no
   shape or command, so the agent hand-rolls a format; `decisions.py` then refuses to
   create (mode 1) and refuses the hand-rolled result (mode 2), each with a message
   that states a fact rather than a remedy.

Per the diagnostic question: the *output* is "the helper errors". The *process that
created the output* is "jig tells an agent where to write but never what shape, and
provides no way to obtain the shape". Fixing only the error text would leave the
backfill gap and the shapeless nudge intact — the treadmill.

## Fix class

structural_fix — closes the missing backfill path and gives the nudge the shape it
never carried, rather than softening the symptom at the point of failure.

**Honest scope (bug-review follow-up):** structural for **plugin-mode** installs,
which is the reported configuration (#109 ran
`~/.claude/plugins/cache/jig/jig/2.7.0/skills/memory-sync/decisions.py`). It does
**not** close the Claude scaffold-mode variant — see `## Remaining risk`.

## Remaining risk

**Claude scaffold mode (copied machinery) still cannot seed.** `copy_machinery`
copies `skills/` and `hooks/` but not `templates/` — only Codex copies templates
(`scaffold.py` `_copy_codex_templates`). A copied helper at
`<project>/.claude/skills/jig-memory-sync/decisions.py` resolves `parents[2]` to
`<project>/.claude`, which has no `templates/` tree, and `CLAUDE_PLUGIN_ROOT` is
unset in that mode. Verified (**pre-mitigation capture** — the message now also
names the two remedies below):

```
$ env -u CLAUDE_PLUGIN_ROOT python3 .claude/skills/jig-memory-sync/decisions.py \
    add-lightweight --title probe --decision probe --project-dir .
error: lightweight-decisions template not found: <project>/.claude/templates/docs/decisions/lightweight-decisions.md.template
```

Scope of the risk:

- **Not a regression.** That mode failed before this fix too (`FileNotFoundError:
  no docs/decisions/lightweight-decisions.md`). This changes which message it
  fails with, not whether it fails.
- **Inherited, not invented.** `adr.py` resolves its template the same way
  (`adr.py:73-81`) and has the identical gap. Closing it properly means deciding
  whether `copy-machinery` should ship `templates/` (Codex parity) or whether
  record helpers should embed their templates — a design call with blast radius
  across both helpers and every scaffolded project's `.claude/` contents.
  **Deferred to the maintainer; asked on
  [#109 (comment)](https://github.com/ramboz/jig/issues/109#issuecomment-4996295388)**
  and parked in [refinement-todo.md](../refinement-todo.md) so the question
  outlives this branch.
- **Mitigated, not hidden.** The failure now names two remedies that demonstrably
  work in that mode — set `CLAUDE_PLUGIN_ROOT` to a jig root (verified: seeds and
  records), or run `migrate.py seed-decisions` from a jig install. Covered by
  `UnreachableTemplateTests`.

## Fix

Four changes, one per surface named in the root cause (all pre-endorsed in #109's
"Suggested fixes" 1/2/3):

1. `decisions.py` seeds `lightweight-decisions.md` from
   `templates/docs/decisions/lightweight-decisions.md.template` when absent, then
   proceeds with the append — following `adr.py`'s established precedent for a
   `docs/decisions/` record helper resolving its template from the plugin root
   (`Path(__file__).resolve().parents[2] / "templates" / ...`).
2. When the file exists but lacks `## Entries` (foreign format), **keep failing and
   write nothing** — but name the expected shape *and* the `migrate seed-decisions`
   remedy in the message. Deliberately not fix #4 (degrade/append): see H3.
3. `migrate.py` gains `seed-decisions` (idempotent, `--dry-run`), and `report` flags
   the gap when the LD home is missing.
4. `render_summary()` names the helper command and the required `### <date> — <title>`
   shape, not just the path. **Host-neutral by construction** — it names
   `decisions.py add-lightweight`, not a plugin-root path: this string is agent-facing
   in every install mode and a `${...PLUGIN_ROOT}` literal resolves in only one of
   them (scaffold installs leave it unset; the host packages use different roots), so
   a literal would hand the agent an unusable path — this bug's own failure shape, one
   surface later. Sibling hooks resolve modes at runtime via `SCRIPT_DIR` for the same
   reason. Guarded by `test_summary_command_is_host_neutral`.

Parity surfaces the four changes drag along (not scope creep — the same claim
mirrored in more than one place; recorded per the bug-review's reconciliation note):

5. `skills/migrate/SKILL.md` — `seed-decisions` op docs + frontmatter description
   (five → six subcommands).
6. `skills/memory-sync/SKILL.md` — the helper now seeds; "never hand-write the file".
7. `skills/scaffold-init/scaffold.py` (`CodexScaffoldRenderer`, ~:1095) — the Codex
   render of migrate's SKILL.md **string-matches** the subcommand-list block and is
   anchored on the literal "exposes five subcommands:". Renaming it to "six" silently
   broke the match and leaked un-rewritten `--host claude` text into the Codex render;
   caught by `CodexCopyMachineryTests`, not by review.
8. `hosts/claude/` + `hosts/codex/` — regenerated via `scripts/build_host_packages.py`
   (the committed host packages mirror `skills/` and `hooks/`).

Bug-review follow-ups folded in (all covered by new tests):

- Validate `--title`/`--decision` **before** seeding, so a rejected CLI call cannot
  leave a record home behind with no signal.
- Report the seeded path through `project_layout`, not the hardcoded
  `docs/decisions/…`, so a `layout.docs_root: "."` corpus (spec 084) is reported
  where the file actually lands.
- Run the `## Entries` format gate **before** the idempotency no-op, so a foreign
  file carrying a matching `### <date> — <title>` heading fails loud instead of
  returning a silent "already recorded".
- The unreachable-template failure names two working remedies (see Remaining risk);
  `migrate.py`'s equivalent message matches, so a user following `decisions.py`'s
  remedy 2 into a copied `migrate.py` isn't stranded on a bare "not found".
- `_foreign_format_error` reports through `project_layout` too — the first pass fixed
  only the success path, leaving the *error* path naming `docs/decisions/…` for a
  spec-084 `docs_root: "."` corpus (i.e. naming a file that doesn't exist). Caught by
  both review passes; covered by
  `test_error_names_the_real_path_under_track_local_docs_root`.
- The nudge is host-neutral (see Fix item 4) — the craft pass caught that the first
  version emitted the only `${CLAUDE_PLUGIN_ROOT}/skills/…` literal in all of
  `hooks/`, resolving in Claude plugin mode alone.
- A drift guard ties the nudge's taught format to the shipped template
  (`test_summary_entry_shape_matches_the_shipped_template`): the nudge restates a
  contract the template owns, and nothing connected them.

**Knowingly accepted, not overlooked:** `_cmd_add_lightweight` calls
`seed_lightweight` and `_require_entry_fields` which `add_lightweight` then calls
again. Both are idempotent (an `exists()` check and two truthiness checks), and the
CLI needs the seed signal to *report* the creation — a file appearing silently is the
failure this bug is about. Collapsing it would mean returning `(seeded, appended)`
from `add_lightweight`, changing a public helper's contract for a cosmetic gain.
Raised by the craft pass, discussed, kept.

## Already tried

- **`bug.py new` allocated 011, colliding with the existing bug 011.**
  `_next_number()` (`bug.py:143`) globs the local `docs/bugs/` and returns
  `highest + 1`; bug 011 lives only on an unmerged branch, so the allocator cannot
  see it and hands out 011 again. `--push` does not help — it reserves against
  `origin/main`, which also stops at 010, so it would reserve 011 *onto main* and
  collide head-on. There is no `--number` flag. Renamed the record to 012 by hand and
  patched the `# Bug NNN:` header. A gap at 011 is harmless if that branch is
  abandoned; two records numbered 011 corrupts the board. Left the allocator alone —
  out of scope for this bug.

## Regression test

Primary (the `regression_test:` field, witnessed red→green by the `bug.py` gate):
`skills/memory-sync/test_decisions.py::SeedFromTemplateTests::test_missing_file_is_seeded_and_entry_appended`

Full set added by this fix:

| Test | Covers |
|---|---|
| `SeedFromTemplateTests` (7) | mode 1 — absent file is seeded from the template; parent dirs created; seeded body is the shipped template verbatim; seed→append round trip |
| `ForeignFormatTests` (7) | mode 2 — loud refusal naming shape + remedy; file never rewritten; gate precedes the idempotency no-op; names the real path under `docs_root: "."` |
| `UnreachableTemplateTests` (2) | scaffold-mode template gap fails with working remedies, writes nothing |
| `CliOrderingTests` (1) | a rejected CLI call cannot seed as a side effect |
| `SeedDecisionsTests` (8) | `migrate seed-decisions`: creates, idempotent, `--dry-run`, refuses foreign, `--docs-root .`, `report` flags the gap and stops once seeded |
| `test_decision_scan.py` (5) | nudge names helper + shape + still names the home; command is host-neutral; taught shape matches the shipped template |

Run: `python3 skills/memory-sync/test_decisions.py` (30 OK) ·
`python3 -m unittest skills.migrate.test_migrate` (155 OK, 1 skipped) ·
`python3 hooks/scripts/lib/test_decision_scan.py` (20 OK)

## Proof

- **Red witnessed** by `bug.py transition 012 FIXING` (`red_confirmed_at: 2026-07-16`),
  which shells to `tdd.py` and refuses an already-green test. Before the fix:
  `test_decisions.py` 2 failures + 8 errors; `test_decision_scan.py` 2 failures;
  `SeedDecisionsTests` 5 failures + 1 error.
- **Green witnessed** by `bug.py transition 012 REVIEWED` (`green_confirmed_at`).
- **Full suite:** 3321 tests OK on `origin/main@91427b4` → **3350 OK** with this fix
  (+29; the source tests plus their `hosts/` mirrors). No pre-existing test was
  weakened; one was deliberately removed (`test_no_file_raises`) because this fix
  reverses the contract it asserted. *(An earlier draft of this section said 3342/+21
  — the count from before the review-follow-up tests were added. Caught by the craft
  pass: a record whose thesis is "jig shipped a claim nobody verified" has no business
  carrying a stale total.)*
- **Original repro, re-run after the fix** (the #109 probe that had never once
  succeeded):
  ```
  $ python3 skills/memory-sync/decisions.py add-lightweight \
      --title probe --decision probe --project-dir <fresh-project>
  seeded docs/decisions/lightweight-decisions.md from jig's template (this project had none)
  recorded lightweight decision in docs/decisions/lightweight-decisions.md: probe
  ```
- **Known flake, not caused by this change:** `run_tests.py` prints
  `ERROR: committed host packages are stale … hosts/claude/.claude-plugin/plugin.json`
  while the suite reports OK. `plugin.json` is byte-identical to committed here
  (`git diff` clean) and the drift guard passes in isolation (13 tests OK). This is
  bug 008 (`flaky-host-package-drift-guard`, REPORTED, unrooted).

## Learning

Recorded in [docs/memory/learnings.md](../memory/learnings.md) — "Bug 012: an
init-time-only seed is a permanent gap for every existing project".

## Main recheck

- 2026-07-16 - `origin/main@91427b4` -> reproduces: Detached worktree at origin/main@91427b4. Mode 1 (no LD file): 'add-lightweight --title probe --decision probe' -> exit 1, 'error: no docs/decisions/lightweight-decisions.md — scaffold the lightweight-decisions home first'. Mode 2 (hand-rolled LD table): same command -> exit 1, 'error: docs/decisions/lightweight-decisions.md is missing its `## Entries` heading — cannot place the entry', file left untouched. migrate.py on main offers only {report,rename-decisions,split-slices,copy-machinery,adopt-layout} — no seed op. All three confirmed.
