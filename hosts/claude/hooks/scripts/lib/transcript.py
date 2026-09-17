"""Bounded, host-neutral transcript input for advisory hooks.

Only JSONL records with an explicit role and content are admitted.  Unknown
records are ignored rather than guessed at, and a transcript is accepted only
when it is a regular file inside the supplied project directory.
"""

from __future__ import annotations

import json
import os

MAX_BYTES = 2 * 1024 * 1024
MAX_LINES = 4000


def _content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for block in value:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return parts
    return value


def _message(record):
    candidate = record.get("message") if isinstance(record, dict) else None
    if not isinstance(candidate, dict):
        candidate = record
    role = candidate.get("role")
    content = _content(candidate.get("content"))
    if role not in ("user", "assistant") or not isinstance(content, (str, list)):
        return None
    return {"role": role, "content": content}


def read_transcript(path, project_dir, *, require_within=True):
    """Read supported JSONL conversation records, or return ``None``.

    ``require_within`` is the safety default for host-provided Stop paths.
    Existing Claude/Codex context-fill callers can opt out because their
    established transcript contract permits host-managed paths.
    """
    if not isinstance(path, str) or not path:
        return None
    try:
        candidate = os.path.realpath(path)
        if not os.path.isfile(candidate):
            return None
        if os.path.getsize(candidate) > MAX_BYTES:
            return None
        if require_within:
            root = os.path.realpath(project_dir or ".")
            if os.path.commonpath((candidate, root)) != root:
                return None
        messages = []
        with open(candidate, encoding="utf-8", errors="replace") as stream:
            for number, line in enumerate(stream):
                if number >= MAX_LINES:
                    break
                try:
                    record = json.loads(line)
                except (TypeError, ValueError):
                    continue
                message = _message(record)
                if message is not None:
                    messages.append(message)
        return messages
    except (OSError, ValueError):
        return None


def messages_from_payload(payload, project_dir):
    """Prefer inline messages; otherwise use a bounded transcript path."""
    if not isinstance(payload, dict):
        return []
    messages = payload.get("messages")
    if isinstance(messages, list):
        return messages
    return read_transcript(payload.get("transcript_path"), project_dir) or []
