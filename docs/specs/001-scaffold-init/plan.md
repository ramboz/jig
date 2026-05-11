# Plan: Slice 001-01 — greenfield-scaffold

## Approach

scaffold-init is a hybrid skill: the SKILL.md body instructs Claude on framing, the
deterministic file-generation runs through a Python script invoked via Bash.

- **Decision boundary:** Claude decides *where* to scaffold (target dir, confirmation
  on non-empty) and *reports* what happened. The script does *what* gets written.
- **Why a script:** scaffold output must be deterministic and testable. AC verification
  needs to run as a reproducible test, not as "ask Claude to do it and check."
- **Why a script in `skills/scaffold-init/`:** colocated with the skill that owns it.
  Referenced via `${CLAUDE_SKILL_DIR}/scaffold.py` from the SKILL body.

## Files to create

| Path | Purpose |
|---|---|
| `skills/scaffold-init/scaffold.py` | Wizard implementation |
| `skills/scaffold-init/test_scaffold.py` | AC verification |
| `templates/docs/*.md.template` | Target-project doc stubs (status-marked) |
| `templates/docs/memory/*.md.template` | Memory layer stubs |
| `templates/docs/specs/README.md.template` | Spec status board stub |
| `templates/docs/adrs/README.md.template` | ADR index stub |
| `templates/scaffold.json.template` | Install-state manifest format |
| `hooks/scripts/jig-spec-gate.sh` | PreToolUse gate for conventions.md |

## Files to modify

| Path | Change |
|---|---|
| `skills/scaffold-init/SKILL.md` | Body: wizard instructions + script invocation |
| `hooks/hooks.json` | Add PreToolUse Edit\|Write gate calling jig-spec-gate.sh |
| `docs/specs/001-scaffold-init/spec.md` | Status: DRAFT → IN_PROGRESS |
| `docs/specs/README.md` | Reflect new status |

## Template-substitution model

`{{PROJECT_NAME}}` is the only placeholder for slice 001-01 (basename of target dir).
Future slices add `{{TECH_STACK}}`, `{{TEAM_SIZE}}`, etc. as signal detection grows.

## Spec-gate hook design

`jig-spec-gate.sh` fires on `PreToolUse` / `Edit|Write`. If the target file path matches
`docs/conventions.md` AND the env var `JIG_CONVENTIONS_APPROVED` is not set to `1`,
the hook blocks with exit 2 and message: "docs/conventions.md changes require human
approval. Set JIG_CONVENTIONS_APPROVED=1 for this session if intentional."

This is the simplest viable enforcement. More sophisticated approval flows (lock file,
ADR reference) are deferred.

## Bootstrap paradox handling (AC #8)

The gate hook lives in the plugin (active whenever jig is enabled). It does NOT
gate the *initial creation* of `docs/conventions.md` by scaffold-init — the hook
only fires on `Edit|Write` to an existing path, and during scaffolding, conventions.md
doesn't yet exist. After scaffold-init completes, the file exists and the gate
applies on subsequent edits.

## Test strategy

`test_scaffold.py` uses `subprocess` + `tempfile` to:
1. Run `scaffold.py` against an empty temp dir
2. Verify each AC programmatically (file presence, content patterns, JSON schema)

No external test framework dependency — pure stdlib unittest.

## Out of scope for this slice (deferred)

- Signal detection from filesystem → slice 001-03
- Q&A wizard interaction → slice 001-05
- Rich doc content (architecture details, conventions rules) → slice 001-02
- Tier 1 skill bundling → slice 001-03 (currently scaffold.py writes a default tier list to scaffold.json)
- Multiple template placeholders beyond `{{PROJECT_NAME}}` → slice 001-02
