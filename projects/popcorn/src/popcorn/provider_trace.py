"""Request-scoped provider HTTP evidence for execution traces."""

from __future__ import annotations

import contextvars
import json
import time
from contextlib import AbstractContextManager
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

Recorder = Callable[[str, dict[str, object], str, float], None]
_recorder: contextvars.ContextVar[Recorder | None] = contextvars.ContextVar("popcorn_provider_trace", default=None)
_current_request: contextvars.ContextVar["_ProviderRequest | None"] = contextvars.ContextVar("popcorn_http_request", default=None)
_SECRET_KEYS = {"authorization", "api_key", "apikey", "access_token", "token", "password", "secret", "guest_session_id"}
_LIMIT = 12_000


def _clean(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): "[REDACTED]" if str(key).casefold().replace("-", "_") in _SECRET_KEYS else _clean(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


def _clean_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(key, "[REDACTED]" if key.casefold().replace("-", "_") in _SECRET_KEYS else value)
             for key, value in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _payload(raw: bytes | None) -> object:
    if raw is None:
        return None
    try:
        value: object = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        value = raw.decode("utf-8", errors="replace")
    value = _clean(value)
    encoded = json.dumps(value, ensure_ascii=False, default=str)
    if len(encoded) > _LIMIT:
        return {"truncated": True, "preview": encoded[:_LIMIT], "original_chars": len(encoded)}
    return value


class _ProviderRequest(AbstractContextManager["_ProviderRequest"]):
    def __init__(self, provider: str, method: str, url: str, body: object):
        self.provider, self.method, self.url, self.body = provider, method.upper(), url, _clean(body)
        self.started = time.perf_counter()
        self.response_body: bytes | None = None
        self.http_status: int | None = None
        self._token = None

    def __enter__(self):
        self._token = _current_request.set(self)
        return self

    def response(self, raw: bytes) -> None:
        self.response_body = raw

    def __exit__(self, exc_type, exc, _tb) -> bool:
        recorder = _recorder.get()
        try:
            if recorder is not None:
                status = "error" if exc is not None else "ok"
                attrs: dict[str, object] = {
                    "provider": self.provider,
                    "method": self.method,
                    "url": _clean_url(self.url),
                    "request": self.body,
                    "response": _payload(self.response_body),
                }
                if isinstance(exc, HTTPError):
                    attrs["http_status"] = exc.code
                elif self.http_status is not None:
                    attrs["http_status"] = self.http_status
                elif exc is not None:
                    attrs["error_type"] = type(exc).__name__
                recorder("provider.http.call", attrs, status, (time.perf_counter() - self.started) * 1000)
        except Exception:
            # Evidence capture must not alter the provider request's outcome.
            pass
        finally:
            if self._token is not None:
                _current_request.reset(self._token)
        return False


def provider_request(provider: str, method: str, url: str, body: object = None) -> _ProviderRequest:
    return _ProviderRequest(provider, method, url, body)


def capture_provider_requests(recorder: Recorder):
    """Set the event recorder for provider calls made in this execution context."""
    return _recorder.set(recorder)


def restore_provider_recorder(token) -> None:
    _recorder.reset(token)


def provider_http_status(status: int) -> None:
    """Attach the real response status when the urllib response exposes it."""
    request = _current_request.get()
    if request is not None:
        request.http_status = status
