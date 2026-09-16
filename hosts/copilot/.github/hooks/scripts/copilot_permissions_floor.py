#!/usr/bin/env python3
"""
copilot_permissions_floor.py — slice 113-05 (enforcing-hooks-and-permissions),
owner reshape of AC3: a Copilot-render-only ENFORCING `preToolUse` hook that
restores jig's `_PERMISSIONS_DENY_DEFAULTS` security floor (ADR-0013) as an
actual DENY GATE, not a settings.json file.

WHY THIS EXISTS (corrects an earlier `.github/copilot/settings.json`
attempt this same slice tried): the installed Copilot CLI (1.0.86-0) has NO
persistent, repo-committable tool-deny mechanism. `copilot help config`'s
own authored list of PERSISTED settings.json keys documents `allowedUrls`/
`deniedUrls` (URL rules) and `hooks`, but no tool-allow/deny key —
`--deny-tool`/`--allow-tool` are SESSION-scoped CLI flags with no
settings.json counterpart. A rendered `deniedTools` settings.json entry
would therefore be a DEAD FILE Copilot never reads. This script restores
the "keep their teeth" floor the way Copilot DOES support durable
enforcement: a committed, file-configurable `preToolUse` hook
(`.github/hooks/*.json`) that runs on every shell-tool call and denies
(`exit 2`) a destructive one.

Ships standalone into the Copilot package ONLY (copied verbatim by
`build_copilot_plugin.py`, alongside `copilot_hook_adapter.py`, into
`hosts/copilot/.github/hooks/scripts/`) — never touches canonical
`hooks/scripts/*.sh` / `lib/*.py`, and never imports `scaffold.py`, mirroring
`copilot_hook_adapter.py`'s own standalone design (see that file's module
docstring): the Copilot package's `.github/hooks/scripts/` directory stays
free of a cross-package dependency into `.github/skills/`.

Invocation contract: always run BEHIND `copilot_hook_adapter.py` in
`--enforce` mode (`CopilotScaffoldRenderer.render_permissions_floor_hook`
is the only renderer of this hook's `.github/hooks/*.json` entry, and it
always sets `enforcing=True`) — this script reads jig's translated
snake_case PreToolUse payload on stdin, the SAME shape
`jig-spec-gate.sh`/`jig-secret-scan.sh` read. It extracts the shell command
from `tool_input["command"]` — confirmed as the field the adapter's
`translate_payload` copies `toolArgs` into VERBATIM (`toolArgs` is copied
whole into `tool_input`), and `command` as the actual argument key for
Copilot's built-in shell-exec tool call: the shipped `copilot-sdk`
`generated/rpc.d.ts`'s `ShellExecRequest` interface
(`{command: string; cwd?: string; ...}`, referenced by the RPC schema
definition "ShellExecRequest") is the concrete evidence for this key name.
(The hook's `matcher` — which tool name actually fires this hook — is
`CLAUDE_TO_COPILOT_TOOLS["Bash"]`, `"bash"`; see
`CopilotScaffoldRenderer.render_permissions_floor_hook`'s own docstring for
that evidence, which is separate from this file's `command`-key evidence.)

On a destructive-pattern match: writes a deny reason to stderr and exits 2
(denied, per the authoritative Copilot hook contract: a non-zero exit code
alone denies, regardless of stdout). Otherwise exits 0. Fails OPEN on any
internal error — a bug in this floor must never wedge every shell command —
matching jig's OTHER deliberateness gates' own posture
(`jig-spec-gate.sh` / `jig-secret-scan.sh`: "Exception -> exit 0").

Pattern coverage (fuller than Copilot's OWN `shell()` permission-pattern
syntax could faithfully express — see
`CopilotScaffoldRenderer.copilot_permission_pattern`'s superseded docstring
in this slice's own history: 6 of jig's 8 Claude deny defaults transliterate
into Copilot's prefix-match-only `shell(command:*?)` syntax, but the 2
mid-string-wildcard force-push variants do not): `DESTRUCTIVE_COMMAND_PATTERNS`
below covers ALL 8, because a PYTHON SCRIPT matching against a known stdin
string can search the whole command line, not just its prefix.

`_PERMISSIONS_DENY_DEFAULTS` below is DUPLICATED (not imported) from
`scaffold._PERMISSIONS_DENY_DEFAULTS` — this file ships standalone with no
`scaffold.py` import dependency, the SAME "duplicate, drift-guarded" idiom
`copilot_hook_adapter._COPILOT_TO_CLAUDE_TOOL_NAME` and `_deny_response`
already established. `test_copilot_permissions_floor.py`'s
`PatternsMatchCanonicalFloorTests` asserts EXACT (order-sensitive) equality
against the canonical tuple so the two cannot silently drift apart; each
regex is then MECHANICALLY derived from its own pattern string (bash-glob
`*` -> regex `.*`, everything else escaped literally) rather than
hand-authored per pattern, minimizing the risk of a human transcription
error and keeping the regex a transparent function of the duplicated
string it comes from.

RESIDUAL (per the coordinator's own honest note): a real Copilot hook could
not be made to fire under headless `copilot -p` in 6 attempts (a
non-interactive/folder-trust limitation) — verified instead by
DETERMINISTIC, POSITIVE-CONFIRMATION subprocess tests
(`test_copilot_permissions_floor.py`'s `EnforcingEndToEndTests`): a real
destructive command run through the REAL `copilot_hook_adapter.py
--enforce` in front of this UNMODIFIED script actually denies (`exit 2` +
a `permissionDecision: deny` body), and a real safe command actually
allows (`exit 0`, empty stdout). Live-firing under an actual Copilot
session remains a post-push/interactive residual, same as 113-04's
plugin-root-path spelling.
"""

