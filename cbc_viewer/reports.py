"""Parse and validate the CBE report and CBP quality manifest.

CBC consumes the contract reports as files.  It deliberately does **not**
compare ``package_id`` to ``cbc``: until CBE/CBP define whether that field is
the producer or the target package, version + tag are the identity binding.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .chain import (
    TAG_RE,
    VERSION_RE,
    normalize_hash,
    normalize_tag,
    normalize_version,
)
from .errors import InputError

GATE_STATUSES = {"PASS", "FAIL", "SKIPPED_INFRA", "PRECONDITION_FAIL"}
CBE_REQUIRED = (
    "schema_version",
    "package_id",
    "version",
    "tag",
    "gate_status",
    "exit_code",
    "applicable_count",
    "skip_count",
    "skip_ratio",
    "blocking_skip",
    "warn_count",
    "rules_manifest_hash",
    "sarif_paths",
    "evidence_sha256",
)
CBP_REQUIRED = (
    "schema_version",
    "package_id",
    "version",
    "gate_status",
    "applicable_gate_count",
    "skip_count",
    "skip_ratio",
    "blocking_skip",
    "gates",
    "artifact_hashes",
    "artifact_repository",
    "release_body_hash",
    "evidence_sha256",
)


@dataclass(frozen=True)
class GateReports:
    cbe: dict[str, Any]
    cbp: dict[str, Any]
    version: str
    tag: str
    body_hash_scope: str | None

    @property
    def cbe_package_id(self) -> str:
        return str(self.cbe.get("package_id", ""))

    @property
    def cbp_package_id(self) -> str:
        return str(self.cbp.get("package_id", ""))

    @property
    def skip_ratio(self) -> float:
        return max(float(self.cbe["skip_ratio"]), float(self.cbp["skip_ratio"]))

    @property
    def blocking_skip(self) -> bool:
        return bool(self.cbe["blocking_skip"] or self.cbp["blocking_skip"])

    @property
    def infra(self) -> bool:
        return self.cbe["gate_status"] == "SKIPPED_INFRA" or self.cbp["gate_status"] == "SKIPPED_INFRA"

    @property
    def skip_over(self) -> bool:
        return self.skip_ratio > 0.20

    @property
    def gate_fail(self) -> bool:
        return self.cbe["gate_status"] != "PASS" or self.cbp["gate_status"] != "PASS"

    def reason(self) -> str | None:
        if self.infra:
            return "upstream_skipped_infra"
        if self.skip_over:
            return "skip_threshold_exceeded"
        if self.blocking_skip:
            return "blocking_skip"
        if self.gate_fail:
            failed = []
            if self.cbe["gate_status"] != "PASS":
                failed.append(f"cbe={self.cbe['gate_status']}")
            if self.cbp["gate_status"] != "PASS":
                failed.append(f"cbp={self.cbp['gate_status']}")
            return "upstream_gate_failed:" + ",".join(failed)
        return None


def _read_json(path: Path | str, label: str) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise InputError(f"{label} not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"{label} must be a JSON object")
    return data


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise InputError(detail)


def _int(value: Any, label: str, *, minimum: int = 0) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
             f"{label} must be an integer >= {minimum}")
    return value


def _ratio(value: Any, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool),
             f"{label} must be a number")
    number = float(value)
    _require(0.0 <= number <= 1.0, f"{label} must be between 0 and 1")
    return number


def _hash(value: Any, label: str) -> str:
    try:
        return normalize_hash(value)
    except InputError as exc:
        raise InputError(f"{label}: {exc}") from exc


def _check_ratio(count: int, applicable: int, reported: float, label: str) -> None:
    _require(applicable > 0, f"{label}.applicable_count must be > 0")
    computed = count / applicable
    _require(abs(computed - reported) <= 1e-9,
             f"{label}.skip_ratio {reported} != {count}/{applicable}")


def _check_status_consistency(
    label: str,
    status: str,
    exit_code: int,
    skip_ratio: float,
    blocking_skip: bool,
) -> None:
    _require(status in GATE_STATUSES, f"{label}.gate_status is invalid")
    _require(exit_code in {0, 2, 3, 4}, f"{label}.exit_code is invalid")
    if status == "PASS":
        _require(exit_code == 0, f"{label}: PASS requires exit_code 0")
        _require(skip_ratio <= 0.20, f"{label}: PASS with skip_ratio > 0.20 is invalid")
        _require(not blocking_skip, f"{label}: PASS with blocking_skip is invalid")
    elif status == "SKIPPED_INFRA":
        _require(exit_code == 3, f"{label}: SKIPPED_INFRA requires exit_code 3")
    elif status == "FAIL":
        _require(exit_code != 0, f"{label}: FAIL requires a non-zero exit_code")
        if exit_code == 4:
            _require(skip_ratio > 0.20, f"{label}: exit 4 requires skip_ratio > 0.20")
            _require(not blocking_skip, f"{label}: exit 4 cannot be a blocking skip")
        if exit_code == 3:
            _require(skip_ratio <= 0.20, f"{label}: skip_ratio > 0.20 must exit 4")
    elif status == "PRECONDITION_FAIL":
        _require(exit_code in {2, 3}, f"{label}: PRECONDITION_FAIL requires exit 2 or 3")


def validate_cbe(data: Mapping[str, Any]) -> dict[str, Any]:
    cbe = dict(data)
    for field in CBE_REQUIRED:
        _require(field in cbe, f"CBE report missing field: {field}")
    _require(cbe["schema_version"] == "1", "CBE schema_version must be 1")
    _require(isinstance(cbe["package_id"], str) and cbe["package_id"], "CBE package_id must be non-empty")
    _require(isinstance(cbe["version"], str) and VERSION_RE.fullmatch(cbe["version"]),
             "CBE version is invalid")
    _require(isinstance(cbe["tag"], str) and TAG_RE.fullmatch(cbe["tag"]),
             "CBE tag is invalid")
    _require(isinstance(cbe["gate_status"], str), "CBE gate_status must be a string")
    exit_code = _int(cbe["exit_code"], "CBE exit_code", minimum=0)
    applicable = _int(cbe["applicable_count"], "CBE applicable_count", minimum=0)
    skip_count = _int(cbe["skip_count"], "CBE skip_count", minimum=0)
    ratio = _ratio(cbe["skip_ratio"], "CBE skip_ratio")
    _check_ratio(skip_count, applicable, ratio, "CBE")
    _require(isinstance(cbe["blocking_skip"], bool), "CBE blocking_skip must be boolean")
    _int(cbe["warn_count"], "CBE warn_count", minimum=0)
    _hash(cbe["rules_manifest_hash"], "CBE rules_manifest_hash")
    _require(isinstance(cbe["sarif_paths"], list) and all(isinstance(item, str) for item in cbe["sarif_paths"]),
             "CBE sarif_paths must be a list of strings")
    _hash(cbe["evidence_sha256"], "CBE evidence_sha256")
    _check_status_consistency("CBE", cbe["gate_status"], exit_code, ratio, cbe["blocking_skip"])
    return cbe


def validate_cbp(data: Mapping[str, Any]) -> dict[str, Any]:
    cbp = dict(data)
    for field in CBP_REQUIRED:
        _require(field in cbp, f"CBP manifest missing field: {field}")
    _require(cbp["schema_version"] == "1", "CBP schema_version must be 1")
    _require(isinstance(cbp["package_id"], str) and cbp["package_id"], "CBP package_id must be non-empty")
    _require(isinstance(cbp["version"], str) and VERSION_RE.fullmatch(cbp["version"]),
             "CBP version is invalid")
    _require(isinstance(cbp["gate_status"], str), "CBP gate_status must be a string")
    applicable = _int(cbp["applicable_gate_count"], "CBP applicable_gate_count", minimum=0)
    skip_count = _int(cbp["skip_count"], "CBP skip_count", minimum=0)
    ratio = _ratio(cbp["skip_ratio"], "CBP skip_ratio")
    if "exit_code" in cbp:
        exit_code = _int(cbp["exit_code"], "CBP exit_code", minimum=0)
    else:
        # Contract section 5 does not put exit_code in the quality manifest.
        # Infer it from the frozen status/ratio rules so consistency checks
        # still apply without inventing a required field.
        if cbp["gate_status"] == "PASS":
            exit_code = 0
        elif cbp["gate_status"] == "SKIPPED_INFRA":
            exit_code = 3
        elif cbp["gate_status"] == "FAIL":
            exit_code = 4 if ratio > 0.20 else 3
        else:
            exit_code = 3
    _check_ratio(skip_count, applicable, ratio, "CBP")
    _require(isinstance(cbp["blocking_skip"], bool), "CBP blocking_skip must be boolean")
    gates = cbp["gates"]
    _require(isinstance(gates, list), "CBP gates must be a list")
    for position, gate in enumerate(gates, 1):
        _require(isinstance(gate, dict), f"CBP gates[{position}] must be an object")
        _require(isinstance(gate.get("name"), str) and gate["name"], f"CBP gates[{position}].name is invalid")
        _require(gate.get("status") in {"PASS", "FAIL", "SKIPPED"}, f"CBP gates[{position}].status is invalid")
        if gate.get("status") == "SKIPPED":
            _require(isinstance(gate.get("reason"), str) and gate["reason"].strip(),
                     f"CBP gates[{position}] is SKIPPED without a reason")
    artifacts = cbp["artifact_hashes"]
    _require(isinstance(artifacts, dict), "CBP artifact_hashes must be an object")
    for name, value in artifacts.items():
        _require(isinstance(name, str) and name, "CBP artifact_hashes key must be non-empty")
        _hash(value, f"CBP artifact_hashes[{name!r}]")
    repository = cbp["artifact_repository"]
    _require(isinstance(repository, dict),
             "CBP artifact_repository must be an object with repository/run_id/artifact_name (RC2 canonical)")
    _require(set(repository) == {"repository", "run_id", "artifact_name"},
             "CBP artifact_repository must contain exactly repository/run_id/artifact_name")
    for field in ("repository", "run_id", "artifact_name"):
        _require(isinstance(repository[field], str) and repository[field].strip(),
                 f"CBP artifact_repository.{field} must be a non-empty string")
    _hash(cbp["release_body_hash"], "CBP release_body_hash")
    _hash(cbp["evidence_sha256"], "CBP evidence_sha256")
    if "tag" in cbp:
        _require(isinstance(cbp["tag"], str) and TAG_RE.fullmatch(cbp["tag"]), "CBP tag is invalid")
    scope = cbp.get("body_hash_scope")
    if scope is not None:
        _require(scope in {"base", "full"}, "CBP body_hash_scope must be 'base' or 'full'")
    _check_status_consistency("CBP", cbp["gate_status"], exit_code, ratio, cbp["blocking_skip"])
    return cbp


def resolve_identity(
    *,
    cbe: Mapping[str, Any],
    cbp: Mapping[str, Any],
    chain_version: str,
    chain_tag: str,
    cli_version: str | None = None,
    cli_tag: str | None = None,
) -> tuple[str, str]:
    """Bind the target by version + tag; package_id is deliberately ignored.

    TODO(v1.8): once CBE/CBP define whether package_id is the producer or the
    target package, add a ``package_id == "cbc"`` check with
    ``reason=REPORT_IDENTITY_MISMATCH``.  Tightening it now would reject every
    current report whose package_id is ``cbe``/``cbp``.
    """
    versions: list[str] = []
    for label, value in (
        ("chain", chain_version),
        ("cbe", cbe.get("version")),
        ("cbp", cbp.get("version")),
        ("--version", cli_version),
    ):
        if value is None:
            continue
        try:
            versions.append(normalize_version(str(value)))
        except InputError as exc:
            raise InputError(f"{label} {exc}") from exc
    _require(bool(versions), "no version provided by chain, CBE, CBP, or --version")
    if len(set(versions)) != 1:
        raise InputError("version mismatch: " + ", ".join(sorted(set(versions))))

    tags: list[str] = []
    for label, value in (
        ("chain", chain_tag),
        ("cbe", cbe.get("tag")),
        ("cbp", cbp.get("tag")),
        ("--tag", cli_tag),
    ):
        if value is None:
            continue
        try:
            tags.append(normalize_tag(str(value)))
        except InputError as exc:
            raise InputError(f"{label} {exc}") from exc
    _require(bool(tags), "no tag provided by chain, CBE, CBP, or --tag")
    if len(set(tags)) != 1:
        raise InputError("tag mismatch: " + ", ".join(sorted(set(tags))))
    return "v" + versions[0], tags[0]


def load_gate_reports(
    cbe_path: Path | str,
    cbp_path: Path | str,
    *,
    chain_version: str,
    chain_tag: str,
    cli_version: str | None = None,
    cli_tag: str | None = None,
) -> GateReports:
    cbe = validate_cbe(_read_json(cbe_path, "CBE report"))
    cbp = validate_cbp(_read_json(cbp_path, "CBP quality manifest"))
    version, tag = resolve_identity(
        cbe=cbe,
        cbp=cbp,
        chain_version=chain_version,
        chain_tag=chain_tag,
        cli_version=cli_version,
        cli_tag=cli_tag,
    )
    return GateReports(
        cbe=cbe,
        cbp=cbp,
        version=version,
        tag=tag,
        body_hash_scope=cbp.get("body_hash_scope"),
    )


def canonical_body_bytes(data: bytes) -> bytes:
    """Contract v1.7.1 §5.3 body canonicalization."""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    data = data.rstrip(b"\n")
    if data:
        data += b"\n"
    return data


def canonical_body_sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(canonical_body_bytes(data)).hexdigest()


def hash_matches(value: str, data: bytes) -> bool:
    """Compare a CBP release_body_hash to the canonical base body."""
    try:
        expected = normalize_hash(value)
    except InputError:
        return False
    actual = "sha256:" + canonical_body_sha256(data)
    return expected == actual
