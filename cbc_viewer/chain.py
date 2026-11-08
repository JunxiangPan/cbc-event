"""CBC release hash chain: manifest shape, link hashing, and verification.

The chain covers the two gate reports, the build control files, and every
release asset listed by ``RELEASE_ASSETS.sha256``.  The release body is not a
link: its base bytes are hashed by CBP, and the CBC appendix binds the chain
root (see ``body.py`` and ``docs/release-chain.md``).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cbc_event.canonical import canonical_bytes

from .errors import BrokenLink, InputError

GENESIS = "sha256:" + ("0" * 64)
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
VERSION_RE = re.compile(r"^v?[0-9]+\.[0-9]+\.[0-9]+$")
TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
SAFE_NAME_RE = re.compile(r"^[^/\\\x00]+$")

LINK_KINDS = {"manifest", "gate_report", "control", "asset"}
HEADER_FIELDS = (
    "schema",
    "chain_scope",
    "chain_profile",
    "package_id",
    "version",
    "tag",
    "body_hash_scope",
    "source_commit",
)
RELEASE_ALLOWLIST = {
    "RELEASE_BODY.md",
    "cbc-chain.json",
    "cbc-chain-report.json",
    "CBC_BODY_BLOCK.md",
}
REQUIRED_MANIFEST_FIELDS = (
    "schema",
    "chain_scope",
    "chain_profile",
    "package_id",
    "version",
    "tag",
    "canonicalization",
    "hash_alg",
    "genesis",
    "link_count",
    "root_hash",
    "links",
)
REQUIRED_LINK_FIELDS = (
    "index",
    "kind",
    "role",
    "name",
    "sha256",
    "size",
    "prev_hash",
    "link_hash",
)


def normalize_hash(value: str) -> str:
    """Return a lowercase ``sha256:<64-hex>`` value, or raise InputError."""
    if not isinstance(value, str):
        raise InputError("hash must be a string")
    text = value.strip()
    if text.lower().startswith("sha256:"):
        text = text[7:]
    if not HEX_RE.fullmatch(text):
        raise InputError(f"invalid sha256 value: {value!r}")
    return "sha256:" + text.lower()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def normalize_version(value: str) -> str:
    if not isinstance(value, str) or not VERSION_RE.fullmatch(value.strip()):
        raise InputError(f"invalid version: {value!r}")
    return value.strip().lstrip("v") if value.strip().startswith("v") else value.strip()


def normalize_tag(value: str) -> str:
    if not isinstance(value, str) or not TAG_RE.fullmatch(value.strip()):
        raise InputError(f"invalid tag: {value!r}")
    return value.strip()


def is_safe_name(name: str) -> bool:
    return (
        isinstance(name, str)
        and bool(name)
        and bool(SAFE_NAME_RE.fullmatch(name))
        and name not in {".", ".."}
    )


def link_core(link: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in link.items() if key != "link_hash"}


def compute_link_hash(prev_hash: str, link: Mapping[str, Any]) -> str:
    body = canonical_bytes(link_core(link))
    return sha256_bytes(prev_hash.encode("utf-8") + b"\n" + body)


def manifest_header(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Metadata bound by the first (manifest) link."""
    return {field: raw[field] for field in HEADER_FIELDS if field in raw}


def header_digest(raw: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(manifest_header(raw)))


@dataclass(frozen=True)
class ChainManifest:
    raw: dict[str, Any]
    links: tuple[dict[str, Any], ...]
    declared_root: str
    declared_link_count: int
    version: str
    tag: str
    package_id: str

    @property
    def link_count(self) -> int:
        return len(self.links)

    def assets(self) -> dict[str, str]:
        return {
            str(link["name"]): str(link["sha256"])
            for link in self.links
            if link.get("kind") == "asset"
        }


@dataclass(frozen=True)
class LinkCheck:
    broken: BrokenLink | None
    verified_count: int
    root_hash: str


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise InputError(detail)


