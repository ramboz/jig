#!/bin/bash
# Fires on Stop. Scans the completed session for *decision* signals (the sibling
# of jig-task-capture.sh, which scans for task signals). Surfaces candidate
# decisions as additionalContext at the START OF THE NEXT TURN for owner-gated
# triage — it never writes a decision itself.
#
# The scan is honest about its reach (slice 083-04 / frame-critique): it catches
# AskUserQuestion answers (Tier 1) and explicit user corrections (Tier 2)
# reliably, and agent settled-choice phrasing (Tier 3) best-effort. It does NOT
# try to catch trigger-phrase-free load-bearing decisions — those are owned by
# 083-06's reconciliation / memory-sync judgment prompt. Candidates are deduped
# against already-recorded decisions so repeat runs stay quiet.
#
# SCRIPT_DIR locates lib/decision_scan.py + lib/read_attribution.py whether jig
# runs as a plugin (${CLAUDE_PLUGIN_ROOT}/hooks/scripts/) or a scaffolded install
# (${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/). Fully fail-open: any error
# leaves the session untouched.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os

script_dir = os.environ.get('SCRIPT_DIR', '.')
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from lib.decision_scan import scan, dedup, render_summary

    data = json.load(sys.stdin)
    messages = data.get('messages', [])
    candidates = scan(messages)
    if not candidates:
        sys.exit(0)

    # Dedup against already-recorded decisions, split into per-entry blocks so a
    # large file does not over-suppress (a candidate is only dropped when its
    # tokens are >=60% contained in a SINGLE recorded entry).
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
    recorded = []
    for rel in ('docs/decisions/lightweight-decisions.md',
                'docs/decisions/README.md',
                'docs/refinement-todo.md'):
        full = os.path.join(project_dir, rel)
        if not os.path.exists(full):
            continue
        try:
            with open(full) as f:
                text = f.read()
        except Exception:
            continue
        # Split into paragraph blocks AND standalone list lines (ADR index).
        for block in text.split('\n\n'):
            block = block.strip()
            if block:
                recorded.append(block)
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('- ') or line.startswith('### '):
                recorded.append(line)

    candidates = dedup(candidates, recorded)
    if not candidates:
        sys.exit(0)

    msg = render_summary(candidates)
    try:
        from lib.read_attribution import append_additional_context_event
        append_additional_context_event(
            project_dir,
            data.get('session_id') or 'default',
            data.get('hook_event_name') or 'Stop',
            'jig-decision-capture', 'decision_capture', msg)
    except Exception:
        pass
    print(json.dumps({'continue': True, 'additionalContext': msg}))
except Exception:
    pass
"
exit 0
