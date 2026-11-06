"""Client and schema branch tests."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cbc_event import Client, emit, validate_event


SOURCE = {"kind": "CBP", "name": "client", "version": "0.1.0", "instance": "test"}


class ClientTests(unittest.TestCase):
    def test_client_defaults_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(event_dir=tmp, enabled=False, source=SOURCE)
            self.assertFalse(client.enabled)
            self.assertIsNone(client.emit("INFO", "x", {}))
            self.assertFalse(Path(tmp, "must-not-exist").exists())

    def test_client_reads_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CBC_REPORT_ENABLED": "true", "CBC_EVENT_DIR": tmp}):
                client = Client(source=SOURCE)
                self.assertTrue(client.enabled)
                event = client.emit("INFO", "env.enabled", {"value": 1})
                self.assertIsNotNone(event)

    def test_convenience_emit_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            event = emit("WARN", "wrapper", {"value": 2}, source=SOURCE, event_dir=tmp, enabled=True)
            self.assertIsNotNone(event)
            self.assertEqual(event["level"], "WARN")

    def test_evidence_bytes_and_explicit_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(event_dir=tmp, enabled=True, source=SOURCE)
            first = client.emit("INFO", "evidence", {}, evidence=b"raw")
            explicit = "sha256:" + "a" * 64
            second = client.emit("INFO", "evidence-hash", {}, evidence_hash=explicit)
            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            self.assertEqual(second["evidence_hash"], explicit)


class SchemaBranchTests(unittest.TestCase):
    def test_non_object_event(self) -> None:
        report = validate_event([])
        self.assertTrue(report["problems"])

    def test_all_field_errors(self) -> None:
        event = {
            "schema": "wrong",
            "timestamp": "not-a-date",
            "source": "not-object",
            "level": "DEBUG",
            "action": "",
            "detail": [],
            "evidence_hash": "bad",
            "prev_hash": "bad",
            "event_hash": "bad",
            "seq": 0,
        }
        report = validate_event(event)
        joined = " ".join(report["problems"])
        for expected in ("schema", "timestamp", "source", "level", "action", "detail", "evidence_hash", "seq"):
            self.assertIn(expected, joined)

    def test_source_field_and_unknown_source_field(self) -> None:
        event = {
            "schema": "cbc-event/v1",
            "timestamp": "2026-11-06T15:30:00.000Z",
            "source": {"kind": "", "name": "", "version": "", "instance": "", "extra": "x"},
            "level": "INFO",
            "action": "a",
            "detail": {},
            "evidence_hash": "sha256:" + "a" * 64,
            "prev_hash": "sha256:" + "0" * 64,
            "event_hash": "sha256:" + "b" * 64,
            "seq": 1,
        }
        report = validate_event(event)
        self.assertTrue(any("source.kind" in item for item in report["problems"]))
        self.assertTrue(any("unknown source field" in item for item in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
