# ADR-0003: Extract `find_slice_section` to `skills/_common/parsing.py`

## Status

Accepted (2026-05-12)

## Context

[ADR-0002](adr-0002-contracts-stays-deferred.md) named "first time jig has three callers
that need the same helper" as the trigger to extract `skills/_common/<module>.py`.

That trigger has fired. Three helpers ([workflow.py](../../skills/spec-workflow/workflow.py),
[review.py](../../skills/independent-review/review.py),
[land.py](../../skills/slice-land/land.py)) each contain a near-identical
function — same regex (`(?im)^##\s+Slice\s+([^\n]+)$`), same case-insensitive
substring matching against a user-supplied fragment, same not-found / ambiguous
error semantics. The only differences are the return shape (2-tuple vs. label
string vs. 3-tuple) and the error class (`WorkflowError` / `ReviewError` /
`LandError`).

Each prior slice's deviation log chose to duplicate rather than abstract:

- **Slice 004-01** (review-helper): "small function, stable regex; option C (shared utility) is overkill for two callers."
- **Slice 005-01** (adr-helper): three callers now, but the three call-sites
  use different regexes (`## Slice` ×2 vs. `### Decision:` ×1), so the shared
  abstraction wouldn't be a clean fit.
- **Slice 006-01** (tdd-helper): different pattern (signal detection), separate
  trigger discussion.
- **Slice 007-01** (land-prepare): four callers now, three of which use the
  *same* `## Slice` regex shape (`workflow.py`, `review.py`, `land.py`); the
  fourth (`adr.py`) uses `### Decision:` and is intentionally divergent.

Slice 007-01's deviation log shifted the bar to "fifth same-shape caller,"
but that goalpost shift was inconsistent with ADR-0002's original explicit
rule ("three callers needing the same helper"). The original bar already
applies — `find_slice_section` has had three same-shape callers since
slice 007-01 landed.

## Decision Options Considered

### Option A: Extract `find_slice_section` to `skills/_common/parsing.py` now

- **Pros:**
  - Honors ADR-0002's explicit trigger.
  - Removes ~40 lines of duplicated code across three helpers.
  - Establishes the `skills/_common/` directory for future shared utilities,
    setting precedent for the next extraction.
- **Cons:**
  - Introduces a cross-skill import. Each caller now sys.path-inserts
    `skills/` and does `from _common.parsing import ...` — slightly noisier
    at the import block.
  - The three callers want different return shapes; the canonical helper
    returns the union `(start, end, label)` and each caller wraps to
    preserve its historical surface.

### Option B: Continue duplicating (deferred bar from slice 007-01)

- **Pros:** Each helper stays self-contained; no cross-skill coupling at all.
- **Cons:**
  - Direct contradiction of ADR-0002's "three callers" trigger.
  - Future drift risk: each helper's regex can evolve independently and
    silently disagree.
  - Goalpost-shifting erodes trust in the trigger system.

### Option C: Extract more broadly — `find_slice_section` *and* expand `contracts` skill

- **Pros:** ADR-0002 said the trigger also marked the moment to "introduce
  a real contract" via the `contracts` skill.
- **Cons:**
  - `contracts` is still a deliberate stub per ADR-0002. Expanding it
    requires a separate spec.
  - The find_slice_section extraction stands on its own value;
    bundling with `contracts` work would delay both.

## Recommended Decision

**Option A.** Extract `find_slice_section` to `skills/_common/parsing.py` now;
keep the `contracts` skill as a stub (ADR-0002 still holds). Each caller
becomes a thin wrapper that re-raises `SliceLookupError` as its own
user-facing error class.

The extraction is small (one function, ~25 lines), the precedent for
`skills/_common/` is set, and ADR-0002's explicit trigger is honored.

## Consequences

**Becomes easier:**

- Future callers needing the same lookup import from `_common.parsing`
  instead of copy-pasting.
- A bug in the regex or substring-match logic is fixed in one place.
- `skills/_common/` is now a real directory other shared utilities can join.

**Becomes harder:**

- Each helper's import block now has three lines of cross-skill plumbing
  (`sys.path.insert` + two `from _common.parsing import`). Mitigated by
  consistent placement at the top of each helper.
- Test discovery from `skills/` top-level was never working (each skill
  has historically been tested via per-directory `python3 -m unittest discover skills/<name>/`),
  so the implicit-namespace-package pattern doesn't regress anything. The
  per-skill test-invocation convention is unchanged.

**Implementation status:**

- `skills/_common/parsing.py` introduced with `find_slice_section(text, fragment) -> (start, end, label)` and `SliceLookupError`.
- `skills/_common/test_parsing.py` covers 10 tests (single-fragment / case-insensitive / substring / EOF / ambiguous / missing / cross-caller realism against jig's own spec 005).
- `workflow.py`, `review.py`, `land.py` each delegate to the shared helper,
  wrapping `SliceLookupError → <Skill>Error`. Each retains its historical
  return shape so callers within the skill don't need to change.
- 257 tests across 8 directories all pass (was 247 → +10 new `_common`
  tests, zero regressions in the three refactored callers' 72 combined tests).

**Resolution trigger for revisiting:**

- The `adr.py` `### Decision:` lookup remains standalone. If a second
  caller with that shape emerges, it joins `find_decision_section` (a sibling
  function in `_common.parsing`) at *its own* three-caller threshold.
- If a fifth, sixth, or seventh distinct parsing pattern emerges, consider
  whether `_common.parsing` deserves to split into per-shape modules.

## Open questions

None. Future shape-specific extractions follow the same ADR-0002 rule.
