#!/bin/bash
# Logs Task tool spawns to .codex/skill-usage.jsonl for workflow telemetry.
# Fires async on PreToolUse/Task — never blocks.
#
# Optional phase/spec/slice attribution comes from explicit tool_input fields
# (`phase`/`jig_phase`, `spec`/`jig_spec`, `slice`/`jig_slice`) or compact
# prompt tags:
#   [jig:phase=compliance] [jig:spec=056] [jig:slice=056-03]
python3 -c "$(cat <<'PY'
import json
import os
import re
import sys
from datetime import datetime, timezone


TAG_PATTERNS = {
    'phase': (
        re.compile(r'\[jig:phase=([A-Za-z0-9_.:-]+)\]'),
        re.compile(r'(?im)^\s*jig[_-]phase\s*[:=]\s*([A-Za-z0-9_.:-]+)\s*$'),
    ),
    'spec': (
        re.compile(r'\[jig:spec=(\d{1,3})\]'),
        re.compile(r'(?im)^\s*jig[_-]spec\s*[:=]\s*(\d{1,3})\s*$'),
    ),
    'slice': (
        re.compile(r'\[jig:slice=(\d{1,3}-\d{1,3})\]'),
        re.compile(r'(?im)^\s*jig[_-]slice\s*[:=]\s*(\d{1,3}-\d{1,3})\s*$'),
    ),
}


def _clean_text(value):
    if value is None:
        return ''
    text = str(value).strip()
    if not text:
        return ''
    return text[:80]


def _normalize_spec(value):
    text = _clean_text(value)
    if not re.fullmatch(r'\d{1,3}', text):
        return text
    return f'{int(text):03d}'


def _normalize_slice(value):
    text = _clean_text(value)
    match = re.fullmatch(r'(\d{1,3})-(\d{1,3})', text)
    if not match:
        return text
    return f'{int(match.group(1)):03d}-{int(match.group(2)):02d}'


def _prompt_tag(prompt, key):
    for pattern in TAG_PATTERNS[key]:
        match = pattern.search(prompt)
        if match:
            return match.group(1)
    return ''


def _extract_tags(tool_input, prompt):
    tags = {}
    phase = (_clean_text(tool_input.get('jig_phase'))
             or _clean_text(tool_input.get('phase'))
             or _clean_text(_prompt_tag(prompt, 'phase')))
    spec = (_clean_text(tool_input.get('jig_spec'))
            or _clean_text(tool_input.get('spec'))
            or _clean_text(_prompt_tag(prompt, 'spec')))
    slice_id = (_clean_text(tool_input.get('jig_slice'))
                or _clean_text(tool_input.get('slice'))
                or _clean_text(_prompt_tag(prompt, 'slice')))
    if phase:
        tags['phase'] = phase
    if spec:
        tags['spec'] = _normalize_spec(spec)
    if slice_id:
        tags['slice'] = _normalize_slice(slice_id)
    return tags


try:
    data = json.load(sys.stdin)
    log_dir = os.path.join(os.environ.get('CODEX_PROJECT_DIR', '.'), '.codex')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'skill-usage.jsonl')

    tool_input = data.get('tool_input', {}) or {}
    prompt = tool_input.get('prompt', tool_input.get('description', ''))
    if not isinstance(prompt, str):
        prompt = str(prompt)
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'session_id': data.get('session_id', ''),
        'event': 'task_spawned',
        'tool_name': data.get('tool_name', 'Task'),
        'prompt_snippet': prompt[:100],
    }
    entry.update(_extract_tags(tool_input, prompt))
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')
except Exception:
    pass
PY
)"
exit 0
