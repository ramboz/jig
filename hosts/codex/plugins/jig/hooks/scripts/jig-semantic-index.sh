#!/bin/bash
# Fires on SessionStart. Calls the host-neutral semantic-index activation
# helper and stays quiet unless there is useful Codex-facing guidance:
# a one-time public-provider opt-in suggestion or a compact fallback warning.
# Never blocks and never installs/indexes anything unless the project has
# explicitly opted in through .jig/semantic-index.json.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import json
import os
import sys
from pathlib import Path

def _load_payload():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}

def _common_dir(project_dir):
    override = os.environ.get('JIG_SEMANTIC_INDEX_COMMON_DIR')
    if override:
        return override
    script_dir = os.environ.get('SCRIPT_DIR', '.')
    script_relative = os.path.abspath(os.path.join(script_dir, '..', '..', 'skills', '_common'))
    if os.path.isdir(script_relative):
        return script_relative
    plugin_root = os.environ.get('CODEX_HOME')
    if plugin_root:
        return os.path.join(plugin_root, 'skills', '_common')
    return script_relative

def _seen_path(project_dir):
    return Path(project_dir) / '.jig' / 'semantic-index-codex-hook.json'

def _already_suggested(project_dir, key):
    path = _seen_path(project_dir)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        data = {}
    suggestions = data.get('suggestions') if isinstance(data, dict) else None
    return isinstance(suggestions, list) and key in suggestions

def _mark_suggested(project_dir, key):
    path = _seen_path(project_dir)
    try:
        data = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
        if not isinstance(data, dict):
            data = {}
        suggestions = data.get('suggestions')
        if not isinstance(suggestions, list):
            suggestions = []
        if key not in suggestions:
            suggestions.append(key)
        data['suggestions'] = suggestions
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, sort_keys=True) + '\\n', encoding='utf-8')
    except Exception:
        pass

def _message_for(result, project_dir):
    action = getattr(result, 'action', '')
    outcome = getattr(result, 'outcome', '')
    provider = getattr(result, 'provider', None) or 'semantic-index provider'
    profile = getattr(result, 'provider_profile', '')
    if action == 'recommend':
        if profile == 'internal-overlay':
            return None
        key = f'{provider}:{action}:{outcome}'
        if _already_suggested(project_dir, key):
            return None
        _mark_suggested(project_dir, key)
        return getattr(result, 'recommendation', None)
    if action == 'fallback':
        return (
            f'Semantic index activation for {provider} did not become ready '
            f'({outcome}). Continue with targeted search/read fallback for now.'
        )
    return None

try:
    payload = _load_payload()
    event = payload.get('hook_event_name')
    if event != 'SessionStart':
        raise SystemExit(0)
    project_dir = os.environ.get('CODEX_PROJECT_DIR') or payload.get('cwd') or os.getcwd()
    common_dir = _common_dir(project_dir)
    if common_dir not in sys.path:
        sys.path.insert(0, common_dir)
    import semantic_index

    result = semantic_index.activate(Path(project_dir), host='codex')
    msg = _message_for(result, project_dir)
    if msg:
        try:
            if os.environ.get('SCRIPT_DIR', '.') not in sys.path:
                sys.path.insert(0, os.environ.get('SCRIPT_DIR', '.'))
            from lib.read_attribution import append_additional_context_event
            append_additional_context_event(
                project_dir,
                payload.get('session_id') or 'default',
                event,
                'jig-semantic-index',
                'semantic_index',
                msg,
            )
        except Exception:
            pass
        print(json.dumps({'continue': True, 'additionalContext': msg}))
except SystemExit:
    pass
except Exception:
    pass
"
exit 0
