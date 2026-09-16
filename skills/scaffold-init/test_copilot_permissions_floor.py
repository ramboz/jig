"""
Tests for skills/scaffold-init/copilot_permissions_floor.py — slice 113-05
(enforcing-hooks-and-permissions), owner reshape of AC3: a Copilot-render-
only ENFORCING preToolUse hook restoring jig's `_PERMISSIONS_DENY_DEFAULTS`
security floor as an actual deny gate.

Covers:
  - `PatternsMatchCanonicalFloorTests`: drift-guards the script's DUPLICATED
    `_PERMISSIONS_DENY_DEFAULTS` tuple against `scaffold._PERMISSIONS_DENY_DEFAULTS`
    (the SAME "duplicate, don't import; pin with a test" idiom
    `test_copilot_hook_adapter.py`'s `ReverseToolMapConsistencyTests` and
    `DenyResponseMatchesTranslateHookProtocolTests` already use).
  - `MatchedPatternTests`: direct unit coverage of `matched_pattern` —
    every one of jig's 8 canonical patterns has a representative destructive
    command that matches, and representative safe commands never match.
  - `MainStdinHandlingTests`: `main()`'s JSON/fail-open handling in isolation.
  - `EnforcingEndToEndTests`: POSITIVE CONFIRMATION — a real destructive
    command run through the REAL `copilot_hook_adapter.py --enforce` in
    front of this UNMODIFIED script actually denies (exit 2 + a
    `permissionDecision: deny` body); a real safe command actually allows
    (exit 0, empty stdout). This is the "verify by positive confirmation,
    not absence of error" bar the slice's DoR sets, exercised the same way
    `test_copilot_hook_adapter.EnforcingModeTests` already does for
    jig-spec-gate.sh / jig-secret-scan.sh.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import copilot_permissions_floor  # noqa: E402
import scaffold  # noqa: E402

ADAPTER_PATH = Path(__file__).resolve().parent / "copilot_hook_adapter.py"
FLOOR_SCRIPT_PATH = Path(__file__).resolve().parent / "copilot_permissions_floor.py"


class PatternsMatchCanonicalFloorTests(unittest.TestCase):
    """The script's duplicated pattern tuple must never silently drift from
    the canonical Claude/Codex floor."""

    def test_duplicated_tuple_matches_canonical_exactly(self):
        self.assertEqual(
            copilot_permissions_floor._PERMISSIONS_DENY_DEFAULTS,
            scaffold._PERMISSIONS_DENY_DEFAULTS,
        )

    def test_destructive_command_patterns_covers_every_canonical_entry(self):
        covered = {p for p, _ in copilot_permissions_floor.DESTRUCTIVE_COMMAND_PATTERNS}
        self.assertEqual(covered, set(scaffold._PERMISSIONS_DENY_DEFAULTS))


class PatternToRegexTests(unittest.TestCase):
    """`_pattern_to_regex`'s mechanical glob->regex derivation."""

    def test_star_becomes_any_run(self):
        regex = copilot_permissions_floor._pattern_to_regex("Bash(rm -rf*)")
        self.assertIsNotNone(regex.search("rm -rf /tmp/x"))
        self.assertIsNotNone(regex.search("prefix rm -rf suffix"))

    def test_no_match_without_the_literal_stem(self):
        regex = copilot_permissions_floor._pattern_to_regex("Bash(rm -rf*)")
        self.assertIsNone(regex.search("rm -r /tmp/x"))

    def test_special_regex_characters_in_the_stem_are_escaped(self):
        # Defensive: a hypothetical future pattern with regex-special chars
        # in its literal stem must be treated literally, not as regex syntax.
        regex = copilot_permissions_floor._pattern_to_regex("Bash(a.b(c)*)")
        self.assertIsNotNone(regex.search("a.b(c) trailing"))
        self.assertIsNone(regex.search("aXbYcZ trailing"))  # '.' must be literal


