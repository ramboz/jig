"""
Tests for scripts/copilot_live_hook_smoke.py — slice 113-08 AC1-AC3, AC5.

Two tiers, mirroring `orchestrator_selection_probe.py`'s own test split:

  - Pure, synthetic-log-driven unit tests (`LogParsingTests`,
    `AuthDetectionTests`, `CliWiringTests`) — deterministic, no CLI, no
    network, always run in CI. These are what makes this module's
    detection logic itself TDD-red/green-provable without spending a real
    model call on every test run.
  - `LiveHookRuntimeE2ETests` — the ONE true end-to-end invocation of
    `run_smoke()` against the real, committed `hosts/copilot/` package.
    Gated behind BOTH `shutil.which("copilot")` AND an explicit
    `JIG_COPILOT_LIVE_HOOK_E2E=1` environment opt-in: a real model call
    costs quota/money and must never run silently on a bare
    `python3 -m unittest discover` — see the module's own docstring for
    why this is the documented MANUAL command (AC5), not a default CI
    suite member.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import copilot_live_hook_smoke as live_smoke  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


class LogParsingTests(unittest.TestCase):
    """`iter_hook_stdout_events` / `find_advisory_context` /
    `find_permission_deny` / `any_permission_deny` against SYNTHETIC debug
    log text shaped exactly like the real `--log-level debug` output this
    slice captured live (see the module docstring's capture-session
    description) — deterministic and CI-safe."""

    _ADVISORY_LINE = (
        '2026-09-16T22:15:02.907Z [DEBUG] [rust:hooks] [hook stdout] '
        '{"continue": true, "additionalContext": "jig hint: Greenfield jig '
        'project"}'
    )
    _DENY_LINE = (
        '2026-09-16T22:15:49.130Z [DEBUG] [rust:hooks] [hook stdout] '
        '{"permissionDecision": "deny", "permissionDecisionReason": '
        '"Blocked: docs/conventions.md changes require deliberate approval."}'
    )
    _NOISE_LINE = (
        '2026-09-16T22:15:00.378Z [DEBUG] [rust:copilot_runtime::session::'
        'pending_request_flow] Detached host delivery started '
        '{"event_type":"hook.start"}'
    )

    def test_iter_hook_stdout_events_extracts_both_events(self):
        log = "\n".join([self._NOISE_LINE, self._ADVISORY_LINE, self._DENY_LINE])
        events = live_smoke.iter_hook_stdout_events(log)
        self.assertEqual(len(events), 2)
        self.assertIn("additionalContext", events[0])
        self.assertEqual(events[1]["permissionDecision"], "deny")

    def test_iter_hook_stdout_events_ignores_non_hook_lines(self):
        events = live_smoke.iter_hook_stdout_events(self._NOISE_LINE)
        self.assertEqual(events, [])

    def test_iter_hook_stdout_events_tolerates_malformed_json(self):
        malformed = '[hook stdout] {not valid json'
        events = live_smoke.iter_hook_stdout_events(malformed)
        self.assertEqual(events, [])

    def test_iter_hook_stdout_events_empty_on_empty_log(self):
        self.assertEqual(live_smoke.iter_hook_stdout_events(""), [])
        self.assertEqual(live_smoke.iter_hook_stdout_events(None), [])

    def test_find_advisory_context_returns_the_text(self):
        context = live_smoke.find_advisory_context(self._ADVISORY_LINE)
        self.assertEqual(context, "jig hint: Greenfield jig project")

    def test_find_advisory_context_none_when_absent(self):
        self.assertIsNone(live_smoke.find_advisory_context(self._DENY_LINE))

    def test_find_advisory_context_ignores_empty_string_context(self):
        line = '[hook stdout] {"additionalContext": ""}'
        self.assertIsNone(live_smoke.find_advisory_context(line))

    def test_find_permission_deny_returns_the_reason(self):
        reason = live_smoke.find_permission_deny(self._DENY_LINE)
        self.assertIn("docs/conventions.md", reason)

    def test_find_permission_deny_none_when_no_deny(self):
        self.assertIsNone(live_smoke.find_permission_deny(self._ADVISORY_LINE))

    def test_find_permission_deny_none_on_allow(self):
        line = '[hook stdout] {"permissionDecision": "allow"}'
        self.assertIsNone(live_smoke.find_permission_deny(line))

    def test_any_permission_deny_true_when_present(self):
        self.assertTrue(live_smoke.any_permission_deny(self._DENY_LINE))

    def test_any_permission_deny_false_when_absent(self):
        self.assertFalse(live_smoke.any_permission_deny(self._ADVISORY_LINE))


class AuthDetectionTests(unittest.TestCase):
    """`is_unauthenticated` — the same "an unauthenticated host surfaces an
    auth error and never really runs" idiom
    `orchestrator_selection_probe._AUTH_MARKERS` already established."""

    def test_detects_a_known_auth_marker(self):
        self.assertTrue(
            live_smoke.is_unauthenticated("Error: not authenticated, please log in")
        )

    def test_case_insensitive(self):
        self.assertTrue(live_smoke.is_unauthenticated("ACCESS TOKEN expired"))

    def test_ordinary_output_is_not_flagged(self):
        self.assertFalse(live_smoke.is_unauthenticated("Hello! \U0001f44b"))

    def test_empty_text_is_not_flagged(self):
        self.assertFalse(live_smoke.is_unauthenticated(""))
        self.assertFalse(live_smoke.is_unauthenticated(None))


class CliWiringTests(unittest.TestCase):
    """`main()`'s exit-code contract and its guard against running against
    an unbuilt package — both testable without any live `copilot` call."""

    def test_main_reports_inconclusive_for_an_unbuilt_package(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-smoke-unbuilt-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        code = live_smoke.main(["--package", str(tmp)])
        self.assertEqual(code, live_smoke._EXIT_CODES["INCONCLUSIVE"])

    def test_exit_codes_cover_all_three_verdicts(self):
        self.assertEqual(
            set(live_smoke._EXIT_CODES.keys()), {"PASS", "FAIL", "INCONCLUSIVE"}
        )
        self.assertEqual(live_smoke._EXIT_CODES["PASS"], 0)
        self.assertNotEqual(live_smoke._EXIT_CODES["FAIL"], 0)
        self.assertNotEqual(live_smoke._EXIT_CODES["INCONCLUSIVE"], 0)

    def test_run_smoke_inconclusive_when_copilot_binary_absent(self):
        # Injected absence via a PATH with nothing named "copilot" on it —
        # deterministic, no reliance on the test host's own PATH contents.
        empty_path_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-smoke-nopath-"))
        self.addCleanup(shutil.rmtree, empty_path_dir, ignore_errors=True)
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(empty_path_dir)
        try:
            summary = live_smoke.run_smoke(REPO_ROOT / "hosts" / "copilot")
        finally:
            os.environ["PATH"] = old_path
        self.assertEqual(summary["verdict"], "INCONCLUSIVE")
        self.assertIn("not found", summary["reason"])


@unittest.skipUnless(shutil.which("copilot"), "copilot CLI is not installed")
@unittest.skipUnless(
    os.environ.get("JIG_COPILOT_LIVE_HOOK_E2E") == "1",
    "live hook E2E is opt-in only (real model calls; costs quota/money) — "
    "set JIG_COPILOT_LIVE_HOOK_E2E=1 to run: this IS the documented AC5 "
    "manual smoke command, not a normal suite member",
)
class LiveHookRuntimeE2ETests(unittest.TestCase):
    """The real thing: `run_smoke()` against the committed `hosts/copilot/`
    package, actually firing hooks through Copilot's own hook runtime.
    Skipped by default everywhere except an explicit, deliberate opt-in."""

    def test_committed_package_fires_advisory_and_enforcing_hooks_live(self):
        summary = live_smoke.run_smoke(
            REPO_ROOT / "hosts" / "copilot", timeout=120,
        )
        if summary["verdict"] == "INCONCLUSIVE":
            self.skipTest(summary.get("reason", "inconclusive"))
        self.assertEqual(summary["verdict"], "PASS", summary)
        checks = summary["checks"]
        self.assertTrue(checks["advisory_additional_context"])
        self.assertTrue(checks["enforcing_permission_deny_reason"])
        self.assertFalse(checks["safe_operation_denied"])
        self.assertTrue(checks["safe_operation_file_changed"])


if __name__ == "__main__":
    unittest.main()
