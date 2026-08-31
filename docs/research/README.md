# Research notes

> Research notes are the home for the **open investigation phase** — the
> stretch *before* a decision is even named, when you are gathering sources,
> weighing pros/cons, and holding open questions on an idea that isn't yet
> attached to any committed build. Governed by
> [ADR-0054](../decisions/adr-0054-research-notes-artifact-convention.md). A
> research note is **not** a decision (that's an ADR, `docs/decisions/`) and
> **not** committed work (that's a spec, `docs/specs/`). It is **sequential
> with, not a competitor to**, [`docs/refinement-todo.md`](../refinement-todo.md)
> — refinement-todo holds a *named deferred decision + resolution trigger*; a
> research note is the open phase that *feeds* one. A note *promotes into* a
> refinement-todo entry, an ADR, or a spec once it crystallizes (see
> Hand-offs below).

## Seed research (frozen — jig's founding corpus)

The numbered files `00-starter-prompt.md` through `09-addition-memory-layer.md`
in this directory are jig's original bootstrap research — the investigation
that produced jig itself. They are kept **frozen** and unrenamed as a
historical record (ADR-0010 ethos: don't rewrite history for its own sake).
They are **not** living notes: no status frontmatter, no index entry, and no
edits expected. Do not renumber, rename, or fold new content into them.

## Living notes

Living notes are `docs/research/R-NNN-<slug>.md`, numbered from `R-001`. The
`R-` prefix is the clean boundary between the frozen `00`–`09` seed corpus
above and the living series. Create one by copying
[`docs/research/TEMPLATE.md`](TEMPLATE.md).

Numbering is **local-and-cheap**: an `R-NNN` number is **not** reserved on
`origin/main` the way spec and ADR numbers are. A concurrent-session
collision (two `R-007`s) is a harmless nuisance, reconciled by hand at
promotion time — not board corruption. There is no `research.py` helper, no
index-regen, and no reservation apparatus (deferred per ADR-0054 pending a
real trigger).

This index is **hand-maintained** — there is no regen helper. Add a row when
you create a note; update its status/promotion when it resolves.

| ID | Topic | Status | Related / Promoted to |
|----|-------|--------|------------------------|
| [R-001](R-001-composed-pilot-run.md) | Composed autonomous UI pilot (jig × vellum × servo) — run record | OPEN | ADR-0059 accept flow; specs 071/104; servo 012-05; inbox 2026-08-30 |

## Hand-offs

Two documented hand-off directions, both convention-enforced (no linter, no
enforcement machinery):

**Inbox → note.** When an investigation captured as a
[`docs/inbox.md`](../inbox.md) entry grows thick, don't swallow the whole
thing inline — inbox entries should stay thin, one-liners. Instead, move the
depth into a research note and leave a one-line pointer in the inbox, e.g.
`[date] exploring X → R-004`.

**Note → decision / work.** When a note crystallizes, it promotes into the
right existing artifact:

- a [`docs/refinement-todo.md`](../refinement-todo.md) entry, if it lands on
  a *named deferred decision + trigger*;
- an ADR (`docs/decisions/`), if it lands on a decision to make now;
- a spec (`docs/specs/`), if it lands on committed work.

The downstream artifact cites `R-NNN` in its Context section. The note itself
flips its frontmatter `status` to `CONCLUDED` and gains a `Promoted to: …`
line pointing at the downstream artifact. If the investigation goes nowhere,
the note flips to `ABANDONED` instead, with `Promoted to: n/a`.
