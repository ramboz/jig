---
status: IN_PROGRESS
dependencies: []
last_verified: 2026-07-31
claimed_by: claude/github-issue-147-c6ab0d
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon). -->
<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 107-01 — protection refusals reach the pull-request fallback

**Goal:** A contributor without branch-protection bypass who runs a reservation
gets routed to the pull-request fallback instead of being told to re-run a push
that can never succeed. The classifier stops reading GitHub's protected-branch
and repository-ruleset refusals as races.

**Decision:** [ADR-0053](../../decisions/adr-0053-reservation-numbering-sees-in-flight-branches.md)
(Option A, folded into the chosen Option C).

**DoR:**
- ✅ Three helpers carry a mirrored `_classify_push_failure` with inline-mirror
  comments citing ADR-0002's three-caller rule and explicitly deferring
  extraction at "two callers": `skills/adr-workflow/adr.py:188-212`,
  `skills/spec-workflow/workflow.py:2928-2950`, `skills/bug-fix/bug.py:77-88`.
  With `bug.py` there are now three callers — the rule's extraction trigger.
- ✅ The copies have already drifted: `bug.py`'s protection list contains
  `gh006`; `adr.py` and `workflow.py` do not, relying on `pre-receive hook
  declined` to catch real GH006 output. Verified by reading all three.
- ✅ Real refusal stderr captured 2026-07-31 (local bare repo + pre-receive
  hook): a non-fast-forward race prints ` ! [rejected]  HEAD -> main (fetch
  first)`; a GH006 decline prints the `remote: error: GH006:` lines plus
  ` ! [remote rejected] HEAD -> main (pre-receive hook declined)`. The
  ` ! [remote rejected]` line — omitted by the current test fixtures — always
  carries the substring `rejected`, which is what the race branch matches first.
- ✅ Host mirrors under `hosts/claude/` and `hosts/codex/` are regenerated from
  `skills/` by `scripts/build_host_packages.py`, not hand-edited.

**Assumptions:** A3 from [spec 107](./spec.md#assumptions) — the replacement
fixtures are captured, not recalled.

**Acceptance Criteria:**

1. **Protection is classified as protection, from real stderr.** Given the
   captured GH006 refusal (including the ` ! [remote rejected] … (pre-receive
   hook declined)` line), the classifier returns `"protection"`. Given the
   captured GH013 repository-ruleset refusal, it also returns `"protection"`.
   Both hold for all three helpers.

2. **Genuine races still classify as races.** Given the captured non-fast-forward
   refusal (` ! [rejected] HEAD -> main (fetch first)`), the classifier returns
   `"race"`. The specific race markers (`non-fast-forward`, `fetch first`,
   `stale info`) are what carry a race; the bare `rejected` / `[rejected]`
   markers are removed, because with protection checked first they otherwise
   swallow every failed push — including genuine `other` failures — into the
   race path (issue #147 direction 3).

3. **Unknown failures classify as `other`, not race.** A push failure that
   contains neither a protection marker nor a specific race marker (e.g. a
   transient network error whose text happens to include `rejected`) returns
   `"other"`, so the caller surfaces it instead of advising a pointless re-run.

4. **Ordering is specific-over-generic.** Protection markers are checked before
   race markers. The `adr.py` docstring claim that "race wins over protection if
   both appear" is removed: a protection refusal never advances `origin/main`,
   so there is no stranded-commit race to recover from, and protection markers
   only ever appear on protection refusals.

5. **One classifier, three callers.** `classify_push_failure` and its signal
   tuples live once in `skills/_common/reservation.py`. `bug.py`, `adr.py` and
   `workflow.py` import it; each keeps a module-level `_classify_push_failure`
   name (a re-export) so existing call sites and tests are unchanged. The
   drift that let `bug.py` diverge from the other two cannot recur.

6. **The end-to-end fallback fires.** With `pr_mode=False` and a mocked push
   that returns the captured GH006 stderr, `reserve_bug_on_origin` /
   `reserve_adr` / `reserve_spec` route to the PR fallback (branch push + `gh pr
   create`) rather than raising a race error. This is the behaviour a
   contributor sees; today it raises.

7. **Host packages regenerated.** After the change, `scripts/build_host_packages.py`
   reproduces `hosts/claude/` and `hosts/codex/` with no diff, and the committed
   mirrors carry the extracted `_common/reservation.py`.

**Definition of Done:**
- [x] `skills/_common/reservation.py` holds `classify_push_failure` +
      `_PUSH_PROTECTION_SIGNALS` + `_PUSH_RACE_SIGNALS`; the three helpers import it.
- [x] `skills/_common/test_reservation.py` pins AC1–AC4 against captured stderr,
      including the GH013 ruleset case.
- [x] Existing protection-path fixtures in `test_bug.py`, `test_adr.py`,
      `test_workflow.py` replaced with the captured multi-line stderr; the
      previously-green-against-the-bug assertions now exercise the real string.
- [x] Host mirrors regenerated; `run_tests.py` green.

**Non-goals:** the numbering scan (slice 107-02); fork branches; the atomic claim
ref (ADR-0053 Option D).

## Deviations

- **Extraction, not in-place edit (AC5).** The slice fixes the classifier by
  extracting it to `_common/reservation.py` and re-exporting, rather than
  editing three mirrored copies. This is the ADR-0002 three-caller trigger
  firing exactly (the inline-mirror comments deferred it at two callers), and
  it removes the drift that caused the defect (`bug.py` alone carried `gh006`).
  Wider blast radius than a three-line edit, narrower failure surface forever.
- **GH013 end-to-end coverage lives in `test_bug.py`, not all three.** The
  shared `test_reservation.py` proves GH013 → protection at the classifier;
  one end-to-end fallback test (`test_ruleset_gh013_push_falls_back_to_pr`)
  proves the full reserve path routes it. The three helpers share the extracted
  classifier, so one end-to-end GH013 proof suffices; adr/workflow keep their
  GH006 end-to-end tests.
