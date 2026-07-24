# The jig philosophy

> *jig (noun): a tool that guides other tools to work accurately and
> consistently.*

jig is an opinionated workflow scaffold for Claude Code and Codex projects. It
puts spec-driven slices, independent review, a memory layer, and deterministic
gates into your repo on day one — then gets out of the way. This page is the
**why**. For who it's for, the competitive landscape, and the full set of design
principles, see [product-vision.md](product-vision.md); for the day-to-day
lifecycle, see [workflow.md](workflow.md).

## The one idea

**jig encodes the AI-native workflow so you don't rediscover it session by
session.** Claude Code and Codex are powerful but deliberately unopinionated
about *project workflow*. Left to invent one, every team relearns the same
lessons over its first few sprints — and those lessons don't carry across
projects. jig is those lessons, encoded once.

## The scars jig is built from

Two years of AI-assisted coding leave the same marks on every non-trivial
project. Each jig feature exists to prevent one of them.

**Horizontal drift.** Left alone, an LLM refactors whole layers before
delivering anything end-to-end — and by the time the flow lands, it's broken
and the tokens are spent. jig splits work into thin *vertical slices* (SPIDR)
the model can actually finish.

**Invisible scope creep.** Without acceptance criteria written into the repo,
"done" is whatever the model decided it meant. jig makes the contract a
*spec*, so done is verifiable.

**Grading your own homework.** Sessions routinely end with a confident "done"
over half-built work. jig hands the finished slice to a *fresh reviewer* — a
separate prompt with read-only tools and no memory of the implementation — so
the gaps get caught by someone who didn't write them.

**The dumb zone.** Past roughly 40% context fill, a model's recall degrades. A
hundred-skill mega-pack burns that budget before your actual work loads. jig
is a *fixed-size, tiered* set — seven skills at the floor, not a marketplace.

**Session amnesia.** Sessions are short; projects aren't. Without somewhere
durable to put what was learned, every new session starts with a re-briefing.
jig keeps a *memory layer* — a hot cache, deep storage, and an inbox — so the
next session picks up where the last left off.

**Workflow babysitting.** Spec → review → implement → verify → reconcile, run
by hand every session, is a tax. jig encodes the loop as *skills and hooks* so
the machine runs it, not you.

## How jig thinks

A few beliefs are load-bearing — they shape every spec jig ships. The complete
set lives in
[product-vision.md § Design principles](product-vision.md#design-principles);
these are the ones you'll feel first.

**Hooks are deterministic; skills carry judgment.** Everything that *must*
happen is a hook. Everything that *should* happen when relevant is a skill.
Determinism is non-negotiable; pattern-matched triggering is best-effort.

**Bring your own depth; jig provides the floor.** Several jig skills are slim
baselines that step aside when you've installed a richer one. jig stays
opinionated about *workflow* and out of the way of *judgment skills you've
already invested in*.

**You can always own the scaffolding — it's one flag away.** Run
`scaffold-init --in-repo` and jig copies its machinery into your repo's
host-native project directory (`.claude/` or `.codex/`), where you can read and
edit it under version control rather than have it hidden behind a plugin runtime
you can't see. That is the opt-in, not the default
([ADR-0039](decisions/adr-0039-scaffold-defaults-to-plugin-mode.md)): copying
~130 files into every project pinned them to the version installed that day and
drowned the project's own history in jig internals. The principle is that
ownership stays *reachable and supported* — reach for it when the plugin can't be
assumed present (CI, cloud agents, teammates without jig, archival repos).

**Dogfood everything.** Every jig feature is built using jig's own spec
lifecycle. This repository's `docs/` is the worked example of what jig
produces — including this page.

## Common objections

**"Isn't spec discipline just overhead?"** It front-loads thinking you'd spend
anyway — either up front in the spec, or later debugging the thing the model
misunderstood. For trivial or throwaway work, skip it; jig is for the
non-trivial work where "done" has to mean something.

**"Why not install a bigger skill pack?"** Because context is a budget. Tools
you don't use crowd out the ones you do, and past the dumb zone the model gets
worse at using any of them. jig is deliberately small and defers to your
richer skills where you have them.

**"Does the reviewer subagent replace human review?"** No. It's an
*independent compliance check* — a fresh prompt plus read-only tools — **not a
hard sandbox** and **not a replacement** for human judgment. It catches the
gaps an implementer glosses over; you still own the call.

**"I'm not on Claude Code, or my repo isn't greenfield."** Codex is supported
alongside Claude Code in the v2 line. For an existing spec-driven repo, adopt
jig through the `/jig:migrate` skill rather than scaffolding fresh; for another
host, wait for a real adapter spec.

**"Do I have to use all of it?"** No. jig installs in tiers and gets out of
the way after day one. Start with the floor; reach for the rest when a real
pain actually shows up.

## See also

- **[product-vision.md](product-vision.md)** — the deep why: target users,
  competitive landscape, and the complete design principles.
- **[adoption-readiness.md](adoption-readiness.md)** — whether to adopt jig,
  what your repo needs first, and your first 30 minutes.
- **[workflow.md](workflow.md)** — the spec lifecycle and session workflow,
  end to end.