class MatchedPatternTests(unittest.TestCase):
    """Direct unit coverage: every one of jig's 8 canonical patterns has a
    representative real-world destructive command that matches; safe
    commands never match."""

    def test_force_push_long_flag_matches(self):
        self.assertEqual(
            copilot_permissions_floor.matched_pattern("git push --force origin main"),
            "Bash(git push --force*)",
        )

    def test_force_push_short_flag_matches(self):
        self.assertEqual(
            copilot_permissions_floor.matched_pattern("git push -f origin main"),
            "Bash(git push -f *)",
        )

    def test_force_push_after_remote_and_branch_matches(self):
        # The mid-string-wildcard case Copilot's OWN `shell()` permission
        # syntax could not faithfully express (see
        # `CopilotScaffoldRenderer.render_permissions_floor_hook`'s
        # docstring) — this is exactly what this script exists to catch.
        self.assertIsNotNone(
            copilot_permissions_floor.matched_pattern("git push origin main --force")
        )

    def test_force_with_lease_after_remote_and_branch_matches(self):
        self.assertIsNotNone(
            copilot_permissions_floor.matched_pattern(
                "git push origin main --force-with-lease"
            )
        )

    def test_hard_reset_matches(self):
        self.assertEqual(
            copilot_permissions_floor.matched_pattern("git reset --hard HEAD~1"),
            "Bash(git reset --hard*)",
        )

    def test_rm_rf_matches(self):
        self.assertEqual(
            copilot_permissions_floor.matched_pattern("rm -rf /tmp/x"),
            "Bash(rm -rf*)",
        )

    def test_rm_fr_matches(self):
        self.assertEqual(
            copilot_permissions_floor.matched_pattern("rm -fr /tmp/x"),
            "Bash(rm -fr*)",
        )

    def test_rm_r_f_matches(self):
        self.assertEqual(
            copilot_permissions_floor.matched_pattern("rm -r -f /tmp/x"),
            "Bash(rm -r -f*)",
        )

    def test_git_status_is_safe(self):
        self.assertIsNone(copilot_permissions_floor.matched_pattern("git status"))

    def test_ls_is_safe(self):
        self.assertIsNone(copilot_permissions_floor.matched_pattern("ls -la"))

    def test_echo_is_safe(self):
        self.assertIsNone(copilot_permissions_floor.matched_pattern("echo hi"))

    def test_plain_git_push_is_safe(self):
        self.assertIsNone(
            copilot_permissions_floor.matched_pattern("git push origin main")
        )

    def test_plain_rm_is_safe(self):
        self.assertIsNone(copilot_permissions_floor.matched_pattern("rm file.txt"))

    def test_plain_git_reset_is_safe(self):
        self.assertIsNone(
            copilot_permissions_floor.matched_pattern("git reset HEAD~1")
        )

    def test_anywhere_match_is_a_deliberate_divergence_from_claude_anchoring(self):
        # DELIBERATE, more-protective divergence (113-05 reconciliation; arch +
        # compliance review). `matched_pattern` uses an UNANCHORED search, so a
        # destructive token appearing ANYWHERE in a command line matches — even
        # inside a benign command that merely MENTIONS it (an `echo`/`printf` of
        # documentation or a warning string). Claude's native `permissions.deny`
        # is prefix-anchored and would ALLOW these. The floor deliberately blocks
        # MORE than Claude, never less (fail-safe for a security floor). This
        # test pins that intent: a future change that prefix-anchors the regex to
        # "match Claude exactly" would silently NARROW the floor — it must trip a
        # red test + a review, not slip through.
        self.assertIsNotNone(
            copilot_permissions_floor.matched_pattern('echo "never run rm -rf / here"'),
            "unanchored anywhere-match is intentional — see the deviation log",
        )
        self.assertIsNotNone(
            copilot_permissions_floor.matched_pattern(
                'printf "%s\\n" "git push --force is dangerous"'
            ),
            "unanchored anywhere-match is intentional — see the deviation log",
        )


class MainStdinHandlingTests(unittest.TestCase):
    """`main()`'s JSON/fail-open handling, in isolation (no subprocess)."""

    def _run(self, payload_bytes: bytes):
        import contextlib
        import io

        old_stdin = sys.stdin
        try:
            sys.stdin = io.TextIOWrapper(io.BytesIO(payload_bytes))
            # Suppress this script's own stderr writes (block/error
            # messages) — assertions below check the RETURN CODE, not
            # console noise; keeps verbose test output clean.
            with contextlib.redirect_stderr(io.StringIO()):
                return copilot_permissions_floor.main(["copilot_permissions_floor.py"])
        finally:
            sys.stdin = old_stdin

    def test_missing_tool_input_allows(self):
        self.assertEqual(self._run(json.dumps({}).encode()), 0)

    def test_missing_command_key_allows(self):
        self.assertEqual(
            self._run(json.dumps({"tool_input": {}}).encode()), 0
        )

    def test_non_string_command_allows(self):
        self.assertEqual(
            self._run(json.dumps({"tool_input": {"command": 123}}).encode()), 0
        )

    def test_empty_command_allows(self):
        self.assertEqual(
            self._run(json.dumps({"tool_input": {"command": "   "}}).encode()), 0
        )

    def test_malformed_json_fails_open(self):
        self.assertEqual(self._run(b"not valid json{{{"), 0)

    def test_safe_command_allows(self):
        payload = json.dumps({"tool_input": {"command": "git status"}}).encode()
        self.assertEqual(self._run(payload), 0)

    def test_destructive_command_denies(self):
        payload = json.dumps({"tool_input": {"command": "rm -rf /tmp/x"}}).encode()
        self.assertEqual(self._run(payload), 2)


