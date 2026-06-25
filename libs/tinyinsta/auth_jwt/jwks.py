from __future__ import annotations

import threading
import time

import requests


class JWKSClient:
    def __init__(self, jwks_url: str, *, ttl_seconds: int = 3600) -> None:
        self._jwks_url = jwks_url
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._keys: dict[str, object] = {}
        self._fetched_at: float = 0.0

    def _refresh(self) -> None:
        from jwt import PyJWK

        resp = requests.get(self._jwks_url, timeout=5)
        resp.raise_for_status()
        keys = {}
        for jwk in resp.json().get("keys", []):
            # Keep only signing keys: a JWKS also exposes encryption keys
            # (use="enc", e.g. RSA-OAEP) that PyJWT cannot load for verification.
            if jwk.get("use", "sig") != "sig":
                continue
            try:
                keys[jwk["kid"]] = PyJWK.from_dict(jwk).key
            except Exception:  # noqa: BLE001 — skip keys with unsupported algorithms
                continue
        with self._lock:
            self._keys = keys
            self._fetched_at = time.monotonic()

    def get_key(self, kid: str):
        expired = (time.monotonic() - self._fetched_at) > self._ttl
        if kid not in self._keys or expired:
            self._refresh()
        if kid not in self._keys:
            raise KeyError(f"unknown JWKS kid={kid}")
        return self._keys[kid]
