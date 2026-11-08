"""CBC-E2E-D01..D05: determinism, no-bypass, and fail-closed behaviour."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from cbc_viewer.verify import verify_release
from tests.e2e.fixtures import make_release

CI = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


class DeterminismTests(unittest.TestCase):
    def test_d01_root_is_path_independent(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one = make_release(Path(first))
            two = make_release(Path(second))
            r1 = verify_release(one["release"])
            r2 = verify_release(two["release"])
            self.assertEqual(r1.report["root_hash"], r2.report["root_hash"])
            self.assertEqual(r1.report["link_count"], r2.report["link_count"])

    def test_d02_repeat_is_stable_except_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            first = verify_release(paths["release"]).report
            second = verify_release(paths["release"]).report
            a, b = copy.deepcopy(first), copy.deepcopy(second)
            a.pop("checked_at")
            b.pop("checked_at")
            self.assertEqual(a, b)

    def test_d03_no_silent_bypass_in_ci(self) -> None:
        text = CI.read_text(encoding="utf-8")
        self.assertNotIn("|| true", text)
        self.assertNotIn("continue-on-error", text)

    def test_d04_missing_top_level_inputs_are_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            for key in ("chain", "cbe", "cbp", "body", "assets_manifest", "wheel_sha"):
                with self.subTest(key=key):
                    paths = make_release(Path(tmp) / key)
                    paths[key].unlink()
                    result = verify_release(paths["release"])
                    self.assertEqual(result.exit_code, 2)
                    self.assertEqual(result.report["cbc_chain_status"], "FAIL")

    def test_d05_unconfirmed_upload_is_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            result = verify_release(paths["release"], expect_uploaded=True)
            self.assertEqual(result.report["gate_status"], "PRECONDITION_FAIL")
            self.assertNotEqual(result.report["gate_status"], "PASS")
            self.assertEqual(result.report["upload_status"], "NOT_UPLOADED")


if __name__ == "__main__":
    unittest.main()
