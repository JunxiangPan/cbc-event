"""CBC-E2E-CBF: optional cbf-evidence/v1 adapter; no CBF import."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from cbc_event import GENESIS, CbfEvidence, CbfEvidenceError, load_cbf_evidence
from cbc_event.canonical import canonical_bytes
from cbc_event.schema import validate_event
from cbc_event.store import compute_event_hash

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "cbf-evidence-pass.json"


def _doc(*, result: str = "PASS", with_summary: bool = False) -> dict:
    doc = {
        "schema": "cbf-evidence/v1",
        "tool": "cbf",
        "version": "0.1.0",
        "policy_version": "0.1.0",
        "policy_sha256": "a" * 64,
        "policy_effective_sha256": "a" * 64,
        "project": "cbc",
        "repo": "JunxiangPan/cbc-event",
        "commit": "0" * 40,
        "ref": "refs/heads/0.2.0-dev",
        "surface": "git",
        "result": result,
        "findings": [],
        "scanned": {"files": 1, "bytes": 4, "skipped": 0},
        "generated_at": "2026-11-12T05:30:00Z",
    }
    import hashlib
    doc["evidence_sha256"] = hashlib.sha256(canonical_bytes(doc)).hexdigest()
    if with_summary:
        doc["summary"] = {"blocking": 0, "warnings": 0}
    return doc


class CbfAdapterTests(unittest.TestCase):
    def test_no_cbf_import(self) -> None:
        self.assertNotIn("cbf", sys.modules)

    def test_real_cbf_fixture_is_read(self) -> None:
        evidence = load_cbf_evidence(FIXTURE)
        self.assertEqual(evidence.schema, "cbf-evidence/v1")
        self.assertEqual(evidence.result, "PASS")
        self.assertEqual(evidence.hash_status, "verified_without_summary")
        view = evidence.view()
        self.assertEqual(view["schema"], "cbc-cbf-view/v1")
        self.assertEqual(view["source_schema"], "cbf-evidence/v1")
        self.assertEqual(view["evidence"]["evidence_sha256"], evidence.evidence_sha256)

    def test_verified_and_summary_quirk(self) -> None:
        self.assertEqual(CbfEvidence.from_dict(_doc()).hash_status, "verified")
        self.assertEqual(
            CbfEvidence.from_dict(_doc(with_summary=True)).hash_status,
            "verified_without_summary",
        )

    def test_tamper_is_reported_not_hidden(self) -> None:
        doc = _doc()
        doc["result"] = "BLOCK"
        evidence = CbfEvidence.from_dict(doc)
        self.assertEqual(evidence.hash_status, "mismatch")
        self.assertEqual(evidence.result, "BLOCK")
        with self.assertRaises(CbfEvidenceError):
            evidence.to_cbc_event(chain_id="c", seq=1)

    def test_unknown_schema_fails_closed(self) -> None:
        doc = _doc()
        doc["schema"] = "cbf-evidence/v2"
        with self.assertRaises(CbfEvidenceError):
            CbfEvidence.from_dict(doc)

    def test_to_cbc_event_is_valid_v2(self) -> None:
        evidence = CbfEvidence.from_dict(_doc(result="BLOCK"))
        event = evidence.to_cbc_event(
            chain_id="cbc-cbf-test",
            seq=1,
            prev_hash=GENESIS,
            source={"kind": "cbf", "name": "cbf", "version": "0.1.0", "instance": "ci"},
            identity={"package_id": "cbc", "producer_id": "cbf", "package_version": "0.2.0"},
        )
        errors, warnings = validate_event(event)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(event["schema"], "cbc-event/v2")
        self.assertEqual(event["event_type"], "gate")
        self.assertEqual(event["level"], "WARN")
        self.assertEqual(event["chain_id"], "cbc-cbf-test")
        self.assertEqual(event["event_hash"], compute_event_hash(GENESIS, event))
        self.assertTrue(event["evidence_hash"].startswith("sha256:"))

    def test_cli_view(self) -> None:
        from cbc_viewer import cli
        from io import StringIO
        import contextlib

        out = StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["cbf-evidence", "--evidence", str(FIXTURE)])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["source_schema"], "cbf-evidence/v1")
        self.assertEqual(data["result"], "PASS")


if __name__ == "__main__":
    unittest.main()


class CbfValidationEdges(unittest.TestCase):
    def test_invalid_documents_fail_closed(self) -> None:
        base = _doc()
        mutations = [
            lambda d: d.pop("tool"),
            lambda d: d.update(policy_sha256="bad"),
            lambda d: d.update(evidence_sha256="bad"),
            lambda d: d.update(result="UNKNOWN"),
            lambda d: d.update(findings="x"),
            lambda d: d.update(scanned=[]),
            lambda d: d.update(generated_at=""),
            lambda d: d.update(tool=1),
        ]
        for mutation in mutations:
            doc = json.loads(json.dumps(base))
            mutation(doc)
            with self.assertRaises(CbfEvidenceError):
                CbfEvidence.from_dict(doc)

    def test_load_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"
            with self.assertRaises(CbfEvidenceError):
                load_cbf_evidence(missing)
            bad = Path(tmp) / "bad.json"
            bad.write_text("{bad", encoding="utf-8")
            with self.assertRaises(CbfEvidenceError):
                load_cbf_evidence(bad)

    def test_conversion_validation_and_defaults(self) -> None:
        evidence = CbfEvidence.from_dict(_doc())
        for kwargs in (
            {"chain_id": "", "seq": 1},
            {"chain_id": "c", "seq": 0},
            {"chain_id": "c", "seq": True},
            {"chain_id": "c", "seq": 1, "prev_hash": "bad"},
        ):
            with self.assertRaises(CbfEvidenceError):
                evidence.to_cbc_event(**kwargs)
        event = evidence.to_cbc_event(chain_id="c", seq=2, timestamp="2026-01-01T00:00:00Z")
        self.assertEqual(event["seq"], 2)
        self.assertEqual(event["timestamp"], "2026-01-01T00:00:00Z")
        self.assertEqual(event["identity"]["producer_id"], "cbf")

    def test_conversion_safe_project_and_version(self) -> None:
        doc = _doc()
        doc["project"] = "Not A Valid Project!"
        doc["version"] = "v1"
        doc["evidence_sha256"] = __import__("hashlib").sha256(
            __import__("cbc_event.canonical", fromlist=["canonical_bytes"]).canonical_bytes(
                {k: v for k, v in doc.items() if k != "evidence_sha256"}
            )
        ).hexdigest()
        event = CbfEvidence.from_dict(doc).to_cbc_event(chain_id="c", seq=1)
        self.assertEqual(event["identity"]["package_id"], "cbf")
        self.assertEqual(event["identity"]["package_version"], "0.1.0")
        self.assertEqual(event["source"]["version"], "0.1.0")

    def test_error_result_is_critical(self) -> None:
        evidence = CbfEvidence.from_dict(_doc(result="ERROR"))
        event = evidence.to_cbc_event(chain_id="c", seq=1)
        self.assertEqual(event["level"], "CRITICAL")

    def test_invalid_timestamp_is_rejected_or_normalized(self) -> None:
        import hashlib
        from cbc_event.canonical import canonical_bytes
        doc = _doc()
        doc["generated_at"] = "not-a-time"
        doc["evidence_sha256"] = hashlib.sha256(
            canonical_bytes({k: v for k, v in doc.items() if k != "evidence_sha256"})
        ).hexdigest()
        event = CbfEvidence.from_dict(doc).to_cbc_event(chain_id="c", seq=1)
        self.assertEqual(event["schema"], "cbc-event/v2")
        with self.assertRaises(CbfEvidenceError):
            CbfEvidence.from_dict(_doc()).to_cbc_event(
                chain_id="c", seq=1, timestamp="not-a-time"
            )
