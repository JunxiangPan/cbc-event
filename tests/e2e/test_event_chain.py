"""CBC-E2E-L01..L08: event-log hash-chain verification."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbc_event import EventStore
from cbc_viewer.event_chain import build_event_manifest
from cbc_viewer.verify import verify_event_log_report

SOURCE = {"kind": "CBP", "name": "cbp-action", "version": "0.1.0", "instance": "test"}


def make_events(tmp: Path, count: int = 3) -> tuple[Path, Path]:
    event_dir = tmp / "events"
    store = EventStore(event_dir, SOURCE, enabled=True)
    for index in range(count):
        store.emit("INFO", f"event.{index}", {"index": index})
    manifest = build_event_manifest(event_dir)
    manifest_path = event_dir / "cbc-chain.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return event_dir, manifest_path


def _jsonl(event_dir: Path) -> Path:
    return next(event_dir.glob("*.jsonl"))


class EventChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.event_dir, self.manifest = make_events(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_l01_clean(self) -> None:
        result = verify_event_log_report(self.event_dir, manifest_path=self.manifest)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report["cbc_chain_status"], "PASS")
        self.assertEqual(result.report["link_count"], 3)
        self.assertEqual(result.report["chain_scope"], "event-log")

    def test_l02_replaced_event(self) -> None:
        target = _jsonl(self.event_dir)
        lines = target.read_text(encoding="utf-8").splitlines()
        event = json.loads(lines[0])
        event["detail"]["index"] = 999
        lines[0] = json.dumps(event)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_event_log_report(self.event_dir)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_hash_mismatch")

    def test_l03_extra_event_file(self) -> None:
        target = _jsonl(self.event_dir)
        (self.event_dir / "2099-01-01.jsonl").write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        result = verify_event_log_report(self.event_dir, manifest_path=self.manifest)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "unexpected_asset")

    def test_l04_missing_event_file(self) -> None:
        _jsonl(self.event_dir).unlink()
        result = verify_event_log_report(self.event_dir, manifest_path=self.manifest)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "missing_asset")

    def test_l05_head_mismatch(self) -> None:
        head_path = self.event_dir / "head.json"
        head = json.loads(head_path.read_text(encoding="utf-8"))
        head["seq"] = 99
        head_path.write_text(json.dumps(head), encoding="utf-8")
        result = verify_event_log_report(self.event_dir)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_link_count_mismatch")

    def test_l05b_head_hash_mismatch(self) -> None:
        head_path = self.event_dir / "head.json"
        head = json.loads(head_path.read_text(encoding="utf-8"))
        head["last_hash"] = "sha256:" + "0" * 64
        head_path.write_text(json.dumps(head), encoding="utf-8")
        result = verify_event_log_report(self.event_dir)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_root_mismatch")

    def test_l06_sequence_gap(self) -> None:
        target = _jsonl(self.event_dir)
        lines = target.read_text(encoding="utf-8").splitlines()
        target.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
        result = verify_event_log_report(self.event_dir)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_seq_gap")

    def test_l07_missing_head_is_input_2(self) -> None:
        (self.event_dir / "head.json").unlink()
        result = verify_event_log_report(self.event_dir)
        self.assertEqual(result.exit_code, 2)

    def test_l08_bad_line_is_reported_not_repaired(self) -> None:
        target = _jsonl(self.event_dir)
        before = target.read_bytes()
        target.write_bytes(before + b"{bad json}\n")
        broken = target.read_bytes()
        result = verify_event_log_report(self.event_dir)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "report_invalid")
        self.assertEqual(target.read_bytes(), broken)


if __name__ == "__main__":
    unittest.main()
