"""Zero-dependency cbc-event protocol client."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .canonical import CanonicalizationError, canonical_bytes, canonical_json
from .protocol import CURRENT_SCHEMA, SUPPORTED_SCHEMAS, UnsupportedEventVersion, V1, V2, negotiate
from .store import EventStore, GENESIS, compute_event_hash, read_events, validate_event

__version__ = "0.2.0rc1"

__all__ = [
    "Client",
    "EventStore",
    "GENESIS",
    "CURRENT_SCHEMA",
    "SUPPORTED_SCHEMAS",
    "UnsupportedEventVersion",
    "V1",
    "V2",
    "CanonicalizationError",
    "negotiate",
    "canonical_bytes",
    "canonical_json",
    "compute_event_hash",
    "emit",
    "read_events",
    "validate_event",
]


class Client:
    """Explicit, disabled-by-default event client."""

    def __init__(
        self,
        event_dir: str | Path | None = None,
        enabled: bool | None = None,
        source: dict[str, str] | None = None,
        *,
        protocol_version: str = "v1",
        identity: dict[str, str] | None = None,
        chain_id: str | None = None,
    ) -> None:
        if enabled is None:
            enabled = os.environ.get("CBC_REPORT_ENABLED", "false").lower() in {"1", "true", "yes"}
        directory = Path(event_dir or os.environ.get("CBC_EVENT_DIR") or str(Path.home() / ".cb" / "events")).expanduser()
        default_source = {
            "kind": "unknown",
            "name": "unknown",
            "version": "0.1.0",
            "instance": os.environ.get("HOSTNAME", "local"),
        }
        self.store = EventStore(
            directory,
            source or default_source,
            enabled=bool(enabled),
            protocol_version=protocol_version,
            identity=identity,
            chain_id=chain_id,
        )

    @property
    def enabled(self) -> bool:
        return self.store.enabled

    def emit(
        self,
        level: str,
        action: str,
        detail: dict[str, Any],
        *,
        evidence: bytes | None = None,
        evidence_hash: str | None = None,
        event_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Append one event, or return None when reporting is disabled."""
        return self.store.emit(
            level,
            action,
            detail,
            evidence=evidence,
            evidence_hash=evidence_hash,
            event_type=event_type,
        )


def emit(
    level: str,
    action: str,
    detail: dict[str, Any],
    *,
    source: dict[str, str] | None = None,
    event_dir: str | Path | None = None,
    enabled: bool | None = None,
    evidence: bytes | None = None,
    evidence_hash: str | None = None,
    protocol_version: str = "v1",
    identity: dict[str, str] | None = None,
    chain_id: str | None = None,
    event_type: str | None = None,
) -> dict[str, Any] | None:
    """Convenience wrapper; disabled unless explicitly enabled."""
    return Client(
        event_dir=event_dir,
        enabled=enabled,
        source=source,
        protocol_version=protocol_version,
        identity=identity,
        chain_id=chain_id,
    ).emit(
        level,
        action,
        detail,
        evidence=evidence,
        evidence_hash=evidence_hash,
        event_type=event_type,
    )