def parse_manifest(data: Any) -> ChainManifest:
    """Validate shape/types only.  Hash mismatches are verification failures."""
    _require(isinstance(data, dict), "chain manifest must be an object")
    for field in REQUIRED_MANIFEST_FIELDS:
        _require(field in data, f"chain manifest missing field: {field}")
    _require(data["schema"] == "cbc-chain/v1", "schema must be cbc-chain/v1")
    _require(data["chain_scope"] == "release", "release verifier requires chain_scope=release")
    _require(data["chain_profile"] == "sealed-v1", "chain_profile must be sealed-v1")
    _require(isinstance(data["package_id"], str) and data["package_id"], "package_id must be non-empty")
    normalize_version(data["version"])
    normalize_tag(data["tag"])
    _require(data["canonicalization"] == "cbc-event.canonical/rfc8785", "unexpected canonicalization")
    _require(data["hash_alg"] == "sha256", "hash_alg must be sha256")
    _require(data["genesis"] == GENESIS, "genesis must be sha256:<64 zeros>")
    _require(isinstance(data["link_count"], int) and not isinstance(data["link_count"], bool), "link_count must be an integer")
    _require(data["link_count"] >= 0, "link_count must be >= 0")
    _require(isinstance(data["root_hash"], str), "root_hash must be a string")
    links = data["links"]
    _require(isinstance(links, list) and links, "links must be a non-empty array")
    for position, link in enumerate(links, 1):
        _require(isinstance(link, dict), f"links[{position}] must be an object")
        for field in REQUIRED_LINK_FIELDS:
            _require(field in link, f"links[{position}] missing field: {field}")
        _require(isinstance(link["index"], int) and not isinstance(link["index"], bool), f"links[{position}].index must be integer")
        _require(link["kind"] in LINK_KINDS, f"links[{position}].kind is invalid")
        _require(isinstance(link["role"], str) and link["role"], f"links[{position}].role must be non-empty")
        _require(isinstance(link["name"], str), f"links[{position}].name must be a string")
        _require(isinstance(link["sha256"], str), f"links[{position}].sha256 must be a string")
        _require(isinstance(link["size"], int) and not isinstance(link["size"], bool), f"links[{position}].size must be integer")
        _require(isinstance(link["prev_hash"], str), f"links[{position}].prev_hash must be a string")
        _require(isinstance(link["link_hash"], str), f"links[{position}].link_hash must be a string")
    _require(links[0]["kind"] == "manifest", "first link must be kind=manifest")
    return ChainManifest(
        raw=data,
        links=tuple(links),
        declared_root=data["root_hash"],
        declared_link_count=data["link_count"],
        version=data["version"],
        tag=data["tag"],
        package_id=data["package_id"],
    )


def read_manifest(path: Path | str) -> ChainManifest:
    target = Path(path)
    if not target.is_file():
        raise InputError(f"chain manifest not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read chain manifest: {exc}") from exc
    return parse_manifest(data)


def _broken(link: Mapping[str, Any], reason: str, *, expected: str | None = None,
            actual: str | None = None, detail: str | None = None,
            index: int | None = None, kind: str | None = None,
            name: str | None = None) -> BrokenLink:
    return BrokenLink(
        index=index if index is not None else int(link.get("index", 0)),
        kind=kind if kind is not None else str(link.get("kind", "unknown")),
        name=name if name is not None else str(link.get("name", "unknown")),
        reason=reason,
        expected=expected,
        actual=actual,
        detail=detail,
    )


def verify_links(manifest: ChainManifest, release_dir: Path | str) -> LinkCheck:
    """Verify continuity, link hashes, file presence, size, and file hashes."""
    root = Path(release_dir)
    prev = GENESIS
    seen: set[str] = set()
    for position, link in enumerate(manifest.links, 1):
        if link["index"] != position:
            return LinkCheck(_broken(link, "chain_seq_gap", expected=str(position), actual=str(link["index"])), position - 1, prev)
        if link["prev_hash"] != prev:
            return LinkCheck(_broken(link, "chain_seq_gap", expected=prev, actual=link["prev_hash"]), position - 1, prev)
        name = str(link["name"])
        if name in seen:
            return LinkCheck(_broken(link, "chain_duplicate"), position - 1, prev)
        seen.add(name)
        if not is_safe_name(name):
            return LinkCheck(_broken(link, "unsafe_name"), position - 1, prev)
        expected_hash = str(link["sha256"])
        if not HASH_RE.fullmatch(expected_hash):
            return LinkCheck(_broken(link, "chain_hash_mismatch", expected="sha256:<64-hex>", actual=expected_hash), position - 1, prev)
        calculated = compute_link_hash(prev, link)
        if calculated != link["link_hash"]:
            return LinkCheck(_broken(link, "chain_hash_mismatch", expected=calculated, actual=str(link["link_hash"])), position - 1, prev)
        if link["kind"] == "manifest":
            expected_header = header_digest(manifest.raw)
            if expected_hash != expected_header:
                return LinkCheck(_broken(link, "chain_hash_mismatch", expected=expected_header,
                                         actual=expected_hash,
                                         detail="manifest metadata is not bound by the header link"),
                                  position - 1, prev)
            header_size = len(canonical_bytes(manifest_header(manifest.raw)))
            if link["size"] != header_size:
                return LinkCheck(_broken(link, "chain_hash_mismatch", expected=str(header_size),
                                         actual=str(link["size"]),
                                         detail="manifest header size mismatch"),
                                  position - 1, prev)
            prev = str(link["link_hash"])
            continue
        target = root / name
        if target.is_symlink():
            return LinkCheck(_broken(link, "unsafe_symlink"), position - 1, prev)
        if not target.is_file():
            return LinkCheck(_broken(link, "missing_asset"), position - 1, prev)
        actual_hash = sha256_file(target)
        if actual_hash != expected_hash:
            return LinkCheck(_broken(link, "hash_mismatch", expected=expected_hash, actual=actual_hash), position - 1, prev)
        size = target.stat().st_size
        if size != link["size"]:
            return LinkCheck(_broken(link, "hash_mismatch", expected=expected_hash, actual=actual_hash,
                                     detail=f"size {size} != declared {link['size']}"), position - 1, prev)
        prev = str(link["link_hash"])
    if prev != manifest.declared_root:
        return LinkCheck(BrokenLink(kind="chain", name="root_hash", reason="chain_root_mismatch",
                                    expected=manifest.declared_root, actual=prev), len(manifest.links), prev)
    if len(manifest.links) != manifest.declared_link_count:
        return LinkCheck(BrokenLink(kind="chain", name="link_count", reason="chain_link_count_mismatch",
                                    expected=str(manifest.declared_link_count), actual=str(len(manifest.links))),
                         len(manifest.links), prev)
    return LinkCheck(None, len(manifest.links), prev)


