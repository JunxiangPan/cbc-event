"""Optional, dependency-free adapter for ``cbf-evidence/v1``.

CBC never imports CBF and CBF is not required at runtime.  This module only
consumes the JSON evidence document; it supports a normalized CBC view and a
conversion to a cbc-event/v2 event.  Conversion is pure and does not append to
an event store.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .canonical import CanonicalizationError, canonical_bytes
from .protocol import V2
from .schema import validate_event
from .store import GENESIS, compute_event_hash

CBF_EVIDENCE_V1 = "cbf-evidence/v1"
CBF_VIEW_V1 = "cbc-cbf-view/v1"
HASH_RE = r"^[0-9a-f]{64}$"
RESULTS = {"PASS", "BLOCK", "ERROR"}


class CbfEvidenceError(ValueError):
    """The document is not a readable cbf-evidence/v1 evidence object."""


@dataclass(frozen=True)
class CbfEvidence:
    schema: str
    tool: str
    version: str
    policy_version: str
    policy_sha256: str
    policy_effective_sha256: str
    project: str
    repo: str
    commit: str
    ref: str
    surface: str
    result: str
    findings: tuple[dict[str, Any], ...]
    scanned: dict[str, Any]
    generated_at: str
    evidence_sha256: str
    hash_status: str
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CbfEvidence":
        if not isinstance(data, Mapping):
            raise CbfEvidenceError("CBF evidence must be a JSON object")
        document = dict(data)
        if document.get("schema") != CBF_EVIDENCE_V1:
            raise CbfEvidenceError(
                f"unsupported CBF evidence schema: {document.get('schema')!r}"
            )
        for field in (
            "tool", "version", "policy_version", "policy_sha256",
            "policy_effective_sha256", "project", "repo", "commit", "ref",
            "surface", "result", "findings", "scanned", "generated_at",
            "evidence_sha256",
        ):
            if field not in document:
                raise CbfEvidenceError(f"missing CBF evidence field: {field}")
        for field in ("policy_sha256", "policy_effective_sha256", "evidence_sha256"):
            value = document[field]
            if not isinstance(value, str) or len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value
            ):
                raise CbfEvidenceError(f"{field} must be 64 lowercase hex")
        if document["result"] not in RESULTS:
            raise CbfEvidenceError("CBF result must be PASS, BLOCK, or ERROR")
        if not isinstance(document["findings"], list) or not all(
            isinstance(item, dict) for item in document["findings"]
        ):
            raise CbfEvidenceError("CBF findings must be a list of objects")
        if not isinstance(document["scanned"], dict):
            raise CbfEvidenceError("CBF scanned must be an object")
        if not isinstance(document["generated_at"], str) or not document["generated_at"]:
            raise CbfEvidenceError("CBF generated_at must be a non-empty string")
        for field in (
            "tool", "version", "policy_version", "project", "repo", "commit",
            "ref", "surface",
        ):
            if not isinstance(document[field], str):
                raise CbfEvidenceError(f"CBF {field} must be a string")

        declared = document["evidence_sha256"]
        hash_status = _hash_status(document, declared)
        return cls(
            schema=str(document["schema"]),
            tool=str(document["tool"]),
            version=str(document["version"]),
            policy_version=str(document["policy_version"]),
            policy_sha256=str(document["policy_sha256"]),
            policy_effective_sha256=str(document["policy_effective_sha256"]),
            project=str(document["project"]),
            repo=str(document["repo"]),
            commit=str(document["commit"]),
            ref=str(document["ref"]),
            surface=str(document["surface"]),
            result=str(document["result"]),
            findings=tuple(dict(item) for item in document["findings"]),
            scanned=dict(document["scanned"]),
            generated_at=str(document["generated_at"]),
            evidence_sha256=declared,
            hash_status=hash_status,
            data=document,
        )

    @classmethod
    def load(cls, path: str | Path) -> "CbfEvidence":
        target = Path(path)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CbfEvidenceError(f"cannot read CBF evidence: {exc}") from exc
        return cls.from_dict(data)

    def view(self) -> dict[str, Any]:
        """Normalized CBC view; keeps the full evidence under ``evidence``."""
        return {
            "schema": CBF_VIEW_V1,
            "source_schema": self.schema,
            "tool": self.tool,
            "version": self.version,
            "policy_version": self.policy_version,
            "policy_sha256": self.policy_sha256,
            "policy_effective_sha256": self.policy_effective_sha256,
            "project": self.project,
            "repo": self.repo,
            "commit": self.commit,
            "ref": self.ref,
            "surface": self.surface,
            "result": self.result,
            "findings": [dict(item) for item in self.findings],
            "scanned": dict(self.scanned),
            "generated_at": self.generated_at,
            "evidence_sha256": self.evidence_sha256,
            "hash_status": self.hash_status,
            "evidence": self.data,
        }

    def to_cbc_event(
        self,
        *,
        source: Mapping[str, Any] | None = None,
        identity: Mapping[str, str] | None = None,
        chain_id: str,
        seq: int,
        prev_hash: str = GENESIS,
        event_type: str = "gate",
        action: str = "cbf.surface.evaluated",
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Return a v2 event; caller owns the append and must use a real chain."""
        if self.hash_status == "mismatch":
            raise CbfEvidenceError("CBF evidence hash mismatch; refusing conversion")
        if not isinstance(chain_id, str) or not chain_id:
            raise CbfEvidenceError("chain_id is required for a CBC event")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
            raise CbfEvidenceError("seq must be a positive integer")
        evidence_hash = _digest_without(self.data, "evidence_sha256")
        default_source = {
            "kind": "cbf",
            "name": "cbf",
            "version": self.version if _semver(self.version) else "0.1.0",
            "instance": self.project or "cbf",
        }
        event = {
            "schema": V2,
            "event_id": str(uuid.uuid4()),
            "timestamp": timestamp or _normalize_time(self.generated_at),
            "source": dict(source) if source is not None else default_source,
            "identity": dict(identity) if identity is not None else {
                "package_id": _safe_id(self.project, "cbf"),
                "producer_id": "cbf",
                "package_version": _safe_version(self.policy_version or self.version),
            },
            "event_type": event_type,
            "chain_id": chain_id,
            "level": {"PASS": "INFO", "BLOCK": "WARN", "ERROR": "CRITICAL"}[self.result],
            "action": action,
            "detail": {
                "cbf_schema": self.schema,
                "surface": self.surface,
                "result": self.result,
                "policy_sha256": self.policy_sha256,
                "policy_effective_sha256": self.policy_effective_sha256,
                "evidence_sha256": self.evidence_sha256,
                "cbf_hash_status": self.hash_status,
                "findings_count": len(self.findings),
                "scanned": dict(self.scanned),
            },
            "evidence_hash": "sha256:" + evidence_hash,
            "prev_hash": prev_hash,
            "seq": seq,
        }
        errors, _warnings = validate_event({**event, "event_hash": GENESIS})
        if errors:
            raise CbfEvidenceError("converted event is invalid: " + "; ".join(errors))
        event["event_hash"] = compute_event_hash(prev_hash, event)
        return event


