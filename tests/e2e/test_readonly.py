"""CBC-E2E-V01..V09: the viewer is read-only by construction and by AST audit."""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from cbc_viewer import cli
from cbc_viewer.errors import ReadOnlyViolation
from cbc_viewer.transport import ReadOnlyTransport
from cbc_viewer.verify import verify_release
from tests.e2e.fixtures import SDIST, WHEEL, make_release

VIEWER_ROOT = Path(__file__).resolve().parents[2] / "cbc_viewer"


class _FakeTransport:
    def __init__(self, release: dict) -> None:
        self.release = release
        self.calls: list[str] = []

    def get_release(self, owner: str, repo: str, tag: str) -> dict:
        self.calls.append("get_release")
        return self.release

    def get_tag_commit(self, owner: str, repo: str, tag: str) -> str | None:
        self.calls.append("get_tag_commit")
        return None


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ReadOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_release(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_v01_no_write_subcommands(self) -> None:
        parser = cli._build_parser()
        subparsers = next(
            action for action in parser._actions if hasattr(action, "choices") and action.choices
        )
        self.assertEqual(set(subparsers.choices), {"verify", "show", "render-body"})
        for forbidden in ("upload", "publish", "delete", "tag", "edit", "force", "release"):
            self.assertNotIn(forbidden, subparsers.choices)

    def test_v02_ast_audit(self) -> None:
        forbidden_attrs = {"post", "put", "patch", "delete", "remove", "unlink", "rename", "replace"}
        for path in VIEWER_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name, {"subprocess", "requests", "httpx"})
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], {"subprocess", "requests", "httpx"})
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    owner = node.func.value
                    if isinstance(owner, ast.Name) and owner.id in {"os", "shutil"}:
                        self.assertNotIn(node.func.attr, forbidden_attrs, f"{path.name}:{node.lineno}")
                    self.assertNotIn(node.func.attr, {"post", "put", "patch", "delete"})
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"post", "put", "patch", "delete"})
            if path.name != "cli.py":
                self.assertNotIn("write_text", path.read_text(encoding="utf-8"))

    def test_v03_transport_rejects_non_get(self) -> None:
        transport = ReadOnlyTransport()
        with self.assertRaises(ReadOnlyViolation):
            transport._request("POST", "https://api.github.com/")
        with self.assertRaises(ReadOnlyViolation):
            transport._request("DELETE", "https://api.github.com/")

    def test_v04_report_out_inside_release_is_rejected(self) -> None:
        target = self.paths["release"] / "report.json"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["verify", "--release-dir", str(self.paths["release"]),
                             "--report-out", str(target)])
        self.assertEqual(code, 2)
        self.assertFalse(target.exists())
        self.assertIn("CBC_VIEWER_ERROR", err.getvalue())

    def test_v05_source_tree_unchanged(self) -> None:
        before = _tree_hashes(self.paths["release"])
        verify_release(self.paths["release"])
        after = _tree_hashes(self.paths["release"])
        self.assertEqual(before, after)

    def test_v06_viewer_does_not_import_writer_api(self) -> None:
        for path in VIEWER_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "cbc_event":
                    names = {alias.name for alias in node.names}
                    self.assertFalse(names & {"Client", "EventStore", "emit"}, path.name)
                if isinstance(node, ast.Name):
                    self.assertNotIn(node.id, {"Client", "EventStore"})

    def test_v07_verify_never_calls_uploader(self) -> None:
        # The verifier has no uploader parameter; the CLI has no upload command.
        self.assertNotIn("upload", cli._build_parser().format_help().lower())
        result = verify_release(self.paths["release"])
        self.assertEqual(result.exit_code, 0)

    def test_v08_remote_check_is_get_only(self) -> None:
        self.paths = make_release(Path(self.tmp.name), uploaded=True)
        release = {
            "body": self.paths["body"].read_text(encoding="utf-8"),
            "assets": [
                {"name": WHEEL, "digest": "sha256:" + hashlib.sha256(self.paths["wheel"].read_bytes()).hexdigest()},
                {"name": SDIST, "digest": "sha256:" + hashlib.sha256(self.paths["sdist"].read_bytes()).hexdigest()},
            ],
        }
        fake = _FakeTransport(release)
        result = verify_release(self.paths["release"], remote="owner/repo", transport=fake)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(fake.calls, ["get_release"])

    def test_v09_event_verifier_never_repairs(self) -> None:
        from cbc_viewer.verify import verify_event_log_report
        event_dir = Path(self.tmp.name) / "events"
        event_dir.mkdir()
        target = event_dir / "2026-11-06.jsonl"
        target.write_text("{bad json}\n", encoding="utf-8")
        (event_dir / "head.json").write_text(
            '{"seq":1,"last_hash":"sha256:' + "0" * 64 + '","date":"2026-11-06"}',
            encoding="utf-8",
        )
        before = _tree_hashes(event_dir)
        result = verify_event_log_report(event_dir)
        after = _tree_hashes(event_dir)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
