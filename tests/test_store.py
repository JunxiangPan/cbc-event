"""Store, chain, and concurrency tests."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from cbc_event import EventStore, GENESIS, compute_event_hash, read_events


SOURCE = {"kind": "CBP", "name": "cbp-action", "version": "0.1.0", "instance": "test"}


class StoreTests(unittest.TestCase):
    def test_disabled_does_not_create_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "must-not-exist"
            store = EventStore(path, SOURCE, enabled=False)
            self.assertIsNone(store.emit("INFO", "test.noop", {}))
            self.assertFalse(path.exists())

    def test_chain_and_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp, SOURCE, enabled=True)
            first = store.emit("INFO", "coverage.pass", {"value": 80})
            second = store.emit("WARN", "coverage.warn", {"value": 79})
            assert first is not None and second is not None
            self.assertEqual((first["seq"], second["seq"]), (1, 2))
            self.assertEqual(first["prev_hash"], GENESIS)
            self.assertEqual(second["prev_hash"], first["event_hash"])
            events, warnings, problems = read_events(tmp)
            self.assertEqual(len(events), 2)
            self.assertEqual(warnings, [])
            self.assertEqual(problems, [])

    def test_chain_break_is_reported_not_hidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp, SOURCE, enabled=True)
            store.emit("INFO", "one", {})
            store.emit("WARN", "two", {})
            target = next(Path(tmp).glob("*.jsonl"))
            lines = target.read_text(encoding="utf-8").splitlines()
            target.write_text(lines[1] + "\n", encoding="utf-8")
            events, _warnings, problems = read_events(tmp)
            self.assertEqual(len(events), 1)
            self.assertTrue(any("sequence gap" in item for item in problems))
            self.assertTrue(any("chain break" in item for item in problems))

    def test_event_hash_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp, SOURCE, enabled=True)
            event = store.emit("INFO", "one", {"value": 1})
            assert event is not None
            event["detail"]["value"] = 2
            target = next(Path(tmp).glob("*.jsonl"))
            target.write_text(json.dumps(event) + "\n", encoding="utf-8")
            events, _warnings, problems = read_events(tmp)
            self.assertEqual(len(events), 1)
            self.assertTrue(any("event_hash mismatch" in item for item in problems))

    def test_unknown_field_is_accepted_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp, SOURCE, enabled=True)
            event = store.emit("INFO", "one", {})
            assert event is not None
            event["future_field"] = "ok"
            event["event_hash"] = compute_event_hash(event["prev_hash"], event)
            target = next(Path(tmp).glob("*.jsonl"))
            target.write_text(json.dumps(event) + "\n", encoding="utf-8")
            events, warnings, problems = read_events(tmp)
            self.assertEqual(len(events), 1)
            self.assertEqual(problems, [])
            self.assertTrue(any("future_field" in item for item in warnings))

    def test_concurrent_append_has_unique_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            barrier = threading.Barrier(20)
            failures: list[BaseException] = []

            def worker(index: int) -> None:
                try:
                    store = EventStore(tmp, {**SOURCE, "instance": f"t{index}"}, enabled=True)
                    barrier.wait()
                    store.emit("INFO", "concurrent", {"index": index})
                except BaseException as exc:
                    failures.append(exc)

            threads = [threading.Thread(target=worker, args=(index,)) for index in range(20)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(failures, [])
            events, _warnings, problems = read_events(tmp)
            self.assertEqual(problems, [])
            self.assertEqual(len(events), 20)
            self.assertEqual(sorted(item["seq"] for item in events), list(range(1, 21)))


if __name__ == "__main__":
    unittest.main()
