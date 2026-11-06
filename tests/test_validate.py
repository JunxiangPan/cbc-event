"""Consumer-facing validate_event tests."""
from __future__ import annotations

import tempfile
import unittest

from cbc_event import EventStore, GENESIS, validate_event


SOURCE = {"kind": "CBC", "name": "reader", "version": "0.1.0", "instance": "test"}


class ValidateEventTests(unittest.TestCase):
    def test_missing_required_fields_problem_unknown_warning(self) -> None:
        report = validate_event({"level": "WARN", "future": True})
        self.assertFalse(report["ok"])
        self.assertTrue(any("missing field" in item for item in report["problems"]))
        self.assertTrue(any("future" in item for item in report["warnings"]))
        self.assertEqual(report["critical"], [])

    def test_chain_break_is_critical_and_event_is_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp, SOURCE, enabled=True)
            first = store.emit("INFO", "one", {})
            assert first is not None
            report = validate_event(first, expected_seq=2, prev_hash="sha256:" + "f" * 64)
            self.assertFalse(report["ok"])
            self.assertEqual(report["problems"], [])
            self.assertTrue(any("sequence gap" in item for item in report["critical"]))
            self.assertTrue(any("chain break" in item for item in report["critical"]))
            self.assertEqual(report["event"]["seq"], 1)

    def test_valid_genesis_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp, SOURCE, enabled=True)
            event = store.emit("INFO", "one", {})
            assert event is not None
            report = validate_event(event, expected_seq=1, prev_hash=GENESIS)
            self.assertTrue(report["ok"])
            self.assertEqual(report["critical"], [])


if __name__ == "__main__":
    unittest.main()
