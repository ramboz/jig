#!/bin/bash
# Lifecycle entry gate (spec 098-01 / ADR-0044). Fires on PostToolUse
# Edit/Write/MultiEdit, co-located with jig-post-edit-verify.sh and
# jig-boundary-change-warn.sh. When an edit to PROJECT SOURCE happens while the
# session is NOT inside the jig lifecycle (no working-lifecycle claim held by
# this checkout), it injects one soft additionalContext nudge — "route it or
# record it". Never blocks, never prompts the owner; opt-out JIG_ENTRY_GATE=0;
# any error fails open (the session is left untouched). Fires at most once per
# session, re-armed when lifecycle state changes.
#
# All logic lives in the testable helper lib/entry_gate.py; this wrapper only
# marshals stdin, prints the nudge, and leaves the auditable trace.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os

script_dir = os.environ.get('SCRIPT_DIR', '.')
# entry_gate lives in lib/; it imports _common.* from the sibling skills/ dir
# (plugin root and .codex/ both carry skills/ beside hooks/).
for p in (script_dir, os.path.join(script_dir, '..', '..', 'skills')):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except Exception:
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)

    project_dir = os.environ.get('CODEX_PROJECT_DIR', '.')
    state_dir = os.environ.get('TMPDIR') or '/tmp'

    from lib.entry_gate import evaluate
    nudge = evaluate(payload, project_dir, state_dir)
    if nudge:
        try:
            from lib.read_attribution import append_additional_context_event
            append_additional_context_event(
                project_dir,
                payload.get('session_id') or 'default',
                payload.get('hook_event_name') or 'PostToolUse',
                'jig-entry-gate', 'out_of_lifecycle_edit', nudge)
        except Exception:
            pass
        print(json.dumps({'continue': True, 'additionalContext': nudge}))
except SystemExit:
    raise
except Exception:
    pass
"
exit 0