from __future__ import annotations

import json
import re
import sys

# Duplicated (not imported) from `scaffold._PERMISSIONS_DENY_DEFAULTS` — see
# the module docstring's "Pattern coverage" section. Order matches the
# canonical tuple exactly; `PatternsMatchCanonicalFloorTests` pins the two
# in sync.
_PERMISSIONS_DENY_DEFAULTS = (
    "Bash(git push --force*)",
    "Bash(git push -f *)",
    "Bash(git push * --force*)",
    "Bash(git push *--force-with-lease*)",
    "Bash(git reset --hard*)",
    "Bash(rm -rf*)",
    "Bash(rm -fr*)",
    "Bash(rm -r -f*)",
)


def _pattern_to_regex(claude_pattern: str):
    """Mechanically compile one `Bash(<glob>)` pattern's inner glob text
    into a regex matching the SAME literal shape ANYWHERE in a command line
    (each bash-glob `*` -> regex `.*`; every other character escaped
    literally). Anywhere-matching is a deliberately BROADER search than
    Claude's own prefix-anchored `permissions.deny` semantics — a script
    scanning a known string can afford to be broader, and broader here
    means MORE protective, not less."""
    inner = claude_pattern[len("Bash("):-1]
    return re.compile(".*".join(re.escape(part) for part in inner.split("*")))


# One (canonical Claude pattern string, compiled regex) pair per entry in
# `_PERMISSIONS_DENY_DEFAULTS`, in the same order.
DESTRUCTIVE_COMMAND_PATTERNS = tuple(
    (pattern, _pattern_to_regex(pattern)) for pattern in _PERMISSIONS_DENY_DEFAULTS
)


def matched_pattern(command: str):
    """Return the first canonical Claude pattern string whose glob shape
    matches `command` anywhere, or `None` if none match."""
    for claude_pattern, regex in DESTRUCTIVE_COMMAND_PATTERNS:
        if regex.search(command):
            return claude_pattern
    return None


def main(argv: list) -> int:
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8") or "{}")
        tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
        command = (
            tool_input.get("command") if isinstance(tool_input, dict) else None
        )
        if not isinstance(command, str) or not command.strip():
            # Nothing to scan (a non-shell tool call slipped through the
            # matcher, or a malformed/empty payload) -> allow.
            return 0

        hit = matched_pattern(command)
        if hit is None:
            return 0

        sys.stderr.write(
            "Blocked: this command matches jig's destructive-command "
            f"permissions floor ({hit}).\n"
            "This is a defense-in-depth deliberateness gate — NOT a "
            "guarantee that a destructive command never runs. Real "
            "enforcement stays out-of-band (branch protection, server-side "
            "hooks, CI).\n"
        )
        return 2
    except Exception as exc:
        # Fail-open: a bug in this floor must never wedge every shell
        # command (same posture as jig-spec-gate.sh / jig-secret-scan.sh).
        sys.stderr.write(f"copilot_permissions_floor error: {exc}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
