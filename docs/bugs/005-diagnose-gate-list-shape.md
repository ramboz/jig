---
status: DONE
tier: standard
severity: medium
claimed_by: claude/jig-issue-80-review-dd7b12
regression_test: skills/bug-fix/test_bug.py::DiagnoseGateListShapeTests
main_repro_checked_at: 2026-07-11
main_repro_ref: origin/main@0389a5f
main_repro_result: reproduces
red_confirmed_at: 2026-07-11
green_confirmed_at: 2026-07-11
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 005: diagnose-gate-list-shape

Reported as GitHub issue 80.

## Symptom

`bug.py`'s diagnose gate (`_diagnosis_gaps`, `→ ROOT_CAUSED`) counts candidate
hypotheses by matching stripped lines that begin with `-`. This mis-parses the
`## Hypotheses` section in two directions:

- **False negative** — Markdown *ordered* lists (`1.`, `2.`) and `*`/`+`
  bullets never match, so well-formed hypotheses count as zero. At `standard`
  tier this prints a confusing warning; at `gnarly` it raises `BugError` and
  hard-blocks the transition, whose only documented escape is the total bypass
  `JIG_BUG_DIAGNOSE_GATE=0`.
- **False positive (worse)** — because the match runs on `line.strip()`,
  indentation is discarded, so nested `- Confirm:` / `- Falsify:` sub-bullets
  under a numbered hypothesis are counted as top-level hypotheses. A record
  with zero real dash-bullet hypotheses can pass the `≥2` check by counting
  its sub-bullets — the anti-anchoring gate green-lights for the wrong reason.

Two secondary fragilities compound it: the leading-hypothesis check accepts
only `[x]` or a line beginning `Leading:`, not the `**(leading)**` that
`SKILL.md`'s "mark the leading one" invites; and `_section`'s exact
`^## <heading>\n` regex makes `### Hypotheses` or `## Hypotheses (…)` headings
invisible.

## Repro

Write a `## Hypotheses` section with two well-formed hypotheses as an ordered
list, one marked leading, then transition to `ROOT_CAUSED`:

```markdown
## Hypotheses

1. ~~A real code bug.~~ **REJECTED** by building the artifact.
2. **The runner never runs the build step.** **CONFIRMED** by the test comment.
```

```bash
python3 skills/bug-fix/bug.py transition <id> ROOT_CAUSED
# warning: diagnose gate missing: at least two candidate hypotheses, a leading hypothesis
```

At `tier: gnarly` the same record raises `BugError` and refuses the transition.

## Evidence

- `skills/bug-fix/bug.py:519-522` — `hypothesis_lines = [line.strip() for line
  in hypotheses.splitlines() if line.strip().startswith("-")]`. Direct
  reproduction: a numbered `## Hypotheses` section counts `0`; the same section
  with nested `- Confirm:`/`- Falsify:` sub-bullets counts `3` and passes `≥2`.
- `skills/bug-fix/bug.py:525-528` — leading detection is `"[x]" in line` or
  `re.search(r"(?im)^leading\s*:", …)`; `**(leading)**` matches neither.
- `skills/bug-fix/bug.py:482-487` — `_section` regex `^##\s+<heading>\s*\n`;
  reproduced: `### Hypotheses` and `## Hypotheses (…)` both return empty.
- `skills/bug-fix/SKILL.md:166-169` — teaches "write ≥2 candidate hypotheses …
  mark the leading one"; never states dash-bullet / `[x]` / `Leading:` shape.
- `skills/bug-fix/bug.py:235-236` — the record template scaffolds a bare
  `## Hypotheses` with no worked example, so it teaches no convention.

## Hypotheses

- [ ] The gate's *quality thresholds* (the `≥2` count or the leading detector)
  are wrong. **REJECTED** — the thresholds match the documented policy; a
  correctly dash-bulleted record passes today. The defect is upstream, in how
  list items are extracted from the section text, not in the thresholds.
- [x] **(leading)** The gate's *list-item parser* is simultaneously too narrow
  and too loose: `line.strip().startswith("-")` (a) excludes ordered lists and
  `*`/`+` bullets and (b) strips indentation, so nested sub-bullets are counted
  as top-level items. **CONFIRMED** by direct reproduction (numbered → 0;
  numbered + sub-bullets → 3, passes `≥2` falsely). Confirm: broaden to all
  markdown list markers *and* count only unindented items; both failing cases
  flip. Falsify: if counting only top-level items still miscounts a
  well-formed record, the parser model is wrong.
- [ ] Users simply ignore a documented convention. **REJECTED** — neither
  `SKILL.md` nor the record template ever states the dash-bullet/`[x]` shape,
  so records written in good faith fail. This is a real *contributing*
  discoverability gap (fixed by the message + template items), but it is not
  the parse defect and does not explain the false positive.

## Root cause

