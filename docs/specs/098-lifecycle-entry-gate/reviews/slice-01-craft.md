---
slice: 098-01 — entry-gate nudge (Claude host)
pass: craft
verdict: pass
reviewer: reviewer subagent (read-only, independent)
reviewed_at: 2026-08-02T07:38:55Z
prompt_source: review.py craft prompt; deliverables: entry_gate.py, jig-entry-gate.sh, hooks.json, verify_install.py, tests
---

Independent craft review (read-only reviewer subagent). **Verdict: pass.**

High-craft, genuinely fail-open hook. Positive-confirmation lifecycle detection
(stale/foreign/unresolvable marker all nudge), the `docs_root="."` anti-dead-gate
trap, and the missing-session_id no-global-silence degradation are correctly
handled and pinned by mutation-resistant tests. Docstrings teach the *why*.

Findings and disposition:
- [blocker-adjacent] Neither git `subprocess.run` (`_claim_identifier`,
  `_git_ignores`) passed `timeout=`; `_claim_identifier` runs on EVERY edit, so a
  hung git would stall the session — a gap the "no failure mode" contract did not
  cover (except catches errors, not hangs). **Fixed:** `timeout=5` added to both
  (TimeoutExpired is swallowed by the surrounding handler → fail-open). New tests
  `test_hung_git_times_out_and_still_evaluates` and
  `test_git_subprocess_calls_pass_a_timeout` pin it.
- [nit] `_DISABLE_VALUES` claimed to mirror `parsing.ENV_FALSEY` but was
  unpinned. **Fixed:** `test_disable_values_match_parsing_env_falsey` added.
- [nit] `evaluate` read the marker twice. **Fixed:** `is_inside_lifecycle` takes
  an optional pre-read marker; `evaluate` reads once and threads it.
- [nit] ambiguous slice/bug globs took first match with no note. **Fixed:**
  docstring states first-match fails toward a nudge via the cross-check.
- [strength] The status-cross-check pair and the two anti-dead-gate tests are
  behavior-pinning, not assertIsNotNone theater. Fail-open posture comprehensive;
  `.sh` wrapper matches the established idiom exactly.
