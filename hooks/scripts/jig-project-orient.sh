#!/bin/bash
# SessionStart project-orientation hint (slice 088-01).
# Emits one compact `jig hint:` additionalContext headline from durable jig
# artifacts before the agent infers state from the shallow source tree. Soft
# hook only: malformed input, non-SessionStart events, opt-out, and workflow
# failures are all silent success.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

FALSEY = {'0', 'false', 'off', 'no'}


def disabled() -> bool:
    value = os.environ.get('JIG_PROJECT_ORIENT')
    return isinstance(value, str) and value.strip().lower() in FALSEY


def workflow_candidates(project_dir: Path, script_dir: Path) -> list[Path]:
    roots = []
    for name in ('CLAUDE_PLUGIN_ROOT', 'PLUGIN_ROOT'):
        value = os.environ.get(name)
        if value:
            roots.append(Path(value))

    candidates = [
        root / 'skills' / 'spec-workflow' / 'workflow.py'
        for root in roots
    ]
    candidates.extend([
        project_dir / '.claude' / 'skills' / 'jig-spec-workflow' / 'workflow.py',
        script_dir.parents[1] / 'skills' / 'spec-workflow' / 'workflow.py',
    ])
    return candidates


try:
    if disabled():
        sys.exit(0)
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except Exception:
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)
    event = payload.get('hook_event_name')
    if event != 'SessionStart':
        sys.exit(0)

    project_dir = Path(
        os.environ.get('CLAUDE_PROJECT_DIR')
        or os.getcwd()
    )
    script_dir = Path(os.environ.get('SCRIPT_DIR', '.'))
    workflow = next(
        (candidate for candidate in workflow_candidates(project_dir, script_dir)
         if candidate.is_file()),
        None,
    )
    if workflow is None:
        sys.exit(0)

    result = subprocess.run(
        [
            sys.executable,
            '-B',
            str(workflow),
            'orient',
            '--project-dir',
            str(project_dir),
        ],
        capture_output=True,
        text=True,
        timeout=4,
    )
    if result.returncode != 0:
        sys.exit(0)
    headline = result.stdout.rstrip('\n')
    if not headline:
        sys.exit(0)

    try:
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from lib.read_attribution import append_additional_context_event
        append_additional_context_event(
            project_dir,
            payload.get('session_id') or 'default',
            event,
            'jig-project-orient',
            'project_orientation',
            headline,
        )
    except Exception:
        pass

    print(json.dumps({'continue': True, 'additionalContext': headline}))
except Exception:
    pass
"
exit 0
