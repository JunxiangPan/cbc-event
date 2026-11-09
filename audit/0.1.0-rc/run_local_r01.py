#!/usr/bin/env python3
"""R01 against a one-off local release test index.

This is NOT a GitHub release and does not claim a public upload. It serves the
real CBC body and real wheel/sdist from a local transport so the R01
``clean uploaded`` code path can be exercised with real bytes.

Run from ``audit/0.1.0-rc``:
    PYTHONPATH=../.. python run_local_r01.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[1]))

from cbc_viewer.verify import verify_release  # noqa: E402
from run_real_cases import WHEEL, SDIST, build_base  # noqa: E402


class LocalReleaseTransport:
    """A local, one-shot release index; no network and no GitHub claim."""

    def __init__(self, body: bytes, assets: list[dict]) -> None:
        self.body = body
        self.assets = assets
        self.calls: list[str] = []

    def get_release(self, owner: str, repo: str, tag: str) -> dict:
        self.calls.append("get_release")
        return {"body": self.body.decode("utf-8"), "assets": self.assets}

    def get_tag_commit(self, owner: str, repo: str, tag: str) -> str | None:
        self.calls.append("get_tag_commit")
        return None


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cbc-local-r01-") as tmp:
        paths = build_base(Path(tmp))
        manifest = json.loads(paths["chain"].read_text(encoding="utf-8"))
        body = paths["body"].read_bytes()
        assets = []
        for link in manifest["links"]:
            if link["kind"] != "asset":
                continue
            name = link["name"]
            path = paths["release"] / name
            assets.append({
                "name": name,
                "size": path.stat().st_size,
                "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        transport = LocalReleaseTransport(body, assets)
        result = verify_release(
            paths["release"], remote="local/test-index", transport=transport
        )
        summary = {
            "scope": "local test index, not GitHub",
            "manifest_sha256": hashlib.sha256(paths["cbp"].read_bytes()).hexdigest(),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "assets": assets,
            "exit_code": result.exit_code,
            "gate_status": result.report["gate_status"],
            "cbc_chain_status": result.report["cbc_chain_status"],
            "upload_status": result.report["upload_status"],
            "root_hash": result.report["root_hash"],
            "link_count": result.report["link_count"],
            "asset_link_count": result.report["asset_link_count"],
            "anchor_scope": result.report["anchor_scope"],
        }
        (BASE / "local_r01_result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0 if (
            result.exit_code == 0
            and result.report["gate_status"] == "PASS"
            and result.report["upload_status"] == "UPLOADED"
        ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
