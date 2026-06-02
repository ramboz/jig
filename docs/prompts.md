# Prompt cookbook

> Copy-paste prompts for the two journeys you'll hit first: scaffolding a
> project, and taking a spec from idea to landed. jig's skills auto-trigger on
> description matching, so the natural-language prompts work as-is — the
> explicit `/jig:*` command is shown alongside, where one applies, for when
> you'd rather be deliberate. For the lifecycle these prompts drive, see
> [workflow.md](workflow.md); to decide whether jig fits your repo first, see
> [adoption-readiness.md](adoption-readiness.md).

## Recipe 1 — Scaffold a project

**Use this when:** you've just opened a repo in Claude Code and want jig's
workflow in place.

```text
Set up this project for AI-native development.
```

Equivalent explicit command:

```text
/jig:scaffold-init
```

**What happens:** jig writes `docs/` (vision, architecture, conventions,
workflow), a hot-cache `CLAUDE.md`, and — in the default scaffold mode — its
skills, hooks, and `settings.json` into `.claude/`. A greenfield repo is also
seeded with a worked-example spec (`docs/specs/001-adopt-jig`, already DONE)
plus a `002-first-spec` DRAFT stub, and the run ends with a "scaffold complete
and verified" check.

**Then set your vision** — this is what every later slice is judged against:

```text
Run the vision wizard to fill in our product vision and architecture.
```

```text
/jig:vision-elicitation
```

## Recipe 2 — Draft and implement a spec, end to end

The core loop. Each step is a copy-paste prompt; the lifecycle states
(`DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION → IN_PROGRESS →
REVIEWED → RECONCILED → DONE`) are jig's, enforced by the spec-workflow helper.

**1 — (optional) Scan the idea for ambiguity before you spec it.**

```text
Before we spec this, scan it for ambiguities and ask me the key questions:
<describe the feature>
```

Skill: `/jig:clarify`.

**2 — Draft the spec and SPIDR-split it into vertical slices.**

```text
Let's spec out <feature>. Reserve a spec number, then SPIDR-split it into
thin vertical slices — each one end-to-end, spike only as a last resort.
```

Skill: `/jig:spec-workflow new <slug>`.

**3 — Implement the first slice, test-first.**

```text
Pick up slice <NNN-01> and implement it. Write the failing test first, then
the code to make it pass.
```

This moves the slice to `IN_PROGRESS`; jig spawns the **`implementer`
subagent** to do the work test-first, driving the red-green loop
(`/jig:tdd-loop`).

**4 — Run the post-implementation review.**

```text
Run the post-implementation review on slice <NNN-01>.
```

A fresh reviewer checks the deliverable against the slice's acceptance
criteria (the compliance pass), plus a craft pass — and an architecture pass
if the slice declares `arch_review: true`. A `pass` verdict is required to
advance to `REVIEWED` (`/jig:independent-review`).

**5 — Reconcile.**

```text
Reconcile slice <NNN-01>: write the deviation log, update any docs that
changed, and run the reconciliation review.
```

Advances `REVIEWED → RECONCILED`.

**6 — Land it.**

```text
Land slice <NNN-01>.
```

jig checks readiness (tests green, DoD ticked, deviation log present) and
either merges directly or opens a PR (`/jig:slice-land`).

## Everyday prompts

| When you want to… | Say this | Skill |
|---|---|---|
| Pick up where you left off | "What's the next slice to work on?" | spec-workflow (status board) |
| Capture a decision | "Record this as an ADR: \<decision>" | `/jig:adr-workflow` |
| Save something for later | "Remember this: \<fact>" | `/jig:memory-sync` |
| Review a PR or diff | "Review this PR: \<url or diff>" | `/jig:pr-review` |
| Bring jig to an existing repo | "This repo already has specs — set up jig" | `/jig:migrate` |

## See also

- **[workflow.md](workflow.md)** — the full spec lifecycle and session workflow.
- **[adoption-readiness.md](adoption-readiness.md)** — whether and how to adopt jig.
- **[philosophy.md](philosophy.md)** — why the workflow is shaped this way.
