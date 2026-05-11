# Plan: Slice 001-02 — doc-content

## Approach

Template-only changes for 4 of 8 ACs; one new behavior in scaffold.py for AC #8 (team detection via git log) plus a new `people.md` template.

Per 001-01 audit, ACs #1, #4, #5, #6 already substantially met by current templates. This slice tightens the remaining four.

## AC audit summary

| AC | Status going in | Work needed |
|---|---|---|
| #1 architecture deferred stubs | ✅ already met | none |
| #2 workflow has spec lifecycle + strictness | 🟡 lifecycle ✅, strictness missing | add Hook Strictness section |
| #3 conventions uses Rule/Why/How throughout | ❌ deferred stubs don't follow format | restructure with 2-3 starter rules in format |
| #4 refinement-todo ≥3 decisions | ✅ 5 present | none |
| #5 memory stubs meaningful content | 🟡 acceptable | (defer — current content already explains usage) |
| #6 inbox header | ✅ already met | none |
| #7 Hot Cache populated with project name + empty lists | 🟡 placeholder text, not name | substitute `{{PROJECT_NAME}}` in codenames section |
| #8 people.md conditional on team | ❌ unimplemented | add `detect_team()` + `people.md.template` |

## Files to create

| Path | Purpose |
|---|---|
| `templates/docs/memory/people.md.template` | Team-roster stub (only rendered when team detected) |

## Files to modify

| Path | Change |
|---|---|
| `templates/docs/workflow.md.template` | Add Hook Strictness Profiles section (deferred marker) |
| `templates/docs/conventions.md.template` | Restructure with starter rules in Rule/Why/How format |
| `templates/CLAUDE.md.template` | Substitute `{{PROJECT_NAME}}` in Project codenames bullet |
| `skills/scaffold-init/scaffold.py` | Add `detect_team()` → conditionally render people.md |
| `skills/scaffold-init/test_scaffold.py` | New tests for ACs #2, #3, #7, #8 (team and solo paths) |
| `docs/specs/001-scaffold-init/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Reflect new status |

## Team detection logic

```python
def detect_team(target: Path) -> bool:
    """Returns True iff `git log` in target shows ≥2 unique author emails.
    Returns False on non-git dirs, missing git binary, or any failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(target), "log", "--format=%ae"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return False
        authors = {line.strip() for line in out.stdout.splitlines() if line.strip()}
        return len(authors) >= 2
    except Exception:
        return False
```

Safe defaults: empty directory, non-git directory, missing git binary, timeout → False (solo).

## Test strategy

Two new test classes:
- `DocContentTests` — content-shape assertions for ACs #2, #3, #7 (no git involvement)
- `TeamDetectionTests` — uses tempfile + `git init` + commits with different author emails to exercise both branches of `detect_team()`

`git` is required for the team-detection tests. They skip gracefully if `git` isn't on PATH.

## Out of scope

- Memory stubs (AC #5) are already "meaningful" enough — current content explains usage, format, and lookup pattern. Promotion to full example-entries is deferred (would bloat templates without commensurate value).
- Q&A wizard's "user confirms team context" path (AC #8 second clause) → slice 001-05.
- Multi-language project detection in conventions starter rules → slice 001-03 (signal detection).
