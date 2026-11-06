"""Canonical JSON and schema validation tests."""
from __future__ import annotations

import unittest

from cbc_event import CanonicalizationError, canonical_json, validate_event


class CanonicalTests(unittest.TestCase):
    def test_key_order_and_whitespace(self) -> None:
        self.assertEqual(
            canonical_json({"b": 2, "a": [True, None, "x"]}),
            '{"a":[true,null,"x"],"b":2}',
        )

    def test_utf8_is_not_escaped(self) -> None:
        self.assertEqual(canonical_json("会议"), '"会议"')

    def test_number_stability(self) -> None:
        self.assertEqual(canonical_json(1.0), "1")
        self.assertEqual(canonical_json(-0.0), "0")
        self.assertEqual(canonical_json(1.5), "1.5")

    def test_boolean_null_and_list(self) -> None:
        self.assertEqual(canonical_json([False, None, "x"]), '[false,null,"x"]')

    def test_jcs_number_boundaries(self) -> None:
        self.assertEqual(canonical_json(1e20), "100000000000000000000")
        self.assertEqual(canonical_json(1e21), "1e+21")
        self.assertEqual(canonical_json(1e-6), "0.000001")
        self.assertEqual(canonical_json(1e-7), "1e-7")

    def test_non_finite_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_json(float("nan"))

    def test_unknown_fields_are_warnings(self) -> None:
        event = {
            "schema": "cbc-event/v1",
            "timestamp": "2026-11-06T15:30:00.000Z",
            "source": {"kind": "CBP", "name": "cbp", "version": "0.1.0", "instance": "x"},
            "level": "INFO",
            "action": "coverage.pass",
            "detail": {},
            "evidence_hash": "sha256:" + "a" * 64,
            "prev_hash": "sha256:" + "0" * 64,
            "event_hash": "sha256:" + "b" * 64,
            "seq": 1,
            "new_optional_field": "ok",
        }
        report = validate_event(event)
        self.assertEqual(report["problems"], [])
        self.assertTrue(any("new_optional_field" in item for item in report["warnings"]))

    def test_missing_core_field_is_error(self) -> None:
        report = validate_event({"level": "INFO"})
        self.assertTrue(any("missing field: timestamp" in item for item in report["problems"]))


if __name__ == "__main__":
    unittest.main()
