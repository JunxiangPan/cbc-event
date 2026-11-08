"""Release-body appendix parsing and rendering.

CBP hashes the *base* body, i.e. the bytes before ``CBC-EVIDENCE-BEGIN``.  The
appendix carries the chain root, so it binds the CBP report (which binds the
base body) without creating a root/body cycle.  A body rewritten in either
half is detectable: base via CBP's hash, appendix via the chain root.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

from .chain import HASH_RE, sha256_bytes

BEGIN = "<!-- CBC-EVIDENCE-BEGIN -->"
END = "<!-- CBC-EVIDENCE-END -->"
ANCHOR_RE = re.compile(r"^<!-- cbc-evidence (\{.*\}) -->\s*$", re.MULTILINE)
ANCHOR_PREFIX = "<!-- cbc-evidence "


class BodyProblem(Exception):
    """A body that cannot be split/parsed; mapped to a failed broken_link."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def split_body(data: bytes) -> tuple[bytes, bytes | None]:
    """Return (base bytes, appendix bytes) or (whole body, None)."""
    begin = BEGIN.encode("utf-8")
    end = END.encode("utf-8")
    begin_count = data.count(begin)
    end_count = data.count(end)
    if begin_count == 0 and end_count == 0:
        return data, None
    if begin_count != 1 or end_count != 1:
        raise BodyProblem("body_anchor_mismatch", "expected exactly one CBC-EVIDENCE begin/end pair")
    start = data.index(begin)
    finish = data.index(end)
    if finish < start:
        raise BodyProblem("body_anchor_mismatch", "CBC-EVIDENCE end marker precedes begin marker")
    trailing = data[finish + len(end):]
    if trailing.strip():
        raise BodyProblem("body_anchor_mismatch", "non-whitespace content after CBC-EVIDENCE end marker")
    return data[:start], data[start + len(begin):finish]


def _appendix_lines(text: str) -> list[str]:
    lines = text.split("\n")
    anchors = [index for index, line in enumerate(lines) if line.strip().startswith(ANCHOR_PREFIX)]
    if len(anchors) != 1:
        raise BodyProblem("body_anchor_mismatch", "expected exactly one cbc-evidence anchor line")
    lines = [line for index, line in enumerate(lines) if index != anchors[0]]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def appendix_preimage(text: str) -> bytes:
    """Bytes covered by ``appendix_sha256`` (all appendix lines except the anchor)."""
    return "\n".join(_appendix_lines(text)).encode("utf-8")


def parse_anchor(appendix: bytes) -> dict[str, Any]:
    try:
        text = appendix.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BodyProblem("body_anchor_missing", f"appendix is not UTF-8: {exc}") from exc

    match = ANCHOR_RE.search(text)
    if not match:
        raise BodyProblem("body_anchor_missing", "no cbc-evidence anchor found")
    try:
        anchor = json.loads(match.group(1))
    except ValueError as exc:
        raise BodyProblem("body_anchor_mismatch", f"invalid cbc-evidence JSON: {exc}") from exc
    if not isinstance(anchor, dict):
        raise BodyProblem("body_anchor_mismatch", "cbc-evidence anchor must be an object")
    root = anchor.get("root_hash")
    count = anchor.get("link_count")
    if not isinstance(root, str) or not HASH_RE.fullmatch(root):
        raise BodyProblem("body_anchor_mismatch", "anchor root_hash is invalid")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise BodyProblem("body_anchor_mismatch", "anchor link_count is invalid")
    asset_count = anchor.get("asset_link_count")
    if not isinstance(asset_count, int) or isinstance(asset_count, bool) or asset_count < 0:
        raise BodyProblem("body_anchor_mismatch", "anchor asset_link_count is invalid")
    verified = anchor.get("verified_link_count")
    if verified is not None and (not isinstance(verified, int) or isinstance(verified, bool) or verified < 0):
        raise BodyProblem("body_anchor_mismatch", "anchor verified_link_count is invalid")
    expected_appendix = anchor.get("appendix_sha256")
    if not isinstance(expected_appendix, str) or not HASH_RE.fullmatch(expected_appendix):
        raise BodyProblem("body_anchor_mismatch", "anchor appendix_sha256 is missing or invalid")
    actual_appendix = sha256_bytes(appendix_preimage(text))
    if actual_appendix != expected_appendix:
        raise BodyProblem("body_anchor_mismatch", "appendix_sha256 does not match the appendix text")
    return anchor


def _broken_text(broken: Mapping[str, Any] | None) -> str:
    if not broken:
        return "none"
    index = broken.get("index")
    prefix = f"#{index} " if index is not None else ""
    text = f"{prefix}{broken.get('kind')} {broken.get('name')} — {broken.get('reason')}"
    expected = broken.get("expected")
    actual = broken.get("actual")
    if expected:
        text += f"; expected {expected}"
    if actual:
        text += f"; actual {actual}"
    if broken.get("detail"):
        text += f"; {broken['detail']}"
    return text


