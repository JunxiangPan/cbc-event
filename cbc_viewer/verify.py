"""High-level verification and report construction.

Exit-code precedence is fixed and tested:

    input 2  >  infra/chain/upstream 3  >  skip 4  >  expect-uploaded 2  >  0

``--expect-uploaded`` is a caller expectation, not a gate verdict: an
unconfirmed upload is ``exit 2`` + ``PRECONDITION_FAIL`` (F1 alignment), never
``exit 3`` with ``NOT_UPLOADED``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .body import BodyProblem, parse_anchor, split_body
from .chain import (
    ChainManifest,
    LinkCheck,
    RELEASE_ALLOWLIST,
    read_manifest,
    scan_untracked,
    verify_artifacts,
    verify_links,
)
from .errors import BrokenLink, InfraError, InputError, NotFoundError
from .event_chain import verify_event_log
from .reports import GateReports, hash_matches, load_gate_reports
from .transport import ReadOnlyTransport


@dataclass(frozen=True)
class VerificationResult:
    report: dict[str, Any]
    exit_code: int


@dataclass(frozen=True)
class RemoteCheck:
    uploaded: bool
    broken: BrokenLink | None
    reason: str | None
    checked: bool


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _empty_skip() -> dict[str, Any]:
    return {
        "cbe_skip_ratio": 0.0,
        "cbp_skip_ratio": 0.0,
        "effective_skip_ratio": 0.0,
        "threshold": 0.2,
        "blocking_skip": False,
        "not_counted_in_skip_ratio": True,
    }


def _skip_from(reports: GateReports | None) -> dict[str, Any]:
    if reports is None:
        return _empty_skip()
    return {
        "cbe_skip_ratio": float(reports.cbe["skip_ratio"]),
        "cbp_skip_ratio": float(reports.cbp["skip_ratio"]),
        "effective_skip_ratio": reports.skip_ratio,
        "threshold": 0.2,
        "blocking_skip": reports.blocking_skip,
        "not_counted_in_skip_ratio": True,
    }


def _report(
    *,
    scope: str,
    version: str | None,
    tag: str | None,
    gate_status: str,
    chain_status: str,
    root_hash: str | None = None,
    link_count: int = 0,
    broken_link: BrokenLink | None = None,
    upload_status: str = "NOT_UPLOADED",
    verified_link_count: int = 0,
    declared_root_hash: str | None = None,
    chain_profile: str = "sealed-v1",
    body_hash_scope: str | None = None,
    upload_allowed: bool = False,
    upload_blocked_reason: str | None = None,
    declared_attached: bool = False,
    skip: dict[str, Any] | None = None,
    inputs: Mapping[str, Any] | None = None,
    error: Mapping[str, Any] | None = None,
    remote_checked: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "package_id": "cbc",
        "version": version,
        "tag": tag,
        "gate_status": gate_status,
        "exit_code": 0,
        "cbc_chain_status": chain_status,
        "root_hash": root_hash,
        "link_count": link_count,
        "broken_link": broken_link.to_dict() if broken_link else None,
        "upload_status": upload_status,
        "verified_link_count": verified_link_count,
        "declared_root_hash": declared_root_hash,
        "chain_scope": scope,
        "chain_profile": chain_profile,
        "body_hash_scope": body_hash_scope,
        "upload_allowed": upload_allowed,
        "upload_blocked_reason": upload_blocked_reason,
        "declared_attached": declared_attached,
        "anchor_scope": "remote" if remote_checked else "local",
        "remote_checked": remote_checked,
        "skip": skip or _empty_skip(),
        "inputs": dict(inputs or {}),
        "error": dict(error) if error else None,
        "checked_at": _now(),
    }


def _result(report: dict[str, Any], exit_code: int) -> VerificationResult:
    report["exit_code"] = exit_code
    return VerificationResult(report=report, exit_code=exit_code)


def _input_result(
    exc: InputError,
    *,
    scope: str,
    version: str | None,
    tag: str | None,
    inputs: Mapping[str, Any],
    reports: GateReports | None = None,
) -> VerificationResult:
    report = _report(
        scope=scope,
        version=version,
        tag=tag,
        gate_status="FAIL",
        chain_status="FAIL",
        root_hash=None,
        link_count=0,
        upload_status="NOT_UPLOADED",
        upload_allowed=False,
        upload_blocked_reason="input_error",
        skip=_skip_from(reports),
        inputs=inputs,
        error=exc.as_dict(),
    )
    return _result(report, 2)


def _chain_fail(
    manifest: ChainManifest,
    check: LinkCheck,
    reports: GateReports,
    inputs: Mapping[str, Any],
    *,
    broken: BrokenLink,
    declared_attached: bool = False,
) -> VerificationResult:
    report = _report(
        scope="release",
        version=reports.version,
        tag=reports.tag,
        gate_status="FAIL",
        chain_status="FAIL",
        root_hash=check.root_hash,
        link_count=manifest.declared_link_count,
        broken_link=broken,
        upload_status="NOT_UPLOADED",
        verified_link_count=check.verified_count,
        declared_root_hash=manifest.declared_root,
        body_hash_scope=reports.body_hash_scope,
        upload_allowed=False,
        upload_blocked_reason="chain_broken",
        declared_attached=declared_attached,
        skip=_skip_from(reports),
        inputs=inputs,
    )
    return _result(report, 3)


def _body_fail(
    exc: BodyProblem,
    manifest: ChainManifest,
    check: LinkCheck,
    reports: GateReports,
    inputs: Mapping[str, Any],
    *,
    declared_attached: bool = False,
) -> VerificationResult:
    broken = BrokenLink(kind="release_body", name="RELEASE_BODY.md", reason=exc.reason, detail=exc.detail)
    report = _report(
        scope="release",
        version=reports.version,
        tag=reports.tag,
        gate_status="FAIL",
        chain_status="FAIL",
        root_hash=check.root_hash,
        link_count=manifest.declared_link_count,
        broken_link=broken,
        upload_status="NOT_UPLOADED",
        verified_link_count=check.verified_count,
        declared_root_hash=manifest.declared_root,
        body_hash_scope=reports.body_hash_scope,
        upload_allowed=False,
        upload_blocked_reason="body_broken",
        declared_attached=declared_attached,
        skip=_skip_from(reports),
        inputs=inputs,
    )
    return _result(report, 3)


def _gate_result(
    *,
    manifest: ChainManifest,
    check: LinkCheck,
    reports: GateReports,
    inputs: Mapping[str, Any],
    gate_status: str,
    exit_code: int,
    reason: str,
    remote_checked: bool = False,
    declared_attached: bool = False,
) -> VerificationResult:
    report = _report(
        scope="release",
        version=reports.version,
        tag=reports.tag,
        gate_status=gate_status,
        chain_status="PASS",
        root_hash=check.root_hash,
        link_count=manifest.declared_link_count,
        upload_status="NOT_UPLOADED",
        verified_link_count=check.verified_count,
        declared_root_hash=manifest.declared_root,
        body_hash_scope=reports.body_hash_scope,
        upload_allowed=False,
        upload_blocked_reason=reason,
        declared_attached=declared_attached,
        skip=_skip_from(reports),
        inputs=inputs,
        remote_checked=remote_checked,
    )
    return _result(report, exit_code)


def _remote_fail(
    *,
    manifest: ChainManifest,
    check: LinkCheck,
    reports: GateReports,
    inputs: Mapping[str, Any],
    broken: BrokenLink,
    declared_attached: bool = False,
) -> VerificationResult:
    report = _report(
        scope="release",
        version=reports.version,
        tag=reports.tag,
        gate_status="FAIL",
        chain_status="PASS",
        root_hash=check.root_hash,
        link_count=manifest.declared_link_count,
        broken_link=broken,
        upload_status="NOT_UPLOADED",
        verified_link_count=check.verified_count,
        declared_root_hash=manifest.declared_root,
        body_hash_scope=reports.body_hash_scope,
        upload_allowed=False,
        upload_blocked_reason="remote_evidence_mismatch",
        declared_attached=declared_attached,
        skip=_skip_from(reports),
        inputs=inputs,
        remote_checked=True,
    )
    return _result(report, 3)


def _precondition_result(
    *,
    manifest: ChainManifest,
    check: LinkCheck,
    reports: GateReports,
    inputs: Mapping[str, Any],
    reason: str,
    error: Mapping[str, Any] | None = None,
    declared_attached: bool = False,
) -> VerificationResult:
    report = _report(
        scope="release",
        version=reports.version,
        tag=reports.tag,
        gate_status="PRECONDITION_FAIL",
        chain_status="PASS",
        root_hash=check.root_hash,
        link_count=manifest.declared_link_count,
        upload_status="NOT_UPLOADED",
        verified_link_count=check.verified_count,
        declared_root_hash=manifest.declared_root,
        body_hash_scope=reports.body_hash_scope,
        upload_allowed=False,
        upload_blocked_reason=reason,
        declared_attached=declared_attached,
        skip=_skip_from(reports),
        inputs=inputs,
        error=error,
        remote_checked=bool(error and error.get("remote_checked")),
    )
    return _result(report, 2)


def _parse_remote(value: str) -> tuple[str, str]:
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise InputError("--remote must be owner/repo")
    return parts[0], parts[1]


def _check_remote(
    transport: ReadOnlyTransport,
    owner: str,
    repo: str,
    tag: str,
    manifest: ChainManifest,
    local_body: bytes,
) -> RemoteCheck:
    release = transport.get_release(owner, repo, tag)
    remote_body = release.get("body")
    if not isinstance(remote_body, str):
        return RemoteCheck(False, BrokenLink(kind="release_body", name="RELEASE_BODY.md",
                                             reason="body_anchor_missing",
                                             detail="remote release has no body"), "remote_body_missing", False)
    if remote_body.encode("utf-8") != local_body:
        return RemoteCheck(False, BrokenLink(kind="release_body", name="RELEASE_BODY.md",
                                             reason="body_hash_mismatch",
                                             detail="remote body differs from the verified local body"),
                           "remote_body_mismatch", False)

    assets = release.get("assets")
    if not isinstance(assets, list):
        return RemoteCheck(False, BrokenLink(kind="asset", name="assets", reason="report_invalid",
                                             detail="remote release assets is not a list"), "remote_assets_invalid", False)
    chain_assets = manifest.assets()
    remote_by_name: dict[str, Mapping[str, Any]] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            return RemoteCheck(False, BrokenLink(kind="asset", name="assets", reason="report_invalid",
                                                 detail="remote asset is not an object"), "remote_assets_invalid", False)
        name = asset.get("name")
        if not isinstance(name, str) or not name:
            return RemoteCheck(False, BrokenLink(kind="asset", name="assets", reason="report_invalid",
                                                 detail="remote asset has no name"), "remote_assets_invalid", False)
        if name in remote_by_name:
            return RemoteCheck(False, BrokenLink(kind="asset", name=name, reason="chain_duplicate",
                                                 detail="duplicate remote asset name"), "remote_duplicate_asset", False)
        remote_by_name[name] = asset

    for name in sorted(set(remote_by_name) - set(chain_assets)):
        if name in RELEASE_ALLOWLIST:
            continue
        return RemoteCheck(False, BrokenLink(kind="asset", name=name, reason="unexpected_asset",
                                             detail="remote release has an asset missing from the chain"),
                           "remote_unexpected_asset", True)

    missing = sorted(set(chain_assets) - set(remote_by_name))
    if missing:
        return RemoteCheck(False, None, "remote_asset_missing", True)

    unconfirmed = False
    for name, digest in chain_assets.items():
        asset = remote_by_name[name]
        remote_digest = asset.get("digest")
        if not isinstance(remote_digest, str) or not remote_digest:
            unconfirmed = True
            continue
        expected = digest.lower()
        actual = remote_digest.lower()
        if not actual.startswith("sha256:"):
            actual = "sha256:" + actual
        if actual != expected:
            return RemoteCheck(False, BrokenLink(kind="asset", name=name, reason="hash_mismatch",
                                                 expected=digest, actual=remote_digest,
                                                 detail="remote asset digest disagrees with the chain"),
                               "remote_digest_mismatch", True)
    if unconfirmed:
        return RemoteCheck(False, None, "remote_digest_unavailable", True)

    source_commit = manifest.raw.get("source_commit")
    if isinstance(source_commit, str) and source_commit:
        getter = getattr(transport, "get_tag_commit", None)
        if callable(getter):
            commit = getter(owner, repo, tag)
            if commit and commit.lower() != source_commit.lower():
                return RemoteCheck(False, BrokenLink(kind="tag", name=tag, reason="tag_mismatch",
                                                     expected=source_commit, actual=commit,
                                                     detail="current tag commit differs from source_commit"),
                                   "remote_tag_mismatch", True)
    return RemoteCheck(True, None, None, True)


def verify_release(
    release_dir: Path | str,
    *,
    chain_path: Path | str | None = None,
    cbe_path: Path | str | None = None,
    cbp_path: Path | str | None = None,
    body_path: Path | str | None = None,
    version: str | None = None,
    tag: str | None = None,
    expect_uploaded: bool = False,
    declared_attached: bool = False,
    remote: str | None = None,
    transport: ReadOnlyTransport | None = None,
) -> VerificationResult:
    root = Path(release_dir)
    chain_p = Path(chain_path) if chain_path is not None else root / "cbc-chain.json"
    cbe_p = Path(cbe_path) if cbe_path is not None else root / "cbe-report.json"
    cbp_p = Path(cbp_path) if cbp_path is not None else root / "quality-manifest.json"
    body_p = Path(body_path) if body_path is not None else root / "RELEASE_BODY.md"
    inputs = {
        "release_dir": str(root),
        "chain": str(chain_p),
        "cbe_report": str(cbe_p),
        "cbp_manifest": str(cbp_p),
        "body": str(body_p),
    }

    reports: GateReports | None = None
    manifest: ChainManifest | None = None
    try:
        manifest = read_manifest(chain_p)
        reports = load_gate_reports(
            cbe_p,
            cbp_p,
            chain_version=manifest.version,
            chain_tag=manifest.tag,
            cli_version=version,
            cli_tag=tag,
        )
        try:
            body_data = body_p.read_bytes()
        except OSError as exc:
            raise InputError(f"cannot read release body: {exc}") from exc
    except InputError as exc:
        return _input_result(exc, scope="release", version=version, tag=tag, inputs=inputs, reports=reports)

    for required_name in ("RELEASE_ASSETS.sha256", "WHEEL_SHA256"):
        if not (root / required_name).is_file():
            return _input_result(
                InputError(f"required release input missing: {required_name}"),
                scope="release", version=reports.version, tag=reports.tag,
                inputs=inputs, reports=reports,
            )

    try:
        check = verify_links(manifest, root)
        broken = check.broken
        if broken is None:
            broken = scan_untracked(manifest, root)
        if broken is None:
            broken = verify_artifacts(manifest, root, reports.cbp)
    except InputError as exc:
        return _input_result(exc, scope="release", version=reports.version, tag=reports.tag,
                             inputs=inputs, reports=reports)
    except OSError as exc:
        return _input_result(InputError(f"cannot read release evidence: {exc}"),
                             scope="release", version=reports.version, tag=reports.tag,
                             inputs=inputs, reports=reports)
    if broken is not None:
        return _chain_fail(manifest, check, reports, inputs, broken=broken,
                           declared_attached=declared_attached)

    if reports.body_hash_scope is None:
        return _input_result(
            InputError("CBP quality manifest is missing body_hash_scope; align CBP P0-06 first"),
            scope="release", version=reports.version, tag=reports.tag, inputs=inputs, reports=reports,
        )
    if reports.body_hash_scope != "base":
        return _input_result(
            InputError(f"body_hash_scope={reports.body_hash_scope!r} is not supported by sealed-v1; require 'base'"),
            scope="release", version=reports.version, tag=reports.tag, inputs=inputs, reports=reports,
        )

    try:
        base, appendix = split_body(body_data)
        if appendix is None:
            raise BodyProblem("body_anchor_missing", "RELEASE_BODY.md has no CBC-EVIDENCE appendix")
        anchor = parse_anchor(appendix)
    except BodyProblem as exc:
        return _body_fail(exc, manifest, check, reports, inputs, declared_attached=declared_attached)

    if not hash_matches(reports.cbp["release_body_hash"], base):
        return _body_fail(
            BodyProblem("body_hash_mismatch", "base body hash does not match CBP release_body_hash"),
            manifest, check, reports, inputs, declared_attached=declared_attached,
        )
    if anchor["root_hash"] != check.root_hash:
        return _body_fail(
            BodyProblem("body_anchor_mismatch", f"anchor root {anchor['root_hash']} != computed {check.root_hash}"),
            manifest, check, reports, inputs, declared_attached=declared_attached,
        )
    if anchor["link_count"] != manifest.declared_link_count:
        return _body_fail(
            BodyProblem("body_anchor_mismatch", "anchor link_count does not match the chain manifest"),
            manifest, check, reports, inputs, declared_attached=declared_attached,
        )

    if reports.infra:
        return _gate_result(
            manifest=manifest, check=check, reports=reports, inputs=inputs,
            gate_status="SKIPPED_INFRA", exit_code=3, reason="upstream_skipped_infra",
            declared_attached=declared_attached,
        )
    if reports.skip_over:
        return _gate_result(
            manifest=manifest, check=check, reports=reports, inputs=inputs,
            gate_status="FAIL", exit_code=4, reason="skip_threshold_exceeded",
            declared_attached=declared_attached,
        )
    if reports.blocking_skip:
        return _gate_result(
            manifest=manifest, check=check, reports=reports, inputs=inputs,
            gate_status="FAIL", exit_code=3, reason="blocking_skip",
            declared_attached=declared_attached,
        )
    if reports.gate_fail:
        return _gate_result(
            manifest=manifest, check=check, reports=reports, inputs=inputs,
            gate_status="FAIL", exit_code=3, reason=str(reports.reason()),
            declared_attached=declared_attached,
        )

    uploaded = False
    remote_checked = False
    if remote is not None:
        try:
            owner, repo = _parse_remote(remote)
            active = transport or ReadOnlyTransport()
            remote_check = _check_remote(active, owner, repo, reports.tag, manifest, body_data)
        except NotFoundError as exc:
            if expect_uploaded:
                return _precondition_result(
                    manifest=manifest, check=check, reports=reports, inputs=inputs,
                    reason="expect_uploaded_unmet", error={**exc.as_dict(), "remote_checked": True},
                    declared_attached=declared_attached,
                )
            uploaded = False
            remote_checked = True
            remote_check = RemoteCheck(False, None, "release_not_found", True)
        except InfraError as exc:
            report = _report(
                scope="release", version=reports.version, tag=reports.tag,
                gate_status="SKIPPED_INFRA", chain_status="PASS",
                root_hash=check.root_hash, link_count=manifest.declared_link_count,
                upload_status="NOT_UPLOADED", verified_link_count=check.verified_count,
                declared_root_hash=manifest.declared_root, body_hash_scope=reports.body_hash_scope,
                upload_allowed=False, upload_blocked_reason="infra_failure",
                declared_attached=declared_attached,
                skip=_skip_from(reports), inputs=inputs, error=exc.as_dict(), remote_checked=True,
            )
            return _result(report, 3)
        except InputError as exc:
            return _input_result(exc, scope="release", version=reports.version, tag=reports.tag,
                                 inputs=inputs, reports=reports)

        remote_checked = True
        if remote_check.broken is not None:
            return _remote_fail(manifest=manifest, check=check, reports=reports,
                                inputs=inputs, broken=remote_check.broken,
                                declared_attached=declared_attached)
        uploaded = remote_check.uploaded
        if not uploaded and expect_uploaded:
            return _precondition_result(
                manifest=manifest, check=check, reports=reports, inputs=inputs,
                reason=remote_check.reason or "expect_uploaded_unmet",
                error={"code": remote_check.reason or "expect_uploaded_unmet",
                       "detail": "remote upload is not confirmed", "remote_checked": True},
                declared_attached=declared_attached,
            )

    if expect_uploaded and not uploaded:
        return _precondition_result(
            manifest=manifest, check=check, reports=reports, inputs=inputs,
            reason="expect_uploaded_unmet",
            error={"code": "expect_uploaded_unmet",
                   "detail": "--expect-uploaded requires --remote confirmation", "remote_checked": False},
            declared_attached=declared_attached,
        )

    if uploaded:
        report = _report(
            scope="release", version=reports.version, tag=reports.tag,
            gate_status="PASS", chain_status="PASS", root_hash=check.root_hash,
            link_count=manifest.declared_link_count, upload_status="UPLOADED",
            verified_link_count=check.verified_count, declared_root_hash=manifest.declared_root,
            body_hash_scope=reports.body_hash_scope, upload_allowed=True,
            declared_attached=declared_attached, skip=_skip_from(reports), inputs=inputs,
            remote_checked=remote_checked,
        )
        return _result(report, 0)
    report = _report(
        scope="release", version=reports.version, tag=reports.tag,
        gate_status="NOT_UPLOADED", chain_status="PASS", root_hash=check.root_hash,
        link_count=manifest.declared_link_count, upload_status="NOT_UPLOADED",
        verified_link_count=check.verified_count, declared_root_hash=manifest.declared_root,
        body_hash_scope=reports.body_hash_scope, upload_allowed=True,
        upload_blocked_reason="not_uploaded", declared_attached=declared_attached,
        skip=_skip_from(reports), inputs=inputs, remote_checked=remote_checked,
    )
    return _result(report, 0)


def verify_event_log_report(
    event_dir: Path | str,
    *,
    manifest_path: Path | str | None = None,
) -> VerificationResult:
    inputs = {"event_dir": str(event_dir), "chain": str(manifest_path) if manifest_path else None}
    try:
        check = verify_event_log(event_dir, manifest_path=manifest_path)
    except InputError as exc:
        report = _report(
            scope="event-log", version="0.1.0", tag=None,
            gate_status="FAIL", chain_status="FAIL", root_hash=None, link_count=0,
            upload_status="NOT_UPLOADED", upload_blocked_reason="input_error",
            chain_profile="event-log/v1", inputs=inputs, error=exc.as_dict(),
        )
        return _result(report, 2)
    if check.broken is not None:
        report = _report(
            scope="event-log", version="0.1.0", tag=None,
            gate_status="FAIL", chain_status="FAIL", root_hash=check.root_hash,
            link_count=check.link_count, broken_link=check.broken,
            upload_status="NOT_UPLOADED", verified_link_count=check.verified_count,
            upload_blocked_reason="chain_broken", chain_profile="event-log/v1", inputs=inputs,
        )
        return _result(report, 3)
    report = _report(
        scope="event-log", version="0.1.0", tag=None,
        gate_status="PASS", chain_status="PASS", root_hash=check.root_hash,
        link_count=check.link_count, upload_status="NOT_UPLOADED",
        verified_link_count=check.verified_count,
        upload_blocked_reason="not_applicable_event_scope",
        chain_profile="event-log/v1", inputs=inputs,
    )
    return _result(report, 0)
