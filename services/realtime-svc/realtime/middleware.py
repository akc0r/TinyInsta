import os
from urllib.parse import parse_qs

import jwt
from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware

from tinyinsta.auth_jwt import JWKSClient, KeycloakUser

_jwks_client: JWKSClient | None = None


def _get_jwks_client() -> JWKSClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = JWKSClient(os.environ["OIDC_JWKS_URL"])
    return _jwks_client


def _decode(token: str) -> KeycloakUser | None:
    # Mirrors KeycloakJWTAuthentication, but for the WS handshake: browsers can't
    # set Authorization headers on a WebSocket, so the token comes in the query
    # string (?token=...). Signature + issuer are always verified.
    audience = os.environ.get("OIDC_AUDIENCE") or None
    try:
        kid = jwt.get_unverified_header(token)["kid"]
        key = _get_jwks_client().get_key(kid)
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            audience=audience,
            issuer=os.environ.get("OIDC_ISSUER") or None,
            options={"verify_aud": audience is not None},
        )
    except (jwt.PyJWTError, KeyError):
        return None
    return KeycloakUser(
        user_id=claims["sub"],
        username=claims.get("preferred_username", ""),
        claims=claims,
    )


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = None
        query = parse_qs((scope.get("query_string") or b"").decode())
        if query.get("token"):
            token = query["token"][0]
        scope["user"] = await sync_to_async(_decode)(token) if token else None
        return await super().__call__(scope, receive, send)
