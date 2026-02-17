import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from typing import Any

from starlette.datastructures import MutableHeaders


class SignedSessionMiddleware:
    def __init__(
        self,
        app,
        secret_key: str,
        cookie_name: str = "esop_session",
        max_age: int = 60 * 60 * 12,
        https_only: bool = False,
        same_site: str = "lax",
    ):
        self.app = app
        self.secret_key = secret_key.encode("utf-8")
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.https_only = https_only
        self.same_site = same_site

    def _sign(self, payload: str) -> str:
        digest = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    def _encode(self, data: dict[str, Any]) -> str:
        payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
        payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
        signature = self._sign(payload_b64)
        return f"{payload_b64}.{signature}"

    def _decode(self, raw: str | None) -> dict[str, Any]:
        if not raw or "." not in raw:
            return {}

        payload_b64, signature = raw.rsplit(".", 1)
        expected_signature = self._sign(payload_b64)
        if not hmac.compare_digest(signature, expected_signature):
            return {}

        try:
            payload = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
            data = json.loads(payload)
            if isinstance(data, dict):
                return data
        except Exception:
            return {}

        return {}

    def _read_cookie(self, scope) -> dict[str, Any]:
        headers = dict(scope.get("headers") or [])
        cookie_header = headers.get(b"cookie", b"").decode("latin-1")
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(self.cookie_name)
        if morsel is None:
            return {}
        return self._decode(morsel.value)

    def _set_cookie(self, headers: MutableHeaders, value: str) -> None:
        cookie = SimpleCookie()
        cookie[self.cookie_name] = value
        cookie[self.cookie_name]["path"] = "/"
        cookie[self.cookie_name]["max-age"] = str(self.max_age)
        cookie[self.cookie_name]["httponly"] = True
        cookie[self.cookie_name]["samesite"] = self.same_site
        if self.https_only:
            cookie[self.cookie_name]["secure"] = True

        expires = datetime.now(timezone.utc) + timedelta(seconds=self.max_age)
        cookie[self.cookie_name]["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        headers.append("set-cookie", cookie.output(header="").strip())

    def _delete_cookie(self, headers: MutableHeaders) -> None:
        cookie = SimpleCookie()
        cookie[self.cookie_name] = ""
        cookie[self.cookie_name]["path"] = "/"
        cookie[self.cookie_name]["max-age"] = "0"
        cookie[self.cookie_name]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        cookie[self.cookie_name]["httponly"] = True
        cookie[self.cookie_name]["samesite"] = self.same_site
        if self.https_only:
            cookie[self.cookie_name]["secure"] = True

        headers.append("set-cookie", cookie.output(header="").strip())

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        initial_session = self._read_cookie(scope)
        scope["session"] = initial_session.copy()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                current_session = scope.get("session") or {}

                if current_session:
                    encoded = self._encode(current_session)
                    self._set_cookie(headers, encoded)
                elif initial_session:
                    self._delete_cookie(headers)

            await send(message)

        await self.app(scope, receive, send_wrapper)
