"""CBC read-only evidence viewer.

The protocol package (``cbc_event``) supports v1 and opt-in v2.  This package adds
release/event-log chain verification, body rendering, and a GET-only GitHub
transport; it has no write-side release operations.
"""
from __future__ import annotations

from .body import BEGIN, END, BodyProblem, parse_anchor, render_appendix, render_not_uploaded_entry, split_body
from .chain import GENESIS, build_manifest, compute_link_hash, read_manifest, sha256_bytes, sha256_file, verify_links
from .errors import (
    BrokenLink,
    InfraError,
    InputError,
    MissingBodyHashScope,
    NotFoundError,
    ReadOnlyViolation,
    UnsupportedBodyHashScope,
    UnsupportedEventVersion,
)
from .event_chain import build_event_manifest, verify_event_log
from .reports import load_gate_reports, validate_cbe, validate_cbp
from .verify import VerificationResult, verify_event_log_report, verify_release

__all__ = [
    "BEGIN",
    "END",
    "BrokenLink",
    "BodyProblem",
    "GENESIS",
    "InfraError",
    "InputError",
    "MissingBodyHashScope",
    "NotFoundError",
    "ReadOnlyViolation",
    "UnsupportedBodyHashScope",
    "UnsupportedEventVersion",
    "VerificationResult",
    "build_event_manifest",
    "build_manifest",
    "compute_link_hash",
    "load_gate_reports",
    "parse_anchor",
    "read_manifest",
    "render_appendix",
    "render_not_uploaded_entry",
    "sha256_bytes",
    "sha256_file",
    "split_body",
    "validate_cbe",
    "validate_cbp",
    "verify_event_log",
    "verify_event_log_report",
    "verify_links",
    "verify_release",
]

__version__ = "0.2.0rc3"
