# Addition Prompt: Memory Layer for the Scaffold

> Paste into Claude Code mid-build, once the Tier 0 scaffold structure exists.
> Self-contained — references the existing design without requiring the full
> conversation context.

---

# Addition: Memory Layer for the Scaffold

We're adding a memory/context tracking layer to the scaffold, borrowing the three-layer pattern from Anthropic's official Productivity plugin (released for Cowork in May 2026). The reference article is here if you want the original framing: <https://www.howtogeek.com/claudes-hidden-project-management-system-is-a-game-changer/>

## Why we're adding this

The v1 design has strong workflow enforcement (specs, reviews, reconciliation, hooks) but is weak on **memory** — cross-session continuity, tribal knowledge, the glossary of project-specific terms and people. Devs and agents both lose time re-establishing context they shouldn't have to rebuild every session.

The Anthropic Productivity plugin solved this with a clean three-layer architecture. We're borrowing the architecture, **not** the task-management framing (we already have specs for project work; we don't need a second task system).

## What we're adding

### New artifacts

1. **`CLAUDE.md` extended** with a "Hot Cache" section. This file is already loaded at every session start. We add a structured section for frequently-referenced people, terms, acronyms, active features, and project codenames. Designed to cover most day-to-day context lookups in one place.

2. **`docs/memory/`** directory — deeper storage layer, loaded on demand when the hot cache misses. Starter files:
   - `glossary.md` — domain terms specific to this project
   - `learnings.md` — non-decisions, dead ends, "we tried X and here's why it didn't work" (the things ADRs don't capture)
   - `tooling.md` — the team's idiosyncratic tool choices and the reasoning
   - `people.md` — collaborators and their context (only if the wizard detects a team setting; skip for solo projects)

3. **`docs/inbox.md`** — thin capture layer. Things the agent surfaces from conversation that aren't yet decided on but shouldn't be lost. Triaged during reconciliation or session-end (becomes a spec, becomes an ADR, gets dropped, or stays parked).

### Lookup pattern

When the agent encounters an unknown reference, it follows:

```text
hot cache (CLAUDE.md)
  ↓ miss
docs/memory/ search
  ↓ miss
ask the user
  ↓ answered
persist to the appropriate file
```

This is the article's pattern, exactly. The persistence step is what makes it valuable — each unknown reference is asked once, never twice.

### Auto-detection hooks

Two new hooks:

1. **Unknown-reference detection** (UserPromptSubmit). Scans the user's message for proper nouns, acronyms, and project codenames that don't resolve against the hot cache or memory folder. Surfaces them at the start of the response — either asks once during the reply, or batches them as "things I don't recognize: [list]." Persists answers to `CLAUDE.md` (if frequent) or `docs/memory/glossary.md` (if niche).

2. **Task-shape capture** (Stop hook, so it sees the full exchange). Detects language patterns in the session that suggest unstructured task capture: "we should also...", "don't forget to...", "TODO:", "later we'll need to...". Surfaces them for triage with three options: (a) add to existing spec NNN, (b) draft a new spec, (c) park in `docs/inbox.md`. Does **not** auto-create specs without confirmation — captures are explicit decisions.

### One new skill

**`memory-sync`** — handles bulk memory updates.

- **Auto-triggers** on phrases like "remember this," "save this for later," "let's add this to the glossary."
- **Auto-fires at session end** (via Stop hook) to consolidate new learnings into `CLAUDE.md` and `docs/memory/`.
- **Also explicitly invocable** as `/memory-sync` for users who want to deliberately trigger a sync and see what changed.

Note the deliberate design choice here: small updates happen automatically (auto-trigger), but the bulk operation is also explicit-invocable so users can see what changed when they want trust visibility. Anthropic's own plugin made the bulk operation explicit-only — we're going one step further with auto-detect + explicit-when-wanted.

## What we're explicitly NOT doing (deliberate exclusions)

- **No `TASKS.md` flat task list.** We have specs. One source of truth for project work. The article's `TASKS.md` is for personal todo management; out of scope for a code project scaffold.
- **No `dashboard.html` Kanban view.** Specs have their own status board at `docs/specs/README.md`.
- **No external integrations (Asana, Notion, Todoist).** Useful for personal productivity, wrong scope for codebase work. If a team uses GitHub Issues or Linear, specs link out; we don't reimplement.
- **No `--comprehensive` deep scan over emails / calendar / chats.** Wrong scope. Our agent works on a codebase, not a personal inbox.

## How this fits into the existing scaffold

The memory layer is **Tier 0** because it's foundational — every skill benefits from it, and the cost is small (one directory, one extension to an existing file, two hooks, one skill).

It connects to the other Tier 0 pieces:

- **`scaffold-init`** seeds `docs/memory/` with starter files and adds the Hot Cache section to `CLAUDE.md`.
- **`spec-workflow`** consults the glossary when drafting specs and surfaces unknown terms during the spec review.
- **`independent-review`** reads from the memory layer for context but does not write to it (reviewers don't get to define glossary).
- **`contracts`** can surface naming inconsistencies by cross-referencing the glossary against contract type names.

The reconciliation phase also gets a small extension: during reconciliation, the agent checks if any new terms / patterns / people emerged during implementation that should be persisted to memory. This is the natural moment to consolidate.

## Implementation order suggestion

If we're mid-build on Tier 0, the right sequence is:

1. **First:** extend the wizard (`scaffold-init`) to generate the memory layer files. This is the cheapest piece and unlocks everything else.
2. **Second:** the `memory-sync` skill, with explicit invocation working before auto-trigger. Test the lookup pattern manually.
3. **Third:** the unknown-reference detection hook. This is the one that delivers "Claude noticed something it didn't know" magic, but it depends on the memory files existing.
4. **Fourth:** the task-shape capture hook. Useful but lower priority — most teams will be fine with explicit `inbox.md` entries until this proves out.

## Open question to flag

The article's pattern relies on the agent asking the user during the response when it hits a memory miss. This is a small interruption that breaks flow. We should test whether **batching** unknown references at the end of the response (so the user sees them after the substantive reply) works better than interrupting mid-response. My instinct is batched-at-end is better — fewer interruptions, easier to ignore if the user is in a hurry. Worth dogfooding both and seeing.

## Reference for the design rationale

The full reasoning for this addition (including what was deliberately excluded from the Anthropic plugin's design and why) is in the research notes. If you've already saved those into the repo at `docs/research/`, the relevant file is `08-research-ecc-lessons.md` (which now also covers the Productivity plugin findings). If not, the short version is: borrow the architecture, drop the task management framing.

---

## Notes on using this prompt

**When to paste it.** Once you've at least scaffolded the repo structure and the Tier 0 directory layout exists. If you paste it before the `scaffold-init` skill has been started, Claude Code will fold it in cleanly. If you paste it after `scaffold-init` is mostly built, it'll need to extend the wizard rather than start fresh — also fine, but flag it.

**What to expect.** Claude Code should ask whether to fold this into the existing `scaffold-init` spec or treat it as a separate spec. Either is defensible; preference: **separate spec**, because the memory layer can ship independently of the wizard and the spec separation keeps the deliverables sharp.

**Watch for scope drift.** The "what we're NOT doing" section is there because it'd be very easy for the agent to over-implement (adding `TASKS.md`, building the dashboard, integrating Asana). If you see it heading there, push back and point at that section.
