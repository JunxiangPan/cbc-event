"""Typed verification failures.

The viewer never turns a failure into a warning.  Callers either get a
structured report (``verify_*``) or one of these exceptions (CLI input
plumbing).  ``ViewerError`` carries the contract exit code explicitly so the
CLI cannot invent a different mapping.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ViewerError(Exception):
    """Base class for errors that terminate verification."""

    exit_code = 2
    reason = "input_error"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail)
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.reason, "detail": self.detail}


class InputError(ViewerError):
    """Missing, unreadable, or structurally invalid input (exit 2)."""

    exit_code = 2
    reason = "input_error"


class MissingBodyHashScope(InputError):
    """CBP report predates the frozen body_hash_scope field (exit 2, FAIL)."""

    reason = "MISSING_BODY_HASH_SCOPE"


class UnsupportedBodyHashScope(InputError):
    """CBP declared a body hash scope that sealed-v1 cannot verify (exit 2, FAIL)."""

    reason = "UNSUPPORTED_BODY_HASH_SCOPE"


class UnsupportedEventVersion(InputError):
    """The event log names a protocol version this viewer cannot read."""

    reason = "UNSUPPORTED_EVENT_VERSION"


class InfraError(ViewerError):
    """Provider/network failure; not a PASS and not a silent SKIP (exit 3)."""

    exit_code = 3
    reason = "infra_failure"


class NotFoundError(InputError):
    """The remote object/tag does not exist (a precondition, exit 2)."""

    reason = "not_found"


class ReadOnlyViolation(RuntimeError):
    """Raised when a caller tries a non-GET transport operation."""


@dataclass(frozen=True)
class BrokenLink:
    """The first failing link/check, in the shape written to the report."""

    kind: str
    name: str
    reason: str
    index: int | None = None
    expected: str | None = None
    actual: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kind": self.kind,
            "name": self.name,
            "reason": self.reason,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
        }
