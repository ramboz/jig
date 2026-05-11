#!/bin/bash
# Logs Task tool spawns to .claude/skill-usage.jsonl for skill invocation telemetry.
# Fires async on PreToolUse/Task — never blocks.
python3 - <<'EOF'
import sys, json, os
from datetime import datetime, timezone

try:
    data = json.load(sys.stdin)
    log_dir = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "skill-usage.jsonl")

    tool_input = data.get("tool_input", {})
    prompt = tool_input.get("prompt", tool_input.get("description", ""))
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": data.get("session_id", ""),
        "tool_name": data.get("tool_name", "Task"),
        "prompt_snippet": prompt[:100],
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
except Exception:
    pass  # Telemetry must never block or error visibly
EOF
exit 0
