#!/usr/bin/env python3
"""
copilot_hook_adapter.py — slice 113-04 (advisory-hooks), the INPUT half of
the hook-protocol translation layer (AC1: "adapts the payload/field access
the hook scripts read").

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
This unconditional-exit-0 posture is scoped to the 3 ADVISORY hooks this
slice fronts — it is the wrong posture for an ENFORCING hook (spec-gate,
review-evidence, bug-closure), whose `permissionDecision` deny signal must
actually reach Copilot; 113-05 must wire a different exit/response posture
for those rather than reuse this one as-is (see `main`'s own comment).

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
from typing import Optional

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


def main(argv: list) -> int:
    if len(argv) < 3:
        # Fail-open: a malformed invocation must not raise a traceback to
        # Copilot's own hook runner. Nothing meaningful to run.
        return 0
    claude_event, script_path = argv[1], argv[2]

    raw = sys.stdin.buffer.read()
    translated = translate_payload(raw, claude_event)

    env = dict(os.environ)
    working_dir = project_dir_from_payload(raw)
    if working_dir and "CLAUDE_PROJECT_DIR" not in env:
        env["CLAUDE_PROJECT_DIR"] = working_dir

    try:
        subprocess.run(["bash", script_path], input=translated, env=env)
    except Exception:
        # Fail-open: an adapter-side spawn failure (e.g. the script path
        # does not resolve — the still-unverified plugin-root-relative
        # residual) must never look like a blocking error to Copilot.
        pass
    # Always 0, regardless of the child's own exit code — but this posture
    # is scoped to the 3 ADVISORY hooks this slice (113-04) actually fronts
    # (session git-freshness, boundary-change-warn, entry-gate-nudge). Each
    # already ends with an unconditional `exit 0` of its own (best-effort —
    # AC3), so the only way `bash` itself would report non-zero here is a
    # packaging/path problem (the command-path residual this slice already
    # flags), not a hook-logic failure. Masking that into 0 is the same
    # "never blocks" guarantee those scripts already give Claude/Codex,
    # extended to Copilot rather than relaxed for it. This is NOT the right
    # posture for an ENFORCING hook (spec-gate, review-evidence,
    # bug-closure): those need their `permissionDecision`/deny signal to
    # actually reach Copilot, which an unconditional exit 0 would mask.
    # 113-05, which adds those, must wire a DIFFERENT (or parameterized)
    # exit/response posture for them rather than reusing this one as-is.
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
