---
status: DRAFT
skill: scaffold-init
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 106: Autonomy governance plane

> **Status: recorded, not yet built.** [ADR-0051](../../decisions/adr-0051-autonomy-governance-plane.md)
> is Proposed and this spec is reserved; the `scaffold-init` changes below are not
> implemented in the branch that introduced this record. Left DRAFT deliberately.
> Part of the long-horizon-autonomy bridge (the `oh-my-cli` follow-on).

## Overview

Implement [ADR-0051](../../decisions/adr-0051-autonomy-governance-plane.md): make
jig **scaffold** the out-of-band governance teeth it currently only recommends,
and make **two-principal identity separation** a checkable precondition for
running a repo unattended.

Two problems this closes:
1. **No scaffolded plane.** `jig-spec-gate.sh` recommends CODEOWNERS + protected-
   path CI + branch protection but jig writes none of it. An autonomous loop on a
   fresh repo has only soft nudges between it and its own governing artifacts.
2. **Identity collapse.** GitHub's owner-approval gates key off *author identity*.
   If the agent commits/pushes/opens PRs as the human, there is one principal:
   the human can't approve their own PR and "require review from a non-author" is
   unsatisfiable — the gate is fictional. A governance plane on a single identity
   is theatre.

Scope: scaffold `CODEOWNERS` + a protected-path CI workflow; add `protected_paths`
to `scaffold.json` (read by existing soft hooks to nudge in-boundary; CI enforces
out-of-boundary); formalize the surface-and-stop governance-proposal routing rule
(spec 102); and add the identity-separation precondition, whose deterministic
check (run-identity ≠ merge-identity) is surfaced by the servo autonomy-readiness
gate (servo ADR-0029 / servo spec 023).

## Assumptions

- Target host is GitHub (CODEOWNERS + branch-protection semantics). Non-GitHub
  forges are out of scope for this spec.
- The runtime can observe run-identity and the configured merge principal well
  enough to compare them. The exact signal is environment-specific and must be
  pinned in slice 106-01 (grounding-by-probe, ADR-0020) — not assumed here.
- `scaffold-init` / `scaffold.json` and the `entry-gate` / `boundary-warn` hooks
  are the integration points; confirm their current shape at slice DoR.

## Decomposition

One slice for this record: the scaffolded artifacts (CODEOWNERS + CI + config
key) and the identity-separation precondition are the minimal coherent governance
plane — a scaffolded CI firewall with no identity separation is exactly the
theatre this spec exists to prevent, so they ship together. SPIDR axis:
**Interfaces** (scaffold output + `scaffold.json` schema) + **Rules** (routing +
identity precondition). Later slices may split CODEOWNERS-owner resolution for
solo-maintainer repos if it proves non-trivial.

## Slices

- [106-01 — scaffold the protected plane and the identity-separation gate](slice-01-scaffold-protected-plane-and-identity-gate.md)
