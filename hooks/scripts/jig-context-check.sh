#!/bin/bash
# Fires on SessionStart. Counts MCP server entries in project config and warns
# if the count exceeds 8 — the practical edge of the "dumb zone" (Horthy).
python3 - <<'EOF'
import sys, json, os

try:
    data = json.load(sys.stdin)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")

    # Count MCP servers from .mcp.json or .claude/settings.json
    server_count = 0
    for candidate in [".mcp.json", ".claude/settings.json", ".claude/settings.local.json"]:
        path = os.path.join(project_dir, candidate)
        if os.path.exists(path):
            with open(path) as f:
                try:
                    cfg = json.load(f)
                    servers = cfg.get("mcpServers", cfg.get("mcp", {}).get("servers", {}))
                    server_count += len(servers)
                except Exception:
                    pass

    if server_count > 8:
        msg = (
            f"Context budget warning: {server_count} MCP servers are configured. "
            "Above ~8 servers, tool description overhead pushes Claude toward the "
            "'dumb zone' (>40% context fill). Consider disabling unused servers."
        )
        print(json.dumps({"continue": True, "additionalContext": msg}))
except Exception:
    pass  # Never block session start
exit(0)
EOF
exit 0