def _content_preimage(lines: list[str]) -> bytes:
    filtered = list(lines)
    while filtered and not filtered[0].strip():
        filtered.pop(0)
    while filtered and not filtered[-1].strip():
        filtered.pop()
    return "\n".join(filtered).encode("utf-8")


def render_appendix(report: Mapping[str, Any]) -> str:
    """Render the append-only CBC evidence block for a verification report."""
    status = str(report.get("cbc_chain_status", "FAIL"))
    root = report.get("root_hash")
    if not isinstance(root, str) or not HASH_RE.fullmatch(root):
        root = "sha256:" + ("0" * 64)
    declared = report.get("declared_root_hash")
    link_count = int(report.get("link_count", 0) or 0)
    asset_link_count = int(report.get("asset_link_count", 0) or 0)
    verified = int(report.get("verified_link_count", 0) or 0)
    upload = str(report.get("upload_status", "NOT_UPLOADED"))
    content: list[str] = []
    if status == "FAIL":
        content.extend(["## CBC chain failure (blocking for CBC upload)", ""])
    else:
        content.extend(["## CBC evidence chain", ""])
    gate = report.get("gate_status")
    if gate:
        content.append(f"- gate_status: **{gate}**")
    if status == "PASS" and upload == "NOT_UPLOADED":
        content.append("- cbc_chain_status: **PASS** (file integrity only; this is NOT a release PASS)")
    else:
        content.append(f"- cbc_chain_status: **{status}**")
    if status == "FAIL" and declared and declared != root:
        content.append(f"- root_hash: `{root}` (verified prefix through link #{verified}; declared root `{declared}`)")
    else:
        content.append(f"- root_hash: `{root}`")
    content.append(f"- link_count: {link_count}" + (f" (verified {verified})" if status == "FAIL" else ""))
    content.append(f"- asset_link_count: {asset_link_count}")
    content.append(f"- broken_link: {_broken_text(report.get('broken_link'))}")
    content.append(f"- upload_status: **{upload}**")
    reason = report.get("upload_blocked_reason")
    if reason:
        content.append(f"- upload_blocked_reason: `{reason}`")
    if report.get("declared_attached"):
        content.append("- declared_attached: true")
        if upload != "UPLOADED":
            content.append("- declared as attached but not uploaded")
    if status == "FAIL":
        content.append("- scope: blocks the CBC upload only; the CBS main package is not blocked by this section (F6)")
        content.append("- action: no upload performed; fix the artifact or publish a new version with ERRATUM")
    if report.get("gate_status") == "SKIPPED_INFRA" or status == "SKIPPED_INFRA":
        content.extend([
            "",
            "## Infrastructure failures",
            "",
            "- cbc: **SKIPPED_INFRA** — publish blocked for CBC; not counted in the 20% SKIP ratio",
        ])
    content.append("- skip_accounting: CBC is not counted in the CBE/CBP SKIP ratio")
    anchor = {
        "schema": "cbc-body-anchor/v1",
        "root_hash": root,
        "link_count": link_count,
        "asset_link_count": asset_link_count,
        "verified_link_count": verified,
        "appendix_sha256": sha256_bytes(_content_preimage(content)),
    }
    anchor_line = "<!-- cbc-evidence " + json.dumps(anchor, ensure_ascii=False, separators=(",", ":")) + " -->"
    lines = [BEGIN, anchor_line, *content, END]
    return "\n".join(lines) + "\n"


def render_not_uploaded_entry(report: Mapping[str, Any]) -> str:
    """One line for CBS's existing ``## NOT_UPLOADED`` list."""
    upload = str(report.get("upload_status", "NOT_UPLOADED"))
    if upload == "UPLOADED":
        raise BodyProblem("uploaded", "CBC is uploaded; NOT_UPLOADED entry does not apply")
    declared = bool(report.get("declared_attached"))
    status = str(report.get("cbc_chain_status", "FAIL"))
    if declared:
        line = "cbc: NOT_UPLOADED — declared as attached but not uploaded"
    else:
        line = "cbc: NOT_UPLOADED (not attached)"
    if status == "FAIL":
        broken = report.get("broken_link") or {}
        reason = broken.get("reason", "chain_failure")
        name = broken.get("name", "unknown")
        index = broken.get("index")
        prefix = f"#{index} " if index is not None else ""
        line += f"; broken_link: {prefix}{name} — {reason}"
    elif report.get("gate_status") == "SKIPPED_INFRA" or status == "SKIPPED_INFRA":
        line += "; SKIPPED_INFRA"
    return line
