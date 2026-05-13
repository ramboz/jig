# Plan: Slice 009-01 — close-out-section-recognition

## Approach

Smallest possible change to `check_dod` that resolves the chicken-and-egg.
One regex, one truncation, one new test, one SKILL.md paragraph, one
in-place slice 008-01 edit.

## `check_dod` change in `land.py`

Current (`land.py:112-119`):

```python
def check_dod(section: str) -> tuple:
    """Returns (ok, ticked, total) where ok iff total >= 1 AND ticked == total."""
    boxes = re.findall(r"(?m)^\s*-\s+\[([ xX])\]", section)
    total = len(boxes)
    ticked = sum(1 for b in boxes if b.lower() == "x")
    ok = total >= 1 and ticked == total
    return ok, ticked, total
```

New:

```python
CLOSE_OUT_RE = re.compile(r"(?im)^###\s+close[- ]?out\b")


def check_dod(section: str) -> tuple:
    """Returns (ok, ticked, total) where ok iff total >= 1 AND ticked == total.

    A `### Close-out` subsection inside the slice section terminates the
    DoD count — anything inside it is treated as post-DONE follow-up and
    excluded. Spec 009 introduced this to resolve the DoD-vs-slice-land
    chicken-and-egg around post-DONE items like `status-board` regen and
    CLAUDE.md updates."""
    m = CLOSE_OUT_RE.search(section)
    dod_section = section[:m.start()] if m else section
    boxes = re.findall(r"(?m)^\s*-\s+\[([ xX])\]", dod_section)
    total = len(boxes)
    ticked = sum(1 for b in boxes if b.lower() == "x")
    ok = total >= 1 and ticked == total
    return ok, ticked, total
```

Surface change: just one regex addition + two lines of logic. The rest
of `land.py` is unchanged. No call-site updates.

## Regression test

`PrepareReportTests` already has fixture-builder `_spec_with_slice`.
Extend it (or write a sibling helper) to optionally append a close-out
subsection. Or just hand-craft the section for one test — the existing
builder is general enough that adding a parameter feels like
scope creep.

Lean: hand-craft for one test. Function signature stays clean.

## Slice 008-01 DoD restructure

In-place edit of `docs/specs/008-migrate-existing-project/spec.md`. Two
items move:
- `docs/specs/README.md regenerated AFTER ...` → close-out
- `CLAUDE.md skills table adds migrate ...` → close-out

The remaining 6 items stay in DoD (currently marked 6/8 ticked all from
the §7 reviewer-fix round). After the move, DoD becomes 6/6 ticked.
Close-out is 0/2 (and that's fine — slice-land won't count it).

## SKILL.md update

Add a short subsection (probably under "Gotchas" or a new "DoD
conventions" section) explaining:
- The close-out heading goes inside the slice, before the `---`
  separator.
- Items there are excluded from `check_dod`'s count.
- Items there should describe steps the user runs AFTER the DONE
  transition (status-board regen, CLAUDE.md updates, etc.).
- The heading is case-insensitive, requires `###`, tolerates
  `Close-out` / `Closeout` / `close out` variants.

## Risk: pre-existing slices with `### Close-out` in their content

None today — `grep -r "### Close-out" docs/` returns zero hits as of
session start. So no slice's existing DoD count will change. Low risk.

## Sequencing

1. Edit `land.py` (CLOSE_OUT_RE + check_dod).
2. Add the regression test to `test_land.py`.
3. Run the full slice-land test suite — must stay green.
4. Edit `slice-land/SKILL.md` (new subsection).
5. Edit slice 008-01 spec.md (move two items to close-out).
6. Run `land.py prepare` against slice 008-01 — expect 3/4 readiness
   (Status/Deviation/DoD all OK; Tests still `[?]` warn).
7. Reconciliation: write deviation log under 009-01, run reviewer,
   address findings.
8. Close 009-01 first (it's smaller and the fix needs to be in place
   before 008-01 can close), then close 008-01.
