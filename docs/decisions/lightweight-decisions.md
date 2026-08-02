# Lightweight Decisions

Small shipped decisions that fall outside spec slices but carry durable rationale:
brand/icon swaps, cosmetic CSS polish, UI string or translation choices, scoped
visual decisions, and "future sessions should/should not override this" notes.

## Routing rubric — where does this decision land?

Triage each settled decision to exactly **one** home:

| Route | Criterion |
|---|---|
| **ADR** | A load-bearing design choice with rejected alternatives — one a future agent would need to know about to avoid undoing it — warrants an ADR even when it changes no module boundary or public contract. Also: any change to a module boundary, public contract, or cross-cutting policy. |
| **Lightweight record (here)** | Settled, local, bounded (one screen / component / string / asset), with no real rejected alternatives — and a future agent would need to know it to avoid undoing it. |
| **`refinement-todo.md`** | Still *open* — has a resolution trigger; not shipped yet. |
| **Drop (write nothing)** | Ephemeral / trivial / already obvious from the code or a commit message. |

The **ADR** row quotes the single canonical trigger sentence from
[ADR-0031](adr-0031-load-bearing-decision-adr-trigger.md); the *same* sentence
appears in both reconcile checklists and the memory-sync session-end prompt, so
the "when is an ADR required?" policy can't drift across surfaces.

Record a lightweight entry with the helper (idempotent append):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/memory-sync/decisions.py" add-lightweight \
  --title "<short title>" --decision "<what>" --context "<why>" --scope "<where>"
```

## Template

```markdown
### [Date] — [Short title]

**Decision:** _what was decided_

**Context:** _why — constraint, user feedback, design call_

**Scope:** _which screen / component / string / asset — not product-wide_

**Commit:** _optional — git SHA or PR; may be added retroactively_
```

This matches what `decisions.py add-lightweight` emits (one blank line between
fields), so the documented shape and the helper output agree.

---

## Entries

> _Illustrative only — the entry below is a worked example of the format, not a
> real jig decision (jig is a CLI/plugin with no UI). Adopter projects replace it
> with their first real entry; the scaffold template ships with no entries._

### 2026-01-15 — Onboarding CTA copy: "Get started" over "Sign up"

**Decision:** The first-run onboarding screen's primary button reads
**"Get started"**, not "Sign up" or "Create account".

**Context:** User testing showed "Sign up" read as a commitment gate and
suppressed first-tap; "Get started" tested as lower-friction for a flow that
doesn't actually require an account until step 3. Not worth an ADR — it changes
no contract or boundary — but a future redesign should know the wording is
deliberate, not a placeholder.

**Scope:** Onboarding screen primary CTA only. Does not set a product-wide
button-copy convention.

**Commit:** _(example — no SHA)_

### 2026-08-02 — jig repo disables its own plugin via committed settings

**Decision:** Set enabledPlugins {"jig@jig": false} in the committed .claude/settings.json so the jig source repo runs its in-repo machinery (the .claude/ cloud-session adapter) instead of the installed jig plugin.

**Context:** Two reasons. (1) Cloud enablement: Claude Code on the web has no interactive /plugin install and no plugin runtime, so plugin-mode jig never loads; the committed .claude/ adapter (hooks -> ${CLAUDE_PROJECT_DIR}/hooks/scripts, a SessionStart shim exporting CLAUDE_PLUGIN_ROOT=repo root via $CLAUDE_ENV_FILE, and skill/agent symlinks) makes jig active from the fresh clone. (2) Collision: the adapter and a locally-installed plugin both register the same hooks and Claude Code does not dedupe across sources, so running both fires every hook twice. Committed rather than per-machine settings.local.json because 'develop jig against in-repo machinery, not the stale marketplace snapshot' is a repo-level decision. It is a no-op for contributors without the plugin and in cloud (nothing to match), and remains overridable per-machine via settings.local.json since Local > Project precedence.

**Scope:** .claude/settings.json (enabledPlugins) in the jig source repo only; regular jig projects get their .claude/ from scaffold-init instead

**Commit:** 1e2cdb8
