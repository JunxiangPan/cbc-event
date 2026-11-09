"""CBC-E2E-F01..F10: F6 NOT_UPLOADED and all body fragments."""
from __future__ import annotations

import hashlib
import importlib.util
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from cbc_viewer import cli
from cbc_viewer.body import render_appendix, render_not_uploaded_entry
from cbc_viewer.verify import verify_release
from tests.e2e.fixtures import SDIST, WHEEL, make_release, reseal, rewrite_cbe

CBS_TOOL = Path(__file__).resolve().parents[3] / "public-release" / "tools" / "release_body_v17.py"


class _FakeTransport:
    def __init__(self, release: dict) -> None:
        self.release = release

    def get_release(self, owner: str, repo: str, tag: str) -> dict:
        return self.release

    def get_tag_commit(self, owner: str, repo: str, tag: str) -> str | None:
        return None


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


class F6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_f01_declared_attached_not_uploaded(self) -> None:
        paths = make_release(Path(self.tmp.name), declared=True)
        result = verify_release(paths["release"], declared_attached=True)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report["gate_status"], "NOT_UPLOADED")
        self.assertEqual(result.report["cbc_chain_status"], "PASS")
        self.assertEqual(result.report["upload_status"], "NOT_UPLOADED")
        self.assertTrue(result.report["skip"]["not_counted_in_skip_ratio"])
        entry = render_not_uploaded_entry(result.report)
        self.assertIn("cbc: NOT_UPLOADED", entry)
        self.assertIn("declared as attached but not uploaded", entry)
        appendix = render_appendix(result.report)
        self.assertIn("declared as attached but not uploaded", appendix)
        self.assertIn("NOT a release PASS", appendix)

    def test_f02_not_declared_not_uploaded(self) -> None:
        paths = make_release(Path(self.tmp.name), declared=False)
        result = verify_release(paths["release"], declared_attached=False)
        entry = render_not_uploaded_entry(result.report)
        self.assertEqual(entry, "cbc: NOT_UPLOADED (not attached)")
        self.assertNotIn("declared as attached", entry)

    def test_f03_expect_uploaded_without_remote_is_2(self) -> None:
        paths = make_release(Path(self.tmp.name))
        result = verify_release(paths["release"], expect_uploaded=True)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.report["gate_status"], "PRECONDITION_FAIL")
        self.assertEqual(result.report["cbc_chain_status"], "PASS")
        self.assertEqual(result.report["upload_status"], "NOT_UPLOADED")

    def test_f04_remote_digest_unavailable_is_not_pass(self) -> None:
        paths = make_release(Path(self.tmp.name), uploaded=True)
        release = {
            "body": paths["body"].read_text(encoding="utf-8"),
            "assets": [{"name": WHEEL}, {"name": SDIST}],
        }
        result = verify_release(paths["release"], remote="owner/repo", transport=_FakeTransport(release))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report["upload_status"], "NOT_UPLOADED")
        self.assertIsNone(result.report["broken_link"])
        expect = verify_release(paths["release"], expect_uploaded=True,
                                remote="owner/repo", transport=_FakeTransport(release))
        self.assertEqual(expect.exit_code, 2)
        self.assertEqual(expect.report["gate_status"], "PRECONDITION_FAIL")

    def test_f05_cbs_body_generator_needs_no_change(self) -> None:
        if not CBS_TOOL.is_file():
            self.skipTest("CBS read-only checkout is not available")
        spec = importlib.util.spec_from_file_location("release_body_v17", CBS_TOOL)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        paths = make_release(Path(self.tmp.name), declared=True)
        report = {
            "version": "v0.1.0", "gate_status": "NOT_UPLOADED",
            "applicable_gate_count": 4, "skip_count": 0, "skip_ratio": 0.0,
            "blocking_skip": False, "gates": [{"name": "encoding", "status": "PASS"}],
            "not_uploaded": [render_not_uploaded_entry(verify_release(paths["release"], declared_attached=True).report)],
        }
        text = module.build(report, paths["wheel"])
        self.assertIn("## NOT_UPLOADED", text)
        self.assertIn("- cbc: NOT_UPLOADED — declared as attached but not uploaded", text)

    def test_f06_not_uploaded_not_in_skip_denominator(self) -> None:
        paths = make_release(Path(self.tmp.name))
        result = verify_release(paths["release"])
        skip = result.report["skip"]
        self.assertEqual(skip["cbe_skip_ratio"], 0.0)
        self.assertEqual(skip["cbp_skip_ratio"], 0.0)
        self.assertEqual(skip["effective_skip_ratio"], 0.0)
        self.assertTrue(skip["not_counted_in_skip_ratio"])
        self.assertNotIn("applicable_count", result.report)

    def test_f07_broken_chain_declared(self) -> None:
        paths = make_release(Path(self.tmp.name), declared=True)
        paths["wheel"].write_bytes(b"tampered")
        result = verify_release(paths["release"], declared_attached=True)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["gate_status"], "FAIL")
        self.assertEqual(result.report["cbc_chain_status"], "FAIL")
        self.assertEqual(result.report["upload_status"], "NOT_UPLOADED")
        self.assertEqual(result.report["upload_blocked_reason"], "chain_broken")
        self.assertEqual(result.report["broken_link"]["reason"], "hash_mismatch")
        entry = render_not_uploaded_entry(result.report)
        self.assertIn("cbc: NOT_UPLOADED", entry)
        self.assertIn("declared as attached but not uploaded", entry)
        self.assertIn("broken_link: #", entry)
        self.assertIn("cbc-0.1.0-py3-none-any.whl", entry)
        self.assertIn("— hash_mismatch", entry)
        self.assertNotIn("CBC PASS", entry)
        appendix = render_appendix(result.report)
        self.assertIn("## CBC chain failure", appendix)
        self.assertNotIn("- cbc_chain_status: **PASS**", appendix)
        self.assertIn("CBS main package is not blocked", appendix)

    def test_f08_broken_chain_not_declared(self) -> None:
        paths = make_release(Path(self.tmp.name), declared=False)
        paths["wheel"].write_bytes(b"tampered")
        result = verify_release(paths["release"], declared_attached=False)
        entry = render_not_uploaded_entry(result.report)
        self.assertIn("cbc: NOT_UPLOADED (not attached)", entry)
        self.assertIn("broken_link: #", entry)
        self.assertIn("hash_mismatch", entry)
        self.assertNotIn("declared as attached", entry)

    def test_f09_missing_remote_asset_expect_uploaded_is_2(self) -> None:
        paths = make_release(Path(self.tmp.name), uploaded=True)
        release = {
            "body": paths["body"].read_text(encoding="utf-8"),
            "assets": [{"name": WHEEL, "digest": _digest(paths["wheel"])}],
        }
        result = verify_release(paths["release"], expect_uploaded=True,
                                remote="owner/repo", transport=_FakeTransport(release))
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.report["gate_status"], "PRECONDITION_FAIL")

    def test_f10_pass_uploaded_and_skipped_infra_fragments(self) -> None:
        uploaded = make_release(Path(self.tmp.name) / "uploaded", uploaded=True)
        remote = {
            "body": uploaded["body"].read_text(encoding="utf-8"),
            "assets": [
                {"name": WHEEL, "digest": _digest(uploaded["wheel"])},
                {"name": SDIST, "digest": _digest(uploaded["sdist"])},
            ],
        }
        passed = verify_release(uploaded["release"], remote="owner/repo",
                                transport=_FakeTransport(remote))
        self.assertEqual(passed.report["upload_status"], "UPLOADED")
        appendix = render_appendix(passed.report)
        self.assertIn("## CBC evidence chain", appendix)
        self.assertIn("upload_status: **UPLOADED**", appendix)
        self.assertIn("cbc_chain_status: **PASS**", appendix)

        infra = make_release(Path(self.tmp.name) / "infra", declared=True)
        rewrite_cbe(infra, gate_status="SKIPPED_INFRA", exit_code=3)
        reseal(infra, gate_status="SKIPPED_INFRA")
        skipped = verify_release(infra["release"], declared_attached=True)
        self.assertEqual(skipped.report["gate_status"], "SKIPPED_INFRA")
        appendix = render_appendix(skipped.report)
        self.assertIn("## Infrastructure failures", appendix)
        self.assertIn("**SKIPPED_INFRA**", appendix)
        self.assertIn("upload_status: **NOT_UPLOADED**", appendix)
        entry = render_not_uploaded_entry(skipped.report)
        self.assertIn("cbc: NOT_UPLOADED", entry)
        self.assertIn("declared as attached but not uploaded", entry)
        self.assertIn("SKIPPED_INFRA", entry)

    def test_f12_pre_release_remote_tag(self) -> None:
        uploaded = make_release(Path(self.tmp.name) / "pre", uploaded=True)
        remote = {
            "body": uploaded["body"].read_text(encoding="utf-8"),
            "assets": [
                {"name": WHEEL, "digest": _digest(uploaded["wheel"])},
                {"name": SDIST, "digest": _digest(uploaded["sdist"])},
            ],
        }
        passed = verify_release(
            uploaded["release"],
            tag="v0.1.0-rc.1",
            remote="owner/repo",
            transport=_FakeTransport(remote),
            expect_uploaded=True,
        )
        self.assertEqual(passed.exit_code, 0)
        self.assertEqual(passed.report["gate_status"], "PASS")
        self.assertEqual(passed.report["upload_status"], "UPLOADED")
        self.assertEqual(passed.report["tag"], "v0.1.0")
        self.assertEqual(passed.report["inputs"]["remote_tag"], "v0.1.0-rc.1")

    def test_f11_render_body_cli_broken_chain(self) -> None:
        paths = make_release(Path(self.tmp.name), declared=True)
        paths["wheel"].write_bytes(b"tampered")
        result = verify_release(paths["release"], declared_attached=True)
        report_path = Path(self.tmp.name) / "report.json"
        report_path.write_text(json.dumps(result.report), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["render-body", "--report", str(report_path),
                             "--format", "cbs-not-uploaded-entry"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("cbc: NOT_UPLOADED", text)
        self.assertIn("declared as attached but not uploaded", text)
        self.assertIn("broken_link: #", text)
        self.assertIn("cbc-0.1.0-py3-none-any.whl", text)
        self.assertIn("— hash_mismatch", text)
        self.assertNotIn("CBC PASS", text)


if __name__ == "__main__":
    unittest.main()
