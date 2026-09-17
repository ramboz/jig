"""
Tests for skills/scaffold-init/copilot_hook_adapter.py — slice 113-04
(advisory-hooks), the INPUT half of the hook-protocol translation layer.

Covers:
  - `translate_payload`: the field-name and tool-name-value mapping from
    Copilot's camelCase stdin JSON to the snake_case shape jig's shared hook
    scripts read, and its fail-open behavior on malformed input.
  - `project_dir_from_payload`: the `workingDirectory` extraction used to
    export `CLAUDE_PROJECT_DIR` for the child process.
  - `ReverseToolMapConsistencyTests`: pins the adapter's
    `_COPILOT_TO_CLAUDE_TOOL_NAME` reverse table in sync with
    `CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS` (113-03) so the two
    cannot silently drift apart.
  - `AllThreeHooksFireUnderCopilotInputTests`: end-to-end — invoke the
    adapter as a real subprocess in front of each of the 3 UNMODIFIED
    `hooks/scripts/jig-*.sh` scripts, feeding a constructed Copilot-shaped
    (camelCase) payload on stdin, and confirm the `additionalContext` nudge
    is produced. This is the "make boundary-warn + entry-gate fire too"
    verification — a deterministic substitute for a live Copilot session
    (no credit-consuming `copilot -p` call).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import copilot_hook_adapter  # noqa: E402
import scaffold  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ADAPTER_PATH = Path(__file__).resolve().parent / "copilot_hook_adapter.py"
HOOK_SCRIPTS_DIR = REPO_ROOT / "hooks" / "scripts"


def _make_repo_behind_origin_main(project_dir: Path) -> None:
    """Turn `project_dir` into a hermetic, no-network git repo whose `HEAD`
    is exactly 1 commit behind a LOCAL `refs/remotes/origin/main` ref — the
    fixture `lib/git_freshness.py`'s `resolve_target`/`_behind_count` need
    to produce a real, non-trivial nudge (craft review fix: prove genuine
    firing, not just "does not crash").

    Mechanics: commit twice on `main`, pin `refs/remotes/origin/main` to
    the SECOND commit, then hard-reset the branch back to the first — so
    `origin/main` (a real, resolvable ref) is 1 commit ahead of `HEAD` with
    no actual remote or network fetch involved (`git fetch origin main`
    inside `evaluate()` fails harmlessly against a non-existent remote and
    is swallowed by `_run_git`'s own fail-open contract, leaving the
    manually-pinned ref in place)."""
    def _git(*args):
        subprocess.run(
            ["git", *args], cwd=str(project_dir), check=True,
            capture_output=True, text=True,
        )

    _git("init", "-q", "-b", "main")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    _git("commit", "-q", "--allow-empty", "-m", "C1")
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(project_dir),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    _git("commit", "-q", "--allow-empty", "-m", "C2")
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(project_dir),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    _git("update-ref", "refs/remotes/origin/main", second)
    _git("reset", "-q", "--hard", first)


class TranslatePayloadTests(unittest.TestCase):
    def test_session_id_mapped(self):
        raw = json.dumps({"sessionId": "abc123"}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "SessionStart"))
        self.assertEqual(out["session_id"], "abc123")

    def test_hook_event_name_always_set_from_argument(self):
        raw = json.dumps({}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "PostToolUse"))
        self.assertEqual(out["hook_event_name"], "PostToolUse")

    def test_tool_name_edit_maps_to_pascal_case_edit(self):
        raw = json.dumps({"toolName": "edit"}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "PostToolUse"))
        self.assertEqual(out["tool_name"], "Edit")

    def test_tool_name_create_maps_to_pascal_case_write(self):
        raw = json.dumps({"toolName": "create"}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "PostToolUse"))
        self.assertEqual(out["tool_name"], "Write")

    def test_unrecognized_tool_name_passes_through_unchanged(self):
        raw = json.dumps({"toolName": "bash"}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "PostToolUse"))
        self.assertEqual(out["tool_name"], "bash")

    def test_tool_args_copied_and_path_becomes_file_path(self):
        raw = json.dumps({"toolArgs": {"path": "openapi.yaml", "file_text": "x"}}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "PostToolUse"))
        self.assertEqual(out["tool_input"]["file_path"], "openapi.yaml")
        self.assertEqual(out["tool_input"]["path"], "openapi.yaml")  # preserved
        self.assertEqual(out["tool_input"]["file_text"], "x")  # preserved

    def test_tool_args_without_path_has_no_file_path_added(self):
        raw = json.dumps({"toolArgs": {"view_range": [1, 2]}}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "PostToolUse"))
        self.assertNotIn("file_path", out["tool_input"])

    def test_source_passed_through_unchanged(self):
        raw = json.dumps({"source": "startup"}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "SessionStart"))
        self.assertEqual(out["source"], "startup")

    def test_prompt_maps_from_user_prompt_submitted(self):
        # SDK UserPromptSubmittedHookInput supplies `prompt`; jig-memory-scan and
        # jig-decision-inflight read `data['prompt']`. Without this mapping they
        # degraded to a silent no-op under Copilot (113-06 craft review).
        raw = json.dumps({"prompt": "explain spec 042"}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "UserPromptSubmit"))
        self.assertEqual(out["prompt"], "explain spec 042")

    def test_transcript_path_is_forwarded_for_agent_stop(self):
        raw = json.dumps({"transcriptPath": "/tmp/sess/transcript.jsonl"}).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "Stop"))
        self.assertEqual(out["transcript_path"], "/tmp/sess/transcript.jsonl")

    def test_a_full_post_tool_use_payload_translates_completely(self):
        raw = json.dumps({
            "sessionId": "s1",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": "/tmp/proj",
            "toolName": "edit",
            "toolArgs": {"path": "openapi.yaml"},
        }).encode()
        out = json.loads(copilot_hook_adapter.translate_payload(raw, "PostToolUse"))
        self.assertEqual(out, {
            "hook_event_name": "PostToolUse",
            "session_id": "s1",
            "tool_name": "Edit",
            "tool_input": {"path": "openapi.yaml", "file_path": "openapi.yaml"},
        })

    def test_malformed_json_returns_raw_unchanged(self):
        raw = b"not valid json{{{"
        self.assertEqual(
            copilot_hook_adapter.translate_payload(raw, "PostToolUse"), raw
        )

    def test_non_dict_json_returns_raw_unchanged(self):
        raw = b"[1, 2, 3]"
        self.assertEqual(
            copilot_hook_adapter.translate_payload(raw, "PostToolUse"), raw
        )

    def test_empty_bytes_still_produce_valid_json_with_event_name(self):
        out = json.loads(copilot_hook_adapter.translate_payload(b"", "SessionStart"))
        self.assertEqual(out, {"hook_event_name": "SessionStart"})


class ProjectDirFromPayloadTests(unittest.TestCase):
    def test_returns_working_directory_when_present(self):
        raw = json.dumps({"workingDirectory": "/tmp/proj"}).encode()
        self.assertEqual(
            copilot_hook_adapter.project_dir_from_payload(raw), "/tmp/proj"
        )

    def test_returns_none_when_absent(self):
        raw = json.dumps({}).encode()
        self.assertIsNone(copilot_hook_adapter.project_dir_from_payload(raw))

    def test_returns_none_on_malformed_json(self):
        self.assertIsNone(
            copilot_hook_adapter.project_dir_from_payload(b"not json")
        )

    def test_returns_none_when_not_a_string(self):
        raw = json.dumps({"workingDirectory": 123}).encode()
        self.assertIsNone(copilot_hook_adapter.project_dir_from_payload(raw))


class ReverseToolMapConsistencyTests(unittest.TestCase):
    """The adapter's reverse table must not silently drift from 113-03's
    forward `CLAUDE_TO_COPILOT_TOOLS` — this is the cross-check the
    adapter's own docstring promises."""

    def test_every_reverse_entry_inverts_a_forward_entry(self):
        forward = scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS
        for copilot_name, claude_name in (
            copilot_hook_adapter._COPILOT_TO_CLAUDE_TOOL_NAME.items()
        ):
            self.assertEqual(
                forward.get(claude_name), copilot_name,
                f"reverse entry {copilot_name!r}->{claude_name!r} does not "
                f"invert CLAUDE_TO_COPILOT_TOOLS[{claude_name!r}]"
                f"={forward.get(claude_name)!r}",
            )


