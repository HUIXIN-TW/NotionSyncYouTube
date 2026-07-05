from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from notionsyncyoutube.errors import ApiError


class HttpClient:
    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_url = self._build_url(url, params)
        body = self._encode_body(json_body)
        request = Request(
            request_url,
            data=body,
            headers=headers or {},
            method=method,
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_text = response.read().decode("utf-8")
        except HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            raise ApiError(f"HTTP {exc.code} error from {url}:\n{error_text}") from exc
        except URLError as exc:
            raise ApiError(f"Request failed for {url}: {exc.reason}") from exc
        except OSError as exc:
            raise ApiError(f"Request failed for {url}: {exc}") from exc

        try:
            data = json.loads(response_text)
        except ValueError as exc:
            raise ApiError(f"Invalid JSON response from {url}") from exc

        if not isinstance(data, dict):
            raise ApiError(f"Unexpected JSON response from {url}: expected object")

        return data

    def _build_url(self, url: str, params: dict[str, Any] | None) -> str:
        if not params:
            return url

        query = urlencode(params)
        separator = "&" if "?" in url else "?"

        return f"{url}{separator}{query}"

    def _encode_body(self, json_body: dict[str, Any] | None) -> bytes | None:
        if json_body is None:
            return None

        return json.dumps(json_body).encode("utf-8")