def scan_untracked(manifest: ChainManifest, release_dir: Path | str) -> BrokenLink | None:
    root = Path(release_dir)
    allowed = {str(link["name"]) for link in manifest.links if link.get("kind") != "manifest"} | RELEASE_ALLOWLIST
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        name = entry.name
        if entry.is_symlink():
            return BrokenLink(kind="asset", name=name, reason="unsafe_symlink")
        if entry.is_dir():
            return BrokenLink(kind="asset", name=name, reason="unexpected_asset", detail="directory")
        if name not in allowed:
            return BrokenLink(kind="asset", name=name, reason="unexpected_asset")
    return None


def parse_assets_manifest(path: Path | str) -> dict[str, str]:
    target = Path(path)
    if not target.is_file():
        raise InputError(f"RELEASE_ASSETS.sha256 not found: {target}")
    entries: dict[str, str] = {}
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise InputError(f"cannot read RELEASE_ASSETS.sha256: {exc}") from exc
    for lineno, line in enumerate(lines, 1):
        text = line.strip()
        if not text:
            continue
        match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", text)
        if not match:
            raise InputError(f"RELEASE_ASSETS.sha256:{lineno}: invalid line")
        digest = "sha256:" + match.group(1).lower()
        name = match.group(2).strip()
        if not is_safe_name(name):
            raise InputError(f"RELEASE_ASSETS.sha256:{lineno}: unsafe asset name")
        if name in entries:
            raise InputError(f"RELEASE_ASSETS.sha256:{lineno}: duplicate asset name {name}")
        entries[name] = digest
    if not entries:
        raise InputError("RELEASE_ASSETS.sha256 lists no assets")
    return entries


def parse_wheel_digest(path: Path | str) -> str:
    target = Path(path)
    if not target.is_file():
        raise InputError(f"WHEEL_SHA256 not found: {target}")
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read WHEEL_SHA256: {exc}") from exc
    match = re.search(r"(?:sha256:)?([0-9a-fA-F]{64})", text)
    if not match:
        raise InputError("WHEEL_SHA256 does not contain a sha256 value")
    return "sha256:" + match.group(1).lower()