class EnforcingEndToEndTests(unittest.TestCase):
    """POSITIVE CONFIRMATION — the REAL adapter, in --enforce mode, in front
    of this UNMODIFIED script, given a REAL Copilot-shaped (camelCase)
    payload: a destructive command denies; a safe one allows."""

    def _run(self, command: str):
        payload = {
            "sessionId": "abc123",
            "toolName": "bash",
            "toolArgs": {"command": command},
        }
        return subprocess.run(
            [sys.executable, str(ADAPTER_PATH), "--enforce", "PreToolUse",
             str(FLOOR_SCRIPT_PATH)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=15,
        )

    def test_rm_rf_denies_with_exit_2_and_a_deny_body(self):
        result = self._run("rm -rf /tmp/x")
        self.assertEqual(result.returncode, 2)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")
        self.assertIn("destructive-command", deny["permissionDecisionReason"])

    def test_git_push_force_denies_with_exit_2(self):
        result = self._run("git push --force origin main")
        self.assertEqual(result.returncode, 2)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")

    def test_git_push_short_force_flag_denies_with_exit_2(self):
        result = self._run("git push -f origin main")
        self.assertEqual(result.returncode, 2)

    def test_force_after_remote_and_branch_denies_with_exit_2(self):
        # The mid-string-wildcard case Copilot's own permission syntax
        # could not express.
        result = self._run("git push origin main --force")
        self.assertEqual(result.returncode, 2)

    def test_force_with_lease_after_remote_and_branch_denies_with_exit_2(self):
        result = self._run("git push origin main --force-with-lease")
        self.assertEqual(result.returncode, 2)

    def test_hard_reset_denies_with_exit_2(self):
        result = self._run("git reset --hard HEAD~1")
        self.assertEqual(result.returncode, 2)

    def test_rm_fr_denies_with_exit_2(self):
        result = self._run("rm -fr /tmp/x")
        self.assertEqual(result.returncode, 2)

    def test_rm_r_f_denies_with_exit_2(self):
        result = self._run("rm -r -f /tmp/x")
        self.assertEqual(result.returncode, 2)

    def test_git_status_allows_with_exit_0_and_empty_stdout(self):
        result = self._run("git status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_ls_allows_with_exit_0(self):
        result = self._run("ls -la")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_echo_allows_with_exit_0(self):
        result = self._run("echo hi")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_plain_git_push_allows_with_exit_0(self):
        result = self._run("git push origin main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_advisory_mode_stays_fail_open_for_the_same_destructive_command(self):
        # Regression guard: WITHOUT --enforce, the adapter's advisory
        # posture must still mask everything to exit 0 (never denies) —
        # the two modes must not bleed into each other. This floor hook is
        # never actually RENDERED in advisory mode (`render_permissions_floor_hook`
        # always sets enforcing=True), but the adapter itself must still
        # honor the flag's absence correctly if invoked that way.
        payload = {
            "sessionId": "abc123",
            "toolName": "bash",
            "toolArgs": {"command": "rm -rf /tmp/x"},
        }
        result = subprocess.run(
            [sys.executable, str(ADAPTER_PATH), "PreToolUse", str(FLOOR_SCRIPT_PATH)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class InterpreterSelectionTests(unittest.TestCase):
    """The adapter picks `python3` for this `.py` target, not `bash` (which
    would try to interpret Python source as shell commands and fail)."""

    def test_adapter_uses_python3_for_the_py_floor_script(self):
        import copilot_hook_adapter

        self.assertEqual(
            copilot_hook_adapter._interpreter_for(str(FLOOR_SCRIPT_PATH)),
            "python3",
        )

    def test_adapter_still_uses_bash_for_sh_scripts(self):
        import copilot_hook_adapter

        self.assertEqual(
            copilot_hook_adapter._interpreter_for("some/path/jig-spec-gate.sh"),
            "bash",
        )


if __name__ == "__main__":
    unittest.main()
