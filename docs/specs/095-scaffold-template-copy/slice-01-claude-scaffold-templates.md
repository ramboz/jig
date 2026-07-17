---
status: DONE
dependencies: []
last_verified: 2026-07-16
arch_review: true
# design_review: true  # set true when this slice ships UI gated by an external
#                      # design-fidelity eval (attest-only; ADR-0014/0022).
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 095-01 — claude-scaffold-templates

**Goal:** A Claude-scaffolded project with `CLAUDE_PLUGIN_ROOT` unset can record
a lightweight decision and open an ADR — because `copy_machinery` brought
`templates/` with the machinery, so the copied helpers' existing `parents[2]`
fallback resolves.

`arch_review: true` — this widens `copy_machinery`'s copy set, which is the
contract every scaffolded Claude project's `.claude/` tree is built from. The
option was the maintainer's call (spec Overview); the review pass is for the
*implementation* of it, not for re-litigating the choice.

**DoR:**
- ✅ Bug 012 is DONE — `decisions.py` seeds from the template (this slice makes
  that seed reachable in the fourth install mode).
- ✅ The maintainer picked option (a) — relayed verbally via Marie-Rose,
  recorded in the spec Overview and [ADR-0038](../../decisions/adr-0038-claude-scaffold-template-copy.md).
- ✅ `_copy_codex_templates` exists as the mirror to follow (`scaffold.py:1386`).

**Acceptance Criteria:**

1. **A scaffold-mode project can seed its record home with no plugin root.**
   After `scaffold.py --with-machinery <project>`, with
   `docs/decisions/lightweight-decisions.md` **absent** — the shape of every
   project scaffolded before that template shipped, which is bug 012's mode 1
   and the case #109 reported — running the *copied*
   `.claude/skills/jig-memory-sync/decisions.py add-lightweight` with
   `CLAUDE_PLUGIN_ROOT` **unset** exits 0, seeds the record home from the
   copied template, and appends the entry.

   (The absent-home precondition is load-bearing, not test convenience: a
   *fresh* scaffold seeds the record home at install time, so `add-lightweight`
   there takes the append path and never reads a template. The template is only
   reached when the home has to be created — which is exactly when scaffold
   mode fails today, with
   `error: lightweight-decisions template not found: <project>/.claude/templates/…`.)
2. **The same holds for the ADR helper.** Under the same conditions,
   `.claude/skills/jig-adr-workflow/adr.py new "<title>"` exits 0 and writes
   `docs/decisions/adr-NNNN-<slug>.md` from the copied template — the family's
   second member, which had the identical gap and no mitigation.
3. **The copy mirrors Codex.** `copy_machinery(host="claude")` copies every file
   under the plugin's `templates/` into `<project>/.claude/templates/`,
   preserving the relative tree, exactly as `_copy_codex_templates` does for
   `.codex/templates/`.
4. **Copied `.md.template` bodies name the copied machinery.** Every
   `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` literal in a copied `.md.template`
   is rewritten to `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` — the same
   transform SKILL.md bodies and rendered docs already get in scaffold mode. A
   record seeded from a copied template must not name a variable that is unset
   in the project that seeded it.
5. **Idempotent re-run.** A second `copy_machinery` run over the same project
   leaves `.claude/templates/` byte-identical (no duplication, no error), so
   `migrate copy-machinery` can be re-run to refresh machinery.
