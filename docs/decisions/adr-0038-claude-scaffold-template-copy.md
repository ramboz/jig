---
status: Accepted
dependencies: [adr-0012]
last_verified: 2026-07-16
frame_review: true
---

# ADR-0038: Claude scaffold mode copies templates/

## Status

Accepted (2026-07-16)

**Provenance — this is the maintainer's call, not this ADR's proposal.** The
question was posted to him on
[#109 (comment)](https://github.com/ramboz/jig/issues/109#issuecomment-4996295388)
with the three options below, and parked in
[refinement-todo.md](../refinement-todo.md). He picked **option (a)**; the pick
was relayed verbally via Marie-Rose, who implemented it in
[spec 095](../specs/095-scaffold-template-copy/spec.md). This record exists so the
choice and its rejected alternatives outlive the branch — a future agent seeing a
`templates/` tree inside `.claude/` and thinking "that looks like duplication,
let's drop it" should land here first (start with the live-file table below).

**On the status field.** The *decision* is the maintainer's and is not in
question; `status:` is not a vote on it. In jig, `status:` is the **record's**
lifecycle state, and the Proposed→Accepted flip is gated: `adr.py accept` refuses
it for a `frame_review: true` ADR without a passing frame-critique verdict
(slice 064-05 / ADR-0020 OQ2). This record starts `Proposed` and is flipped by
`adr.py accept` once that gate clears — which is the whole point of the gate.

An earlier draft hand-wrote `Accepted` on the reasoning that the maintainer's
pick *is* the acceptance act. That reasoning is not wrong about authority, but it
was wrong about mechanism: hand-stamping the field bypassed the one gate jig
applies to exactly this kind of record, on an ADR that was at that moment failing
its frame critique. The gate has a sanctioned bypass
(`JIG_REVIEW_EVIDENCE_GATE=0`) that leaves a trace; a hand-written status leaves
none. Recording the correction here because the same temptation will recur:
`adr.py resolve-todo` refuses a non-Accepted ADR, which creates pressure to
hand-set the field. The order is frame-critique → `accept` → `resolve-todo`.

## Context

jig's record helpers seed their files from the shipped `templates/` tree:
`decisions.py` creates `docs/decisions/lightweight-decisions.md` (bug 012), and
`adr.py new` renders `adr-0000-template.md`. Both resolve the tree the same way
(`_plugin_root`, byte-identical in both helpers): `CLAUDE_PLUGIN_ROOT` if set,
else `Path(__file__).resolve().parents[2] / "templates"`.

That reaches a template in three of jig's four install modes. It does not reach
one in **Claude scaffold mode** — where the machinery is copied into the project
and there is no plugin root:

| Install mode | Helper lives at | `parents[2]` | Template reachable? |
|---|---|---|---|
| Claude plugin | `<plugin>/skills/memory-sync/` | `<plugin>` | ✅ |
| Codex plugin | `<plugin>/skills/memory-sync/` | `<plugin>` | ✅ |
| Codex scaffold | `<project>/.codex/skills/jig-memory-sync/` | `<project>/.codex` | ✅ — `_copy_codex_templates` copies `templates/` |
| **Claude scaffold** | `<project>/.claude/skills/jig-memory-sync/` | `<project>/.claude` | ❌ |

`copy_machinery` copied `skills/`, `agents/` and `hooks/` into `.claude/`, but not
`templates/`. Only the Codex path copied templates. **Both hosts need the copy for
the same primary reason** — a copied helper resolves `parents[2]/templates/`,
which is `<project>/.codex` or `<project>/.claude`, so the tree has to be there or
the fallback is a lie. Codex has a **second, host-specific** reason on top:
`CodexScaffoldRenderer.rewrite_skill_md_paths` redirects
`${CLAUDE_PLUGIN_ROOT}/templates/` → `${CODEX_PROJECT_DIR:-$PWD}/.codex/templates/`,
so its copy is also what makes its own rewritten prose true. The Claude renderer
(`_PLUGIN_SKILL_PATH_RE`) rewrites only `/skills/<name>/` and never touches
`/templates/`, which is plausibly why the Claude gap went unnoticed: nothing on
the Claude side ever *pointed* at a copied templates tree, so nothing broke
loudly until a helper tried to read one.

So on the function this ADR is about — the helper fallback — the hosts are
symmetric, and Claude is the odd one out. What load-bears is not parity either
way: it is that the copy is the only thing that makes the helpers' **existing**
fallback true in a mode with no plugin root.

### Which of the 25 copied files are actually live

The copy ships the whole tree, but only **4 of 25 files** are read at runtime by
a copied helper. A future agent auditing `.claude/templates/` needs this list,
because the rest looks — correctly — inert:

| Live file | Read by |
|---|---|
| `docs/decisions/lightweight-decisions.md.template` | `decisions.py` (seed the record home); `migrate.py seed-decisions` |
| `docs/decisions/adr-0000-template.md` | `adr.py new` |
| `docs/specs/slice-template.md` | `workflow.py` `_render_stub_slice` (else a degraded inline fallback) |
| `docs/memory/people.md.template` | `memory.py` (people.md bootstrap; spec 050 solo→team) |

The other 21 are `scaffold-init` seed templates (`CLAUDE.md.template`,
`docs/workflow.md.template`, the `docs/specs/seed/…` tree, …) whose only consumer
is `scaffold()`, which **refuses to run in an already-scaffolded project**. They
are inert weight in a scaffolded tree, and that is the honest cost of (a).

**The hazard this creates is authority confusion, not bulk.** A scaffolded
project now has `.claude/templates/CLAUDE.md.template` sitting beside its own
generated `CLAUDE.md`, and a seed `docs/specs/` tree beside its real one. jig's
own primer carries "templates/CLAUDE.md.template is the scaffold source — not
this file" precisely because that confusion is real. **The copied tree is not
your project's content: it is jig's source, materialized so helpers can read it.
Edit your project's files, never `.claude/templates/`** (a `copy-machinery`
refresh overwrites them).

