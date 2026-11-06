"""Reader edge cases and store rejection paths."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbc_event import EventStore, canonical_json, read_events
from cbc_event.canonical import _number


SOURCE = {"kind": "CBP", "name": "reader", "version": "0.1.0", "instance": "test"}


class ReaderEdgeTests(unittest.TestCase):
    def test_missing_path_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            events, warnings, problems = read_events(Path(tmp) / "missing")
            self.assertEqual((events, warnings, problems), ([], [], []))

    def test_invalid_json_is_a_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "2026-11-06.jsonl"
            target.write_text("{bad json}\n", encoding="utf-8")
            events, _warnings, problems = read_events(tmp)
            self.assertEqual(events, [])
            self.assertTrue(any("invalid json" in item for item in problems))

    def test_invalid_event_is_a_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "2026-11-06.jsonl"
            target.write_text(json.dumps({"level": "INFO"}) + "\n", encoding="utf-8")
            events, _warnings, problems = read_events(tmp)
            self.assertEqual(events, [])
            self.assertTrue(any("missing field" in item for item in problems))

    def test_invalid_head_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "head.json").write_text("{not json}\n", encoding="utf-8")
            store = EventStore(tmp, SOURCE, enabled=True)
            event = store.emit("INFO", "head.repair", {})
            self.assertIsNotNone(event)
            self.assertEqual(event["seq"], 1)

    def test_invalid_level_is_rejected_by_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp, SOURCE, enabled=True)
            with self.assertRaises(ValueError):
                store.emit("DEBUG", "bad.level", {})

    def test_canonical_unsupported_values(self) -> None:
        with self.assertRaises(Exception):
            _number("not-a-number")
        with self.assertRaises(Exception):
            canonical_json(object())
        with self.assertRaises(Exception):
            canonical_json({1: "non-string-key"})


if __name__ == "__main__":
    unittest.main()
