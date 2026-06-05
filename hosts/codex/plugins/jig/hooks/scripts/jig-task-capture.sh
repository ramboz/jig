#!/bin/bash
# Fires on Stop. Scans the completed session exchange for task-capture language
# patterns ("we should also", "don't forget", "TODO:", etc.). If found, surfaces
# them as additionalContext at the START OF THE NEXT TURN for triage.
python3 -c "
import sys, json, re

PATTERNS = [
    r'we should also\b',
    r'don.?t forget\b',
    r'\bTODO\s*:',
    r'later we.?ll?\s+need\b',
    r'remind me to\b',
    r'follow[- ]?up[:\s]',
]

try:
    data = json.load(sys.stdin)
    messages = data.get('messages', [])
    parts = []
    for m in messages:
        content = m.get('content', '')
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict):
                    parts.append(c.get('text', ''))
    text = ' '.join(parts)

    found = []
    for pattern in PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend(matches)

    if found:
        examples = '; '.join(dict.fromkeys(found[:3]))
        msg = (
            f'Task-capture patterns detected ({examples}). '
            'Please triage any unresolved items: '
            '(a) add to an existing spec, '
            '(b) create a new spec via spec-workflow, or '
            '(c) park in docs/inbox.md.'
        )
        print(json.dumps({'continue': True, 'additionalContext': msg}))
except Exception:
    pass
"
exit 0
