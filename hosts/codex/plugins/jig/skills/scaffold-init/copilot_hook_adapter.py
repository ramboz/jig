#!/usr/bin/env python3
"""
copilot_hook_adapter.py — slice 113-04 (advisory-hooks), the INPUT half of
the hook-protocol translation layer (AC1: "adapts the payload/field access
the hook scripts read"); grown by slice 113-05 (enforcing-hooks-and-
permissions) with an enforcing mode (`--enforce`) that preserves exit codes
for blocking gates.

Rendered ONLY into the Copilot package (copied verbatim by
`build_copilot_plugin.py` to `hosts/copilot/.github/hooks/scripts/`) — never
shipped to Claude or Codex, and it never touches canonical
`hooks/scripts/*.sh` / `hooks/scripts/lib/*.py`, which stay byte-identical
across all three hosts. This file lives beside `scaffold.py` (the render
layer), not under `hooks/scripts/`, precisely so it is never mistaken for a
cross-host shared hook script.

Why this exists: jig's shared advisory hook scripts read Claude-shaped,
snake_case stdin JSON (`tool_name` valued `"Edit"`/`"Write"`/`"MultiEdit"`,
`tool_input.file_path`, `session_id`, `hook_event_name`) and locate the
project directory via the `CLAUDE_PLUGIN_ROOT`-sibling `CLAUDE_PROJECT_DIR`
environment variable. Copilot's file-configurable hooks send camelCase
stdin JSON per the shipped CLI's own `copilot-sdk/types.d.ts`
(`BaseHookInput`: `sessionId` / `timestamp` / `workingDirectory`;
`PostToolUseHookInput` adds `toolName` / `toolArgs`) and expose no
analogous environment variable. This adapter sits between Copilot and the
UNMODIFIED jig script: it reads Copilot's stdin JSON, re-shapes it into the
structure the target script already expects, exports `CLAUDE_PROJECT_DIR`
for the child process from `workingDirectory`, invokes the target script
with the re-shaped JSON on stdin, and transparently forwards its
stdout/stderr/exit code.

Field mapping (grounded in `copilot-sdk/types.d.ts` `BaseHookInput` /
`PreToolUseHookInput` / `PostToolUseHookInput`, and the shipped `app.js`
built-in file-tool argument schemas):
  sessionId        -> session_id
  toolName         -> tool_name, VALUE-translated via
                      `_COPILOT_TO_CLAUDE_TOOL_NAME` (Copilot's own
                      lowercase tool vocabulary — confirmed in `app.js`:
                      `e==="edit"||e==="create"?t.path:null` — back to the
                      PascalCase names jig's shared scripts hardcode
                      (`"Edit"`, `"Write"`); this is the REVERSE of
                      `CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS`
                      (113-03), pinned in sync by
                      `test_copilot_hook_adapter.py`'s
                      `ReverseToolMapConsistencyTests`.
  toolArgs         -> tool_input (copied whole; `toolArgs.path`, confirmed
                      as the file-path argument key for Copilot's built-in
                      edit/create/view tool family in the shipped app.js —
                      `Xd({command:…,path:Sa(),…})`, `Xd({path:Sa(),
                      view_range:…})`, and the `t.path` access above — is
                      ALSO written to `tool_input.file_path`, the only key
                      jig's 3 advisory hooks + `lib/protected_paths.py`
                      read out of `tool_input`).
  workingDirectory -> NOT a payload key any target script reads; instead
                      exported as the `CLAUDE_PROJECT_DIR` environment
                      variable for the child process (the mechanism jig's
                      scripts already use to locate the project root),
                      only when not already set in this process's own
                      environment.
  (no Copilot field)-> `hook_event_name` is set from this adapter's own
                      first command-line argument (the Claude event name
                      the calling `.github/hooks/*.json` entry was
                      rendered for) since Copilot's `BaseHookInput` carries
                      no event-name field — the event is implicit in which
                      hook file/key fired, information the renderer already
                      has statically at build time
                      (`CopilotScaffoldRenderer.build_hook_command`).
  source           -> passed through unchanged (`SessionStartHookInput`'s
                      `source` field is spelled identically in both hosts;
                      no translation needed — read by `lib/git_freshness.py`).

Fail-open (AC3): ANY translation error falls back to forwarding the
ORIGINAL, untranslated stdin bytes to the target script unchanged — the
target script's own `.get()`-based reads already tolerate a payload missing
expected keys (this is the SAME graceful-degradation behavior these scripts
have today under any foreign payload), so a translation bug produces, at
worst, a missing nudge — never a crash. This adapter also never raises: a
malformed invocation, an unreadable target script, or a spawn failure all
return exit 0 rather than propagating an error to Copilot's own hook runner.
This unconditional-exit-0 posture is scoped to ADVISORY hooks (the default
mode) — it is the wrong posture for an ENFORCING hook (spec-gate,
secret-scan), whose `permissionDecision` deny signal must actually reach
Copilot.

Enforcing mode (113-05, NEW): invoked with a leading `--enforce` argv flag
(before `<claude_event>`), `main()` switches from the advisory posture
above to one that PRESERVES the target script's exit code, per the
AUTHORITATIVE Copilot hook contract (GitHub's own hooks reference): exit 0
allows; exit 2 (and, generalizing the same contract's "other non-zero ->
fail-closed deny too", ANY non-zero exit) denies — the non-zero exit code
ALONE is what Copilot treats as a deny, regardless of stdout content. On a
non-zero exit this adapter ALSO overwrites its own stdout with an explicit
`{"permissionDecision": "deny", "permissionDecisionReason": <reason>}` body
(belt-and-suspenders, not the primary mechanism) built by `_deny_response`,
using the child's stderr (jig's spec-gate/secret-scan write their block
message there) as the human-readable reason, falling back to stdout, then
to an empty reason. `_deny_response` intentionally DUPLICATES — rather than
imports — `CopilotScaffoldRenderer.translate_hook_protocol`'s
`block_reason` -> `permissionDecision`/`permissionDecisionReason` mapping
(see that method's own HONESTY NOTE): this adapter ships standalone with no
`scaffold.py` import dependency (the SAME design choice already made for
`_COPILOT_TO_CLAUDE_TOOL_NAME` below), and
`test_copilot_hook_adapter.DenyResponseMatchesTranslateHookProtocolTests`
pins the duplicate in sync so the two cannot silently drift apart.

An adapter-level SPAWN failure (e.g. an unresolved script path) in
enforcing mode fails CLOSED (`exit 2` + a stderr message), the opposite of
advisory's fail-OPEN: silently allowing every future edit through on a
packaging bug would be exactly the "gate quietly stops blocking" failure
ADR-0061's "keep their teeth / degrade visibly, not silently" invariant
forbids — a loud, deterministic deny is the safer failure mode for a
gate whose entire purpose is blocking.

Interpreter selection (113-05, NEW — see `_interpreter_for`): every target
script through 113-04 was a `.sh` file, so `main()` always spawned `bash
<script_path>`. 113-05 adds `copilot_permissions_floor.py` (the
destructive-command permissions-floor hook, a standalone PYTHON module
rather than a bash wrapper — see ITS module docstring), so this adapter now
picks `python3` for a `.py` target and `bash` for everything else, still
reading the SAME translated stdin JSON and passing the SAME environment
either way.

RESIDUAL (fail-open covers a wrong guess with a no-op, not breakage): the
`toolArgs.path` mapping and the `edit`/`create` tool-name vocabulary are
grounded in the shipped CLI's OWN schemas and switch statements (not the
Adobe guide), but have not been confirmed against a live Copilot session
emitting a REAL PostToolUse hook payload — see the slice's report for the
verification method used instead (direct adapter + target-script
invocation with a constructed payload). If a future Copilot version (or a
tool this slice did not inspect) uses a different key or name, the
downstream script silently no-ops, matching today's already-fail-open
behavior for an unrecognized payload shape.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Bug 036 — the SessionStart hook that also publishes jig's runtime root.
# Exactly one publisher, so the announcement is not repeated once per
# SessionStart hook. `jig-project-orient` is the natural carrier: it already
# exists to tell the session where it is.
ROOT_PUBLISHER_SCRIPT = "jig-project-orient.sh"


def jig_root() -> str:
    """Absolute path of jig's runtime root, derived from this adapter's own
    location: the adapter ships at `<root>/hooks/scripts/copilot_hook_adapter.py`,
    so the root is two parents up. Self-locating on purpose — Copilot exposes
    no plugin-root environment variable, and the hook runner is the one place
    that reliably executes plugin-resident code, so this is where the value
    can be learned without a filesystem search."""
    return str(Path(__file__).resolve().parents[2])


def merge_root_context(stdout: bytes) -> bytes:
    """Fold the runtime-root announcement into a SessionStart hook body.

    Merges rather than replaces so the carrier hook's own `additionalContext`
    (the "jig hint: ..." orientation line) still reaches the session. Any
    unparseable or non-object child output is treated as empty — fail-open,
    matching the advisory contract everywhere else in this adapter."""
    note = (
        "jig runtime root: JIG_ROOT=" + jig_root() + " — jig skills document "
        'helper commands as `python3 "$JIG_ROOT/skills/<skill>/<helper>.py"`. '
        "Substitute this value (or export JIG_ROOT) when running them; "
        "Copilot exposes no plugin-root environment variable."
    )
    data = None
    if stdout and stdout.strip():
        try:
            data = json.loads(stdout.decode("utf-8", errors="replace"))
        except ValueError:
            data = None
    if not isinstance(data, dict):
        data = {}
    existing = data.get("additionalContext")
    existing = existing if isinstance(existing, str) and existing else ""
    data["additionalContext"] = (existing + "\n" if existing else "") + note
    data.setdefault("continue", True)
    return json.dumps(data).encode("utf-8")

# Slice 113-03's CLAUDE_TO_COPILOT_TOOLS (scaffold.py) is the forward
# (Claude -> Copilot) direction, used to RENDER agent tool lists and hook
# matchers. This is its REVERSE for the two file-editing tool names jig's
# shared hook scripts actually gate on — `test_copilot_hook_adapter.py`
# pins the two in sync so they cannot silently drift apart. Deliberately
# NOT imported from `scaffold.py`: this file ships standalone into the
# Copilot package (a sibling of `hooks/scripts/`, not `skills/`), so it
# carries no cross-package import dependency.
_COPILOT_TO_CLAUDE_TOOL_NAME = {
    "edit": "Edit",
    "create": "Write",
}


def translate_payload(raw: bytes, claude_event: str) -> bytes:
    """Return the re-shaped, snake_case JSON (as bytes) jig's hook scripts
    expect, translated from Copilot's camelCase stdin JSON. On ANY error,
    returns `raw` unchanged (fail-open — see the module docstring)."""
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            return raw

        out: dict = {"hook_event_name": claude_event}

        if "sessionId" in payload:
            out["session_id"] = payload["sessionId"]

        if "toolName" in payload:
            tool_name = payload["toolName"]
            out["tool_name"] = _COPILOT_TO_CLAUDE_TOOL_NAME.get(tool_name, tool_name)

        tool_args = payload.get("toolArgs")
        if isinstance(tool_args, dict):
            tool_input = dict(tool_args)
            if "path" in tool_args:
                tool_input["file_path"] = tool_args["path"]
            out["tool_input"] = tool_input

        if "source" in payload:
            out["source"] = payload["source"]

        # userPromptSubmitted supplies `prompt` (SDK UserPromptSubmittedHookInput);
        # jig's prompt-consuming hooks (jig-memory-scan, jig-decision-inflight) read
        # `data['prompt']`. Without this they saw only the base fields and degraded
        # to a silent no-op (113-06 craft review).
        if "prompt" in payload:
            out["prompt"] = payload["prompt"]

        # When AgentStop supplies transcriptPath, shared advisory hooks accept
        # only bounded JSONL conversation records from this path; unknown shapes
        # remain an honest no-op.
        if "transcriptPath" in payload:
            out["transcript_path"] = payload["transcriptPath"]

        return json.dumps(out).encode("utf-8")
    except Exception:
        return raw


def project_dir_from_payload(raw: bytes) -> Optional[str]:
    """Return `workingDirectory` from the raw Copilot payload, or `None` on
    any error or absence — the caller falls back to leaving
    `CLAUDE_PROJECT_DIR` as this process already has it (or unset, which
    jig's scripts' own `os.environ.get('CLAUDE_PROJECT_DIR', '.')` then
    defaults to their CWD, exactly as today)."""
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
        working_dir = payload.get("workingDirectory") if isinstance(payload, dict) else None
        return working_dir if isinstance(working_dir, str) and working_dir else None
    except Exception:
        return None


ENFORCE_FLAG = "--enforce"


def _deny_response(reason: str) -> dict:
    """Build the Copilot deny-decision JSON body for a blocked enforcing
    hook. INTENTIONALLY DUPLICATES (not imports)
    `CopilotScaffoldRenderer.translate_hook_protocol`'s `block_reason` ->
    `permissionDecision`/`permissionDecisionReason` mapping — see the
    module docstring's "Enforcing mode" section for why this stays a
    duplicate rather than an import. Always includes
    `permissionDecisionReason` (even when `reason` is empty), matching
    `translate_hook_protocol`'s own unconditional behavior whenever a
    `block_reason` key is present — pinned exactly by
    `test_copilot_hook_adapter.DenyResponseMatchesTranslateHookProtocolTests`."""
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}


def _interpreter_for(script_path: str) -> str:
    """The interpreter used to run `script_path`: `python3` for a `.py`
    target — `copilot_permissions_floor.py` (113-05's destructive-command
    floor guard) is the first, and so far only, non-bash target this
    adapter fronts — `bash` for every other jig hook script (all `.sh`,
    unchanged since 113-04)."""
    return "python3" if script_path.endswith(".py") else "bash"


def main(argv: list) -> int:
    args = argv[1:]
    enforcing = bool(args) and args[0] == ENFORCE_FLAG
    if enforcing:
        args = args[1:]
    if len(args) < 2:
        # Fail-open: a malformed invocation must not raise a traceback to
        # Copilot's own hook runner. Nothing meaningful to run.
        return 0
    claude_event, script_path = args[0], args[1]

    raw = sys.stdin.buffer.read()
    translated = translate_payload(raw, claude_event)

    env = dict(os.environ)
    working_dir = project_dir_from_payload(raw)
    if working_dir and "CLAUDE_PROJECT_DIR" not in env:
        env["CLAUDE_PROJECT_DIR"] = working_dir

    if not enforcing:
        publishes_root = (
            claude_event == "SessionStart"
            and Path(script_path).name == ROOT_PUBLISHER_SCRIPT
        )
        try:
            if publishes_root:
                # Capture so the root announcement can be merged into the
                # carrier's own body; a single JSON object must reach Copilot.
                result = subprocess.run(
                    [_interpreter_for(script_path), script_path],
                    input=translated, env=env, capture_output=True,
                )
                sys.stdout.buffer.write(merge_root_context(result.stdout))
                if result.stderr:
                    sys.stderr.buffer.write(result.stderr)
            else:
                subprocess.run(
                    [_interpreter_for(script_path), script_path],
                    input=translated, env=env,
                )
        except Exception:
            # Fail-open: an adapter-side spawn failure (e.g. the script
            # path does not resolve — the still-unverified
            # plugin-root-relative residual) must never look like a
            # blocking error to Copilot. Scoped to ADVISORY mode only —
            # see the enforcing branch below for the opposite (fail-closed)
            # posture. The root announcement is best-effort for the same
            # reason: still emitted below so a failed carrier does not cost
            # the session its only route to `$JIG_ROOT`.
            if publishes_root:
                try:
                    sys.stdout.buffer.write(merge_root_context(b""))
                except Exception:
                    pass
        # Always 0, regardless of the child's own exit code. Each of the 3
        # advisory hooks (session git-freshness, boundary-change-warn,
        # entry-gate-nudge) already ends with an unconditional `exit 0` of
        # its own (best-effort — AC3), so the only way `bash` itself would
        # report non-zero here is a packaging/path problem, not a
        # hook-logic failure. Masking that into 0 is the same "never
        # blocks" guarantee those scripts already give Claude/Codex,
        # extended to Copilot rather than relaxed for it.
        return 0

    # Enforcing mode (113-05): preserve the child's exit code so a blocking
    # gate's `exit 2` actually reaches Copilot as a deny — see the module
    # docstring's "Enforcing mode" section for the full contract.
    try:
        result = subprocess.run(
            [_interpreter_for(script_path), script_path], input=translated, env=env,
            capture_output=True,
        )
    except Exception as exc:
        sys.stderr.write(
            f"copilot_hook_adapter: enforcing hook failed to spawn "
            f"{script_path!r}: {exc}\n"
        )
        sys.stdout.buffer.write(
            json.dumps(_deny_response(f"jig enforcing hook adapter error: {exc}"))
            .encode("utf-8")
        )
        return 2

    if result.returncode == 0:
        if result.stdout:
            sys.stdout.buffer.write(result.stdout)
    else:
        # Replace stdout with a single, clean deny body rather than
        # concatenating it after whatever the child already wrote — jig's
        # spec-gate.sh/secret-scan.sh write nothing to stdout on either
        # exit path today, but a future enforcing hook that DOES emit
        # stdout on a non-zero exit must not end up with two JSON objects
        # back to back. The exit code (returned below) is what actually
        # denies per the authoritative contract; this body is
        # belt-and-suspenders context for a human or a client that also
        # reads stdout on a non-zero exit.
        if result.stderr:
            reason = result.stderr.decode("utf-8", errors="replace").strip()
        elif result.stdout:
            reason = result.stdout.decode("utf-8", errors="replace").strip()
        else:
            reason = ""
        sys.stdout.buffer.write(
            json.dumps(_deny_response(reason)).encode("utf-8")
        )
    if result.stderr:
        sys.stderr.buffer.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
