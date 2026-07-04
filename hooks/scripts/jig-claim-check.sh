#!/bin/bash
# Fires on Stop. The cheapest-first-cut mitigation named in the
# refinement-todo "Memory-recall verification (claims-from-memory linter)"
# entry: scans the LAST assistant message for spec/slice/ADR-shaped claims
# ("spec 042", "slice 042-01", "ADR-0011") and cross-checks each against
# the on-disk inventory (docs/specs/, docs/decisions/). An unresolved claim
# surfaces as additionalContext at the START OF THE NEXT TURN — a nudge to
# verify, never a block. It writes nothing and never fails the session.
#
# Same-turn framing on purpose: only the most recent assistant message is
# scanned (not the whole session), so a flagged claim surfaces once, right
# after the turn that made it, rather than re-nagging on every later Stop.
#
# SCRIPT_DIR locates lib/claim_check.py whether jig runs as a plugin
# (${CLAUDE_PLUGIN_ROOT}/hooks/scripts/) or a scaffolded install
# (${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/). Fully fail-open: any
# error leaves the session untouched.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os

script_dir = os.environ.get('SCRIPT_DIR', '.')
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from lib.claim_check import last_assistant_text, scan_claims, render_warning

    data = json.load(sys.stdin)
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
    messages = data.get('messages', [])

    text = last_assistant_text(messages)
    claims = scan_claims(project_dir, text)
    msg = render_warning(claims)
    if not msg:
        sys.exit(0)

    print(json.dumps({'continue': True, 'additionalContext': msg}))
except Exception:
    pass
"
exit 0