class MainInvocationTests(unittest.TestCase):
    """Coverage of `main()`'s argv handling and fail-open exit codes.
    `test_too_few_args_returns_zero` is a pure in-process call (no target
    script to spawn); the others are real subprocess invocations (an
    in-process `sys.stdin` mock does not work — `TextIOWrapper.buffer` is
    read-only) — see `AllThreeHooksFireUnderCopilotInputTests` for the
    fuller end-to-end subprocess coverage against the real jig scripts."""

    def test_too_few_args_returns_zero(self):
        self.assertEqual(copilot_hook_adapter.main(["adapter.py"]), 0)
        self.assertEqual(copilot_hook_adapter.main(["adapter.py", "PostToolUse"]), 0)

    def test_nonexistent_script_path_fails_open_to_zero(self):
        # Real subprocess invocation (not an in-process `sys.stdin` mock —
        # `TextIOWrapper.buffer` is read-only): `bash` itself reports a
        # non-zero exit for an unreadable script; the adapter must mask
        # that to 0 rather than surface it as a blocking hook failure.
        result = subprocess.run(
            [sys.executable, str(ADAPTER_PATH), "PostToolUse", "/no/such/script.sh"],
            input=b"{}",
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class AgentStopTranscriptAdapterTests(unittest.TestCase):
    def test_agent_stop_transcript_reaches_shared_task_hook(self):
        with tempfile.TemporaryDirectory(prefix="jig-copilot-stop-") as tmp:
            project = Path(tmp)
            transcript = project / "session.jsonl"
            transcript.write_text(json.dumps({
                "type": "assistant",
                "message": {"role": "assistant",
                            "content": "TODO: capture this follow-up"},
            }) + "\n")
            env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
            result = subprocess.run(
                [sys.executable, str(ADAPTER_PATH), "Stop",
                 str(HOOK_SCRIPTS_DIR / "jig-task-capture.sh")],
                input=json.dumps({
                    "sessionId": "s", "workingDirectory": str(project),
                    "transcriptPath": str(transcript),
                }),
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Task-capture patterns detected", result.stdout)


class MainClaudeProjectDirDerivationTests(unittest.TestCase):
    """Craft review fix — focused coverage of `main()`'s CLAUDE_PROJECT_DIR
    derivation-and-guard branch, independent of any target script's own
    business logic: spawn the adapter in front of a tiny echo script that
    just reports its OWN `CLAUDE_PROJECT_DIR`, so the assertion is about
    the adapter's env-passing directly rather than inferred from
    `entry_gate.py`'s lifecycle logic."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-adapter-cwd-"))
        self.echo_script = self.tmp / "echo_project_dir.sh"
        self.echo_script.write_text(
            "#!/bin/bash\n"
            "cat >/dev/null\n"  # drain stdin; the adapter always writes some
            'echo "CLAUDE_PROJECT_DIR=$CLAUDE_PROJECT_DIR"\n'
        )
        self.echo_script.chmod(0o755)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, payload: dict, env: dict):
        return subprocess.run(
            [sys.executable, str(ADAPTER_PATH), "SessionStart", str(self.echo_script)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=15,
            env=env,
        )

    def test_derives_claude_project_dir_from_working_directory_when_absent(self):
        env = {**os.environ}
        env.pop("CLAUDE_PROJECT_DIR", None)
        result = self._run({"workingDirectory": "/some/temp/project"}, env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "CLAUDE_PROJECT_DIR=/some/temp/project", result.stdout.decode()
        )

    def test_does_not_override_claude_project_dir_when_already_set(self):
        # The guard: an EXPLICITLY-configured CLAUDE_PROJECT_DIR (e.g. set
        # by a real Claude Code session) must survive even when the
        # payload names a DIFFERENT `workingDirectory` — the adapter never
        # clobbers an existing value.
        env = {**os.environ, "CLAUDE_PROJECT_DIR": "/already/set/dir"}
        result = self._run({"workingDirectory": "/some/other/project"}, env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLAUDE_PROJECT_DIR=/already/set/dir", result.stdout.decode())
        self.assertNotIn("/some/other/project", result.stdout.decode())

    def test_leaves_claude_project_dir_unset_when_payload_has_no_working_directory(self):
        env = {**os.environ}
        env.pop("CLAUDE_PROJECT_DIR", None)
        result = self._run({}, env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLAUDE_PROJECT_DIR=", result.stdout.decode())  # empty, not absent
        self.assertNotIn("/some/", result.stdout.decode())


class AllThreeHooksFireUnderCopilotInputTests(unittest.TestCase):
    """End-to-end (deterministic substitute for a live Copilot session, per
    the slice's AC2/AC3): pipe a REAL Copilot-shaped (camelCase) payload
    through the adapter into each of the 3 UNMODIFIED
    `hooks/scripts/jig-*.sh` scripts, and confirm the `additionalContext`
    nudge is produced — not merely "does not crash" (that was already
    covered before this fix; this proves genuine firing)."""

    def setUp(self):
        self.project_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-adapter-e2e-"))

    def tearDown(self):
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _run_through_adapter(self, claude_event: str, script_name: str, payload: dict):
        script_path = HOOK_SCRIPTS_DIR / script_name
        # Isolate TMPDIR to this test's own temp dir: `jig-entry-gate.sh`'s
        # cadence state (fire-at-most-once-per-session) lives under
        # `$TMPDIR`, keyed by `session_id` — every test in this class uses
        # the same literal `sessionId`, so without isolation the SECOND
        # test to run would find "already fired" state left by an earlier
        # one (or an earlier suite run) and be wrongly suppressed.
        #
        # ALSO force CLAUDE_PROJECT_DIR to this test's own temp dir (craft
        # review fix — hermeticity): the adapter only exports
        # CLAUDE_PROJECT_DIR from the payload's `workingDirectory` when it
        # is NOT already present in the inherited environment (a deliberate
        # "don't clobber an explicit value" guard — see
        # `MainInvocationTests.test_claude_project_dir_not_overridden_when_
        # already_set`). Under a real Claude Code session CLAUDE_PROJECT_DIR
        # is set to the actual repo being worked in; without this override,
        # entry_gate.py would evaluate lifecycle state against the REAL
        # repo (which has its own `.jig/spec-ref` marker) instead of this
        # test's isolated temp dir — an environment-dependent result, not a
        # hermetic one. Matches the sibling raw-script tests in
        # `scripts/test_build_copilot_plugin.py`, which already set this
        # explicitly.
        env = {
            **os.environ,
            "TMPDIR": str(self.project_dir),
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
        }
        result = subprocess.run(
            [sys.executable, str(ADAPTER_PATH), claude_event, str(script_path)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=15,
            env=env,
        )
        return result

    def test_boundary_warn_fires_under_copilot_shaped_edit_payload(self):
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "openapi.yaml"},
        }
        result = self._run_through_adapter(
            "PostToolUse", "jig-boundary-change-warn.sh", payload
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("additionalContext", result.stdout.decode())
        self.assertIn("openapi.yaml", result.stdout.decode())

    def test_boundary_warn_fires_under_copilot_shaped_create_payload(self):
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "create",
            "toolArgs": {"path": "spec.proto", "file_text": "syntax = \"proto3\";"},
        }
        result = self._run_through_adapter(
            "PostToolUse", "jig-boundary-change-warn.sh", payload
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("additionalContext", result.stdout.decode())

    def test_entry_gate_fires_under_copilot_shaped_edit_payload(self):
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "app.py"},
        }
        result = self._run_through_adapter(
            "PostToolUse", "jig-entry-gate.sh", payload
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("additionalContext", result.stdout.decode())
        self.assertIn("outside the jig lifecycle", result.stdout.decode())

    def test_git_freshness_still_fires_cleanly_through_the_adapter(self):
        # A non-repo temp dir: git-freshness must degrade silently (no repo
        # to resolve a base against), never crash.
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "source": "startup",
        }
        result = self._run_through_adapter(
            "SessionStart", "jig-git-freshness.sh", payload
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_git_freshness_fires_a_real_behind_nudge_through_the_adapter(self):
        # Craft review fix: prove genuine firing (an `additionalContext`
        # nudge naming the real behind-count), not merely "does not
        # crash" — a hermetic, no-network "HEAD is behind origin/main"
        # fixture (see `_make_repo_behind_origin_main`).
        _make_repo_behind_origin_main(self.project_dir)
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "source": "startup",
        }
        result = self._run_through_adapter(
            "SessionStart", "jig-git-freshness.sh", payload
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        stdout = result.stdout.decode()
        self.assertIn("additionalContext", stdout)
        self.assertIn("1 commit(s) behind", stdout)
        self.assertIn("origin/main", stdout)

    def test_boundary_warn_does_not_fire_on_a_non_contract_file(self):
        # Negative control: the adapter must not manufacture a nudge where
        # the underlying script's own logic would not produce one.
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "README.md"},
        }
        result = self._run_through_adapter(
            "PostToolUse", "jig-boundary-change-warn.sh", payload
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_unrecognized_tool_name_value_fails_open_silently(self):
        # AC3: a tool name this adapter/slice does not recognize must
        # degrade to no nudge, never a crash.
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "bash",
            "toolArgs": {"command": "ls"},
        }
        result = self._run_through_adapter(
            "PostToolUse", "jig-boundary-change-warn.sh", payload
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")


class PromptConsumingHookFiresUnderCopilotInputTests(unittest.TestCase):
    """End-to-end (113-06 craft-review fix): a hook that reads a field BEYOND
    `tool_input`/`source` must actually receive it through the adapter.
    Copilot's `userPromptSubmitted` supplies `prompt` (SDK
    UserPromptSubmittedHookInput); before the adapter forwarded it,
    jig-memory-scan / jig-decision-inflight were registered-but-inert. Proven
    by a REAL lexicon surfacing driven by the forwarded prompt, not
    "does not crash"."""

    LEXICON_COMMON = HOOK_SCRIPTS_DIR.parent.parent / "skills" / "_common"

    def setUp(self):
        self.project_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-prompt-e2e-"))

    def tearDown(self):
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _run(self, claude_event, script_name, payload):
        env = {
            **os.environ,
            "TMPDIR": str(self.project_dir),
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
            # Resolve the lexicon deterministically against the real shipped
            # skills/_common (memory-scan's default resolution walks SCRIPT_DIR,
            # which varies by invocation shape) so the assertion is stable.
            "JIG_LEXICON_COMMON_DIR": str(self.LEXICON_COMMON),
        }
        return subprocess.run(
            [sys.executable, str(ADAPTER_PATH), claude_event,
             str(HOOK_SCRIPTS_DIR / script_name)],
            input=json.dumps(payload).encode(),
            capture_output=True, timeout=15, env=env,
        )

    def test_memory_scan_surfaces_lexicon_terms_from_a_copilot_prompt(self):
        # Without the adapter forwarding `prompt`, memory-scan sees prompt='' and
        # surfaces NOTHING — so this fails if the prompt-forwarding is removed
        # (the exact registered-but-inert defect the craft review found).
        payload = {
            "sessionId": "abc123",
            "timestamp": "2026-09-16T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "prompt": "explain SPIDR and the vertical slice",
        }
        result = self._run("UserPromptSubmit", "jig-memory-scan.sh", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout.decode()
        self.assertIn("additionalContext", out)
        self.assertIn("spidr", out.lower())

    def test_memory_scan_stays_silent_when_no_prompt_field_is_present(self):
        # Negative control: no `prompt` (as when the adapter dropped it) → no
        # surfacing. Pins that the surfacing above is driven by the forwarded
        # prompt, not something ambient in the environment.
        payload = {
            "sessionId": "abc123",
            "workingDirectory": str(self.project_dir),
        }
        result = self._run("UserPromptSubmit", "jig-memory-scan.sh", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("spidr", result.stdout.decode().lower())


class ShippedAdvisoryOutputThroughAdapterTests(unittest.TestCase):
    """Compliance review fix — de-vacuous the shipped-output claim.

    `CopilotHookProtocolTranslationTests` in `test_copilot_renderer.py`
    proves `translate_hook_protocol` COMPUTES the right mapping when called
    directly — but nothing calls it at runtime today (see that method's own
    HONESTY NOTE): `copilot_hook_adapter.py` forwards each advisory hook's
    child stdout VERBATIM. This class pins what a real shipped advisory
    hook ACTUALLY emits through the adapter: `additionalContext` fires
    (the part that matters to a Copilot session), AND `continue` currently
    survives un-stripped (a harmless, documented residual — Copilot's
    `HookOutput` schema simply ignores an unrecognized key; 113-05's
    adapter response-translation, once wired, is what will remove it)."""

    def setUp(self):
        self.project_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-shipped-e2e-"))

    def tearDown(self):
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _run(self, claude_event: str, script_name: str, payload: dict):
        env = {
            **os.environ,
            "TMPDIR": str(self.project_dir),
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
        }
        return subprocess.run(
            [sys.executable, str(ADAPTER_PATH), claude_event,
             str(HOOK_SCRIPTS_DIR / script_name)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=15,
            env=env,
        )

    def test_boundary_warn_shipped_output_fires_and_continue_is_unstripped(self):
        result = self._run("PostToolUse", "jig-boundary-change-warn.sh", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "openapi.yaml"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout.decode())
        self.assertIn("additionalContext", parsed)  # fires
        self.assertIn("openapi.yaml", parsed["additionalContext"])
        self.assertIs(parsed.get("continue"), True)  # documented residual

    def test_entry_gate_shipped_output_fires_and_continue_is_unstripped(self):
        result = self._run("PostToolUse", "jig-entry-gate.sh", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "app.py"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout.decode())
        self.assertIn("additionalContext", parsed)  # fires
        self.assertIs(parsed.get("continue"), True)  # documented residual

    def test_git_freshness_shipped_output_fires_and_continue_is_unstripped(self):
        _make_repo_behind_origin_main(self.project_dir)
        result = self._run("SessionStart", "jig-git-freshness.sh", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "source": "startup",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout.decode())
        self.assertIn("additionalContext", parsed)  # fires
        self.assertIs(parsed.get("continue"), True)  # documented residual


class DenyResponseMatchesTranslateHookProtocolTests(unittest.TestCase):
    """Slice 113-05 DoR — the adapter's enforcing-mode deny-JSON builder
    (`_deny_response`) intentionally DUPLICATES (not imports)
    `CopilotScaffoldRenderer.translate_hook_protocol`'s `block_reason` ->
    `permissionDecision`/`permissionDecisionReason` mapping (the adapter
    ships standalone — see its own module docstring). This pins the
    duplicate in sync with the original so they cannot silently drift
    apart, mirroring `ReverseToolMapConsistencyTests`'s own idiom for
    `_COPILOT_TO_CLAUDE_TOOL_NAME`."""

    def _renderer(self):
        return scaffold.CopilotScaffoldRenderer(plugin=Path("."), target=Path("."))

    def test_matches_for_a_nonempty_reason(self):
        reason = "Blocked: some reason.\n"
        self.assertEqual(
            copilot_hook_adapter._deny_response(reason),
            self._renderer().translate_hook_protocol({"block_reason": reason}),
        )

    def test_matches_for_an_empty_reason(self):
        self.assertEqual(
            copilot_hook_adapter._deny_response(""),
            self._renderer().translate_hook_protocol({"block_reason": ""}),
        )


class EnforcingModeTests(unittest.TestCase):
    """Slice 113-05 AC1 — the `--enforce` argv flag against the REAL
    (unmodified) `jig-spec-gate.sh` / `jig-secret-scan.sh`: exit code
    preserved end to end (a block denies with exit 2 + a deny JSON body; an
    allow stays exit 0), and the identical payload WITHOUT `--enforce` stays
    fail-open (regression guard against the two modes bleeding into each
    other)."""

    # Built by concatenation, not a literal, so this TEST FILE's own source
    # text never contains the contiguous AWS-key-shaped substring — jig's
    # OWN secret-scan gate (the enforcing hook this test class exercises)
    # would otherwise block editing this very file. The concatenated VALUE
    # is what actually reaches `jig-secret-scan.sh` at test-runtime, via
    # the subprocess payload below, which is what the test needs.
    _FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"

    def setUp(self):
        self.project_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-enforce-"))

    def tearDown(self):
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _run(self, script_name: str, payload: dict, *, enforcing: bool, extra_env=None):
        script_path = HOOK_SCRIPTS_DIR / script_name
        argv = [sys.executable, str(ADAPTER_PATH)]
        if enforcing:
            argv.append("--enforce")
        argv += ["PreToolUse", str(script_path)]
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
            **(extra_env or {}),
        }
        return subprocess.run(
            argv, input=json.dumps(payload).encode(),
            capture_output=True, timeout=15, env=env,
        )

    def test_spec_gate_allows_a_non_gated_file_with_exit_0(self):
        result = self._run("jig-spec-gate.sh", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "README.md"},
        }, enforcing=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_spec_gate_denies_conventions_md_with_exit_2_and_a_deny_body(self):
        result = self._run("jig-spec-gate.sh", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "docs/conventions.md"},
        }, enforcing=True)
        self.assertEqual(result.returncode, 2)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")
        self.assertIn("deliberate approval", deny["permissionDecisionReason"])

    def test_spec_gate_allows_conventions_md_when_approved(self):
        result = self._run(
            "jig-spec-gate.sh",
            {
                "sessionId": "abc123",
                "toolName": "edit",
                "toolArgs": {"path": "docs/conventions.md"},
            },
            enforcing=True,
            extra_env={"JIG_CONVENTIONS_APPROVED": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_secret_scan_allows_benign_content_with_exit_0(self):
        result = self._run("jig-secret-scan.sh", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "config.py", "new_string": "hello world"},
        }, enforcing=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_secret_scan_denies_an_aws_key_with_exit_2_and_a_deny_body(self):
        result = self._run("jig-secret-scan.sh", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {
                "path": "config.py",
                "new_string": self._FAKE_AWS_KEY,
            },
        }, enforcing=True)
        self.assertEqual(result.returncode, 2)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")
        self.assertIn("secret pattern", deny["permissionDecisionReason"])

    def test_advisory_mode_stays_fail_open_for_the_same_blocked_edit(self):
        # Regression guard: the SAME payload that denies under --enforce
        # must stay exit 0 without it — the two modes must not bleed into
        # each other.
        result = self._run("jig-spec-gate.sh", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "docs/conventions.md"},
        }, enforcing=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unresolvable_script_path_denies_via_bashs_own_nonzero_exit(self):
        # `bash` itself spawns fine and reports ITS OWN non-zero exit (e.g.
        # 127, "No such file or directory") for an unresolvable script path
        # — this hits the ordinary non-zero-exit deny branch, not the
        # spawn-exception one (see EnforcingModeSpawnFailureTests for that
        # one, which needs a mock since `bash` itself is always present).
        result = subprocess.run(
            [sys.executable, str(ADAPTER_PATH), "--enforce", "PreToolUse",
             "/no/such/script.sh"],
            input=b"{}", capture_output=True, timeout=15,
        )
        self.assertNotEqual(result.returncode, 0)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")

    def test_too_few_args_after_enforce_flag_returns_zero(self):
        # In-process (no target script identified — nothing to spawn,
        # mirrors MainInvocationTests.test_too_few_args_returns_zero).
        self.assertEqual(
            copilot_hook_adapter.main(["adapter.py", "--enforce"]), 0
        )
        self.assertEqual(
            copilot_hook_adapter.main(["adapter.py", "--enforce", "PreToolUse"]),
            0,
        )


class EnforcingModeSpawnFailureTests(unittest.TestCase):
    """Slice 113-05 — enforcing mode's fail-CLOSED spawn-exception branch
    (the opposite of advisory's fail-open one — see the module docstring).
    Hard to trigger via a real subprocess (`bash` itself is a hard OS
    dependency every jig hook script already assumes present, so a bad
    SCRIPT path still lets `bash` spawn and fail on its own — see
    `EnforcingModeTests.test_unresolvable_script_path_denies_via_bashs_own_nonzero_exit`)
    — a mocked `subprocess.run` isolates the adapter-level spawn exception
    itself."""

    def test_spawn_exception_denies_with_exit_2(self):
        fake_stdin = mock.Mock()
        fake_stdin.buffer.read.return_value = b"{}"
        with mock.patch.object(sys, "stdin", fake_stdin), \
             mock.patch.object(
                 copilot_hook_adapter.subprocess, "run",
                 side_effect=OSError("boom"),
             ), \
             mock.patch.object(sys, "stdout") as fake_stdout, \
             mock.patch.object(sys, "stderr"):
            code = copilot_hook_adapter.main(
                ["adapter.py", "--enforce", "PreToolUse", "/some/script.sh"]
            )
        self.assertEqual(code, 2)
        written = b"".join(
            call_args.args[0]
            for call_args in fake_stdout.buffer.write.call_args_list
        )
        deny = json.loads(written.decode())
        self.assertEqual(deny["permissionDecision"], "deny")
        self.assertIn("boom", deny["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
