#!/bin/bash
# Logs Skill-tool invocations to .codex/skill-usage.jsonl for routing
# observability (spec 041). Fires on PreToolUse/Skill — records which skill
# the model actually invoked, including auto-triggered (implicit) routing,
# so a user can verify a richer user-installed skill won over jig's baseline
# (e.g. `pr-review` vs `jig:pr-review`). Async — never blocks.
#
# Scope note: this captures Skill-TOOL invocations in the MAIN agent. Typed
# `/slash` commands expand via UserPromptExpansion (not PreToolUse), and a
# subagent's own Skill calls are not guaranteed to surface to this hook — see
# docs/skill-routing-verification.md.
#
# `tool_input.skill_name` is an OBSERVED Skill-tool payload field, not a
# documented contract. If upstream renames it, skill_name logs empty rather
# than crashing (pinned by test_missing_tool_input_is_graceful).
python3 -c "
import sys, json, os
from datetime import datetime, timezone

try:
    data = json.load(sys.stdin)
    log_dir = os.path.join(os.environ.get('CODEX_PROJECT_DIR', '.'), '.codex')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'skill-usage.jsonl')

    tool_input = data.get('tool_input', {}) or {}
    skill_name = tool_input.get('skill_name', '')
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'session_id': data.get('session_id', ''),
        'event': 'skill_invoked',
        'tool_name': data.get('tool_name', 'Skill'),
        'skill_name': skill_name,
    }
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')
except Exception:
    pass
"
exit 0