def verify_artifacts(manifest: ChainManifest, release_dir: Path | str, cbp: Mapping[str, Any]) -> BrokenLink | None:
    """Cross-check chain, RELEASE_ASSETS.sha256, WHEEL_SHA256, and CBP hashes."""
    root = Path(release_dir)
    chain_assets = manifest.assets()
    manifest_assets = parse_assets_manifest(root / "RELEASE_ASSETS.sha256")

    for name, digest in manifest_assets.items():
        if name not in chain_assets:
            return BrokenLink(kind="asset", name=name, reason="manifest_conflict",
                              detail="RELEASE_ASSETS.sha256 lists an asset missing from the chain")
        if chain_assets[name] != digest:
            return BrokenLink(kind="asset", name=name, reason="manifest_conflict",
                              expected=chain_assets[name], actual=digest,
                              detail="chain and RELEASE_ASSETS.sha256 disagree")
    for name in sorted(set(chain_assets) - set(manifest_assets)):
        return BrokenLink(kind="asset", name=name, reason="manifest_entry_missing",
                          expected=chain_assets[name],
                          detail="chain asset has no RELEASE_ASSETS.sha256 entry")

    artifact_hashes = cbp.get("artifact_hashes", {})
    if not isinstance(artifact_hashes, dict):
        raise InputError("CBP artifact_hashes must be an object")
    wheels = sorted(name for name in chain_assets if name.lower().endswith(".whl"))
    for key, raw_value in artifact_hashes.items():
        try:
            value = normalize_hash(str(raw_value))
        except InputError as exc:
            raise InputError(f"CBP artifact_hashes[{key!r}]: {exc}") from exc
        if key in chain_assets:
            if chain_assets[key] != value:
                return BrokenLink(kind="asset", name=key, reason="manifest_conflict",
                                  expected=chain_assets[key], actual=value,
                                  detail="CBP artifact_hashes disagrees with the chain")
            continue
        if key == "wheel" and len(wheels) == 1:
            if chain_assets[wheels[0]] != value:
                return BrokenLink(kind="asset", name=wheels[0], reason="manifest_conflict",
                                  expected=chain_assets[wheels[0]], actual=value,
                                  detail="CBP artifact_hashes['wheel'] disagrees with the chain")
            continue
        matches = [name for name, digest in chain_assets.items() if digest == value]
        if len(matches) == 1:
            continue
        return BrokenLink(kind="asset", name=str(key), reason="manifest_entry_missing",
                          expected=value,
                          detail="CBP artifact_hashes entry matches no chain asset")

    if len(wheels) != 1:
        return BrokenLink(kind="asset", name="wheel", reason="manifest_conflict",
                          detail=f"expected exactly one wheel, found {len(wheels)}")
    wheel_digest = parse_wheel_digest(root / "WHEEL_SHA256")
    if chain_assets[wheels[0]] != wheel_digest:
        return BrokenLink(kind="asset", name=wheels[0], reason="hash_mismatch",
                          expected=wheel_digest, actual=chain_assets[wheels[0]],
                          detail="WHEEL_SHA256 disagrees with the chain")
    return None


def _link(kind: str, role: str, name: str, path: Path) -> dict[str, Any]:
    return {
        "kind": kind,
        "role": role,
        "name": name,
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def build_manifest(
    release_dir: Path | str,
    *,
    version: str,
    tag: str,
    package_id: str = "cbc",
    cbe_name: str = "cbe-report.json",
    cbp_name: str = "quality-manifest.json",
    source_commit: str | None = None,
) -> dict[str, Any]:
    """Build a manifest for a release directory (used by release prep/tests).

    This is a pure function: it never writes to ``release_dir``.
    """
    root = Path(release_dir)
    normalize_version(version)
    normalize_tag(tag)
    data: dict[str, Any] = {
        "schema": "cbc-chain/v1",
        "chain_scope": "release",
        "chain_profile": "sealed-v1",
        "package_id": package_id,
        "version": version,
        "tag": tag,
        "body_marker": "CBC-EVIDENCE",
        "body_hash_scope": "base",
        "canonicalization": "cbc-event.canonical/rfc8785",
        "hash_alg": "sha256",
        "genesis": GENESIS,
    }
    if source_commit:
        data["source_commit"] = source_commit
    header_bytes = canonical_bytes(manifest_header(data))
    entries: list[dict[str, Any]] = [
        {
            "kind": "manifest",
            "role": "header",
            "name": "manifest",
            "sha256": sha256_bytes(header_bytes),
            "size": len(header_bytes),
        }
    ]
    controls = [
        ("gate_report", "cbe", cbe_name),
        ("gate_report", "cbp", cbp_name),
        ("control", "assets_manifest", "RELEASE_ASSETS.sha256"),
        ("control", "wheel_digest", "WHEEL_SHA256"),
    ]
    for kind, role, name in controls:
        path = root / name
        if not path.is_file():
            raise InputError(f"required chain input missing: {name}")
        entries.append(_link(kind, role, name, path))

    assets = parse_assets_manifest(root / "RELEASE_ASSETS.sha256")
    for name in sorted(assets, key=lambda item: item.encode("utf-8")):
        path = root / name
        if path.is_symlink():
            raise InputError(f"asset is a symlink: {name}")
        if not path.is_file():
            raise InputError(f"asset listed but missing: {name}")
        link = _link("asset", "artifact", name, path)
        if link["sha256"] != assets[name]:
            raise InputError(f"asset hash disagrees with RELEASE_ASSETS.sha256: {name}")
        entries.append(link)

    prev = GENESIS
    links: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, 1):
        link = {"index": index, "prev_hash": prev, **entry}
        link["link_hash"] = compute_link_hash(prev, link)
        links.append(link)
        prev = link["link_hash"]
    data["link_count"] = len(links)
    data["root_hash"] = links[-1]["link_hash"]
    data["links"] = links
    return data
