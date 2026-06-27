---
status: DRAFT
dependencies: [083-04, 083-07]
last_verified:
frame_review: true  # host-payload/hook-shape assumptions can only be proven on
#                   # the actual Codex runtime — the whole point of this slice.
---

## Slice 083-08 — Codex host validation (HANDOFF — owned by the maintainer on Codex)

> **Tracking-only stub (authored 2026-06-26).** This file makes 083-08 a tracked
> slice so spec 083's derived rollup stays `IN_PROGRESS` while the Codex-side work
> is open — it does **not** do that work. The Claude-side Phase-2 build (083-04..07)
> is DONE and shipping; **083-08 is deferred to the maintainer on the Codex
> runtime** (out of Codex tokens at hand-off, 2026-06-26). Full contract lives in
> [spec.md § Slice 083-08](spec.md). Pick this up by fleshing out the AC/DoD below
> and transitioning DRAFT → … on Codex.

**Goal:** Prove (or honestly degrade) Phase 2's deterministic mechanisms — the
083-04 Stop-hook scan and the 083-07 in-flight capture — on the **Codex** host,
which is unverified for the Stop-payload shape, whether `AskUserQuestion` (or its
Codex analog) is hookable with a structured answer, and whether the
`PostToolUse`/`UserPromptSubmit` hook points exist. jig is dual-host
([ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)), so
a mechanism that silently works only on Claude is a half-shipped feature.

**DoR:**
- ✅ 083-04 (scan) + 083-07 (in-flight capture) DONE on the Claude side, with
  Claude-side host assumptions stated and fallbacks wired (degrade-to-scan /
  degrade-to-nudge).
- ⏳ Requires the actual Codex runtime to confirm payload/hook shapes — cannot be
  proven from the Claude side by inspection.

**Acceptance Criteria (to be finalized on Codex):**

1. A host-parity fixture/test asserting, on Codex: (a) the Stop payload exposes
   the session content the scan reads; (b) the decision-signal patterns fire on a
   Codex transcript fixture; (c) the in-flight hook point for the structured
   answer exists, or is documented absent → fall back to scan + judgment prompts.
2. A documented **host-capability matrix** (Claude vs Codex) per Phase-2
   mechanism: `supported` / `degraded-to-nudge` / `unsupported`.
3. Any Codex host-transform adjustments to the hooks (mirroring the standard
   `CLAUDE.md→AGENTS.md` / `CLAUDE_PLUGIN_ROOT→PLUGIN_ROOT` transforms).

**DoD (to be finalized on Codex):**
- [ ] Parity harness green on Codex (or honest `degraded`/`unsupported` cells with
      the fallback wired).
- [ ] Capability matrix committed.
- [ ] `build_host_packages.py --check` stays green with the Codex hook copies.
