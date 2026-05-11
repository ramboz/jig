---
status: DRAFT
skill: scaffold-init
---

# Spec 001: scaffold-init

## Overview

The `scaffold-init` skill runs a discovery wizard that initializes an AI-native development workspace. It produces the full `docs/` structure, `CLAUDE.md` with Hot Cache section, hook infrastructure, and `scaffold.json` install-state manifest.

## SPIDR Analysis

| Technique | Question | Outcome |
|---|---|---|
| S — Spike | How do we reliably detect LLM/agent work, CI, team size? | Spike 001a (docs/spikes/) — not gated for slice 001-01 |
| P — Path | Greenfield vs. existing repo with signals? | 2 slices (001-01, 001-03) |
| I — Interface | Q&A wizard vs. filesystem-inference only? | Slice 001-05 (last) |
| D — Data | Stub docs vs. content-filled? | Slice 001-02 |
| R — Rules | Draft markers, deferred decision tracking? | Slice 001-04 |

---

## Spike 001a — signal-detection

**STATUS: DRAFT**

Tracking artifact: [docs/spikes/spike-001a-signal-detection.md](../../spikes/spike-001a-signal-detection.md)

This spike is NOT a gate for slice 001-01. Slice 001-01 uses hardcoded defaults.

---

## Slice 001-01 — greenfield-scaffold

**STATUS: DRAFT**

**Goal:** Happy path wizard — no signal detection, default tier install (Tier 0 + Tier 1), produces complete docs/ skeleton, CLAUDE.md with Hot Cache, hooks.json, and scaffold.json manifest.

**DoR (Definition of Ready):**
- No prior slice dependency.
- spec.md (this file) is STATUS: READY_FOR_IMPLEMENTATION.

**Acceptance Criteria:**
1. Running `/jig:scaffold-init` on an empty directory produces the full expected tree (docs/, CLAUDE.md, .claude/hooks/, scaffold.json).
2. `scaffold.json` is written with: installed tiers, timestamp, jig version.
3. All scaffolded docs carry `Status: Draft (wizard-generated)` marker at the top.
4. `docs/memory/glossary.md`, `learnings.md`, `tooling.md` are seeded with stub content.
5. `docs/inbox.md` is created with a header explaining its purpose.
6. `CLAUDE.md` is generated from `templates/CLAUDE.md.template` and includes a Hot Cache section.
7. After scaffold-init completes, `docs/memory/people.md` is NOT created (solo project detection).
8. Bootstrap note: the spec-gate hook for `docs/conventions.md` activates AFTER scaffold-init. Verify post-completion: editing conventions.md without approval is blocked.

**DoD (Definition of Done):**
- [ ] All ACs pass
- [ ] Implementer test coverage for the scaffold tree output
- [ ] Reviewed by `reviewer` subagent
- [ ] Deviation log produced (if any deviations)
- [ ] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ Running `/jig:scaffold-init` produces a complete, runnable project structure end-to-end.

---

## Slice 001-02 — doc-content

**STATUS: DRAFT**

**Goal:** Scaffolded docs have structured content — not empty files. Deferred-decision stubs, architecture template, conventions template, memory layer stubs.

**DoR:** Slice 001-01 STATUS: DONE.

**Acceptance Criteria:**
1. `architecture.md` has a tech-stack section with `> Deferred — no signal from initial pitch.` stubs for undefined choices.
2. `workflow.md` documents the spec lifecycle states and hook strictness profiles (as deferred).
3. `conventions.md` uses the rule → **Why:** → **How to apply:** format throughout.
4. `refinement-todo.md` lists ≥3 wizard-deferred decisions with resolution triggers.
5. Memory stubs: glossary, learnings, tooling have meaningful starter content (not just headers).
6. `docs/inbox.md` exists with a header explaining its purpose.
7. `CLAUDE.md` Hot Cache section is populated with the project name and empty term/spec lists.
8. `docs/memory/people.md` created ONLY when ≥2 git contributors OR user confirms team context.

**DoD:** Same as 001-01.

**Anti-horizontal-phasing check:** ✅ Produces end-to-end output with improved content quality.

---

## Slice 001-03 — signal-detection

**STATUS: DRAFT**

**Goal:** Wizard detects project signals from the filesystem and selects appropriate tiers.

**DoR:** Spike 001a STATUS: DONE.

**Acceptance Criteria:**
1. LLM/agent file presence → Tier 2 (`eval-harness`) is offered.
2. CI files present → hook strictness default set to `strict` (recorded in scaffold.json, not yet enforced).
3. Existing test suite → `tdd-loop` (Tier 1) auto-installed.
4. Signal detection produces a `brief.md` summary at the project root.
5. No false positives on a bare `git init` repo (no signals → default tiers, no Tier 2 offered).

**DoD:** Same as 001-01.

**Anti-horizontal-phasing check:** ✅ Still end-to-end; adapts output to project context.

---

## Slice 001-04 — deferred-decisions

**STATUS: DRAFT**

**Goal:** `refinement-todo.md` is structured and complete — not just a flat list.

**DoR:** Slice 001-02 STATUS: DONE.

**Acceptance Criteria:**
1. Each entry format: `## Decision: <name>` / `**Deferred:** <reason>` / `**Resolution trigger:** first <X>-touching spec`.
2. Decisions categorized: Architecture, Conventions, Operations.
3. After 3 reconciled specs in a dogfood project, scaffold-reconciliation check (skill, not hook) suggests promoting stale deferred items.

**DoD:** Same as 001-01.

**Anti-horizontal-phasing check:** ✅ Adds governance layer to existing output.

---

## Slice 001-05 — wizard-qa

**STATUS: DRAFT** _(implement last)_

**Goal:** Q&A interaction mode — wizard asks project-scoping questions before generating output.

**DoR:** Slice 001-03 STATUS: DONE.

**Acceptance Criteria:**
1. 3-5 targeted questions: runtime/language, team size, existing CI, LLM/agent work planned.
2. User answers override filesystem inferences.
3. Questions are skippable — filesystem inference used as fallback if user skips.
4. If all questions skipped, output is identical to 001-03 (pure inference mode).

**DoD:** Same as 001-01.

**Anti-horizontal-phasing check:** ✅ UX layer on top of existing functional output.
