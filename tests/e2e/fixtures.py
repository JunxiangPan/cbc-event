"""Fixtures for CBC release-chain E2E tests.

A fixture is built in a deliberately non-circular order:

1. assets + gate reports + base body;
2. CBP hashes the base body;
3. the chain hashes the assets, reports, and control files;
4. the CBC appendix (with the chain root) is appended to the base body.

Tests may re-seal after editing a report so the chain is internally consistent
and the intended check (status/skip/cross-check) is the one that fires.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cbc_viewer.body import render_appendix
from cbc_viewer.chain import build_manifest

VERSION = "v0.1.0"
TAG = "v0.1.0"
WHEEL = "cbc-0.1.0-py3-none-any.whl"
SDIST = "cbc-0.1.0.tar.gz"


def _hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_body(*, not_uploaded: bool, declared: bool) -> bytes:
    lines = [
        "# cbc v0.1.0 — Release evidence",
        "",
        "## Section A: Gate evidence (blocking)",
        "",
        "- gate_status: **PASS**",
        "",
        "## NOT_UPLOADED",
        "",
    ]
    if not_uploaded:
        lines.append("- cbc: declared as attached but not uploaded" if declared else "- cbc: NOT_UPLOADED (not attached)")
    else:
        lines.append("- none")
    lines += ["", "## Honesty boundary", "", "CBE verifies the rule framework, CBP verifies evidence coherence."]
    return ("\n".join(lines) + "\n").encode("utf-8")


def make_cbe(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1",
        "package_id": "cbe",
        "version": VERSION,
        "tag": TAG,
        "gate_status": "PASS",
        "exit_code": 0,
        "applicable_count": 5,
        "skip_count": 0,
        "skip_ratio": 0.0,
        "blocking_skip": False,
        "warn_count": 0,
        "rules_manifest_hash": "a" * 64,
        "sarif_paths": [],
        "evidence_sha256": "b" * 64,
    }
    value.update(overrides)
    return value


def make_cbp(*, base: bytes, wheel_hash: str, **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1",
        "package_id": "cbp",
        "version": VERSION,
        "gate_status": "PASS",
        "applicable_gate_count": 4,
        "skip_count": 0,
        "skip_ratio": 0.0,
        "blocking_skip": False,
        "gates": [
            {"name": "encoding", "status": "PASS", "reason": ""},
            {"name": "claims", "status": "PASS", "reason": ""},
            {"name": "binary", "status": "PASS", "reason": ""},
            {"name": "docs", "status": "PASS", "reason": ""},
        ],
        "artifact_hashes": {"wheel": wheel_hash},
        "release_body_hash": _hex(base),
        "body_hash_scope": "base",
        "evidence_sha256": "c" * 64,
    }
    value.update(overrides)
    return value


def write_appendix(paths: dict[str, Path], *, status: str = "PASS", gate_status: str = "PASS",
                   upload: str = "NOT_UPLOADED", declared: bool = False,
                   broken: dict[str, Any] | None = None, verified: int | None = None,
                   blocked: str | None = "not_uploaded") -> None:
    manifest = json.loads(paths["chain"].read_text(encoding="utf-8"))
    report = {
        "cbc_chain_status": status,
        "gate_status": gate_status,
        "root_hash": manifest["root_hash"],
        "declared_root_hash": manifest["root_hash"],
        "link_count": manifest["link_count"],
        "verified_link_count": verified if verified is not None else manifest["link_count"],
        "broken_link": broken,
        "upload_status": upload,
        "upload_blocked_reason": blocked,
        "declared_attached": declared,
    }
    base = paths["body"].read_bytes().split(b"<!-- CBC-EVIDENCE-BEGIN -->", 1)[0]
    paths["body"].write_bytes(base + render_appendix(report).encode("utf-8"))


def make_release(tmp: Path, *, declared: bool = False, uploaded: bool = False) -> dict[str, Path]:
    release = tmp / "release"
    release.mkdir(parents=True, exist_ok=True)
    wheel = release / WHEEL
    sdist = release / SDIST
    wheel.write_bytes(b"wheel-bytes")
    sdist.write_bytes(b"sdist-bytes")
    wheel_hash = _hex(wheel.read_bytes())
    sdist_hash = _hex(sdist.read_bytes())

    cbe_path = release / "cbe-report.json"
    cbp_path = release / "quality-manifest.json"
    _write_json(cbe_path, make_cbe())

    base = _base_body(not_uploaded=not uploaded, declared=declared)
    body_path = release / "RELEASE_BODY.md"
    body_path.write_bytes(base)
    _write_json(cbp_path, make_cbp(base=base, wheel_hash=wheel_hash))

    (release / "RELEASE_ASSETS.sha256").write_text(
        f"{wheel_hash}  {WHEEL}\n{sdist_hash}  {SDIST}\n", encoding="utf-8"
    )
    (release / "WHEEL_SHA256").write_text(f"{wheel_hash}  {WHEEL}\n", encoding="utf-8")

    manifest = build_manifest(release, version=VERSION, tag=TAG)
    (release / "cbc-chain.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    paths = {
        "release": release,
        "cbe": cbe_path,
        "cbp": cbp_path,
        "chain": release / "cbc-chain.json",
        "body": body_path,
        "wheel": wheel,
        "sdist": sdist,
        "assets_manifest": release / "RELEASE_ASSETS.sha256",
        "wheel_sha": release / "WHEEL_SHA256",
    }
    write_appendix(paths, status="PASS", gate_status="NOT_UPLOADED" if not uploaded else "PASS",
                   upload="UPLOADED" if uploaded else "NOT_UPLOADED", declared=declared,
                   blocked="not_uploaded")
    return paths


def reseal(paths: dict[str, Path], *, status: str = "PASS", gate_status: str = "PASS",
           upload: str = "NOT_UPLOADED", declared: bool = False,
           broken: dict[str, Any] | None = None, verified: int | None = None,
           blocked: str | None = "not_uploaded") -> dict[str, Any]:
    manifest = build_manifest(paths["release"], version=VERSION, tag=TAG)
    paths["chain"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_appendix(paths, status=status, gate_status=gate_status, upload=upload,
                   declared=declared, broken=broken, verified=verified, blocked=blocked)
    return manifest


def rewrite_cbe(paths: dict[str, Path], **overrides: Any) -> None:
    _write_json(paths["cbe"], make_cbe(**overrides))


def rewrite_cbp(paths: dict[str, Path], **overrides: Any) -> None:
    base = paths["body"].read_bytes().split(b"<!-- CBC-EVIDENCE-BEGIN -->", 1)[0]
    wheel_hash = _hex(paths["wheel"].read_bytes())
    _write_json(paths["cbp"], make_cbp(base=base, wheel_hash=wheel_hash, **overrides))