6. **Plugin-only mode is unaffected.** `scaffold.py --plugin-only` writes no
   `.claude/templates/` — the plugin root is the template home there, and the
   copy would be dead weight.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). _(3.12: 3508 →
      3518 OK; 3.9: 3361 OK, unchanged — see deviation §7 for why the floor
      count doesn't move.)_
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
      _(AC4's edge case was covered vacuously at first — see §5.)_
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. _(This slice **resolves** the "how should
      record helpers reach their templates in Claude scaffold mode?" entry.)_

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`; the
      load-bearing invariants migrated to its Notes column (preserved across regen).
- [x] Primer hygiene per spec 025-01: this slice closes the spec, so **no**
      Active-specs entry was added. A one-line Key-terms entry was drafted and
      then dropped: it pushed `CLAUDE.md` to 71 lines against the 70-line budget
      guard (spec 076-01), and the guard is right — the "don't delete this tree"
      warning belongs at the code site (`_copy_claude_templates`,
      `decisions.py`) and in the glossary, which is the on-demand home the
      primer indexes into. `docs/memory/glossary.md` gains **Copied templates
      tree**, reachable via `/jig:explain`.

**Edge cases covered explicitly:**

- Re-run over an existing `.claude/templates/` (AC5) — the refresh path
  `migrate copy-machinery` depends on.
- `--plugin-only` (AC6) — the copy must not leak into the mode that does not
  copy machinery.
- A template with no `${CLAUDE_PLUGIN_ROOT}` literal must survive the rewrite
  byte-identically (the rewrite is a no-op, not a re-render).
- Non-`.md.template` files (e.g. `scaffold.json.template`) are byte-copied, not
  rewritten — same split `_copy_codex_templates` makes.

**Anti-horizontal-phasing check:** After this slice a scaffold-mode project can
actually record a decision end-to-end (AC1/AC2 run the copied helpers as
subprocesses against a real scaffolded tree) — not "the copy exists and a later
slice will make it usable".

### Reconciliation sweep

| Artifact | Disposition | Why |
|---|---|---|
| `docs/architecture.md` | **rewrite** (live prose, inline per ADR-0010) | Enumerated the Claude scaffold copy set (no `templates/`) and framed the templates copy as a Codex-only trait. Both now false; the paragraph teaches the host asymmetry this slice removed. |
| `skills/migrate/SKILL.md` | **rewrite** | `copy-machinery`'s shipped contract omitted the templates step. This is what an agent reads before running the repair `decisions.py` now recommends. |
| `scaffold.py` `finalize_codex_migrate_skill` | **rewrite** | The Codex *render* of that contract is a separate hardcoded list; fixing SKILL.md alone left Codex users with the old one. |
| `migrate.py` `--help` + `report` Operations text | **rewrite** | Two more copies of the same contract, at the CLI rather than in SKILL.md. |
| `decisions.py`, `migrate.py`, `memory.py`, `workflow.py` | **rewrite** (comments/messages) | Each asserted "scaffold mode has no templates" as a premise. Re-premised; no resolution logic touched. |
| `docs/bugs/012-…md` | **amend** (closed record → `## Amendments`) | `status: DONE`, so ADR-0010 forbids rewriting the prose. The `## Remaining risk` this slice closes is preserved as written, with a dated amendment. |
| `docs/refinement-todo.md` | **resolve** | Struck through by `adr.py resolve-todo` + the substance of the pick. |
| [ADR-0038](../../decisions/adr-0038-claude-scaffold-template-copy.md) | **new** | Records the maintainer's choice + rejected options. |
| `docs/inbox.md` | **new** (3 entries) | Follow-ups surfaced by review that are out of this slice's scope: the family's remaining default-encoding reads; the two copy functions already drifting at n=2; `spec-workflow/SKILL.md`'s bare relative template path. |
| `docs/conventions.md` | **no-op** | Untouched by design — needs explicit human approval, and nothing here is a convention change. |
| `scripts/scaffold_contract.py` | **no-op** (knowing) | See §9. |
| `CLAUDE.md` | **compress** | Spec closes in one slice; per spec 025-01 the Active-specs entry is not grown. One primer line earns its place (see close-out). |

**Not swept, deliberately:** `_copy_codex_templates`'s default-encoding read and
`adr.py`/`memory.py`'s template reads. Pre-existing, failing identically in plugin
mode on `main` today, and inboxed rather than folded in — this slice fixes the one
read it *newly* broke (`workflow.py`, §6).

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**§1 — Red witnessed, both helpers, against a real install.** Probed on a real
`scaffold.py --with-machinery` tree with `CLAUDE_PLUGIN_ROOT` unset, before any
implementation:

```
$ env -u CLAUDE_PLUGIN_ROOT python3 .claude/skills/jig-memory-sync/decisions.py \
    add-lightweight --title probe --decision probe --project-dir .
error: lightweight-decisions template not found: <project>/.claude/templates/docs/decisions/lightweight-decisions.md.template

$ env -u CLAUDE_PLUGIN_ROOT python3 .claude/skills/jig-adr-workflow/adr.py \
    new probe-decision --no-push --project-dir .
template not found: <project>/.claude/templates/docs/decisions/adr-0000-template.md
```

Test-level red: 3 failures + 2 errors across the new `ClaudeScaffoldTemplatesTests`
/ `PluginOnlyTemplatesTests`; green after `_copy_claude_templates` landed, with no
test edited to make it pass. AC6 was green from the start — it is a guard against
the copy leaking into `--plugin-only`, not a behaviour this slice adds.

**§2 — The family is five helpers, not two. The spec undercounted, and so did
the first correction.** The spec and the refinement-todo entry framed this as "the
record-helper family" (`decisions.py` + `adr.py`). The craft pass found
`workflow.py`'s `_render_stub_slice` reads
`parents[2]/templates/docs/specs/slice-template.md`; a follow-up grep found
`memory.py` (people.md bootstrap) — whose error message *already said* the failure
was "expected for a scaffold-mode target", documenting this gap in a helper nobody
had connected to it; and the compliance re-review found the fifth, `migrate.py`
(`seed-decisions`, sharing `decisions.py`'s template). Enumerated with a grep over
every non-test helper, rather than a third guess:

| Helper | Template |
|---|---|
| `decisions.py`, `migrate.py` | `docs/decisions/lightweight-decisions.md.template` |
| `adr.py` | `docs/decisions/adr-0000-template.md` |
| `workflow.py` | `docs/specs/slice-template.md` |
| `memory.py` | `docs/memory/people.md.template` |

Five helpers, four distinct files. Consequences:

- Two helpers silently changed behaviour in scaffold mode: `workflow.py` stops
  using its degraded inline slice template, and `memory.py`'s bootstrap starts
  working. Neither is in an AC; both are improvements. Now pinned by
  `test_workflow_renders_the_real_slice_template_not_the_fallback` and
  `test_memory_bootstraps_people_md_from_the_copied_template` — an earlier
  version asserted only that the *file* was copied, which AC3 already covered and
  which proved nothing about the consumer.
- Their now-false comments/messages were re-premised here.
- **This is the argument for the whole-tree copy over a scoped allowlist**, and
  it is stronger than the Codex-parity and duplication-cost arguments ADR-0038
  first leaned on: an allowlist built from the two templates in evidence would
  have shipped, looked correct, and left two consumers broken. Found by review,
  not by design — and the count needed two corrections before it settled, which
  is itself the argument against curating the list by hand.
- Caveat on "identical shape": `workflow.py` goes straight to `parents[2]` and
  never consults `CLAUDE_PLUGIN_ROOT`, unlike the other four. Same fallback, one
  fewer door.

**§3 — "No helper changes" was literally false as written.** The spec said a
helper edit "would mean the copy is not doing its job", and the refinement-todo
asserted "no helper changes". Four helper *files* do change — comments and error
messages carrying the old premise. No helper's `_plugin_root()` /
`_template_path()` logic is touched, which is what the claim meant. Both
documents now say "no change to any helper's template *resolution*". Caught by
the compliance pass.

**§4 — Two ADR-0038 claims were asserted as fact and were false.** Recorded
because the record's own Assumptions section said "None unverified" while
carrying them:

- *"A `migrate copy-machinery` re-run picks the tree up — same call."* True only
  from a jig install. A project's own copied `migrate.py` cannot retrofit itself
  — probed: it fails at `cannot locate scaffold.py at
  <project>/.claude/skills/scaffold-init/scaffold.py`. So (a) fixes projects
  scaffolded *after* it, not the ones already out there. Corrected in ADR-0038
  Open questions and the spec's Out-of-scope.
- *"Codex's template copy is an asymmetry with no recorded rationale."* It has
  one: `CodexScaffoldRenderer.rewrite_skill_md_paths` redirects
  `${CLAUDE_PLUGIN_ROOT}/templates/` into `.codex/templates/`, so the Codex copy
  is also what makes its own rewritten prose true.

Both found by the frame-critique pass. **The correction to the second one then
over-corrected** and had to be walked back by the re-critique: the first fix
claimed Codex's copy is a "mechanical necessity of the rewrite table" and that
(a) therefore *creates* parity rather than restoring it. That contradicts the
ADR's own Context table — Codex scaffold mode resolves via `parents[2]` precisely
*because* `_copy_codex_templates` copies, so on the helper-fallback function the
hosts are symmetric and Claude is the odd one out. The rewrite table is an
*additional*, host-specific reason. The record now says that; worth noting that
the over-correction was more flattering to the reviewer than the truth was.

**A citation lesson, recorded because it bit twice.** An earlier version of this
section cited `scaffold.py:944-947` for the rewrite table. That was correct when
observed against `origin/main` and false by the time it was written down — this
slice inserts ~47 lines above it, moving it to ~991-994. Two reviewers
independently flagged it. Line citations in a deviation log describe a file the
same change is editing; cite by symbol.

**§5 — A test asserted its edge case against the wrong branch.**
`test_ac4_templates_without_plugin_root_are_byte_identical` claimed to pin "the
rewrite is a substitution, not a re-render" using `adr-0000-template.md` and
`scaffold.json.template` — neither of which ends in `.md.template`, so both took
the byte-copy branch and the rewrite round-trip had **zero** coverage. Split into
`test_ac4_rewritten_templates_without_a_literal_are_byte_identical` (real
`.md.template` files) and `test_ac4_non_md_templates_are_byte_copied` (iterates
every non-`.md.template` file rather than hand-listing two — the hand-list had
already missed `slice-template.md`). Caught by the compliance pass.

**§6 — Encoding, on the write side and the reads it newly enables.**
`_copy_claude_templates` reads with an explicit `encoding="utf-8"` to match
`atomic_write_text`'s utf-8 write. Mirroring `_copy_codex_templates` verbatim
would have inherited its default-encoding read, which under `LANG=C` mojibakes or
raises on the em-dashes in the templates — and that corruption would propagate
into every seeded record.

The re-review pass then made the obvious point back: if `LANG=C` is a real enough
threat model to change the write side, it is real on the **read** side this slice
just enabled. `workflow.py`'s `_render_stub_slice` was the live case and is fixed
here — it read at the default encoding inside `except OSError`, and
`UnicodeDecodeError` is a `ValueError`, so post-095-01 a C-locale scaffold-mode
project would **crash** where the pre-095-01 behaviour (file absent →
`FileNotFoundError` → inline fallback) degraded cleanly. That is a regression this
slice would have introduced; it now reads utf-8 and catches both.

Knowingly not fixed: `adr.py` and `memory.py` read their templates at the default
encoding too. Unlike `workflow.py`'s, those paths fail the same way in *plugin*
mode on `main` today — pre-existing, not introduced here, and fixing them is a
separate concern (inboxed).

**Not pinned by a test:** no fixture forces a non-UTF-8 locale, so dropping any
of these `encoding=` kwargs would ship green. The reasoning is the only guard.

**§7 — Test-suite reach.** `test_scaffold_mode.py` has a module-level
`load_tests` hook that returns an empty suite below Python 3.11 (a `tomllib` gate
for the Codex-packaging tests). On a 3.9 interpreter — the documented floor, and
the default macOS python3 — `run_tests.py` therefore skips this file **whole**,
including these new tests. They were verified two ways instead: directly on 3.9
(`python3 skills/scaffold-init/test_scaffold_mode.py`, which bypasses the hook)
and via the full suite on 3.12, which is what CI's matrix runs. Not introduced
here and not fixed here; flagged in the PR as a question — an 88-test file
vanishing on the supported floor is a bigger call than this slice.

**§7b — A gate was bypassed by hand, and the gate caught it.** ADR-0038 was
first written with `status: Accepted` hand-stamped into the frontmatter, on the
reasoning that the maintainer's pick *is* the acceptance act so "Proposed" would
misattribute his decision to this branch. The authority argument is fine; the
mechanism was not. `adr.py accept` gates the Proposed→Accepted flip on a passing
frame-critique verdict for a `frame_review: true` ADR (slice 064-05 / ADR-0020
OQ2) — so hand-writing the field skipped the one gate jig applies to exactly this
kind of record, on an ADR that was at that moment **failing** its frame critique.
`adr.py resolve-todo` then accepted the refinement-todo resolution because it only
reads the field.

Two things worth keeping from this: the pressure was structural (resolve-todo
*requires* Accepted, which is precisely what tempts a hand-write), and the gate's
sanctioned bypass (`JIG_REVIEW_EVIDENCE_GATE=0`) leaves a trace where a
hand-written status leaves none. The record is now `Proposed` and flipped by
`adr.py accept` once the frame critique passes; the order is frame-critique →
`accept` → `resolve-todo`. Found by the frame re-critique, which noticed that the
machinery cited in defence of the hand-write actually ordered the steps against
it.

**§7c — The reverted hand-stamp left downstream state behind, and §7b initially
narrated the intended sequence as if it were the shipped one.** Reverting
`status:` to `Proposed` did not undo what the hand-written `Accepted` had already
enabled: `adr.py resolve-todo` had struck the refinement-todo entry through
(it refuses a non-Accepted ADR — that is the whole reason the field got
hand-written), and `docs/decisions/README.md` still advertised the ADR as
Accepted. For a window, three durable records disagreed about one ADR's state,
and §7b described the correct order without saying that the last step had not yet
run. The reconciliation pass caught it as "a redemption story whose ending never
happened" — the finding §7b would have caught about anyone else.

Now actually run, in the order the ADR prescribes: frame-critique passed (round 4
of 4) → verdict recorded → `adr.py accept 0038` (the gate cleared on evidence,
not on a hand-write) → `adr.py index` regenerated. **Note the index does not
self-heal**: `cmd_accept` rewrites only the ADR file, so the README entry was
correct afterwards only because `_today()` happened to be the same date the
hand-stamp used. On any later date the index would have been stale too. The order
worth carrying forward is frame-critique → `accept` → **`index`** →
`resolve-todo`, plus a host rebuild if any canonical helper prose moved (it had —
see below).

**§7d — The four→five sweep needed three passes, and that is the lesson, not a
footnote.** The family count went two → four (craft) → five (compliance), and each
correction left surfaces behind: after the "five" fix landed in the ADR and the
deviation log, `docs/refinement-todo.md`, `docs/architecture.md`, and the *Codex
render* of the migrate contract still said four; `test_workflow.py`'s
`SelfDefiningReminderInRenderersTests` still documented "a scaffolded project,
where `slice-template.md` is NOT copied" as its rationale; and the committed
`hosts/` mirrors still carried the pre-fix ordinals ("a third member…") because
the canonical edit landed after the last rebuild. All swept, found by the
reconciliation pass. §2 argues that hand-curated lists of consumers go stale;
this slice's own records proved it three times while making that argument. (live prose, corrected inline per ADR-0010):
`docs/architecture.md` (twice — the copy-set enumeration and the paragraph that
framed the templates copy as a Codex-only trait) and the `copy-machinery`
contract, which omitted the templates step for **both** hosts and is what an
agent reads before running the repair `decisions.py` now recommends.

That contract has **three** surfaces, and the first pass fixed one. The
compliance re-review caught that `skills/migrate/SKILL.md` is only the Claude
source: `finalize_codex_migrate_skill` replaces the whole "What it does" section
with a hardcoded list for the Codex render, so the fix never reached
`.codex/skills/jig-migrate/SKILL.md`. `migrate.py`'s own `--help` and its
`report` Operations suggestion were also still enumerating the old copy set.
All three now name templates.

**§9 — Knowingly not done.** `scripts/scaffold_contract.py` pins a scaffolded
`.claude/` tree and was not extended to assert `.claude/templates/`; the copy is
asserted by `test_scaffold_mode.py` only. Raised by the arch pass as low-value;
recording the omission as a choice rather than an oversight.

**§9 ↔ §7, stated plainly because separately they read better than they are:**
§9 declines the contract check on the grounds that `test_scaffold_mode.py` covers
it — and §7 establishes that file is skipped whole below Python 3.11. Together:
on the *documented floor*, this slice has zero discovered coverage, and the one
check that would have pinned it version-independently is the one declined. CI's
3.12 job makes this non-blocking, and the direct-run verification is real, but
§9's rationale is weaker than it sounds and should not be read as "covered".

Also from the arch pass: a copied `scaffold-init` run in `--plugin-only` mode can
now read an already-rewritten template tree where it previously crashed. Narrow,
and precedented — `plugin_root(host="codex")` ignores the env var entirely, so
Codex-scaffolded projects have always done this. An earlier version of this
section said ADR-0038's first kill criterion covers it; it does not — that
criterion is about staleness producing a wrong record, which is a different
failure. Recorded here as an uncovered narrow case, not as a covered one.
