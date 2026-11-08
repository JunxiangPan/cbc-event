"""CBC-E2E-R01..R17: release chain integrity and tamper detection."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from cbc_viewer.chain import GENESIS, parse_manifest, verify_artifacts
from cbc_viewer.verify import verify_release
from tests.e2e.fixtures import SDIST, WHEEL, make_release, reseal, rewrite_cbp


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


class FakeTransport:
    def __init__(self, release: dict) -> None:
        self.release = release
        self.calls: list[str] = []

    def get_release(self, owner: str, repo: str, tag: str) -> dict:
        self.calls.append("get_release")
        return self.release

    def get_tag_commit(self, owner: str, repo: str, tag: str) -> str | None:
        self.calls.append("get_tag_commit")
        return None


class ReleaseChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_release(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_r01_clean_uploaded(self) -> None:
        self.paths = make_release(Path(self.tmp.name), uploaded=True)
        release = {
            "body": self.paths["body"].read_text(encoding="utf-8"),
            "assets": [
                {"name": WHEEL, "digest": _digest(self.paths["wheel"])},
                {"name": SDIST, "digest": _digest(self.paths["sdist"])},
            ],
        }
        result = verify_release(self.paths["release"], remote="owner/repo", transport=FakeTransport(release))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report["gate_status"], "PASS")
        self.assertEqual(result.report["upload_status"], "UPLOADED")
        self.assertEqual(result.report["cbc_chain_status"], "PASS")

    def test_r02_clean_not_uploaded(self) -> None:
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report["gate_status"], "NOT_UPLOADED")
        self.assertEqual(result.report["cbc_chain_status"], "PASS")
        self.assertEqual(result.report["upload_status"], "NOT_UPLOADED")

    def test_r03_replaced_asset(self) -> None:
        self.paths["wheel"].write_bytes(b"tampered")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["cbc_chain_status"], "FAIL")
        self.assertEqual(result.report["broken_link"]["reason"], "hash_mismatch")

    def test_r04_extra_asset(self) -> None:
        (self.paths["release"] / "evil.bin").write_bytes(b"extra")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "unexpected_asset")

    def test_r05_missing_asset(self) -> None:
        self.paths["sdist"].unlink()
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "missing_asset")

    def test_r06_manifest_missing_entry(self) -> None:
        manifest = parse_manifest(json.loads(self.paths["chain"].read_text(encoding="utf-8")))
        wheel_hex = self.paths["wheel"].read_bytes()
        # Rewrite the checksum manifest without rebuilding the chain: the chain
        # still carries the sdist link, so the cross-check must name it.
        self.paths["assets_manifest"].write_text(
            f"{hashlib.sha256(wheel_hex).hexdigest()}  {WHEEL}\n", encoding="utf-8"
        )
        cbp = json.loads(self.paths["cbp"].read_text(encoding="utf-8"))
        broken = verify_artifacts(manifest, self.paths["release"], cbp)
        self.assertIsNotNone(broken)
        self.assertEqual(broken.reason, "manifest_entry_missing")

    def test_r07_cbp_manifest_conflict(self) -> None:
        rewrite_cbp(self.paths, artifact_hashes={"wheel": "0" * 64})
        reseal(self.paths, upload="NOT_UPLOADED")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "manifest_conflict")

    def test_r08_wheel_sha_mismatch(self) -> None:
        self.paths["wheel_sha"].write_text(f"{'0' * 64}  {WHEEL}\n", encoding="utf-8")
        reseal(self.paths, upload="NOT_UPLOADED")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "hash_mismatch")

    def test_r09_body_base_rewritten(self) -> None:
        data = self.paths["body"].read_bytes()
        self.paths["body"].write_bytes(data.replace(b"# cbc v0.1.0", b"# cbc v0.1.1", 1))
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["cbc_chain_status"], "FAIL")
        self.assertEqual(result.report["broken_link"]["reason"], "body_hash_mismatch")

    def test_r10_body_appendix_rewritten(self) -> None:
        data = self.paths["body"].read_bytes()
        self.paths["body"].write_bytes(data.replace(b"upload_status: **NOT_UPLOADED**", b"upload_status: **UPLOADED**", 1))
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["cbc_chain_status"], "FAIL")
        self.assertEqual(result.report["broken_link"]["reason"], "body_anchor_mismatch")

    def test_r11_link_hash_rewritten(self) -> None:
        manifest = json.loads(self.paths["chain"].read_text(encoding="utf-8"))
        manifest["links"][0]["link_hash"] = "0" * 64
        self.paths["chain"].write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_hash_mismatch")

    def test_r12_root_rewritten(self) -> None:
        manifest = json.loads(self.paths["chain"].read_text(encoding="utf-8"))
        manifest["root_hash"] = "0" * 64
        self.paths["chain"].write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_root_mismatch")

    def test_r13_index_gap(self) -> None:
        manifest = json.loads(self.paths["chain"].read_text(encoding="utf-8"))
        manifest["links"][1]["index"] = 3
        self.paths["chain"].write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_seq_gap")

    def test_r14_duplicate_link(self) -> None:
        manifest = json.loads(self.paths["chain"].read_text(encoding="utf-8"))
        manifest["links"][1]["name"] = manifest["links"][0]["name"]
        self.paths["chain"].write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "chain_duplicate")

    def test_r15_unsafe_name(self) -> None:
        manifest = json.loads(self.paths["chain"].read_text(encoding="utf-8"))
        manifest["links"][0]["name"] = "../evil.json"
        self.paths["chain"].write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "unsafe_name")

    def test_r16_symlink(self) -> None:
        target = self.paths["wheel"]
        target.unlink()
        try:
            os.symlink(self.paths["sdist"], target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not permitted on this platform")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "unsafe_symlink")

    def test_r17_empty_chain(self) -> None:
        manifest = json.loads(self.paths["chain"].read_text(encoding="utf-8"))
        manifest["links"] = []
        manifest["link_count"] = 0
        manifest["root_hash"] = GENESIS
        self.paths["chain"].write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.report["gate_status"], "FAIL")

    def test_r18_header_metadata_is_bound(self) -> None:
        manifest = json.loads(self.paths["chain"].read_text(encoding="utf-8"))
        manifest["source_commit"] = "a" * 40
        self.paths["chain"].write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["cbc_chain_status"], "FAIL")
        self.assertEqual(result.report["broken_link"]["reason"], "chain_hash_mismatch")


if __name__ == "__main__":
    unittest.main()
