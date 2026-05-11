#!/bin/bash
# Spec gate: blocks Edit/Write to docs/conventions.md unless explicitly approved
# via the JIG_CONVENTIONS_APPROVED=1 environment variable.
#
# Fires on PreToolUse / Edit|Write|MultiEdit. Exit 2 to block; exit 0 to allow.
#
# Rationale: docs/conventions.md encodes project rules. Changes should be a
# deliberate, human-approved act — not something an agent does as a side effect
# of unrelated work. The env var is the simplest viable approval signal.
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
        'Blocked: docs/conventions.md changes require human approval.\n'
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
