# Adopting jig: a readiness guide

> A short, jig-sized guide for deciding **whether** jig fits your repo and
> **how** to start safely. For the *why* behind jig see
> [docs/product-vision.md](product-vision.md); for the workflow mechanics
> see [docs/workflow.md](workflow.md).

jig is a focused workflow scaffold, not an organization-wide AI-native
program. This page stays deliberately small — it points you at the right
next action and links out, rather than recreating a leadership curriculum.

## Who jig is for

- **Devs starting a new Claude Code project** who want spec-driven slices,
  reviewer gates, and a memory layer on day 1 instead of inventing them
  over the first few sprints.
- **Small teams who want a thin, opinionated baseline** they can extend
  with their own richer skills — jig's baselines defer to user-installed
  ones (see [README § Extension points](../README.md#extension-points)).
- **Existing spec-driven repos** that want to standardize on jig's layout
  — via the sibling `/jig:migrate` skill, not `scaffold-init`.

## Who should not adopt jig yet

- You want a **maximalist skill marketplace**, or tooling that makes
  architectural decisions for you — jig is intentionally small and stays
  out of judgment calls (product-vision § Target users, "Not for").
- Your work is **one-off scripts or throwaway spikes** — the spec
  lifecycle is overhead you won't recoup.
- You **can't keep specs/ADRs in the repo** (e.g. process forbids it) —
  jig's whole contract is that "done" is verifiable in version control.
- You're **not on Claude Code** today. Cross-tool support (Codex /
  `AGENTS.md`) is planned, not shipped — see
  [spec 033](specs/033-host-adapter-portability/spec.md).

## Prerequisites

- **Claude Code** — CLI, desktop, web, or an IDE extension.
- **A git repository** in reasonable health (a clean-ish tree; you can
  commit). jig reserves spec/ADR numbers on `origin/main` when a remote is
  present and falls back gracefully when it isn't.
- **Python 3** on `PATH` — every jig helper and hook is Python 3 (no `jq`,
  no Node required for the machinery itself).
- **A test command** for your stack (pytest / vitest / jest are
  auto-detected; override via a `.jig/test-command` file) — or an explicit
  acknowledgement that the project has none yet.

## Readiness checklist

Run through this before scaffolding. Each item is a quick yes/no:

- [ ] **Git repo health** — initialized, not mid-rebase, you can commit.
- [ ] **Claude Code access** — you can open this repo in a Claude Code
      session.
- [ ] **Python 3 available** — `python3 --version` works.
- [ ] **Test command** — you know your stack's test command, or you accept
      there isn't one yet (jig still works; `tdd-loop` reports the gap).
- [ ] **Specs/ADRs in-repo** — you're willing to keep `docs/specs/` and
      `docs/decisions/` under version control as the source of truth for
      "done."
- [ ] **Human review expectations** — you understand the reviewer subagent
      is an *independent compliance check* (a fresh prompt + read-only
      tools), **not** a replacement for human review, and that changes to
      `docs/conventions.md` still want human sign-off.

If every box is checked, you're ready to scaffold.

## Choosing an install shape

jig ships in two shapes (full detail in
[README § Installation](../README.md#installation)):

| Shape | Pick it when | Start with |
|---|---|---|
| **Scaffold** (default) | You want to **own and edit** the machinery in version control and customize it per-project. | `/jig:scaffold-init` |
| **Plugin** | You want **install-and-forget**; the machinery stays under `${CLAUDE_PLUGIN_ROOT}` and upgrades centrally. | `/plugin install jig@jig` |

When in doubt, scaffold — owning the scaffolding is jig's default posture
(product-vision § Design principle 7).

## Your first 30 minutes

1. **Scaffold** — run `/jig:scaffold-init` at your repo root. You get
   `docs/`, a hot-cache `CLAUDE.md`, hooks + skills under `.claude/`, and a
   completion check that reports "scaffold complete and verified."
2. **Read the worked example** — a fresh scaffold seeds
   `docs/specs/001-adopt-jig/` (a `DONE` reference spec to imitate) plus a
   `002-first-spec` `DRAFT` stub. Skim `001-adopt-jig` to see the shape of a
   finished slice.
3. **Set your vision** — run `/jig:vision-elicitation` to fill in
   `docs/product-vision.md` and `docs/architecture.md` (or fill them by
   hand). This is what every later slice is judged against.
4. **Cut your first spec** — `/jig:spec-workflow new <slug>`, then
   SPIDR-split it into thin vertical slices.
5. **Run one slice end to end** — implement → independent review →
   reconcile → DONE. See
   [docs/workflow.md § Session workflow](workflow.md#session-workflow).

## Evaluating the first few slices

After two or three slices, check that jig is paying for itself:

- **Slices are vertical.** Each delivered end-to-end value, not a
  half-built layer (the anti-horizontal-phasing guardrail).
- **The reviewer caught something real.** If the compliance pass never
  pushes back, your prompts may be too loose — see
  [workflow § Post-implementation review](workflow.md#post-implementation-review).
- **Memory survives sessions.** A new session picks up from the hot cache +
  `docs/memory/` without a re-briefing.
- **The board reflects reality.** `docs/specs/README.md` shows accurate
  per-slice state after `workflow.py status-board`.

If those hold, jig is doing its job. If a gap bites you twice, that's the
signal to file a spec — see product-vision § How new work enters jig.