def _canonical_digest(document: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(canonical_bytes(dict(document))).hexdigest()
    except CanonicalizationError as exc:
        raise CbfEvidenceError(f"CBF evidence is not canonicalizable: {exc}") from exc


def _digest_without(document: Mapping[str, Any], field: str) -> str:
    body = {key: value for key, value in document.items() if key != field}
    return _canonical_digest(body)


def _hash_status(document: Mapping[str, Any], declared: str) -> str:
    if _digest_without(document, "evidence_sha256") == declared:
        return "verified"
    # CBF 0.1.0 adds ``summary`` after sealing the evidence digest.  Recognize
    # that exact legacy shape without hiding other mismatches.
    if _digest_without({key: value for key, value in document.items() if key != "summary"},
                       "evidence_sha256") == declared:
        return "verified_without_summary"
    return "mismatch"


def _semver(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 3 and all(part.isdigit() for part in parts)


def _safe_id(value: str, fallback: str) -> str:
    candidate = value.strip().lower().replace(" ", "-")
    if candidate and candidate[0].isalpha() and all(
        char.islower() or char.isdigit() or char in "._-" for char in candidate
    ):
        return candidate
    return fallback


def _safe_version(value: str) -> str:
    return value if _semver(value) else "0.1.0"


def _normalize_time(value: str) -> str:
    text = value.strip()
    if text.endswith("Z"):
        return text
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
