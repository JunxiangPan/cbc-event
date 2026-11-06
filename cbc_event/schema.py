"""Strict event validation with forward-compatible unknown fields."""
from __future__ import annotations

import re
from typing import Any

HASH_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
LEVELS = {"INFO", "WARN", "CRITICAL"}
REQUIRED = (
    "schema", "timestamp", "source", "level", "action", "detail",
    "evidence_hash", "prev_hash", "event_hash", "seq",
)
TOP_LEVEL_KNOWN = set(REQUIRED) | {"event_id", "trace_id", "host"}


def validate_event(event: Any) -> tuple[list[str], list[str]]:
    """Return (errors, warnings); unknown fields are warnings, never fatal."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(event, dict):
        return ["event must be an object"], warnings
    for field in REQUIRED:
        if field not in event:
            errors.append(f"missing field: {field}")
    for field in sorted(set(event) - TOP_LEVEL_KNOWN):
        warnings.append(f"unknown field: {field}")
    if event.get("schema") not in (None, "cbc-event/v1"):
        errors.append("schema must be cbc-event/v1")
    if "timestamp" in event and not (isinstance(event["timestamp"], str) and TIMESTAMP_RE.fullmatch(event["timestamp"])):
        errors.append("timestamp must be RFC3339 UTC with Z")
    source = event.get("source")
    if not isinstance(source, dict):
        if "source" in event:
            errors.append("source must be an object")
    else:
        for field in ("kind", "name", "version", "instance"):
            if not isinstance(source.get(field), str) or not source.get(field):
                errors.append(f"source.{field} must be a non-empty string")
        for field in sorted(set(source) - {"kind", "name", "version", "instance"}):
            warnings.append(f"unknown source field: {field}")
    if "level" in event and event["level"] not in LEVELS:
        errors.append("level must be INFO, WARN, or CRITICAL")
    if "action" in event and (not isinstance(event["action"], str) or not event["action"]):
        errors.append("action must be a non-empty string")
    if "detail" in event and not isinstance(event["detail"], dict):
        errors.append("detail must be an object")
    for field in ("evidence_hash", "prev_hash", "event_hash"):
        if field in event and not (isinstance(event[field], str) and HASH_RE.fullmatch(event[field])):
            errors.append(f"{field} must be sha256:<64 hex>")
    if "seq" in event and (not isinstance(event["seq"], int) or isinstance(event["seq"], bool) or event["seq"] < 1):
        errors.append("seq must be a positive integer")
    return errors, warnings
