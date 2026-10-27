---
status: Accepted
dependencies: []
last_verified: 2026-10-26
frame_review: true
---

# ADR-0067: Genesis spec 000 and a stub-free seed

## Status

Accepted (2026-10-26)

## Context

The worked example `scaffold-init` seeds moves to a genesis spec `000-adopt-jig` with no placeholder spec, so a project's own first spec is `001` instead of `003`.

Until now a greenfield `scaffold-init` seeded two numbered specs, `001-adopt-jig` (a `DONE` worked example) and `002-first-spec` (a `DRAFT` placeholder).

Slice 048-05 introduced the seed so the first turn has a faithful pattern to
imitate, and its Clarification Q3 settled `001-adopt-jig` as "permanent honest
history … nothing to clean up." The project owner reported (2026-10-26, in the
session that drafted this ADR) feedback received several times from adopters
that says otherwise:

- Users want **their** first spec to be `001`. The seed occupies `001` and
  `002`, so every project's own numbering starts at `003`.
- The `002-first-spec` stub is noise. It is a placeholder that `workflow.py
  new` already makes redundant (it emits a well-formed `spec.md` +
  `slice-01-tbd.md` from the packaged templates), and it lingers as a `DRAFT`
  row on the status board and in `orient` until someone hand-deletes it.
- Once a project has real specs, users want to drop the seed, and a hand
  delete leaves dangling links. Probed on a fresh scaffold (2026-10-26) with
  the seed deleted: `verify_install.py --mode scaffold`'s docs check reports
  dangling links from the user-owned `CLAUDE.md` / `AGENTS.md` and
  `docs/adoption-readiness.md` into `specs/001-adopt-jig/`. That verifier runs
  only at greenfield scaffold completion (`seed_expected`,
  `skills/scaffold-init/scaffold.py:4191`), so nothing flags the links later.
  They stay as silent breakage in always-loaded context, alongside the skill
  prose pointer described next.

The seed is also a **referent of shipped skill prose**, not only project
history. `skills/spec-workflow/SKILL.md` (two places) names
`docs/specs/001-adopt-jig/` as the structural worked example to mirror when
authoring a slice (the bug 027 fix sent authors there instead of an unanchored
template path), and the scaffolded `CLAUDE.md` / `AGENTS.md` call it "the
worked example to imitate." Skill prose is versioned with the plugin, so any
change to the seed's name or presence must keep that pointer valid in every
seed state a project can be in.

Same probe, `000` viability: a seed renamed to `000-adopt-jig` passes
`spec_lint.py --all`, renders on `workflow.py status-board`, and the next
`workflow.py new` reserves `001` (`_next_spec_number` is `max(NNN)+1`, and the
only spec-number truthiness check, in the `.jig/spec-ref` stamp, tests the
zero-padded string `"000"`, which is truthy).

## Decision Options Considered

### Option A: Keep the seed as-is (status quo, 048-05 Q3)
- **Pros:** No change; the worked example stays maximally discoverable.
- **Cons:** Ignores the repeated feedback; user numbering starts at 003; the
  stub stays as board noise; removal stays unsafe.

### Option B: Genesis spec `000`, no stub, removable on request
Renumber the adoption spec to `000-adopt-jig` (genesis — the project's
adoption, not its work), stop emitting `002-first-spec`, and make removing the
genesis spec a supported, deterministic, user-initiated operation, with a
one-line advisory when the project's first own spec reaches `DONE`.
- **Pros:** User specs start at `001` with zero special-casing in numbering;
  the board carries one honest `DONE` row instead of a `DONE` + a fake `DRAFT`;
  the worked example still exists for the first turns; removal is one command
  and leaves `verify_install` green.
- **Cons:** A small new command surface; two seed shapes exist in the wild
  (legacy `001`/`002` and new `000`), so removal must recognise both.

### Option C: Option B, but auto-delete the genesis spec when the first own spec lands
- **Pros:** Zero user effort.
- **Cons:** A lifecycle `transition` silently deleting files outside the spec
  it is transitioning is surprising and hard to reverse in an uncommitted tree;
  it couples the transition gate to seed housekeeping; some projects *want* to
  keep the adoption record. Violates the "nudge, don't act" posture jig uses
  for advisories.

### Option D: Use `000` but keep the `002`-style stub (as `001-first-spec`)
- **Pros:** Keeps an explicit "your turn" placeholder.
- **Cons:** Re-creates the exact noise and still steals the user's `001`.

### Option E: Ship the worked example with the plugin, seed no numbered spec
Put the filled-in example next to the skill (as `spec-workflow` already does
for `worked-example-spidr-split.md`) and seed nothing into `docs/specs/`.
- **Pros:** The user gets `001` with no stub, no removal command, and no
  dual-shape recognition; the skill-prose referent is stable.
- **Cons:** The always-loaded primer and the first-turn model lose the
  in-project pattern 048-05 was built for. Scaffolded prose cannot point into
  the plugin: in a plugin-only install there is no project-resolvable path to
  it (spec 046: scaffolded artifacts must not depend on `${CLAUDE_PLUGIN_ROOT}`
  or source-checkout paths). It also drops the honest adoption record and the
  `DONE` row that shows a new user what a finished slice looks like on the
  board.

