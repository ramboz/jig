---
status: DRAFT
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 080: Semantic-index auto-activation

> Source: 2026-06-20 design discussion: Scout vs. tokensave for jig's
> `cache_read`-heavy token pattern, and how to make `scout daemon start` /
> `scout attach <path>` transparent when jig's Codex v2 adapter lands.

## Overview

jig's context-cost guidance now recommends a semantic/code index as the
turn-count lever: one graph query can replace several speculative Grep /
Read rounds. But the operational seam is still manual. A user has to know
whether Scout is installed, whether its daemon is running, and whether the
current repository is attached before the model can rely on it.

That manual setup is exactly the kind of low-level ceremony jig should hide
once a project has opted in. The desired behavior is:

- If no semantic index is installed, jig stays silent until the work shape
  makes a recommendation useful.
- If Scout (or a future provider) is installed but the project has not opted
  in, jig emits a one-time soft suggestion rather than doing heavyweight work.
- If the project has opted in, jig makes the index ready transparently:
  ensure the provider daemon is available, attach the canonical repository
  root if needed, then steer Claude Code and Codex toward index-first
  exploration.
- Every automatic action is instrumented locally so we can measure whether
  index activation actually reduces broad reads, raw Grep loops, and
  `cache_read` growth.

This spec deliberately ties the Claude side to the same implementation wave
as the Codex v2 adapter from spec 033. The point is not to add another
Claude-only hook now; it is to define the host-neutral contract and then
materialize it through both host adapters at once.

## Goals

1. **Provider-neutral activation contract.** Define a small local contract
   for semantic-index providers: detect availability, report attachment
   status, start or wake a daemon when safe, attach a repository when the
   project opted in, and return a compact status summary.
2. **Transparent after opt-in.** After a project records `auto_attach: true`,
   sessions should not require a human or agent to remember `scout daemon
   start` or `scout attach <path>`.
3. **No silent install or model download.** jig never installs Scout,
   tokensave, or any indexer, and never triggers first-run heavyweight setup
   without an explicit project/user opt-in.
4. **Same semantics for Claude Code and Codex.** The Claude and Codex host
   adapters render the same logical behavior in host-native hooks, primers,
   and skill/agent instructions.
5. **Instrument the effect.** Activation attempts, outcomes, and fallbacks are
   recorded in local, content-free telemetry so `usage.py` can compare
   indexed vs. non-indexed sessions.

## Non-goals

- **Choosing Scout as a mandatory dependency.** Scout is the first provider
  because it best matches jig's measured pattern today; the contract must not
  make jig require Scout.
- **Replacing the read-once/read-lean hooks.** Index activation complements
  the existing context-cost nudges. It does not remove the `PreToolUse(Read)`
  warning or thin-orchestrator guidance.
- **Global agent configuration management.** jig can recommend provider MCP
  registration, but it should not rewrite global Claude/Codex config as a
  side effect of scaffolding.
- **Indexing every worktree automatically.** Worktrees are often temporary.
  The helper must distinguish canonical repo roots from throwaway worktrees
  and avoid multiplying indexes accidentally.
- **Hard gating.** A missing, stale, or failed index never blocks a jig flow.
  It degrades to Grep/Read guidance.

## Assumptions

<!-- Spec 064-02 / ADR-0020: prove runnable-surface facts by probe before implementation. -->

- **Scout remains the first concrete provider.** Before implementation,
  re-probe the installed Scout CLI and MCP docs/behavior for: status/list
  commands, daemon autostart behavior, attach idempotence, worktree
  auto-attach policy, and Codex/Claude MCP install shape.
- **tokensave remains a viable fallback provider category.** Before
  implementation, re-probe whether tokensave's hooks conflict with jig's
  delegated-read guidance, especially any behavior that blocks Explore-style
  subagents.
- **Codex hook and skill surfaces may drift.** The Codex slices must verify
  current Codex project-local hooks, skills, custom agents, and plugin
  packaging before rendering files.
- **Telemetry can reuse or sibling the existing local JSONL pattern.** Reuse
  an existing local sink only if the event discriminator stays unambiguous;
  otherwise create a content-free sibling JSONL and teach `usage.py` to read
  it.

## Clarifications

- **Opt-in state:** record project intent in a small project-local file or
  manifest field, not in the user's global Scout/Codex/Claude config. The
  implementation slice decides whether that is `scaffold.json`,
  `.jig/index.json`, or another host-neutral location.
- **Activation rule:** after opt-in, `attach` is allowed to run automatically
  and must be idempotent. Explicit daemon start is a fallback only when the
  provider's cheap status/attach path proves the daemon is unavailable.
- **Worktree policy:** default to the canonical repo root. Temporary Codex /
  Claude worktrees should not be silently attached unless the project opts
  into per-worktree indexing.
- **User-facing noise budget:** missing provider -> silent most of the time;
  provider present but no opt-in -> one-time soft suggestion; provider
  opted-in but activation fails -> compact warning with fallback.
- **Implementation timing:** implement the Claude and Codex host-adapter
  materialization together with spec 033 v2 (`033-05` / `033-06`) so the
  behavior does not become another Claude-only seam.

## Decomposition

SPIDR split: **Interface + Path + Data**.

- **080-01 (Interface):** the provider-neutral activation contract, project
  opt-in state, and telemetry schema. This is the seam both hosts consume.
- **080-02 (Path):** Claude Code materialization: SessionStart/Prompt hook
  behavior, prompt/agent guidance, and Scout-first exploration when present.
- **080-03 (Path):** Codex materialization: the same behavior rendered through
  Codex scaffold/plugin adapters from spec 033 v2.
- **080-04 (Data):** usage/digest integration proving whether indexed
  sessions reduce raw read/search loops and context growth.

## Slices

- [080-01 - activation contract and opt-in state](slice-01-activation-contract.md)
- [080-02 - Claude Code adapter activation](slice-02-claude-adapter-activation.md)
- [080-03 - Codex adapter activation](slice-03-codex-adapter-activation.md)
- [080-04 - usage attribution digest](slice-04-usage-attribution-digest.md)

## References

- [spec 033: Host adapter portability](../033-host-adapter-portability/spec.md)
- [spec 055: Context-cost discipline](../055-context-cost-discipline/spec.md)
- [spec 056: Token-usage tracking](../056-token-usage-tracking/spec.md)
- [spec 057: Thin-orchestrator](../057-thin-orchestrator/spec.md)
- [spec 079: Semantic-index guidance](../079-semantic-index-guidance/spec.md)
