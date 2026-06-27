#!/bin/bash
# In-flight decision capture (slice 083-07). The deterministic fast path that
# 083-04's Stop-hook scan complements: it writes a one-line stub to a per-session
# scratch log THE MOMENT a Tier-1 structured decision settles, so capture does
# not depend on the agent attending at session end.
#
# Two hook points (registered in hooks.json):
#   - PostToolUse matcher=AskUserQuestion -> stub the user's answer.
#   - UserPromptSubmit -> stub the message IFF it carries a Tier-2 override marker
#     (reuses decision_scan.is_user_override so in-flight + scan agree).
#
# It only WRITES a scratch stub; surfacing stays owner-gated at the Stop hook
# (jig-decision-capture.sh reads, dedups, surfaces, clears). Fully fail-open: any
# error leaves the session untouched, and ephemera produce no stub.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os

script_dir = os.environ.get('SCRIPT_DIR', '.')
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from lib.decision_scratch import (
        append_stub, extract_askuserquestion_answer, is_override)

    data = json.load(sys.stdin)
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
    session_id = data.get('session_id') or 'default'
    event = data.get('hook_event_name') or ''

    if event == 'PostToolUse' and data.get('tool_name') == 'AskUserQuestion':
        answer = extract_askuserquestion_answer(
            data.get('tool_response'), data.get('tool_input'))
        append_stub(project_dir, session_id, 'user', answer, 'askuserquestion')
    elif event == 'UserPromptSubmit':
        prompt = data.get('prompt') or ''
        if is_override(prompt):
            append_stub(project_dir, session_id, 'user', prompt, 'user-override')
except Exception:
    pass
"
exit 0
