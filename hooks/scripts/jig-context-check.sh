#!/bin/bash
# Fires on SessionStart. Emits soft warnings (additionalContext) when the
# session looks at risk of context-fill problems. Never blocks — always
# exits 0, never sets `continue: false`. Hard gates live in servo.
#
# Two branches:
#   1. MCP-server count (legacy proxy). Warns above 8 servers — tool-
#      description overhead pushes Claude toward the dumb zone (>40%
#      context fill, Horthy).
#   2. Context-fill estimate (slice 026-01). Sums primer files
#      (AGENTS.md / CLAUDE.md) + every docs/memory/*.md in the project
#      and warns once the byte total crosses a configured threshold of
#      the model's context window.
#
# Environment variables (both read by lib/context_fill.py):
#   JIG_CONTEXT_WINDOW_BYTES  — context window size in bytes. Default
#                               800_000 (Opus 4.7-sized, ~200K tokens at
#                               4 bytes/token). Override per-model.
#   JIG_CONTEXT_SOFT_WARN_PCT — warning threshold as a fraction of the
#                               window. **Set as 0.30 (not 30)** — the
#                               name says "PCT" but the value is a
#                               fraction in (0, 1]; out-of-range values
#                               silently fall back to the default 0.30
#                               (pre-dumb-zone — gives the user time to
#                               act before recall degrades).
#
# Both warnings can coexist in a single `additionalContext` emission;
# they're concatenated with a blank line between them.

# Resolve the directory this script lives in so the Python helper can
# import lib/context_fill.py regardless of whether jig is running as a
# plugin (${CLAUDE_PLUGIN_ROOT}/hooks/scripts/) or a scaffolded install
# (${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os
script_dir = os.environ.get('SCRIPT_DIR', '.')
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')

    warnings = []

    # ----- Branch 1: MCP server count (legacy proxy) ------------------
    server_count = 0
    for candidate in ['.mcp.json', '.claude/settings.json', '.claude/settings.local.json']:
        path = os.path.join(project_dir, candidate)
        if os.path.exists(path):
            with open(path) as f:
                try:
                    cfg = json.load(f)
                    servers = cfg.get('mcpServers', cfg.get('mcp', {}).get('servers', {}))
                    server_count += len(servers)
                except Exception:
                    pass

    if server_count > 8:
        warnings.append(
            f'Context budget warning: {server_count} MCP servers are configured. '
            'Above ~8 servers, tool description overhead pushes Claude toward the '
            \"'dumb zone' (>40% context fill). Consider disabling unused servers.\"
        )

    # ----- Branch 2: byte-based context-fill estimate (slice 026-01) --
    # The helper lives at <script_dir>/lib/context_fill.py.
    try:
        from pathlib import Path
        from lib.context_fill import estimate, RATIO
        result = estimate(Path(project_dir))
        if result['ratio'] >= result['threshold']:
            pct = result['threshold'] * 100
            actual_pct = result['ratio'] * 100
            warnings.append(
                f\"Context-fill warning: ~{result['bytes']} bytes \"
                f\"(~{result['est_tokens']} tokens at {RATIO} bytes/token) of \"
                f'always-loaded primer + memory content are estimated to '
                f'consume {actual_pct:.1f}% of a {result[\"window_bytes\"]}-byte '
                f'context window — past the {pct:.0f}% soft-warn threshold. '
                'Consider running \`/jig:memory-sync\` to consolidate, then '
                '\`/compact\` to free context.'
            )
    except Exception:
        # Importing the helper or running the estimator must never
        # block the hook. Swallow silently — the MCP branch is a useful
        # fallback signal even when this branch fails.
        pass

    if warnings:
        print(json.dumps({'continue': True, 'additionalContext': '\n\n'.join(warnings)}))
except Exception:
    pass
"
exit 0