### Option F: Keep the example in-project but unnumbered (e.g. `docs/examples/adopt-jig/`)
- **Pros:** The user gets `001`; scaffolded prose can link it (unlike Option
  E); no spec number `000` reaches any consumer.
- **Cons:** It sits outside the lifecycle, so the board loses the `DONE` row
  and the adoption record stops being a real spec. It becomes a reference doc
  that looks like a spec but is not one. That gap between appearance and kind
  is exactly what 048-05 avoided by making the example honest history. It still
  needs a removal story and the same pointer handling as Option B.

## Recommended Decision

**Option B.**

1. `scaffold-init` seeds the worked example as **`000-adopt-jig`** (spec 000,
   slice `000-01`). Spec number `000` is reserved for this genesis record; a
   project's own specs start at `001` through the unchanged `max+1` rule.
2. `scaffold-init` **no longer emits `002-first-spec`.** The hand-off to the
   first real spec lives in the scaffold completion message, the genesis
   spec's overview, and `docs/adoption-readiness.md`, all pointing at
   `/jig:spec-workflow new <slug>`.
3. The genesis spec is **kept by default but removable on request.** A
   deterministic `workflow.py retire-genesis` removes it, together with the
   pointer lines that link to it, and regenerates the status board. It
   recognises both the new (`000-adopt-jig`) and the legacy
   (`001-adopt-jig` + an untouched `002-first-spec` stub) seed shapes, and never
   removes a `002-first-spec` the user has turned into real work.
   The legacy stub is recognised by its own content, never by comparison
   with a live template (which this ADR deletes): `status: DRAFT` and its
   `# Spec 002: First spec — replace me` heading. The legacy genesis is
   `001-adopt-jig/` whose `spec.md` frontmatter carries `skill: scaffold-init`.
   Genesis detection everywhere keys on these directory slugs and shapes,
   never on the spec number's integer value.
4. After removal no always-loaded or adoption doc links into the removed
   directory. (The scaffold seed check needs no change for this: it runs only
   when a scaffold run emits the seed.)
   **Invariant:** the genesis pointers in the scaffolded primers (`CLAUDE.md`,
   `AGENTS.md`) and `docs/adoption-readiness.md` are rendered **only when a
   genesis spec is present or is being emitted** by that scaffold run. The
   templates render on every scaffold, including `--force` re-scaffold and
   migrate-adjacent runs where the seed itself is skipped, so an
   unconditional pointer would put the dangling link straight back after
   retirement. `retire-genesis` and re-scaffold must agree.
5. When a project's first non-genesis spec reaches `DONE` while a genesis
   spec is still present, `transition` prints a one-line, non-blocking hint
   naming `retire-genesis`. It never deletes anything itself.
6. Existing projects are **not renumbered**. Their legacy seed keeps working;
   `retire-genesis` is how they shed it.
7. **Shipped prose resolves the exemplar by state, never by one fixed path.**
   Skill prose that points authors at the worked example names it as "the
   genesis spec (`000-adopt-jig/`, or `001-adopt-jig/` in projects scaffolded
   before this ADR) if present, otherwise any `DONE` slice in the project",
   with the `workflow.py new` starter as the shape of last resort. So the
   pointer stays meaningful in all three seed states: new, legacy, and
   retired. Scaffolded primer bullets that link the genesis spec are removed
   by `retire-genesis` along with it.

This partially supersedes 048-05's Clarification Q3: the adoption record is
still honest history and is kept by default, but it is no longer
"permanent — nothing to clean up." The 048 record itself is not rewritten
here (ADR-0010 / spec 102: amending a closed record needs separate owner
approval).

## Consequences

**Becomes easier:**
- A project's own first spec is `001`.
- The status board and `orient` no longer show a placeholder `DRAFT` spec.
- Shedding the seed is one command and keeps `verify_install` green.

**Becomes harder:**
- Two seed shapes exist in the wild; `retire-genesis` and the seed check must
  recognise both.
- Docs and tests that name `001-adopt-jig` / `002-first-spec` must move to
  `000-adopt-jig` (templates, verify fixtures, host packages). Skill prose is
  not a rename: it moves to the state-resolved wording in decision 7. The seed's
  own text that relies on numbering (its DoD's "first subagent review is your
  spec 002", its overview's pointer to `002-first-spec`) is rewritten, not
  just moved.
- A retired project keeps no in-project worked example; authors fall back to
  their own `DONE` slices, which by then exist.

## Assumptions

- Every spec-number consumer treats `000` like any other three-digit number.
  Probed for `spec_lint`, `status-board`, `new`, and the `.jig/spec-ref`
  stamp (see Context). `refs/claims/<N>` and cross-ref reads were not
  exercised on a `000` slice; the genesis slice is born `DONE` and never
  transitions, so they are not on its path.

## Kill criteria

- A spec-number consumer is found that mishandles `000` and cannot be fixed
  locally (e.g. a host or external tool that parses spec numbers as positive
  integers).
- Adopters report that losing the `002` placeholder makes the first-spec
  hand-off harder to find (the hint surfaces would then need strengthening,
  not the stub restored).

## Open questions

None.
