#!/bin/bash
# Fires on SessionStart, UserPromptSubmit (slice 055-02), AND PreToolUse with
# matcher Read (slice 055-03) — one script, three events; it branches on the
# hook input's `hook_event_name`. Emits soft warnings (additionalContext)
# when the session looks at risk of context-fill problems. Never blocks —
# always exits 0, never sets `continue: false`. Hard gates live in servo.
#
# SessionStart branches (the always-loaded baseline — unchanged by 055-02):
#   1. MCP-server count (legacy proxy). Warns above 8 servers — tool-
#      description overhead pushes Codex toward the dumb zone (>40%
#      context fill, Horthy).
#   2. Context-fill estimate (slice 026-01). Sums CLAUDE.md + every
#      docs/memory/*.md in the project and warns once the byte total
#      crosses a configured threshold of the model's context window.
#
# UserPromptSubmit branch (slice 055-02 — the in-session growth nudge):
#   3. Reads the LAST assistant turn's `cache_read_input_tokens` from the
#      `transcript_path` tail (O(1) — never a full scan) as the current
#      context-size proxy, and nudges when it crosses a band (default 0.40 of
#      the token-window — the dumb-zone line). Fires at most once per band
#      (40/60/80%) per session, tracked in a per-session state file under
#      $TMPDIR; the band re-arms when the estimate drops back below it (e.g.
#      after /compact). Silent + safe when there's no assistant turn yet or
#      the transcript is missing/unreadable/malformed. Slice 057-02 adds a
#      higher active-compaction band (JIG_CONTEXT_COMPACT_PCT, default 0.75):
#      crossing it swaps the warn-only message for an actionable compaction /
#      fresh-session-handoff prompt — same band machinery, different message.
#
# Environment variables (read by lib/context_fill.py):
#   JIG_CONTEXT_WINDOW_BYTES   — context window size in bytes. Default
#                                800_000 (Opus 4.7-sized, ~200K tokens at
#                                4 bytes/token). Override per-model.
#   JIG_CONTEXT_SOFT_WARN_PCT  — SessionStart baseline threshold as a
#                                fraction of the window. **Set as 0.30 (not
#                                30)** — the name says "PCT" but the value is
#                                a fraction in (0, 1]; out-of-range values
#                                silently fall back to the default 0.30
#                                (pre-dumb-zone — gives the user time to act
#                                before recall degrades).
#   JIG_CONTEXT_GROWTH_WARN_PCT — UserPromptSubmit first-band threshold as a
#                                fraction of the window. Default 0.40 (the
#                                dumb-zone line); same out-of-range fallback
#                                as JIG_CONTEXT_SOFT_WARN_PCT.
#   JIG_CONTEXT_COMPACT_PCT     — UserPromptSubmit active-compaction band as a
#                                fraction of the window (slice 057-02). Default
#                                0.75 — above the 40/60 warn bands. Crossing it
#                                escalates from the warn-only growth message to
#                                an actionable compaction / fresh-session-handoff
#                                prompt (with a carry-over hint). Rides the same
#                                once-per-band + re-arm-on-drop machinery; only
#                                the message differs. jig recommends — it never
#                                runs /compact (ADR-0011). Same out-of-range
#                                fallback as the other PCT knobs.
#   JIG_READ_LEAN_BYTES        — PreToolUse(Read) large-whole-file threshold
#                                in bytes (slice 055-03). A whole-file Read
#                                (no offset/limit) of a file at/above this
#                                size is nudged toward offset/limit. Default
#                                65536 (64 KiB); out-of-range / non-numeric
#                                values silently fall back to the default.
#
# PreToolUse(Read) branch (slice 055-03 — the read-once / read-lean nudge):
#   4. Tracks Read target paths per session in a state file under $TMPDIR.
#      A path Read more than once → one nudge (at most once per path),
#      recommending reuse of the in-context copy; a whole-file Read of a
#      file above JIG_READ_LEAN_BYTES → a nudge suggesting offset/limit.
#      Silent + safe on missing/malformed input and non-Read tools.
#
# On SessionStart both warnings can coexist in a single `additionalContext`
# emission; they're concatenated with a blank line between them.

