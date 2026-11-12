"""CBC-E2E-V2: protocol v2 negotiation, dual-read, fail-closed edges."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbc_event import EventStore, GENESIS, compute_event_hash, read_events
from cbc_event.schema import validate_event as validate_schema
from cbc_event.protocol import V1, V2, UnsupportedEventVersion, negotiate
from cbc_viewer.event_chain import build_event_manifest
from cbc_viewer.verify import verify_event_log_report

SOURCE_V1 = {"kind": "CBP", "name": "cbp-action", "version": "0.1.0", "instance": "test"}
SOURCE_V2 = {"kind": "cbp", "name": "cbp-action", "version": "1.3.1", "instance": "ci"}
IDENTITY = {"package_id": "cbc", "producer_id": "cbp", "package_version": "0.2.0"}
CHAIN_ID = "cbc-main"


def _jsonl(event_dir: Path) -> Path:
    return next(event_dir.glob("*.jsonl"))


def _rewrite(events: list[dict], event_dir: Path) -> None:
    target = _jsonl(event_dir)
    target.write_text("".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events),
                      encoding="utf-8")
    head = {
        "seq": len(events),
        "last_hash": events[-1]["event_hash"],
        "date": events[-1]["timestamp"][:10],
        "updated_at": events[-1]["timestamp"],
    }
    (event_dir / "head.json").write_text(json.dumps(head), encoding="utf-8")


def _v2_store(root: Path) -> EventStore:
    return EventStore(
        root,
        SOURCE_V2,
        enabled=True,
        protocol_version="v2",
        identity=IDENTITY,
        chain_id=CHAIN_ID,
    )


class ProtocolNegotiationTests(unittest.TestCase):
    def test_supported_versions(self) -> None:
        self.assertEqual(negotiate(V1).major, 1)
        self.assertEqual(negotiate(V2).major, 2)
        with self.assertRaises(UnsupportedEventVersion):
            negotiate("cbc-event/v3")

    def test_v2_requires_identity_type_and_chain(self) -> None:
        event = _v2_store(Path(tempfile.mkdtemp())).emit(
            "INFO", "one", {}, event_type="observation"
        )
        assert event is not None
        good = validate_schema(event)
        self.assertEqual(good[0], [])
        for field in ("identity", "event_type", "chain_id", "event_id"):
            broken = dict(event)
            broken.pop(field)
            errors, _ = validate_schema(broken)
            self.assertTrue(any(field in item for item in errors), field)

    def test_v2_identity_is_strict(self) -> None:
        event = _v2_store(Path(tempfile.mkdtemp())).emit(
            "INFO", "one", {}, event_type="observation"
        )
        assert event is not None
        event["identity"]["package_id"] = "CBC"
        errors, _ = validate_schema(event)
        self.assertTrue(any("package_id" in item for item in errors))
        event["identity"] = {**IDENTITY, "package_version": "v0.2.0"}
        errors, _ = validate_schema(event)
        self.assertTrue(any("package_version" in item for item in errors))

    def test_unknown_version_is_error_not_warning(self) -> None:
        event = _v2_store(Path(tempfile.mkdtemp())).emit(
            "INFO", "one", {}, event_type="observation"
        )
        assert event is not None
        event["schema"] = "cbc-event/v3"
        errors, warnings = validate_schema(event)
        self.assertTrue(any("unsupported event schema" in item for item in errors))
        self.assertFalse(any("schema" in item for item in warnings))

    def test_unknown_v2_field_is_warning(self) -> None:
        event = _v2_store(Path(tempfile.mkdtemp())).emit(
            "INFO", "one", {}, event_type="observation"
        )
        assert event is not None
        event["future_field"] = "ok"
        errors, warnings = validate_schema(event)
        self.assertEqual(errors, [])
        self.assertTrue(any("future_field" in item for item in warnings))


class DualReadTests(unittest.TestCase):
    def test_v2_log_pass_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = _v2_store(root)
            store.emit("INFO", "one", {}, event_type="observation")
            store.emit("WARN", "two", {}, event_type="decision")
            result = verify_event_log_report(root)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.report["chain_profile"], "event-log/v2")
            self.assertEqual(set(result.report["inputs"]["event_versions"]), {V2})
            self.assertEqual(result.report["inputs"]["event_chain_ids"], [CHAIN_ID])

    def test_mixed_v1_v2_log_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            EventStore(root, SOURCE_V1, enabled=True).emit("INFO", "legacy", {})
            _v2_store(root).emit("INFO", "new", {}, event_type="observation")
            result = verify_event_log_report(root)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.report["chain_profile"], "event-log/mixed")
            self.assertEqual(set(result.report["inputs"]["event_versions"]), {V1, V2})

    def test_v1_only_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            EventStore(root, SOURCE_V1, enabled=True).emit("INFO", "legacy", {})
            result = verify_event_log_report(root)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.report["chain_profile"], "event-log/v1")

    def test_v2_unknown_field_viewer_warns_but_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = _v2_store(root)
            event = store.emit("INFO", "one", {}, event_type="observation")
            assert event is not None
            event["future_field"] = "ok"
            event["event_hash"] = compute_event_hash(event["prev_hash"], event)
            _rewrite([event], root)
            result = verify_event_log_report(root)
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(any("future_field" in item for item in result.report["inputs"]["event_warnings"]))

    def test_v2_chain_id_mismatch_is_chain_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = _v2_store(root)
            first = store.emit("INFO", "one", {}, event_type="observation")
            second = store.emit("INFO", "two", {}, event_type="observation")
            assert first is not None and second is not None
            second["chain_id"] = "other-chain"
            second["event_hash"] = compute_event_hash(second["prev_hash"], second)
            _rewrite([first, second], root)
            result = verify_event_log_report(root)
            self.assertEqual(result.exit_code, 3)
            self.assertEqual(result.report["broken_link"]["reason"], "chain_identity_mismatch")

    def test_unknown_version_viewer_fails_closed_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = _v2_store(root)
            event = store.emit("INFO", "one", {}, event_type="observation")
            assert event is not None
            event["schema"] = "cbc-event/v3"
            _rewrite([event], root)
            result = verify_event_log_report(root)
            self.assertEqual(result.exit_code, 2)
            self.assertEqual(result.report["error"]["code"], "UNSUPPORTED_EVENT_VERSION")

    def test_read_events_unknown_version_is_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event = _v2_store(root).emit("INFO", "one", {}, event_type="observation")
            assert event is not None
            event["schema"] = "cbc-event/v3"
            _rewrite([event], root)
            events, _warnings, problems = read_events(root)
            self.assertEqual(events, [])
            self.assertTrue(any("unsupported event schema" in item for item in problems))


class StoreOptInTests(unittest.TestCase):
    def test_default_remains_v1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            event = EventStore(Path(tmp), SOURCE_V1, enabled=True).emit("INFO", "one", {})
            assert event is not None
            self.assertEqual(event["schema"], V1)

    def test_v2_emit_requires_event_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _v2_store(Path(tmp))
            with self.assertRaises(ValueError):
                store.emit("INFO", "one", {})

    def test_v2_manifest_shape_is_still_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _v2_store(root).emit("INFO", "one", {}, event_type="observation")
            manifest = build_event_manifest(root)
            self.assertEqual(manifest["chain_scope"], "event-log")
            self.assertEqual(manifest["link_count"], 1)
            self.assertTrue(manifest["root_hash"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
