"""Strict event validation with protocol version negotiation.

v1 is the frozen 0.1.x schema.  v2 is opt-in and adds a strict package
identity, an event type, and a chain id.  Unknown fields remain warnings in
both versions; an unknown *schema* is an error and never falls back to v1.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from .protocol import V1, V2, UnsupportedEventVersion, negotiate

HASH_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
HASH_RE_V2 = re.compile(r"^sha256:[0-9a-f]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
IDENTITY_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
CHAIN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
LEVELS = {"INFO", "WARN", "CRITICAL"}
EVENT_TYPES = {"observation", "decision", "gate", "release", "error"}

REQUIRED_V1 = (
    "schema", "timestamp", "source", "level", "action", "detail",
    "evidence_hash", "prev_hash", "event_hash", "seq",
)
REQUIRED_V2 = REQUIRED_V1 + ("event_id", "identity", "event_type", "chain_id")
TOP_LEVEL_KNOWN_V1 = set(REQUIRED_V1) | {"event_id", "trace_id", "host"}
TOP_LEVEL_KNOWN_V2 = set(REQUIRED_V2) | {"trace_id", "host"}
IDENTITY_KEYS = {"package_id", "producer_id", "package_version"}


def _hash_valid(value: Any, version: str) -> bool:
    if not isinstance(value, str):
        return False
    return bool((HASH_RE_V2 if version == V2 else HASH_RE).fullmatch(value))


def validate_event(event: Any) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)`` for a v1 or v2 event.

    Unknown fields are warnings, never fatal, in both versions.  Unknown
    schemas are errors (fail-closed).
    """
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(event, dict):
        return ["event must be an object"], warnings

    schema = event.get("schema")
    version = V1
    if "schema" not in event:
        errors.append("missing field: schema")
    else:
        try:
            version = negotiate(schema).schema
        except UnsupportedEventVersion as exc:
            # Fail closed at the version gate, but keep collecting field
            # diagnostics for callers that want a complete validation report.
            errors.append(str(exc))
            version = V1

    required = REQUIRED_V2 if version == V2 else REQUIRED_V1
    known = TOP_LEVEL_KNOWN_V2 if version == V2 else TOP_LEVEL_KNOWN_V1
    for field in required:
        if field not in event:
            errors.append(f"missing field: {field}")
    for field in sorted(set(event) - known):
        warnings.append(f"unknown field: {field}")

    if version == V2:
        event_id = event.get("event_id")
        if not isinstance(event_id, str):
            errors.append("event_id must be a UUID string in cbc-event/v2")
        else:
            try:
                uuid.UUID(event_id)
            except (ValueError, AttributeError):
                errors.append("event_id must be a UUID string in cbc-event/v2")
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
        if version == V2 and isinstance(source.get("version"), str) and source.get("version"):
            if not VERSION_RE.fullmatch(source["version"]):
                errors.append("source.version must be X.Y.Z in cbc-event/v2")
        for field in sorted(set(source) - {"kind", "name", "version", "instance"}):
            warnings.append(f"unknown source field: {field}")

    if version == V2:
        identity = event.get("identity")
        if not isinstance(identity, dict):
            if "identity" in event:
                errors.append("identity must be an object in cbc-event/v2")
        else:
            for field in sorted(IDENTITY_KEYS):
                if field not in identity:
                    errors.append(f"missing identity field: {field}")
            for field in sorted(set(identity) - IDENTITY_KEYS):
                warnings.append(f"unknown identity field: {field}")
            for field in ("package_id", "producer_id"):
                value = identity.get(field)
                if isinstance(value, str) and value:
                    if not IDENTITY_RE.fullmatch(value):
                        errors.append(f"identity.{field} must be a lowercase package id")
                elif field in identity:
                    errors.append(f"identity.{field} must be a non-empty string")
            package_version = identity.get("package_version")
            if isinstance(package_version, str) and package_version:
                if not VERSION_RE.fullmatch(package_version):
                    errors.append("identity.package_version must be X.Y.Z")
            elif "package_version" in identity:
                errors.append("identity.package_version must be a non-empty string")

        event_type = event.get("event_type")
        if "event_type" in event and (not isinstance(event_type, str) or event_type not in EVENT_TYPES):
            errors.append("event_type must be one of: " + ", ".join(sorted(EVENT_TYPES)))
        chain_id = event.get("chain_id")
        if isinstance(chain_id, str) and chain_id:
            if not CHAIN_ID_RE.fullmatch(chain_id):
                errors.append("chain_id contains invalid characters")
        elif "chain_id" in event:
            errors.append("chain_id must be a non-empty string")

    if "level" in event and event["level"] not in LEVELS:
        errors.append("level must be INFO, WARN, or CRITICAL")
    if "action" in event and (not isinstance(event["action"], str) or not event["action"]):
        errors.append("action must be a non-empty string")
    if "detail" in event and not isinstance(event["detail"], dict):
        errors.append("detail must be an object")
    for field in ("evidence_hash", "prev_hash", "event_hash"):
        if field in event and not _hash_valid(event[field], version):
            suffix = "bare lowercase sha256:<64 hex>" if version == V2 else "sha256:<64 hex>"
            errors.append(f"{field} must be {suffix}")
    if "seq" in event and (not isinstance(event["seq"], int) or isinstance(event["seq"], bool) or event["seq"] < 1):
        errors.append("seq must be a positive integer")
    return errors, warnings
