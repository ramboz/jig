---
status: DONE
dependencies: [113-04]
last_verified: 2026-09-16
arch_review: true  # permission-decision translation + the mapped/unmappable inventory
---

## Slice 113-05 — enforcing-hooks-and-permissions

**Goal:** jig's gates keep their teeth under Copilot — the permission-decision
hooks (spec-gate, review-evidence, bug-closure) translated to Copilot's
`permissionRequest`/`preToolUse` decision schema, plus the security-floor
permissions rendered in Copilot syntax — with every hook **mapped or explicitly
recorded as unmappable**.

**DoR:**
- ✅ 113-04 done (advisory-hook translation + schema proven).
- ✅ 113-01 finding recorded Copilot's permission-decision (allow/deny) response
  shape.
- ⚠️ **113-04 input adapter is advisory-only (fail-open) — enforcing needs an
  output/exit path (arch + compliance review of 113-04):** `copilot_hook_adapter.py`
  (Copilot-render-only) translates Copilot camelCase hook *input* → jig's snake_case
  script input and is **always-exit-0**. Enforcing hooks route through the SAME
  adapter but 113-05 MUST add a runtime **output/exit post-processing** path: capture
  the child script's exit code + stdout and translate `exit 2` / `block_reason` →
  Copilot `permissionDecision:"deny"` (+ `permissionDecisionReason`), via a per-hook
  **advisory-vs-enforcing mode** (e.g. an extra argv). Reusing the advisory adapter
  verbatim would convert `exit 2` → `exit 0` with no `deny` and **silently lose the
  gate's teeth** (ADR-0061 "keep their teeth / degrade visibly, not silently").
  `translate_hook_protocol`'s response half (`block_reason→deny`) is currently
  render-layer-only/unwired — decide here whether the runtime response mapping lives
  in the adapter (which is what sees the runtime `exit 2`), and drift-guard any
  duplicated mapping. **Verify enforcement by positive confirmation (a real deny),
  not absence-of-error** — the advisory adapter masks failures, so the plugin-root
  command-path spelling residual (still unverified) hides behind exit-0 until proven
  by a firing deny.

**Acceptance Criteria:**

1. **Decision-schema translation.** Enforcing hooks render to Copilot's
   allow/deny decision schema so a blocking gate actually blocks in a Copilot
   session (or deterministic substitute). A test asserts a translated enforcing
   hook denies the disallowed action.
