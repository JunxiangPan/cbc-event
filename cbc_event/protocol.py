"""Protocol version negotiation for the append-only cbc-event format.

v1 (``cbc-event/v1``) is the frozen 0.1.x wire format.  v2
(``cbc-event/v2``) is opt-in and adds an explicit package identity, an event
type, and a chain id.  Readers negotiate the schema before parsing fields;
unknown versions fail closed and are never treated as v1 or "unknown fields".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

V1 = "cbc-event/v1"
V2 = "cbc-event/v2"
SUPPORTED_SCHEMAS = (V1, V2)
CURRENT_SCHEMA = V2


class UnsupportedEventVersion(ValueError):
    """The event names a schema this package cannot read."""

    def __init__(self, schema: Any) -> None:
        self.schema = schema
        super().__init__(f"unsupported event schema: {schema!r}")


@dataclass(frozen=True)
class ProtocolVersion:
    schema: str
    major: int
    legacy: bool

    @property
    def label(self) -> str:
        return f"event-log/v{self.major}"


V1_INFO = ProtocolVersion(V1, 1, True)
V2_INFO = ProtocolVersion(V2, 2, False)


def negotiate(schema: Any) -> ProtocolVersion:
    """Return the negotiated protocol version or raise fail-closed."""
    if schema == V1:
        return V1_INFO
    if schema == V2:
        return V2_INFO
    raise UnsupportedEventVersion(schema)


def normalize_emit_version(value: str | None) -> str:
    """Resolve an EventStore/Client emit version (default v1).

    Accepts ``v1``/``v2`` and the full schema strings.  The default is v1 so
    upgrading to the 0.2.x client does not silently change producers.
    """
    if value is None:
        return V1
    if value in (V1, "v1", "1", "V1"):
        return V1
    if value in (V2, "v2", "2", "V2"):
        return V2
    raise UnsupportedEventVersion(value)
