"""Read-only CLI.  There is intentionally no upload/delete/tag/edit command."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .body import BodyProblem, render_appendix, render_not_uploaded_entry
from .errors import InputError
from .verify import VerificationResult, verify_event_log_report, verify_release

VERSION = "0.2.0rc2"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cbc-viewer", description="Read-only CBC evidence viewer")
    parser.add_argument("--version", action="version", version=f"cbc-viewer {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="verify a release directory or event log")
    verify.add_argument("--scope", choices=["release", "event-log"], default="release")
    verify.add_argument("--release-dir")
    verify.add_argument("--event-dir")
    verify.add_argument("--chain")
    verify.add_argument("--cbe-report")
    verify.add_argument("--cbp-manifest")
    verify.add_argument("--body")
    verify.add_argument("--version-id", dest="target_version")
    verify.add_argument("--tag")
    verify.add_argument("--remote", help="owner/repo; read-only GitHub check")
    verify.add_argument("--remote-tag", help="remote release tag when it differs from the chain tag (e.g. a pre-release)")
    verify.add_argument("--expect-uploaded", action="store_true")
    verify.add_argument("--declared-attached", action="store_true")
    verify.add_argument("--report-out")
    verify.add_argument("--force", action="store_true")
    verify.add_argument("--json", action="store_true")

    show = sub.add_parser("show", help="print a saved report")
    show.add_argument("--report", required=True)
    show.add_argument("--json", action="store_true")

    cbf = sub.add_parser("cbf-evidence", help="read cbf-evidence/v1 and emit a CBC view/event")
    cbf.add_argument("--evidence", required=True)
    cbf.add_argument("--event", action="store_true", help="convert to a cbc-event/v2 event")
    cbf.add_argument("--chain-id")
    cbf.add_argument("--seq", type=int)
    cbf.add_argument("--prev-hash", default="sha256:" + "0" * 64)

    render = sub.add_parser("render-body", help="render the CBC body block")
    render.add_argument("--report", required=True)
    render.add_argument("--format", choices=["cbs-not-uploaded-entry", "appendix"], required=True)
    return parser


def _resolve(path: str | None, base: Path) -> Path | None:
    if path is None:
        return None
    return Path(path) if Path(path).is_absolute() else base / Path(path)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _write_report(report: dict[str, Any], output: str, source_dirs: Sequence[Path], *, force: bool) -> None:
    target = Path(output).resolve()
    for source in source_dirs:
        if _inside(target, source.resolve()):
            raise InputError("--report-out must be outside the verified source directory")
    if target.exists() and not force:
        raise InputError(f"report already exists (use --force): {target}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot write report: {exc}") from exc


def _summary(result: VerificationResult) -> str:
    report = result.report
    broken = report.get("broken_link")
    lines = [
        f"cbc-viewer: {report.get('gate_status')} (exit {result.exit_code})",
        f"chain: {report.get('cbc_chain_status')} root={report.get('root_hash')} links={report.get('link_count')}",
        f"upload: {report.get('upload_status')}",
        "broken_link: " + ("none" if not broken else f"{broken.get('reason')} at {broken.get('name')}"),
    ]
    if report.get("error"):
        lines.append(f"error: {report['error'].get('code')}: {report['error'].get('detail')}")
    return "\n".join(lines)


def _run_verify(args: argparse.Namespace) -> int:
    if args.scope == "release":
        if not args.release_dir:
            raise InputError("--release-dir is required for --scope release")
        base = Path(args.release_dir)
        result = verify_release(
            base,
            chain_path=_resolve(args.chain, base),
            cbe_path=_resolve(args.cbe_report, base),
            cbp_path=_resolve(args.cbp_manifest, base),
            body_path=_resolve(args.body, base),
            version=args.target_version,
            tag=args.tag,
            expect_uploaded=args.expect_uploaded,
            declared_attached=args.declared_attached,
            remote=args.remote,
        )
        sources = [base]
    else:
        if not args.event_dir:
            raise InputError("--event-dir is required for --scope event-log")
        base = Path(args.event_dir)
        result = verify_event_log_report(base, manifest_path=_resolve(args.chain, base))
        sources = [base]
    if args.report_out:
        _write_report(result.report, args.report_out, sources, force=args.force)
    print(json.dumps(result.report, ensure_ascii=False, indent=2) if args.json else _summary(result))
    return result.exit_code


def _load_report(path: str) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise InputError(f"report not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read report: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError("report must be a JSON object")
    return data


def _run_show(args: argparse.Namespace) -> int:
    report = _load_report(args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _run_cbf(args: argparse.Namespace) -> int:
    from cbc_event.cbf import CbfEvidence

    evidence = CbfEvidence.load(args.evidence)
    if evidence.hash_status == "mismatch":
        raise InputError("CBF evidence hash mismatch")
    if not args.event:
        print(json.dumps(evidence.view(), ensure_ascii=False, indent=2))
        return 0
    if not args.chain_id or args.seq is None:
        raise InputError("--event requires --chain-id and --seq")
    event = evidence.to_cbc_event(
        chain_id=args.chain_id,
        seq=args.seq,
        prev_hash=args.prev_hash,
    )
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def _run_render(args: argparse.Namespace) -> int:
    report = _load_report(args.report)
    if args.format == "appendix":
        print(render_appendix(report), end="")
        return 0
    entry = render_not_uploaded_entry(report)
    print(entry)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            return _run_verify(args)
        if args.command == "show":
            return _run_show(args)
        if args.command == "cbf-evidence":
            return _run_cbf(args)
        if args.command == "render-body":
            return _run_render(args)
        raise InputError(f"unknown command: {args.command}")
    except (InputError, BodyProblem) as exc:
        code = getattr(exc, "reason", "input_error")
        print(f"CBC_VIEWER_ERROR: {code}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