# Resolve the directory this script lives in so the Python helper can
# import lib/context_fill.py regardless of whether jig is running as a
# plugin (${CODEX_HOME}/hooks/scripts/) or a scaffolded install
# (${CODEX_PROJECT_DIR}/.codex/hooks/scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os
script_dir = os.environ.get('SCRIPT_DIR', '.')
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    # Read + parse the hook input once. Garbage stdin is malformed hook input:
    # stay silent rather than defaulting into SessionStart.
    try:
        payload = json.loads(sys.stdin.read() or '{}')
        if not isinstance(payload, dict):
            sys.exit(0)
    except Exception:
        sys.exit(0)
    event = payload.get('hook_event_name', 'SessionStart')

    project_dir = os.environ.get('CODEX_PROJECT_DIR', '.')

    if event == 'PreToolUse':
        # ----- Branch 4: read-once / read-lean nudge (slice 055-03) ---
        # Fires only for the Read tool (the hooks.json matcher narrows it;
        # this also defends against a broadly-registered hook). Delegates to
        # the testable helper: load per-session seen/nudged paths, decide if
        # this Read is a duplicate or an oversized whole-file read, persist
        # the new state, and return the nudge text or None. Never blocks.
        try:
            if payload.get('tool_name') == 'Read':
                from lib.context_fill import read_nudge_event_for_turn
                tool_input = payload.get('tool_input') or {}
                if not isinstance(tool_input, dict):
                    tool_input = {}
                file_path = tool_input.get('file_path') or ''
                session_id = payload.get('session_id') or 'default'
                state_dir = os.environ.get('TMPDIR') or '/tmp'
                decision = read_nudge_event_for_turn(
                    file_path, tool_input, session_id, state_dir)
                if decision:
                    try:
                        from lib.read_attribution import (
                            append_additional_context_event,
                            append_read_nudge_event,
                        )
                        append_read_nudge_event(project_dir, session_id, decision)
                        append_additional_context_event(
                            project_dir, session_id, event,
                            'jig-context-check', 'read_nudge',
                            decision['text'])
                    except Exception:
                        pass
                    print(json.dumps({
                        'continue': True,
                        'additionalContext': decision['text'],
                    }))
        except Exception:
            # The read nudge must never block the tool call — swallow.
            pass
    elif event == 'UserPromptSubmit':
        # ----- Branch 3: in-session growth nudge (slice 055-02) -------
        # Delegate to the testable helper: tail-read the transcript, apply
        # the per-band rate-limit (with re-arm-on-drop) against a per-session
        # state file, and return the nudge text or None. Never raises.
        try:
            from lib.context_fill import growth_nudge_for_turn
            transcript_path = payload.get('transcript_path') or ''
            session_id = payload.get('session_id') or 'default'
            state_dir = os.environ.get('TMPDIR') or '/tmp'
            nudge = growth_nudge_for_turn(transcript_path, session_id, state_dir)
            if nudge:
                try:
                    from lib.read_attribution import append_additional_context_event
                    append_additional_context_event(
                        project_dir, session_id, event,
                        'jig-context-check', 'context_growth', nudge)
                except Exception:
                    pass
                print(json.dumps({'continue': True, 'additionalContext': nudge}))
        except Exception:
            # The growth nudge must never block the turn — swallow silently.
            pass
    else:
        # ----- SessionStart: the always-loaded baseline (unchanged) ---
        warnings = []

        # ----- Branch 1: MCP server count (legacy proxy) --------------
        server_count = 0
        for candidate in ['.mcp.json', '.codex/settings.json', '.codex/settings.local.json']:
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
                'Above ~8 servers, tool description overhead pushes Codex toward the '
                \"'dumb zone' (>40% context fill). Consider disabling unused servers.\"
            )

        # ----- Branch 2: byte-based context-fill estimate (slice 026-01)
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
            nudge = '\n\n'.join(warnings)
            try:
                from lib.read_attribution import append_additional_context_event
                append_additional_context_event(
                    project_dir, payload.get('session_id') or 'default', event,
                    'jig-context-check', 'context_check', nudge)
            except Exception:
                pass
            print(json.dumps({'continue': True, 'additionalContext': nudge}))
except Exception:
    pass
"
exit 0