**This list is the argument against a scoped copy.** The templates the reported
bug is *about* are 2 of the 4; the other two belong to helpers nobody had
connected to the problem. An allowlist built from the bug in evidence would have
shipped, looked right, and left `workflow.py` and `memory.py` broken. Copy the
tree, not a curated subset of it.

Two forces made this worth deciding rather than mitigating again:

1. **It is a family problem, not one helper's.** `adr.py` has the identical gap
   and no mitigation — and it is not a family of two: `migrate.py`, `memory.py`
   and `workflow.py` resolve templates the same way, each with its own resolver
   and its own template path (see the live-file table). A per-helper fix lands
   five times, then again for the next one.
2. **Bug 012 already mitigated once.** Its fix made the failure name two working
   remedies (set `CLAUDE_PLUGIN_ROOT`; run `migrate.py seed-decisions`) and left
   the mode broken, under `## Remaining risk`. A second mitigation stacked on the
   first is how a gap becomes permanent.

## Decision Options Considered

### Option A: Claude-side template copy — mirror `_copy_codex_templates`
`copy_machinery(host="claude")` copies `templates/` into `.claude/templates/`,
so the helpers' existing `parents[2]` fallback resolves unchanged.

- **Pros:** Smallest conceptual change — the mechanism already exists and is
  proven on the Codex side. No helper changes at all, so it fixes the whole
  family (and every future helper) at once. Templates keep exactly one source of
  truth.
- **Cons:** Every scaffolded Claude project's `.claude/` grows a `templates/`
  tree (25 files, ~120 KB) — a change to scaffold output for **every** install,
  including projects that never record a decision. **Only 4 of those 25 files
  are live** (see the live-file table in Context), so the tree is mostly inert
  weight. And the drift story
  is weaker than it looks: the copy can go stale relative to the plugin, and the
  refresh path (`copy-machinery` **from a jig install**) requires exactly the
  plugin root this mode is defined by not having — the same remedy-class this
  ADR faults bug 012's mitigation for. The difference is one of default, not
  kind: after (a) the mode works out of the box and only *staleness* needs the
  plugin root, where before, *every* first record did.

### Option B: Embed each template in its helper
A module constant per helper, plus a drift test asserting it equals the shipped
template file.