`_diagnosis_gaps` encodes brittle text-shape assumptions that the docs never
teach, so the machine-checked shape and the human-taught shape diverge. The
proximate defect is the list-item extractor: it conflates "is a list item"
with "starts with `-` after stripping indentation," which both under-counts
(ordered / `*` / `+` markers) and over-counts (indented sub-bullets). The
leading-marker vocabulary and the exact-match `_section` heading regex are the
same class of over-narrow assumption. Root fix: parse *top-level* list items
across all Markdown list markers, widen the leading-marker vocabulary, name
the expected shape in the error, and make the template teach the convention by
example.

## Fix class

structural_fix — the list-item parser is rewritten to count top-level items
across all Markdown list markers (not a symptom patch on one record). Paired
with discoverability changes (error message names the shape; template carries a
worked example) so the gap does not recur.

## Fix

`skills/bug-fix/bug.py`:

- Replaced the `line.strip().startswith("-")` extractor in `_diagnosis_gaps`
  with `_top_level_list_items`: a marker-agnostic regex
  (`^([-*+]|\d+[.)])\s+\S`) matching every Markdown list marker, gated by an
  `indent >= 2` (tabs expanded to 4) filter so nested `- Confirm:` /
  `- Falsify:` sub-bullets are excluded. This flips both failure directions —
  ordered / `*` / `+` hypotheses now count, indented sub-bullets no longer do.
- Widened leading-marker detection into `_has_leading_marker`: `[x]`, an inline
  `(leading)` tag, or a `Leading:` line all satisfy it, matching SKILL.md's
  "mark the leading one" rather than one exact token.
- The two gap strings now name the expected shape (`top-level '-'/'*'/'+'/'1.'
  list items under '## Hypotheses'`; `mark it '- [x] …', add '(leading)', or a
  line starting 'Leading:'`), so the warning/error is self-correcting. Both
  strings retain the `hypotheses` / `evidence` substrings existing tests assert.
- Scaffolded the record template's `## Hypotheses` with a worked two-hypothesis
  example + a guiding comment, so the convention teaches itself.

`skills/bug-fix/SKILL.md`: the diagnose step now states the accepted list-item
shape and leading-marker vocabulary. Host mirrors regenerated via
`scripts/build_host_packages.py` (drift `--check` clean).

**Deviation / scope (deliberate, reviewer-confirmed):**

- **`_section` heading fragility deferred.** `### Hypotheses`,
  `## Hypotheses (…)` trailing-text headings, and `## Hypotheses` literals
  inside fenced code blocks all make the section invisible (the last one warned
  on this very record). Same root class, but `_section` is shared by the
  Evidence/Proof gates, so widening it is a separate change with its own blast
  radius and tests. Logged to `docs/inbox.md`; not fixed here.
- **Template pre-satisfies the shape gate.** An unedited scaffold now carries
  ≥2 placeholder hypotheses + a `[x]` marker. Accepted: the diagnose gate is a
  presence/shape deliberateness gate, not a quality gate — an unedited record
  is still tripped by the empty `## Evidence`, and hypothesis *quality* is the
  bug-review pass's job.

## Already tried

## Regression test

`skills/bug-fix/test_bug.py::DiagnoseGateListShapeTests` — asserts numbered and
`*`/`+` hypotheses count toward `≥2`, nested sub-bullets do **not** count as
top-level hypotheses, `**(leading)**` satisfies the leading check, and the
error/warning message names the expected shape.

## Proof

Red→green witnessed by the `→ FIXING` / `→ REVIEWED` gates (`bug.py` shells to
`tdd.py` → `scripts/run_tests.py`):

- `red_confirmed_at: 2026-07-11` — the full suite ran red (exit 1) with the new
  `DiagnoseGateListShapeTests` failing 5/6 against the unfixed extractor.
- After the fix: `Ran 3261 tests … OK`, `pyright: clean` (exit 0); the same
  tests pass. `green_confirmed_at` stamped at the `→ REVIEWED` gate.
- Full local CI gate green: `ruff` / code-health floor, `spec_lint --all`,
  `validate_manifests`, `skill_routing --min-rank1 0.85` (95%), host-package
  drift `--check`.

## Learning

A machine-checked gate that parses free-form Markdown must accept every shape
the docs invite, or it punishes good-faith authors and — worse — can pass for
the wrong reason (here, counting nested sub-bullets as hypotheses). When the
only escape from a false negative is a total bypass (`JIG_BUG_DIAGNOSE_GATE=0`),
a cosmetic parse nit pressures users into disabling a real safety gate. Fix the
parser to be liberal in what it accepts *and* precise about top-level structure;
make the gate message name the shape; and make the scaffold teach the
convention by example so the machine-checked shape and the human-taught shape
never diverge.

## Main recheck

- 2026-07-11 - `origin/main@0389a5f` -> reproduces: skills/bug-fix/bug.py identical to origin/main@0389a5f (git diff empty). Repro: _diagnosis_gaps counts a numbered '## Hypotheses' as 0 candidate hypotheses (false negative) and counts nested '- Confirm:'/'- Falsify:' sub-bullets as 3 (false positive, passes >=2). Both reproduced by running the exact origin/main function.
