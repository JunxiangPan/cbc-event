"""CBC-E2E-SEM: optional semantic-verdict/v1 reader."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from cbc_event import (
    SEMANTIC_DISCLAIMER,
    SEMANTIC_VIEW_V1,
    SemanticVerdict,
    SemanticVerdictError,
    canonical_semantic_sha256,
)
from cbc_event.canonical import canonical_bytes


def _verdict(*, verdict: str = "PASS", confidence: float | None = 0.82) -> dict:
    data = {
        "schema": "semantic-verdict/v1",
        "verdict": verdict,
        "subject": {"package_id": "cbc", "version": "0.2.0", "artifact_sha256": "a" * 64},
        "generated_at": "2026-11-12T07:00:00Z",
        "findings": [{
            "rule_id": "semantic.check",
            "category": "SEMANTIC",
            "severity": "MEDIUM",
            "path": "cbc_event/cbf.py",
            "line": 42,
            "confidence": 0.7,
        }],
        "policy": {"name": "semantic-policy", "version": "1.0.0"},
    }
    if confidence is not None:
        data["confidence"] = confidence
    data["evidence_sha256"] = canonical_semantic_sha256(data)
    return data


class SemanticReaderTests(unittest.TestCase):
    def test_no_forbidden_imports(self) -> None:
        self.assertNotIn("cbf", sys.modules)
        self.assertNotIn("cbp", sys.modules)
        self.assertNotIn("cbe", sys.modules)
        self.assertNotIn("cbm", sys.modules)

    def test_view_displays_fields(self) -> None:
        view = SemanticVerdict.from_dict(_verdict()).view()
        self.assertEqual(view["schema"], SEMANTIC_VIEW_V1)
        self.assertEqual(view["verdict"], "PASS")
        self.assertEqual(view["confidence"], 0.82)
        self.assertEqual(view["subject"]["package_id"], "cbc")
        self.assertEqual(view["findings"][0]["rule_id"], "semantic.check")
        self.assertEqual(view["evidence_sha256"], _verdict()["evidence_sha256"])
        self.assertEqual(view["disclaimer"], SEMANTIC_DISCLAIMER)

    def test_not_run_and_no_confidence(self) -> None:
        verdict = SemanticVerdict.from_dict(_verdict(verdict="NOT_RUN", confidence=None))
        self.assertEqual(verdict.verdict, "NOT_RUN")
        self.assertIsNone(verdict.confidence)

    def test_unknown_schema_fail_closed(self) -> None:
        data = _verdict()
        data["schema"] = "semantic-verdict/v2"
        data["evidence_sha256"] = canonical_semantic_sha256(data)
        with self.assertRaises(SemanticVerdictError):
            SemanticVerdict.from_dict(data)

    def test_tamper_fail_closed(self) -> None:
        data = _verdict()
        data["verdict"] = "FAIL"
        with self.assertRaises(SemanticVerdictError):
            SemanticVerdict.from_dict(data)

    def test_invalid_fields_fail_closed(self) -> None:
        for mutation in (
            lambda d: d.update(verdict="UNKNOWN"),
            lambda d: d.update(generated_at=""),
            lambda d: d.update(subject={"package_id": "cbc", "artifact_sha256": "bad"}),
            lambda d: d.update(findings="x"),
            lambda d: d.update(confidence=1.5),
            lambda d: d.update(confidence=True),
        ):
            data = _verdict()
            mutation(data)
            data["evidence_sha256"] = canonical_semantic_sha256(data)
            with self.assertRaises(SemanticVerdictError):
                SemanticVerdict.from_dict(data)

    def test_load_and_cli_text_json(self) -> None:
        from cbc_viewer import cli
        from io import StringIO
        import contextlib

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "semantic.json"
            path.write_text(json.dumps(_verdict()), encoding="utf-8")
            out = StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cli.main(["semantic-verdict", "--evidence", str(path)]), 0)
            text = out.getvalue()
            self.assertIn("Semantic verdict: PASS", text)
            self.assertIn("confidence: 0.820", text)
            self.assertIn("semantic.check", text)
            self.assertIn("not factual proof", text)

            out = StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(
                    cli.main(["semantic-verdict", "--evidence", str(path), "--json"]), 0
                )
            data = json.loads(out.getvalue())
            self.assertEqual(data["schema"], SEMANTIC_VIEW_V1)
            self.assertEqual(data["verdict"], "PASS")

    def test_canonical_hash_matches_cbm_shape(self) -> None:
        data = _verdict()
        actual = data.pop("evidence_sha256")
        import hashlib
        expected = hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertEqual(actual, expected)
        self.assertEqual(actual, __import__("hashlib").sha256(canonical_bytes(data)).hexdigest())


if __name__ == "__main__":
    unittest.main()
