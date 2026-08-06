#!/bin/bash
# SessionStart git-freshness nudge (spec 103-01 / ADR-0048). Co-located with
# jig-context-check.sh, jig-project-orient.sh, and jig-semantic-index.sh
# under SessionStart. Fires a timeout-guarded `git fetch` of the branch's
# resolved integration base, then nudges — actively recommending a sync —
# when HEAD is behind it. Silent when up-to-date, not a work tree, opted
# out, or on a mid-session `compact` SessionStart. Never blocks, never
# mutates working-tree state beyond the fetch's remote-tracking refs, and
# always exits 0.
#
# All logic lives in the testable helper lib/git_freshness.py; this wrapper
# only marshals stdin, prints the nudge, and leaves the auditable trace.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os

script_dir = os.environ.get('SCRIPT_DIR', '.')
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except Exception:
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)

    project_dir = os.environ.get('CODEX_PROJECT_DIR', '.')

    from lib.git_freshness import evaluate
    nudge = evaluate(payload, project_dir)
    if nudge:
        try:
            from lib.read_attribution import append_additional_context_event
            append_additional_context_event(
                project_dir,
                payload.get('session_id') or 'default',
                payload.get('hook_event_name') or 'SessionStart',
                'jig-git-freshness', 'branch_behind_upstream', nudge)
        except Exception:
            pass
        print(json.dumps({'continue': True, 'additionalContext': nudge}))
except SystemExit:
    raise
except Exception:
    pass
"
exit 0
