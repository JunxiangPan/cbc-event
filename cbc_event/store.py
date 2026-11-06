"""Append-only JSONL event store with a per-file hash chain."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .canonical import canonical_bytes
from .schema import validate_event

GENESIS = "sha256:" + ("0" * 64)
HEAD = "head.json"
LOCK = ".cbc-event.lock"
_THREAD_LOCK = threading.Lock()


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def compute_event_hash(prev_hash: str, event: dict[str, Any]) -> str:
    """Hash prev_hash and the canonical event without event_hash."""
    body = {key: value for key, value in event.items() if key != "event_hash"}
    return _sha256(prev_hash.encode("utf-8") + b"\n" + canonical_bytes(body))


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _THREAD_LOCK, path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_head(event_dir: Path) -> dict[str, Any] | None:
    path = event_dir / HEAD
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("seq"), int) and isinstance(data.get("last_hash"), str):
            return data
    except (OSError, ValueError):
        pass
    return None


class EventStore:
    """Append one event at a time; disabled stores never touch the filesystem."""

    def __init__(self, event_dir: Path | str, source: dict[str, str], enabled: bool = False) -> None:
        self.event_dir = Path(event_dir)
        self.source = dict(source)
        self.enabled = enabled

    def emit(
        self,
        level: str,
        action: str,
        detail: dict[str, Any],
        *,
        evidence: bytes | None = None,
        evidence_hash: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        if evidence is not None:
            evidence_hash = _sha256(evidence)
        if evidence_hash is None:
            evidence_hash = _sha256(canonical_bytes(detail))
        self.event_dir.mkdir(parents=True, exist_ok=True)
        with _file_lock(self.event_dir / LOCK):
            head = _read_head(self.event_dir)
            seq = int(head["seq"]) + 1 if head else 1
            prev_hash = str(head["last_hash"]) if head else GENESIS
            event: dict[str, Any] = {
                "schema": "cbc-event/v1",
                "event_id": str(uuid.uuid4()),
                "timestamp": _timestamp(),
                "source": self.source,
                "level": level,
                "action": action,
                "detail": detail,
                "evidence_hash": evidence_hash,
                "prev_hash": prev_hash,
                "seq": seq,
            }
            errors, _warnings = validate_event({**event, "event_hash": GENESIS})
            if errors:
                raise ValueError("invalid cbc-event: " + "; ".join(errors))
            event["event_hash"] = compute_event_hash(prev_hash, event)
            day = event["timestamp"][:10]
            target = self.event_dir / f"{day}.jsonl"
            with target.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            updated = {
                "seq": seq,
                "last_hash": event["event_hash"],
                "date": day,
                "updated_at": event["timestamp"],
            }
            temporary = self.event_dir / (HEAD + ".tmp")
            temporary.write_text(
                json.dumps(updated, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, self.event_dir / HEAD)
            return event


def read_events(path: Path | str) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Read all event lines; never reject unknown fields or a broken chain."""
    root = Path(path)
    files = sorted(root.glob("*.jsonl")) if root.is_dir() else [root]
    events: list[dict[str, Any]] = []
    warnings: list[str] = []
    problems: list[str] = []
    expected_seq = 1
    expected_prev = GENESIS
    for file in files:
        if not file.is_file():
            continue
        for lineno, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            try:
                event = json.loads(line)
            except ValueError as exc:
                problems.append(f"{file.name}:{lineno}: invalid json: {exc}")
                continue
            errors, event_warnings = validate_event(event)
            warnings.extend(f"{file.name}:{lineno}: {item}" for item in event_warnings)
            if errors:
                problems.extend(f"{file.name}:{lineno}: {item}" for item in errors)
                continue
            if event["seq"] != expected_seq:
                problems.append(f"{file.name}:{lineno}: sequence gap: expected {expected_seq}, got {event['seq']}")
            if event["prev_hash"] != expected_prev:
                problems.append(f"{file.name}:{lineno}: chain break: prev_hash does not match")
            if compute_event_hash(event["prev_hash"], event) != event["event_hash"]:
                problems.append(f"{file.name}:{lineno}: event_hash mismatch")
            expected_seq = event["seq"] + 1
            expected_prev = event["event_hash"]
            events.append(event)
    return events, warnings, problems