- **Pros:** Works in every install mode with no scaffold change. Makes
  `decisions.py` genuinely self-contained — which its own module docstring
  already claims ("Self-contained by design … so the host-packaging step can
  copy the skill tree whole without a cross-tree dependency"). **On size it
  wins outright:** ~4 KB embedded once in the plugin source, against ~120 KB
  copied into every scaffolded project. This option is cheaper on bytes, and
  the record should not pretend otherwise.
- **Cons:** Duplicates template bodies into helpers (`adr.py` too, then
  `workflow.py`, then the next one), so every template edit has two homes and a
  drift test standing between them — a synthetic single source of truth
  defended by a test, in place of a real one. That is the whole case against it,
  and it does not need a bytes argument.

### Option C: Leave it
Scaffold mode stays unable to seed a record home; bug 012's mitigation stands.

- **Pros:** Zero change; the reported case (#109) was plugin mode, and scaffold
  mode is a minority path.
- **Cons:** A documented, permanently-broken path in the mode jig offers for
  in-repo adoption — and it fails at the worst moment: when someone is trying to
  record a decision, which is exactly when they are least interested in
  debugging their install. Leaves `adr.py` with no mitigation at all.

## Recommended Decision

**Option (a)**, and not because of parity — parity is a consequence, not the
argument. The reason is that (a) makes the fallback the helpers **already have**
true, in the one mode where it is false, without touching any of the five helpers
that depend on it. Options (b) and (c) both lack that: (b) fixes the family by
editing every member of it (and the next one), (c) fixes nothing.

The record should be explicit that (a) is not free, and that it declines a stated
principle: `decisions.py`'s docstring claims to be "self-contained by design",
which is exactly what option (b) would deliver and (a) does not — the helper
stays dependent on a sibling tree being copied next to it. (a) accepts that
dependency and moves the tree instead. The other accepted costs: scaffold output
grows a 25-file `templates/` tree for every Claude install, of which 21 files are
inert there; and projects scaffolded *before* this cannot repair themselves from
inside (Open questions).

## Consequences

**Becomes easier:**
- Recording a decision or opening an ADR in a scaffold-mode project — the
  reported #109 workflow, in the mode with no plugin root to fall back on.
- Adding a future helper that seeds from a template: it inherits reachability in
  all four modes with no per-helper work.
- Reasoning about hosts: both scaffold hosts now copy the same four trees
  (skills, agents, hooks, templates).

**Becomes harder:**
- `.claude/` is bulkier and less obviously hand-auditable; `templates/` is one
  more copied tree that can drift from the plugin between `copy-machinery`
  refreshes.
- Any future change to the copy set has to keep two hosts in step, not one.

## Assumptions

Every claim below was probed. Citations are by symbol, not line number —
this slice's own insertion shifted `scaffold.py` by ~47 lines and stale-dated an
earlier draft's line citations within the same change.

- **Five *record* helpers** read `templates/` through a
  plugin-root-then-`parents[2]` fallback: `decisions.py` (`_plugin_root`),
  `adr.py` (`_plugin_root`),
  `migrate.py` (`_resolve_plugin_root`), `memory.py` (`plugin_root`), and
  `workflow.py` (`_render_stub_slice`). They share the *shape*, not the code —
  and `_render_stub_slice` is the odd one: it goes straight to `parents[2]`
  without consulting `CLAUDE_PLUGIN_ROOT` at all. Four distinct template files
  are read (see the live-file table; `migrate.py seed-decisions` shares
  `decisions.py`'s). `scaffold.py` resolves the tree the same way but is not in
  this family: it is the *writer* of the copy, and the consumer of the other 21
  seed templates named in Context.
- **The gap is real and reproduces** — probed against a real `--with-machinery`
  install with `CLAUDE_PLUGIN_ROOT` unset:
  `error: lightweight-decisions template not found: <project>/.claude/templates/…`
  and `template not found: <project>/.claude/templates/docs/decisions/adr-0000-template.md`
  (captured in the slice 095-01 deviation log; now pinned by
  `ClaudeScaffoldTemplatesTests`).
- **Codex's rewrite table** redirects `${CLAUDE_PLUGIN_ROOT}/templates/` into
  `.codex/templates/` — `CodexScaffoldRenderer.rewrite_skill_md_paths`; the
  Claude rewrite (`_PLUGIN_SKILL_PATH_RE`) matches only `/skills/<name>/`.
- **A scaffolded project's own copied `migrate.py` cannot retrofit templates** —
  probed (Open questions).

Two claims in an earlier draft were asserted as fact, unprobed, and false — the
retrofit claim and Codex's copy being an unexplained asymmetry. Both are
corrected above; the drafting history is in the slice's deviation log (§4), which
is its home. Noted here only because this section is where a reader decides how
much to trust the rest.

Remaining assumption, **not** probed: that 21 inert seed templates in every
scaffolded `.claude/` cause no harm beyond weight and the authority confusion
named in Context. The mitigation is documentation (that warning), not a
mechanism.

## Kill criteria

**Neither criterion has an automatic detector today, and saying so is part of the
record** — the copied tree carries no version stamp, nothing compares it to the
plugin, and `migrate report` flagging the gap is explicitly deferred (Open
questions). Both fire on a human noticing. That is a real weakness of this
decision, not a formality:

- **The copied tree drifts and misleads.** If a stale `.claude/templates/`
  produces a *wrong* record rather than a merely refreshable one, the copy is
  worse than the plugin-root read it replaced, and option (b)'s single-artifact
  property starts to look right. *Closest thing to a detector:* a project's
  seeded record disagreeing with the shipped template's shape.
- **`templates/` outgrows what belongs in every project.** 25 files today, 4 of
  them live. *Partial detector:* `test_ac3_every_plugin_template_is_copied` pins
  the copied set against the plugin's tree, so growth changes a test — but it
  asserts equality, not a budget, so it will happily follow the tree to 200
  files. If someone objects to the weight, the retreat is a scoped copy, and the
  live-file table in Context is the list to scope to — re-derive it first rather
  than trusting it, since it is exactly the kind of list that goes stale as
  helpers grow.

## Open questions

- **Retrofitting existing scaffolded projects.** Projects scaffolded before this
  ADR have no `.claude/templates/` until someone re-runs `migrate copy-machinery`
  **from a jig install (or with `CLAUDE_PLUGIN_ROOT` set)**. The qualifier is
  load-bearing, and an earlier draft of this record omitted it: re-running the
  project's *own copied* `.claude/skills/jig-migrate/migrate.py` does **not**
  retrofit. That helper resolves its plugin root to `<project>/.claude`, so the
  copy would read from a `templates/` tree that is precisely what is missing.
  Probed on this branch — it fails before that, at
  `cannot locate scaffold.py at <project>/.claude/skills/scaffold-init/scaffold.py`
  (copied skills carry the `jig-` prefix), so the self-refresh is a dead end
  either way, not a silent no-op. **A scaffolded project cannot repair itself
  from inside**; the remedy needs a jig install, which is the same
  go-get-a-plugin-root remedy-class this ADR faults in bug 012's mitigation.
  That is the honest limit of (a): it fixes every project scaffolded *after* it,
  not the ones already out there.

  Whether the re-run is the sanctioned backfill, and whether `migrate report`
  should flag the gap so an affected project learns about it before the failure
  rather than after, is out of scope for spec 095 and posted as a question on
  [#109](https://github.com/ramboz/jig/issues/109).

- **Tier gating (discharging `dependencies: [adr-0012]`).** ADR-0012 makes tier
  gating a promise-integrity decision: a project's on-disk skill set must match
  its manifest. Templates ship **ungated** — a Tier-0-only project receives
  `adr-0000-template.md` even though `adr-workflow` is Tier 1 and not installed.
  This is deliberate: templates have no natural tier (`docs/workflow.md.template`
  is owned by no skill), so gating would mean inventing and maintaining a second
  template→tier map, and a partial tree is the same gap with a smaller blast
  radius. Precedent: the `.gitignore` security floor is ungated infra for the
  same reason (ADR-0013 / slice 052-04). Recording it here because a reader of
  ADR-0012 alone would expect gating and find none.
