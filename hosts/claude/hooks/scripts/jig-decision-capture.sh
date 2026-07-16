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
# 083-06's reconciliation / memory-sync judgment prompt. Candidates overlapping
# an already-recorded decision are flagged for triage, never dropped (bug 011).
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
    from lib.decision_scan import scan, flag_duplicates, render_summary
    from lib.decision_scratch import (
        read_stubs, write_stubs, flag_recorded_stubs,
        stubs_to_candidates, dedup_scan_against_stubs)

    data = json.load(sys.stdin)
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
    session_id = data.get('session_id') or 'default'
    messages = data.get('messages', [])

    # Already-recorded decisions corpus, split into per-entry blocks so a large
    # file does not over-flag (a candidate is flagged only when its tokens are
    # >=60% contained in a SINGLE recorded entry). Flags in-flight stubs AND
    # scan hits; nothing is dropped against this corpus.
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
        for block in text.split('\n\n'):
            block = block.strip()
            if block:
                recorded.append(block)
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('- ') or line.startswith('### '):
                recorded.append(line)

    # 083-07: in-flight stubs. Flag the ones that look already recorded and persist
    # them all, so every stub re-surfaces on the next Stop — same durability as a
    # scan candidate (a stub is never silently dropped after a single surfacing).
    stubs = flag_recorded_stubs(read_stubs(project_dir, session_id), recorded)
    write_stubs(project_dir, session_id, stubs)
    stub_candidates = stubs_to_candidates(stubs)

    # Scan the transcript; drop scan hits already captured in-flight so a decision
    # settled both ways surfaces ONCE (no double-surface). Stubs are already
    # flagged against recorded; flag the scan hits against recorded too. Nothing
    # is suppressed for being already recorded — the owner triages (bug 011).
    scan_candidates = dedup_scan_against_stubs(scan(messages), stub_candidates)
    candidates = stub_candidates + flag_duplicates(scan_candidates, recorded)
    candidates.sort(key=lambda c: (c.turn, c.tier))

    if not candidates:
        sys.exit(0)

    msg = render_summary(candidates)
    try:
        from lib.read_attribution import append_additional_context_event
        append_additional_context_event(
            project_dir,
            session_id,
            data.get('hook_event_name') or 'Stop',
            'jig-decision-capture', 'decision_capture', msg)
    except Exception:
        pass
    print(json.dumps({'continue': True, 'additionalContext': msg}))
except Exception:
    pass
"
exit 0
