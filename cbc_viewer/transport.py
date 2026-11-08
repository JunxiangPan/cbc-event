"""GET-only GitHub transport for the read-only viewer.

There is no generic public ``request(method, ...)``.  The only public methods
are release/tag readers; the private method allowlist rejects everything that
is not GET/HEAD before any socket is opened.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .errors import InfraError, InputError, NotFoundError, ReadOnlyViolation

GITHUB_API = "https://api.github.com"
ALLOWED_METHODS = frozenset({"GET", "HEAD"})
SAFE_PART_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
RETRY_STATUS = {429, 500, 502, 503, 504}


class ReadOnlyTransport:
    """Minimal GitHub client that can only read."""

    def __init__(self, *, token: str | None = None, timeout: float = 20.0, retries: int = 3) -> None:
        self._token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        self.timeout = timeout
        self.retries = max(1, int(retries))

    @staticmethod
    def _safe_part(value: str, label: str) -> str:
        if not isinstance(value, str) or not SAFE_PART_RE.fullmatch(value):
            raise InputError(f"invalid {label}: {value!r}")
        return value

    def _request(self, method: str, url: str) -> bytes:
        verb = method.upper()
        if verb not in ALLOWED_METHODS:
            raise ReadOnlyViolation(f"read-only transport refuses {verb}")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cbc-viewer/0.1",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = urllib.request.Request(url, headers=headers, method=verb)
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise NotFoundError(f"remote object not found: {url}") from exc
                if exc.code in {401, 403}:
                    raise InfraError(f"GitHub API denied access ({exc.code}); cannot verify remotely") from exc
                if exc.code in RETRY_STATUS and attempt < self.retries:
                    time.sleep(min(0.5 * attempt, 2.0))
                    last = exc
                    continue
                if exc.code in RETRY_STATUS:
                    raise InfraError(f"GitHub API {exc.code} after {attempt} attempts: {url}") from exc
                raise InputError(f"GitHub API request failed ({exc.code}): {url}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = exc
                if attempt < self.retries:
                    time.sleep(min(0.5 * attempt, 2.0))
                    continue
                raise InfraError(f"GitHub API unreachable after {attempt} attempts: {exc}") from exc
        raise InfraError(f"GitHub API failed: {last}")

    def _get_json(self, path: str) -> dict[str, Any]:
        raw = self._request("GET", GITHUB_API + path)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise InfraError(f"GitHub API returned invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise InfraError("GitHub API returned a non-object JSON payload")
        return data

    def get_release(self, owner: str, repo: str, tag: str) -> dict[str, Any]:
        owner = self._safe_part(owner, "owner")
        repo = self._safe_part(repo, "repo")
        tag = self._safe_part(tag, "tag")
        return self._get_json(f"/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag)}")

    def get_tag_commit(self, owner: str, repo: str, tag: str) -> str | None:
        owner = self._safe_part(owner, "owner")
        repo = self._safe_part(repo, "repo")
        tag = self._safe_part(tag, "tag")
        data = self._get_json(f"/repos/{owner}/{repo}/commits/{urllib.parse.quote(tag)}")
        sha = data.get("sha")
        if isinstance(sha, str) and re.fullmatch(r"[0-9a-fA-F]{40}", sha):
            return sha.lower()
        return None

    def get_asset_bytes(self, asset: dict[str, Any]) -> bytes:
        url = asset.get("url")
        if not isinstance(url, str) or not url.startswith(GITHUB_API):
            raise InputError("asset has no usable GitHub API url")
        request = urllib.request.Request(url, headers={
            "Accept": "application/octet-stream",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cbc-viewer/0.1",
            **({"Authorization": f"Bearer {self._token}"} if self._token else {}),
        }, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise NotFoundError("remote asset not found") from exc
            if exc.code in RETRY_STATUS:
                raise InfraError(f"GitHub asset download failed ({exc.code})") from exc
            raise InputError(f"GitHub asset download failed ({exc.code})") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise InfraError(f"GitHub asset download failed: {exc}") from exc
