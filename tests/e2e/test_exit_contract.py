"""CBC-E2E-S01..S16: input, upstream, skip, and exit-code contract."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbc_viewer.verify import verify_release
from tests.e2e.fixtures import make_release, reseal, rewrite_cbe, rewrite_cbp


class ExitContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_release(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _verify(self):
        return verify_release(self.paths["release"])

    def test_s01_missing_cbe_is_input_2(self) -> None:
        self.paths["cbe"].unlink()
        result = self._verify()
        self.assertEqual(result.exit_code, 2)
        self.assertIn("input", result.report["upload_blocked_reason"])

    def test_s02_malformed_cbe_is_input_2(self) -> None:
        self.paths["cbe"].write_text("{not json", encoding="utf-8")
        result = self._verify()
        self.assertEqual(result.exit_code, 2)

    def test_s03_cbe_fail_is_3(self) -> None:
        rewrite_cbe(self.paths, gate_status="FAIL", exit_code=3)
        reseal(self.paths, gate_status="FAIL")
        result = self._verify()
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["gate_status"], "FAIL")
        self.assertEqual(result.report["cbc_chain_status"], "PASS")

    def test_s04_cbp_fail_is_3(self) -> None:
        rewrite_cbp(self.paths, gate_status="FAIL")
        reseal(self.paths, gate_status="FAIL")
        result = self._verify()
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["gate_status"], "FAIL")

    def test_s05_cbe_skipped_infra_is_3(self) -> None:
        rewrite_cbe(self.paths, gate_status="SKIPPED_INFRA", exit_code=3)
        reseal(self.paths, gate_status="SKIPPED_INFRA")
        result = self._verify()
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["gate_status"], "SKIPPED_INFRA")

    def test_s06_cbp_skipped_infra_is_3(self) -> None:
        rewrite_cbp(self.paths, gate_status="SKIPPED_INFRA")
        reseal(self.paths, gate_status="SKIPPED_INFRA")
        result = self._verify()
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["gate_status"], "SKIPPED_INFRA")

    def test_s07_skip_025_is_4(self) -> None:
        rewrite_cbe(self.paths, gate_status="FAIL", exit_code=4, applicable_count=4,
                    skip_count=1, skip_ratio=0.25)
        reseal(self.paths, gate_status="FAIL")
        result = self._verify()
        self.assertEqual(result.exit_code, 4)
        self.assertEqual(result.report["gate_status"], "FAIL")

    def test_s08_skip_exactly_020_passes(self) -> None:
        rewrite_cbe(self.paths, applicable_count=5, skip_count=1, skip_ratio=0.2)
        reseal(self.paths)
        result = self._verify()
        self.assertEqual(result.exit_code, 0)

    def test_s09_skip_02000001_is_4(self) -> None:
        rewrite_cbe(self.paths, gate_status="FAIL", exit_code=4, applicable_count=10_000_000,
                    skip_count=2_000_001, skip_ratio=0.2000001)
        reseal(self.paths, gate_status="FAIL")
        result = self._verify()
        self.assertEqual(result.exit_code, 4)

    def test_s10_blocking_skip_is_3(self) -> None:
        rewrite_cbe(self.paths, gate_status="FAIL", exit_code=3, applicable_count=5,
                    skip_count=1, skip_ratio=0.2, blocking_skip=True)
        reseal(self.paths, gate_status="FAIL")
        result = self._verify()
        self.assertEqual(result.exit_code, 3)

    def test_s11_cbp_skipped_without_reason_is_2(self) -> None:
        gates = [{"name": "encoding", "status": "SKIPPED", "reason": ""}]
        rewrite_cbp(self.paths, gates=gates)
        reseal(self.paths)
        result = self._verify()
        self.assertEqual(result.exit_code, 2)

    def test_s12_cbe_exit_3_without_status_is_2(self) -> None:
        cbe = json.loads(self.paths["cbe"].read_text(encoding="utf-8"))
        del cbe["gate_status"]
        self.paths["cbe"].write_text(json.dumps(cbe), encoding="utf-8")
        reseal(self.paths)
        result = self._verify()
        self.assertEqual(result.exit_code, 2)

    def test_s13_pass_with_exit_3_is_2(self) -> None:
        rewrite_cbe(self.paths, gate_status="PASS", exit_code=3)
        reseal(self.paths)
        result = self._verify()
        self.assertEqual(result.exit_code, 2)

    def test_s14_zero_applicable_is_2(self) -> None:
        rewrite_cbe(self.paths, applicable_count=0, skip_count=0, skip_ratio=0.0)
        reseal(self.paths)
        result = self._verify()
        self.assertEqual(result.exit_code, 2)

    def test_s15_ratio_mismatch_is_2(self) -> None:
        rewrite_cbe(self.paths, applicable_count=4, skip_count=0, skip_ratio=0.1)
        reseal(self.paths)
        result = self._verify()
        self.assertEqual(result.exit_code, 2)

    def test_s16_version_mismatch_is_2(self) -> None:
        rewrite_cbe(self.paths, version="v9.9.9")
        reseal(self.paths)
        result = self._verify()
        self.assertEqual(result.exit_code, 2)


if __name__ == "__main__":
    unittest.main()
