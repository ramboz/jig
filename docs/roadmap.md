# Roadmap

> Milestone view of jig's work. This is the **overlay**: it groups specs into
> releases and names the integration branch each milestone is built on. It is
> **not** a second status board — per-slice truth (DONE / DRAFT / DEFERRED)
> lives in [docs/specs/README.md](specs/README.md), regenerated from each
> branch's own `spec.md` files by `workflow.py status-board`.
>
> **Non-duplication rule.** A spec's per-slice status is recorded once, on the
> branch where the work lives. The roadmap never restates DONE/DRAFT per slice —
> it points at the branch and the board. When an integration branch lands on
> `main`, `main`'s board absorbs its rows automatically; nothing here needs
> hand-reconciling.

## Milestones

### 1.x — Spec-driven workflow on Claude Code _(current · shipped on `main`)_

The released line. A complete spec-driven development scaffold for Claude Code:
SPIDR slicing, the lifecycle state machine, the review-evidence gate
([ADR-0014](decisions/adr-0014-review-evidence-model.md)), the security floor
([ADR-0013](decisions/adr-0013-security-floor-policy.md)), code-health
([ADR-0017](decisions/adr-0017-scaffolded-code-health.md)), context-cost and
thin-orchestrator discipline ([spec 055](specs/055-context-cost-discipline/spec.md) /
[057](specs/057-thin-orchestrator/spec.md)), and the vocabulary barrier
([spec 065](specs/065-lower-vocabulary-barrier/spec.md)).

- **Branch:** `main`
- **Latest release:** 1.12.0
- **Status:** ongoing — new single-host capability work continues to land here.

### 2.0 — Multi-host portability _(in progress · integration branch `v2`)_

Decouple jig's workflow model from any one LLM harness. One canonical source
tree; materialized, host-native files per supported host (**copy prose, share
code**). Adds Codex as a first-class host alongside Claude Code, with symmetric
packaging and install paths.

- **Branch:** `v2` (kept current with `main`; see "Working model" below)
- **Board:** the `v2` branch's [status board](specs/README.md) is the
  per-slice source of truth for these specs until `v2` lands.

| Spec | Theme | Status on `v2` |
|------|-------|----------------|
| [033 — host-adapter-portability](specs/033-host-adapter-portability/spec.md) | Host-adapter architecture; Codex scaffold + plugin packaging + TOML custom-agent adapter | IN_PROGRESS — 033-06/07 DONE, 033-05 deferred, 033-01..04 drafted |
| 059 — codex-port-polish _(on `v2`)_ | Parity polish after the core port: host-aware migrate, hook-trust onboarding, install smoke, override deferral, role-capability dogfood | **DONE** (all slices) |
| 061 — dual-host-plugin-artifacts _(on `v2`)_ | Symmetric Claude + Codex plugin packages, drift guard, host-explicit release zips (ADR-0018) | IN_PROGRESS — 061-01..05 DONE, 061-06/07 (install verification) drafted |

### Future — Federation & beyond _(exploring)_

Longer-horizon work that builds on the multi-host foundation but is not gated
into 2.0.

| Spec | Theme | Status |
|------|-------|--------|
| [034 — federation-tier](specs/034-federation-tier/spec.md) | Multi-repo orgs: cross-repo specs, shared ADR/glossary layer, federation host adapter | DRAFT |

## Working model

- **`main` is the released trunk.** Single-host capability work lands here
  directly and ships in the 1.x line.
- **`v2` is the 2.0 integration branch.** Multi-host work lands on `v2`. It is
  kept current with `main` by **merging `main` → `v2`** periodically (one-shot
  conflict resolution, no history rewrite) — not by rebasing the shared branch.
- **When 2.0 is ready, `v2` merges into `main`** as the 2.0 release. At that
  point its specs' DONE rows flow into `main`'s board and these roadmap entries
  collapse into the 1.x-style "shipped" record.
