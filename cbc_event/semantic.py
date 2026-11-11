"""Optional, dependency-free reader for ``semantic-verdict/v1``.

CBC never imports CBF/CBP/CBE/CBM and never runs a semantic model.  This module
only parses and displays an external semantic verdict.  A verdict is a
**semantic signal**, not a factual proof and not a gate result.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .canonical import CanonicalizationError, canonical_bytes

SEMANTIC_VERDICT_V1 = "semantic-verdict/v1"
SEMANTIC_VIEW_V1 = "cbc-semantic-view/v1"
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
VERDICTS = {"PASS", "FAIL", "NOT_RUN"}
DISCLAIMER = "semantic signal only; this is not factual proof and not a gate PASS"


class SemanticVerdictError(ValueError):
    """The document is not a readable semantic-verdict/v1 object."""


@dataclass(frozen=True)
class SemanticVerdict:
    schema: str
    verdict: str
    confidence: float | None
    subject: dict[str, Any]
    generated_at: str
    findings: tuple[dict[str, Any], ...]
    policy: dict[str, Any]
    evidence_sha256: str
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticVerdict":
        if not isinstance(data, Mapping):
            raise SemanticVerdictError("semantic verdict must be a JSON object")
        document = dict(data)
        if document.get("schema") != SEMANTIC_VERDICT_V1:
            raise SemanticVerdictError(
                f"unsupported semantic verdict schema: {document.get('schema')!r}"
            )
        for field in ("verdict", "subject", "generated_at", "evidence_sha256"):
            if field not in document:
                raise SemanticVerdictError(f"missing semantic verdict field: {field}")
        verdict = document["verdict"]
        if verdict not in VERDICTS:
            raise SemanticVerdictError("verdict must be PASS, FAIL, or NOT_RUN")
        subject = document["subject"]
        if not isinstance(subject, dict):
            raise SemanticVerdictError("subject must be an object")
        if not isinstance(subject.get("package_id"), str) or not subject["package_id"]:
            raise SemanticVerdictError("subject.package_id is required")
        artifact = subject.get("artifact_sha256")
        if not isinstance(artifact, str) or not HEX64.fullmatch(artifact):
            raise SemanticVerdictError("subject.artifact_sha256 must be 64 hex")
        if not isinstance(document["generated_at"], str) or not document["generated_at"]:
            raise SemanticVerdictError("generated_at must be a non-empty string")
        declared = document["evidence_sha256"]
        if not isinstance(declared, str) or not HEX64.fullmatch(declared):
            raise SemanticVerdictError("evidence_sha256 must be 64 hex")
        if declared.lower() != canonical_semantic_sha256(document):
            raise SemanticVerdictError("evidence_sha256 does not match canonical JSON")
        findings = document.get("findings", [])
        if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
            raise SemanticVerdictError("findings must be an array of objects")
        policy = document.get("policy", {})
        if not isinstance(policy, dict):
            raise SemanticVerdictError("policy must be an object")
        confidence = document.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise SemanticVerdictError("confidence must be a number between 0 and 1")
            if not 0.0 <= float(confidence) <= 1.0:
                raise SemanticVerdictError("confidence must be between 0 and 1")
        return cls(
            schema=str(document["schema"]),
            verdict=str(verdict),
            confidence=None if confidence is None else float(confidence),
            subject=dict(subject),
            generated_at=str(document["generated_at"]),
            findings=tuple(dict(item) for item in findings),
            policy=dict(policy),
            evidence_sha256=str(declared),
            data=document,
        )

    @classmethod
    def load(cls, path: str | Path) -> "SemanticVerdict":
        target = Path(path)
        try:
            data = json.loads(target.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise SemanticVerdictError(f"cannot read semantic verdict: {exc}") from exc
        return cls.from_dict(data)

    def view(self) -> dict[str, Any]:
        return {
            "schema": SEMANTIC_VIEW_V1,
            "source_schema": self.schema,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "subject": dict(self.subject),
            "generated_at": self.generated_at,
            "findings": [dict(item) for item in self.findings],
            "policy": dict(self.policy),
            "evidence_sha256": self.evidence_sha256,
            "disclaimer": DISCLAIMER,
            "evidence": self.data,
        }


def canonical_semantic_sha256(data: Mapping[str, Any]) -> str:
    body = {key: value for key, value in data.items() if key != "evidence_sha256"}
    try:
        return hashlib.sha256(canonical_bytes(body)).hexdigest()
    except CanonicalizationError as exc:
        raise SemanticVerdictError(f"semantic verdict is not canonicalizable: {exc}") from exc


def load_semantic_verdict(path: str | Path) -> SemanticVerdict:
    return SemanticVerdict.load(path)
