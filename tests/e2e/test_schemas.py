"""Schema and report-shape checks (no third-party jsonschema dependency)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbc_viewer.verify import verify_release
from tests.e2e.fixtures import make_release

ROOT = Path(__file__).resolve().parents[2]


class SchemaTests(unittest.TestCase):
    def test_report_schema_has_frozen_evidence_fields(self) -> None:
        schema = json.loads((ROOT / "schemas" / "cbc-report.schema.json").read_text(encoding="utf-8"))
        required = set(schema["required"])
        for field in ("cbc_chain_status", "root_hash", "link_count", "broken_link", "upload_status"):
            self.assertIn(field, required)
        self.assertIn("NOT_UPLOADED", schema["properties"]["gate_status"]["enum"])
        self.assertEqual(set(schema["properties"]["upload_status"]["enum"]), {"UPLOADED", "NOT_UPLOADED"})

    def test_chain_schema_has_both_scopes(self) -> None:
        schema = json.loads((ROOT / "schemas" / "cbc-chain.schema.json").read_text(encoding="utf-8"))
        self.assertIn("release", schema["$defs"])
        self.assertIn("eventLog", schema["$defs"])
        self.assertIn("links", schema["$defs"]["release"]["required"])
        self.assertIn("files", schema["$defs"]["eventLog"]["required"])

    def test_actual_reports_match_schema_shape(self) -> None:
        report_schema = json.loads((ROOT / "schemas" / "cbc-report.schema.json").read_text(encoding="utf-8"))
        allowed = set(report_schema["properties"])
        required = set(report_schema["required"])
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            release = verify_release(paths["release"]).report
        self.assertEqual(set(release), allowed)
        self.assertTrue(required <= set(release))
        self.assertEqual(release["package_id"], "cbc")

    def test_chain_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            manifest = json.loads(paths["chain"].read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "schemas" / "cbc-chain.schema.json").read_text(encoding="utf-8"))
        release = schema["$defs"]["release"]
        self.assertTrue(set(release["required"]) <= set(manifest))
        self.assertEqual(manifest["links"][0]["kind"], "manifest")
        link = manifest["links"][0]
        self.assertTrue(set(schema["$defs"]["releaseLink"]["required"]) <= set(link))
        self.assertIn("manifest", schema["$defs"]["releaseLink"]["properties"]["kind"]["enum"])


if __name__ == "__main__":
    unittest.main()