2. **Mapped-or-unmappable inventory (invariant).** The slice produces an explicit
   inventory: every jig hook is either mapped to a Copilot event with equivalent
   enforcement, or recorded as unmappable with the residual documented (mirroring
   servo ADR-0028's honesty). No jig hook is silently dropped. A Claude event
   with no Copilot equivalent degrades **visibly** (documented residual), never
   silently.
3. **Permissions floor (owner-reshaped — see deviation log).** jig's security-floor
   destructive-command set is *enforced* under Copilot. Because Copilot CLI has **no
   persistent, repo-committable tool-deny** mechanism (`--deny-tool` is session-scoped
   only; there is no `settings.json` `deniedTools` key), the floor renders as a real
   **enforcing `preToolUse` deny-hook** (`jig-permissions-floor.json` →
   `copilot_permissions_floor.py`) that denies (exit 2) every pattern in
   `_PERMISSIONS_DENY_DEFAULTS` — **not** a dead `settings.json`. A test asserts the
   floor denies a destructive command, allows a safe one, and that no dead
   `settings.json` is emitted. (Original AC3 asked for a `settings.json` render with
   `shell(git:*)` syntax; that would have been a silently-inert file — the reshape to
   an enforcing hook is what actually keeps the floor's teeth. See the deviation log.)

**DoD:**
- [x] All ACs pass; full suite green (4807 tests, 0 failures, 7 skipped); drift
      `--check` clean; `uvx ruff check .` clean; new tests fail when the feature is
      removed (the enforcing-deny + anywhere-match pins are non-vacuous).
- [x] Inventory written where a maintainer will find it — architecture.md's
      host-adapter section documents `_JIG_HOOK_INVENTORY` (the mapped-or-unmappable
      inventory); residuals homed (MAPPABLE→113-06 AC6; live-fire path-spelling +
      `scripts/` shipping→113-06; refinement-todo carries the path-rewrite entry).
- [x] Reviewed by `reviewer` subagent — compliance (pass) + craft (pass) + arch
      (pass, after the inventory-home blocker was cleared in-review); verdicts under
      `reviews/slice-05-{compliance,craft,arch}.md`.
- [x] Deviation log + reconciliation sweep produced (below).

**Anti-horizontal-phasing check:** After this slice jig's enforced lifecycle
gates work for a Copilot user (or are documented as degraded) — the core value.

### Deviation log (after reconciliation)

- **AC3 reshaped — `settings.json` → enforcing `preToolUse` deny-hook (owner-approved).**
  AC3/DoR originally asked the floor to render into `.github/copilot/settings.json`
  with `shell(git:*)` syntax. Discovery (grounded in Copilot CLI 1.0.86-0 +
  `api.schema.json`): Copilot has **no persistent, repo-committable tool-deny**
  mechanism — `--deny-tool` is session-scoped only; there is no settings.json
  `deniedTools` key (`allowedUrls`/`deniedUrls` are the only persistent permission
  keys and they don't gate shell commands). A rendered `deniedTools` file would have
  been a dead, silently-inert file — the exact "gate quietly stops blocking" failure
  ADR-0061 forbids. Owner-approved reshape → a Copilot-only enforcing `preToolUse`
  deny-hook (`copilot_permissions_floor.py` + `jig-permissions-floor.json`) denying
  (exit 2) every `_PERMISSIONS_DENY_DEFAULTS` pattern. The dead settings.json render
  path was removed; `test_no_dead_settings_json_rendered` guards its return. AC3
  prose corrected inline (ADR-0010 live-prose; slice not yet DONE).
- **Enforcing adapter mode (built).** The 113-04 advisory adapter was always-exit-0
  (fail-open). 113-05 added `copilot_hook_adapter.py --enforce`: it preserves the
  child's exit code (exit 2 → deny), emits `{permissionDecision:"deny",
  permissionDecisionReason}`, and fails **closed** on spawn error. Advisory mode
  stays fail-open. spec-gate + secret-scan render with `--enforce`; the 3 advisory
  hooks (113-04) stay advisory. The runtime response mapping lives in the adapter
  (which sees the runtime exit 2), NOT the render-layer `translate_hook_protocol`
  (still unwired repo-wide); the emitted deny shape is drift-guarded by tests.
- **113-04 hook-schema bug corrected here (folded, not reopened).** 113-04 shipped
  Claude's **nested** `{event:[{matcher, hooks:[{command, timeout}]}]}` shape, which
  Copilot **cannot load** — Copilot's authoritative schema (GitHub hooks reference +
  `api.schema.json` `HookType`/`DiscoveredHook`) is the **flat** `{version:1,
  hooks:{<camelCaseEvent>:[{matcher?, type:"command", bash, timeoutSec}]}}`. Fixed
  `render_copilot_hook_file` centrally → ALL rendered hooks (advisory + enforcing +
  floor) now use the flat schema; the 3 advisory JSONs from 113-04 were re-rendered.
  Folded into 113-05 (where `render_copilot_hook_file` was already being modified)
  rather than reopening DONE 113-04 — arch-endorsed seam call (ADR-0010). **The
  113-04 record's shipped-wrong-schema fact needs a `## Amendments` note — PENDING
  explicit owner approval (ADR-0010 / spec 102); surfaced, NOT self-applied.**
- **Anywhere-match parity divergence (deliberate, more-protective).**
  `matched_pattern` uses an **unanchored** `regex.search`, so a destructive token
  matches ANYWHERE in a command line — including inside a benign command that merely
  mentions it (`echo "…rm -rf…"`). Claude's native prefix-anchored `permissions.deny`
  would ALLOW these. The floor deliberately blocks MORE than Claude, never less
  (fail-safe for a security floor; also the only way to express the 2 mid-string
  force-push variants Copilot's prefix-only `shell()` syntax can't). Pinned by
  `test_anywhere_match_is_a_deliberate_divergence_from_claude_anchoring` so a future
  "anchor it to match Claude" change — which would silently NARROW the floor — trips
  red + a review.
- **Enforce-mode fail-open on an untranslatable payload (deliberate seam).** In
  `--enforce` mode, if `translate_payload` raises, the adapter forwards RAW bytes to
  the gate, which then can't read its snake_case fields and exits 0 (allow) — a
  malformed/untranslatable payload fails OPEN even in the enforcing path. Deliberate:
  a gate can't block on data it can't parse, matching the gates' own fail-open
  posture; logged so it is a conscious choice, not an accident.
- **`preToolUse` key single-sourced (craft/arch nit).** `render_permissions_floor_hook`
  hardcoded the top-level `"preToolUse"` key; changed to
  `cls.copilot_event_name("PreToolUse")` so the event spelling has one source
  (`CLAUDE_TO_COPILOT_EVENTS`). Byte-identical output (drift `--check` clean).
- **Arch-review blocker (inventory home) — raised + cleared in-review.** The
  inventory marked 9 advisory hooks (11 registrations) MAPPABLE "homed to 113-06,"
  but 113-06 had no AC owning the render and its DoR falsely claimed the renderer
  already emitted the full content. Fix: added slice-06 **AC6** (renders every
  MAPPABLE hook via the advisory path, flips each MAPPABLE→SHIPPED, test asserts no
  MAPPABLE remains — mechanically closing the ADR-0061 invariant); corrected the false
  DoR; reworded all 11 inventory notes + 2 header pointers to the real home. Arch
  reviewer re-verified: blocker cleared.

### Reconciliation sweep

- **docs/architecture.md** — `updated`: host-adapter section now documents the
  enforcing gates (adapter `--enforce`, exit-2→deny, fail-closed), the permissions-floor
  reshape (Copilot-only enforcing `preToolUse` deny-hook; no persistent tool-deny),
  and `_JIG_HOOK_INVENTORY` as the mapped-or-unmappable invariant's maintainer-facing
  home (DoD requirement).
- **docs/specs/113-06 (slice-06)** — `updated`: NEW **AC6** owns rendering the
  remaining MAPPABLE advisory hooks (full parity); DoR corrected (no longer claims the
  renderer emits the full `hosts/copilot/` content by 113-05).
- **docs/refinement-todo.md** — `no-op (already homed)`: the `${CLAUDE_PLUGIN_ROOT}`
  path-rewrite entry (mechanism landed 113-04; spelling live-verification + `scripts/`
  shipping → 113-06) already carries the residual; nothing new to add this slice.
- **113-04 record `## Amendments`** — `PENDING owner approval`: the shipped-wrong
  (nested) hook schema is a canon-artifact conflict on a DONE record; per ADR-0010 +
  spec 102 an amendment needs explicit owner approval. Surfaced to the owner; not
  self-applied. The correction itself is live in 113-05 (flat schema re-rendered).
- **Architecture impact / ADR** — `no-op` (no new ADR): implements ADR-0061; the AC3
  reshape + anywhere-match divergence are within its "keep their teeth / degrade
  **visibly**" invariant (documented + tested, not silent).
- **docs/conventions.md / Lightweight decisions / Inbox** — `no-op`.
- **Primer hygiene (CLAUDE.md)** — `no-op`: spec 113 not closed (113-06 remains).
- **hosts/ regeneration** — `updated`: `build_host_packages.py` re-emitted the Copilot
  package (enforcing hooks + floor + flat-schema advisory hooks) + the scaffold.py /
  adapter mirrors under `hosts/{claude,codex}`; `--check` clean.
- **Status board** — `updated (regenerated)` after the DONE transition.
- **Memory-sync** — light; per-slice progress on the board; `copilot-migration-tri-host`
  project memory updated at spec close (113-06).
