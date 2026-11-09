"""Unit edges for the viewer modules (in addition to the E2E matrix)."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cbc_viewer.body import BodyProblem, parse_anchor, render_appendix, render_not_uploaded_entry, split_body
from cbc_viewer.chain import (
    GENESIS,
    build_manifest,
    is_safe_name,
    normalize_hash,
    normalize_tag,
    normalize_version,
    parse_assets_manifest,
    parse_manifest,
    parse_wheel_digest,
    verify_artifacts,
    verify_links,
)
from cbc_viewer.errors import InfraError, InputError, NotFoundError
from cbc_viewer.event_chain import build_event_manifest, read_event_manifest, verify_event_log
from cbc_viewer.reports import canonical_body_sha256, hash_matches, load_gate_reports, resolve_identity, validate_cbe, validate_cbp
from cbc_viewer.transport import ReadOnlyTransport
from cbc_viewer.verify import _check_remote, verify_release
from tests.e2e.fixtures import SDIST, WHEEL, make_cbe, make_cbp, make_release


class ChainUnitTests(unittest.TestCase):
    def test_normalizers(self) -> None:
        self.assertEqual(normalize_hash("A" * 64), "sha256:" + "a" * 64)
        self.assertEqual(normalize_version("v1.2.3"), "1.2.3")
        self.assertEqual(normalize_tag("v1.2.3"), "v1.2.3")
        self.assertTrue(is_safe_name("a.whl"))
        self.assertFalse(is_safe_name("../x"))
        for value in ("", "x", "sha256:zz"):
            with self.assertRaises(InputError):
                normalize_hash(value)
        with self.assertRaises(InputError):
            normalize_version("1.2")
        with self.assertRaises(InputError):
            normalize_tag("1.2.3")

    def test_parse_manifest_shape_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            data = json.loads(paths["chain"].read_text(encoding="utf-8"))
            for mutation in (
                lambda d: d.pop("root_hash"),
                lambda d: d.update(schema="other"),
                lambda d: d.update(chain_scope="event-log"),
                lambda d: d.update(chain_profile="other"),
                lambda d: d.update(links=[]),
                lambda d: d.update(link_count=True),
                lambda d: d["links"][0].pop("sha256"),
                lambda d: d["links"][0].update(index=True),
                lambda d: d["links"][0].update(kind="other"),
            ):
                value = json.loads(json.dumps(data))
                mutation(value)
                with self.assertRaises(InputError):
                    parse_manifest(value)

    def test_manifest_file_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InputError):
                parse_manifest({"schema": "x"})
            with self.assertRaises(InputError):
                from cbc_viewer.chain import read_manifest
                read_manifest(Path(tmp) / "missing.json")
            (Path(tmp) / "bad.json").write_text("{bad", encoding="utf-8")
            with self.assertRaises(InputError):
                from cbc_viewer.chain import read_manifest
                read_manifest(Path(tmp) / "bad.json")

    def test_verify_links_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            data = json.loads(paths["chain"].read_text(encoding="utf-8"))
            manifest = parse_manifest(data)
            # invalid link hash format
            data["links"][0]["sha256"] = "not-a-hash"
            broken = verify_links(parse_manifest(data), paths["release"]).broken
            self.assertEqual(broken.reason, "chain_hash_mismatch")
            # size mismatch (link hash is stale, so hash fires first); set size
            data = json.loads(paths["chain"].read_text(encoding="utf-8"))
            data["links"][-1]["size"] = 1
            broken = verify_links(parse_manifest(data), paths["release"]).broken
            self.assertEqual(broken.reason, "chain_hash_mismatch")
            # declared count mismatch with intact links
            data = json.loads(paths["chain"].read_text(encoding="utf-8"))
            data["link_count"] = 99
            check = verify_links(parse_manifest(data), paths["release"])
            self.assertEqual(check.broken.reason, "chain_link_count_mismatch")
            # untracked directory
            (paths["release"] / "extra").mkdir()
            from cbc_viewer.chain import scan_untracked
            self.assertEqual(scan_untracked(manifest, paths["release"]).reason, "unexpected_asset")

    def test_assets_manifest_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "assets"
            for text in ("", "bad line\n", f"{'a' * 64}  ../x\n", f"{'a' * 64}  x\n{'b' * 64}  x\n"):
                target.write_text(text, encoding="utf-8")
                with self.assertRaises(InputError):
                    parse_assets_manifest(target)
            target.write_text(f"{'a' * 64}  {WHEEL}\n", encoding="utf-8")
            self.assertEqual(parse_assets_manifest(target)[WHEEL], "sha256:" + "a" * 64)
            wheel_sha = Path(tmp) / "wheel"
            for text in ("", "nope"):
                wheel_sha.write_text(text, encoding="utf-8")
                with self.assertRaises(InputError):
                    parse_wheel_digest(wheel_sha)
            with self.assertRaises(InputError):
                parse_wheel_digest(Path(tmp) / "missing")

    def test_build_manifest_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / "release"
            release.mkdir()
            with self.assertRaises(InputError):
                build_manifest(release, version="v1.0.0", tag="v1.0.0")
            with self.assertRaises(InputError):
                build_manifest(release, version="bad", tag="v1.0.0")

    def test_verify_artifacts_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            manifest = parse_manifest(json.loads(paths["chain"].read_text(encoding="utf-8")))
            cbp = json.loads(paths["cbp"].read_text(encoding="utf-8"))
            # checksum manifest lists an asset not in the chain
            paths["assets_manifest"].write_text(
                f"{'a' * 64}  other.whl\n", encoding="utf-8"
            )
            broken = verify_artifacts(manifest, paths["release"], cbp)
            self.assertEqual(broken.reason, "manifest_conflict")
            # restore and make artifact_hashes invalid
            paths["assets_manifest"].write_text(
                "".join(f"{digest[7:]}  {name}\n" for name, digest in manifest.assets().items()),
                encoding="utf-8",
            )
            cbp["artifact_hashes"] = {"wheel": "not-a-hash"}
            with self.assertRaises(InputError):
                verify_artifacts(manifest, paths["release"], cbp)


class BodyUnitTests(unittest.TestCase):
    def test_split_edges(self) -> None:
        self.assertEqual(split_body(b"x"), (b"x", None))
        for data in (
            b"<!-- CBC-EVIDENCE-BEGIN -->x",
            b"<!-- CBC-EVIDENCE-BEGIN -->x<!-- CBC-EVIDENCE-BEGIN -->y<!-- CBC-EVIDENCE-END -->",
            b"<!-- CBC-EVIDENCE-END -->x<!-- CBC-EVIDENCE-BEGIN -->",
            b"<!-- CBC-EVIDENCE-BEGIN -->x<!-- CBC-EVIDENCE-END -->tail",
        ):
            with self.assertRaises(BodyProblem):
                split_body(data)

    def test_parse_anchor_edges(self) -> None:
        good = render_appendix({"cbc_chain_status": "PASS", "root_hash": "sha256:" + "a" * 64,
                                "link_count": 1, "upload_status": "NOT_UPLOADED"})
        appendix = good.encode("utf-8").split(b"<!-- CBC-EVIDENCE-BEGIN -->", 1)[1].split(b"<!-- CBC-EVIDENCE-END -->", 1)[0]
        self.assertEqual(parse_anchor(appendix)["link_count"], 1)
        for data in (b"", b"\xff", b"<!-- cbc-evidence {bad} -->", b"<!-- cbc-evidence [] -->"):
            with self.assertRaises(BodyProblem):
                parse_anchor(data)
        # remove appendix hash
        broken = appendix.replace(b'"appendix_sha256":"sha256:', b'"x":"sha256:')
        with self.assertRaises(BodyProblem):
            parse_anchor(broken)

    def test_render_variants(self) -> None:
        base = {"root_hash": "sha256:" + "a" * 64, "link_count": 2, "upload_status": "NOT_UPLOADED",
                "declared_attached": True}
        fail = render_appendix({**base, "cbc_chain_status": "FAIL", "gate_status": "FAIL",
                                "broken_link": {"index": 1, "kind": "asset", "name": "x",
                                                "reason": "hash_mismatch", "expected": "a", "actual": "b",
                                                "detail": "d"}})
        self.assertIn("CBC chain failure", fail)
        self.assertIn("declared as attached but not uploaded", fail)
        infra = render_appendix({**base, "cbc_chain_status": "SKIPPED_INFRA", "gate_status": "SKIPPED_INFRA"})
        self.assertIn("SKIPPED_INFRA", infra)
        with self.assertRaises(BodyProblem):
            render_not_uploaded_entry({**base, "upload_status": "UPLOADED"})

    def test_render_not_uploaded_fail_and_infra(self) -> None:
        base = {"upload_status": "NOT_UPLOADED", "declared_attached": False,
                "cbc_chain_status": "FAIL", "broken_link": {"reason": "hash_mismatch", "index": 3, "name": "x"}}
        self.assertEqual(render_not_uploaded_entry(base),
                         "cbc: NOT_UPLOADED (not attached); broken_link: #3 x — hash_mismatch")
        self.assertIn("SKIPPED_INFRA", render_not_uploaded_entry({**base, "cbc_chain_status": "SKIPPED_INFRA"}))


class ReportUnitTests(unittest.TestCase):
    def test_cbe_validation_edges(self) -> None:
        good = make_cbe()
        validate_cbe(good)
        mutations = [
            lambda d: d.pop("tag"),
            lambda d: d.update(schema_version="2"),
            lambda d: d.update(version="x"),
            lambda d: d.update(tag="x"),
            lambda d: d.update(gate_status="OTHER"),
            lambda d: d.update(exit_code=1),
            lambda d: d.update(applicable_count=0),
            lambda d: d.update(skip_ratio=2),
            lambda d: d.update(skip_count=2),
            lambda d: d.update(blocking_skip="no"),
            lambda d: d.update(warn_count=-1),
            lambda d: d.update(rules_manifest_hash="x"),
            lambda d: d.update(sarif_paths=[1]),
            lambda d: d.update(evidence_sha256="x"),
            lambda d: d.update(gate_status="PASS", exit_code=3),
        ]
        for mutation in mutations:
            value = make_cbe()
            mutation(value)
            with self.assertRaises(InputError):
                validate_cbe(value)

    def test_cbp_validation_edges(self) -> None:
        base = b"body"
        good = make_cbp(base=base, wheel_hash="a" * 64)
        validate_cbp(good)
        mutations = [
            lambda d: d.pop("release_body_hash"),
            lambda d: d.update(schema_version="2"),
            lambda d: d.update(version="x"),
            lambda d: d.update(gate_status="OTHER"),
            lambda d: d.update(applicable_gate_count=0),
            lambda d: d.update(skip_ratio=2),
            lambda d: d.update(gates="x"),
            lambda d: d.update(gates=[{"name": "", "status": "PASS"}]),
            lambda d: d.update(gates=[{"name": "x", "status": "OTHER"}]),
            lambda d: d.update(gates=[{"name": "x", "status": "SKIPPED", "reason": ""}]),
            lambda d: d.update(artifact_hashes={"x": "bad"}),
            lambda d: d.update(artifact_repository="JunxiangPan/cbc-event"),
            lambda d: d.update(artifact_repository={"repository": "x", "run_id": "y"}),
            lambda d: d.update(artifact_repository={"repository": "x", "run_id": "y",
                                                    "artifact_name": "z", "extra": "x"}),
            lambda d: d.update(schema_version=1),
            lambda d: d.update(release_body_hash="bad"),
            lambda d: d.update(body_hash_scope="other"),
            lambda d: d.update(tag="bad"),
            lambda d: d.update(gate_status="PASS", skip_ratio=0.5, skip_count=2, applicable_gate_count=4),
        ]
        for mutation in mutations:
            value = make_cbp(base=base, wheel_hash="a" * 64)
            mutation(value)
            with self.assertRaises(InputError):
                validate_cbp(value)

    def test_canonical_body_hash(self) -> None:
        self.assertEqual(canonical_body_sha256(b"x\r\n\r\n"), canonical_body_sha256(b"x\n"))
        self.assertEqual(canonical_body_sha256(b"\xef\xbb\xbfx"), canonical_body_sha256(b"x"))
        self.assertTrue(hash_matches(canonical_body_sha256(b"x"), b"x\r\n\r\n"))

    def test_identity(self) -> None:
        cbe = make_cbe()
        cbp = make_cbp(base=b"x", wheel_hash="a" * 64)
        self.assertEqual(resolve_identity(cbe=cbe, cbp=cbp, chain_version="v0.1.0", chain_tag="v0.1.0"),
                         ("v0.1.0", "v0.1.0"))
        with self.assertRaises(InputError):
            resolve_identity(cbe=cbe, cbp=cbp, chain_version="v0.1.0", chain_tag="v0.1.1")
        with self.assertRaises(InputError):
            resolve_identity(cbe=make_cbe(version="v0.1.1"), cbp=cbp,
                             chain_version="v0.1.0", chain_tag="v0.1.0")
        self.assertFalse(hash_matches("bad", b"x"))

    def test_load_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            reports = load_gate_reports(paths["cbe"], paths["cbp"],
                                        chain_version="v0.1.0", chain_tag="v0.1.0")
            self.assertEqual(reports.version, "v0.1.0")
            with self.assertRaises(InputError):
                load_gate_reports(paths["cbe"], paths["cbp"], chain_version="v0.1.0", chain_tag="v0.1.1")


class EventUnitTests(unittest.TestCase):
    def test_event_manifest_edges(self) -> None:
        from tests.e2e.test_event_chain import make_events
        with tempfile.TemporaryDirectory() as tmp:
            _event_dir, manifest_path = make_events(Path(tmp))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            target = Path(tmp) / "event.json"
            for mutation in (
                lambda d: d.pop("head"),
                lambda d: d.update(schema="x"),
                lambda d: d.update(chain_scope="release"),
                lambda d: d.update(files=[]),
                lambda d: d.update(link_count=0),
            ):
                value = json.loads(json.dumps(manifest))
                mutation(value)
                target.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(InputError):
                    read_event_manifest(target)

    def test_build_event_manifest_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "head.json").write_text(
                '{"seq":1,"last_hash":"sha256:' + "0" * 64 + '"}', encoding="utf-8")
            with self.assertRaises(InputError):
                build_event_manifest(tmp)

    def test_event_manifest_head_hash_mismatch(self) -> None:
        from tests.e2e.test_event_chain import make_events
        with tempfile.TemporaryDirectory() as tmp:
            event_dir, manifest_path = make_events(Path(tmp))
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["head"]["sha256"] = "sha256:" + "0" * 64
            manifest_path.write_text(json.dumps(data), encoding="utf-8")
            check = verify_event_log(event_dir, manifest_path=manifest_path)
            self.assertEqual(check.broken.reason, "hash_mismatch")


class TransportUnitTests(unittest.TestCase):
    class _Response:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def read(self) -> bytes:
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def test_request_success_and_errors(self) -> None:
        transport = ReadOnlyTransport(timeout=0.01, retries=1)
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen", return_value=self._Response(b"{}")):
            self.assertEqual(transport._request("GET", "https://api.github.com/x"), b"{}")
        import urllib.error
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 404, "n", {}, io.BytesIO(b""))):
            with self.assertRaises(NotFoundError):
                transport._request("GET", "https://api.github.com/x")
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 401, "n", {}, io.BytesIO(b""))):
            with self.assertRaises(InfraError):
                transport._request("GET", "https://api.github.com/x")
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 500, "n", {}, io.BytesIO(b""))):
            with self.assertRaises(InfraError):
                transport._request("GET", "https://api.github.com/x")
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen", side_effect=OSError("no")):
            with self.assertRaises(InfraError):
                transport._request("GET", "https://api.github.com/x")

    def test_helpers(self) -> None:
        transport = ReadOnlyTransport(retries=1)
        with mock.patch.object(transport, "_get_json", return_value={"body": "x", "assets": []}):
            self.assertEqual(transport.get_release("o", "r", "v1.0.0")["body"], "x")
        with mock.patch.object(transport, "_get_json", return_value={"sha": "a" * 40}):
            self.assertEqual(transport.get_tag_commit("o", "r", "v1.0.0"), "a" * 40)
        with mock.patch.object(transport, "_get_json", return_value={"sha": "bad"}):
            self.assertIsNone(transport.get_tag_commit("o", "r", "v1.0.0"))
        with self.assertRaises(InputError):
            transport.get_release("bad/part", "r", "v1.0.0")
        with self.assertRaises(InputError):
            transport.get_asset_bytes({})

    def test_retry_and_json_edges(self) -> None:
        import urllib.error
        transport = ReadOnlyTransport(token="t", retries=2)
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=[urllib.error.HTTPError("u", 500, "n", {}, io.BytesIO(b"")),
                                     urllib.error.HTTPError("u", 500, "n", {}, io.BytesIO(b""))]), \
                mock.patch("cbc_viewer.transport.time.sleep"):
            with self.assertRaises(InfraError):
                transport._request("GET", "https://api.github.com/x")
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=[OSError("one"), self._Response(b"{}")]), \
                mock.patch("cbc_viewer.transport.time.sleep"):
            self.assertEqual(transport._request("GET", "https://api.github.com/x"), b"{}")
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 400, "n", {}, io.BytesIO(b""))):
            with self.assertRaises(InputError):
                transport._request("GET", "https://api.github.com/x")
        with mock.patch.object(transport, "_request", return_value=b"not json"):
            with self.assertRaises(InfraError):
                transport._get_json("/x")
        with mock.patch.object(transport, "_request", return_value=b"[]"):
            with self.assertRaises(InfraError):
                transport._get_json("/x")

    def test_asset_download_edges(self) -> None:
        import urllib.error
        transport = ReadOnlyTransport(token="t", retries=1)
        asset = {"url": "https://api.github.com/asset/1"}
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen", return_value=self._Response(b"data")):
            self.assertEqual(transport.get_asset_bytes(asset), b"data")
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 404, "n", {}, io.BytesIO(b""))):
            with self.assertRaises(NotFoundError):
                transport.get_asset_bytes(asset)
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 500, "n", {}, io.BytesIO(b""))):
            with self.assertRaises(InfraError):
                transport.get_asset_bytes(asset)
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 400, "n", {}, io.BytesIO(b""))):
            with self.assertRaises(InputError):
                transport.get_asset_bytes(asset)
        with mock.patch("cbc_viewer.transport.urllib.request.urlopen", side_effect=OSError("no")):
            with self.assertRaises(InfraError):
                transport.get_asset_bytes(asset)


class RemoteVerifyTests(unittest.TestCase):
    class _Transport:
        def __init__(self, release=None, commit=None, error=None) -> None:
            self.release = release
            self.commit = commit
            self.error = error
            self.calls: list[str] = []

        def get_release(self, owner: str, repo: str, tag: str) -> dict:
            self.calls.append("get_release")
            if self.error:
                raise self.error
            return self.release

        def get_tag_commit(self, owner: str, repo: str, tag: str) -> str | None:
            self.calls.append("get_tag_commit")
            return self.commit

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_release(Path(self.tmp.name), uploaded=True)
        self.manifest = parse_manifest(json.loads(self.paths["chain"].read_text(encoding="utf-8")))
        self.body = self.paths["body"].read_bytes()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _assets(self) -> list[dict]:
        return [
            {"name": WHEEL, "digest": "sha256:" + hashlib.sha256(self.paths["wheel"].read_bytes()).hexdigest()},
            {"name": SDIST, "digest": "sha256:" + hashlib.sha256(self.paths["sdist"].read_bytes()).hexdigest()},
        ]

    def _release(self, **overrides) -> dict:
        value = {"body": self.body.decode("utf-8"), "assets": self._assets()}
        value.update(overrides)
        return value

    def _check(self, release: dict):
        return _check_remote(self._Transport(release), "owner", "repo", "v0.1.0",
                             self.manifest, self.body)

    def test_remote_check_branches(self) -> None:
        self.assertEqual(self._check(self._release()).uploaded, True)
        self.assertEqual(self._check(self._release(body=None)).broken.reason, "body_anchor_missing")
        self.assertEqual(self._check(self._release(body="other")).broken.reason, "body_hash_mismatch")
        self.assertEqual(self._check(self._release(assets="x")).broken.reason, "report_invalid")
        self.assertEqual(self._check(self._release(assets=["x"])).broken.reason, "report_invalid")
        self.assertEqual(self._check(self._release(assets=[{}])).broken.reason, "report_invalid")
        self.assertEqual(self._check(self._release(assets=[{"name": WHEEL}, {"name": WHEEL}])).broken.reason, "chain_duplicate")
        self.assertEqual(self._check(self._release(assets=self._assets() + [{"name": "evil"}])).broken.reason, "unexpected_asset")
        missing = self._check(self._release(assets=self._assets()[:1]))
        self.assertFalse(missing.uploaded)
        self.assertEqual(missing.reason, "remote_asset_missing")
        bad_digest = self._assets()
        bad_digest[0]["digest"] = "sha256:" + "0" * 64
        self.assertEqual(self._check(self._release(assets=bad_digest)).broken.reason, "hash_mismatch")

    def test_remote_tag_mismatch(self) -> None:
        self.manifest.raw["source_commit"] = "a" * 40
        try:
            result = _check_remote(self._Transport(self._release(), commit="b" * 40),
                                   "owner", "repo", "v0.1.0", self.manifest, self.body)
        finally:
            self.manifest.raw.pop("source_commit", None)
        self.assertEqual(result.broken.reason, "tag_mismatch")

    def test_remote_not_found_and_infra(self) -> None:
        not_found = self._Transport(error=NotFoundError("missing"))
        result = verify_release(self.paths["release"], remote="owner/repo", transport=not_found)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report["upload_status"], "NOT_UPLOADED")
        expected = verify_release(self.paths["release"], expect_uploaded=True,
                                  remote="owner/repo", transport=not_found)
        self.assertEqual(expected.exit_code, 2)
        infra = self._Transport(error=InfraError("down"))
        result = verify_release(self.paths["release"], remote="owner/repo", transport=infra)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["gate_status"], "SKIPPED_INFRA")

    def test_remote_bad_name_and_body_mismatch(self) -> None:
        result = verify_release(self.paths["release"], remote="bad")
        self.assertEqual(result.exit_code, 2)
        bad = self._Transport(self._release(body="other"))
        result = verify_release(self.paths["release"], remote="owner/repo", transport=bad)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "body_hash_mismatch")

    def test_body_scope_and_anchor_failures(self) -> None:
        cbp = json.loads(self.paths["cbp"].read_text(encoding="utf-8"))
        cbp.pop("body_hash_scope")
        self.paths["cbp"].write_text(json.dumps(cbp), encoding="utf-8")
        from tests.e2e.fixtures import reseal
        reseal(self.paths, upload="UPLOADED")
        self.assertEqual(verify_release(self.paths["release"]).exit_code, 2)

        cbp["body_hash_scope"] = "full"
        self.paths["cbp"].write_text(json.dumps(cbp), encoding="utf-8")
        reseal(self.paths, upload="UPLOADED")
        self.assertEqual(verify_release(self.paths["release"]).exit_code, 2)

    def test_body_anchor_root_and_count_mismatch(self) -> None:
        from cbc_viewer.body import BEGIN
        from tests.e2e.fixtures import write_appendix
        base = self.body.split(BEGIN.encode("utf-8"), 1)[0]
        wrong_root = render_appendix({
            "cbc_chain_status": "PASS", "root_hash": "sha256:" + "0" * 64,
            "link_count": self.manifest.declared_link_count, "upload_status": "UPLOADED",
        })
        self.paths["body"].write_bytes(base + wrong_root.encode("utf-8"))
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "body_anchor_mismatch")

        correct_root = render_appendix({
            "cbc_chain_status": "PASS", "root_hash": self.manifest.declared_root,
            "link_count": 99, "upload_status": "UPLOADED",
        })
        self.paths["body"].write_bytes(base + correct_root.encode("utf-8"))
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.report["broken_link"]["reason"], "body_anchor_mismatch")


class CliUnitTests(unittest.TestCase):
    def test_show_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            report = Path(tmp) / "report.json"
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = __import__("cbc_viewer.cli", fromlist=["main"]).main(
                    ["verify", "--release-dir", str(paths["release"]), "--json", "--report-out", str(report)]
                )
            self.assertEqual(code, 0)
            self.assertTrue(report.is_file())
            with contextlib.redirect_stdout(out):
                self.assertEqual(__import__("cbc_viewer.cli", fromlist=["main"]).main(
                    ["show", "--report", str(report)]), 0)
                self.assertEqual(__import__("cbc_viewer.cli", fromlist=["main"]).main(
                    ["render-body", "--report", str(report), "--format", "appendix"]), 0)
                self.assertEqual(__import__("cbc_viewer.cli", fromlist=["main"]).main(
                    ["render-body", "--report", str(report), "--format", "cbs-not-uploaded-entry"]), 0)
            with contextlib.redirect_stderr(err):
                self.assertEqual(__import__("cbc_viewer.cli", fromlist=["main"]).main(
                    ["show", "--report", str(Path(tmp) / "missing.json")]), 2)

    def test_verify_event_scope_and_missing_dir(self) -> None:
        from tests.e2e.test_event_chain import make_events
        with tempfile.TemporaryDirectory() as tmp:
            event_dir, manifest_path = make_events(Path(tmp))
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = __import__("cbc_viewer.cli", fromlist=["main"]).main(
                    ["verify", "--scope", "event-log", "--event-dir", str(event_dir),
                     "--chain", str(manifest_path)]
                )
                missing = __import__("cbc_viewer.cli", fromlist=["main"]).main(
                    ["verify", "--scope", "release", "--release-dir", str(Path(tmp) / "nope")]
                )
            self.assertEqual(code, 0)
            self.assertEqual(missing, 2)

    def test_report_overwrite_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_release(Path(tmp))
            report = Path(tmp) / "report.json"
            report.write_text("{}", encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                cli = __import__("cbc_viewer.cli", fromlist=["main"])
                self.assertEqual(cli.main(["verify", "--release-dir", str(paths["release"]),
                                           "--report-out", str(report)]), 2)
                self.assertEqual(cli.main(["verify", "--release-dir", str(paths["release"]),
                                           "--report-out", str(report), "--force"]), 0)


if __name__ == "__main__":
    unittest.main()
