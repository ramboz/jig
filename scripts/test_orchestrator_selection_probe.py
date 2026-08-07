"""Contract test for `orchestrator_selection_probe._probe_host` verdict routing
(spec 096-04). The routing is where the timeout-laundering bug lived, so it is
pinned here via an INJECTED runner — no live host, no CLI install (mirrors the
injected-runner convention of the sibling `codex_*_probe.py` tests).

The verdict rules under test:
  - any fixture timed out            → INCONCLUSIVE (weak negative, not FAIL)
  - any fixture auth-broken          → INCONCLUSIVE (+ codex prompt-inspection)
  - both fixtures match expected     → PASS
  - a positively WRONG emission      → FAIL
  - a None-among-correct (no wrong)  → INCONCLUSIVE (weak negative, not FAIL)
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchestrator_selection_probe as probe  # noqa: E402


def _cp(stdout: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.CompletedProcess(args=["fake"], returncode=0,
                                       stdout=stdout, stderr="")


class VerdictRoutingTest(unittest.TestCase):
    def _run(self, outputs, *, timeout_on=(), inspector=None):
        """`outputs` is a list of stdout strings (or the sentinel "TIMEOUT")
        returned per fixture call, in order (positive, then empty)."""
        calls = {"i": 0}

        def fake_runner(cwd, timeout):
            idx = calls["i"]
            calls["i"] += 1
            if idx in timeout_on:
                raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)
            return _cp(outputs[idx])

        with TemporaryDirectory() as td:
            return probe._probe_host(
                "codex", Path(td), 5, runner=fake_runner,
                prompt_inspector=inspector or (lambda cwd, t: None),
                check_cli=False,
            )

    def test_both_correct_is_pass(self):
        r = self._run(["RICHER_SKILL=review-pr-deep", "RICHER_SKILL=none"])
        self.assertEqual(r["verdict"], "PASS")

    def test_positively_wrong_is_fail(self):
        # positive fixture emits the WRONG skill (a real non-compliance signal).
        r = self._run(["RICHER_SKILL=morning-github", "RICHER_SKILL=none"])
        self.assertEqual(r["verdict"], "FAIL")

    def test_empty_fixture_fabricating_a_pick_is_fail(self):
        # The load-bearing anti-fabrication signal: the empty control's tiers
        # are empty, so the ONLY correct answer is `none`. Emitting a skill name
        # means the agent fabricated a pick rather than honoring the empty list.
        r = self._run(["RICHER_SKILL=review-pr-deep",
                       "RICHER_SKILL=review-pr-deep"])
        self.assertEqual(r["verdict"], "FAIL")

    def test_single_timeout_is_inconclusive_not_fail(self):
        # The regression guard: one fixture passes, the other times out.
        r = self._run(["RICHER_SKILL=review-pr-deep", ""], timeout_on=(1,))
        self.assertEqual(r["verdict"], "INCONCLUSIVE")

    def test_both_timeout_is_inconclusive(self):
        r = self._run(["", ""], timeout_on=(0, 1))
        self.assertEqual(r["verdict"], "INCONCLUSIVE")

    def test_auth_broken_is_inconclusive(self):
        auth = "Error: your access token could not be refreshed."
        r = self._run([auth, auth])
        self.assertEqual(r["verdict"], "INCONCLUSIVE")

    def test_auth_broken_runs_codex_prompt_inspection(self):
        auth = "Error: please log out and sign in again."
        r = self._run([auth, auth], inspector=lambda cwd, t: True)
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertIn("CONFIRMS the recipe", r["reason"])

    def test_none_among_correct_is_inconclusive_not_fail(self):
        # One fixture correct, the other emits nothing (no auth, no timeout) —
        # a weak negative, must NOT be laundered into FAIL.
        r = self._run(["RICHER_SKILL=review-pr-deep", "no emission at all"])
        self.assertEqual(r["verdict"], "INCONCLUSIVE")

    def test_both_none_is_inconclusive(self):
        r = self._run(["nothing here", "nor here"])
        self.assertEqual(r["verdict"], "INCONCLUSIVE")

    def test_trailing_period_not_absorbed(self):
        # `RICHER_SKILL=none.` must parse as `none`, not `none.`
        r = self._run(["RICHER_SKILL=review-pr-deep", "final: RICHER_SKILL=none."])
        self.assertEqual(r["verdict"], "PASS")

    def test_last_emission_wins_over_echoed_template(self):
        # Agent may echo the instruction template `RICHER_SKILL=<name-or-none>`
        # (the `<` breaks the char class, so it can't false-match) then emit the
        # real value last.
        echoed = "I will output RICHER_SKILL=<name-or-none>.\nRICHER_SKILL=none"
        r = self._run(["RICHER_SKILL=review-pr-deep", echoed])
        self.assertEqual(r["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
