"""Read-only verification of the ``cbc-event`` JSONL hash chain.

This is the event-log scope of CBC: sequence continuity, ``prev_hash``,
recomputed ``event_hash``, the ``head.json`` manifest, and (when supplied) a
file-level manifest that detects replaced/extra/missing JSONL files.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cbc_event import GENESIS, validate_event
from cbc_event.protocol import V1, V2, UnsupportedEventVersion as ProtocolVersionError, negotiate

from .chain import HASH_RE, is_safe_name, sha256_bytes, sha256_file
from .errors import BrokenLink, InputError, UnsupportedEventVersion


@dataclass(frozen=True)
class EventCheck:
    broken: BrokenLink | None
    root_hash: str
    link_count: int
    verified_count: int
    head: dict[str, Any] | None
    profile: str = "event-log/v1"
    versions: tuple[str, ...] = ()
    chain_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _read_head(event_dir: Path) -> tuple[dict[str, Any], bytes]:
    path = event_dir / "head.json"
    if not path.is_file():
        raise InputError("event-log head.json is missing")
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise InputError(f"cannot read event-log head.json: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError("event-log head.json must be an object")
    if not isinstance(data.get("seq"), int) or isinstance(data.get("seq"), bool) or data["seq"] < 1:
        raise InputError("event-log head.json seq is invalid")
    if not isinstance(data.get("last_hash"), str) or not HASH_RE.fullmatch(data["last_hash"]):
        raise InputError("event-log head.json last_hash is invalid")
    return data, raw


def _event_files(event_dir: Path) -> list[Path]:
    if not event_dir.is_dir():
        raise InputError(f"event directory not found: {event_dir}")
    return sorted(event_dir.glob("*.jsonl"), key=lambda item: item.name)


def _manifest_files(data: Any) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if not isinstance(data, dict):
        raise InputError("event manifest must be an object")
    for field in ("schema", "chain_scope", "files", "head", "link_count", "root_hash"):
        if field not in data:
            raise InputError(f"event manifest missing field: {field}")
    if data["schema"] != "cbc-chain/v1":
        raise InputError("event manifest schema must be cbc-chain/v1")
    if data["chain_scope"] != "event-log":
        raise InputError("event manifest chain_scope must be event-log")
    if not isinstance(data["files"], list) or not data["files"]:
        raise InputError("event manifest files must be a non-empty array")
    files: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(data["files"], 1):
        if not isinstance(item, dict):
            raise InputError(f"event manifest files[{position}] must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not name.endswith(".jsonl") or not is_safe_name(name):
            raise InputError(f"event manifest files[{position}] name is invalid")
        if name in files:
            raise InputError(f"event manifest duplicate file: {name}")
        if not isinstance(item.get("sha256"), str) or not HASH_RE.fullmatch(item["sha256"]):
            raise InputError(f"event manifest files[{position}] sha256 is invalid")
        if not isinstance(item.get("size"), int) or isinstance(item.get("size"), bool) or item["size"] < 0:
            raise InputError(f"event manifest files[{position}] size is invalid")
        files[name] = item
    head = data["head"]
    if not isinstance(head, dict):
        raise InputError("event manifest head must be an object")
    if not isinstance(head.get("seq"), int) or isinstance(head.get("seq"), bool) or head["seq"] < 1:
        raise InputError("event manifest head.seq is invalid")
    if not isinstance(head.get("last_hash"), str) or not HASH_RE.fullmatch(head["last_hash"]):
        raise InputError("event manifest head.last_hash is invalid")
    if "sha256" in head and (not isinstance(head["sha256"], str) or not HASH_RE.fullmatch(head["sha256"])):
        raise InputError("event manifest head.sha256 is invalid")
    if not isinstance(data["link_count"], int) or isinstance(data["link_count"], bool) or data["link_count"] < 1:
        raise InputError("event manifest link_count must be a positive integer")
    if not isinstance(data["root_hash"], str) or not HASH_RE.fullmatch(data["root_hash"]):
        raise InputError("event manifest root_hash is invalid")
    return files, head


def read_event_manifest(path: Path | str) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise InputError(f"event manifest not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read event manifest: {exc}") from exc
    _manifest_files(data)
    return data


def _profile(versions: list[str]) -> str:
    unique = set(versions)
    if unique == {V1, V2}:
        return "event-log/mixed"
    if unique == {V2}:
        return "event-log/v2"
    return "event-log/v1"


def verify_event_log(event_dir: Path | str, *, manifest_path: Path | str | None = None) -> EventCheck:
    root = Path(event_dir)
    files = _event_files(root)
    if not files and manifest_path is None:
        raise InputError("event directory contains no *.jsonl files")
    head, head_raw = _read_head(root)

    declared_files: dict[str, dict[str, Any]] = {}
    declared_head: dict[str, Any] | None = None
    declared_count: int | None = None
    declared_root: str | None = None
    if manifest_path is not None:
        manifest = read_event_manifest(manifest_path)
        declared_files, declared_head = _manifest_files(manifest)
        declared_count = int(manifest["link_count"])
        declared_root = str(manifest["root_hash"])
        actual_names = {path.name for path in files}
        expected_names = set(declared_files)
        extra = sorted(actual_names - expected_names)
        if extra:
            return EventCheck(BrokenLink(kind="event_file", name=extra[0], reason="unexpected_asset"),
                              GENESIS, declared_count, 0, head)
        missing = sorted(expected_names - actual_names)
        if missing:
            return EventCheck(BrokenLink(kind="event_file", name=missing[0], reason="missing_asset"),
                              GENESIS, declared_count, 0, head)
        if declared_head and declared_head.get("sha256"):
            if sha256_bytes(head_raw) != declared_head["sha256"]:
                return EventCheck(BrokenLink(kind="head", name="head.json", reason="hash_mismatch",
                                             expected=declared_head["sha256"], actual=sha256_bytes(head_raw)),
                                  GENESIS, declared_count, 0, head)
        if declared_head:
            if declared_head["seq"] != head["seq"] or declared_head["last_hash"] != head["last_hash"]:
                return EventCheck(BrokenLink(kind="head", name="head.json", reason="chain_root_mismatch",
                                             expected=declared_head["last_hash"], actual=head["last_hash"]),
                                  GENESIS, declared_count, 0, head)

    expected_seq = 1
    expected_prev = GENESIS
    root_hash = GENESIS
    verified = 0
    versions: list[str] = []
    chain_ids: list[str] = []
    warnings: list[str] = []
    v2_chain_id: str | None = None
    for path in files:
        if manifest_path is not None:
            declared = declared_files.get(path.name)
            if declared is not None:
                actual_hash = sha256_file(path)
                actual_size = path.stat().st_size
                if actual_hash != declared["sha256"] or actual_size != declared["size"]:
                    return EventCheck(BrokenLink(kind="event_file", name=path.name, reason="hash_mismatch",
                                                 expected=declared["sha256"], actual=actual_hash),
                                      root_hash, declared_count or 0, verified, head)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return EventCheck(BrokenLink(kind="event_file", name=path.name, reason="report_invalid",
                                         detail=str(exc)), root_hash, declared_count or 0, verified, head)
        for lineno, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except ValueError as exc:
                return EventCheck(BrokenLink(kind="event", name=f"{path.name}:{lineno}", reason="report_invalid",
                                             detail=str(exc)), root_hash, declared_count or 0, verified, head)
            try:
                info = negotiate(event.get("schema"))
            except ProtocolVersionError as exc:
                raise UnsupportedEventVersion(
                    f"unsupported event version at {path.name}:{lineno}: {exc}"
                ) from exc
            report = validate_event(event, expected_seq=expected_seq, prev_hash=expected_prev)
            warnings.extend(f"{path.name}:{lineno}: {item}" for item in report["warnings"])
            versions.append(info.schema)
            if info.schema == V2:
                chain_id = str(event.get("chain_id", ""))
                if chain_id not in chain_ids:
                    chain_ids.append(chain_id)
                if v2_chain_id is None:
                    v2_chain_id = chain_id
                elif chain_id != v2_chain_id:
                    return EventCheck(
                        BrokenLink(kind="chain", name="chain_id", reason="chain_identity_mismatch",
                                   expected=v2_chain_id, actual=chain_id,
                                   detail="all cbc-event/v2 events in one log must share chain_id"),
                        root_hash, declared_count or 0, verified, head,
                        profile="event-log/v2", versions=tuple(versions),
                        chain_ids=tuple(chain_ids), warnings=tuple(warnings),
                    )
            if report["problems"]:
                return EventCheck(BrokenLink(kind="event", name=f"{path.name}:{lineno}", reason="report_invalid",
                                             detail="; ".join(report["problems"])), root_hash, declared_count or 0, verified, head,
                                  profile=_profile(versions), versions=tuple(versions),
                                  chain_ids=tuple(chain_ids), warnings=tuple(warnings))
            if report["critical"]:
                reason = "chain_seq_gap" if any("sequence gap" in item for item in report["critical"]) else "chain_hash_mismatch"
                return EventCheck(BrokenLink(kind="event", name=f"{path.name}:{lineno}", reason=reason,
                                             expected=expected_prev, actual=str(event.get("event_hash")),
                                             detail="; ".join(report["critical"])), root_hash, declared_count or 0, verified, head)
            expected_seq = int(event["seq"]) + 1
            expected_prev = str(event["event_hash"])
            root_hash = expected_prev
            verified += 1

    if head["seq"] != verified:
        return EventCheck(BrokenLink(kind="head", name="head.json", reason="chain_link_count_mismatch",
                                     expected=str(head["seq"]), actual=str(verified)), root_hash, declared_count or 0, verified, head)
    if head["last_hash"] != root_hash:
        return EventCheck(BrokenLink(kind="head", name="head.json", reason="chain_root_mismatch",
                                     expected=head["last_hash"], actual=root_hash), root_hash, declared_count or 0, verified, head)
    if declared_count is not None and declared_count != verified:
        return EventCheck(BrokenLink(kind="chain", name="link_count", reason="chain_link_count_mismatch",
                                     expected=str(declared_count), actual=str(verified)), root_hash, declared_count, verified, head)
    if declared_root is not None and declared_root != root_hash:
        return EventCheck(BrokenLink(kind="chain", name="root_hash", reason="chain_root_mismatch",
                                     expected=declared_root, actual=root_hash), root_hash, declared_count or 0, verified, head)
    profile = _profile(versions)
    return EventCheck(None, root_hash, declared_count if declared_count is not None else verified, verified, head,
                      profile=profile, versions=tuple(versions), chain_ids=tuple(chain_ids), warnings=tuple(warnings))


def build_event_manifest(event_dir: Path | str) -> dict[str, Any]:
    """Build an event-log chain manifest (pure; no writes)."""
    root = Path(event_dir)
    files = _event_files(root)
    if not files:
        raise InputError("event directory contains no *.jsonl files")
    head, head_raw = _read_head(root)
    entries: list[dict[str, Any]] = []
    count = 0
    for path in files:
        first = None
        last = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                raise InputError(f"{path.name}: blank line")
            event = json.loads(line)
            count += 1
            if first is None:
                first = int(event["seq"])
            last = int(event["seq"])
        if first is None:
            raise InputError(f"{path.name}: no events")
        entries.append({
            "name": path.name,
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
            "first_seq": first,
            "last_seq": last,
        })
    return {
        "schema": "cbc-chain/v1",
        "chain_scope": "event-log",
        "files": entries,
        "head": {
            "seq": head["seq"],
            "last_hash": head["last_hash"],
            "sha256": sha256_bytes(head_raw),
        },
        "link_count": count,
        "root_hash": head["last_hash"],
    }
