#!/bin/bash
# Spec gate (deliberateness gate — see Rationale): blocks Edit/Write to
# docs/conventions.md unless JIG_CONVENTIONS_APPROVED=1 is set in the environment.
#
# Fires on PreToolUse / Edit|Write|MultiEdit. Exit 2 to block; exit 0 to allow.
#
# Rationale (see ADR-0011): docs/conventions.md encodes project rules. This gate
# is a DELIBERATENESS check, not a human-only guarantee. The env var is
# satisfiable by anyone with a shell — including the agent itself, via Bash — so
# it does NOT enforce human approval. What it reliably catches is the ACCIDENTAL
# case: an agent editing conventions.md as a side effect of unrelated work won't
# have the flag set, so the stray edit is blocked. A deliberate actor sets the
# flag to proceed. True human-only enforcement is out of scope for an in-process
# hook (a hook runs inside the agent's trust boundary); enforce it out-of-band —
# CODEOWNERS on docs/conventions.md, a CI check on the PR diff, or branch
# protection.
#
# Layout note: this gate is jig-layout-specific — it matches docs/conventions.md
# only. A project using a different constitution path (e.g. root CONVENTIONS.md)
# gets no gate. A configurable gated set (JIG_GATED_FILES) is a deferred
# enhancement (ADR-0011 Scope).
python3 -c "
import sys, json, os

try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path') or tool_input.get('path') or ''
    if not file_path:
        sys.exit(0)

    # Normalize to defeat path-traversal bypasses like
    # 'foo/docs/conventions.md/../conventions.md'. realpath resolves symlinks too.
    try:
        resolved = os.path.realpath(file_path) if os.path.isabs(file_path) else os.path.normpath(file_path)
    except Exception:
        sys.exit(0)

    # Gate the resolved path docs/conventions.md (absolute suffix or relative match)
    if not (resolved.endswith(os.sep + 'docs' + os.sep + 'conventions.md')
            or resolved == os.path.join('docs', 'conventions.md')):
        sys.exit(0)

    if os.environ.get('JIG_CONVENTIONS_APPROVED') == '1':
        sys.exit(0)

    sys.stderr.write(
        'Blocked: docs/conventions.md changes require deliberate approval.\n'
        'This gate catches accidental side-effect edits; it is not a human-only '
        'guarantee.\n'
        'If this change is intentional, set JIG_CONVENTIONS_APPROVED=1 in your '
        'shell session and retry.\n'
    )
    sys.exit(2)
except SystemExit:
    raise
except Exception as exc:
    sys.stderr.write(f'jig-spec-gate hook error: {exc}\n')
    sys.exit(0)
"
