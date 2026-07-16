---
bug: 011
pass: craft
verdict: needs-changes
reviewer: jig:reviewer
reviewed_at: 2026-07-16T20:41:43Z
prompt_source: skills/independent-review/SKILL.md (craft pass, bug 011)
---

Independent craft pass, 2026-07-16. Verdict recorded as **needs-changes** — the verdict the
reviewer actually returned. Findings addressed after recording; git history is the audit trail
(ADR-0014 §4).

## Assessed as sound

- Naming coheres: `flag_duplicates` / `possible_duplicate` / `_DUPLICATE_*` / the rendered
  "possible duplicate" tag form one vocabulary. Rename churn justified — the old names describe
  behaviour that no longer exists, the constants were private, and the only consumers (hook +
  tests) ship in the same copy. No stragglers outside `hosts/`.
- Python 3.9 compat clean: `dataclasses.replace` is 3.7+, no `match`, no runtime `X | Y` unions.
- Tests assert the contract with genuinely useful failure messages.
- `hosts/` consistent with source.

## Blocking findings (all addressed)

1. Six comments still described the deleted behaviour, **shipped to both hosts** — so scaffolded
   downstream projects would receive header comments contradicting their code. Worst:
   `jig-decision-capture.sh:11-12`, the first thing a reader of the changed hook sees. **Fixed**,
   including `decision_scan.py:28` and `test_jig_decision_capture.py:5`.
2. New docstrings spent most of their length narrating *why the change was made* — bug-record
   prose already living in `docs/bugs/011`. 8 of 11 lines in `flag_duplicates`; same in
   `flag_recorded_stubs`. **Fixed**: trimmed to the load-bearing constraint (overlap can't
   distinguish restatement from reversal, so never drop).
3. `duplicate_note` (~45 words) violated `docs/conventions.md:51-53` — hook `additionalContext`
   must be terse and single-concern, and this fires every Stop (context × turns, spec 055).
   **Fixed**: compressed to one sentence.
4. The containment rule existed in three near-copies, in two styles (`any(...)` vs explicit
   `break` loop), handling the empty-token-set edge differently — and the tell was that the
   docstrings had to *say* "mirrors flag_duplicates's containment rule". **Fixed**: extracted
   `is_contained()` / `token_sets()`; all three sites route through it and the hedge is gone.
5. `decision_scratch.py:155` docstring said "Never drops one" while `continue`-ing malformed
   stubs. **Fixed**: docstring now names the skip and why it is safe (`read_stubs` pre-filters).

## Not adopted

`flag_recorded_stubs` → `flag_duplicate_stubs` for parallelism with `flag_duplicates`. The
current name reads correctly at the call site (it flags stubs against the recorded corpus) and
pairs with `dedup_scan_against_stubs`, which is also named for its corpus. Noted, not churned.
